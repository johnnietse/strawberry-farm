# Hardware Manufacturing Specifications: Strawberry Research IoT Fleet

To move from prototype to mass production for greenhouse research, the following hardware considerations are critical for reliability and data integrity.

## 1. PCB Design & Routing (nRF52840 Custom Board)
- **High Impedance Isolation**: EC and pH sensor traces must be guarded with grounded planes to prevent crosstalk and drift. Use low-leakage capacitors (C0G/NP0) in the analog front-end.
- **Power Planes**: Use a 4-layer stackup (Signal, GND, PWR, Signal). Ensure 0.1uF and 10uF decoupling capacitors are as close as possible to the nRF52 power pins.
- **RF Optimization**: Use a Pi-network matching circuit for the 2.4GHz antenna. Follow Nordic's reference design for the nRF52840-QIAA package.

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
- **MCUs**: Nordic nRF52840 (Thread/Zigbee/BLE).
- **Batteries**: 2000mAh LiPo with integrated protection circuit (PCM).
- **Gateway**: Raspberry Pi 4 Model B (4GB) with heatsink and active cooling.
- **RCP**: nRF52840 USB Dongle (PCA10059) flashed with OpenThread RCP firmware.
