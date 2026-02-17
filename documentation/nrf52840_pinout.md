# nRF52840 Phytotron Node: Hardware Pinout Guide

This guide is for the **Electronics/Embedded** team. It maps the Zephyr [DeviceTree](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/boards/nrf52840_phytotron.overlay) to the physical pins on the nRF52840 aQFN-73 chip.

## 🔌 1. Multi-Bus Pin Mapping

| Peripheral | Bus | Chip Pin (Port.Pin) | Function |
| :--- | :--- | :--- | :--- |
| **Debug Console** | UART | P0.06 (TX) / P0.08 (RX) | Serial terminal (115200 8N1) |
| **SHT4x Sensor** | I2C (TWIM0) | P0.26 (SDA) / P0.27 (SCL) | Temp & Humidity Data (0x44) |
| **TSL2591 Sensor** | I2C (TWIM0) | P0.26 (SDA) / P0.27 (SCL) | Light / PAR Data (0x29) |
| **TSL2591 Interrupt** | GPIO | P0.15 (active-low) | Light sensor alert (10kΩ pull-up R11) |
| **LED Array (PWM)** | PWM0 | P0.13 (Blue) / P0.14 (Red) | AL8860 CTRL pins (active-low, 50Hz) |
| **Battery ADC** | SAADC | P0.02 (AIN0) | Battery voltage via gated 1MΩ divider |
| **Battery Gate** | GPIO | P0.03 | Enables Q4 P-MOSFET for ADC read (LOW=ON) |
| **802.15.4 Radio** | Internal | — | On-chip radio, PCB antenna or u.FL (J5) |
| **QSPI Flash** | QSPI | P0.19/P0.20/P0.21/P0.22 | High-speed data logging (XIP) |
| **SWD Debug** | SWD | SWDCLK / SWDIO | J2 (2×5 1.27mm Samtec FTSH-105) |
| **USB-C** | USB 2.0 | D+ / D- | J1 (GCT USB4085-GF-A) — programming, charging |

## 🛠 2. Hands-on Soldering Protocol
As per the mandatory responsibilities:
1.  **nRF52840 Package**: aQFN-73 (7×7mm) with exposed ground pad. Requires **reflow soldering** — ensure thermal pad has solder paste (70-80% coverage) and thermal vias (4×4 grid, 0.3mm drill) for heat dissipation.
2.  **Pull-up Resistors**: Ensure **4.7kΩ pull-ups** (R3-R4) are soldered to the I2C lines (P0.26/P0.27). Only ONE set of pull-ups on the shared bus.
3.  **Battery Connector**: J4 (2-pin JST-PH 2mm). 18650 cell via Keystone 1042P spring-contact holder. Protected by DW01A + FS8205A (OVP/ODP/OCP/SCP) and charged by BQ24075 via USB-C.
4.  **ESD Protection**: PRTR5V0U2X (D5) on USB lines, PESD0402-140 (D6) on antenna, PESD5V0S1BSF (D7-D8) on external I2C (J3).

## 🧪 3. Multimeter Checkpoints
Before flashing the [firmware](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/src/main.c), verify:
- **VCC Target**: 3.3V stable at the TPS62740 buck regulator output (VDD_3V3 rail).
- **DEC4 Voltage**: 1.3V at nRF52840 DEC4 pin (REG1 internal regulator output).
- **I2C Idle**: SDA/SCL should sit at 3.3V (pulled up by R3/R4).
- **Radio Ground**: Check continuity between the chip's exposed ground pad and the battery negative terminal.
- **USB-C CC Pins**: Verify 5.1kΩ pull-downs (R26-R27) to GND for proper device-mode detection.

## 🔎 4. Oscilloscope Validation
- **I2C Clock**: Verify a clean 100kHz square wave on P0.27 during sensor polling.
- **UART Data**: Look for 3.3V logic pulses on P0.06 when the device prints startup messages.
- **PWM Output**: Verify 50Hz inverted-polarity signal on P0.13/P0.14 when LEDs are active.
- **Battery Gate**: P0.03 should pulse LOW for ~1ms during each ADC read cycle, then return HIGH.
