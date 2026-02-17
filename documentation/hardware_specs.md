# Hardware Manufacturing Specifications: Strawberry Research IoT Fleet

To move from prototype to mass production for greenhouse research, the following hardware considerations are critical for reliability and data integrity.

## 1. PCB Design & Routing (nRF52840 Custom Board)
- **Package**: nRF52840-QIAA-R7 in **aQFN-73** (7×7mm). Requires thermal vias (4×4 grid, 0.3mm drill) under the exposed ground pad.
- **High Impedance Isolation**: EC and pH sensor traces must be guarded with grounded planes to prevent crosstalk and drift. Use low-leakage capacitors (C0G/NP0) in the analog front-end.
- **Power Planes**: Use a 4-layer stackup (Signal, GND, PWR, Signal). Decoupling capacitors per Nordic PS v1.8 §6.6:
  - VDDH: 4.7µF (C1),  VDD: 4×100nF (C2-C5),  DEC4: 1µF + 47nF (C7-C8)
  - DECUSB: 4.7µF (C12),  GPIO: 1µF (C13)
- **RF Optimization**: Use a Nordic-recommended pi-network matching circuit (L4=3.9nH, C31=0.8pF) for the 2.4GHz PCB antenna. Follow the nRF52840 reference design for the aQFN-73 package.
- **LED Drivers**: Two AL8860MP-13 constant-current buck drivers powered from external 5-12V rail (J6). **Not** from VDD_3V3 or battery — AL8860 minimum VIN is 4.5V.

## 2. 3D Printing & Enclosure (Fusion 360)
- **Material**: **ASA (Acrylic Styrene Acrylonitrile)** is mandatory. PLA will warp in greenhouse heat (>50°C), and PETG lacks sufficient UV resistance for multi-month deployments.
- **Infill**: 25% Gyroid infill for structural robustness while maintaining lightweight characteristics.
- **IP67 Sealing**:
    - Design a tongue-and-groove lid interface.
    - Integrate a slot for a **Nitrile O-Ring** or use a TPU-printed gasket.
    - Use PG7 or PG9 cable glands for external sensors to prevent moisture ingress.
- **UV Protection**: Even with ASA, consider a UV-reflective white finish to minimize solar heating.

## 3. High-Fidelity Calibration
- **EC Calibration**: Bracketing method using 1413 µS/cm and 12.88 mS/cm standards.
- **pH Calibration**: 3-point calibration (pH 4.0, 7.0, 10.0) with automated temperature compensation (ATC) enabled in firmware.
- **PAR Sensor**: Annual cross-calibration against a NIST-traceable quantum sensor.

## 4. Bill of Materials (Scalable Sourcing)
- **MCU**: Nordic nRF52840-QIAA-R7 (aQFN-73, Thread/Zigbee/BLE).
- **Battery**: 18650 Li-Ion cell (3.0-4.2V) in Keystone 1042P holder, with:
  - **Charger**: BQ24075RGTR (USB power-path management, 750mA charge via ISET 2kΩ)
  - **Protection**: DW01A-G + FS8205A (OVP 4.3V, ODP 2.4V, OCP, SCP)
  - **Monitoring**: Gated 1MΩ voltage divider via DMG2305UX P-MOSFET (zero standby drain)
- **Regulator**: TPS62740DSSR buck converter (3.3V output, 360nA Iq, VSEL[1:4] all HIGH)
- **Sensors**: SHT40-AD1B-R2 (temp/hum, I2C 0x44) + TSL2591FN (light, I2C 0x29)
- **LED Drivers**: 2× AL8860MP-13 (MSOP-8) with 33µH inductors, 0.1Ω sense resistors
- **ESD Protection**: PRTR5V0U2X (USB), PESD0402-140 (antenna), PESD5V0S1BSF (ext I2C)
- **Gateway**: Raspberry Pi 4 Model B (4GB) with heatsink and active cooling.
- **RCP**: nRF52840 USB Dongle (PCA10059) flashed with OpenThread RCP firmware.

## 5. Power Budget

| Mode | Current | Duration | Notes |
|------|---------|----------|-------|
| SYSTEM_OFF (deep sleep) | 0.9 µA | ~99.7% of time | SED, GPIO wake |
| SYSTEM_ON (LP) | 2.5 µA | Sensor read | ~200ms per cycle |
| ACTIVE_RADIO (TX) | 8.5 mA | Transmit | ~10ms per cycle |
| LED driving (AL8860) | Powered from J6 | As scheduled | External 5-12V supply |

Estimated battery life (2600mAh 18650): **7+ years** in SED mode with 60s polling interval.
