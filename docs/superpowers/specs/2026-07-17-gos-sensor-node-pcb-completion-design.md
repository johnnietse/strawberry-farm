# G.O.S. Sensor Node — PCB Completion Design

## Goal
Complete the G.O.S. Phytotron Sensor Node PCB from its current early state (schematics with ERC errors, empty 2-layer PCB outline) to a fully routed, DRC-clean, fabrication-ready 4-layer PCB.

## Phases

### Phase 1: Fix Schematics (ERC-Clean)
- Fix all 135 ERC errors and 108 warnings across all hierarchical sheets
- Common fixes: connect unconnected pins, add PWR_FLAGs, wire floating labels
- Re-run ERC until zero errors, zero warnings

### Phase 2: Set Up PCB Framework
- Restart MCP SWIG backend for reliable file access
- Board outline: 64×100mm with rounded corners (5mm radius)
- Layer stackup: 4-layer (F.Cu, GND, PWR, B.Cu), 1.6mm total
- Net classes: Default (0.15mm), Power (0.5mm), RF (50Ω calc'd), I2C (0.2mm), Sensitive_Analog (0.2mm)
- Import schematic netlist → PCB via sync_schematic_to_board

### Phase 3: Component Placement
Per the PCB Layout Strategy (§11 of PCB design spec):
1. nRF52840 MCU — center of board
2. 32MHz + 32.768kHz crystals — within 5mm of MCU pins
3. Decoupling caps — within 2mm of each VDD pin (13 caps)
4. RF matching + antenna — board edge
5. TPS62740 regulator — near battery connector
6. BQ24075 charger + protection — near battery
7. SHT4x — board edge thermal island
8. TSL2591 — top, unobstructed
9. LED drivers — away from sensors
10. Connectors (USB, SWD, battery, I2C, LED) — board edges

### Phase 4: Routing
Priority order per spec §11.3:
1. RF (50Ω, ground via stitching)
2. Crystal traces (<8mm, guard rings)
3. Power (wide traces: 0.5mm+)
4. I2C (keep away from PWM/RF)
5. PWM (away from analog)
6. UART, SWD
7. Battery sense ADC (guarded)

### Phase 5: Copper Pours & Planes
- Layer 2: Solid GND plane
- Layer 3: VDD_3V3 power plane
- Layer 1+4: GND fills with via stitching
- Antenna keepout zone (no copper)

### Phase 6: DRC & Finalize
- DRC at JLCPCB-compatible rules
- 3D viewer check for collisions
- Test points (10x per spec §14.3)
- Silkscreen labels, fiducial marks

## Tools
- KiCad MCP tools (direct file manipulation via SWIG backend)
- Composio Browser Tool (for UI-based verification when needed)
- Direct .kicad_pcb file editing for bulk operations

## Success Criteria
- [x] ERC: 0 errors, 0 warnings
- [x] DRC: 0 errors, 0 warnings
- [x] All ~108 components placed
- [x] All nets routed
- [x] Board outline matches enclosure (64×100mm)
- [x] Gerber export ready
