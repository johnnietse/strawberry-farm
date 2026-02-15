# 🧠 Complete PCB Design Engineering Reference & AI Prompt Guide

> **Purpose:** Exhaustive PCB design reference with detailed engineering explanations, formulas, and reusable AI prompt templates. Covers power integrity, signal integrity, grounding, EMC, thermal management, DFM, and more.

---

## Table of Contents

1. [Master PCB Design Prompt](#1-master-pcb-design-prompt)
2. [Advanced Engineering-Level Prompt](#2-advanced-engineering-level-prompt)
3. [Embedded Systems / MCU Board Prompt](#3-embedded-systems--mcu-board-prompt)
4. [Automotive / CAN / EV Prompt](#4-automotive--can--ev-high-noise)
5. [Power Tree Design In-Depth](#5-power-tree-design-in-depth)
6. [Grounding Strategy In-Depth](#6-grounding-strategy-in-depth)
7. [Trace Width & Current Carrying](#7-trace-width--current-carrying-capacity)
8. [Decoupling & Filtering Strategy](#8-decoupling--filtering-strategy)
9. [Signal Integrity](#9-signal-integrity)
10. [ESD & Protection Circuits](#10-esd--protection-circuits)
11. [Thermal Management](#11-thermal-management)
12. [PCB Stackup Design](#12-pcb-stackup-design)
13. [DFM & DFT](#13-design-for-manufacturability--testability)
14. [Pre-Layout Checklist](#14-complete-pre-layout-checklist)
15. [Pre-Tapeout Checklist](#15-professional-pre-tapeout-checklist)
16. [Tips for Better AI Output](#16-tips-for-better-ai-output)

---

## 1. Master PCB Design Prompt

> **Use case:** General-purpose PCB design assistance. Copy-paste and fill in the brackets.

```text
I am designing a PCB in KiCad (or Altium Designer).

Please help me design this board from a professional hardware
engineering perspective.

Project Description:
[Describe what the board does]

Requirements:
- Input voltage: [e.g., 12V automotive]
- Output voltage(s): [e.g., 5V, 3.3V]
- Max current draw: [e.g., 2A]
- Interfaces: [UART, SPI, I2C, CAN, USB, etc.]
- Microcontroller: [Exact part number]
- Expected operating environment: [indoor, automotive, high noise, etc.]
- Layer count preference: [2-layer or 4-layer]

I want you to provide:
1. Recommended system architecture
2. Power tree design
3. Component selection suggestions (with reasoning)
4. Schematic design guidelines
5. PCB placement strategy
6. Routing strategy
7. Grounding strategy
8. Decoupling and filtering strategy
9. High-current trace width recommendations
10. DRC/stackup recommendations
11. Common mistakes to avoid

Please structure the response as if you are a senior hardware engineer
reviewing my design before fabrication.
```

### What Each Item Means

**System Architecture:** A block diagram showing how power flows, how signals interconnect, and which ICs talk to each other. This is the "map" of your board before you draw a single schematic symbol.

**Power Tree Design:** A hierarchical diagram showing every voltage rail, its source regulator, current capacity, and downstream consumers. Example:

```
12V Battery Input
├── Buck Converter (TPS54331) → 5V @ 3A
│   ├── USB Host (500mA max)
│   ├── CAN Transceiver (70mA)
│   └── LDO (AMS1117-3.3) → 3.3V @ 800mA
│       ├── MCU (150mA max)
│       ├── SPI Flash (25mA)
│       └── I2C Sensors (10mA)
└── Direct → 12V Motor Driver (5A peak)
```

**Component Selection:** Choose parts based on: availability (check Digi-Key/Mouser stock), package type suitable for your assembly method (hand solder = SOIC/0805+, reflow = QFN/0402), thermal rating, and cost.

**Routing Strategy Priority Order:**
1. Power traces (widest first)
2. High-speed differential pairs (USB, CAN)
3. Crystal traces (keep < 10mm)
4. Clock signals
5. Standard digital I/O
6. Low-priority signals (LED indicators, test points)

---

## 2. Advanced Engineering-Level Prompt

> **Use case:** Production-quality, EMI-conscious designs that must pass certification.

```text
I am designing a production-quality PCB in KiCad/Altium.

The board must be reliable, EMI-conscious, and suitable for
professional fabrication.

Provide a complete engineering-level design review including:

1. Power integrity considerations
2. Ground plane strategy (single-point vs solid plane)
3. Signal integrity considerations
4. Thermal management analysis
5. Decoupling capacitor placement rules
6. Via stitching strategy
7. Copper weight recommendations
8. Trace width calculations (show formula)
9. Creepage/clearance considerations
10. ESD protection strategy
11. Protection circuitry recommendations
12. Manufacturability considerations (DFM)
13. Testability improvements (DFT)

Assume I want this board to pass EMI testing on first revision.
Explain reasoning behind every recommendation.
```

### Detailed Breakdown of Each Item

#### Power Integrity

Power integrity (PI) ensures that every IC on your board receives clean, stable voltage. Poor PI causes:
- Logic errors from voltage droops during current transients
- Increased EMI from ringing on power rails
- Thermal hotspots from resistive losses

**Key PI practices:**
- Keep power loop areas small (source → load → return path)
- Use wide traces or copper pours for power rails
- Place bulk capacitors (10µF-100µF) near power entry
- Place high-frequency decoupling (100nF, 10nF) within 3mm of IC VCC pins
- Use multiple vias for power connections to inner planes

#### Ground Plane Strategy

**Solid Ground Plane (recommended for 99% of designs):**
- Provides low-impedance return path for all signals
- Acts as electromagnetic shield
- Reduces loop areas (lower EMI)
- Improves thermal dissipation

**When to split ground planes:**
- Only when you have truly isolated analog + digital sections
- NEVER split under a signal that crosses the boundary
- If you split, reconnect at a single point near the ADC/DAC

**Common Mistake:** Students split ground planes thinking it "isolates noise." In reality, split planes INCREASE noise because return currents are forced to take long paths around the split, creating large loop antennas.

#### Via Stitching Strategy

Via stitching connects ground planes on different layers, ensuring they stay at the same potential:

```
Recommended via stitching spacing:
- λ/20 rule: spacing < λ/20 of highest frequency
- For 100MHz signals: λ = 3m → spacing < 150mm (easy)
- For 1GHz signals: λ = 0.3m → spacing < 15mm
- General rule: Every 5-10mm along board edges
- Around high-speed ICs: Every 2-3mm
```

**Where to stitch:**
- Board perimeter (every 5mm)
- Around high-speed ICs
- Between ground pours on different layers
- Near connectors
- Around crystal oscillators

---

## 3. Embedded Systems / MCU Board Prompt

```text
I am designing an embedded controller PCB in KiCad/Altium.

MCU: [e.g., STM32F407VG]
Input: [e.g., 12V automotive battery]
Interfaces: [CAN, UART debug, SPI sensors, I2C, USB]

Please help me:
1. Design the power tree (automotive-safe)
2. Choose voltage regulators
3. Design proper CAN transceiver protection
4. Add ESD and reverse polarity protection
5. Design proper decoupling network for MCU
6. Recommend crystal layout strategy
7. Recommend PCB stackup
8. Suggest placement floorplanning
9. Provide routing priority order
10. Provide checklist before Gerber export

Please respond as a hardware design mentor reviewing my schematic
before layout.
```

### Detailed Engineering Guidance

#### Power Tree for Automotive Input

Automotive 12V is actually **6V to 42V** with transients up to **100V** (load dump). You MUST protect against this:

```
Battery (6-42V, transients to 100V)
│
├── TVS Diode (SMBJ33A) — clamps transients
├── Reverse Polarity MOSFET (Si4435DDY)
├── Input LC Filter (10µH + 100µF ceramic)
│
└── Wide-Input Buck (LM2596 or TPS54331)
    Input: 6-40V → Output: 5V @ 3A
    │
    ├── Efficiency: 85-92% (vs 40% for LDO!)
    ├── CAN Transceiver (3.3V or 5V tolerant)
    │
    └── LDO (AMS1117-3.3 or MCP1700)
        Input: 5V → Output: 3.3V @ 500mA
        │
        ├── MCU (STM32)
        ├── SPI Flash
        ├── I2C Sensors
        └── Crystal Oscillator
```

**Why Buck then LDO?**
- Buck converter efficiently drops 12V to 5V (high voltage delta)
- LDO cleanly drops 5V to 3.3V (low noise, low dropout)
- Direct 12V → 3.3V LDO would dissipate: P = (12-3.3) × 0.5A = **4.35W** (too hot!)

#### Voltage Regulator Selection Guide

| Parameter | LDO | Buck (Switching) |
|-----------|-----|-----------------|
| **Efficiency** | η = Vout/Vin (poor for large dropouts) | 85-95% typical |
| **Noise** | Very low (µV ripple) | Higher (mV ripple, switching noise) |
| **Cost** | $0.10-$0.50 | $0.50-$3.00 |
| **External parts** | 2 caps | Inductor + 3 caps + diode |
| **Use when** | Vin - Vout < 2V, low current | Vin - Vout > 2V, high current |

#### CAN Transceiver Protection

```
CAN Bus ──┬── 120Ω Term Resistor ──┬── CAN Bus
           │                        │
      ┌────┴────┐            ┌─────┴─────┐
      │ CANH    │            │  CANL     │
      │         │            │           │
      │  ┌──────┤            ├──────┐    │
      │  │ ESD  │            │ ESD  │    │
      │  │TVS   │            │TVS   │    │
      │  │PESD2  │           │PESD2 │    │
      │  │CAN   │            │CAN   │    │
      │  └──┬───┘            └──┬───┘    │
      │     │    Common Mode    │        │
      │     │    Choke (CMC)    │        │
      │     └────────┬─────────┘        │
      │              │                   │
      │           ┌──┴──┐               │
      │           │ GND │               │
      │           └─────┘               │
      │                                  │
      └──── CAN Transceiver (MCP2551) ──┘
```

**Protection components:**
- **TVS Diodes (PESD2CAN):** Clamp ESD strikes (±15kV contact, ±25kV air)
- **Common Mode Choke:** Filters common-mode noise from long cable runs
- **120Ω Termination:** Required at both ends of CAN bus (split termination: 2×60Ω with 4.7nF cap to GND for better EMC)

#### Crystal Layout Rules

Crystal layout is **critical** — poor layout causes clock jitter, EMI, and startup failures:

```
┌─────────────────────────────────────────┐
│                                         │
│    MCU Pin (OSC_IN)                     │
│        │                                │
│        ├── C_load1 (12pF) ── GND       │
│        │                                │
│        ├── XTAL ─────────┐             │
│        │   (keep < 10mm) │             │
│        │                  │             │
│    MCU Pin (OSC_OUT)     │             │
│        │                  │             │
│        ├── C_load2 (12pF) ── GND       │
│        │                                │
│        └── Guard ring (GND pour)        │
│                                         │
│    ⚠ NO OTHER TRACES IN THIS AREA!     │
│    ⚠ Ground plane SOLID underneath     │
│    ⚠ Keep traces < 10mm total          │
│    ⚠ No vias under crystal             │
│                                         │
└─────────────────────────────────────────┘
```

**Rules:**
1. Crystal traces MUST be < 10mm (shorter is better)
2. Load capacitors directly adjacent to crystal pins
3. Solid ground plane below crystal — NO splits, NO routing
4. Surround with ground pour (guard ring)
5. No high-speed signals routed near crystal
6. Crystal is a high-impedance node — extremely sensitive to crosstalk

---

## 4. Automotive / CAN / EV (High Noise)

```text
This PCB will operate in a noisy automotive environment.

Provide recommendations for:
1. TVS diode placement
2. CAN bus termination and split termination
3. Common mode choke usage
4. Grounding strategy
5. EMI reduction techniques
6. Filtering input supply
7. Load dump protection
8. Transient protection
9. Shielding strategy

Assume ISO 7637 transient exposure.
```

### Detailed Automotive Protection Design

#### ISO 7637 Transient Pulses

Your board MUST survive these transients on the 12V supply:

| Pulse | Description | Voltage | Duration |
|-------|------------|---------|----------|
| **1** | Supply disconnect (inductive) | -100V | 2ms |
| **2a** | Supply disconnect (ignition off) | +50V | 0.2ms |
| **2b** | Supply disconnect (ignition off) | +10V | 0.2ms |
| **3a** | Switching transients | -150V | 150ns |
| **3b** | Switching transients | +100V | 150ns |
| **4** | Starting voltage drop | -6V to -25V | 20ms |
| **5a** | Load dump (alternator) | +65V to +87V | 400ms |
| **5b** | Load dump (enhanced) | +100V to +120V | 350ms |

#### Input Protection Circuit

```
Battery ──┤ Fuse (5A) ├──┬── TVS (SMBJ33A) ── GND
                         │
                    ┌────┴────┐
                    │ Reverse │
                    │Polarity │
                    │ MOSFET  │
                    │(P-ch or │
                    │ ideal   │
                    │ diode)  │
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │  EMI    │
                    │ Filter  │
                    │(LC: 10µH│
                    │+ 100µF) │
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │  Buck   │
                    │Converter│
                    │(wide    │
                    │ input)  │
                    └────┬────┘
                         │
                      5V Rail
```

**Component Selection:**
- **TVS Diode:** SMBJ33A (33V standoff, 53.3V clamping, 600W peak pulse)
- **Reverse Polarity:** P-channel MOSFET (Si4435DDY) or ideal diode controller (LTC4357)
- **Input Inductor:** 10µH, rated for 2× max current, low DCR
- **Input Caps:** 100µF ceramic (X7R) + 470µF electrolytic

#### CAN Bus Split Termination

Standard termination (120Ω at each end) works but split termination provides better EMC:

```
Standard:          Split:
CANH ──┤120Ω├── CANL   CANH ──┤60Ω├──┬──┤60Ω├── CANL
                                      │
                                   ┤4.7nF├
                                      │
                                     GND
```

**Why split termination is better:**
- The 4.7nF cap provides AC ground reference at the bus midpoint
- Reduces common-mode voltage on the bus
- Improves EMC performance by 5-10 dB
- Required for ISO 11898-2 compliance in many automotive designs

#### Grounding in Automotive

```
Chassis Ground (vehicle body)
│
├── Star-grounded to PCB via single bolt
│   (prevents ground loops through chassis)
│
│   PCB Internal:
│   ┌─────────────────────────────────┐
│   │ Solid copper pour (ground plane)│
│   │                                 │
│   │ Power GND ←→ Signal GND        │
│   │    (connected, NOT split)       │
│   │                                 │
│   │ Shield GND ── separate trace    │
│   │    to chassis bolt              │
│   └─────────────────────────────────┘
│
└── Cable shields terminated at connector
    (connected to chassis GND, not signal GND)
```

---

## 5. Power Tree Design In-Depth

### Step-by-Step Power Tree Process

**Step 1: List every voltage rail needed**
```
Rail    | Voltage | Max Current | Noise Tolerance | Source
--------|---------|-------------|-----------------|--------
VBAT    | 12V     | Input       | N/A             | Battery
5V_SW   | 5.0V    | 3A          | 50mV ripple OK  | Buck
3V3_MCU | 3.3V    | 500mA       | < 10mV ripple   | LDO
3V3_ANA | 3.3V    | 50mA        | < 1mV ripple    | Ferrite + LDO
1V8_PLL | 1.8V    | 20mA        | < 5mV ripple    | LDO
```

**Step 2: Calculate total power dissipation**

For LDO: `P_diss = (V_in - V_out) × I_out`
For Buck: `P_diss = P_out × (1 - η) / η`

Example:
- LDO 5V→3.3V at 500mA: P = (5-3.3)×0.5 = **0.85W** (SOT-223 can handle this)
- LDO 12V→3.3V at 500mA: P = (12-3.3)×0.5 = **4.35W** (NEEDS heatsink or switch to buck!)

**Step 3: Choose regulator topology**

| Dropout | Current | Best Choice |
|---------|---------|-------------|
| < 1V | < 300mA | LDO |
| < 2V | < 1A | LDO with good thermal pad |
| > 2V | Any | Buck converter |
| Any | > 3A | Buck converter |
| Ultra-low noise needed | < 500mA | LDO (even after buck) |

### Sequencing Considerations

Some ICs require power rails to come up in a specific order:
- FPGAs: Core voltage FIRST, then I/O voltage
- DDR memory: VTT must track VDDQ/2
- Multi-rail MCUs: Check datasheet for sequencing requirements

Use a voltage supervisor (like TPS3808) or enable-chain to enforce sequencing.

---

## 6. Grounding Strategy In-Depth

### Why Ground Matters

Current ALWAYS returns to its source. The question is: **what path does it take?**

AC return currents follow the path of **lowest impedance** (not lowest resistance). At high frequencies, return current follows directly beneath the signal trace on the nearest ground plane.

### Ground Plane Rules

**Rule 1: Never split the ground plane under a signal path**
```
BAD:                               GOOD:
Signal ──────────────►              Signal ──────────────►
                                    
GND ████████ gap ████████          GND ██████████████████████
         ↑
Return current forced around gap
= large loop area = EMI antenna!
```

**Rule 2: Minimize loop area**
```
Loop area = signal path area + return path area

Smaller loop area = less EMI radiation
                  = less susceptibility to external noise
                  = better signal integrity
```

**Rule 3: Via placement for layer transitions**
When a signal changes layers, the return current must also change layers. Place a ground via RIGHT NEXT to the signal via:

```
Signal via ○  ○ Ground via  ← within 1mm!
```

### Star Grounding vs Solid Plane

| Method | When to Use |
|--------|-------------|
| **Solid plane** | Digital boards, mixed-signal (99% of designs) |
| **Star ground** | Audio equipment, precision measurement |
| **Split plane** | Only if mandated by IC datasheet (rare) |

---

## 7. Trace Width & Current Carrying Capacity

### IPC-2221 Formula

The industry standard for calculating trace width based on current:

```
For external (outer) layers:
I = k × ΔT^0.44 × A^0.725

Where:
I = current (Amps)
k = 0.048 (external) or 0.024 (internal)
ΔT = temperature rise above ambient (°C)
A = cross-sectional area (mils²)

A = thickness (oz) × 1.378 × width (mils)
For 1oz copper: thickness = 1.378 mils (35µm)
```

### Quick Reference Table (1oz copper, 10°C rise)

| Current | External Width | Internal Width |
|---------|---------------|----------------|
| 0.5A | 10 mil (0.25mm) | 20 mil (0.5mm) |
| 1.0A | 25 mil (0.64mm) | 50 mil (1.27mm) |
| 2.0A | 60 mil (1.52mm) | 110 mil (2.8mm) |
| 3.0A | 100 mil (2.54mm) | 200 mil (5.1mm) |
| 5.0A | 200 mil (5.1mm) | 400 mil (10.2mm) |
| 10A | 500 mil (12.7mm) | Use copper pour |

### Voltage Drop Calculation

```
R_trace = ρ × L / A

Where:
ρ (copper resistivity) = 1.724 × 10⁻⁶ Ω·cm
L = trace length (cm)
A = cross-sectional area (cm²)

V_drop = I × R_trace
```

**Example:** 3A through 10cm trace, 1oz copper, 100mil wide:
```
A = 0.00350 × 0.254 = 0.000889 cm²
R = 1.724e-6 × 10 / 0.000889 = 0.0194 Ω
V_drop = 3 × 0.0194 = 0.058V (58mV)
```

At 3.3V rail, that's a 1.8% drop — acceptable for most applications but NOT for precision analog.

---

## 8. Decoupling & Filtering Strategy

### Why Decoupling Capacitors?

When an IC switches, it draws sudden current spikes. The power supply can't respond fast enough (due to inductance of traces and wires). Decoupling caps act as local energy reservoirs.

### The Capacitor Impedance Curve

Every real capacitor has:
- **Capacitance** (dominates at low frequency)
- **ESR** (equivalent series resistance — the valley)
- **ESL** (equivalent series inductance — dominates at high frequency)

```
Impedance
    │
    │ \
    │   \  ← Capacitive region
    │     \
    │      ── ← ESR (minimum impedance)
    │     /
    │   /  ← Inductive region (ESL)
    │ /
    └──────────────── Frequency
          SRF (Self-Resonant Frequency)
```

### Multi-Value Decoupling Strategy

Use MULTIPLE cap values to cover a wide frequency range:

| Capacitor | Covers | Placement |
|-----------|--------|-----------|
| 100µF electrolytic | Power entry filtering (kHz) | Near power connector |
| 10µF ceramic (X7R) | Bulk local decoupling (10kHz-1MHz) | Within 10mm of IC |
| 100nF ceramic (X7R) | Standard decoupling (1MHz-100MHz) | Within 3mm of VCC pin |
| 10nF ceramic (C0G) | High-frequency decoupling (100MHz+) | Within 1mm of VCC pin |
| 1nF ceramic (C0G) | RF decoupling (500MHz+) | Only for GHz designs |

### Placement Rules

```
CORRECT:                          WRONG:
                                  
IC ─┤VCC├─── 100nF ── GND       IC ─┤VCC├─── long trace ── 100nF ── GND
     ↑            ↑                              ↑
  < 3mm        via to                     inductance of trace
              ground plane                negates capacitor!
```

**Critical:** The TOTAL loop area (VCC pin → cap → GND via → GND plane → IC GND pin) must be minimized.

### Switching Regulator Input/Output Filtering

```
Input side:                    Output side:
VIN ──┤Cin├── Buck ──┤Cout├── VOUT
       │      │        │
      GND    L,D      GND

Cin: Low-ESR ceramic, rated for ripple current
     Typical: 10µF-22µF X7R (same voltage rating as VIN)

Cout: Low-ESR ceramic for transient response
      Typical: 22µF-47µF X7R
      
⚠ ALWAYS check regulator datasheet for specific requirements
⚠ Ceramic cap loses capacitance under DC bias!
   (A "10µF" 0805 at 5V DC may only have 4µF effective)
```

---

## 9. Signal Integrity

### When Does Signal Integrity Matter?

**Rule of thumb:** If the trace length > λ/10 of the signal's rise time:

```
Critical length = rise_time × propagation_speed / 10

Propagation speed on FR4 ≈ 15 cm/ns (half speed of light)

Example:
- UART at 115200 baud: rise_time ≈ 1µs → critical length = 15m (never an issue)
- SPI at 10MHz: rise_time ≈ 5ns → critical length = 7.5cm (starts to matter)
- USB 2.0 (480Mbps): rise_time ≈ 500ps → critical length = 7.5mm (CRITICAL)
- DDR3 (800MHz+): rise_time ≈ 200ps → critical length = 3mm (VERY CRITICAL)
```

### Controlled Impedance

For high-speed signals, the trace must have consistent impedance:

**Microstrip (trace on outer layer over ground plane):**
```
Z₀ = 87 / √(εr + 1.41) × ln(5.98 × h / (0.8 × w + t))

Where:
εr = dielectric constant (FR4 ≈ 4.2-4.5)
h = height above ground plane
w = trace width
t = copper thickness

Common targets:
- Single-ended: 50Ω
- USB differential: 90Ω
- LVDS: 100Ω
- CAN: Not impedance-controlled (low speed)
```

### Differential Pair Routing

For USB, CAN, LVDS, Ethernet:

```
Rules:
1. Route both traces together (matched length within 5 mils)
2. Maintain constant spacing between P and N
3. Keep ground plane solid and continuous underneath
4. Avoid sharp bends — use 45° or curves
5. Length matching: within 50 mils for USB 2.0
                    within 5 mils for USB 3.0 / DDR

Good:                    Bad:
━━━━━━━━━━              ━━━━┓
━━━━━━━━━━                   ┗━━━━━
  (parallel)              (different lengths!)
```

---

## 10. ESD & Protection Circuits

### ESD Standards

| Standard | Test Level | Application |
|----------|-----------|-------------|
| IEC 61000-4-2 Level 2 | ±4kV contact, ±8kV air | Consumer electronics |
| IEC 61000-4-2 Level 4 | ±8kV contact, ±15kV air | Industrial |
| ISO 10605 | ±8kV contact, ±25kV air | Automotive |

### Protection Strategy by Interface

| Interface | Protection | Recommended Part |
|-----------|-----------|-----------------|
| USB | TVS array | TPD2E001 or USBLC6-2 |
| CAN | Bidirectional TVS | PESD2CAN |
| UART/GPIO | TVS + series resistor | PESD5V0S1BA + 100Ω |
| Ethernet | Magnetics + TVS | Built into RJ45 jack |
| Power input | TVS + fuse | SMBJ series |
| Antenna | Gas discharge + TVS | Two-stage protection |

### Reverse Polarity Protection

**Method 1: Series Diode (simple, lossy)**
```
VIN ──┤►├── Circuit
       Schottky
       V_drop = 0.3V
       P_loss = 0.3V × I
```

**Method 2: P-Channel MOSFET (efficient)**
```
VIN ──┤ PMOS ├── Circuit
       Gate tied to GND
       V_drop = I × Rds_on ≈ 0.05V
       Auto-blocks reverse polarity
```

**Method 3: Ideal Diode Controller (best)**
```
VIN ──┤ NMOS + Controller ├── Circuit
       LTC4357 or similar
       V_drop ≈ 0.02V
       For high-current applications
```

---

## 11. Thermal Management

### Junction Temperature Calculation

```
T_junction = T_ambient + (P_dissipated × θ_JA)

Where:
θ_JA = junction-to-ambient thermal resistance (from datasheet)
```

**Example:** LDO dissipating 1W, θ_JA = 60°C/W, ambient = 40°C:
```
T_j = 40 + (1 × 60) = 100°C
Max T_j for most ICs = 125°C → 25°C margin ✓
```

### Thermal Relief Techniques

| Technique | Heat Reduction |
|-----------|---------------|
| Thermal vias under pad | 30-50% lower θ_JA |
| Copper pour on both sides | 20-30% lower |
| Increase copper weight (2oz) | 15-20% lower |
| Airflow | 30-60% lower |
| Heatsink | 50-80% lower |

### Thermal Via Array

```
┌─────────────────┐
│  Exposed pad     │
│  ○ ○ ○ ○ ○     │   ○ = thermal via (0.3mm drill)
│  ○ ○ ○ ○ ○     │
│  ○ ○ ○ ○ ○     │   Connected to ground plane
│  ○ ○ ○ ○ ○     │   and copper pour on bottom
│                  │
└─────────────────┘

Via pitch: 1.0-1.2mm
Via drill: 0.3mm
Via finish: Filled and capped (preferred)
            or tented (budget option)
```

---

## 12. PCB Stackup Design

### 2-Layer Stackup

```
Layer 1 (Top):    Signal + Power traces
                  ─────────────────────
Dielectric:       FR4 (1.6mm)
                  ─────────────────────
Layer 2 (Bottom): Ground plane (as solid as possible)
```

**Best for:** Simple designs < 50MHz, < 100 components

### 4-Layer Stackup (Recommended)

```
Layer 1 (Top):    Signal + Components
                  ─────────────────────  (0.2mm prepreg)
Layer 2 (Inner1): Ground Plane (SOLID!)
                  ─────────────────────  (1.0mm core)
Layer 3 (Inner2): Power Plane
                  ─────────────────────  (0.2mm prepreg)
Layer 4 (Bottom): Signal + Components
```

**Why 4-layer is worth the cost:**
- Top signals have immediate ground reference (Layer 2)
- Bottom signals have immediate ground reference (Layer 2 or power plane)
- EMI reduced by 10-20 dB compared to 2-layer
- Better power distribution
- Cost increase: ~30-50% more than 2-layer

### 6-Layer Stackup (High-Speed)

```
Layer 1: Signal (high-speed)
Layer 2: Ground
Layer 3: Signal (low-speed)
Layer 4: Power
Layer 5: Ground
Layer 6: Signal (high-speed)
```

---

## 13. Design for Manufacturability & Testability

### DFM Rules

| Parameter | Minimum (Standard) | Recommended |
|-----------|-------------------|-------------|
| Trace width | 4 mil (0.1mm) | 6 mil (0.15mm) |
| Trace spacing | 4 mil | 6 mil |
| Drill size | 0.2mm | 0.3mm |
| Annular ring | 0.1mm | 0.15mm |
| Solder mask dam | 3 mil | 5 mil |
| Silkscreen width | 4 mil | 6 mil |
| Board edge clearance | 0.2mm | 0.5mm |
| Via-to-pad clearance | 0.2mm | 0.3mm |

### DFT (Design for Testability)

Add test points for:
- [ ] Every power rail (VCC, 3.3V, 5V, 1.8V)
- [ ] Ground (accessible probe point)
- [ ] UART TX/RX (debug console)
- [ ] Reset line
- [ ] Boot mode select
- [ ] SWD/JTAG programming header
- [ ] Critical clock signals
- [ ] I2C SDA/SCL (for logic analyzer)
- [ ] CAN H/L (for bus analyzer)

### Panelization

If ordering production quantities:
- Add V-score or tab-route breakaway tabs
- Add tooling holes (3× minimum, 3.2mm diameter)
- Add fiducials (3× minimum, 1mm diameter)
- Leave 5mm rail around panel edges

---

## 14. Complete Pre-Layout Checklist

- [ ] Schematic fully complete and reviewed
- [ ] All components have confirmed footprints
- [ ] All footprints verified against datasheets (1:1 print or 3D view)
- [ ] BOM created with exact MPNs
- [ ] All parts confirmed in-stock (check Digi-Key/Mouser)
- [ ] Power tree documented with current/voltage at each rail
- [ ] Total power dissipation calculated
- [ ] Thermal analysis done for hot components
- [ ] PCB stackup decided (2/4/6 layer)
- [ ] Design rules set (trace width, spacing, via size)
- [ ] Manufacturer capabilities confirmed (drill, clearance, etc.)
- [ ] Board dimensions and mounting holes defined
- [ ] Connector placement constrained by enclosure
- [ ] Critical component placement planned
- [ ] ESD protection added for all external connectors
- [ ] Reverse polarity protection on power input
- [ ] Decoupling strategy planned (cap values and quantities)

---

## 15. Professional Pre-Tapeout Checklist

Before sending Gerbers to fab:

- [ ] All ERC errors resolved
- [ ] All DRC violations resolved
- [ ] No unconnected nets (ratsnest clear)
- [ ] All decoupling capacitors placed and routed
- [ ] Power traces wide enough for current requirements
- [ ] Ground plane solid (no unintended splits)
- [ ] Crystal layout follows rules (short traces, guard ring)
- [ ] Differential pairs length-matched
- [ ] Thermal vias under hot components
- [ ] Mount holes correct size (plated/non-plated as needed)
- [ ] Mount holes connected to ground (if required for EMC)
- [ ] Silkscreen readable, no overlap with pads
- [ ] Polarity markings on all polarized components
- [ ] Pin 1 indicators on all ICs
- [ ] Board orientation arrow/marking
- [ ] Test points accessible
- [ ] Fiducials placed (if assembly)
- [ ] Board outline on correct layer
- [ ] 3D view checked for component collisions
- [ ] Gerber files generated and reviewed in viewer
- [ ] Drill file verified
- [ ] BOM matches schematic

---

## 16. Tips for Better AI Output

### ❌ Bad Prompt
```
Design me a PCB.
```

### ✅ Good Prompt
Always include:
- **Voltage** (input and all output rails)
- **Current** (per rail and total)
- **MCU** (exact part number)
- **Environment** (temp range, noise level, indoor/outdoor)
- **Layer count** (2 or 4 layer)
- **Board size** constraint
- **Assembly method** (hand solder vs reflow)

### 🧩 Senior Engineer Meta Prompt

Add this preamble for aggressive design review:

```text
Assume you are a senior hardware engineer with 15+ years of
experience designing multi-layer PCBs for embedded systems
and automotive applications.

Review my PCB design concept and critique it aggressively.
Identify weaknesses, risk areas, and first-revision failure risks.
Suggest improvements that reduce EMI, noise, thermal issues,
and manufacturability problems.

Provide numeric values, not general advice.
```

### ⚡ Specific Numeric Requests

To get concrete values instead of vague advice:

```text
"Provide numeric values, not general advice."
"Show me the IPC-2221 calculation for X amps."
"Generate KiCad net class rules for my design."
"Calculate the impedance for my stackup."
```

This works for:
- KiCad net class rules (.kicad_dru format)
- Altium design rules
- Trace width calculations with formulas
- IPC-2221 current capacity tables
- Stackup impedance calculations

---

*Comprehensive PCB design reference for the G.O.S. Phenotyping Platform hardware design workflow.*
