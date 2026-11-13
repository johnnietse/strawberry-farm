# G.O.S. sensor node rev 3.0 hardware reference

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
| LED drivers | 2 x AL8860 on board | header J4 to a separate board | moved off this board |
| Charger | BQ24075 | BQ24074 | BQ24075 holds OUT at 5.5 V on USB, the TPS62740 input limit. BQ24074 holds 4.4 V. Same footprint. |
| Buck pin map | 9 pins, 2 VSEL, both low | 12 pins, 4 VSEL, all high | rev 2 table did not match the part. All four low gives 1.8 V, not 3.3 V. |
| Cell protection | both FETs on one gate net | OD to FET 1, OC to FET 2, DW01A GND to cell negative | rev 2 wiring could not switch charge and discharge separately |
| Reverse cell | none | Q2 P-FET in the positive lead | the holder accepts a cell either way round |
| Battery sense | 1M / 1M | 2.2M / 2.2M + 100 nF | halves the standing drain |
| Sheets | 8 | 5 (root, power, MCU, sensors, connectors) | protection merged into power |

## Power tree

| Net | Source | Voltage | Loads |
|---|---|---|---|
| `VBUS_CONN` | USB-C J1 | 5 V | F1 only |
| `VBUS` | F1 (0.75 A PTC) | 5 V | BQ24074 IN, module VBUS pin, USB ESD clamp |
| `VSYS` | BQ24074 OUT | 4.4 V on USB, cell voltage on battery | TPS62740, J4 (LED board) |
| `VBAT` | BQ24074 BAT | 3.0 to 4.2 V | cell through Q2, DW01A supply, sense divider |
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
| `PWM_BLUE` | P0.13 | 37 | J4 pin 5 through 100R |
| `PWM_RED` | P0.14 | 36 | J4 pin 6 through 100R |
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
| J4 | 1x6 2.54 mm LED board | 1-2 `VSYS`, 3-4 GND, 5 PWM blue, 6 PWM red |

## Firmware

`firmware/` is a Zephyr application for upstream board `raytac_mdbt50q_db_40/nrf52840` (Raytac's demo board for the same module).

```
west build -b raytac_mdbt50q_db_40/nrf52840
```

| File | Role |
|---|---|
| `boards/raytac_mdbt50q_db_40_nrf52840.overlay` | turns the demo board into this board: pins, sensors, battery divider, charger status |
| `src/main.c` | every 60 s reads SHT40, TSL2591, battery voltage and charger status and logs them; feeds the watchdog; holds both LED-board PWM channels at 0 % |
| `prj.conf` | driver subsystems only |

It uses Zephyr's own SHT4x, TSL2591 and voltage-divider drivers. There are no project drivers or bindings.

Not implemented: Thread / CoAP uplink, low-power sleep, any use of the user button or the TSL2591 interrupt.

## Sources

| Part | Document | Used for |
|---|---|---|
| BQ24074 | TI SLUS810N, https://www.ti.com/lit/ds/symlink/bq24075.pdf | device table, pin functions, EN table, ISET/ILIM/TMR constants, logic levels |
| TPS62740 | TI SLVSB02B, https://www.ti.com/lit/ds/symlink/tps62740.pdf | pin table, VSEL table, input range, L and C values |
| MDBT50Q-1MV2 | Raytac spec ver. K, sections 2.5, 2.6, 8 | pin table, low-frequency pins, supply circuit, crystal caps, USB resistors |
| DW01A | H&M Semi datasheet, https://hmsemi.com/downfile/DW01A.PDF | pin table, application circuit, thresholds |
| FS8205A | Fortune FS8205A-DS-12 | pin assignment, ratings |

## Not verified

- SHT40 and TSL2591 pinouts come from the KiCad stock symbols. Their datasheets were not read. The 1 uF on the TSL2591 is a choice, not a datasheet value.
- Y1 load capacitance (9 pF) is calculated from Raytac's 12 pF capacitors. Confirm against the crystal chosen.
- Q2 reverse-cell protection is an addition of this revision. It follows the standard P-FET arrangement and has not been simulated or bench tested.
- Battery life has not been calculated. Datasheet standing currents: BQ24074 up to 6.5 uA, DW01A 3 uA typical, TPS62740 0.36 uA typical, sense divider about 1 uA.
- FS8205A stock was not checked. One distributor listing seen during the search marked it discontinued.
- The board is not laid out. `gos_sensor_node.kicad_pcb` is still the empty rev 2 file.
- The firmware compiles (Zephyr `main` at f8da8ea, 2026-11-12, SDK 1.0.1, GCC 14.3) with no errors or warnings: 48 KB flash, 8.6 KB RAM. It has never run on hardware. Built without `dtc`, so the overlay was parsed by Zephyr's Python devicetree tooling only.
