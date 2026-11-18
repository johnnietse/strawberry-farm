# G.O.S. - Greenhouse Operating System

**Wireless climate sensing and LED spectrum control for research strawberries in a phytotron.**

Sensor nodes measure temperature, humidity and light at the plants and send signed readings over
a Thread radio network to a Raspberry Pi. On the Pi, a strawberry canopy model works out what
the plants are doing, a trained controller picks a blue/red LED mix for each grow light, and the
answer goes back to each node, signed, in the reply to its next reading. Researchers watch and
annotate everything in a web dashboard; the data ends up in one ML-ready dataset.

**Status (2026-11-15):** both circuit boards are designed, simulated and ready to order; the
firmware builds; all software is tested end to end against a simulated node. Nothing has run on
real boards or plants yet. What is and is not verified: [Verification](#verification).
Review of how the parts fit together, and what to change next:
[`documentation/system_review.md`](documentation/system_review.md).

- [How it works](#how-it-works)
- [Hardware](#hardware)
- [Software and models](#software-and-models)
- [Run it](#run-it)
- [Dashboard, API, network](#dashboard-api-network)
- [Verification](#verification)
- [Repository map](#repository-map)

---

## How it works

```mermaid
graph LR
    subgraph Light["Light node (USB powered, Thread router)"]
        S1[SHT40 + TSL2591] --> M1[nRF52840<br/>Zephyr + OpenThread]
    end
    subgraph Climate["Climate node (battery, sleepy)"]
        S2[SHT40 + TSL2591] --> M2[nRF52840]
    end
    M1 -- "4-wire cable, 2 x PWM" --> L[LED driver board<br/>24 V, blue + red]
    M2 -. "Thread" .-> M1
    M1 -- "Thread: signed reading every 60 s" --> R[Raspberry Pi<br/>border router + Docker]
    M2 -. "Thread" .-> R
    R --> DB[(TimescaleDB)]
    DB --> BIO[biology engine<br/>canopy model + forecast]
    BIO --> CTL[LED controller<br/>PPO policy]
    CTL --> SP[setpoints]
    UI[dashboard] --> SP
    SP --> SAFE[safety monitor]
    SAFE -- "signed LED command in the reply" --> M1
```

*Figure 1. System overview. Each sensor node measures temperature, humidity and light and sends a signed reading over Thread to the Raspberry Pi. On the Pi the reading is stored, the biology engine works out the plant state, the LED controller turns it into an LED setpoint, and the safety monitor checks it before the signed LED command goes back to the light node, which drives its LED driver board over a 4-wire cable. Climate nodes only measure; their packets can reach the Pi through a light node.*

Two kinds of sensor node, same board, different firmware build:

*Table 1. The two node roles. Both use the same board; the firmware build decides whether a node is a USB-powered Thread router that drives an LED board, or a battery-powered sleepy device that only measures.*

| Node | Power | Thread role | Job |
|---|---|---|---|
| **Light node** | 5 V USB-C adapter | router: radio always on, relays for others | measures, and drives one LED driver board |
| **Climate node** | 18650 cell (months) | sleepy end device: wakes once a minute | measures only |

```mermaid
sequenceDiagram
    participant N as Node
    participant R as coap_receiver (Pi)
    participant DB as TimescaleDB
    participant B as biology engine
    participant C as LED controller
    loop every 60 s
        N->>R: CoAP POST, reading (HMAC-signed, counter)
        R->>R: check signature, EUI-64, counter
        R->>DB: store reading, read the node's LED setpoint
        R->>R: safety monitor: dark period, over 32 C, ramp limit
        R-->>N: 2.04 + LED command (signed, bound to this reading)
        N->>N: check tag and counter, set the PWM
    end
    loop every 60 s
        B->>DB: plant state: photosynthesis, transpiration, light integral, 2 h forecast
    end
    loop every 5 min
        C->>DB: LED setpoint per node (unless set by hand)
    end
```

*Figure 2. One control cycle. Every 60 s the node posts a signed reading; the receiver checks the signature, the node's identity and the counter, applies the safety rules to the node's LED setpoint and returns the LED command in the same CoAP reply, bound to that reading so it cannot be replayed. The biology engine (every 60 s) and the LED controller (every 5 min) update the plant state and the setpoints on their own schedules.*

If a node hears nothing for 15 minutes it switches its LEDs off; if the cable is unplugged the
LED board's pull-downs keep the LEDs off.

---

## Hardware

*Table 2. The hardware: what each piece contains and where its documentation is.*

| Piece | What it is | Docs |
|---|---|---|
| **Sensor node** rev 3.1, 40 x 65 mm, 4 layers | Raytac MDBT50Q (nRF52840) module; SHT40 temperature and humidity; TSL2591 light; 18650 cell with BQ24074 USB-C charger, DW01A/FS8205A protection, reverse-cell FET; TPS62740 3.3 V buck; 4-pin LED cable connector | [`pcbs/gos_sensor_node/HARDWARE.md`](pcbs/gos_sensor_node/HARDWARE.md) |
| **LED driver** rev 1.0, 60 x 45 mm, 4 layers | two AL8860 constant-current channels, 333 mA, 24 V input; blue 448 nm and red 655 nm strings of 4 LEDs; off when the control cable is unplugged | [`pcbs/led_driver/README.md`](pcbs/led_driver/README.md) |
| **Border router** | Raspberry Pi + Nordic nRF52840 Dongle (OpenThread border router); runs all the software in Docker | [`documentation/raspberry_pi_setup.md`](documentation/raspberry_pi_setup.md) |
| **Enclosures** | printed in ASA, generated from the KiCad boards and fit-checked | [`mechanical/README.md`](mechanical/README.md) |

| Sensor node | LED driver |
|---|---|
| ![Sensor node, top](pcbs/gos_sensor_node/docs/gos_sensor_node_render_top.png) | ![LED driver, top](pcbs/led_driver/docs/led_driver_render_top.png) |
| ![Sensor node top copper](docs/images/gos_sensor_node_top_copper.svg) | ![LED driver top copper](docs/images/led_driver_top_copper.svg) |
| ![Sensor node enclosure](docs/images/sensor_enclosure_exploded.png) | ![LED driver enclosure](docs/images/led_enclosure_exploded.png) |

*Figure 3. The two boards, sensor node on the left and LED driver on the right. Row 1: 3D render of the assembled top side. Row 2: top copper layer. Row 3: the board in its printed enclosure with the lid raised.*

**Engineering drawings** of both enclosures (third-angle orthographic views with dimensions,
exploded isometric view with balloons, parts list, title block; generated by
[`mechanical/make_drawings.py`](mechanical/make_drawings.py)):

![Sensor node enclosure drawing](docs/images/drawings/sensor_node_enclosure_drawing.png)

*Figure 4. Engineering drawing GOS-MECH-001, sensor node enclosure: top, front and right-side views with overall dimensions (85.0 x 130.0 x 48.0 mm; USB-C cut-out in the front wall, gland hole and vents in the right wall), exploded view with numbered balloons, parts list and title block.*

![LED driver enclosure drawing](docs/images/drawings/led_driver_enclosure_drawing.png)

*Figure 5. Engineering drawing GOS-MECH-002, LED driver enclosure: 65.6 x 82.0 x 35.6 mm including the mounting flanges, control-cable slot and vents in the front wall, the two LED-plug openings in the right wall, exploded view, parts list and title block.*

**System assembly drawing** (GOS-MECH-003, two sheets): how the printed parts go together once
the boards and enclosures arrive. Sheet 1 shows the light node and the LED driver it drives at
the same true scale (1:2 when printed on A3), with one exploded view of both units, the control
cable between them and a combined parts list; its notes explain how to get the cable's plug
through the cable gland. Sheet 2 shows the installation in the growth chamber, every cable
(W1 to W7) in an interconnect list, the assembly sequence and the radio placement.

![System assembly, sheet 1](docs/images/drawings/system_assembly_sheet1.png)

*Figure 6. System assembly drawing GOS-MECH-003, sheet 1: the light node and the LED driver at the same scale (1:2 on A3), one exploded view of both with the control cable (item 8), a combined parts list, and notes on routing the cable through the gland and the slot.*

![System assembly, sheet 2](docs/images/drawings/system_assembly_sheet2.png)

*Figure 7. GOS-MECH-003, sheet 2: installation in the growth chamber (LED driver on the fixture frame, light node and climate nodes at canopy height, gateway outside), interconnect list W1 to W7 and R1, assembly sequence, and where to put the Thread Dongle.*

The **Raspberry Pi and the nRF52840 Dongle** are bought boards, so they get no printed
enclosure: the Pi goes in the official case for its model, and the Dongle sits outside it on a
short USB extension in a USB 2.0 port. USB 3.0 ports radiate noise in the 2.4 GHz band, and a
closed case or a metal chamber wall would shield the Dongle's antenna.

<details>
<summary>Schematics</summary>

Sensor node: [top level](docs/images/schematics/gos_sensor_node.svg) ·
[power](docs/images/schematics/gos_sensor_node-Power.svg) ·
[MCU](docs/images/schematics/gos_sensor_node-MCU.svg) ·
[sensors](docs/images/schematics/gos_sensor_node-Sensors.svg) ·
[connectors](docs/images/schematics/gos_sensor_node-Connectors.svg) ·
LED driver: [schematic](docs/images/schematics/led_driver.svg)

![Sensor node power](docs/images/schematics/gos_sensor_node-Power.svg)

*Figure 8. Sensor node schematic, power sheet: the path from the USB-C input and the 18650 cell to the 3.3 V rail (charger with power path, cell protection, reverse-cell protection, buck converter).*

![LED driver](docs/images/schematics/led_driver.svg)

*Figure 9. LED driver schematic: 24 V input, two AL8860 constant-current channels (blue and red, 333 mA each), their PWM inputs from the 4-wire cable with pull-downs that keep the LEDs off when it is unplugged, and the LED-string connectors.*

</details>

**Firmware** (Zephyr, [`pcbs/gos_sensor_node/firmware`](pcbs/gos_sensor_node/firmware)):

*Table 3. Sensor node firmware builds: which build for which node, what to add to the build command, and the flash and RAM it uses (the nRF52840 has 1 MB and 256 KB).*

| Build | For | `west build -b raytac_mdbt50q_db_40/nrf52840 pcbs/gos_sensor_node/firmware ...` | Flash / RAM |
|---|---|---|---|
| bench | first power-on, with logging | (nothing more) | 214.6 / 62.4 KB |
| climate node | battery, in the phytotron | `-- -DEXTRA_CONF_FILE=low_power.conf` | 197.3 / 60.1 KB |
| climate node, locked | same, debugger blocked so keys cannot be read | `-- -DEXTRA_CONF_FILE="low_power.conf;lock.conf"` | 197.3 / 60.1 KB |
| light node | USB powered, Thread router | `-- -DEXTRA_CONF_FILE=router.conf` | 261.6 / 70.6 KB |

**Order and build:** [`documentation/ordering.md`](documentation/ordering.md) (JLCPCB settings,
every part with its stock, what to buy separately), then
[`documentation/bring_up.md`](documentation/bring_up.md) (first power-on, step by step).

**Known limits of this revision** (details and proposals in `system_review.md`): one LED board
adds about 120 umol m-2 s-1 over 0.25 m2, a spectral treatment rather than a main grow light; the
TSL2591 measures lux, so daylight PAR is estimated; the charger warms the SHT40 while charging
(those readings are flagged).

---

## Software and models

All on the Raspberry Pi, in Docker Compose:

*Table 4. The Docker Compose services on the Raspberry Pi, what each does and where its code is.*

| Service | What it does | Code |
|---|---|---|
| `db` | TimescaleDB: readings, plant state, LED setpoints and commands, events, harvests | [`gateway/schema.sql`](gateway/schema.sql) |
| `coap_receiver` (profile `hardware`) | receives node readings over Thread, checks signatures and counters, stores them, replies with each node's signed LED command after the safety monitor | [`gateway/services/coap_receiver.py`](gateway/services/coap_receiver.py), [`led_safety.py`](gateway/services/led_safety.py) |
| `biology_engine` | canopy model on live data each minute, daily light integral, 2 h climate forecast | [`ml_engine/biology_engine.py`](ml_engine/biology_engine.py) |
| `ml_engine` | LED controller: PPO policy picks blue and red levels per node every 5 min | [`ml_engine/controller.py`](ml_engine/controller.py) |
| `sync_engine` | joins readings, LED commands, plant state, met data, events and harvests into one ML-ready CSV | [`gateway/services/sync.py`](gateway/services/sync.py) |
| `api` | REST API | [`gateway/services/api.py`](gateway/services/api.py) |
| `dashboard` | web dashboard on port 8080; also forwards `/api/` to the API | [`dashboard/`](dashboard) |
| `grafana` | time-series dashboard (temperature, humidity, VPD, photosynthesis, transpiration, light integral, LED levels, battery) on port 3000 | [`monitoring/`](monitoring) |
| `ollama` (profile `assistant`) | local language model for the research assistant, offline | [`gateway/services/assistant.py`](gateway/services/assistant.py) |
| `ingest`, `met_station` (profile `sim`) | simulated 40 nodes and met station, for a demo on a PC without hardware | `gateway/services/farm_sim.py`, `met_station.py` |
| `mqtt`, `mqtt_bridge` | MQTT input for other instruments (local only by default) | `gateway/services/mqtt_bridge.py` |

*Table 5. The models: the job each does, where its weights are, and the result of its check.*

| Job | Model | Weights | Result |
|---|---|---|---|
| What the plants are doing | strawberry canopy model: Farquhar photosynthesis, Medlyn stomata, Penman-Monteith transpiration | code | light-saturated photosynthesis 15.9 umol m-2 s-1, inside the 15 to 20 reported for strawberry |
| LED levels | PPO reinforcement-learning policy, trained in the canopy model, numpy on the Pi | [`ml_engine/models/led_policy.npz`](ml_engine/models) | within 0.5 % of a model-based optimiser on 60 held-out days |
| 2 h climate forecast | Chronos-Bolt Tiny (Amazon, Hugging Face), offline | [`ml_engine/models/hf/`](ml_engine/models/hf) | VPD error at 6 h 0.118 kPa, half of "no change" (0.245), on a year of measured weather |
| Notes to research events | Qwen2.5-1.5B-Instruct via Ollama, offline; Claude if a key is set; keyword rules otherwise | [GitHub release](https://github.com/johnnietse/strawberry-farm/releases/tag/models-2026-11-15) | 6 of 6 test notes filed correctly |

Model card with versions, licenses and checksums: [`ml_engine/models/README.md`](ml_engine/models/README.md).
Details and how to retrain: [`ml_engine/README.md`](ml_engine/README.md).

| Plant model | LED policy over one held-out day |
|---|---|
| ![Plant model](docs/images/ml/plant_response.png) | ![LED policy day](docs/images/ml/led_policy_day.png) |
| ![Forecast error](docs/images/ml/forecast_error.png) | ![Policy comparison](docs/images/ml/policy_comparison.png) |

*Figure 10. Model checks. Top left: leaf photosynthesis against light at 15, 25 and 32 C, and against temperature; it saturates at 15.9 umol m-2 s-1, inside the 15 to 20 reported for strawberry, with an optimum at 28 C. Top right: one held-out day, daylight plus LED light at the canopy, and the LED levels the PPO policy chose (full through the photoperiod, off in the dark period). Bottom left: VPD forecast error against lead time over a year of measured weather; Chronos-Bolt Tiny has the lowest error, half that of "no change" at 6 h. Bottom right: daily reward of five LED strategies on 60 held-out days; PPO matches the model-based optimiser and beats fixed or no LED light.*

---

## Run it

**On a PC, without hardware** (simulated nodes):

```bash
git clone https://github.com/johnnietse/strawberry-farm.git
cd strawberry-farm
cp .env.example .env              # set POSTGRES_PASSWORD, GF_SECURITY_ADMIN_PASSWORD, GOS_API_TOKEN
                                  # (required: there are no default passwords; .env is never committed)
python -c "import secrets; print(secrets.token_hex(24))"     # a token for GOS_API_TOKEN
docker compose --profile sim up -d --build
```

Open http://localhost:8080, click **Access** at the top right and paste the token once.

**On the Raspberry Pi, with real nodes:** border router setup, then

```bash
docker compose --profile hardware --profile assistant up -d --build
OLLAMA="docker compose exec -T ollama ollama" bash ml_engine/models/fetch_models.sh
python gateway/tools/provision_node.py --index 1 --network-key <32 hex digits>   # per node
```

and flash each node with the build for its role (table above). Full guide:
[`documentation/raspberry_pi_setup.md`](documentation/raspberry_pi_setup.md), first power-on:
[`documentation/bring_up.md`](documentation/bring_up.md).

**Tests:**

```bash
cd gateway && python -m pytest tests && cd ..        # receiver, LED commands, safety, API, assistant
cd ml_engine && python -m pytest tests && cd ..      # canopy model, policy, controller
bash tests/e2e/run_e2e.sh                            # the whole loop in Docker, simulated node
```

---

## Dashboard, API, network

![Dashboard](docs/images/dashboard.png)

*Figure 11. The research dashboard during a run with the simulator. Top: latest reading per node. Middle: plant state from the biology engine and the LED level each node is set to. Bottom: set the LEDs by hand, log an event in plain words, and the LED commands actually sent after the safety monitor ("Asked" is the setpoint before it).*

The dashboard shows each node, the plant state and forecast, the LED level each node was sent
(with any safety note) and recent events; it sets LEDs by hand (timed, or until switched back)
and turns free-text notes into research events.

*Table 6. API endpoints. Reading is open; every POST and DELETE needs the API token.*

| Method | Endpoint | |
|---|---|---|
| GET | `/api/nodes`, `/api/plant`, `/api/led/commands`, `/api/events`, `/api/curated` | node readings, plant state with LED setpoint and forecast, LED commands sent, events, the ML dataset (CSV) |
| GET | `/api/phenotype/summary`, `/health` | last-hour summary, health |
| POST | `/api/led` | set LEDs by hand: `{"node": "RF-NODE-01" or "ALL", "blue_pct", "red_pct", "minutes"}` (`0` = until switched back) |
| DELETE | `/api/led/override` | back to automatic (`?node=` for one node) |
| POST | `/api/event`, `/api/yield`, `/api/assistant`, `/api/phenotype` | log an event or harvest; note to event; VPD and stress for given values |

Reading needs nothing; every change needs `Authorization: Bearer <GOS_API_TOKEN>` (from `.env`;
without it the API is read-only). The dashboard and the API share port 8080, so the system works
at whatever address the Pi has, on any network. The database, MQTT and port 5000 are reachable
from the Pi only. Other networks, other web sites, another server, HTTPS:
[`documentation/network_and_access.md`](documentation/network_and_access.md).

### Grafana

Grafana (port 3000, `monitoring/grafana/provisioning/dashboards/gos_phytotron.json`) is the
time-series view: ten panels per node, read straight from TimescaleDB. The screenshots below
are from the end-to-end test, for its test node `RF-NODE-07`, at the last hour.

![Grafana: air temperature, humidity, VPD, canopy photosynthesis](docs/images/grafana/grafana_climate_biology.png)

*Figure 12. Grafana, test node RF-NODE-07, last hour: air temperature and relative humidity measured by the SHT40, VPD and canopy photosynthesis computed by the biology engine.*

**Air temperature and relative humidity**: the node's SHT40 readings. The test seeds 24 h of
history as a daily sine wave (temperature falling and humidity rising through this hour); the
last point, the jump to 22.3 C, is the first packet from the simulated node, signed and checked
like a real one. **VPD** (vapour pressure deficit) and **canopy photosynthesis** come from the
biology engine's canopy model (Farquhar-von Caemmerer-Berry with Medlyn stomata): about 0.85
kPa, comfortable for strawberries, and about 5 umol m-2 s-1 of net CO2 uptake at this light.

![Grafana: transpiration and daily light integral](docs/images/grafana/grafana_transpiration_dli.png)

*Figure 13. Grafana: transpiration and daily light integral, computed by the biology engine.*

**Transpiration** (Penman-Monteith, about 45 g of water per m2 per hour) tells how fast the
plants use water. **Daily light integral** is the light summed since midnight; it is still
tiny here because the test started its light record minutes before the screenshot.

![Grafana: LED levels sent, battery, light at the node](docs/images/grafana/grafana_led_battery_light.png)

*Figure 14. Grafana: LED duty cycles sent to the node after the safety monitor, battery voltage and light at the node.*

**LED level sent, blue and red**: the duty cycle in the signed command the node received in its
reply, after the safety monitor (about 63 % blue and 78 % red here, set by the LED
controller). **Battery** and **light at the node** are flat because the test history uses a fixed
3,900 mV and 8,000 lux. The model panels and the LED panels show one point each: the biology
engine and the LED controller had run one cycle when the screenshot was taken; with the system
running they fill in every cycle, like the temperature panel.

---

## Verification

*Table 7. Verification so far. Each line was checked by a design tool, a simulation or a test; nothing has run on real boards yet.*

| Check | Result |
|---|---|
| KiCad DRC at every severity, with schematic parity | both boards: 0 violations, 0 unrouted |
| Layout review (USB pair, buck switching loop, antenna strip, LED switching loops) | measured; loops routed by hand ([`design_review.md`](documentation/design_review.md)) |
| LTspice: LED current and frequency, PWM dimming, CTRL fail-safe, battery sense, reversed cell | all pass after two fixes ([`simulation/README.md`](simulation/README.md)) |
| Datasheet checks: crystal load (nRF52840 LFXO table and Nordic's reference circuit), TSL2591 decoupling, FS8205A pinout | match ([`HARDWARE.md`](pcbs/gos_sensor_node/HARDWARE.md#not-verified)) |
| LTspice: crystal oscillator loop (frequency error, required gain, drive level) | +0.3 ppm at the design stray, at most 38 ppm over 0 to 4 pF |
| Firmware: four builds, devicetree with `dtc` | no warnings from the project's code |
| Firmware LED-command check against commands made by the gateway (PC) | passes |
| Gateway tests | 81 pass |
| ML engine tests | 13 pass |
| End to end in Docker with the production images (torch, Chronos, Qwen): signed commands verified by the node, plant state and forecast, dashboard proxy, token refusals, manual override, assistant, ML dataset columns, Grafana | 17 of 17 checks pass |
| Enclosure fit | 12 checks pass |

| LED channel at 24 V (LTspice) | PWM dimming 50 % (LTspice) |
|---|---|
| ![LED channel](simulation/plots/led_channel_24V.png) | ![PWM dimming](simulation/plots/led_pwm_50pct.png) |

*Figure 15. LTspice, LED driver. Left: current in one AL8860 channel at 24 V for the blue and red strings, switching at about 0.55 MHz with 104 mA ripple around the 333 mA target. Right: 50 % PWM dimming at 250 Hz; the LED current follows the CTRL signal and averages 168 mA, exactly half of full.*

![Crystal oscillator loop (LTspice)](simulation/plots/crystal_lfxo.png)

*Figure 16. LTspice, sensor node 32.768 kHz crystal. Left: frequency error against board stray capacitance, +0.3 to +0.9 ppm at the 2 pF design value and at most 38 ppm over 0 to 4 pF, far inside the +/-500 ppm the radio needs. Middle: the loop's transimpedance peaks at 32 768.010 Hz, where it oscillates; this needs an oscillator gain of at least 1.24 uA/V. Right: the power dissipated in the crystal stays under its 0.5 uW limit up to 2 V peak to peak.*

**Not verified yet (needs hardware):** sleep current and battery life, Thread range, charging,
the LED current and light output, the plant-model parameters for your cultivar, the forecast on
phytotron air. Every issue found so far and its status:
[`documentation/issues_log.md`](documentation/issues_log.md).

---

## Repository map

*Table 8. Repository map: the top-level folders and what is in them.*

| Path | What |
|---|---|
| [`pcbs/gos_sensor_node/`](pcbs/gos_sensor_node) | sensor node: generators for schematic and board, routing, layout review, order files (`fab/`), drawings and renders (`docs/`), firmware |
| [`pcbs/led_driver/`](pcbs/led_driver) | LED driver board, same structure |
| [`mechanical/`](mechanical) | enclosures (OpenSCAD), fit check, engineering drawings, print files |
| [`simulation/`](simulation) | LTspice netlists, results, plots |
| [`gateway/`](gateway) | database schema, receiver, safety monitor, API, assistant, curation, simulators, node provisioning, tests |
| [`ml_engine/`](ml_engine) | canopy model, biology engine, lighting task, PPO training and policy, controller, forecasters, models, tests |
| [`dashboard/`](dashboard) | web dashboard and its nginx configuration |
| [`monitoring/`](monitoring) | Grafana datasource and dashboard, MQTT broker configuration |
| [`tests/e2e/`](tests/e2e) | end-to-end test |
| [`documentation/`](documentation) | guides and reviews (below) |
| `firmware/` | legacy rev 2 firmware, kept for reference; does not build for the current board |

*Table 9. The main documents and what each covers.*

| Document | |
|---|---|
| [`system_review.md`](documentation/system_review.md) | how the parts fit together, deployment plan, proposals for revision 3.2 |
| [`design_review.md`](documentation/design_review.md) | electrical, firmware and mechanical review with evidence |
| [`issues_log.md`](documentation/issues_log.md) | every issue found, its effect and status |
| [`ordering.md`](documentation/ordering.md) | ordering both boards from JLCPCB, part stock, items bought separately |
| [`bring_up.md`](documentation/bring_up.md) | first power-on and bench tests |
| [`raspberry_pi_setup.md`](documentation/raspberry_pi_setup.md) | border router and the software stack |
| [`network_and_access.md`](documentation/network_and_access.md) | ports, token, other networks, sites and servers |
| [`hardware_protocol.md`](documentation/hardware_protocol.md) | reading packet and LED command formats |
| [`hardware_specs.md`](documentation/hardware_specs.md), [`nrf52840_pinout.md`](documentation/nrf52840_pinout.md) | board summary and pin map |
| [`requirements.md`](documentation/requirements.md) | course requirements checklist |

*Table 10. Course requirements: where the project meets each one, and its status.*

| Requirement | Where | Status |
|---|---|---|
| Wireless sensor network | sensor node rev 3.1, Thread mesh with router nodes | designed and simulated; not built |
| Database and data backbone | TimescaleDB, `sync.py` (readings, LED commands, plant state, met, events, harvests) | tested |
| Preserved sample identity | EUI-64 in every reading; per-node keys | tested |
| GUI with event annotation | dashboard, research assistant | tested |
| ML-ready dataset | `/api/curated` | tested |
| Phenotyping | canopy model: photosynthesis, transpiration, VPD, light integral | tested in simulation; not calibrated on plants |
| RL model for LED control (stretch) | PPO controller, closed loop to the LEDs | simulation and end-to-end test; not on plants |
