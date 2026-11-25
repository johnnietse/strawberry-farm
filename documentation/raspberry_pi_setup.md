# G.O.S. Raspberry Pi Integration Guide
## Role: OpenThread Border Router (OTBR) & Data Bridge

The Raspberry Pi is the bridge between the Thread mesh of sensor nodes (IPv6/UDP) and the G.O.S. Docker backbone (TimescaleDB).

## 🛠 1. Hardware Preparation
1.  **Raspberry Pi 4B**: Main processor.
2.  **nRF52840 Dongle (PCA10059)**: Connect this to the Pi's USB port. It will act as the **Radio Co-Processor (RCP)**.
    Use a USB 2.0 port and a short USB extension, so the Dongle sits outside the Pi's case and
    away from the USB 3.0 ports (they radiate noise in the 2.4 GHz band). In a closed metal
    growth chamber, put the Dongle inside, at a window or a cable port. Placement and cables:
    system assembly drawing, sheet 2 (`docs/images/drawings/system_assembly_sheet2.png`).
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
2.  **Setup for nRF52 USB**: `INFRA_IF_NAME` is the Pi's link to the rest of the network,
    `eth0` for a cable or `wlan0` for Wi-Fi. The Thread side does not depend on which network
    that is.
    ```bash
    INFRA_IF_NAME=wlan0 ./script/setup     # or eth0
    ```
3.  **Reboot & Verify**:
    ```bash
    sudo service otbr-agent status
    sudo ot-ctl state
    # Expected: "disabled" or "leader" (if network is formed)
    ```

## 3. Receiving the sensor data

The nodes send a signed CoAP packet (PACKET_V5 with rev 3.2 firmware, see `hardware_protocol.md`) to `ff03::1`, UDP
5683, every 60 s. On the Pi, the `coap_receiver` service receives it on the Thread interface
only, checks the signature and counter, and writes it to TimescaleDB:

```bash
python gateway/tools/provision_node.py --index 1 --network-key <your 32-hex-digit network key>
docker compose --profile hardware up -d coap_receiver
```

(The earlier MQTT-SN bridge is not used by the rev 3 nodes.)

## 3b. Running the whole stack

```bash
cp .env.example .env                    # then set passwords and GOS_API_TOKEN (see below)
python -c "import secrets; print(secrets.token_hex(24))"     # a token for GOS_API_TOKEN
docker compose --profile hardware --profile assistant up -d  # everything, incl. receiver and local LLM
OLLAMA="docker compose exec -T ollama ollama" bash ml_engine/models/fetch_models.sh
```

Then open `http://<pi address>:8080` from any computer or phone on the same network, open
**Access** at the top right and paste the token once. The forecast and LED models are in the
repository and need no internet; the language model comes from the Ollama registry or, offline,
from this repository's GitHub release. Ports, the token and use on other networks:
[`network_and_access.md`](network_and_access.md).

## 4. Forming the network

The network settings must match the node firmware (`pcbs/gos_sensor_node/firmware/prj.conf` and
the node's `credentials.conf`):

*Table 1. Thread network settings the border router forms; every node is provisioned with the same values.*

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

*Table 2. Gateway parts to buy.*

| Item | Part | Where (stock checked 2026-11-14) |
|---|---|---|
| Raspberry Pi | Raspberry Pi 4 Model B (2 GB or more) or Raspberry Pi 5 | Raspberry Pi approved resellers |
| Thread radio | Nordic nRF52840 Dongle (PCA10059), part `nRF52840-Dongle` | Mouser, 4,904 in stock |
