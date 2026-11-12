# G.O.S. Sensor Node — PCB Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the G.O.S. Phytotron Sensor Node from early schematic skeletons to a fully routed, DRC-clean, fabrication-ready 4-layer PCB.

**Architecture:** Hierarchical KiCad 9.0 design with 7 sub-sheets (Power, MCU, Sensors, Radio, Protection, LEDs, Connectors) feeding into a root sheet. 4-layer PCB stackup (Signal-GND-PWR-Signal) at 64×100mm. nRF52840 MCU with Thread/BLE radio, SHT4x+TSL2591 sensors, AL8860 LED drivers, TPS62740 regulator, BQ24075 charger.

**Tech Stack:** KiCad 9.0, KiCad MCP tools (SWIG/IPC backend), Python for batch generation if needed.

## Global Constraints

- All schematic sheets must be ERC-clean (0 errors, 0 warnings)
- Board dimensions: 64×100mm ± 0.1mm
- Layer stackup: 4-layer (F.Cu, GND, PWR, B.Cu), 1.6mm total
- All values per PCB design spec v2.0 (see docs/pcb_design_specification.md)
- Net classes: Default (0.15/0.15), Power (0.5/0.2), RF (50Ω calc'd/0.3), I2C (0.2/0.2), Sensitive_Analog (0.2/0.25)
- JLCPCB-compatible design rules (min trace 0.15mm, min drill 0.3mm)

---

## Task 1: Fix Power.kicad_sch — Add Passives + Wire BQ24075 + TPS62740 + DW01A

**Files:**
- Modify: `pcbs/gos_sensor_node/power.kicad_sch`

**Goal:** Take the existing BQ24075 U5, TPS62740 U4, DW01A U6 skeletons and fully populate with all BOM passives, wiring, and hierarchical labels.

**Components to add:** R7 (10k), R8 (1.2k), R9 (10k), R10 (10k NTC), R1 (1M), R2 (1M), C18 (4.7uF/0603), C19 (10uF/0603), C20 (10uF/0603), C21 (10uF/0603), C22 (1uF/0402), L1 (2.2uH), D3 (PMEG2010AEH), D4 (PMEG2010AEH), FB1 (600R), Q4 (DMG2305UX), C33 (100nF), R30 (100k)

- [ ] **1.1: Add all missing passives via batch_add_components**
  - Use kicad_batch_add_components on power.kicad_sch with 19 components
  - Position each near its parent IC using the spec's layout guidance

- [ ] **1.2: Wire BQ24075 circuit**
  - IN ← VUSB (from hierarchical label), ISET → R8→GND, ILIM → R9→GND
  - CE → VDD_3V3 (enable), TS → R10→GND, OUT → VSYS, PGOOD → LED indicator
  - Add C20 (10uF IN), C21 (10uF BAT), C22 (1uF bypass)

- [ ] **1.3: Wire TPS62740 buck circuit**
  - VIN ← VSYS, EN ← VSYS (always on), VOUT → VDD_3V3
  - VSEL1-4 all → HIGH (+3.3V select)
  - SW → L1 (2.2uH) → VOUT
  - PG → R7(10k) → VDD_3V3
  - Add C18 (4.7uF IN), C19 (10uF OUT)
  - FB1 (600R) from VDD_3V3 → AVDD_3V3

- [ ] **1.4: Wire battery monitor (gated divider)**
  - Q4 (DMG2305UX): S ← VBATT, G ← R30(100k)→BAT_EN(hierarchical label), D → divider
  - R1 (1M) top divider, R2 (1M) bottom divider, C33 (100nF) anti-alias
  - Divider midpoint → VBATT_SENSE (hierarchical label)

- [ ] **1.5: Wire DW01A protection circuit**
  - VCC ← VBATT, GND ← GND, OD/OC → FS8205A gates
  - Add FS8205A dual NMOS with proper connections

- [ ] **1.6: Add hierarchical labels** connecting to root sheet:
  - VUSB (input), VSYS (output), VDD_3V3 (output)
  - VBATT (bidirectional), AVDD_3V3 (output)
  - BAT_EN (input), VBATT_SENSE (output)
  - GND (power)

- [ ] **1.7: Add PWR_FLAGs** to VDD_3V3, VBATT, AVDD_3V3

---

## Task 2: Fix MCU.kicad_sch — Proper Decoupling + Crystals + Reset

**Files:**
- Modify: `pcbs/gos_sensor_node/MCU.kicad_sch`

**Goal:** Fix the existing skeleton nRF52840 with correct decoupling (per Nordic PS v1.8 §6.6), crystals, reset circuit, buttons.

- [ ] **2.1: Delete all 13 placeholder caps (all wrong 100nF)** and re-add with correct values:
  - C1: 4.7uF VDDH, C2-C5: 100nF each (VDDx4), C6: 100nF DEC1
  - C7: 1uF DEC4 bulk, C8: 47nF DEC4 HF bypass
  - C9: 100nF DEC3, C10: 1uF DEC5, C11: 4.7uF DEC6
  - C12: 4.7uF DECUSB, C13: 1uF GPIO

- [ ] **2.2: Add crystals + load caps**
  - Y1: NX3225GD (32MHz) + C14(12pF) + C15(12pF) HFXO
  - Y2: ABS07 (32.768kHz) + C16(6.8pF) + C17(6.8pF) LFXO

- [ ] **2.3: Add reset circuit**
  - R18: 10k pull-up to VDD_3V3
  - C25: 100nF debounce
  - SW1: tactile switch to GND

- [ ] **2.4: Add DFU button**
  - R19: 10k pull-up, C26: 100nF debounce
  - SW2: tactile switch to GND

- [ ] **2.5: Add status LEDs**
  - LED1: Green (power) + R28: 1k
  - LED2: Orange (charge) + R29: 1k

- [ ] **2.6: Add hierarchical labels** matching the root sheet:
  - I2C_SDA, I2C_SCL, PWM_BLUE, PWM_RED, TSL_INT
  - BATT_ADC, UART_TX, UART_RX, SWDIO, SWDCLK
  - NRESET, ANT

- [ ] **2.7: Wire decoupling caps** to each VDD/DEC pin with short traces (<2mm)

---

## Task 3: Fix Sensors.kicad_sch — Wire I2C Bus + SHT4x + TSL2591

**Files:**
- Modify: `pcbs/gos_sensor_node/sensors.kicad_sch`

**Goal:** Wire the existing SHT4x and TSL2591 components into a working I2C bus.

- [ ] **3.1: Wire I2C pull-ups**
  - R3(4.7k) + R4(4.7k) from VDD_3V3 to I2C_SDA / I2C_SCL
  - R12(100Ω) + R13(100Ω) series damping on SDA/SCL

- [ ] **3.2: Connect SHT4x (U2)**
  - SDA ← I2C_SDA, SCL ← I2C_SCL
  - VDD ← VDD_3V3, VSS ← GND
  - C23(100nF) decoupling at VDD pin

- [ ] **3.3: Connect TSL2591 (U3)**
  - SDA ← I2C_SDA, SCL ← I2C_SCL
  - VDD ← VDD_3V3, GND ← GND
  - C24(1uF) decoupling at VDD pin
  - INT ← TSL_INT (hierarchical label) with R11(10k) pull-up

- [ ] **3.4: Add hierarchical labels**: I2C_SDA, I2C_SCL, TSL_INT

- [ ] **3.5: Run ERC on sensors sheet alone** → fix any issues

---

## Task 4: Fix Radio.kicad_sch — Antenna Matching + Selection

**Files:**
- Modify: `pcbs/gos_sensor_node/radio.kicad_sch`

**Goal:** Build out the antenna section with matching network, 0Ω select, and u.FL.

- [ ] **4.1: Add matching network components**
  - L4(3.9nH) series from ANT to feed
  - C31(0.8pF) shunt to GND
  - C32(0.5pF) DNP (fine tuning pad)

- [ ] **4.2: Add antenna selection**
  - R24: 0Ω (PCB antenna path, default stuffed)
  - R25: DNP (u.FL path, alternate)
  - J5: u.FL connector

- [ ] **4.3: Add PCB antenna footprint** (IFA or simple trace antenna)

- [ ] **4.4: Add hierarchical labels**: ANT (from MCU), ANT_FEED (to antenna)

- [ ] **4.5: Add ESD protection**
  - D6: PESD0402-140 (<1pF TVS) at antenna feed

---

## Task 5: Build Protection.kicad_sch — ESD + Battery Protection

**Files:**
- Modify: `pcbs/gos_sensor_node/protection.kicad_sch`

**Goal:** Full battery protection and ESD circuitry.

- [ ] **5.1: Complete DW01A + FS8205A battery protection** (already partially done in power sheet, reorganize here per hierarchy)
  - Move DW01A + FS8205A from power sheet OR replicate connections properly

- [ ] **5.2: Add USB ESD protection**
  - D5: PRTR5V0U2X dual TVS on USB D+/D-
  - R14(100Ω) + R15(100Ω) series on D+/D-
  - F1: 500mA PTC fuse on VBUS

- [ ] **5.3: Add external I2C ESD protection**
  - D7-D8: PESD5V0S1BSF TVS diodes
  - R16-R17: 1kΩ series limit

- [ ] **5.4: Add hierarchical labels**: VUSB, VBUS, I2C_SDA_EXT, I2C_SCL_EXT

---

## Task 6: Build LEDs.kicad_sch — AL8860 Drivers + Passives

**Files:**
- Modify: `pcbs/gos_sensor_node/leds.kicad_sch`

**Goal:** Complete LED driver circuits with all passives.

- [ ] **6.1: Add supporting passives for U7 (Blue AL8860)**
  - C27(10uF/0805) input cap, C29(47uF/1206) output cap
  - L2(33uH) buck inductor
  - R20(0.1Ω/1206) current sense
  - R22(10k) CTRL pull-down

- [ ] **6.2: Add supporting passives for U8 (Red AL8860)**
  - C28(10uF/0805) input cap, C30(47uF/1206) output cap
  - L3(33uH) buck inductor
  - R21(0.1Ω/1206) current sense
  - R23(10k) CTRL pull-down

- [ ] **6.3: Add LED connectors**
  - D1: Blue LED connector (Cree XPEBBL) with TVS
  - D2: Red LED connector (Cree XPEBRO) with TVS

- [ ] **6.4: Add hierarchical labels**
  - PWM_BLUE, PWM_RED, LED_VIN, LED_VOUT_BLUE, LED_VOUT_RED

- [ ] **6.5: Wire power path**
  - LED_VIN (from J6) → D4 (reverse protect) → AL8860 VIN
  - AL8860 SW → L → LED anode → LED cathode → sense R → GND

---

## Task 7: Build Connectors.kicad_sch — All Connectors

**Files:**
- Modify: `pcbs/gos_sensor_node/connectors.kicad_sch`

**Goal:** Add all physical connectors.

- [ ] **7.1: Add USB-C connector (J1)**
  - GCT USB4085-GF-A
  - Wire VBUS, D+, D-, GND, CC1(R26 5.1k), CC2(R27 5.1k)
  - Add hierarchical labels: VUSB, VBUS

- [ ] **7.2: Add SWD debug header (J2)**
  - 2x5 1.27mm (Samtec FTSH-105-01)
  - VDD_3V3, SWDIO, SWDCLK, SWO, RESET, GND(×3)

- [ ] **7.3: Add battery connector (J4)**
  - 2-pin JST-PH (S2B-PH-K-S)
  - VBATT, GND

- [ ] **7.4: Add external I2C connector (J3)**
  - 4-pin JST-SH (SM04B-SRSS-TB)
  - VDD_3V3, I2C_SDA_EXT, I2C_SCL_EXT, GND

- [ ] **7.5: Add LED power input (J6)**
  - 2-pin JST-XH
  - LED_VIN, GND

- [ ] **7.6: Add hierarchical labels**: VUSB, VDD_3V3, VBATT, SWDIO, SWDCLK, RESET, UART_TX, UART_RX, I2C_SDA_EXT, I2C_SCL_EXT, LED_VIN

---

## Task 8: Root Sheet — Finalize Hierarchical Connections + PWR_FLAGs

**Files:**
- Modify: `pcbs/gos_sensor_node/gos_sensor_node.kicad_sch` (root sheet)

**Goal:** Ensure all sheet pins match hierarchical labels across all sub-sheets, all power flags present.

- [ ] **8.1: Audit all sheet pins** — verify each sub-sheet's labels have matching sheet pins in root

- [ ] **8.2: Add missing PWR_FLAGs** for VDD_3V3, VBATT, AVDD_3V3

- [ ] **8.3: Run comprehensive ERC** — fix every remaining error/warning until 0/0

---

## Task 9: Set Up PCB Framework — 4-Layer Stackup + Board Outline + Net Classes

**Files:**
- Create board parameters

**Goal:** Transform the current 2-layer 40×65mm placeholder into the proper 4-layer 64×100mm board.

- [ ] **9.1: Fix board outline** — 64×100mm with 5mm corner radius on Edge.Cuts

- [ ] **9.2: Add 4-layer stackup** — F.Cu, GND (inner), PWR (inner), B.Cu

- [ ] **9.3: Set design rules** — 0.15mm min trace/clearance, 0.3mm min drill

- [ ] **9.4: Create net classes** — Default, Power, RF, I2C, Sensitive_Analog with correct widths/clearances

- [ ] **9.5: Update mounting holes** — reposition to match 64×100mm board corners (5mm inset)

- [ ] **9.6: Sync schematic to board** — import all components + nets

---

## Task 10: Component Placement

**Files:**
- Modify: `pcbs/gos_sensor_node/gos_sensor_node.kicad_pcb`

**Goal:** Place all ~108 components per the spec's placement strategy (§11.1).

- [ ] **10.1: Place U1 (nRF52840)** — center of board (~32, 50mm)
- [ ] **10.2: Place Y1 (32MHz) + Y2 (32.768kHz)** — within 5mm of MCU pins
- [ ] **10.3: Place decoupling caps (C1-C13)** — each within 2mm of its VDD/DEC pin
- [ ] **10.4: Place TPS62740 + L1 + C18, C19** — near battery connector
- [ ] **10.5: Place BQ24075 + C20, C21, C22** — near USB connector
- [ ] **10.6: Place U2 (SHT4x)** — board edge thermal island
- [ ] **10.7: Place U3 (TSL2591)** — top side, unobstructed
- [ ] **10.8: Place U7, U8 (AL8860)** — away from sensors, near LED connectors
- [ ] **10.9: Place connectors** — board edges per enclosure cutouts
- [ ] **10.10: Place all passives** — adjacent to their parent ICs
- [ ] **10.11: Add thermal vias** — 4×4 grid (0.3mm drill) under nRF52840 epad
- [ ] **10.12: Add test points (TP1-TP10)** — per spec §14.3

---

## Task 11: PCB Routing

**Files:**
- Modify: `pcbs/gos_sensor_node/gos_sensor_node.kicad_pcb`

**Goal:** Route all nets following priority order.

- [ ] **11.1: Route RF (ANT → matching → antenna)** — 50Ω microstrip, ground via stitching every 2mm
- [ ] **11.2: Route crystal traces (32MHz + 32.768kHz)** — <8mm, guard rings, no vias under
- [ ] **11.3: Route power (VBATT, VDD_3V3, VSYS)** — 0.5mm+ wide traces/copper pours
- [ ] **11.4: Route I2C bus (SDA/SCL)** — together, away from PWM/RF
- [ ] **11.5: Route PWM (PWM_BLUE, PWM_RED)** — away from analog
- [ ] **11.6: Route UART + SWD** — low priority
- [ ] **11.7: Route VBATT_SENSE** — guarded, away from switching regulator
- [ ] **11.8: Route LED power (LED_VIN)** — wide traces (0.5mm+) for 1A

---

## Task 12: Copper Pours + Planes + Antenna Keepout

**Files:**
- Modify: `pcbs/gos_sensor_node/gos_sensor_node.kicad_pcb`

- [ ] **12.1: Layer 2 — Solid GND plane** (no splits, no traces)
- [ ] **12.2: Layer 3 — VDD_3V3 power plane**
- [ ] **12.3: Layer 1 — GND fill with via stitching (every 3mm)**
- [ ] **12.4: Layer 4 — GND fill with via stitching**
- [ ] **12.5: Antenna keepout zone** — no copper any layer within 5mm of antenna

---

## Task 13: DRC + Finalize

**Files:**
- Modify: `pcbs/gos_sensor_node/gos_sensor_node.kicad_pcb`

- [ ] **13.1: Run DRC** — fix all errors/warnings
- [ ] **13.2: 3D viewer check** — verify no component collisions
- [ ] **13.3: Silkscreen cleanup** — ref designators visible, polarity marks, board name/rev
- [ ] **13.4: Add fiducials** — 3x (1mm Cu, 2mm mask clearance)
- [ ] **13.5: Final DRC run** — zero errors
- [ ] **13.6: Generate output files** — Gerbers, BOM, pick-and-place

---

## Task 14: Verification Report

- [ ] **14.1: Run final ERC** — 0 errors, 0 warnings
- [ ] **14.2: Run final DRC** — 0 errors, 0 warnings
- [ ] **14.3: Generate schematic PDF**
- [ ] **14.4: Generate 3D view**
- [ ] **14.5: Write completion summary**
