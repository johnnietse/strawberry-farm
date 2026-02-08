# nRF52840 Phytotron Node: Hardware Pinout Guide

This guide is for the **Electronics/Embedded** team. It maps the Zephyr [DeviceTree](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/boards/nrf52840_phytotron.dts) to the physical pins on the nRF52 chip.

## 🔌 1. Multi-Bus Pin Mapping

| Peripheral | Bus | Chip Pin (Port.Pin) | Function |
| :--- | :--- | :--- | :--- |
| **Debug Console** | UART | P0.06 (TX) / P0.08 (RX) | Serial terminal (115200 8N1) |
| **SHT4x Sensor** | I2C (TWIM0) | P0.26 (SDA) / P0.27 (SCL) | Temp & Humidity Data |
| **LED Array** | GPIO | P0.13 (Blue) / P0.14 (Red) | Photosynthesis Steering |
| **802.15.4 Radio** | SPI (SPIM1) | P1.01(SCK)/P1.02(MOSI)/P1.03(MISO) | Mesh Communication CS: P0.17 |
| **External Flash** | QSPI | P0.19/P0.20/P0.21/P0.22 | High-speed data logging (XIP) |

## 🛠 2. Hand-on Soldering Protocol
As per the mandatory responsibilities:
1.  **SMD Footprint**: Use a fine-tip soldering iron and 0.3mm solder for the nRF52840 package.
2.  **Pull-up Resistors**: Ensure **4.7kΩ pull-ups** are soldered to the I2C lines (P0.26/P0.27).
3.  **Battery Header**: Use 22AWG wire for the LiPo connector to handle peak radio transmit currents (~15mA).

## 🧪 3. Multimeter Checkpoints
Before flashing the [firmware](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/src/main.cpp), verify:
- **VCC Target**: 3.3V stable at the chip's VDD pins.
- **I2C Idle**: SDA/SCL should sit at 3.3V.
- **Radio Ground**: Check continuity between the chip's Ground Pad (EP) and the battery negative terminal.

## 🔎 4. Oscilloscope Validation
- **I2C Clock**: Verify a clean 100kHz square wave on P0.27 during boot.
- **UART Data**: Look for 3.3V logic pulses on P0.06 when the device prints "SYSTEM START".
