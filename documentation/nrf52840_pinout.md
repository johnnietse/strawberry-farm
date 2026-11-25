# G.O.S. Sensor Node rev 3.2: Pinout and Assembly Guide

For the Electronics/Embedded team. Full design reference: [`pcbs/gos_sensor_node/HARDWARE.md`](../pcbs/gos_sensor_node/HARDWARE.md).
The rev 2 version of this guide (bare nRF52840 chip) is in [`archive/nrf52840_pinout_rev2.md`](archive/nrf52840_pinout_rev2.md).

## 1. Pin map

The MCU is a Raytac MDBT50Q-1MV2 module (nRF52840 inside). Firmware pin names are in
`pcbs/gos_sensor_node/firmware/boards/raytac_mdbt50q_db_40_nrf52840.overlay`.

| Function | nRF pin | Connects to |
|:---|:---|:---|
| I2C SDA / SCL | P0.26 / P0.27 | SHT40 (0x44), TSL2591 (0x29), J3 header; 4.7 kOhm pull-ups on the board |
| Light sensor interrupt | P0.15 | TSL2591 INT (open drain, 100 kOhm pull-up) |
| LED board PWM blue / red | P0.13 / P0.14 | J4 pins 2 / 3 through 100 Ohm; 100 kOhm pull-downs |
| Debug UART TX / RX | P0.06 / P0.08 | test points TP5 / TP6, 115200 8N1 |
| Battery voltage | P0.02 (AIN0) | VBAT through 2.2 MOhm / 2.2 MOhm divider |
| PAR sensor (rev 3.2) | P0.03 (AIN1) | J6 pin 2 through 1 kOhm (R24), 100 nF (C15) to GND; SAADC gain 4 |
| USB power good / charging | P0.28 / P0.29 | BQ24074 PGOOD / CHG, active low |
| Status LED | P0.17 | D2, on when low |
| User button | P0.24 | SW2 to ground |
| Reset | P0.18 | SW1, J2 pin 10 |
| SWD | SWDIO, SWDCLK, P1.00 (SWO) | J2, 10-pin 1.27 mm Cortex debug header |
| USB | D+ / D- | J1 USB-C through 27 Ohm and the ESD clamp |
| 32.768 kHz crystal | P0.00 / P0.01 | Y1, Abracon ABS07-32.768KHZ-9-T, 12 pF load caps |

## 2. Connectors

| Ref | What | Pins |
|:---|:---|:---|
| J1 | USB-C (power and USB) | |
| J2 | SWD debug, 2x5 1.27 mm | 1 VTref, 2 SWDIO, 4 SWDCLK, 6 SWO, 10 reset, 3/5/9 GND |
| J3 | I2C expansion, 1x4 2.54 mm | 1 3.3 V, 2 GND, 3 SDA, 4 SCL |
| J4 | LED driver board, 1x4 2.54 mm | 1 GND, 2 PWM blue, 3 PWM red, 4 GND. Signals only. |
| J5 | Battery, 2-pin JST-PH | 1 cell positive, 2 cell negative |
| J6 (rev 3.2) | PAR (quantum) sensor, 1x4 2.54 mm | 1 GND (shield), 2 sensor +, 3 GND (sensor -), 4 3.3 V (50 mA max) |

## 3. Assembly notes

1. **Reflow only** for the module, U1 (BQ24074, QFN-16), U2 (TPS62740, WSON-12) and U6 (TSL2591, DFN-6): the exposed pads need paste and reflow.
2. **SHT40 (U5):** no copper under it except its four pads, and leave its centre pad unsoldered (Sensirion land pattern). Keep it away from flux residue; do not wash it with aggressive solvents.
3. **TSL2591 (U6):** nothing taller beside it; keep its window clean.
4. **Battery:** check the 18650 lead polarity against J5 pin 1 = positive before plugging in. Q2 blocks a reversed cell, but the cell will not charge until fixed. Plug USB in once after connecting a cell to wake the protection IC.
5. **Antenna:** keep the strip along the module's top edge free of copper, metal and fingers when testing range.
