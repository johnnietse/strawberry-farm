# G.O.S. sensor node rev 3.1 hardware reference

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

## What changed from rev 2

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

| Event | Threshold |
|---|---|
| Overcharge | 4.30 V +/- 0.05 V, release 4.10 V |
| Overdischarge | 2.40 V +/- 0.10 V, release 3.00 V |
| Overcurrent | 150 mV across both FETs. At 25 to 35 mohm each that is about 2.1 to 3 A. |

After a cell is fitted the DW01A may stay off until USB is plugged in once.

## Module pin map (MDBT50Q-1MV2)

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

| Ref | Type | Pins |
|---|---|---|
| J1 | USB-C, USB 2.0 device | 5.1k on CC1 and CC2 |
| J2 | 2x5 1.27 mm Cortex debug | 1 VTref, 2 SWDIO, 4 SWDCLK, 6 SWO, 10 reset, 3/5/9 GND |
| J3 | 1x4 2.54 mm I2C | 1 `+3V3`, 2 GND, 3 SDA, 4 SCL |
| J4 | 1x4 2.54 mm LED board PWM | 1 GND, 2 PWM blue, 3 PWM red, 4 GND. Signals only: the LED board brings its own 5 to 12 V. |
| J5 | 2-pin JST-PH battery | 1 cell positive, 2 cell negative. The 18650 sits in the enclosure cradle. |

## Sensors, checked against datasheets

| Part | Pins | Limits that matter here |
|---|---|---|
| SHT40-AD1B | 1 SDA, 2 SCL, 3 VDD, 4 VSS; address 0x44 | 1.08 to 3.6 V. No copper under the part except its pads; centre pad not soldered. Idle 0.08 uA. |
| TSL25911FN | 1 SCL, 2 INT (open drain), 3 GND, 4 NC, 5 VDD, 6 SDA; address 0x29 | 2.7 to 3.6 V, -30 to 70 C. Sleep 2.3 uA, active 275 uA. |

Both match the KiCad stock symbols used.

## Power budget (estimate)

Standing current with the node asleep, typical datasheet values, at the battery:

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
- Thread polling dominates. Nordic publishes no nRF52840 figure; its nRF5340 board measures 17.8 uC per poll at 0 dBm, and the nRF52840 radio draws roughly twice the current. At 20 to 40 uC per poll, a 1 s poll period costs 20 to 40 uA and a 10 s period 2 to 4 uA.
- An 18650 loses about 2 % a month by itself, the equivalent of roughly 80 uA from a 3000 mAh cell.

So with sleep implemented properly the electronics draw 40 to 60 uA at a 1 s poll, less than the cell's own self-discharge, and the 6-month target has a wide margin. The current firmware does not sleep and has no radio code, so none of this applies to it yet. Nothing here has been measured.

## Firmware

`firmware/` is a Zephyr application for upstream board `raytac_mdbt50q_db_40/nrf52840` (Raytac's demo board for the same module).

```
west build -b raytac_mdbt50q_db_40/nrf52840
```

| File | Role |
|---|---|
| `boards/raytac_mdbt50q_db_40_nrf52840.overlay` | turns the demo board into this board: pins, sensors, battery divider, charger status |
| `src/main.c` | every 60 s reads SHT40, TSL2591, battery voltage and charger status, logs them and sends them over Thread; feeds the watchdog; holds both LED-board PWM channels at 0 % |
| `src/uplink.c` | builds the 22-byte PACKET_V2 research packet and sends it as a non-confirmable CoAP POST |
| `Kconfig` | node index (1 to 40), uplink address, port and CoAP path |
| `credentials.conf` | Thread network key; git-ignored, copy from `credentials.conf.example`. Without it the node cannot join. |
| `prj.conf` | driver subsystems; Thread as a sleepy end device polling every 1 s, channel 15, PAN 0x1234, name GOS_PHYTOTRON |

It uses Zephyr's own SHT4x, TSL2591 and voltage-divider drivers. There are no project drivers or bindings.

### Uplink

| Setting | Default | Change with |
|---|---|---|
| Destination | `ff03::1` (all Thread devices, including the border router) port 5683 | `CONFIG_GOS_UPLINK_PEER_ADDR`, `CONFIG_GOS_UPLINK_PEER_PORT` |
| CoAP path | `/telemetry` | `CONFIG_GOS_UPLINK_URI_PATH` |
| Node index | 1 | `CONFIG_GOS_NODE_INDEX` |

Payload, 22 bytes, all fields little-endian, decode with Python `struct.unpack("<BBQffHH", payload)`:

| Offset | Field | Notes |
|---|---|---|
| 0 | version | always 2 |
| 1 | node index | |
| 2 | EUI-64 | factory address as an integer, first EUI byte most significant |
| 10 | temperature, float, degC | NaN if the read failed |
| 14 | humidity, float, %RH | NaN if the read failed |
| 18 | light, lux | clamped to 65534; 65535 if the read failed |
| 20 | battery, mV | 65535 if the read failed |

This follows `documentation/hardware_protocol.md`. That document does not say how the EUI-64 is ordered or what marks a failed reading; the choices above are this firmware's.

The gateway receiver is `gateway/services/coap_receiver.py` (Docker Compose service `coap_receiver`, started with `docker compose --profile hardware up` on the border router host). It stores each packet in `raw_telemetry`; lux goes in `payload.light_lux` because `par_umol` is PAR, which the node does not measure.

### Power

- Between samples every thread sleeps, so Zephyr idles the CPU in System ON sleep.
- The TSL2591 is powered up only for each reading (driver suspend/resume, `CONFIG_PM_DEVICE`), so it draws 2.3 uA instead of 275 uA between readings.
- The debug UART keeps the high-frequency clock running. For nodes in the phytotron build without it:

```
west build -b raytac_mdbt50q_db_40/nrf52840 -- -DEXTRA_CONF_FILE=low_power.conf
```

Not implemented: any use of the user button or the TSL2591 interrupt. Sleep current has not been measured.

## Sources

| Part | Document | Used for |
|---|---|---|
| BQ24074 | TI SLUS810N, https://www.ti.com/lit/ds/symlink/bq24075.pdf | device table, pin functions, EN table, ISET/ILIM/TMR constants, logic levels |
| TPS62740 | TI SLVSB02B, https://www.ti.com/lit/ds/symlink/tps62740.pdf | pin table, VSEL table, input range, L and C values |
| MDBT50Q-1MV2 | Raytac spec ver. K, sections 2.5, 2.6, 8 | pin table, low-frequency pins, supply circuit, crystal caps, USB resistors |
| DW01A | H&M Semi datasheet, https://hmsemi.com/downfile/DW01A.PDF | pin table, application circuit, thresholds |
| FS8205A | Fortune FS8205A-DS-12 | pin assignment, ratings |
| SHT4x | Sensirion datasheet V7.3 (June 2026) | pin assignment, address, supply, land pattern, currents |
| TSL2591 | ams datasheet ams163.5 (April 2013) | pin assignment, address, supply, temperature range, currents |
| nRF52840 | Nordic product specification, current consumption tables | sleep, radio and CPU currents |
| AL8860 supply | `documentation/hardware_specs.md` in this repo | 4.5 V minimum input. Not re-read from the Diodes datasheet. |

## Not verified

- TSL2591 decoupling: 1 uF is a choice. The datasheet pages read give no value.
- Y1 is specified as Abracon ABS07-32.768KHZ-9-T (9 pF load, +/-20 ppm, ESR 70 kOhm max, shunt capacitance 2 pF max, same 3.2 x 1.5 mm footprint; Abracon ABS07 datasheet rev 08-10-22). The 9 pF figure assumes 4 pF nRF52840 pin capacitance, which Nordic states for the nRF5340; the nRF52840 crystal limits table could not be opened.
- Q2 reverse-cell protection is an addition of this revision. It follows the standard P-FET arrangement and has not been simulated or bench tested.
- Battery life is an estimate from datasheet figures (see Power budget), not a measurement.
- FS8205A: the Fortune Semiconductor part (LCSC C16052) is listed as discontinued and unavailable. The in-stock part sold under the same name by TECH PUBLIC (LCSC C2830320) is SOT-23-6, not TSSOP-8, so it is not a drop-in: using it needs a footprint and pin-map change. Its datasheet link returned no PDF, so its pinout is unchecked. Decision needed before ordering: find a TSSOP-8 8205A with a datasheet, or move to a SOT-23-6 dual FET.
- The board is not laid out. `gos_sensor_node.kicad_pcb` is still the empty rev 2 file.
- The firmware compiles (Zephyr `main` at f8da8ea, 2026-11-12, SDK 1.0.1, GCC 14.3) with no compiler warnings: 213 KB flash, 62 KB RAM with Thread (196 KB, 60 KB for the `low_power.conf` field build). The packet encoder was also checked on a PC against the Python decode. It has never run on hardware or joined a Thread network.
- Zephyr warns that keys stored in flash, including the Thread network key, are protected only by a key derived from the chip ID. Anyone with the board and a debugger can read them. Built without `dtc`, so the overlay was parsed by Zephyr's Python devicetree tooling only.
