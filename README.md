# 🌿 G.O.S. - Greenhouse Operating System
## High-Throughput Plant Phenotyping Platform

**Illuminate & Automate: Reinforcement Learning + IoT Sensor Array for LED-Steered Transpiration in Greenhouse Strawberries**

---

## 📋 Table of Contents

1. [What is G.O.S.?](#-what-is-gos)
2. [Hardware](#hardware)
3. [System Architecture](#-system-architecture)
4. [Data Flow Workflow](#-data-flow-workflow)
5. [Quick Start](#-quick-start)
6. [Testing & Verification](#-testing--verification)
7. [File Reference](#-file-reference)
8. [API Endpoints](#-api-endpoints)
9. [Hardware Integration](#-hardware-integration)

---

## 🎯 What is G.O.S.?

G.O.S. is an **open-source phenotyping platform** that transforms raw greenhouse sensor data into actionable plant insights:

| Feature | Description |
|:---|:---|
| **40 Wireless Nodes** | nRF52840 sensors (Thread mesh) |
| **VPD Calculation** | Real-time vapor pressure deficit |
| **Transpiration** | Penman-Monteith estimation |
| **Stress Detection** | Multi-factor scoring (0-100) |
| **LED Control** | RL-based spectral recommendations |
| **ML Pipeline** | 5-source temporal synchronization |

---

## Hardware

Two custom boards plus off-the-shelf parts. Both boards are 4-layer (two solid ground planes),
fully designed, DRC-clean and ready to order assembled from JLCPCB; none has been built yet.

| Piece | What it does | Where | Status |
|---|---|---|---|
| **Sensor node** (40 x 65 mm) | nRF52840 module running Zephyr RTOS and OpenThread; SHT40 temperature/humidity, TSL2591 light, 18650 battery with USB-C charging; sends a signed reading every 60 s; drives the LED board with two PWM signals | one per measurement point, in its own enclosure | [`pcbs/gos_sensor_node`](pcbs/gos_sensor_node) |
| **LED driver** (60 x 45 mm) | two AL8860 constant-current channels (blue 448 nm, red 655 nm strings, 333 mA) from a 24 V adapter, dimmed by the node's PWM | one per grow light, in its own enclosure at the light | [`pcbs/led_driver`](pcbs/led_driver) |
| Border router | Raspberry Pi + Nordic nRF52840 Dongle running the OpenThread border router; the `coap_receiver` service checks each packet's signature and writes it to TimescaleDB | one per phytotron | [`documentation/raspberry_pi_setup.md`](documentation/raspberry_pi_setup.md) |

```mermaid
graph LR
    subgraph Node["Sensor node (battery)"]
        S[SHT40 + TSL2591] --> M[nRF52840 module<br/>Zephyr + OpenThread]
        B[18650 + BQ24074 charger] --> M
    end
    M -- "4-wire cable, 2 x PWM 250 Hz" --> L[LED driver board<br/>2 x AL8860, 24 V]
    L --> LED[Blue + red LED strings]
    M -- "Thread 802.15.4, signed CoAP every 60 s" --> R[Raspberry Pi + nRF52840 Dongle<br/>OpenThread border router]
    R --> DB[(TimescaleDB)]
    DB --> A[API / dashboard / RL agent]
    A -. "LED mix" .-> M
```

### Boards

| Sensor node | LED driver |
|---|---|
| ![Sensor node, top](pcbs/gos_sensor_node/docs/gos_sensor_node_render_top.png) | ![LED driver, top](pcbs/led_driver/docs/led_driver_render_top.png) |
| ![Sensor node top copper](docs/images/gos_sensor_node_top_copper.svg) | ![LED driver top copper](docs/images/led_driver_top_copper.svg) |

Bottom views, assembly drawings, courtyards, all layers and STEP models: `pcbs/*/docs/`.

<details>
<summary>Schematics (click to open)</summary>

Sensor node: [top level](docs/images/schematics/gos_sensor_node.svg) ·
[power](docs/images/schematics/gos_sensor_node-Power.svg) ·
[MCU](docs/images/schematics/gos_sensor_node-MCU.svg) ·
[sensors](docs/images/schematics/gos_sensor_node-Sensors.svg) ·
[connectors](docs/images/schematics/gos_sensor_node-Connectors.svg)

![Sensor node power](docs/images/schematics/gos_sensor_node-Power.svg)
![Sensor node MCU](docs/images/schematics/gos_sensor_node-MCU.svg)

LED driver: [schematic](docs/images/schematics/led_driver.svg)

![LED driver](docs/images/schematics/led_driver.svg)

PDFs: `pcbs/gos_sensor_node/gos_sensor_node_schematic.pdf`, `pcbs/led_driver/led_driver_schematic.pdf`.
</details>

### Enclosures

| Sensor node (exploded) | LED driver (exploded) |
|---|---|
| ![Sensor node enclosure](docs/images/sensor_enclosure_exploded.png) | ![LED driver enclosure](docs/images/led_enclosure_exploded.png) |
| ![Board inside the enclosure, top view](mechanical/fit_check_top.png) | ![LED board inside its enclosure](mechanical/led_fit_top.png) |

Generated from the KiCad boards and fit checked by [`mechanical/fit_check.py`](mechanical/fit_check.py);
print files in [`mechanical/print/`](mechanical/print) (ASA). Details: [`mechanical/README.md`](mechanical/README.md).

### Verification so far

| Check | Result |
|---|---|
| KiCad DRC, every severity, with schematic parity | 0 violations, 0 unrouted, 0 mismatches (both boards) |
| Layout review (USB pair, buck switching loop, antenna strip) | [`documentation/design_review.md`](documentation/design_review.md) |
| LTspice: LED current, switching frequency, PWM dimming, fail-safe, battery sense, reversed cell | all pass after two design fixes: [`simulation/README.md`](simulation/README.md) |
| Firmware build (Zephyr main, SDK 1.0.1) | no warnings, 214 KB flash, 62 KB RAM |
| Gateway receiver tests | 44 pass |
| Enclosure fit | 12 checks pass |

| LED channel at 24 V (LTspice) | PWM dimming 50 % (LTspice) |
|---|---|
| ![LED channel](simulation/plots/led_channel_24V.png) | ![PWM dimming](simulation/plots/led_pwm_50pct.png) |

**Order it:** [`documentation/ordering.md`](documentation/ordering.md) (JLCPCB settings, every part with
stock, what to buy separately). **Build it:** [`documentation/bring_up.md`](documentation/bring_up.md).

---

## 🏗️ System Architecture

### Service Topology (12 Docker Containers)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│   Dashboard (:8080)  │  Grafana (:3000)  │  API (:5000)     │
├─────────────────────────────────────────────────────────────┤
│                    DATA STORAGE LAYER                        │
│                   TimescaleDB (:5432)                        │
│  ┌────────────┬────────────┬────────────┬────────────┐      │
│  │raw_telemetry│met_station │research_   │led_schedule│      │
│  │            │_data       │events      │_history    │      │
│  └────────────┴────────────┴────────────┴────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                  PROCESSING LAYER                            │
│  sync_engine │ api │ ml_engine │ biology_engine │ safety    │
├─────────────────────────────────────────────────────────────┤
│                   INGESTION LAYER                            │
│  mqtt_bridge │ ingest (farm_sim) │ met_station              │
├─────────────────────────────────────────────────────────────┤
│                   MESSAGING LAYER                            │
│              Mosquitto MQTT (:1883 / :9001)                  │
├─────────────────────────────────────────────────────────────┤
│                    HARDWARE LAYER                            │
│  Raspberry Pi (OTBR) ─── nRF52840 Nodes (x40) ─── Sensors   │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependencies

```mermaid
graph TD
    DB[TimescaleDB] --> MQTT_BRIDGE[mqtt_bridge]
    DB --> INGEST[ingest/farm_sim]
    DB --> MET[met_station]
    DB --> API[api]
    INGEST --> SYNC[sync_engine]
    MET --> SYNC
    SYNC --> ML[ml_engine]
    BIO[biology_engine] --> ML
    MQTT[Mosquitto] --> MQTT_BRIDGE
    API --> DASH[dashboard]
    DB --> GRAFANA[Grafana]
```

---

## 🔄 Data Flow Workflow

### Step-by-Step Data Journey

```
1. SENSOR LAYER
   └── Sensor nodes (rev 3.1) measure temperature, humidity, light (lux) and battery
   └── Send a signed CoAP packet (PACKET_V4) over Thread every 60 s

2. GATEWAY LAYER
   └── Raspberry Pi runs OTBR (OpenThread Border Router) with an nRF52840 Dongle
   └── coap_receiver checks the HMAC signature, EUI-64 and replay counter

3. INGESTION LAYER
   └── coap_receiver inserts each reading into raw_telemetry
       (lux, counter and charger flags in the payload column)
   └── mqtt_bridge.py handles MQTT sources (simulation, other instruments)

4. METEOROLOGICAL LAYER
   └── met_station.py logs pyranometer + spectrometer data
   └── Writes to met_station_data table

5. SYNCHRONIZATION LAYER
   └── sync.py runs every 5 minutes
   └── Performs 5-source temporal joins:
       ├── raw_telemetry (hardware)
       ├── met_station_data (environment)
       ├── led_schedule_history (light control)
       ├── research_events (annotations)
       └── yield_logs (harvest data)
   └── Outputs curated_research_dataset.csv

6. PHENOTYPING LAYER
   └── api.py exposes /api/phenotype endpoint
   └── Calculates VPD, transpiration, stress in real-time
   └── Returns LED recommendations

7. ML LAYER
   └── agent_rl.py loads curated dataset
   └── Trains/runs RL policy for LED optimization
   └── biology_engine provides physics constraints

8. VISUALIZATION LAYER
   └── dashboard/ displays real-time data
   └── Grafana provides monitoring dashboards
   └── LLM assistant enables natural language queries
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop 24+
- Python 3.11+
- 8GB RAM minimum

### Installation

```bash
# Clone repository
git clone https://github.com/queensu-epower/gos.git
cd Stawberry_Farm

# Windows setup
.\setup.bat

# OR manual setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Running the System

```bash
# Start all 12 services
python run.py --up

# Check service status
python run.py --status

# View sync engine logs
python run.py --logs backbone

# View ML engine logs
python run.py --logs ai

# Stop all services
python run.py --down

# Clean (removes all data!)
python run.py --clean
```

### Access Points

| Service | URL | Credentials |
|:---|:---|:---|
| Dashboard | http://localhost:8080 | — |
| Grafana | http://localhost:3000 | admin / (see .env) |

| API | http://localhost:5000 | — |
| Database | localhost:5432 | researcher / (see .env) |

| MQTT | localhost:1883 | — |

---

## 🧪 Testing & Verification

### 1. Verify Docker Services

```bash
# Check all containers are running
docker compose ps

# Expected: 12 services with "Up" status
```

### 2. Test Database Connection

```bash
# Connect to database
docker exec -it stawberry_farm-db-1 psql -U researcher -d strawberry_research

# Check tables exist
\dt

# Query sample data
SELECT COUNT(*) FROM raw_telemetry;
SELECT * FROM raw_telemetry ORDER BY time DESC LIMIT 5;
```

### 3. Test API Endpoints

```bash
# Get node status
curl http://localhost:5000/api/nodes

# Calculate phenotype
curl -X POST http://localhost:5000/api/phenotype \
  -H "Content-Type: application/json" \
  -d '{"temp_c": 25.0, "humidity_pct": 65.0, "par_umol": 800.0}'

# Get phenotype summary
curl http://localhost:5000/api/phenotype/summary

# Log a research event
curl -X POST http://localhost:5000/api/event \
  -H "Content-Type: application/json" \
  -d '{"type": "pest", "description": "Spider mites on row 3", "severity": 2}'
```

### 4. Test Data Pipeline

```bash
# Wait 5 minutes for sync cycle, then check:
ls -la data/

# Should see: curated_research_dataset.csv
```

### 5. Test MQTT (Real Hardware)

```bash
# Subscribe to all topics
mosquitto_sub -h localhost -t "gos/#" -v

# Publish test message
mosquitto_pub -h localhost -t "gos/node/test01/telemetry" \
  -m '{"temp_c": 24.5, "humidity_pct": 62.0, "par_umol": 750}'
```

---

## 📂 File Reference

### Root Directory

| File | Purpose |
|:---|:---|
| `docker-compose.yml` | Orchestrates 12 Docker services |
| `run.py` | CLI tool for system management |
| `setup.bat` | Windows environment setup |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

### gateway/ - Data Backbone Services

| File | Purpose | Writes To |
|:---|:---|:---|
| `schema.sql` | Database schema (6 hypertables) | TimescaleDB |
| `services/sync.py` | 5-source temporal joins | `data/curated_*.csv` |
| `services/api.py` | REST API + phenotype endpoints | — |
| `services/mqtt_bridge.py` | MQTT → Database | `raw_telemetry` |
| `services/farm_sim.py` | 40-node sensor simulation | `raw_telemetry` |
| `services/met_station.py` | Met station simulation | `met_station_data` |
| `services/coap_receiver.py` | Receives signed packets from real sensor nodes over Thread | `raw_telemetry` |
| `tools/provision_node.py` | Creates a node's signing key and its `credentials.conf` | `secrets/node_keys.json` |
| `services/mqtt_sn_bridge.py` | MQTT-SN for nRF52 | — |
| `services/safety_ltl.py` | LTL safety monitor | — |
| `Dockerfile` | Container build | — |
| `requirements.txt` | Python deps | — |

### ml_engine/ - Machine Learning

| File | Purpose | Input | Output |
|:---|:---|:---|:---|
| `phenotyping.py` | VPD, transpiration, stress | Sensor data | Phenotype metrics |
| `plant_sim_c3.py` | FvCB photosynthesis model | T, CO2, PAR | Assimilation rate |
| `agent_rl.py` | LED control RL agent | Curated CSV | LED recommendations |
| `spectral_opt.py` | Spectral optimization | LED params | Optimal ratios |
| `macq_learner.py` | Action model learning | Trace data | PDDL actions |
| `domain.pddl` | AI planning domain | — | — |

### pcbs/gos_sensor_node/ - Sensor Node Hardware and Firmware (rev 3.1)

| Path | Purpose |
|:---|:---|
| `HARDWARE.md` | Design reference: pin map, power, signing, sources |
| `generate_schematics.py`, `generate_pcb.py` | Generate the KiCad schematic and board |
| `route_pcb.py` | Autoroute (Freerouting), ground planes and stitching, DRC, write `fab/` (Gerbers, drill, JLCPCB BOM and placement) and `docs/` (PDFs, renders, STEP) |
| `review_layout.py` | Measure the USB pair, buck switching loop and antenna strip |
| `fab/`, `docs/` | Order files; assembly, courtyard, user-layer and all-layer PDFs, renders, STEP |
| `firmware/` | Zephyr firmware to build and flash (`raytac_mdbt50q_db_40/nrf52840`) |

### pcbs/led_driver/ - LED Driver Board (rev 1.0)

| Path | Purpose |
|:---|:---|
| `README.md` | Design choices, ratings, recommended LEDs |
| `generate_schematic.py`, `generate_pcb.py` | Generate the KiCad schematic and board (routed with `../gos_sensor_node/route_pcb.py`) |
| `fab/`, `docs/` | Order files and documentation outputs |

### mechanical/ - Enclosures

| Path | Purpose |
|:---|:---|
| `enclosure_gen.scad`, `led_enclosure.scad` | Sensor node and LED driver enclosures (OpenSCAD) |
| `fit_check.py` | Generate board positions from KiCad, check the fit, render, export print files |
| `print/` | Print-ready STL files |

### simulation/ - LTspice

| Path | Purpose |
|:---|:---|
| `*.cir` | LED channel, PWM dimming, CTRL fail-safe, battery sense, reversed cell |
| `README.md`, `plots/` | Results and plots |

### firmware/ - Legacy rev 2 research firmware (does not build for current hardware; see `firmware/README.md`)

| File | Purpose |
|:---|:---|
| `src/main.c` | Main firmware (Zephyr RTOS + CoAP) |
| `prj.conf` | Zephyr config (SED mode, sensors) |
| `CMakeLists.txt` | Build system |
| `boards/nrf52840_phytotron.overlay` | Device tree (I2C, PWM, ADC) |
| `drivers/led_control.c` | PWM LED driver |
| `include/*.h` | Header files (7 files) |

### dashboard/ - Web GUI

| File | Purpose |
|:---|:---|
| `index.html` | Main UI |
| `css/style.css` | Styling |
| `js/dashboard.js` | Data fetching, node display |
| `js/llm_assistant.js` | LLM chat for event annotation |

### monitoring/ - Observability

| File | Purpose |
|:---|:---|
| `grafana/provisioning/datasources/timescaledb.yml` | Grafana → DB connection |
| `mosquitto/config/mosquitto.conf` | MQTT broker config |

### documentation/ - Hardware Guides

| File | Purpose |
|:---|:---|
| `raspberry_pi_setup.md` | OTBR installation |
| `nrf52840_pinout.md` | Pin map and assembly guide (rev 3.1) |
| `hardware_specs.md` | Board and LED board summary (rev 3.1) |
| `design_review.md` | Electrical, firmware and mechanical review with the evidence for each finding |
| `archive/` | Rev 2 hardware documents, kept for reference |
| `bench_testing.md` | Validation procedures |
| `bring_up.md` | First power-on of a rev 3.1 sensor node, step by step |
| `ordering.md` | Ordering both boards assembled from JLCPCB: settings, part stock, items bought separately |
| `hardware_protocol.md` | Communication protocol |
| `requirements.md` | ELEC 490/498 checklist |

---

## 📡 API Endpoints

### Phenotyping

| Method | Endpoint | Description |
|:---|:---|:---|
| POST | `/api/phenotype` | Calculate VPD, transpiration, stress from sensor data |
| GET | `/api/phenotype/summary` | Greenhouse-wide summary (last hour) |

### Data Input (Group 2 GUI)

| Method | Endpoint | Description |
|:---|:---|:---|
| POST | `/api/event` | Log research event (pest, fertilizer, equipment) |
| POST | `/api/yield` | Log harvest yield data |
| POST | `/api/led` | Update LED schedule |

### Data Output

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/api/nodes` | Get all node status |
| GET | `/api/events` | Get recent events |
| GET | `/api/curated` | Download ML-ready dataset (CSV) |

### Health

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/health` | Service health check |

---

## 🔧 Hardware Integration

### For Real Hardware Deployment

1. **Order the boards and parts:** [`documentation/ordering.md`](documentation/ordering.md).
2. **Border router:** [`documentation/raspberry_pi_setup.md`](documentation/raspberry_pi_setup.md)
   (OTBR + nRF52840 Dongle, network settings matching the node firmware).
3. **Provision, build and flash each node** (from the repo root, with a Zephyr workspace):
   ```bash
   python gateway/tools/provision_node.py --index 1 --network-key <32 hex digits>
   west build -b raytac_mdbt50q_db_40/nrf52840 pcbs/gos_sensor_node/firmware
   west flash
   ```
4. **Start the receiver** on the Pi: `docker compose --profile hardware up -d coap_receiver`.
5. **Bring-up and checks:** [`documentation/bring_up.md`](documentation/bring_up.md) (power, charger,
   sensors, Thread, database, LED board, sleep current, enclosures).
6. **Switch off the simulator:** comment out the `ingest` service in `docker-compose.yml`.

---

## Requirements, Implementation, and Status

| Requirement | Implementation | Status |
|:---|:---|:---:|
| Data backbone pipeline | `sync.py` - 5-source joins | ✅ |
| PostgreSQL database | TimescaleDB hypertables | ✅ |
| Docker orchestration | 12-service compose | ✅ |
| 40 wireless nodes | Thread mesh; sensor node rev 3.1 designed, ready to order, not yet built | in progress |
| Preserved sample identity | EUI64 in all tables | ✅ |
| Group 2 GUI | Dashboard + LLM | ✅ |
| ML-ready datasets | `/api/curated` | ✅ |
| Phenotyping | VPD, transpiration | ✅ |
| RL model (stretch) | `agent_rl.py` | ✅ |

---


