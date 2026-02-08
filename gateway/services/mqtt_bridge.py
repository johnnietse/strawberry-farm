"""
G.O.S. MQTT-to-Database Bridge
==============================
Bridges MQTT messages from Raspberry Pi border router to TimescaleDB.
For use with real nRF52 hardware deployment.

MQTT Topics:
- gos/telemetry/{node_id} - Sensor data from nodes
- gos/health/{node_id} - Node health/status updates
- gos/led/schedule - LED control commands
"""

import paho.mqtt.client as mqtt
import psycopg2
import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [MQTT-BRIDGE] %(message)s')
logger = logging.getLogger("MQTTBridge")

class MQTTDatabaseBridge:
    def __init__(self, db_url, mqtt_broker, mqtt_port):
        self.db_url = db_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.client = mqtt.Client(client_id="gos_bridge", protocol=mqtt.MQTTv5)
        
        # MQTT callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"Connected to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
        
        # Subscribe to all G.O.S. topics
        client.subscribe("gos/telemetry/#")
        client.subscribe("gos/health/#")
        client.subscribe("gos/led/schedule")
        logger.info("Subscribed to gos/telemetry/#, gos/health/#, gos/led/schedule")
    
    def on_disconnect(self, client, userdata, rc, properties=None):
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")
    
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if topic.startswith("gos/telemetry/"):
                self.handle_telemetry(topic, payload)
            elif topic.startswith("gos/health/"):
                self.handle_health(topic, payload)
            elif topic == "gos/led/schedule":
                self.handle_led_schedule(payload)
            else:
                logger.warning(f"Unknown topic: {topic}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    def handle_telemetry(self, topic, payload):
        """Insert telemetry data into raw_telemetry table."""
        node_id = topic.split('/')[-1]
        
        try:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO raw_telemetry 
                    (node_id, sample_identity, temp_c, humidity_pct, par_umol, battery_mv, rssi)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    node_id,
                    payload.get('eui64', payload.get('sample_identity')),
                    payload.get('temp_c', payload.get('temp')),
                    payload.get('humidity_pct', payload.get('humidity')),
                    payload.get('par_umol', payload.get('par')),
                    payload.get('battery_mv'),
                    payload.get('rssi')
                ))
            conn.commit()
            conn.close()
            logger.info(f"Telemetry from {node_id}: {payload.get('temp_c', payload.get('temp'))}°C")
        except Exception as e:
            logger.error(f"DB insert error: {e}")
    
    def handle_health(self, topic, payload):
        """Insert node health data into node_health table."""
        node_id = topic.split('/')[-1]
        
        try:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO node_health 
                    (node_id, battery_mv, rssi, uptime_seconds, reboot_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    node_id,
                    payload.get('battery_mv'),
                    payload.get('rssi'),
                    payload.get('uptime'),
                    payload.get('reboots', 0)
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Health insert error: {e}")
    
    def handle_led_schedule(self, payload):
        """Insert LED schedule changes into led_schedule_history table."""
        try:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO led_schedule_history 
                    (blue_ratio, red_ratio, intensity_pct, sector_id)
                    VALUES (%s, %s, %s, %s)
                """, (
                    payload.get('blue_ratio'),
                    payload.get('red_ratio'),
                    payload.get('intensity', 100),
                    payload.get('sector', 'ALL')
                ))
            conn.commit()
            conn.close()
            logger.info(f"LED schedule updated: Blue={payload.get('blue_ratio')}, Red={payload.get('red_ratio')}")
        except Exception as e:
            logger.error(f"LED schedule insert error: {e}")
    
    def run(self):
        logger.info("=== G.O.S. MQTT-DB BRIDGE STARTING ===")
        logger.info(f"Connecting to {self.mqtt_broker}:{self.mqtt_port}...")
        
        self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self.client.loop_forever()


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", 1883))
    
    if not db_url:
        logger.error("DATABASE_URL not set!")
        exit(1)
    
    bridge = MQTTDatabaseBridge(db_url, mqtt_broker, mqtt_port)
    bridge.run()
