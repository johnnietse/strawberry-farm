import asyncio
import random
import logging
import math
from datetime import datetime
import psycopg2
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [PHYTOTRON] %(message)s')
logger = logging.getLogger("PhytotronSim")

class PhytotronSimulator:
    """
    Production-grade Phytotron simulation for Queen's University.
    Simulates 40 nRF52840 sensor nodes with realistic environmental patterns.
    Uses TimescaleDB-compatible schema for real-world deployment.
    """
    
    def __init__(self, db_url, node_count=40):
        self.db_url = db_url
        self.node_count = node_count
        self.start_time = datetime.now()
        # Sector mapping (real greenhouse would have physical sectors)
        self.sectors = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2']

    def get_ambient_conditions(self):
        """Calculates realistic diurnal temperature and humidity."""
        now = datetime.now()
        hour = now.hour + now.minute/60.0
        
        # Diurnal temperature cycle: peaks at 3 PM (hour 15), lowest at 5 AM
        # Ontario greenhouse typical range: 18C (night) to 26C (day)
        temp_base = 22 + 4 * math.sin((hour - 9) * math.pi / 12)
        
        # Relative humidity: inverse to temperature
        # Range: 45% (day) to 75% (night)
        hum_base = 60 - 15 * math.sin((hour - 9) * math.pi / 12)
        
        # PAR (Photosynthetically Active Radiation) follows sun pattern
        # Peak at solar noon, zero at night
        if 6 <= hour <= 20:
            par_base = 800 * math.sin((hour - 6) * math.pi / 14)
        else:
            par_base = 0
            
        return temp_base, hum_base, max(0, par_base)

    def get_node_sector(self, node_index):
        """Maps node index to greenhouse sector."""
        return self.sectors[node_index % len(self.sectors)]

    async def simulate_node(self, node_index):
        """Simulates a single nRF52840 node with local variance."""
        node_id = f"PH-NODE-{node_index:02d}"
        eui64 = f"00:11:22:33:44:55:66:{node_index:02X}"
        sector = self.get_node_sector(node_index)
        
        # Simulate initial boot delay (realistic mesh joining)
        await asyncio.sleep(random.uniform(5, 30))
        logger.info(f"Node {node_id} joined mesh (Sector {sector})")
        
        while True:
            # Sampling interval: 60s ± 5s (realistic sensor jitter)
            await asyncio.sleep(60 + random.uniform(-5, 5))
            
            amb_temp, amb_hum, amb_par = self.get_ambient_conditions()
            
            # Local micro-climate variance
            node_temp = amb_temp + random.gauss(0, 0.3)
            node_hum = amb_hum + random.gauss(0, 2)
            node_par = amb_par + random.gauss(0, 50)
            
            # Simulate sensor-specific anomalies
            # Node 12: Near heating vent (warmer)
            if node_index == 12:
                node_temp += 2.5
            # Node 28: Near door (drafty, cooler)
            if node_index == 28:
                node_temp -= 1.5
                node_hum += 5
            
            # Simulate battery drain (realistic: starts at 4200mV, drains slowly)
            runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
            battery_mv = int(4200 - (runtime_hours * 0.5) + random.gauss(0, 20))
            battery_mv = max(3200, min(4200, battery_mv))
            
            # Simulate RSSI (signal strength)
            rssi = -50 - (node_index % 20) + random.randint(-5, 5)
            
            try:
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    # Insert telemetry (TimescaleDB hypertable)
                    cur.execute("""
                        INSERT INTO raw_telemetry 
                        (node_id, sample_identity, temp_c, humidity_pct, par_umol, battery_mv, rssi)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        node_id, 
                        eui64, 
                        round(node_temp, 2),
                        round(node_hum, 1),
                        round(max(0, node_par), 1),
                        battery_mv,
                        rssi
                    ))
                    
                    # Update node health table
                    uptime = int((datetime.now() - self.start_time).total_seconds())
                    cur.execute("""
                        INSERT INTO node_health 
                        (node_id, battery_mv, rssi, uptime_seconds)
                        VALUES (%s, %s, %s, %s)
                    """, (node_id, battery_mv, rssi, uptime))
                    
                conn.commit()
                conn.close()
                logger.info(f"{node_id} [{sector}]: {node_temp:.1f}°C | {node_hum:.0f}% | {node_par:.0f}µmol | {battery_mv}mV")
            except Exception as e:
                logger.error(f"Node {node_index} DB error: {e}")

    async def run(self):
        logger.info(f"=== PHYTOTRON SIMULATION STARTING ===")
        logger.info(f"Nodes: {self.node_count} | Sectors: {len(self.sectors)}")
        logger.info(f"Database: TimescaleDB")
        logger.info(f"=====================================")
        
        tasks = [self.simulate_node(i) for i in range(1, self.node_count + 1)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set!")
        exit(1)
        
    sim = PhytotronSimulator(db_url, node_count=40)
    asyncio.run(sim.run())
