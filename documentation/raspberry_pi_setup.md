# G.O.S. Raspberry Pi Integration Guide
## Role: OpenThread Border Router (OTBR) & Data Bridge

The Raspberry Pi is the bridge between the Thread mesh of sensor nodes (IPv6/UDP) and the G.O.S. Docker backbone (TimescaleDB).

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

## 3. Receiving the sensor data

The nodes send a signed CoAP packet (PACKET_V4, see `hardware_protocol.md`) to `ff03::1`, UDP
5683, every 60 s. On the Pi, the `coap_receiver` service receives it on the Thread interface
only, checks the signature and counter, and writes it to TimescaleDB:

```bash
python gateway/tools/provision_node.py --index 1 --network-key <your 32-hex-digit network key>
docker compose --profile hardware up -d coap_receiver
```

(The earlier MQTT-SN bridge is not used by the rev 3.1 nodes.)

## 4. Forming the network

The network settings must match the node firmware (`pcbs/gos_sensor_node/firmware/prj.conf` and
the node's `credentials.conf`):

| Setting | Value |
|---|---|
| Channel | 15 |
| PAN ID | 0x1234 (4660) |
| Network name | GOS_PHYTOTRON |
| Extended PAN ID | dead00beef00cafe |
| Network key | your own random 32 hex digits, the same one passed to `provision_node.py` |

```bash
sudo ot-ctl dataset init new
sudo ot-ctl dataset channel 15
sudo ot-ctl dataset panid 0x1234
sudo ot-ctl dataset networkname GOS_PHYTOTRON
sudo ot-ctl dataset extpanid dead00beef00cafe
sudo ot-ctl dataset networkkey <your 32-hex-digit network key>
sudo ot-ctl dataset commit active
sudo ot-ctl ifconfig up
sudo ot-ctl thread start
sudo ot-ctl state        # "leader" after a few seconds
```

Never use an example key on a real network. The nodes join with the key from their
`credentials.conf`; see `documentation/bring_up.md` step 3.

## Parts

| Item | Part | Where (stock checked 2026-11-14) |
|---|---|---|
| Raspberry Pi | Raspberry Pi 4 Model B (2 GB or more) or Raspberry Pi 5 | Raspberry Pi approved resellers |
| Thread radio | Nordic nRF52840 Dongle (PCA10059), part `nRF52840-Dongle` | Mouser, 4,904 in stock |
