> **Superseded.** This file describes the rev 2 board (bare nRF52840, BQ24075, on-board LED drivers). The current design is rev 3.1: see [HARDWARE.md](../pcbs/gos_sensor_node/HARDWARE.md).

# 🔌 G.O.S. Phytotron Sensor Node — Complete PCB Design Specification

> **Purpose:** Everything needed to design the G.O.S. sensor node PCB in KiCad or Altium Designer, derived directly from the project firmware, device tree overlay, enclosure CAD, and system architecture.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Complete Bill of Materials](#2-complete-bill-of-materials)
3. [Schematic Design](#3-schematic-design)
4. [Power System Design](#4-power-system-design)
5. [nRF52840 MCU Circuit](#5-nrf52840-mcu-circuit)
6. [Sensor Circuits](#6-sensor-circuits)
7. [LED Driver Circuit](#7-led-driver-circuit)
8. [Radio & Antenna](#8-radio--antenna)
9. [Battery Monitoring Circuit](#9-battery-monitoring-circuit)
10. [Programming & Debug Interface](#10-programming--debug-interface)
11. [PCB Layout Strategy](#11-pcb-layout-strategy)
12. [Stackup & Design Rules](#12-stackup--design-rules)
13. [Mechanical Constraints](#13-mechanical-constraints)
14. [Fabrication & Assembly](#14-fabrication--assembly)
15. [KiCad Project Setup](#15-kicad-project-setup)

---

## 1. System Overview

### What This Board Does

The G.O.S. Phytotron Sensor Node is a **battery-powered wireless environmental monitor** for greenhouse research. Each node:

- Measures **temperature** (±0.1°C) and **humidity** (±1.8% RH) via SHT4x
- Measures **light intensity / PAR** via TSL2591
- Controls **blue (450nm) and red (660nm) LED grow lights** via PWM
- Communicates over **Thread mesh network** (IEEE 802.15.4) using CoAP
- Monitors **battery voltage** via ADC with voltage divider
- Stores data locally in **NVS flash** during network outages
- Runs on **Zephyr RTOS** with Sleepy End Device mode for 7+ year battery life

### Block Diagram

```
                    ┌──────────────────────────────────────────┐
                    │          G.O.S. SENSOR NODE PCB          │
                    │                                          │
  18650 Battery ────┤  ┌─────────┐    ┌───────────────────┐   │
  (3.0-4.2V)        │  │ Battery │    │    nRF52840       │   │
       │            │  │ Monitor │    │    (aQFN-73)      │   │
       │            │  │ (ADC +  │    │                   │   │
       │            │  │ divider,│    │ P0.26 ── I2C SDA │───┤── SHT4x (0x44)
       │   Buck  ───┤  │ gated)  │    │ P0.27 ── I2C SCL │───┤── TSL2591 (0x29)
       │            │  └────┬────┘    │                   │   │
       │            │       │         │ P0.13 ── PWM CH0  │───┤── Blue LED Driver
       │            │       │         │ P0.14 ── PWM CH1  │───┤── Red LED Driver
       │            │       │         │                   │   │
       │            │       │         │ P0.15 ── INT      │───┤── TSL2591 INT
       │            │       │         │                   │   │
       │            │  ┌────┴────┐    │ AIN0 ── Battery V │   │
       │            │  │  32MHz  │    │                   │   │
       │            │  │ Crystal │    │ 802.15.4 Radio    │───┤── PCB Antenna
       │            │  └─────────┘    │                   │   │   or u.FL
       │            │                 │ UART TX/RX        │───┤── Debug Header
       │            │                 │ SWD CLK/DIO       │───┤── Programming
       │            │                 └───────────────────┘   │
       │            │                                          │
       └────────────┴──────────────────────────────────────────┘
```

### Derived From Project Files

| Source File | What It Tells Us |
|-------------|-----------------|
| `firmware/src/main.c` | Sensors used, pin functions, data flow |
| `firmware/prj.conf` | Peripherals enabled (I2C, PWM, ADC, Thread) |
| `firmware/boards/nrf52840_phytotron.overlay` | **Exact pin assignments**, I2C addresses, ADC config |
| `firmware/include/power_mgmt.h` | Power states and current draw |
| `firmware/include/protocol.h` | Packet format (determines radio bandwidth) |
| `firmware/drivers/led_control.c` | LED GPIO fallback pins |
| `mechanical/enclosure_gen.scad` | PCB dimensions, mounting holes, battery cradle |
| `ml_engine/spectral_opt.py` | LED wavelengths needed (450nm blue, 660nm red) |

---

## 2. Complete Bill of Materials

> [!IMPORTANT]
> This BOM lists **every component** needed for fabrication, including all passive
> components (resistors, capacitors, inductors, ferrite beads, diodes). Values are
> derived from Nordic Semiconductor reference designs, component datasheets, and
> lessons from professional embedded projects (see §2.7 Design Rationale).

### 2.1 Active ICs

| Ref | Component | Part Number | Package | Qty | Purpose |
|-----|-----------|-------------|---------|-----|---------|
| U1 | MCU + Radio | **nRF52840-QIAA-R7** | aQFN-73 (7×7mm) | 1 | Cortex-M4F, 802.15.4, BLE |
| U2 | Temp/Humidity | **SHT40-AD1B-R2** | DFN-4 (2.5×2.5mm) | 1 | ±0.1°C, ±1.8% RH, I2C 0x44 |
| U3 | Light Sensor | **TSL2591FN** | DFN-6 (2×2mm) | 1 | 600M:1 dynamic range, I2C 0x29 |
| U4 | Buck Regulator | **TPS62740DSSR** | DSBGA-9 (1.6×1.6mm) | 1 | 3.3V, 360nA Iq, 300mA |
| U5 | Battery Charger | **BQ24075RGTR** | QFN-16 (3×3mm) | 1 | Li-Ion, USB power-path, 1.5A |
| U6 | Battery Protection | **DW01A-G** | SOT-23-6 | 1 | OVP/ODP/OCP/SCP |
| U7 | LED Driver (Blue) | **AL8860MP-13** | MSOP-8 | 1 | CC buck, 1.5A, PWM dim |
| U8 | LED Driver (Red) | **AL8860MP-13** | MSOP-8 | 1 | CC buck, 1.5A, PWM dim |
| Y1 | 32MHz Crystal | **NX3225GD-8M-EXS00A** | 3.2×2.5mm | 1 | HFXO, 8pF load, ±10ppm |
| Y2 | 32.768kHz Crystal | **ABS07-120-32.768KHZ-T** | 3.2×1.5mm | 1 | LFXO, 7pF load, ±20ppm |

### 2.2 nRF52840 Decoupling Capacitors (Nordic Reference)

> [!NOTE]
> Values corrected per Nordic nRF52840 Product Specification v1.8 §6.6.
> DEC4 uses 1µF + 47nF (not 4.7µF). DEC5 is only needed for build codes
> before Fxx. DECUSB is 4.7µF.

| Ref | Value | Dielectric | Pkg | Qty | nRF52840 Pin | Notes |
|-----|-------|-----------|-----|-----|-------------|-------|
| C1 | 4.7µF | X5R | 0402 | 1 | VDDH | Main supply decoupling |
| C2-C5 | 100nF | X7R | 0402 | 4 | VDD (×4) | One per VDD pin, <2mm |
| C6 | 100nF | X7R | 0402 | 1 | DEC1 | Internal reg output |
| C7 | 1µF | X7R | 0402 | 1 | DEC4 | REG1 output (1.3V) bulk |
| C8 | 47nF | X7R | 0402 | 1 | DEC4 | REG1 high-freq bypass |
| C9 | 100nF | X7R | 0402 | 1 | DEC3 | Internal regulator |
| C10 | 1µF | X5R | 0402 | 1 | DEC5 | DC/DC output (if used) |
| C11 | 4.7µF | X5R | 0402 | 1 | DEC6 | DC/DC bulk (if DC/DC mode) |
| C12 | 4.7µF | X5R | 0402 | 1 | DECUSB | USB 3.3V LDO output |
| C13 | 1µF | X7R | 0402 | 1 | GPIO | nRF52840 GPIO port decouple |

### 2.3 Crystal Capacitors

| Ref | Value | Dielectric | Pkg | Qty | Purpose |
|-----|-------|-----------|-----|-----|---------|
| C14-C15 | 12pF | C0G/NP0 | 0402 | 2 | 32MHz crystal load (CL=8pF, Cstray~2pF) |
| C16-C17 | 6.8pF | C0G/NP0 | 0402 | 2 | 32.768kHz crystal load (CL=7pF, Cstray≈4pF) |

### 2.4 Power System Passives

| Ref | Value | Dielectric/Rating | Pkg | Qty | Purpose |
|-----|-------|-------------------|-----|-----|---------|
| C18 | 4.7µF | X5R, 10V | 0603 | 1 | TPS62740 input (CIN) |
| C19 | 10µF | X5R, 10V | 0603 | 1 | TPS62740 output (COUT) |
| C20 | 10µF | X5R, 10V | 0603 | 1 | BQ24075 input (PMID) |
| C21 | 10µF | X5R, 10V | 0603 | 1 | BQ24075 output (BAT, TI recommends ≥4.7µF) |
| C22 | 1µF | X7R | 0402 | 1 | BQ24075 bypass |
| L1 | 2.2µH | Murata LQH2MCN2R2 | 0805 | 1 | TPS62740 inductor (Isat>500mA) |
| FB1 | 600Ω@100MHz | Murata BLM15AG601 | 0402 | 1 | Analog VDD filter (ADC supply) |
| D3 | Schottky | **PMEG2010AEH** | SOD-323 | 1 | Reverse polarity BAT protect |
| D4 | Schottky | **PMEG2010AEH** | SOD-323 | 1 | LED_VIN reverse protect |
| R7 | 10kΩ | 1% | 0402 | 1 | TPS62740 PG pull-up |
| R8 | 1.2kΩ | 1% | 0402 | 1 | BQ24075 ISET (742mA charge, KISET=890) |
| R9 | 10kΩ | 1% | 0402 | 1 | BQ24075 ILIM (500mA USB) |
| R10 | 10kΩ | NTC | 0402 | 1 | BQ24075 TS (battery temp) |

### 2.5 Sensor & I2C Passives

| Ref | Value | Dielectric | Pkg | Qty | Purpose |
|-----|-------|-----------|-----|-----|---------|
| C23 | 100nF | X7R | 0402 | 1 | SHT4x VDD decoupling (<2mm) |
| C24 | 1µF | X7R, low-ESR | 0402 | 1 | TSL2591 VDD decoupling (<2mm) |
| R3-R4 | 4.7kΩ | 1% | 0402 | 2 | I2C SDA/SCL pull-ups (shared bus) |
| R11 | 10kΩ | 1% | 0402 | 1 | TSL2591 INT pull-up (open-drain) |
| R12-R13 | 100Ω | 1% | 0402 | 2 | I2C series damping resistors |

> [!TIP]
> **Lesson from professional experience:** When using multiple I2C
> sensors, beware of fixed-address conflicts. The SHT4x (0x44) and TSL2591
> (0x29) have different addresses so they share one bus safely. If adding
> more sensors with conflicting addresses, use an I2C multiplexer (TCA9548A)
> or a secondary I2C bus. A professional encountered this exact issue with REV Color
> Sensors on FRC robots and had to use a Raspberry Pi as a second I2C master.

### 2.6 ESD & Protection Components

> [!WARNING]
> **Lesson from embedded engineering practice:** Every exposed connector
> pin (USB, I2C ext, antenna) MUST have ESD protection. A professional's experience
> with sensors showed that even internal pull-downs/pull-ups can fail under
> ESD stress. Series resistors on GPIO lines limit current to internal
> protection diodes.

| Ref | Value / Part | Pkg | Qty | Purpose |
|-----|-------------|-----|-----|---------|
| D5 | **PRTR5V0U2X** (dual TVS) | SOT-143B | 1 | USB D+/D- ESD (±8kV IEC) |
| D6 | **PESD0402-140** (<1pF TVS) | 0402 | 1 | Antenna ESD (low-C, <0.25pF) |
| D7-D8 | **PESD5V0S1BSF** (TVS) | SOD-962 | 2 | External I2C ESD (J3) |
| R14 | 100Ω | 0402 | 1 | USB D+ series protection |
| R15 | 100Ω | 0402 | 1 | USB D- series protection |
| R16-R17 | 1kΩ | 0402 | 2 | External I2C series ESD limit |
| F1 | 500mA PTC fuse | 0805 | 1 | USB VBUS overcurrent |
| Q3 | **FS8205A** (dual NMOS) | TSSOP-8 | 1 | Battery OVP/ODP switch |

### 2.7 Reset, Buttons & Debounce

> [!NOTE]
> **Lesson from A professional's VHDL debouncer work:** Mechanical buttons "bounce"
> for ~5-20ms. Hardware debouncing (RC filter) is more reliable than
> software-only debounce, especially during reset sequences where firmware
> hasn't started. Use 100nF + 10kΩ = ~1ms time constant.

| Ref | Value | Pkg | Qty | Purpose |
|-----|-------|-----|-----|---------|
| R18 | 10kΩ | 0402 | 1 | RESET pull-up |
| R19 | 10kΩ | 0402 | 1 | DFU button pull-up |
| C25 | 100nF | X7R, 0402 | 1 | RESET debounce (RC w/ R18) |
| C26 | 100nF | X7R, 0402 | 1 | DFU debounce (RC w/ R19) |
| SW1 | Tactile switch | 6×6mm | 1 | RESET button |
| SW2 | Tactile switch | 6×6mm | 1 | DFU/Boot button |

### 2.8 LED Driver Passives (AL8860 × 2 channels)

| Ref | Value | Rating | Pkg | Qty | Purpose |
|-----|-------|--------|-----|-----|---------|
| C27-C28 | 10µF | X5R, 25V | 0805 | 2 | AL8860 input caps (×1 each) |
| C29-C30 | 47µF | X5R, 10V | 1206 | 2 | AL8860 output caps (×1 each) |
| L2-L3 | 33µH | Isat>1.5A | 1210 | 2 | AL8860 buck inductors |
| R20 | 0.1Ω | 1%, 1/2W | 1206 | 1 | Blue LED current sense (1A) |
| R21 | 0.1Ω | 1%, 1/2W | 1206 | 1 | Red LED current sense (1A) |
| R22-R23 | 10kΩ | 1% | 0402 | 2 | PWM CTRL pull-down (off default) |
| D1 | Cree **XPEBBL-L1-0000-00201** | Star PCB | 1 | Blue LED, 450nm, 350-1000mA |
| D2 | Cree **XPEBRO-L1-0000-00801** | Star PCB | 1 | Red LED, 660nm, 350-1000mA |

### 2.9 RF Matching Network

| Ref | Value | Part Number | Pkg | Qty | Purpose |
|-----|-------|-------------|-----|-----|---------|
| L4 | 3.9nH | Murata LQW15AN3N9C00 | 0402 | 1 | Antenna match series L |
| C31 | 0.8pF | Murata GJM1555C1HR80 | 0402 | 1 | Antenna match shunt C |
| C32 | 0.5pF | (placeholder / DNP) | 0402 | 1 | Fine tuning pad (optional) |
| R24 | 0Ω | — | 0402 | 1 | PCB antenna select (default) |
| R25 | DNP | — | 0402 | 1 | u.FL select (stuff alternate) |
| J5 | u.FL/IPEX MHF | — | — | 1 | External antenna connector |

### 2.10 Connectors & Mechanical

| Ref | Component | Part Number | Qty | Purpose |
|-----|-----------|-------------|-----|---------|
| J1 | USB Type-C 2.0 | **GCT USB4085-GF-A** | 1 | Programming, charging, power |
| J2 | 2×5 1.27mm header | Samtec FTSH-105-01 | 1 | SWD Cortex Debug |
| J3 | 4-pin JST-SH (1mm) | **SM04B-SRSS-TB** | 1 | External I2C sensor |
| J4 | 2-pin JST-PH (2mm) | **S2B-PH-K-S** | 1 | Battery connector |
| J6 | 2-pin JST-XH (2.5mm) | — | 1 | LED power input (5-12V) |
| BT1 | 18650 holder | **Keystone 1042P** | 1 | Spring-contact battery cradle |
| — | M2.5×8 standoffs | — | 4 | PCB mounting |
| — | Fiducial marks | 1mm Cu pad, 2mm mask | 3 | Pick-and-place alignment |

### 2.11 Miscellaneous

| Ref | Component | Pkg | Qty | Purpose |
|-----|-----------|-----|-----|---------|
| R26-R27 | 5.1kΩ | 0402 | 2 | USB-C CC1/CC2 (device mode) |
| LED1 | Green | 0402 | 1 | Power indicator |
| LED2 | Orange | 0402 | 1 | Charge status (from BQ24075) |
| R28-R29 | 1kΩ | 0402 | 2 | Status LED current limit |

### 2.11a Battery Monitoring Components (Gated Divider)

| Ref | Component | Pkg | Qty | Purpose |
|-----|-----------|-----|-----|---------|
| R1 | 1MΩ, 1% | 0402 | 1 | Battery divider top (gated) |
| R2 | 1MΩ, 1% | 0402 | 1 | Battery divider bottom (gated) |
| R30 | 100kΩ | 0402 | 1 | Q4 gate pull-up (divider OFF at reset) |
| C33 | 100nF, X7R | 0402 | 1 | ADC anti-aliasing filter |
| Q4 | **DMG2305UX** (P-MOSFET) | SOT-23 | 1 | Battery divider gate switch |

### 2.12 Complete Component Count Summary

| Category | Count |
|----------|-------|
| ICs (MCU, sensors, regulators, drivers, protection) | 8 |
| Crystals | 2 |
| Capacitors | 33 |
| Resistors | 32 |
| Inductors / Ferrite beads | 5 |
| Diodes (TVS, Schottky, LED) | 8 |
| MOSFETs | 2 (1 dual + 1 P-ch) |
| Connectors | 6 |
| Switches | 2 |
| LEDs (indicator) | 2 |
| Mechanical (holder, standoffs, fiducials) | 8 |
| **Total unique line items** | **~70** |
| **Total placed components** | **~108** |

---

## 3. Schematic Design

### 3.1 Complete Schematic Block Structure

Design your KiCad schematic as **hierarchical sheets**:

```
Root Sheet: GOS_SENSOR_NODE.kicad_sch
├── Power.kicad_sch        (TPS62740, BQ24075 charger, power flags)
├── Protection.kicad_sch   (DW01A+FS8205A, ESD TVS, fuse)
├── MCU.kicad_sch          (nRF52840 + crystals + decoupling)
├── Sensors.kicad_sch      (SHT4x + TSL2591 + I2C bus)
├── LEDs.kicad_sch         (AL8860 ×2 CC drivers + connectors)
├── Radio.kicad_sch        (Antenna matching + u.FL + 0Ω select)
└── Connectors.kicad_sch   (USB-C, SWD, battery, external I2C)
```

### 3.2 Net Names (From Device Tree Overlay)

Use these exact net names in KiCad for clarity:

| Net Name | nRF52840 Pin | Function |
|----------|-------------|----------|
| `I2C0_SDA` | P0.26 | I2C data (SHT4x + TSL2591) |
| `I2C0_SCL` | P0.27 | I2C clock |
| `PWM_BLUE` | P0.13 | Blue LED PWM (50Hz, 20ms period) |
| `PWM_RED` | P0.14 | Red LED PWM (50Hz, 20ms period) |
| `TSL_INT` | P0.15 | TSL2591 interrupt (active low) |
| `VBATT_SENSE` | AIN0 (P0.02) | Battery ADC input (through R1/R2 divider) |
| `UART_TX` | P0.06 | Debug UART transmit |
| `UART_RX` | P0.08 | Debug UART receive |
| `SWDCLK` | — | SWD clock (dedicated pin) |
| `SWDIO` | — | SWD data (dedicated pin) |
| `VDD_3V3` | — | Regulated 3.3V rail |
| `VBATT` | — | Raw battery (3.0-4.2V) |
| `VBUS` | — | USB 5V input (from J1) |
| `LED_VIN` | — | External LED power (5-12V, from J6) |
| `GND` | — | Ground |

### 3.3 Power Flags & Net Labels

In KiCad, add `PWR_FLAG` symbols to:
- `VDD_3V3` (where regulator outputs)
- `VBATT` (at battery connector)
- `GND` (at ground connection)

This prevents ERC errors.

---

## 4. Power System Design

### 4.1 Power Requirements (From `power_mgmt.h`)

| State | Current Draw | Duration per Cycle | Source |
|-------|-------------|-------------------|--------|
| SYSTEM_OFF (Deep Sleep) | 0.9 µA | 59 seconds | `power_mgmt.h` line 39 |
| SYSTEM_ON_LP (Idle) | 2.5 µA | When waiting | `power_mgmt.h` line 30 |
| SYSTEM_ON_CL (Constant Latency) | 15 µA | During sensor read | `power_mgmt.h` line 35 |
| ACTIVE_RADIO (TX/RX) | 8.5 mA | ~20ms per transmission | `power_mgmt.h` line 43 |
| SHT4x Measurement | 0.4 mA | 8ms | Datasheet |
| TSL2591 Measurement | 0.6 mA | 100ms | Datasheet |

### 4.2 Battery Life Calculation

```
Per 60-second cycle:
  Sleep:      0.9µA × 59s     = 53.1 µAs
  Sensor:     0.5mA × 0.1s    = 50.0 µAs
  Radio TX:   8.5mA × 0.02s   = 170.0 µAs
  ─────────────────────────────────────
  Total per cycle:             = 273.1 µAs

Average current: 273.1 / 60 = 4.55 µA

18650 battery capacity: 3000 mAh
Battery life: 3000mAh / 0.00455mA = 659,340 hours = 75 years (theoretical)

With 50% derating for self-discharge and aging:
Practical battery life: ~10+ years
```

### 4.3 Voltage Regulator Selection

**Recommended: TPS62740 (Ultra-Low Iq Buck Converter)**

| Parameter | Value | Why It Matters |
|-----------|-------|---------------|
| Input range | 2.2V - 5.5V | Covers full 18650 range (2.5V-4.2V) |
| Output | 3.3V (adjustable) | nRF52840 nominal |
| Quiescent current | 360 nA | Critical for 7-year battery life |
| Max output current | 300 mA | Enough for MCU + sensors + brief LED test |
| Efficiency at 10µA | 90%+ | Most of the time we're in sleep |
| Package | DSBGA-9 (1.6×1.6mm) | Tiny footprint |

**Alternative: TPS63001 (Buck-Boost)**
- Use if you need to extract every mAh from the 18650
- Works down to 1.8V input (vs 2.2V for buck-only)
- Higher Iq (50µA) — acceptable if LED driving is primary use

### 4.4 Regulator Circuit

```
VBATT ──┬── C18 (4.7µF) ── GND
        │
        ├── TPS62740
        │   ├── VIN ── VBATT
        │   ├── VOUT ── VDD_3V3
        │   ├── EN ── VBATT (always on)
        │   ├── SW ──┤ L1 (2.2µH) ├── VOUT
        │   ├── VSEL1 = HIGH ┐
        │   ├── VSEL2 = HIGH │ All HIGH = 3.3V output
        │   ├── VSEL3 = HIGH │ (see TPS62740 Table 1)
        │   ├── VSEL4 = HIGH ┘
        │   ├── PG ──┤ R7 (10kΩ) ├── VDD_3V3 (power good)
        │   └── GND
        │
        └── VDD_3V3 ──┬── C19 (10µF) ── GND
                       ├── FB1 (600Ω ferrite) ── AVDD_3V3 (analog)
                       ├── To nRF52840
                       ├── To SHT4x
                       ├── To TSL2591
                       └── To I2C pull-ups

⚠ CRITICAL LAYOUT RULES:
- Input cap C18 within 3mm of VIN pin
- Output cap C19 within 3mm of VOUT pin
- Inductor L1 as close as possible to SW and VOUT
- Keep the SW-L1-VOUT loop area MINIMAL
- Solid ground plane under entire regulator area
- No signal traces routed under or near the switching node
- Ferrite bead FB1 isolates switching noise from ADC supply
```

### 4.4a Battery Charger Circuit (BQ24075)

> [!NOTE]
> The BQ24075 provides power-path management: system runs from USB when
> available, automatically switching to battery when USB is disconnected.
> This prevents battery wear during development/testing. Lesson from
> A professional's experience: always plan for both powered and battery operation.

```
USB VBUS (5V) ──── F1 (500mA PTC) ──┬── BQ24075
                                     │   ├── IN ── VBUS (after fuse)
     D3 (Schottky)                   │   ├── OUT ── VSYS (to TPS62740 VIN)
     ├──── VBATT ─── BAT pin ────────┤   ├── BAT ── VBATT (to 18650)
                                     │   ├── ISET ── R8 (1.2kΩ to GND) → 742mA
                                     │   ├── ILIM ── R9 (10kΩ to GND) → 500mA
                                     │   ├── TS ── R10 (10kΩ NTC) → battery temp
                                     │   ├── CE ── VDD_3V3 (charge enable)
                                     │   ├── PGOOD ── LED2 (charge indicator)
                                     │   └── GND
                                     │
                                     └── C20 (10µF) ── GND

Power Flow:
  USB connected:  VBUS → F1 → BQ24075 → VSYS → TPS62740 → VDD_3V3
                                      └→ BAT (charging 18650)
  USB disconnected: VBATT → BQ24075 VSYS → TPS62740 → VDD_3V3
```

### 4.5 LED Power Consideration

The grow LEDs (Cree XP-E2) draw significant current:
- Blue LED: ~350mA @ 3.0V forward voltage = **1.05W**
- Red LED: ~350mA @ 2.2V forward voltage = **0.77W**

**This CANNOT come from the coin cell / 18650 during normal operation.**

Options:
1. **Separate LED power input** via J6 connector (5-12V dedicated supply)
2. **PWM duty cycle limiting** — firmware already does this
3. **For prototype/demo:** Brief LED pulses only (< 100ms), acceptable from 18650

Add a **dedicated LED power rail** with reverse protection:

```
LED_VIN (5V external) ──┬── Schottky diode ── LED_5V
                        └── TVS (SMAJ5.0A)

LED_5V ──┬── Q1 (N-MOSFET) ── Blue LED ── R_sense
         └── Q2 (N-MOSFET) ── Red LED ── R_sense
              │
         Gate ── PWM_BLUE / PWM_RED (from nRF52840)
```

---

## 5. nRF52840 MCU Circuit

### 5.1 Decoupling (Corrected Per Nordic Spec v1.8 §6.6)

> [!IMPORTANT]
> These values are corrected from v1.0 of this spec. DEC4 uses dual-cap
> (1µF + 47nF), not single 4.7µF. VDDH is 4.7µF.

```
Pin         Cap Value        Ref    Distance   Notes
──────────────────────────────────────────────────────────────
VDDH        4.7µF X5R        C1     < 3mm     Main supply input
VDD (×4)    100nF X7R each   C2-C5  < 2mm     One per VDD pin
DEC1        100nF X7R        C6     < 1mm     Internal reg output
DEC2        NC               —               Leave floating
DEC3        100nF X7R        C9     < 1mm     Internal regulator
DEC4        1µF + 47nF       C7,C8  < 2mm     REG1 1.3V output
DEC5        1µF X5R          C10    < 1mm     DC/DC (build <Fxx)
DEC6        4.7µF X5R        C11    < 2mm     DC/DC bulk
DECUSB      4.7µF X5R        C12    < 3mm     Internal USB LDO
GPIO        1µF X7R          C13    < 3mm     GPIO port decouple
```

### 5.1a Thermal Pad (Exposed Pad) Connection

> [!CAUTION]
> The nRF52840 aQFN-73 has an exposed thermal/ground pad on the bottom.
> This pad **MUST** be soldered to GND with thermal vias for proper heat
> dissipation and RF ground return. Failure causes overheating and poor
> radio performance.

```
Thermal Via Pattern (under nRF52840 epad):
┌─────────────────┐
│ ○  ○  ○  ○      │   ○ = thermal via (0.3mm drill, 0.6mm pad)
│                  │
│ ○  ○  ○  ○      │   Minimum: 9 vias in 3×3 grid
│                  │   Recommended: 16 vias in 4×4 grid
│ ○  ○  ○  ○      │   Connected to Layer 2 solid GND plane
│                  │
│ ○  ○  ○  ○      │   Via pitch: ~1.2mm
└─────────────────┘   Fill epad region with solder paste (70-80%)
```

### 5.2 Crystal Circuits

**32MHz Main Crystal (Y1):**
```
         12pF (C14)
P0.00 ──┤├── GND
  │
  ├── XTAL (32MHz) ──┤
  │                   │
P0.01 ──┤├── GND     │
         12pF (C15)    │

Layout Rules:
- Traces < 8mm total
- Guard ring (GND pour) around crystal
- NO other traces in this zone
- Solid ground plane underneath
- No vias under crystal footprint
```

**32.768kHz RTC Crystal (Y2):**
```
XC1 ──┤├── GND      ←── 6.8pF (C16)
  │
  ├── XTAL (32.768kHz)
  │
XC2 ──┤├── GND      ←── 6.8pF (C17)

- Even MORE sensitive than 32MHz
- Keep traces < 5mm
- Must be on same layer as nRF52840
- Stray capacitance affects accuracy
```

### 5.3 Reset Circuit

```
VDD_3V3 ──┤ 10kΩ ├──┬── nRF52840 P0.18 (RESET)
                     │
                     ├── 100nF ── GND (debounce)
                     │
                     └── Tactile switch ── GND
```

### 5.4 Boot/DFU Button (Optional)

For firmware update via USB DFU:
```
VDD_3V3 ──┤ 10kΩ ├──┬── nRF52840 P0.19 (configurable)
                     │
                     └── Tactile switch ── GND

Press during reset → enters DFU bootloader
```

---

## 6. Sensor Circuits

### 6.1 I2C Bus Design (From Device Tree Overlay)

```
Pin Assignment (from overlay lines 92-93):
  SDA = P0.26 (NRF_PSEL(TWIM_SDA, 0, 26))
  SCL = P0.27 (NRF_PSEL(TWIM_SCL, 0, 27))
  Speed = I2C_BITRATE_STANDARD (100 kHz)

Bus Configuration:
                    R3 (4.7kΩ)    R4 (4.7kΩ)
  VDD_3V3 ──────────┤              ├──────── VDD_3V3
                     │              │
  P0.26 (SDA) ──────┼──────────────┤
                     │              │
                     ├── SHT4x SDA ├── TSL2591 SDA
                     │              │
  P0.27 (SCL) ──────┼──────────────┤
                     │              │
                     ├── SHT4x SCL ├── TSL2591 SCL
                     │              │
                    GND            GND
```

**Pull-up Resistor Selection:**
- 4.7kΩ is correct for 100kHz I2C at 3.3V
- For 400kHz (fast mode): use 2.2kΩ
- Only ONE set of pull-ups on the bus (not per device)

### 6.2 SHT4x Circuit (Address 0x44)

From device tree overlay line 69: `reg = <0x44>`

```
       ┌──────────┐
       │  SHT4x   │
       │          │
 SDA ──┤ SDA  VDD ├── VDD_3V3
       │          │     │
 SCL ──┤ SCL  VSS ├── GND
       │          │     ┤ C23 (100nF)
       └──────────┘     │
                       GND

CRITICAL:
- Decoupling cap C11 within 2mm of VDD pin
- Keep AWAY from heat sources (regulator, LEDs, MCU)
- Direct airflow path through enclosure ventilation grilles
- Avoid routing power traces under sensor (thermal coupling)
- If possible, route on thermal isolation slot (milled slot in PCB)
```

**Thermal Isolation Strategy:**
```
          ┌─────── Thermal slot (routed slot in PCB) ──────┐
          │                                                  │
  [Main PCB area]    [SHT4x on isolated peninsula]
  [MCU, regulator]   [Connected only by narrow bridge]
  [LEDs, etc.]       [with I2C + power traces]
          │                                                  │
          └──────────────────────────────────────────────────┘

This prevents heat from MCU/LEDs from affecting temperature reading.
Accuracy requirement: ±0.1°C (from project spec)
```

### 6.3 TSL2591 Circuit (Address 0x29)

From device tree overlay lines 74-78: `reg = <0x29>`, `int-gpios = <&gpio0 15 GPIO_ACTIVE_LOW>`

```
       ┌──────────┐
       │ TSL2591  │
       │          │
 SDA ──┤ SDA  VDD ├── VDD_3V3
       │          │     │
 SCL ──┤ SCL  GND ├── GND     ┤ C24 (1µF low-ESR)
       │          │            │
       │  INT     ├── P0.15   GND
       └──────────┘
            │
        R11 (10kΩ) pull-up to VDD_3V3
        (internal pull on nRF52840 also acceptable)

CRITICAL:
- Light sensor MUST face upward through LED window in enclosure
- Enclosure has 15mm LED window (enclosure_gen.scad line 105)
- No components above TSL2591 that would cast shadows
- Consider light pipe or clear epoxy over sensor
- Keep traces away from sensor aperture area
```

---

## 7. LED Driver Circuit

### 7.1 PWM Configuration (From Device Tree Overlay)

```
Pin Assignment (overlay lines 107-108):
  PWM_CH0 (Blue) = P0.13 (NRF_PSEL(PWM_OUT0, 0, 13))
  PWM_CH1 (Red)  = P0.14 (NRF_PSEL(PWM_OUT1, 0, 14))
  Period = 20ms (50Hz) (overlay line 40: PWM_MSEC(20))
  Polarity = INVERTED (active low)
```

### 7.2 MOSFET LED Driver

```
                              LED_VIN (5V or 12V external)
                                │
                          ┌─────┴─────┐
                          │  Blue LED │ (Cree XP-E2, 450nm)
                          │  (D1)     │
                          └─────┬─────┘
                                │
                          R5 (varies by LED, sets current)
                                │
                          ┌─────┴─────┐
  PWM_BLUE (P0.13) ──┤── │ Gate      │
                     │   │  SI2302   │ (N-ch MOSFET)
                     │   │  Drain    │ ← LED cathode
              10kΩ   │   │  Source   │ ── GND
              pull-  │   └───────────┘
              down   │
               │     │
              GND   GND

Same circuit repeated for Red LED on PWM_RED (P0.14).

Component Values:
- R_LED = (V_supply - V_forward) / I_LED
- Blue: R = (5V - 3.0V) / 0.350A = 5.7Ω → use 5.6Ω (1W resistor!)
- Red:  R = (5V - 2.2V) / 0.350A = 8.0Ω → use 8.2Ω (1W resistor!)

⚠ These resistors dissipate significant heat!
Alternative: Use a constant-current LED driver IC (e.g., AL8860)
```

### 7.3 Constant Current LED Driver (AL8860) — RECOMMENDED

> [!WARNING]
> The AL8860 has a **minimum input voltage of 4.5V**. It **cannot** be
> powered from the 3.3V VDD_3V3 rail or directly from the 18650 battery
> (max 4.2V). The AL8860 VIN **must** connect to the `LED_VIN` rail via
> connector J6 (5-12V external supply).

For production boards, replace the MOSFET + resistor with:

```
LED_VIN (5-12V, from J6) ──┬── C27 (10µF, 25V) ── GND
                            │
                            ├── AL8860 (U7, Blue channel)
                            │   ├── VIN ── LED_VIN (NOT VDD_3V3!)
                            │   ├── SW ── L2 (33µH) ── D1 anode (Blue)
                            │   ├── CTRL ── PWM_BLUE (P0.13)
                            │   ├── RS ── R20 (0.1Ω) ── GND
                            │   │          → Iout = 0.1V / 0.1Ω = 1A
                            │   └── GND ── C29 (47µF) ── LED cathode
                            │
                            └── AL8860 (U8, Red channel)
                                ├── VIN ── LED_VIN
                                ├── SW ── L3 (33µH) ── D2 anode (Red)
                                ├── CTRL ── PWM_RED (P0.14)
                                ├── RS ── R21 (0.1Ω) ── GND
                                └── GND ── C30 (47µF) ── LED cathode

Benefits:
- 97% efficiency (vs ~60% with resistor)
- No heat dissipation on current-sense resistor
- Stable current regardless of LED temperature
- Dimming via PWM on CTRL pin (drive <0.2V to disable)
- R22-R23 (10kΩ pull-down) ensure LEDs OFF at power-up
```

---

## 8. Radio & Antenna

### 8.1 nRF52840 RF Matching (From Nordic Reference)

The nRF52840 requires a specific matching network for the 2.4GHz antenna:

```
                    L4 (3.9nH)
ANT pin ──┤├──┬──────────── Antenna Feed
              │
              C31 (0.8pF)  ← Shunt to GND (required per Nordic AN-032)
              │
             GND

Nordic's recommended matching network values (AN-032):
- For PCB antenna: L4=3.9nH series, C31=0.8pF shunt
- For u.FL connector: 50Ω trace to connector, matching network per datasheet

Component specs:
- L4: Murata LQW15AN3N9C00 (3.9nH, 0402, SRF > 6GHz)
- C31: Murata GJM1555C1HR80 (0.8pF, 0402, C0G)
```

### 8.2 Antenna Options

**Option A: PCB Trace Antenna (Recommended for Cost)**
```
- Inverted-F antenna (IFA) on PCB edge
- FREE (no component cost)
- Requires keepout zone on ground plane
- Nordic provides reference design in nRF52840 DK
- Performance: -3 to 0 dBi typical

Layout Rules:
┌────────────────────────────────────────┐
│                                        │
│  [Components]    [Ground plane]        │
│                                        │
│                  ┌─── Antenna keepout ──┤
│                  │  (no copper, no      │
│                  │   components, no     │
│                  │   traces in this     │
│                  │   zone)              │
│                  │                      │
│                  │  ┌── IFA trace ──┐   │
│                  │  │               │   │
│                  └──┘               │   │
│                                     │   │
└─────────────────────────────────────────┘
```

**Option B: u.FL Connector (For External Antenna)**
```
- u.FL/IPEX connector on board edge
- Allows external antenna (higher gain, better range)
- Useful for nodes mounted inside metal enclosures
- Add 0Ω resistor to select between PCB antenna and u.FL
```

### 8.3 RF Layout Rules

1. **50Ω trace impedance** from matching network to antenna
2. **Solid ground plane** under RF trace (no splits!)
3. **Ground via stitching** every 2mm along RF trace edges
4. **No signal traces** crossing under the antenna element
5. **Antenna keepout zone**: No copper (any layer) within 5mm of antenna
6. **Place matching components** directly adjacent to ANT pin (< 2mm)

---

## 9. Battery Monitoring Circuit

### 9.1 Voltage Divider (From Device Tree Overlay)

From overlay lines 49-54:
```
battery_adc {
    compatible = "voltage-divider";
    io-channels = <&adc 0>;
    output-ohms = <1000000>;         // R_bottom = 1MΩ (gated divider)
    full-ohms = <(1000000 + 1000000)>; // R_top + R_bottom = 2MΩ
};
```

**Circuit (Gated Divider — Low Power):**

> [!IMPORTANT]
> The original always-on 100kΩ divider drew 21µA continuously — 24× more
> than the MCU's 0.9µA sleep current. This gated design uses a P-MOSFET
> to enable the divider only during ADC reads, reducing average divider
> current to ~0.035µA.

```
                    Q4 (P-MOSFET, e.g. DMG2305UX)
VBATT ──────────┤S     D├──┬── R1 (1MΩ) ──┬── AIN0 (P0.02)
                │  Gate  │  │              │
         R30    │        │  │         R2 (1MΩ)
       (100kΩ)  │        │  │              │
         │      │        │  │             GND
BAT_EN ──┴──────┘        │  │
(P0.03, GPIO)            │  └── C33 (100nF) ── GND  (anti-alias)
                         │
                        GND

Operation:
  1. Set P0.03 LOW  → Q4 turns ON → divider energized
  2. Wait 1ms (RC settling: 1MΩ × 100nF = 100µs, use 10τ)
  3. Read ADC (12-bit)
  4. Set P0.03 HIGH → Q4 turns OFF → zero divider current

Divider math (1MΩ + 1MΩ):
  Ratio: 0.5
  Always-on current: 0 µA (gated off in sleep)
  During read: 4.2V / 2MΩ = 2.1µA × 1ms = negligible

ADC Configuration (from overlay lines 119-126):
  Gain: ADC_GAIN_1_6 (÷6)
  Reference: ADC_REF_INTERNAL (0.6V)
  Resolution: 12-bit (4096 levels)
  Input: NRF_SAADC_AIN0

Voltage calculation:
  V_battery = (ADC_raw / 4096) × 0.6V × 6 × 2 = ADC_raw × 1.758mV
```

**Component Selection:**
- Use **1% tolerance** resistors for accuracy
- Use **1MΩ** value (gated) — zero standby drain
- Q4: DMG2305UX P-MOSFET (SOT-23, Vgs(th) < 1V, Rds(on) < 100mΩ)
- R30 (100kΩ): pull-up ensures divider is OFF when GPIO is floating/reset
- C33 (100nF): anti-aliasing filter on ADC input

### 9.2 Battery Protection

Add a **DW01A + FS8205** battery protection IC (standard for 18650):

```
VBATT ──┬── DW01A
        │   ├── CS (current sense)
        │   ├── OD (overdischarge gate)
        │   ├── OC (overcharge gate)
        │   └── GND
        │
        └── FS8205 (dual N-MOSFET)
            └── Protects against:
                - Over-discharge (< 2.4V cutoff, ±0.1V)
                - Over-charge (> 4.25V cutoff)
                - Short circuit (> 3A cutoff)
                - Reverse polarity
```

---

## 10. Programming & Debug Interface

### 10.1 SWD Header (2×5 1.27mm Cortex Debug)

```
Pin Layout (standard ARM Cortex 10-pin):
┌────────────────┐
│ 1  VDD_3V3     │ ● ○ │ 2  SWDIO   │
│ 3  GND         │ ● ○ │ 4  SWDCLK  │
│ 5  GND         │ ● ○ │ 6  SWO     │
│ 7  NC          │ ● ○ │ 8  NC      │
│ 9  GND         │ ● ○ │ 10 RESET   │
└────────────────┘

Works with:
- J-Link (recommended for nRF52840)
- CMSIS-DAP probes
- ST-Link (with adapter)
```

### 10.2 UART Debug Header (From Overlay)

From overlay lines 135-139: `current-speed = <115200>`

```
Pin Layout (4-pin 2.54mm header):
┌──────────┐
│ 1  VDD   │ (reference only, do NOT power board from here)
│ 2  TX    │ (P0.06 → to USB-UART adapter RX)
│ 3  RX    │ (P0.08 ← from USB-UART adapter TX)
│ 4  GND   │
└──────────┘

Baud rate: 115200
Used for: LOG_INF, LOG_WRN, LOG_ERR output (Zephyr logging)
```

---

## 11. PCB Layout Strategy

### 11.1 Component Placement Priority

```
Step 1: Place nRF52840 FIRST (center of board)
        └── All other placement radiates from MCU

Step 2: 32MHz crystal + load caps
        └── Within 5mm of XOSC pins, guard ring

Step 3: 32.768kHz crystal + load caps
        └── Within 5mm of XC pins

Step 4: Decoupling capacitors
        └── Each cap within 2mm of its VDD pin

Step 5: Antenna / u.FL connector
        └── Board edge, away from battery/ground plane

Step 6: Voltage regulator + inductor + caps
        └── Near battery connector, away from sensors

Step 7: SHT4x sensor
        └── Board edge, away from heat sources
        └── Near ventilation grille in enclosure

Step 8: TSL2591 light sensor
        └── Top side, unobstructed, near LED window

Step 9: LED driver MOSFETs
        └── Away from sensors (heat source!)

Step 10: Connectors (USB, SWD, battery, I2C ext)
         └── Board edges, matching enclosure cutouts
```

### 11.2 Placement Floorplan

```
        ┌─────────── 64mm (PCB width) ──────────┐
        │                                         │
        │  ┌─USB─┐                               │
   ┌────┤  └─────┘  ┌──────────┐                 ├── SHT4x
   │    │            │  nRF52840│  ┌──── Y1 ──┐  │   (thermal
   │    │  ┌─REG─┐  │  (aQFN-73) │  │  32MHz    │  │    island)
   │    │  │TPS    │ │          │  └──────────┘  │
   │    │  │62740  │ │  ┌─────┐│                 │
 100mm  │  └──────┘  │  │DeCap││   Y2 (32kHz)   │
   │    │            │  └─────┘│                 │
   │    │  ┌──BAT──┐ └────────┘                  │
   │    │  │Conn   │                              │
   │    │  │(JST)  │  ┌─SWD Header─┐  ┌TSL2591┐ │
   │    │  └───────┘  └────────────┘  │(light)│ │
   │    │                              └───────┘ │
   └────│  ┌──── Antenna Zone ────────────────┐  │
        │  │  (keepout - no GND plane!)       │  │
        │  │  IFA or u.FL                     │  │
        │  └──────────────────────────────────┘  │
        └─────────────────────────────────────────┘
```

### 11.3 Routing Priority

```
Priority 1 (FIRST): RF matching network → Antenna
  - 50Ω controlled impedance
  - Ground via stitching

Priority 2: Crystal traces (32MHz and 32.768kHz)
  - Keep SHORT (< 8mm)
  - Guard ring with GND pour

Priority 3: Power traces (VBATT, VDD_3V3)
  - Wide traces: 0.5mm minimum for VDD_3V3
  - Copper pour preferred

Priority 4: I2C bus (SDA, SCL)
  - Route together, same length not critical at 100kHz
  - Keep away from PWM and RF traces

Priority 5: PWM LED signals
  - Route away from I2C and analog signals
  - OK to use thin traces (signal only, not power)

Priority 6: UART, SWD (low speed, not critical)

Priority 7: Battery sense ADC trace
  - Keep away from switching regulator
  - Guard with GND traces on both sides
```

---

## 12. Stackup & Design Rules

### 12.1 Recommended Stackup: 4-Layer

```
Layer 1 (Top):     Signal + Components (1oz copper)
                   ───────────── 0.2mm FR4 prepreg ─────────────
Layer 2 (Inner 1): Ground Plane — SOLID, unbroken (1oz copper)
                   ───────────── 1.0mm FR4 core ────────────────
Layer 3 (Inner 2): Power Plane (VDD_3V3) (1oz copper)
                   ───────────── 0.2mm FR4 prepreg ─────────────
Layer 4 (Bottom):  Signal + Components (1oz copper)

Total thickness: ~1.6mm (standard)

WHY 4-layer for this project:
- Solid ground plane = better RF performance for Thread radio
- Lower EMI = easier FCC/IC certification
- Better signal integrity for I2C
- Cost increase: ~$3 per board (worth it for production)
```

### 12.2 Design Rules for KiCad

```
Net Classes:

Class        | Width  | Clearance | Via Drill | Via Size
─────────────|────────|───────────|───────────|──────────
Default      | 0.15mm | 0.15mm   | 0.3mm    | 0.6mm
Power        | 0.5mm  | 0.2mm    | 0.3mm    | 0.6mm
RF           | *calc* | 0.3mm    | 0.3mm    | 0.6mm
I2C          | 0.2mm  | 0.2mm    | 0.3mm    | 0.6mm
LED_Drive    | 0.3mm  | 0.2mm    | 0.3mm    | 0.6mm

* RF trace width calculated for 50Ω:
  4-layer, 0.2mm prepreg (εr=4.2), 1oz copper:
  Width ≈ 0.35mm for 50Ω microstrip

Minimum specs (JLCPCB compatible):
- Min trace/space: 0.1mm / 0.1mm
- Min drill: 0.2mm
- Min annular ring: 0.13mm
- Min solder mask dam: 0.1mm
```

### 12.3 Copper Zones (Fills)

```
Layer 1 (Top): GND fill around all components
  - Provides shielding
  - Via stitch to Layer 2 every 3mm
  - EXCEPT antenna keepout zone

Layer 2 (Inner 1): Solid GND plane
  - NO cuts, NO traces
  - Only break for vias (unavoidable)

Layer 3 (Inner 2): VDD_3V3 plane
  - Cover entire board except antenna zone
  - Via connections to VDD_3V3 pads

Layer 4 (Bottom): GND fill
  - Thermal pad for regulator if needed
  - Via stitch to Layer 2
```

---

## 13. Mechanical Constraints

### 13.1 Enclosure Dimensions (From `enclosure_gen.scad`)

```
Enclosure outer: 85 × 130 × 45 mm (lines 12-14)
Wall thickness:  2.5mm (line 15)
Corner radius:   5mm (line 16)

PCB dimensions: 64 × 100mm (lines 19-20)
  ← Derived from nRF52840 DK dimensions

PCB mounting holes:
  4× M2.5 at corners
  Offset 5mm from PCB edges (lines 121-124)
  Post height: 5mm above enclosure floor (line 117)
  Hole diameter: 2.5mm (line 118)

Mounting hole coordinates (relative to PCB center):
  (-27mm, -45mm)  (+27mm, -45mm)
  (-27mm, +45mm)  (+27mm, +45mm)
```

### 13.2 Connector Placement (Match Enclosure Cutouts)

```
USB Port:
  - Bottom edge of PCB, centered (enclosure line 84)
  - Cutout: 12mm × 7mm with rounded corners
  - PCB USB connector must align with enclosure wall

Sensor Port:
  - Right edge of PCB, centered (enclosure line 97-100)
  - Cutout: 8mm diameter circle
  - For external I2C sensor cable

Cable Gland:
  - Bottom edge, offset left (enclosure line 198)
  - M12 cable gland (12mm diameter)
  - For external LED power cable

LED Window:
  - Top edge of PCB, centered (enclosure line 106)
  - Window: 15mm width
  - TSL2591 light sensor should face this window
```

### 13.3 Battery Clearance

```
18650 battery: 19mm diameter × 68mm length (lines 21-22)
Battery cradle in upper portion of enclosure (line 138)
PCB must NOT overlap with battery space

Board clearance zones:
┌─────────── 85mm enclosure ───────────┐
│                                       │
│  ┌──── 64mm PCB ────┐                │
│  │                   │  ┌──────────┐ │
│  │                   │  │ 18650    │ │
│  │  [components]     │  │ Battery  │ │
│  │                   │  │ (19×68)  │ │
│  │                   │  │          │ │
│  └───────────────────┘  └──────────┘ │
│                                       │
└───────────────────────────────────────┘
```

---

## 14. Fabrication & Assembly

### 14.1 PCB Specifications for Ordering

| Parameter | Value |
|-----------|-------|
| **Layers** | 4 |
| **Dimensions** | 64 × 100mm |
| **Thickness** | 1.6mm |
| **Copper weight** | 1oz (35µm) all layers |
| **Surface finish** | ENIG (for QFN pads) |
| **Solder mask** | Green (or matte black) |
| **Silkscreen** | White |
| **Min trace/space** | 0.15mm / 0.15mm |
| **Min drill** | 0.3mm |
| **Impedance control** | Yes (50Ω RF trace) |

**Estimated cost per board (JLCPCB, qty 10):** ~$8-12 USD

### 14.2 Assembly Notes

**aQFN-73 Soldering (nRF52840):**
- REQUIRES reflow oven or hot air station
- Stencil paste application recommended
- Inspect for solder bridges under QFN with X-ray (production)
- Thermal pad MUST be soldered to ground plane

**Hand-Solderable Components:**
- All 0402 passives (with practice)
- SOT-23 MOSFETs
- JST connectors
- Pin headers

**Reflow Required:**
- nRF52840 (aQFN-73)
- SHT4x (DFN-4)
- TSL2591 (DFN-6)
- TPS62740 (DSBGA-9) — WARNING: BGA requires stencil!

### 14.3 Test Points

Add test points (1.5mm exposed pad) for:

| Test Point | Signal | Purpose |
|------------|--------|---------|
| TP1 | VDD_3V3 | Verify regulator output |
| TP2 | VBATT | Measure battery voltage |
| TP3 | GND | Probe ground reference |
| TP4 | I2C_SDA | Debug I2C communication |
| TP5 | I2C_SCL | Debug I2C communication |
| TP6 | PWM_BLUE | Verify PWM output |
| TP7 | PWM_RED | Verify PWM output |
| TP8 | ANT | RF signal measurement |
| TP9 | VBATT_SENSE | Verify ADC input |
| TP10 | RESET | Manual reset access |

### 14.4 Gerber Checklist

Before submitting to fab:

- [ ] Board outline on Edge.Cuts layer
- [ ] 4 mounting holes (2.5mm drill, plated, connected to GND)
- [ ] Fiducials (3× minimum, 1mm diameter, on Top + Bottom)
- [ ] Silkscreen: component references, pin 1 dots, polarity marks
- [ ] Silkscreen: board name "G.O.S. PHY v1.0", date, QU logo
- [ ] No unconnected nets (ratsnest clear)
- [ ] DRC clean (zero errors)
- [ ] 3D model verified (no component collisions)
- [ ] Antenna keepout zone verified
- [ ] Impedance control notes in fab drawing

---

## 15. KiCad Project Setup

### 15.1 Project File Structure

```
gos_sensor_node/
├── gos_sensor_node.kicad_pro          (Project file)
├── gos_sensor_node.kicad_sch          (Root schematic)
├── Power.kicad_sch                     (Power sub-sheet)
├── MCU.kicad_sch                       (nRF52840 sub-sheet)
├── Sensors.kicad_sch                   (I2C sensors sub-sheet)
├── LEDs.kicad_sch                      (LED drivers sub-sheet)
├── Radio.kicad_sch                     (Antenna sub-sheet)
├── Connectors.kicad_sch                (All connectors sub-sheet)
├── gos_sensor_node.kicad_pcb          (PCB layout)
├── libraries/
│   ├── gos_symbols.kicad_sym          (Custom symbols)
│   └── gos_footprints.pretty/         (Custom footprints)
│       ├── nRF52840_aQFN73.kicad_mod
│       ├── SHT4x_DFN4.kicad_mod
│       ├── TSL2591_DFN6.kicad_mod
│       ├── IFA_2.4GHz.kicad_mod       (PCB antenna)
│       └── 18650_Holder.kicad_mod
├── 3d_models/
│   ├── nRF52840.step
│   ├── SHT4x.step
│   └── 18650_holder.step
├── fabrication/
│   ├── gerbers/
│   ├── BOM.csv
│   ├── pick_and_place.csv
│   └── assembly_drawing.pdf
└── docs/
    ├── schematic.pdf
    └── design_review_checklist.md
```

### 15.2 KiCad Net Class Setup

In Board Setup → Design Rules → Net Classes:

```
Net Class: Default
  Track Width: 0.15mm
  Clearance: 0.15mm
  Via Size: 0.6mm
  Via Drill: 0.3mm

Net Class: Power
  Members: VDD_3V3, VBATT, LED_VIN
  Track Width: 0.5mm
  Clearance: 0.2mm

Net Class: RF
  Members: ANT, RF_MATCH
  Track Width: 0.35mm (calculated for 50Ω)
  Clearance: 0.3mm

Net Class: I2C
  Members: I2C0_SDA, I2C0_SCL
  Track Width: 0.2mm
  Clearance: 0.2mm

Net Class: Sensitive_Analog
  Members: VBATT_SENSE
  Track Width: 0.2mm
  Clearance: 0.25mm
```

### 15.3 Design Rule Check Config

```
Minimum values:
  Copper clearance: 0.15mm
  Track width: 0.1mm
  Via diameter: 0.6mm
  Via drill: 0.3mm
  Annular ring: 0.13mm
  Silkscreen width: 0.12mm
  Silkscreen clearance: 0.05mm
  Courtyard to courtyard: 0.25mm
  Edge clearance: 0.3mm

Copper zones:
  Clearance: 0.3mm
  Min width: 0.2mm
  Thermal relief spoke width: 0.3mm
  Thermal relief gap: 0.3mm
```

---

## Summary — What You Have & What You Need

### ✅ Already Defined in Project Code

| Item | Source | Status |
|------|--------|--------|
| MCU pin assignments | `nrf52840_phytotron.overlay` | ✅ Complete |
| Sensor I2C addresses | Device tree overlay | ✅ 0x44, 0x29 |
| PWM configuration | Overlay + `main.c` | ✅ 50Hz, inverted |
| ADC configuration | Overlay | ✅ AIN0, 12-bit, 1/6 gain |
| Power states | `power_mgmt.h` | ✅ 0.9µA to 8.5mA |
| LED wavelengths | `spectral_opt.py` | ✅ 450nm, 660nm |
| Enclosure dimensions | `enclosure_gen.scad` | ✅ 85×130×45mm |
| PCB mount positions | `enclosure_gen.scad` | ✅ 4× M2.5 |
| Protocol/packet format | `protocol.h` | ✅ 18-byte struct |

### 🔧 What You Need to Do in KiCad

| Step | Priority | Effort |
|------|----------|--------|
| Create schematic (7 sheets incl. Protection) | HIGH | 3-4 hours |
| Verify footprints against datasheets | HIGH | 1 hour |
| Place components per floorplan | HIGH | 1-2 hours |
| Route RF trace (50Ω impedance) | CRITICAL | 1 hour |
| Route crystal traces | CRITICAL | 30 min |
| Route power traces (incl. charger) | HIGH | 1.5 hours |
| Route remaining signals | MEDIUM | 1-2 hours |
| Copper fills + via stitching | HIGH | 30 min |
| DRC + ERC clean | HIGH | 30 min |
| Generate Gerbers + BOM | MEDIUM | 30 min |
| **Total estimated time** | | **10-14 hours** |

---

## 16. Design Engineering Insights

> This section documents lessons learned from professional embedded systems
> engineering, including analysis of A professional's portfolio (VEX Robotics,
> FRC, ESP32, STM32, FPGA projects) and industry best practices for PCB design.

### 16.1 I2C Bus Management (From FRC Robot Experience)

**Problem:** Multiple sensors with fixed I2C addresses on a shared bus.
**Example:** REV Color Sensors (all address 0x52) required bus multiplexing.
**Our Solution:** SHT4x (0x44) and TSL2591 (0x29) have unique addresses —
no conflict on this design. However, if J3 external sensor has a conflicting
address, add a TCA9548A I2C multiplexer to the Sensors schematic sheet.

### 16.2 ESD Protection as a Non-Negotiable

**Problem:** GPIO pins damaged by static discharge during testing/assembly.
**Industry Data:** >30% of field failures in consumer electronics trace to ESD.
**Our Solution:** TVS diodes on every external-facing connector (USB, I2C ext,
antenna). Series resistors (100Ω-1kΩ) on exposed GPIOs limit current through
internal protection diodes. PTC fuse on USB VBUS prevents overcurrent.

### 16.3 Hardware Debouncing (From VHDL Debouncer Work)

**Problem:** Mechanical switch bounce causes multiple edge detections.
**Why Hardware:** During RESET, firmware hasn't started — software debounce
cannot help. RC filter (10kΩ + 100nF = 1ms τ) provides reliable debounce.
**VHDL Insight:** Even FPGA designs use multi-stage synchronizers for
metastability; analog RC filtering is the PCB equivalent.

### 16.4 Power-Path Management (From Battery-Powered Design)

**Problem:** Continuously charging/discharging battery during development
reduces cycle life and causes unexpected behavior.
**Our Solution:** BQ24075 power-path management allows system to run
directly from USB while independently charging the battery. This extends
development convenience and battery longevity.

### 16.5 Analog Supply Isolation (From ADC Accuracy Requirements)

**Problem:** Switching regulator noise couples into ADC readings, degrading
battery voltage measurement accuracy.
**Our Solution:** Ferrite bead (FB1, 600Ω@100MHz) between VDD_3V3 and
AVDD_3V3 creates a low-pass filter that attenuates switching noise.
Combined with proper ADC trace guarding (ground traces on both sides),
this ensures clean 12-bit ADC readings.

### 16.6 Thermal Management for Sensor Accuracy

**Problem:** Self-heating from MCU, regulator, and LEDs affects SHT4x
temperature measurement (±0.1°C accuracy target).
**Our Solution:** Thermal isolation slot in PCB (milled slot creating a
peninsula), SHT4x placed at board edge near ventilation grille, no power
traces routed under sensor, and copper pour thermal relief on sensor pads.

### 16.7 Firmware-Hardware Co-Design Principles

From A professional's STM32/FreeRTOS and Zephyr experience:

| Principle | Hardware Implication |
|-----------|---------------------|
| DMA for peripheral I/O | Reserve DMA channels in pin assignment |
| Thread-safe sensor drivers | I2C bus mutex — one set of pull-ups |
| Watchdog timer | Add TP on WDT output for debug |
| Power state machine | EN pin on regulator, CTRL on LED drivers |
| OTA firmware update | USB-C DFU + SWD debug header both required |

---

*G.O.S. Phytotron Sensor Node PCB Design Specification v2.0. All pin
assignments, dimensions, and specifications derived directly from project
source code. Engineering insights from professional embedded systems
practice and A professional's portfolio analysis.*
