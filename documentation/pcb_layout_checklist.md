# 🔧 PCB Layout Preparation Checklist for KiCad

> **Purpose:** Structured pre-layout checklist for serious engineering workflows. Preparing properly before starting a PCB layout in KiCad can save hours of redesign — especially for embedded systems and hardware projects.

---

## 📋 Table of Contents

1. [Define Electrical Requirements](#1-define-electrical-requirements-first)
2. [Schematic-Level Preparation](#2-schematic-level-preparation)
3. [Footprints & Libraries](#3-footprints--libraries)
4. [Stackup & Board Rules Planning](#4-stackup--board-rules-planning)
5. [Placement Planning Strategy](#5-placement-planning-strategy)
6. [High-Speed / Critical Signals](#6-high-speed--critical-signals-checklist)
7. [Power & Ground Planning](#7-power--ground-planning)
8. [DRC & ERC Preparation](#8-drc--erc-preparation)
9. [Fabrication Output Preparation](#9-fabrication-output-preparation)
10. [Professional Pre-Tapeout Checklist](#10-professional-pre-tapeout-checklist)
11. [Engineering-Level Improvements](#bonus-engineering-level-improvements)

---

## 1. Define Electrical Requirements First

> ⚠️ **Do this BEFORE opening KiCad.**

### ✅ Functional Requirements

- [ ] What does the board do?
- [ ] Input/output interfaces (USB? CAN? UART? SPI? I2C?)
- [ ] Voltage domains (3.3V? 5V? 12V? isolated?)
- [ ] Current requirements (especially motors, LEDs, heaters, etc.)
- [ ] Signal speeds (low-speed GPIO vs high-speed differential)

### ✅ Power Budget

- [ ] Total current draw
- [ ] Regulator thermal dissipation
- [ ] Efficiency targets
- [ ] Noise sensitivity

> **Note:** For EV-related or robotics applications, current capacity and ground strategy become very important.

---

## 2. Schematic-Level Preparation

### ✔ Component Selection

> **Do NOT start layout without finalized components.**

Prepare:
- [ ] Exact part numbers
- [ ] Package types (QFN? TQFP? 0603? 0805?)
- [ ] Manufacturer datasheets downloaded

### ✔ Verify

- [ ] Pinout correctness
- [ ] Absolute max ratings
- [ ] Recommended layout guidelines (very important for regulators, crystals, CAN transceivers)

---

## 3. Footprints & Libraries

### 🔍 Check Before Layout

- [ ] Does KiCad have the correct footprint?
- [ ] Is pad size correct?
- [ ] Is courtyard reasonable?
- [ ] Is 3D model available?

If not:
- [ ] Create custom footprint
- [ ] Verify against datasheet mechanical drawing

> ⚠️ **Always print 1:1 scale or use 3D viewer to verify footprint correctness.**

---

## 4. Stackup & Board Rules Planning

Before routing, decide:

| Parameter | Standard | High-Performance |
|-----------|----------|------------------|
| **Layer count** | 2-layer | 4-layer |
| **Copper thickness** | 1 oz | 2 oz |
| **Board thickness** | 1.6 mm | Application-specific |
| **Min trace width** | 6 mil | Manufacturer limit |
| **Min clearance** | 6 mil | Manufacturer limit |
| **Via size** | 0.3 mm drill | 0.2 mm (HDI) |

### Ask your manufacturer for:
- [ ] DRC limits
- [ ] Drill sizes
- [ ] Annular ring requirements

**Key rules:**
- High current → wider traces
- High speed → controlled impedance

---

## 5. Placement Planning Strategy

> **Think before placing.**

### 🧭 Functional Grouping

- [ ] Power section grouped together
- [ ] MCU + crystal close together
- [ ] Decoupling caps right beside IC pins
- [ ] Analog separated from noisy digital

### 📏 Mechanical Constraints

- [ ] Mounting holes positioned
- [ ] Connector edge placement
- [ ] Enclosure size limits verified
- [ ] USB ports flush with board edge

---

## 6. High-Speed / Critical Signals Checklist

If applicable:

- [ ] Differential pair impedance calculated
- [ ] Length matching implemented
- [ ] Keep traces short for:
  - Crystal
  - CAN
  - USB
  - High-speed clocks
- [ ] Avoid sharp 90° corners (use 45° or arcs)
- [ ] Continuous ground plane under high-speed signals

---

## 7. Power & Ground Planning

> 🔥 **This is where many designs fail.**

### Always:

- [ ] Use solid ground plane
- [ ] Avoid ground islands
- [ ] Place decoupling capacitors:
  - As close as possible to VCC pin
  - Short return path to ground

### For Switching Regulators:

- [ ] Follow manufacturer reference layout **exactly**
- [ ] Keep input cap, output cap, and inductor loop tight
- [ ] Route feedback trace away from noisy switching node

---

## 8. DRC & ERC Preparation

Before finishing:

- [ ] Fix all ERC errors
- [ ] Fix all DRC violations
- [ ] Run 3D viewer inspection
- [ ] Check silkscreen overlap
- [ ] Check reference designators visible

---

## 9. Fabrication Output Preparation

### Prepare:

- [ ] Gerber files
- [ ] Drill files
- [ ] Pick & place file
- [ ] BOM (with MPNs)
- [ ] Assembly drawing (if needed)

### Double-check:

- [ ] Board outline layer correct
- [ ] Mount holes — plated or not?
- [ ] Fiducials added (if assembly required)

---

## 10. Professional Pre-Tapeout Checklist

Before sending to fab:

- [ ] All decoupling caps placed?
- [ ] No unconnected nets?
- [ ] Power traces thick enough?
- [ ] Mount holes connected to ground if required?
- [ ] Silkscreen readable?
- [ ] Polarity markings correct?
- [ ] Board orientation arrow added?
- [ ] Test points added?

---

## Bonus: Engineering-Level Improvements

> For professional-grade designs:

### Test Pads

- [ ] Power rails
- [ ] UART debug
- [ ] Reset line

### Protection

- [ ] ESD protection for external connectors
- [ ] Reverse polarity protection
- [ ] TVS diodes for automotive/CAN applications
- [ ] Current measurement shunt (for power debugging)

> **Note:** For EV systems and embedded robotics, these protections matter in real deployment.

---

## 🎯 Summary — What To Prepare BEFORE Opening KiCad PCB Editor

| Step | Status |
|------|--------|
| Finalized schematic | ☐ |
| Confirmed footprints | ☐ |
| Stackup decided | ☐ |
| Design rules set | ☐ |
| Power/current calculation done | ☐ |
| Mechanical constraints known | ☐ |
| Manufacturer specs collected | ☐ |

---

*Reference document for G.O.S. Phenotyping Platform PCB design workflow.*
