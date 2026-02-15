# 🧠 PCB Design Prompt Templates for AI-Assisted Hardware Engineering

> **Purpose:** Reusable prompt templates for generating professional PCB design guidance using AI. Tailored for embedded systems and automotive-grade hardware projects.

---

## Table of Contents

1. [Master PCB Design Prompt](#1-master-pcb-design-prompt)
2. [Advanced Engineering-Level Prompt](#2-advanced-engineering-level-prompt)
3. [Embedded Systems / MCU Board Prompt](#3-embedded-systems--mcu-board-prompt)
4. [Automotive / CAN / EV Prompt](#4-automotive--can--ev-high-noise)
5. [Tips for Better AI Output](#5-tips-for-better-ai-output)

---

## 1. Master PCB Design Prompt

> **Use case:** General-purpose PCB design assistance.

```text
I am designing a PCB in KiCad (or Altium Designer).

Please help me design this board from a professional hardware engineering perspective.

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

---

## 2. Advanced Engineering-Level Prompt

> **Use case:** Production-quality, EMI-conscious designs.

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

---

## 3. Embedded Systems / MCU Board Prompt

> **Use case:** Embedded controller boards with mixed interfaces.

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

---

## 4. Automotive / CAN / EV (High Noise)

> **Use case:** Boards operating in noisy automotive environments.

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

---

## 5. Tips for Better AI Output

### ❌ Bad Prompt

```text
Design me a PCB.
```

### ✅ Good Prompt

Include these constraints:
- Specify voltage
- Specify current
- Specify MCU (exact part number)
- Specify environment
- Specify fabrication layer count
- Specify board size constraint

> AI performs much better with constraints.

### 🧩 Ultra-Detailed Meta Prompt

Add this preamble for senior-engineer-level critique:

```text
Assume you are a senior hardware engineer with 15+ years of experience
designing multi-layer PCBs for embedded systems and automotive applications.

Review my PCB design concept and critique it aggressively.
Identify weaknesses, risk areas, and first-revision failure risks.
Suggest improvements that reduce EMI, noise, thermal issues,
and manufacturability problems.
```

### ⚡ Pro Tip

To get numeric values instead of general advice, explicitly ask:

```text
"Provide numeric values, not general advice."
```

This works for:
- KiCad net class rules
- Altium design rules
- Trace width calculations
- IPC-2221 trace calculations
- Stackup suggestions

---

*Reference document for G.O.S. Phenotyping Platform hardware design workflow.*
