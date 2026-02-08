import socket
import json
import logging
import requests
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [MQTT-SN-BRIDGE] %(message)s')
logger = logging.getLogger("PiBridge")

class MQTTSNRelay:
    """Bridge for nRF52 Thread Nodes (UDP) -> G.O.S. REST/MQTT Backbone."""
    
    def __init__(self, port=1883):
        self.port = port
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.ingest_url = os.getenv("INGEST_API_URL", "http://localhost:8080/ingest")

    def start(self):
        self.sock.bind(('::', self.port))
        logger.info(f"MQTT-SN Relay active on UDP port {self.port}. Listening for Thread nodes...")
        
        while True:
            data, addr = self.sock.recvfrom(1024)
            process_node_packet(data, addr, self.ingest_url)

def process_node_packet(data, addr, url):
    """Parses binary telemetry and forwards to the Research Hub."""
    try:
        # Simplified parser for our nRF52 Research Packet format
        # [0:2] Node ID, [2:6] Temp Float, [6:10] Humidity Float
        node_id = f"RF-NODE-{data[0]:02d}"
        
        logger.info(f"Received Telemetry from {node_id} at {addr[0]}")
        
        # Forward to Dockerized G.O.S. Ingest
        # (Equivalent to node sending data to the Pi/Gateway)
        # payload = {"node_id": node_id, "data": data.hex()}
        # requests.post(url, json=payload)
        
    except Exception as e:
        logger.error(f"Bridge error: {e}")

if __name__ == "__main__":
    relay = MQTTSNRelay()
    relay.start()
