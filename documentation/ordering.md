# Ordering: boards, parts, enclosures and accessories

Everything here is ordered online. Both boards come fully assembled, so nothing needs soldering.
This file tracks where each part comes from, its catalogue numbers and how much stock each source
had. **Stock was checked on 2026-11-14 and 2026-11-15 and changes daily; recheck before ordering.**

Contents: [the board order](#1-the-board-order-jlcpcb) · [part list with stock](#2-every-part-on-the-boards)
· [design changes for stock](#3-parts-changed-because-of-stock-or-simulation) · [bought separately](#4-bought-separately)
· [enclosures](#5-enclosures) · [shopping list](#6-shopping-list-for-one-complete-node)

## 1. The board order (JLCPCB)

**Why JLCPCB:** every part on both boards is matched to its catalogue (LCSC numbers below), and
it fabricates and assembles in one order: 4 layers, the JLC04161H-1080 stack-up, ENIG, 0.5 mm-pitch
QFN, through-hole parts, X-ray inspection. It is the cheapest and fastest option for small runs.
**Fallback: PCBWay** turnkey assembly, rated slightly more consistent by most comparisons and more
expensive; it sources from Digi-Key/Mouser using the MPN column of the same BOM files. (Most
published comparisons are written by board houses, so treat them as indications.)

### Files to upload

| Board | Gerbers + drill | BOM | Placement (CPL) |
|---|---|---|---|
| Sensor node | `pcbs/gos_sensor_node/fab/gos_sensor_node_gerbers.zip` | `.../fab/gos_sensor_node_jlcpcb_bom.csv` | `.../fab/gos_sensor_node_jlcpcb_cpl.csv` |
| LED driver | `pcbs/led_driver/fab/led_driver_gerbers.zip` | `.../fab/led_driver_jlcpcb_bom.csv` | `.../fab/led_driver_jlcpcb_cpl.csv` |

Placement coordinates are measured from each board's bottom-left corner.

### Order-form settings (both boards)

| Setting | Choose |
|---|---|
| Layers | 4 |
| Thickness | 1.6 mm |
| Impedance control / stack-up | Yes, **JLC04161H-1080** (0.076 mm prepreg puts every outer-layer track right above a ground plane) |
| Material | FR-4, TG155 or better |
| Surface finish | **ENIG** |
| Outer / inner copper | 1 oz / 0.5 oz |
| Via covering | Epoxy filled and capped if offered (thermal vias sit in the exposed pads of U1, U2 and the AL8860s), otherwise tented |
| Minimum via | 0.3 mm drill / 0.6 mm pad |
| Colour | Green mask, white silkscreen |
| Mark on PCB | Remove mark |
| Electrical test | Yes |
| PCB assembly | Yes, **Standard** PCBA, top side only |
| Quantity | 5 of each for a first run |

The same settings are printed on each board's User.Comments layer (`docs/*_user_layers.pdf`).

### Before paying: placement review

JLCPCB shows each part on the board. Rotation conventions sometimes differ between KiCad and the
assembly house, so check: pin-1 dots of U1-U7, Q1, Q2 (sensor node) and U1, U2 (LED board) on the
footprint's pin-1 mark; LED and diode stripes on the cathode pad; the stripe of C1 (LED board,
electrolytic) on the side opposite the "+". Rotate any wrong part in JLCPCB's preview tool. The
assembly drawings in `pcbs/*/docs/*_assembly_top.pdf` show the intended orientation.

## 2. Every part on the boards

JLCPCB stock from its parts library; Mouser stock as the backup source for the parts that are
scarce or pre-order at JLCPCB (JLCPCB can buy from other distributors through "global sourcing",
or you can send it parts as consignment).

### Sensor node

| Ref | Part | Manufacturer, MPN | LCSC | JLCPCB stock | Mouser stock |
|---|---|---|---|---|---|
| U4 | nRF52840 radio module | Raytac MDBT50Q-1MV2 | C5118826 | **0, pre-order (about 12 days, about $18)** | Raytac part not listed; Adafruit 4078 (same module): 0, 1,378 on order |
| U1 | Li-ion charger, power path | TI BQ24074RGTR | C54313 | 3,758 | 5,165 |
| U2 | 3.3 V buck | TI TPS62740DSSR | C128606 | 13,263 | 25,177 |
| U3 | cell protection | PUOLOP DW01A | C351410 | 90,868 | - |
| Q1 | dual N-MOSFET (protection) | FUXINSEMI FS8205A, SOT-23-6 | C908265 | 21,717 | - |
| Q2 | P-MOSFET (reverse cell) | Alpha & Omega AO3401A | C15127 | 1,536,782 (Basic) | - |
| U5 | temperature / humidity | Sensirion SHT40-AD1B-R2 | C2909890 | 14,002 | 77,507 |
| U6 | light | ams OSRAM TSL25911FN | C176812 | **28** | 24,846 |
| U7 | USB ESD | ST USBLC6-2SC6 | C7519 | 40,816 | - |
| Y1 | 32.768 kHz crystal | Abracon ABS07-32.768KHZ-9-T | C179635 | 9,375 | - |
| L1 | 2.2 uH, 3 x 3 mm | Sunlord SWPA3015S2R2MT | C43389 | 33,659 | - |
| J1 | USB-C | GCT USB4105-GF-A | C3020560 | 16,850 | 384,480 |
| J2 | SWD 2x5 1.27 mm | Samtec FTSH-105-01-L-DV-K | C5155080 | **pre-order (about 9 days)** | 89,650 |
| J3, J4 | 1x4 2.54 mm header | LXWCONN 254PZ-1x4P-V | C53055674 | 46,506 | - |
| J5 | battery, JST-PH 2-pin | JST S2B-PH-K-S(LF)(SN) | C173752 | 180,893 | - |
| SW1, SW2 | buttons | Omron B3U-1000P | C231329 | 71,328 | - |
| F1 | USB fuse 0.75 A | RUILON SMD1206P075TF | C20987 | 4,512 | - |
| D1 | charge LED (yellow) | Hubei KENTO KT-0603Y | C2287 | 61,078 | - |
| D2 | status LED (green) | Hubei KENTO KT-0603G | C12624 | 259,367 | - |
| TH1 | NTC 10k B3380 | Murata NCP18XH103F03RB | C13564 | 280,553 | - |
| C1, C14 | 1 uF 50 V X5R 0603 | Samsung CL10A105KB8NNNC | C15849 | 13.3 M (Basic) | - |
| C2-C5, C10, C12 | 10 uF 25 V X5R 0805 | Samsung CL21A106KAYNNNE | C15850 | 8.9 M (Basic) | - |
| C6, C7, C11, C13 | 100 nF 50 V X7R 0603 | YAGEO CC0603KRX7R9BB104 | C14663 | 34.5 M (Basic) | - |
| C8, C9 | 12 pF C0G 0603 | Samsung CL10C120JB8NNNC | C38523 | 521,239 (Basic) | - |
| resistors | 0603 1 % thick film | UNI-ROYAL 0603WAF.... | C25803 (100k), C23231 (68k), C4211 (3.0k), C4177 (1.8k), C21190 (1k), C22775 (100R), C22938 (2.2M), C23162 (4.7k), C23186 (5.1k), C25190 (27R) | all above 180,000 | - |

### LED driver board

| Ref | Part | Manufacturer, MPN | LCSC | JLCPCB stock | Mouser stock |
|---|---|---|---|---|---|
| U1, U2 | LED driver | Diodes AL8860MP-13 | C500782 | 228 | 199 (97,500 on order) |
| L1, L2 | 100 uH, 6 x 6 mm | Bourns SRN6045TA-101M | C3222641 | **86** | 6,994 |
| D1-D3 | Schottky 3 A 40 V | MDD SS34 | C8678 | 2.7 M (Basic) | - |
| J1 | 24 V jack, 2.0 mm pin | CUI PJ-063AH | C22434582 | **37, pre-order** | 4,822 |
| J2 | 1x4 2.54 mm header | LXWCONN 254PZ-1x4P-V | C53055674 | 46,506 | - |
| J3, J4 | LED terminal header 3.81 mm | Phoenix Contact 1803277 | C480537 | 1,864 | 27,768 |
| F1 | PTC 1.1 A 30 V | BHFUSE BSMD1206-110-30V | C21714343 | 15,059 | - |
| C1 | 47 uF 50 V electrolytic | ROQANG RVT1H470M0607 | C72523 | 254,389 | - |
| C2, C4 | 10 uF 50 V X7R 1210 | Samsung CL32B106KBJNNNE | C138687 | 137,993 | - |
| C3, C5 | 100 nF 50 V X7R 0603 | YAGEO CC0603KRX7R9BB104 | C14663 | 34.5 M (Basic) | - |
| R1, R3 | 0.30 ohm 1 % | YAGEO RL0603FR-070R3L | C309621 | 22,780 | - |
| R2, R4 | 1.5 k 1 % | UNI-ROYAL 0603WAF1501T5E | C22843 | 2.9 M (Basic) | - |

**Stock risks:** the radio module and the SWD header are pre-order only at JLCPCB; the light sensor
(28), the LED-board inductor (86), the barrel jack (37) and the AL8860 (228) are low. For 5 boards
all are sufficient; if JLCPCB runs out, Mouser has thousands of each except the Raytac module.

## 3. Parts changed because of stock or simulation

| Ref | Was | Now | Why |
|---|---|---|---|
| Q1 (sensor) | VBsemi 8205A-VB, TSSOP-8 | FUXINSEMI FS8205A, SOT-23-6, C908265 | TSSOP part had 15 in stock. Same dual N-MOSFET, 25 mOhm max at 4.5 V. Pinout from the FUXINSEMI datasheet Ver2.1 (1 S1, 2 D, 3 S2, 4 G2, 5 D, 6 G1); schematic symbol and footprint changed to match. |
| L1 (sensor) | Coilcraft LPS3314 2.2 uH | Sunlord SWPA3015S2R2MT, C43389 | Coilcraft part pre-order only. 2.2 uH, 2 A; footprint changed to the Sunlord land pattern. |
| D1 (sensor) | amber LED | KENTO KT-0603Y yellow (590 nm) | No amber 0603 in stock. |
| L1, L2 (LED) | Bourns SRN6045TA-470M, 47 uH | SRN6045TA-101M, 100 uH, C3222641 | LTspice: 47 uH switched the AL8860 above its 1 MHz limit at 333 mA (`simulation/README.md`). Same footprint. |
| R2, R4 (LED) | 2.2 k | 1.5 k, C22843 | LTspice: keeps CTRL at most 0.12 V (below the 0.2 V off threshold) with the cable unplugged. |

All schematics, boards, BOMs, Gerbers and documents were regenerated after each change.

## 4. Bought separately

| Item | Use | Specific part | Where, stock |
|---|---|---|---|
| 18650 Li-ion cell with 2-pin JST-PH lead, protected | sensor node J5 | Adafruit 1781 (3.7 V 2200 mAh, protection circuit, JST-PH) | Mouser 808 in stock, $9.95; adafruit.com |
| 24 V adapter, wall plug | LED board J1 | Mean Well GST36U24-P1J (24 V 1.5 A, plug 5.5 x 2.1 mm centre positive; "U" = North American wall plug, "E" = European) | Mouser 224 in stock |
| LED plugs (screw terminals) x 2 | LED board J3, J4 | Phoenix Contact 1803578 (MC 1,5/2-ST-3,81, 2-pole 3.81 mm, 28-16 AWG) | Mouser 21,913 in stock |
| Blue LEDs x 4 | LED string on J3 | Luxeon Star SP-01-V4: Royal-Blue 448 nm Rebel on 20 mm star, Vf 2.9 V typ / 3.5 V max | luxeonstar.com, 199 in stock, $8.33 |
| Red LEDs x 4 | LED string on J4 | Luxeon Star SP-01-D2: Deep Red 655 nm Rebel on 20 mm star, Vf 2.1 V typ / 2.8 V max, rated 350 mA | luxeonstar.com, built to order in 4 to 10 days, $9.37 |
| Heatsink for the 8 stars | LED strings | any aluminium heatsink of about 2 C/W per channel, with thermal tape or paste | - |
| Cable node to LED board | sensor J4 to LED J2 | 4-wire cable with 2.54 mm 4-pin female housings both ends, pin 1 to pin 1 (GND, PWM blue, PWM red, GND) | any electronics shop online |
| SWD programmer | flashing, once per node | Segger J-Link EDU Mini 8.08.91 (comes with the 10-pin 1.27 mm Cortex cable; non-commercial licence) or a Nordic nRF52840 DK | Mouser 973 in stock |
| Thread radio for the Raspberry Pi | border router | Nordic nRF52840-Dongle | Mouser 4,904 in stock |
| Raspberry Pi | border router and gateway | Raspberry Pi 4 Model B (2 GB or more) or Raspberry Pi 5 | Raspberry Pi approved resellers |
| Cable gland | sensor enclosure, LED cable | LAPP S1507, SKINTOP SL-M 12x1.5 with locknut | Mouser 127 in stock |
| Light window | sensor enclosure lid | clear polycarbonate disc 16 mm x 1.5 mm (cut from sheet, or a laser-cut service) | - |
| Screws | enclosures | sensor: 4 x M2.5x6 + 4 x M3x10 self-tapping; LED: 4 x M3x6 + 4 x M3x10 self-tapping | - |
| USB-C dust plug | sensor enclosure | silicone USB-C port plug, keeps the cut-out closed when not charging | - |
| 5 V USB-C adapter and cable | light node power (cable W5) | any 5 V USB-C wall adapter of at least 1 A | - |
| Blanking plug M12 x 1.5 | climate node enclosure, closes the unused gland hole | nylon blanking plug with sealing ring | - |
| Raspberry Pi case and power supply | gateway | the official case and the official power supply for the Pi model | Raspberry Pi approved resellers |
| USB extension cable | gateway, Dongle (cable W6) | short USB-A male to female extension, into a USB 2.0 port | - |

**Battery polarity:** JST-PH battery leads are not standardised. Adafruit states its cells match
its own boards; no Adafruit document states the pin numbering. Before plugging any cell in, check
with a meter that the red wire lands on J5 pin 1 (marked on the board). If it is reversed, the
board is protected: Q2 blocks a reversed cell (LTspice: 0 V on the board, 8 pA drawn), so nothing
is damaged; swap the two contacts in the plug (a JST-PH pin extractor or a fine needle releases them).

## 5. Enclosures

Print-ready files: `mechanical/print/` (sensor node base and lid, LED driver base and lid). See
`mechanical/README.md` for the design.

| | Recommended | Acceptable | Avoid |
|---|---|---|---|
| Material | **ASA**: UV-stable, 95 C heat resistance, low moisture uptake; suits a warm, humid, lit phytotron for years | PETG (indoor, out of direct sun) | PLA: softens near 55 C and creeps; grow lights and summer temperatures reach that |
| Sensor-node lid colour | black (the light tube must not glow) | | clear or white |
| Settings | 0.2 mm layers, 4 walls, 25 % infill, base open side up, lid upside down | | |

To avoid printing yourself, order the four STL files from an online 3D-printing service (JLCPCB's
JLC3DP can be used from the same account) and ask for ASA; check the material list before ordering.

## 6. Shopping list for one complete node

1. JLCPCB: sensor node board (assembled) + LED driver board (assembled).
2. Mouser: Adafruit 1781 cell, Mean Well GST36U24-P1J, 2 x Phoenix 1803578, LAPP S1507 gland,
   J-Link EDU Mini (once), nRF52840-Dongle (once per gateway).
3. Luxeon Star LEDs: 4 x SP-01-V4, 4 x SP-01-D2, plus a heatsink.
4. 3D prints: four STL files in ASA.
5. Small items: 4-wire 2.54 mm cable, screws, polycarbonate disc, USB-C dust plug.
6. Raspberry Pi (once per gateway).

Then follow `documentation/bring_up.md`.
