# G.O.S. Raspberry Pi Integration Guide
## Role: OpenThread Border Router (OTBR) & Data Bridge

The Raspberry Pi is the central bridge that connects the 40-node Thread mesh (UDP/IPv6) to the G.O.S. Docker Backbone (MQTT/Postgres).

## 🛠 1. Hardware Preparation
1.  **Raspberry Pi 4B**: Main processor.
2.  **nRF52840 Dongle (PCA10059)**: Connect this to the Pi's USB port. It will act as the **Radio Co-Processor (RCP)**.
3.  **Flash RCP Firmware**:
    - Download `ot-rcp.nrf52840.hex` from the nRF Connect SDK.
    - Put the dongle in DFU mode (Reset button) and flash using `nrfutil`:
      ```bash
      nrfutil device program --firmware ot-rcp.hex --traits nrf52840
      ```

## 📦 2. Software Installation (on Raspberry Pi)
We use the official `ot-br-posix` stack to handle IPv6 routing.

1.  **Clone & Bootstrap**:
    ```bash
    git clone --recursive https://github.com/openthread/ot-br-posix
    cd ot-br-posix
    ./script/bootstrap
    ```
2.  **Setup for nRF52 USB**:
    ```bash
    INFRA_IF_NAME=eth0 ./script/setup
    ```
3.  **Reboot & Verify**:
    ```bash
    sudo service otbr-agent status
    sudo ot-ctl state
    # Expected: "disabled" or "leader" (if network is formed)
    ```

## 🌉 3. The MQTT-SN Bridge
Traditional MQTT (TCP) is too heavy for nRF52840 mesh nodes. We use **MQTT-SN (UDP)**.

1.  **Run the G.O.S. Bridge Service**:
    We have provided the [mqtt_sn_bridge.py](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/gateway/services/mqtt_sn_bridge.py) which should be auto-launched on the Pi. It listens for UDP packets on port 1883 and forwards them to your main database.

## 🔗 4. Forming the Research Mesh
From the Raspberry Pi terminal, run:
```bash
sudo ot-ctl dataset init new
sudo ot-ctl dataset networkname GOS_Mesh
sudo ot-ctl dataset panid 0xFACE
sudo ot-ctl dataset masterkey DEADBEEFCAFE
sudo ot-ctl dataset commit active
sudo ot-ctl ifconfig up
sudo ot-ctl thread start
```

Your 40 nRF52 nodes will now be able to join using the `masterkey`.
