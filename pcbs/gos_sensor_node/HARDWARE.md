# G.O.S. sensor node rev 3.2 hardware reference

This replaces the hardware sections of `PROJECT_CONTEXT.md` and all of `WIRING_GUIDE.md`.
Both describe rev 2 and contain pin tables that contradict the datasheets.

The schematic is generated. Edit `generate_schematics.py`, then run:

```
"C:\Program Files\KiCad\9.0\bin\python.exe" generate_schematics.py --verify
```

`--verify` regenerates the sheets and fails unless all three hold:

1. Every symbol pin number exists as a pad in the assigned footprint.
2. The netlist KiCad exports equals the nets declared in the script, pin for pin.
3. KiCad ERC reports zero violations at every severity.

## What changed from rev 3.1 (rev 3.2, 2026-11-22)

The rev 3.1 board is kept in `pcbs/archive/gos_sensor_node_rev3.1/`. Full before/after comparison
with the test results: [`documentation/rev3.2_changes.md`](../../documentation/rev3.2_changes.md).

*Table 1. What changed from rev 3.1 to rev 3.2, and why.*

| Area | Rev 3.1 | Rev 3.2 | Why |
|---|---|---|---|
| Light measurement | TSL2591 only (lux) | plus J6, an input for a self-powered quantum (PAR) sensor, e.g. Apogee SQ-500-SS (0.01 mV per umol m-2 s-1), through R24 1k + C15 100 nF to AIN1 (P0.03) | lux is a poor measure of photosynthetic light under narrow-band red and blue LEDs |
| SHT40 | on the board edge, surrounded by ground pour and both planes | on a tongue cut free by two notches from the edge and a slot (1.0 mm), no pour, planes or vias on it; four 0.127 mm tracks cross a 2.2 mm FR-4 bridge | charging (0.64 W in the BQ24074) warmed the sensor; 2-D thermal estimate: 11.7 K -> 8.2 K above the air (30 % less) |
| I2C pull-ups R13-R15 | beside the SHT40 | beside J6 | off the tongue |
| J3 (I2C header) | y 31.0 mm | y 32.5 mm | clear of the lower notch |
| Firmware packet | PACKET_V4, 43 bytes | PACKET_V5, 45 bytes, PAR after light | carries the PAR reading; the gateway still accepts V4 and V3 |
| Enclosure | one M12 gland (LED cable, right wall) | plus an M12 gland in the left wall for the PAR cable | the sensor sits outside at canopy height |

## What changed from rev 2

*Table 2. What changed from rev 2 to rev 3, and why.*

| Area | Rev 2 | Rev 3 | Why |
|---|---|---|---|
| MCU | bare nRF52840-QIAA | Raytac MDBT50Q-1MV2 module | no RF layout, crystal and DC/DC inductor inside the module |
| LoRa, GNSS | SX1262, L76K | removed | dropped from scope |
| LED drivers | 2 x AL8860 on board | PWM-only header J4 to a separately powered board | AL8860 needs at least 4.5 V; this board's VSYS is 3.0 to 4.4 V |
| Charger | BQ24075 | BQ24074 | BQ24075 holds OUT at 5.5 V on USB, the TPS62740 input limit. BQ24074 holds 4.4 V. Same footprint. |
| Buck pin map | 9 pins, 2 VSEL, both low | 12 pins, 4 VSEL, all high | rev 2 table did not match the part. All four low gives 1.8 V, not 3.3 V. |
| Cell protection | both FETs on one gate net | OD to FET 1, OC to FET 2, DW01A GND to cell negative | rev 2 wiring could not switch charge and discharge separately |
| Reverse cell | none | Q2 P-FET in the positive lead | a battery lead can be wired or plugged backwards |
| Battery | JST-PH connector, cell in the enclosure | same: 2-pin JST-PH J5 | rev 3.0 briefly put a Keystone 1042 holder on the board; its pads span 79 mm and the board is 40 x 65 mm |
| Battery sense | 1M / 1M | 2.2M / 2.2M + 100 nF | halves the standing drain |
| Sheets | 8 | 5 (root, power, MCU, sensors, connectors) | protection merged into power |

## Power tree

*Table 3. Power tree: each supply net, its source, voltage and loads.*

| Net | Source | Voltage | Loads |
|---|---|---|---|
| `VBUS_CONN` | USB-C J1 | 5 V | F1 only |
| `VBUS` | F1 (0.75 A PTC) | 5 V | BQ24074 IN, module VBUS pin, USB ESD clamp |
| `VSYS` | BQ24074 OUT | 4.4 V on USB, cell voltage on battery | TPS62740 only |
| `VBAT` | BQ24074 BAT | 3.0 to 4.2 V | cell through Q2 and J5, DW01A supply, sense divider |
| `+3V3` | TPS62740 + L1 | 3.3 V, follows VSYS down once VSYS is below about 3.5 V | module, sensors, pull-ups, J2, J3 |
| `BAT_N` | cell negative | below GND by the FET drop | DW01A, FS8205A source 1 |

`BAT_N` is not `GND`. The FS8205A sits between them and opens on a fault.

## Charger settings (BQ24074)

*Table 4. BQ24074 charger pin settings: what each connection sets, and the datasheet rule it follows.*

| Pin | Connection | Result | Datasheet rule |
|---|---|---|---|
| EN2 | GND | USB500 mode, 500 mA input limit | table 7-2 |
| EN1 | `VBUS` through 100k | high only while USB is present | VIH 1.4 V; pin has a 285k pull-down |
| ISET | 1.8k to GND | 494 mA fast charge | I = 890 / R, R from 590 ohm to 8.9k |
| ILIM | 3.0k to GND | 508 mA, used only if EN2 = 1 | must be fitted or charging is disabled |
| TMR | 68k to GND | 9.1 h charge timer, 54 min precharge | 10 x R x 48 s/k, R from 18k to 72k |
| ITERM | open | terminate at 10 % of charge current | default |
| TS | 10k NTC (TH1) to GND | charge only between about 0 and 50 C | fit a fixed 10k if no NTC |
| CE | GND | charging enabled | active low |
| PGOOD, CHG | 100k pull-ups to `+3V3` | read by the MCU; D1 lights while charging | open drain |

The three resistor values are constants at the top of `generate_schematics.py`.

## Cell protection (DW01A + FS8205A)

*Table 5. Cell protection thresholds (DW01A controller with FS8205A switches).*

| Event | Threshold |
|---|---|
| Overcharge | 4.30 V +/- 0.05 V, release 4.10 V |
| Overdischarge | 2.40 V +/- 0.10 V, release 3.00 V |
| Overcurrent | 150 mV across both FETs. At 25 to 35 mohm each that is about 2.1 to 3 A. |

After a cell is fitted the DW01A may stay off until USB is plugged in once.

## Module pin map (MDBT50Q-1MV2)

*Table 6. Module pin map: each net, its nRF52840 pin, its module pin and where it goes.*

| Net | nRF pin | Module pin | Goes to |
|---|---|---|---|
| `I2C_SDA` | P0.26 | 19 | SHT40, TSL2591, J3, 4.7k pull-up |
| `I2C_SCL` | P0.27 | 16 | same |
| `TSL_INT` | P0.15 | 39 | TSL2591 INT, 100k pull-up |
| `PWM_BLUE` | P0.13 | 37 | J4 pin 2 through 100R |
| `PWM_RED` | P0.14 | 36 | J4 pin 3 through 100R |
| `UART_TX` | P0.06 | 22 | TP5 |
| `UART_RX` | P0.08 | 24 | TP6 |
| `VBAT_SENSE` | P0.02 / AIN0 | 11 | VBAT / 2 |
| `PAR_SENSE` | P0.03 / AIN1 | 9 | rev 3.2: J6 pin 2 through R24 (1k), C15 (100 nF) to GND |
| `PGOOD_N` | P0.28 | 13 | low when USB power is good |
| `CHG_N` | P0.29 | 10 | low while charging |
| `LED_STAT_N` | P0.17 | 41 | status LED D2, low = on |
| `BTN_USER` | P0.24 | 48 | SW2 to GND, needs the internal pull-up |
| `NRESET` | P0.18 | 40 | SW1, J2 |
| `SWDIO`, `SWDCLK`, `SWO` | SWDIO, SWDCLK, P1.00 | 51, 53, 47 | J2 |
| `USB_DP`, `USB_DN` | D+, D- | 35, 34 | J1 through 27R and the ESD clamp |
| `XL1`, `XL2` | P0.00, P0.01 | 17, 18 | 32.768 kHz crystal Y1 |

VDD and VDDH are both on `+3V3` and DCCH is open (Raytac reference circuit 8.3).
Module pins 3 to 14 and 50 to 61 are limited to signals below 10 kHz. Only static signals use them here.
All other pins carry no-connect flags.

## Connectors

*Table 7. Connectors on the sensor node.*

| Ref | Type | Pins |
|---|---|---|
| J1 | USB-C, USB 2.0 device | 5.1k on CC1 and CC2 |
| J2 | 2x5 1.27 mm Cortex debug | 1 VTref, 2 SWDIO, 4 SWDCLK, 6 SWO, 10 reset, 3/5/9 GND |
| J3 | 1x4 2.54 mm I2C | 1 `+3V3`, 2 GND, 3 SDA, 4 SCL |
| J4 | 1x4 2.54 mm LED board PWM | 1 GND, 2 PWM blue, 3 PWM red, 4 GND. Signals only (250 Hz, high-drive 3.3 V); mates with `pcbs/led_driver` J2, which has its own 24 V supply. |
| J5 | 2-pin JST-PH battery | 1 cell positive, 2 cell negative. The 18650 sits in the enclosure cradle. |
| J6 | 1x4 2.54 mm PAR sensor (rev 3.2) | 1 GND (shield), 2 sensor signal +, 3 GND (sensor -), 4 `+3V3` (50 mA max, for a powered sensor). Self-powered sensors up to 150 mV full scale (SAADC gain 4). |

## Sensors, checked against datasheets

*Table 8. Sensors checked against their datasheets: pins and the limits that matter here.*

| Part | Pins | Limits that matter here |
|---|---|---|
| SHT40-AD1B | 1 SDA, 2 SCL, 3 VDD, 4 VSS; address 0x44 | 1.08 to 3.6 V. No copper under the part except its pads; centre pad not soldered. Idle 0.08 uA. Rev 3.2: on the isolated tongue (Sensirion design guide: slots, no copper planes near the sensor). |
| Quantum sensor on J6 (rev 3.2, bought) | 2 wires + shield | Apogee SQ-500-SS: self-powered, 0 to 40 mV, 0.01 mV per umol m-2 s-1, calibration +/-5 %, factor on its certificate (`CONFIG_GOS_PAR_UMOL_PER_MV`). At gain 4 the SAADC counts 37 uV, about 3.7 umol m-2 s-1; 256x oversampling averages below that. |
| TSL25911FN | 1 SCL, 2 INT (open drain), 3 GND, 4 NC, 5 VDD, 6 SDA; address 0x29 | 2.7 to 3.6 V, -30 to 70 C. Sleep 2.3 uA, active 275 uA. |

Both match the KiCad stock symbols used.

## Power budget (estimate)

Standing current with the node asleep, typical datasheet values, at the battery:

*Table 9. Sleep current budget at the battery, from typical datasheet values (an estimate, not a measurement).*

| Consumer | Current |
|---|---|
| BQ24074, battery side, no USB | 4.3 uA (6.5 max) |
| DW01A | 3.0 uA (6.0 max) |
| Battery sense divider (4.4 Mohm) | 0.8 uA |
| TPS62740 | 0.4 uA |
| nRF52840, System ON, RAM kept, RTC running | 3.2 uA |
| TSL2591 asleep | 2.3 uA |
| SHT40 idle | 0.1 uA |
| **Floor** | **about 14 uA** |

On top of the floor:

- One sensor reading a minute adds about 2 uA, if the TSL2591 is put back to sleep between readings. Left awake it draws 275 uA on its own.
- Thread polling: Nordic publishes no nRF52840 figure; its nRF5340 board measures 17.8 uC per poll at 0 dBm, and the nRF52840 radio draws roughly twice the current. At 20 to 40 uC per poll a 1 s poll period would cost 20 to 40 uA, so the firmware polls every 30 s (about 1 uA) and polls fast for 2.5 s only after each packet, to collect the LED reply.
- One packet a minute with its fast polls: a few uA.
- LED PWM: the PWM peripheral keeps the 16 MHz clock running only while a channel is dimmed (not 0 % or 100 %; Zephyr's nRF driver stops the peripheral otherwise). Nodes that drive an LED board run on USB power as routers (see `documentation/system_review.md`).
- An 18650 loses about 2 % a month by itself, the equivalent of roughly 80 uA from a 3000 mAh cell.

So a sleepy climate node draws an estimated 20 to 30 uA, less than the cell's own self-discharge: years on a 3000 mAh cell by the electronics alone, so the 6-month target has a wide margin. Nothing here has been measured; `bring_up.md` step 8 measures it.

## Firmware

`firmware/` is a Zephyr application for upstream board `raytac_mdbt50q_db_40/nrf52840` (Raytac's demo board for the same module).

```
west build -b raytac_mdbt50q_db_40/nrf52840
```

*Table 10. Firmware files and the role of each.*

| File | Role |
|---|---|
| `boards/raytac_mdbt50q_db_40_nrf52840.overlay` | turns the demo board into this board: pins, sensors, battery divider, charger status |
| `src/main.c` | every 60 s reads SHT40, TSL2591, battery voltage and charger status, logs them and sends them over Thread; feeds the watchdog; LED-board PWM starts at 0 % and falls back to `CONFIG_GOS_LED_FALLBACK_*` if no LED command arrives for `CONFIG_GOS_LED_HOLD_S` |
| `src/uplink.c` | builds and signs the 43-byte PACKET_V4 and sends it as a non-confirmable CoAP POST; its response handler applies the LED command in the gateway's reply |
| `src/downlink.c` | checks an LED command (version, tag, counter, range); host test in `tests/host/test_downlink.c` |
| `Kconfig` | node index (1 to 40), uplink address, port and CoAP path, LED hold time and fallback levels |
| `credentials.conf` | Thread network key, node index and the node's own signing key; git-ignored. `gateway/tools/provision_node.py --index N` prints it. Without a valid signing key the node sends nothing. |
| `prj.conf` | driver subsystems; Thread as a sleepy end device polling every 1 s, channel 15, PAN 0x1234, name GOS_PHYTOTRON |

It uses Zephyr's own SHT4x, TSL2591 and voltage-divider drivers. There are no project drivers or bindings.

### Uplink

*Table 11. Uplink settings: default and how to change each.*

| Setting | Default | Change with |
|---|---|---|
| Destination | `ff03::1` (all Thread devices, including the border router) port 5683 | `CONFIG_GOS_UPLINK_PEER_ADDR`, `CONFIG_GOS_UPLINK_PEER_PORT` |
| CoAP path | `/telemetry` | `CONFIG_GOS_UPLINK_URI_PATH` |
| Node index | 1 | `CONFIG_GOS_NODE_INDEX` |

Payload (PACKET_V5, rev 3.2 firmware), 45 bytes, all fields little-endian, decode with Python `struct.unpack("<BBQffHHHIB16s", payload)`. Built by `src/packet.c`, which has no Zephyr calls so `tests/host/test_packet.c` checks its bytes against the gateway's format on a PC:

*Table 12. PACKET_V5 payload: 45 bytes, little-endian, field by field (V4 had no PAR field; everything after it moved 2 bytes).*

| Offset | Field | Notes |
|---|---|---|
| 0 | version | 5 (signed; the receiver also accepts version 4, without PAR, and 3, without flags) |
| 1 | node index | |
| 2 | EUI-64 | factory address as an integer, first EUI byte most significant |
| 10 | temperature, float, degC | NaN if the read failed |
| 14 | humidity, float, %RH | NaN if the read failed |
| 18 | light, lux | clamped to 65534; 65535 if the read failed |
| 20 | PAR, umol m-2 s-1 | rev 3.2: quantum sensor on J6; 65535 when `CONFIG_GOS_PAR_SENSOR` is off or the read failed |
| 22 | battery, mV | 65535 if the read failed |
| 24 | counter, u32 | boot epoch (kept in flash) << 16, plus a sequence number; never repeats |
| 28 | flags | bit 7 charger state valid, bit 0 USB power present, bit 1 charging. The charger warms the board (up to about 0.65 W), so climate readings taken while charging read high; filter them with `payload->>'charging'`. |
| 29 | tag, 16 bytes | first 16 bytes of HMAC-SHA256(node key, bytes 0 to 28) |

### LED commands

The gateway's 2.04 reply to each packet carries the LED level for this node (23 bytes, format in
`documentation/hardware_protocol.md`), signed with the node's key and bound to the counter of the
packet it answers. The node sets the PWM only if both check out. With the 1 s poll period the reply
arrives within about a second. No command for `CONFIG_GOS_LED_HOLD_S` (900 s): fallback levels
(default off).

### Packet authentication

Each node has its own 128-bit key. `gateway/tools/provision_node.py --index N` generates it, stores it in `gateway/secrets/node_keys.json` (git-ignored, mounted read-only into the receiver) and prints the node's `credentials.conf`. After the node's first boot, rerun the tool with `--eui64` (the node logs its EUI-64 at boot) to pin that chip to the index.

The receiver stores a packet only if the tag verifies with that node's key, the EUI-64 matches when pinned, and the counter is higher than the last one stored for the node. The last counter is read back from the database after a restart, so recorded packets cannot be replayed. Rejected packets get CoAP 4.01 when confirmable and are otherwise dropped. `GOS_ALLOW_UNSIGNED=1` turns all of this off for bench testing.

What this does not cover: anyone who can read a node's flash (with a debugger) gets its key, and readings are signed, not encrypted. Thread's own network encryption still protects them in transit.

This extends `documentation/hardware_protocol.md` (PACKET_V2) with the counter and tag.

The gateway receiver is `gateway/services/coap_receiver.py` (Docker Compose service `coap_receiver`, started with `docker compose --profile hardware up` on the border router host). It stores each packet in `raw_telemetry`; lux goes in `payload.light_lux` because `par_umol` is PAR, which the node does not measure.

### Power

- Between samples every thread sleeps, so Zephyr idles the CPU in System ON sleep.
- The TSL2591 is powered up only for each reading (driver suspend/resume, `CONFIG_PM_DEVICE`), so it draws 2.3 uA instead of 275 uA between readings.
- The debug UART keeps the high-frequency clock running. For nodes in the phytotron build without it:

```
west build -b raytac_mdbt50q_db_40/nrf52840 -- -DEXTRA_CONF_FILE=low_power.conf
```

Not implemented: any use of the user button or the TSL2591 interrupt. Sleep current has not been measured.

### Builds

*Table 13. Firmware builds and the flash and RAM each uses.*

| Node | Build | Flash / RAM |
|---|---|---|
| bench (logging on) | `west build -b raytac_mdbt50q_db_40/nrf52840` | 214.7 KB / 62.4 KB |
| climate node in the field (battery, sleepy) | `... -- -DEXTRA_CONF_FILE=low_power.conf` | 197.3 KB / 60.1 KB |
| same, debugger locked (keys cannot be read out) | `... -- -DEXTRA_CONF_FILE="low_power.conf;lock.conf"` | 197.3 KB / 60.1 KB |
| light node (USB powered, Thread router, relays for others) | `... -- -DEXTRA_CONF_FILE=router.conf` | 261.6 KB / 70.6 KB |
| rev 3.2 light node with a quantum sensor on J6 | `... -- -DEXTRA_CONF_FILE="router.conf;par_sensor.conf"` | 261.8 KB / 70.6 KB |
| rev 3.2 climate node with a quantum sensor | `... -- -DEXTRA_CONF_FILE="low_power.conf;par_sensor.conf"` | 197.5 KB / 60.1 KB |

All six built on 2026-11-22 (Zephyr main f8da8ea, SDK 1.0.1). Each prints one Kconfig warning
from Zephyr's own defaults (`SECURE_STORAGE_ITS_TRANSFORM_AEAD_KEY_PROVIDER_DEVICE_ID_HASH`), the
same as the rev 3.1 builds; none from the project's code. Set the quantum sensor's calibration
factor in `par_sensor.conf` (`CONFIG_GOS_PAR_UMOL_PER_MV`, umol m-2 s-1 per mV, from its certificate).

A locked node can only be reflashed after a full chip erase (`nrfjprog --recover`), which also
erases its message-counter epoch: re-provision it (new key) before reflashing, or the gateway
rejects its packets as replays.

## Board layout

Two scripts, both run with KiCad's Python (`C:\Program Files\KiCad\9.0\bin\python.exe`):

1. `generate_pcb.py` builds `gos_sensor_node.kicad_pcb` from the schematic:
   - the 40 x 65 mm outline from `mechanical/enclosure_gen.scad`, with the four M2.5 holes 5 mm in from each corner where the enclosure posts are
   - **4 layers**: F.Cu signals and parts, In1.Cu solid GND plane, In2.Cu solid GND plane, B.Cu signals. Stack-up JLCPCB JLC04161H-1080 (1.6 mm; 1080 prepreg 0.0764 mm between each outer layer and its plane), ENIG finish, written into the board file
   - all 70 footprints with every net, placed in groups: module on the top edge with a 6.5 mm part-free strip for the antenna, USB-C on the bottom edge, sensors on the side edges away from the charger and buck, battery connector and protection parts down the left side
   - a copper keep-out (tracks, vias and pour, all four layers) across the full width beside the antenna, wider than the module footprint's own keep-out
   - net classes in `gos_sensor_node.kicad_pro`: 0.2 mm signal tracks with 0.15 mm clearance and 0.6/0.3 mm vias; 0.3 mm for VBUS, VSYS, VBAT, the cell path (BAT_P, BAT_N, FET_D) and the buck switch node. The highest current on any of them is the charger's 0.54 A input limit. +3V3 (300 mA buck limit) and GND use signal width: GND current flows in the planes and pours.
   - the drill/place origin at the board's bottom-left corner, fabrication notes on User.Comments, small-part reference labels on the fab (assembly) layer
2. Before autorouting, the buck converter's switching loop is placed and routed by hand (locked copper in `generate_pcb.py`: L1 at the SW pin, C4 at VIN, C5 at L1's output, 2.6 mm switch node with no vias). `route_pcb.py` then autoroutes the rest with Freerouting, adds thermal vias in the charger and buck exposed pads, pours GND on all four layers, adds ground stitching vias on a 1.6 mm grid wherever they fit (about 230), runs DRC with schematic parity and, only if that is clean, writes:
   - `fab/`: Gerbers for all layers, Excellon drill files with drill maps, KiCad and JLCPCB placement files, the JLCPCB BOM (LCSC part numbers) and `gos_sensor_node_gerbers.zip`
   - `docs/`: assembly drawing, courtyards, user layers (fabrication notes) and all-layers PDFs, top and bottom renders, a STEP model

```
set FREEROUTING_JAR=C:\path\to\freerouting-2.0.1.jar
set JAVA=C:\Program Files\Java\jdk-22\bin\java.exe
python generate_pcb.py
python route_pcb.py
```

`route_pcb.py --fab-only` skips routing and regenerates `fab/` and `docs/` from the board as it is.

Freerouting 2.0.1 runs on Java 21 or later; 2.2 and later need Java 25. 2.5.0 (Java 25) was tried on 2026-11-14 on the 2-layer version: the LED board came out clean but with more vias, and the sensor board was left with 17 unrouted connections. The boards are routed with 2.0.1. Its result differs between runs, so `route_pcb.py` retries (up to 4 times) when connections are left unrouted or no session is written.

### Why 4 layers

The two inner layers are unbroken ground planes. Every track on the outer layers runs 0.076 mm above one, so its return current flows directly underneath: small current loops, low radiated noise, and low coupling between the buck converter's switch node and the I2C sensors, the battery ADC input and the 32 kHz crystal. The radio module sits over solid ground (except the antenna strip, which has no copper on any layer), and the USB pair has a continuous reference. The stitching vias tie the outer ground pours to both planes every 1.6 mm (2.4 GHz wavelength in FR-4 is about 62 mm; the usual limit is one twentieth of that, about 3 mm).

Current result: KiCad DRC at every severity, with schematic parity: 0 violations, 0 unconnected items, 0 parity issues. No tracks on the inner layers.

Layout review (`review_layout.py`, results in `documentation/design_review.md`): USB pair matched to 0.1 mm, buck switch node 2.6 mm on one layer with no vias and the input capacitor 2.1 mm from VIN, no copper, via or pour in the antenna strip on any layer. Both scripts regenerate the board from scratch, so hand edits in KiCad are lost if they are rerun.

Ordering (manufacturer, settings, part availability, items bought separately): `documentation/ordering.md`. Enclosure fit: `mechanical/README.md`.

## Sources

*Table 14. Datasheets and documents used, and what each was used for.*

| Part | Document | Used for |
|---|---|---|
| BQ24074 | TI SLUS810N, https://www.ti.com/lit/ds/symlink/bq24075.pdf | device table, pin functions, EN table, ISET/ILIM/TMR constants, logic levels |
| TPS62740 | TI SLVSB02B, https://www.ti.com/lit/ds/symlink/tps62740.pdf | pin table, VSEL table, input range, L and C values |
| MDBT50Q-1MV2 | Raytac spec ver. K, sections 2.5, 2.6, 8 | pin table, low-frequency pins, supply circuit, crystal caps, USB resistors |
| DW01A | H&M Semi datasheet, https://hmsemi.com/downfile/DW01A.PDF | pin table, application circuit, thresholds |
| FS8205A (Q1) | FUXINSEMI FS8205A datasheet Ver2.1 (LCSC C908265) | SOT-23-6 pinout (1 S1, 2 D, 3 S2, 4 G2, 5 D, 6 G1), 20 V, 25 mOhm max at 4.5 V |
| SWPA3015S (L1) | Sunlord SWPA series catalogue, revised 2025-05-08 | 3 x 3 x 1.5 mm outline and recommended land pattern |
| PJ-063AH (LED board J1) | CUI Devices datasheet 10/20/2022 | 2.0 mm centre pin, 5.5 mm plug, 24 V 8 A, pin numbering |
| Stack-up | jlcpcb.com/impedance, JLC04161H-1080 | layer thicknesses |
| ABS07 | Abracon ABS07 datasheet rev 08-10-22 | load capacitance options, ESR, tolerance |
| SHT4x | Sensirion datasheet V7.3 (June 2026) | pin assignment, address, supply, land pattern, currents |
| TSL2591 | ams datasheet ams163.5 (April 2013) | pin assignment, address, supply, temperature range, currents |
| nRF52840 | Nordic product specification, current consumption tables | sleep, radio and CPU currents |
| AL8860 supply | `documentation/archive/hardware_specs_rev2.md` in this repo | 4.5 V minimum input. Not re-read from the Diodes datasheet. |

## Not verified

Checked since the first version of this list (2026-11-15):

- **TSL2591 decoupling**: the ams datasheet (v3-00, page 22) specifies a 1 uF low-ESR capacitor as
  close as possible to VDD. The board has 1 uF: matches.
- **Y1 crystal**: the nRF52840 Product Specification (LFXO table, docs.nordicsemi.com) gives C_L max
  12.5 pF, C0 max 2 pF, ESR max 100 kOhm, drive level max 0.5 uW and pin capacitance 4 pF typical.
  With 12 pF capacitors the load is (12 + 4 + about 2 pF board) / 2 = about 9 pF, the ABS07's
  9 pF; its 70 kOhm ESR and 2 pF C0 are within the limits. Nordic's own reference circuit
  (Product Specification, Reference circuitry) uses the same: a 32.768 kHz crystal with
  C_L = 9 pF and 12 pF NP0 capacitors (C17, C18). LTspice (`simulation/crystal_lfxo.cir`):
  +0.3 to +0.9 ppm at the design stray, -29 to +38 ppm over 0 to 4 pF of stray, far inside
  the +/-500 ppm requirement.
- **Q1 FS8205A pinout**: FUXINSEMI datasheet (Ver 2.1, page 1): 1 S1, 2 D1/D2, 3 S2, 4 G2, 5 D1/D2,
  6 G1. The schematic symbol uses exactly these pins. The TECH PUBLIC alternate in the BOM is not
  checked.
- **Q2 reverse-cell protection**: simulated in LTspice (`simulation/cell_reverse.cir`): reversed
  cell gives 0 V on the board and 8 pA; correct cell 29 mV drop, 15 mW at 500 mA.
- **Routing**: the switching loops were placed and routed by hand and measured with
  `review_layout.py` (USB pair matched to 0.1 mm, buck switch node 2.6 mm on one layer, antenna
  strip free of copper); DRC clean.
- **Devicetree**: the bench and field builds' devicetrees compile with `dtc` 1.7.2; its only
  warnings are four shared-address notices in Zephyr's own nRF52840 SoC file.
- **Key protection**: `lock.conf` blocks debugger access (nRF APPROTECT) for nodes in service.

Still not verified (needs hardware, or a decision):

- Battery life is an estimate from datasheet figures (see Power budget), not a measurement.
- Q1 and Q2 as parts: datasheet and simulation only; nothing has been built.
- Part stock was checked on 2026-11-14 and 2026-11-15 (`documentation/ordering.md`). It changes daily.
- The SHT40 sits on the board edge for airflow; no slot or thermal isolation from the charger has
  been added (the charging flag lets readings taken while charging be filtered; a slot is proposed
  for revision 3.2 in `documentation/system_review.md`).
- The noise benefit of the 4-layer stack-up is standard practice, not a measurement on this board.
- The firmware compiles with no warnings from the project's code (Zephyr `main` at f8da8ea,
  SDK 1.0.1, GCC 14.3; sizes in Builds above). The packet encoder and the LED-command check were
  tested on a PC against the gateway's code. It has never run on hardware or joined a Thread
  network.
- Without `lock.conf`, anyone with the board and a debugger can read the keys in flash (Zephyr
  stores them under a key derived from the chip ID).
