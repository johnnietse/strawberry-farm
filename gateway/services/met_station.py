"""
G.O.S. Meteorological Station Simulation
=========================================
Simulates the Phytotron meteorological station measuring:
- Net radiation (W/m²)
- Spectral blue irradiance (W/m²/nm @ 450nm)
- Spectral red irradiance (W/m²/nm @ 660nm)
- Air temperature (°C)
- Relative humidity (%)
- CO2 concentration (ppm)

ELEC 490/498 Requirement: "Meteorological station measuring net radiation
and spectral irradiance"
"""

import asyncio
import random
import logging
import math
from datetime import datetime
import psycopg2
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [MET-STATION] %(message)s')
logger = logging.getLogger("MetStation")


class MetStationSimulator:
    """
    Simulates realistic Phytotron meteorological data.
    Uses diurnal patterns for solar radiation.
    """
    
    def __init__(self, db_url):
        self.db_url = db_url

    def get_solar_conditions(self):
        """Calculate solar conditions based on time of day."""
        now = datetime.now()
        hour = now.hour + now.minute / 60.0
        
        # Net radiation: follows sun pattern (0 at night, peak at noon)
        # Peak ~500 W/m² at solar noon, 0 at night
        if 6 <= hour <= 20:
            solar_angle = math.sin((hour - 6) * math.pi / 14)
            net_radiation = 500 * solar_angle + random.gauss(0, 20)
        else:
            net_radiation = random.gauss(0, 5)  # Small thermal radiation at night
        
        # Spectral irradiance depends on LED schedule and sunlight
        # Blue (450nm): ~45 W/m²/nm at peak
        # Red (660nm): ~180 W/m²/nm at peak
        spectral_blue = max(0, 45 * solar_angle + random.gauss(0, 3)) if 6 <= hour <= 20 else random.gauss(5, 1)
        spectral_red = max(0, 180 * solar_angle + random.gauss(0, 10)) if 6 <= hour <= 20 else random.gauss(20, 2)
        
        # Air temperature: follows diurnal cycle
        air_temp = 22 + 4 * math.sin((hour - 9) * math.pi / 12) + random.gauss(0, 0.5)
        
        # Relative humidity: inverse to temperature
        rel_humidity = 60 - 15 * math.sin((hour - 9) * math.pi / 12) + random.gauss(0, 2)
        
        # CO2: higher at night due to respiration
        co2 = 400 + (100 if hour < 6 or hour > 20 else 0) + random.gauss(0, 10)
        
        return {
            'net_radiation': max(0, net_radiation),
            'spectral_blue': max(0, spectral_blue),
            'spectral_red': max(0, spectral_red),
            'air_temp': air_temp,
            'rel_humidity': max(0, min(100, rel_humidity)),
            'co2': max(300, co2)
        }

    async def run(self):
        logger.info("=== METEOROLOGICAL STATION SIMULATION ===")
        logger.info("Sensors: Net radiation, Spectral (Blue/Red), Temp, RH, CO2")
        
        while True:
            # 5-minute sampling interval (standard for met stations)
            await asyncio.sleep(300)
            
            conditions = self.get_solar_conditions()
            
            try:
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO met_station_data 
                        (net_radiation, spectral_blue_irradiance, spectral_red_irradiance,
                         air_temp_c, relative_humidity_pct, co2_ppm)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        round(conditions['net_radiation'], 1),
                        round(conditions['spectral_blue'], 2),
                        round(conditions['spectral_red'], 2),
                        round(conditions['air_temp'], 2),
                        round(conditions['rel_humidity'], 1),
                        round(conditions['co2'], 0)
                    ))
                conn.commit()
                conn.close()
                
                logger.info(
                    f"Logged: NetRad={conditions['net_radiation']:.0f}W/m² | "
                    f"Blue={conditions['spectral_blue']:.1f} | "
                    f"Red={conditions['spectral_red']:.1f} | "
                    f"Temp={conditions['air_temp']:.1f}°C | "
                    f"RH={conditions['rel_humidity']:.0f}% | "
                    f"CO2={conditions['co2']:.0f}ppm"
                )
            except Exception as e:
                logger.error(f"DB Error: {e}")


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set!")
        exit(1)
    
    simulator = MetStationSimulator(db_url)
    asyncio.run(simulator.run())
