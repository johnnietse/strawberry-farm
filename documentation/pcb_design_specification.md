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
       │            │  │ Monitor │    │    (QFN-48)       │   │
       │            │  │ (ADC +  │    │                   │   │
       ├── Boost ───┤  │ divider)│    │ P0.26 ── I2C SDA │───┤── SHT4x (0x44)
       │   3.3V     │  └────┬────┘    │ P0.27 ── I2C SCL │───┤── TSL2591 (0x29)
       │            │       │         │                   │   │
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

### Core Components

| Ref | Component | Part Number | Package | Qty | Purpose |
|-----|-----------|-------------|---------|-----|---------|
| U1 | MCU | **nRF52840-QIAA** | QFN-48 (6×6mm) | 1 | Main processor + radio |
| U2 | Temp/Humidity Sensor | **SHT40-AD1B** | DFN-4 (2.5×2.5mm) | 1 | ±0.1°C, ±1.8% RH |
| U3 | Light Sensor | **TSL2591** | DFN-6 (2×2mm) | 1 | PAR measurement |
| U4 | Voltage Regulator | **TPS62740** | DSBGA-9 (1.6×1.6mm) | 1 | 3.3V buck, 360nA Iq |
| Y1 | Crystal | **NX3225GD-8M** | 3.2×2.5mm | 1 | 32MHz for nRF52840 |
| Y2 | Crystal | **ABS07-32.768KHZ** | 3.2×1.5mm | 1 | 32.768kHz RTC |

### Passive Components

| Ref | Value | Package | Qty | Purpose |
|-----|-------|---------|-----|---------|
| C1-C4 | 100nF X7R | 0402 | 4 | nRF52840 decoupling |
| C5-C6 | 1µF X7R | 0402 | 2 | nRF52840 VDDH, DEC1 |
| C7-C8 | 12pF C0G | 0402 | 2 | 32MHz crystal load |
| C9-C10 | 6.8pF C0G | 0402 | 2 | 32.768kHz crystal load |
| C11 | 100nF X7R | 0402 | 1 | SHT4x decoupling |
| C12 | 100nF X7R | 0402 | 1 | TSL2591 decoupling |
| C13 | 10µF X5R | 0603 | 1 | Regulator input |
| C14 | 10µF X5R | 0603 | 1 | Regulator output |
| C15 | 4.7µF X5R | 0402 | 1 | DEC4 (nRF52840) |
| L1 | 2.2µH | 0603 | 1 | Buck regulator inductor |
| L2 | 10nH | 0402 | 1 | RF matching |
| R1-R2 | 100kΩ 1% | 0402 | 2 | Battery voltage divider |
| R3-R4 | 4.7kΩ | 0402 | 2 | I2C pull-ups |
| R5-R6 | 100Ω | 0402 | 2 | LED current limiting (optional) |

### Connectors & Mechanical

| Ref | Component | Purpose |
|-----|-----------|---------|
| J1 | USB Micro-B or USB-C | Programming & power |
| J2 | 2×5 1.27mm header | SWD debug/programming |
| J3 | 4-pin JST-SH (1mm) | External I2C sensor connector |
| J4 | 2-pin JST-PH (2mm) | Battery connector |
| J5 | u.FL connector (optional) | External antenna |
| BT1 | 18650 holder (Keystone 1042) | Battery cradle |
| — | M2.5 standoffs × 4 | PCB mounting to enclosure |

### LED Components (External or On-Board)

| Ref | Component | Part Number | Wavelength | Purpose |
|-----|-----------|-------------|------------|---------|
| D1 | Blue LED | Cree XP-E2 Blue | 450nm | Vegetative growth |
| D2 | Red LED | Cree XP-E2 Red | 660nm | Flowering/fruiting |
| Q1 | N-MOSFET | SI2302CDS | SOT-23 | Blue LED driver |
| Q2 | N-MOSFET | SI2302CDS | SOT-23 | Red LED driver |

---

## 3. Schematic Design

### 3.1 Complete Schematic Block Structure

Design your KiCad schematic as **hierarchical sheets**:

```
Root Sheet: GOS_SENSOR_NODE.kicad_sch
├── Power.kicad_sch        (Battery, regulator, power flags)
├── MCU.kicad_sch          (nRF52840 + crystal + decoupling)
├── Sensors.kicad_sch      (SHT4x + TSL2591 + I2C bus)
├── LEDs.kicad_sch         (MOSFET drivers + connectors)
├── Radio.kicad_sch        (Antenna matching + u.FL)
└── Connectors.kicad_sch   (USB, SWD, battery, external I2C)
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
| `VBATT_SENSE` | AIN0 (P0.02) | Battery ADC input (through divider) |
| `UART_TX` | P0.06 | Debug UART transmit |
| `UART_RX` | P0.08 | Debug UART receive |
| `SWDCLK` | — | SWD clock (dedicated pin) |
| `SWDIO` | — | SWD data (dedicated pin) |
| `VDD_3V3` | — | Regulated 3.3V rail |
| `VBATT` | — | Raw battery (3.0-4.2V) |
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
VBATT ──┬── C13 (10µF) ── GND
        │
        ├── TPS62740
        │   ├── VIN ── VBATT
        │   ├── VOUT ── VDD_3V3
        │   ├── EN ── VBATT (always on)
        │   ├── SW ──┤ L1 (2.2µH) ├── VOUT
        │   ├── FB ── voltage divider to VOUT
        │   └── GND
        │
        └── VDD_3V3 ──┬── C14 (10µF) ── GND
                       ├── To nRF52840
                       ├── To SHT4x
                       ├── To TSL2591
                       └── To I2C pull-ups

⚠ CRITICAL LAYOUT RULES:
- Input cap C13 within 3mm of VIN pin
- Output cap C14 within 3mm of VOUT pin
- Inductor L1 as close as possible to SW and VOUT
- Keep the SW-L1-VOUT loop area MINIMAL
- Solid ground plane under entire regulator area
- No signal traces routed under or near the switching node
```

### 4.5 LED Power Consideration

The grow LEDs (Cree XP-E2) draw significant current:
- Blue LED: ~350mA @ 3.0V forward voltage = **1.05W**
- Red LED: ~350mA @ 2.2V forward voltage = **0.77W**

**This CANNOT come from the coin cell / 18650 during normal operation.**

Options:
1. **Separate LED power input** via J3 connector (5V USB or dedicated supply)
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

### 5.1 Decoupling (From Nordic Reference Design)

The nRF52840 requires specific decoupling on each power pin:

```
Pin         Cap Value    Distance   Notes
────────────────────────────────────────────────────
VDDH        1µF          < 3mm     Main supply input
VDD (×4)    100nF each   < 2mm     Core supply (one per pin)
DEC1        100nF        < 1mm     Internal regulator output
DEC2        NC                     Leave floating
DEC3        100nF        < 1mm     Internal regulator
DEC4        4.7µF        < 2mm     Internal regulator bulk
DEC5        1µF          < 1mm     DC/DC output (if using)
DEC6        4.7µF        < 2mm     DC/DC bulk (if using)
VBUS        4.7µF        < 3mm     USB VBUS (if used)
```

### 5.2 Crystal Circuits

**32MHz Main Crystal (Y1):**
```
         12pF (C7)
P0.00 ──┤├── GND
  │
  ├── XTAL (32MHz) ──┤
  │                   │
P0.01 ──┤├── GND     │
         12pF (C8)    │

Layout Rules:
- Traces < 8mm total
- Guard ring (GND pour) around crystal
- NO other traces in this zone
- Solid ground plane underneath
- No vias under crystal footprint
```

**32.768kHz RTC Crystal (Y2):**
```
XC1 ──┤├── GND      ←── 6.8pF (C9)
  │
  ├── XTAL (32.768kHz)
  │
XC2 ──┤├── GND      ←── 6.8pF (C10)

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
       │          │     ┤ C11 (100nF)
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
 SCL ──┤ SCL  GND ├── GND     ┤ C12 (100nF)
       │          │            │
       │  INT     ├── P0.15   GND
       └──────────┘
            │
        10kΩ pull-up to VDD_3V3
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

### 7.3 Constant Current LED Driver Alternative

For production boards, replace the MOSFET + resistor with:

```
PWM_BLUE ── AL8860 (350mA CC driver)
              │
              ├── VIN ── LED_VIN
              ├── SW ── Inductor ── LED anode
              ├── EN ── PWM_BLUE (from nRF52840)
              ├── FB ── sense resistor
              └── GND

Benefits:
- 95% efficiency (vs ~60% with resistor)
- No heat dissipation on current-sense resistor
- Stable current regardless of LED temperature
- Dimming via PWM on EN pin
```

---

## 8. Radio & Antenna

### 8.1 nRF52840 RF Matching (From Nordic Reference)

The nRF52840 requires a specific matching network for the 2.4GHz antenna:

```
                    L2 (10nH)
ANT pin ──┤├──┬──────────── Antenna Feed
              │
              C (0.8pF)    ← May be parasitic, depends on layout
              │
             GND

Nordic's recommended matching network values:
- For PCB antenna: Follow Nordic's AN-032 application note
- For u.FL connector: 50Ω trace to connector, matching network per datasheet

Component specs:
- L2: Murata LQW15AN10NJ00 (10nH, 0402, SRF > 3GHz)
- C: May not be needed if PCB antenna is well-tuned
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
    output-ohms = <100000>;         // R_bottom = 100kΩ
    full-ohms = <(100000 + 100000)>; // R_top + R_bottom = 200kΩ
};
```

**Circuit:**
```
VBATT ──┤ R1 (100kΩ) ├──┬── AIN0 (P0.02) ── nRF52840 ADC
                        │
                   ┤ R2 (100kΩ) ├
                        │
                       GND

Divider ratio: 0.5
ADC range: 0 - 3.6V (with 1/6 gain, internal ref = 0.6V)
Measurable battery range: 0 - 7.2V (covers full 18650 range)

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
- Use **100kΩ** value to minimize battery drain: I = 4.2V / 200kΩ = **21 µA**
- Add **100nF cap** across R2 for noise filtering (optional, adds settling time)

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
                - Over-discharge (< 2.5V cutoff)
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
   │    │  ┌─REG─┐  │  (QFN48) │  │  32MHz    │  │    island)
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

**QFN-48 Soldering (nRF52840):**
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
- nRF52840 (QFN-48)
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
│       ├── nRF52840_QFN48.kicad_mod
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
| Create schematic (6 sheets) | HIGH | 2-3 hours |
| Verify footprints against datasheets | HIGH | 1 hour |
| Place components per floorplan | HIGH | 1-2 hours |
| Route RF trace (50Ω impedance) | CRITICAL | 1 hour |
| Route crystal traces | CRITICAL | 30 min |
| Route power traces | HIGH | 1 hour |
| Route remaining signals | MEDIUM | 1-2 hours |
| Copper fills + via stitching | HIGH | 30 min |
| DRC + ERC clean | HIGH | 30 min |
| Generate Gerbers + BOM | MEDIUM | 30 min |
| **Total estimated time** | | **8-12 hours** |

---

*PCB design specification for the G.O.S. Phenotyping Platform sensor node. All pin assignments, dimensions, and specifications derived directly from project source code.*
