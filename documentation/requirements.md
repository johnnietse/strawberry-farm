# G.O.S. System Requirements & Support Matrix

To successfully deploy and run the **Illuminate & Automate** project, ensure you have the following hardware and software support in place.

## 🛠 1. Hardware Support (The Physical Tier)

### 🛰 Edge Nodes (The "40 Nodes")
*   **MCU**: Nordic nRF52840 (Dongles, DKs, or custom PCBs).
*   **Sensors**: Sensirion SHT4x (I2C) for high-accuracy climate monitoring.
*   **Light Sensing**: TSL2591 (I2C) for PAR/Lux measurements.
*   **Actuators**: Red/Blue LED Growth Channels connected via GPIO (P0.13/P0.14).
*   **Memory**: Optional QSPI Flash (e.g., MX25R6435F) for offline data persistence.

### 🌉 Gateway & Border Router
*   **Host**: Raspberry Pi 4B (4GB+ RAM recommended).
*   **Radio Co-Processor (RCP)**: nRF52840 Dongle (PCA10059) connected via USB to the Pi.
*   **Power**: 5V/3A stable power supply for the Pi.

## 💻 2. Software Support (The Digital Tier)

### 🐳 Infrastructure (The Cluster)
*   **Docker Desktop**: Required to run the 11-service G.O.S. cluster.
*   **Docker Compose v3.8+**: For orchestration of the Data Backbone and AI tiers.
*   **PostgreSQL 15+**: (Included in the Docker cluster).

### 🛠 Development & Build Tools
*   **Python 3.11+**: Required for the `run.py` CLI and various support scripts.
*   **nRF Connect SDK (v2.x)**: Required to build the [Zephyr RTOS firmware](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/src/main.cpp).
*   **West (Zephyr Tool)**: For building and flashing the embedded code.
*   **VS Code**: Highly recommended with the *nRF Connect for VS Code* extension.

### 🌐 Networking & Protocols
*   **OpenThread Border Router (OTBR)**: `ot-br-posix` installed on the Raspberry Pi.
*   **MQTT-SN / CoAP**: Support for low-power UDP-based messaging (handled by our [Bridge](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/gateway/services/mqtt_sn_bridge.py)).

### 📊 Research Assistant GUI
*   **Web Browser**: Latest Chrome, Edge, or Firefox (for the HTML5/JS Dashboard).
*   **Internet Access**: Only required if enabling external LLM tokens for the research assistant.

---
*For detailed setup instructions, refer to the [Raspberry Pi Setup Guide](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/documentation/raspberry_pi_setup.md).*
