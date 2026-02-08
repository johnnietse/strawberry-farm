"""
G.O.S. Research Curation Engine (Data Backbone)
================================================
ELEC 490/498 Requirement: Robust preprocessing pipeline to ingest, validate,
synchronize, and curate data from multiple sources.

Sources:
1. Hardware Telemetry (40 nRF52 nodes)
2. Meteorological Station (net radiation, spectral irradiance)
3. Auxiliary Inputs (LED schedules, yield, researcher events via GUI)

Output:
- Clean, ML-ready datasets with PRESERVED SAMPLE IDENTITY
"""

import pandas as pd
import psycopg2
import os
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [DATA-BACKBONE] %(message)s')
logger = logging.getLogger("ResearchCurationEngine")

# === DATA VALIDATION SCHEMA (Pydantic) ===
class TelemetryRecord(BaseModel):
    """Schema for validating incoming telemetry data."""
    node_id: str
    sample_identity: Optional[str] = None
    temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    par_umol: Optional[float] = None
    battery_mv: Optional[int] = None
    
    @field_validator('temp_c')
    @classmethod
    def validate_temp(cls, v):
        if v is not None and (v < -10 or v > 60):
            raise ValueError(f'Temperature {v}°C out of valid range [-10, 60]')
        return v
    
    @field_validator('humidity_pct')
    @classmethod
    def validate_humidity(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f'Humidity {v}% out of valid range [0, 100]')
        return v
    
    @field_validator('par_umol')
    @classmethod
    def validate_par(cls, v):
        if v is not None and (v < 0 or v > 3000):
            raise ValueError(f'PAR {v} out of valid range [0, 3000]')
        return v


class ResearchCurationEngine:
    """
    The 'Data Backbone' for Queen's Phytotron ELEC 490/498 project.
    
    Implements:
    - Ingestion from PostgreSQL/TimescaleDB
    - Validation using Pydantic schemas
    - Temporal synchronization (triple-join)
    - Curation with preserved sample identity
    """
    
    def __init__(self, db_url):
        self.db_url = db_url
        self.output_path = "/app/data/curated_research_dataset.csv"
        self.validation_errors = []
    
    def validate_telemetry(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates telemetry data using Pydantic schema."""
        valid_records = []
        self.validation_errors = []
        
        for idx, row in df.iterrows():
            try:
                record = TelemetryRecord(
                    node_id=row['node_id'],
                    sample_identity=row.get('sample_identity'),
                    temp_c=row.get('temp_c'),
                    humidity_pct=row.get('humidity_pct'),
                    par_umol=row.get('par_umol'),
                    battery_mv=row.get('battery_mv')
                )
                valid_records.append(row)
            except ValidationError as e:
                self.validation_errors.append({
                    'node_id': row.get('node_id'),
                    'error': str(e)
                })
        
        if self.validation_errors:
            logger.warning(f"Filtered {len(self.validation_errors)} invalid records")
        
        return pd.DataFrame(valid_records).reset_index(drop=True)

    def curate_ml_ready_set(self):
        """
        Assembles the high-fidelity ML-ready dataset from THREE distinct streams.
        Performs temporal joins with preserved sample identity.
        """
        try:
            conn = psycopg2.connect(self.db_url)
            
            # --- SOURCE 1: HARDWARE TELEMETRY (40 nRF52 nodes) ---
            df_hardware = pd.read_sql("""
                SELECT 
                    time as timestamp,
                    node_id, 
                    sample_identity,
                    temp_c,
                    humidity_pct,
                    par_umol,
                    battery_mv,
                    rssi
                FROM raw_telemetry 
                WHERE time > NOW() - INTERVAL '24 hours'
                ORDER BY time DESC
            """, conn)
            
            # Validate hardware data
            if not df_hardware.empty:
                df_hardware = self.validate_telemetry(df_hardware)
            
            # --- SOURCE 2: METEOROLOGICAL STATION ---
            df_met = pd.read_sql("""
                SELECT 
                    time as met_ts,
                    net_radiation,
                    spectral_blue_irradiance,
                    spectral_red_irradiance,
                    air_temp_c,
                    relative_humidity_pct,
                    co2_ppm
                FROM met_station_data 
                WHERE time > NOW() - INTERVAL '24 hours'
            """, conn)
            
            # --- SOURCE 3: RESEARCHER INPUTS (Group 2 GUI / LLM) ---
            df_events = pd.read_sql("""
                SELECT 
                    time as event_ts,
                    event_type,
                    severity,
                    description,
                    created_via_llm
                FROM research_events 
                WHERE time > NOW() - INTERVAL '7 days'
            """, conn)
            
            # --- SOURCE 4: LED SCHEDULE HISTORY ---
            df_led = pd.read_sql("""
                SELECT 
                    time as led_ts,
                    blue_ratio,
                    red_ratio,
                    intensity_pct,
                    sector_id
                FROM led_schedule_history 
                WHERE time > NOW() - INTERVAL '24 hours'
            """, conn)
            
            # --- SOURCE 5: YIELD DATA ---
            df_yield = pd.read_sql("""
                SELECT 
                    time as yield_ts,
                    row_index,
                    weight_grams,
                    brix_value,
                    plant_id
                FROM yield_logs 
                WHERE time > NOW() - INTERVAL '30 days'
            """, conn)
            
            if df_hardware.empty:
                logger.warning("Data backbone ready, awaiting hardware telemetry...")
                conn.close()
                return
            
            logger.info(f"Loaded: {len(df_hardware)} telemetry, {len(df_met)} met, {len(df_events)} events, {len(df_led)} LED, {len(df_yield)} yield")
            
            # --- TEMPORAL SYNCHRONIZATION (Triple+ Joins) ---
            
            # 1. Join Hardware with Meteorological (nearest within 10 minutes)
            df_hardware['timestamp'] = pd.to_datetime(df_hardware['timestamp'])
            if not df_met.empty:
                df_met['met_ts'] = pd.to_datetime(df_met['met_ts'])
                df_joined = pd.merge_asof(
                    df_hardware.sort_values('timestamp'),
                    df_met.sort_values('met_ts'),
                    left_on='timestamp',
                    right_on='met_ts',
                    direction='nearest',
                    tolerance=pd.Timedelta('10 minutes')
                )
            else:
                df_joined = df_hardware
            
            # 2. Join with LED Schedule (backward - what was the light setting)
            if not df_led.empty:
                df_led['led_ts'] = pd.to_datetime(df_led['led_ts'])
                df_joined = pd.merge_asof(
                    df_joined.sort_values('timestamp'),
                    df_led.sort_values('led_ts'),
                    left_on='timestamp',
                    right_on='led_ts',
                    direction='backward',
                    tolerance=pd.Timedelta('1 hour')
                )
            
            # 3. Join with Research Events (backward - carry event state)
            if not df_events.empty:
                df_events['event_ts'] = pd.to_datetime(df_events['event_ts'])
                df_final = pd.merge_asof(
                    df_joined.sort_values('timestamp'),
                    df_events.sort_values('event_ts'),
                    left_on='timestamp',
                    right_on='event_ts',
                    direction='backward',
                    tolerance=pd.Timedelta('24 hours')
                )
            else:
                df_final = df_joined
            
            # --- ENSURE PRESERVED SAMPLE IDENTITY ---
            # Critical ELEC 490/498 requirement
            if 'sample_identity' not in df_final.columns:
                df_final['sample_identity'] = df_final['node_id']
            
            # --- EXPORT ML-READY CURATION ---
            os.makedirs("/app/data", exist_ok=True)
            df_final.to_csv(self.output_path, index=False)
            
            logger.info(f"✓ DATA BACKBONE CURATED: {len(df_final)} rows")
            logger.info(f"  - Sample identities preserved: {df_final['sample_identity'].nunique()}")
            logger.info(f"  - Output: {self.output_path}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Backbone Curation Failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import time
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set!")
        exit(1)
    
    engine = ResearchCurationEngine(db_url)
    logger.info("=== ELEC 490/498 DATA BACKBONE INITIALIZED ===")
    
    while True:
        engine.curate_ml_ready_set()
        time.sleep(300)  # Re-curate every 5 minutes
