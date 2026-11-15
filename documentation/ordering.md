# Ordering the boards (sensor node rev 3.1, LED driver rev 1.0)

Both boards are ordered fully assembled, so nothing needs soldering. Everything is ordered
online; nothing has to be bought in a store.

## Manufacturer: JLCPCB (fabrication and assembly)

Why JLCPCB:

- Every part on both boards is matched to its catalogue (LCSC part numbers). JLCPCB buys them,
  builds the bare boards and assembles them in one order.
- It offers everything these boards need: 4 layers, the JLC04161H-1080 stack-up, ENIG finish,
  0.5 mm-pitch QFN assembly, through-hole assembly, and X-ray inspection of QFN parts.
- It is the cheapest option for small runs and has the fastest standard lead times.

Fallback: **PCBWay** turnkey assembly. Most comparisons rate PCBWay as slightly more
consistent in quality, at a higher price. It sources parts from Digi-Key or Mouser, so the
manufacturer part numbers (MPN column) in the same BOM files work there too. Use it if
JLCPCB cannot get a part. These comparisons are mostly written by board houses, so treat
them as indications, not measurements.

## Files to upload

| Board | Gerber zip | BOM | Placement (CPL) |
|---|---|---|---|
| Sensor node | `pcbs/gos_sensor_node/fab/gos_sensor_node_gerbers.zip` | `.../fab/gos_sensor_node_jlcpcb_bom.csv` | `.../fab/gos_sensor_node_jlcpcb_cpl.csv` |
| LED driver | `pcbs/led_driver/fab/led_driver_gerbers.zip` | `.../fab/led_driver_jlcpcb_bom.csv` | `.../fab/led_driver_jlcpcb_cpl.csv` |

Placement coordinates are measured from each board's bottom-left corner. The same
fabrication settings are printed in the board files on the User.Comments layer (see
`docs/*_user_layers.pdf`).

## Order form settings (both boards)

| Setting | Choose |
|---|---|
| Layers | 4 |
| Thickness | 1.6 mm |
| Impedance control / stack-up | Yes, **JLC04161H-1080**. The design does not need a specific impedance; this stack-up puts each outer layer 0.076 mm from a ground plane, which keeps noise low. |
| Material | FR-4, TG155 or better |
| Surface finish | **ENIG** (flat pads for the 0.5 mm-pitch charger and buck chips) |
| Outer / inner copper | 1 oz / 0.5 oz |
| Via covering | Epoxy filled and capped if offered (vias sit inside the exposed pads of U1, U2 and the AL8860s); otherwise tented |
| Minimum via | 0.3 mm drill / 0.6 mm pad |
| Colour | Green mask, white silkscreen |
| Mark on PCB | Remove mark, or "specify location" (no place has been reserved, so remove is simpler) |
| Electrical test | Yes (free) |
| PCB assembly | Yes, **Standard** PCBA, top side only |
| Tooling holes | Added by JLCPCB |
| Confirm parts placement | Yes. Check the rotation preview before paying (see below). |

Quantity: 5 of each is a good first run.

## Before paying: placement review

JLCPCB shows each part on the board. Check these, because part rotation conventions sometimes
differ between KiCad and the assembly house:

- U1 (BQ24074), U2 (TPS62740), U3 (DW01A), U4 (radio module), U5 (SHT40), U6 (TSL2591),
  U7 (USBLC6) and Q1/Q2: the pin 1 dot sits on the pin 1 mark of the footprint.
- D1, D2 (LEDs) and the SS34 diodes: cathode stripe on the cathode pad.
- C1 on the LED board (electrolytic): the stripe is negative, opposite the "+" on the silkscreen.

If one is wrong, rotate it in JLCPCB's preview tool. The files stay as they are.

## Part availability (JLCPCB catalogue, 2026-11-14)

All parts are listed with LCSC numbers in the BOM files. Some were in short supply or
available only on pre-order:

| Ref | Part | LCSC | Stock on 2026-11-14 | Note |
|---|---|---|---|---|
| U4 | Raytac MDBT50Q-1MV2 | C5118826 | 0, pre-order about 12 days | JLCPCB buys it for the order; about $18 each |
| J2 | Samtec FTSH-105-01-L-DV-K (SWD) | C5155080 | pre-order, about 9 days | Only needed to program the board |
| U6 | ams TSL25911FN | C176812 | 28 | Enough for a few boards; order soon |
| J1 (LED) | CUI PJ-063AH | C22434582 | 37, pre-order | |
| U1-U2 (LED) | Diodes AL8860MP-13 | C500782 | 228 | |

Changed from the original design because of stock:

| Ref | Was | Now | Why |
|---|---|---|---|
| Q1 | VBsemi 8205A-VB, TSSOP-8 (15 in stock) | FUXINSEMI FS8205A, SOT-23-6, C908265 (21,717 in stock) | Same dual N-MOSFET; 25 mOhm max at 4.5 V; pinout from the FUXINSEMI datasheet Ver2.1 (1 S1, 2 D, 3 S2, 4 G2, 5 D, 6 G1) |
| L1 | Coilcraft LPS3314 2.2 uH (pre-order only) | Sunlord SWPA3015S2R2MT, C43389 | 2.2 uH, 2 A, 3 x 3 mm; land pattern from Sunlord's datasheet |
| D1 | amber LED | KENTO KT-0603Y yellow (590 nm), C2287 | No amber 0603 in stock |

Every other part had thousands in stock.

## Bought separately (not on the boards)

Order these online as well (Digi-Key, Mouser, LCSC or Amazon):

| Item | For | Notes |
|---|---|---|
| 18650 Li-ion cell with a JST-PH 2.0 mm 2-pin lead | sensor node J5 | Brand-name cell (Samsung, LG, Molicel). **Check the polarity before plugging in: J5 pin 1 is positive (marked on the board).** Lead wiring is not standardised. |
| Phoenix Contact MC 1,5/2-ST-3,81 plug (1803578), 2 pcs | LED board J3, J4 | Screw plugs for the LED string wires. Match by part number; it was not looked up in a catalogue. |
| 4-wire 2.54 mm female-female jumper cable, 4-pin housing | sensor node J4 to LED board J2 | Pin 1 to pin 1 (GND, PWM blue, PWM red, GND) |
| 24 V DC adapter, 1 A or more, 5.5 x 2.1 mm centre-positive plug | LED board J1 | The jack has a 2.0 mm pin: a 5.5 x 2.1 mm plug fits; a 5.5 x 2.5 mm plug does not make contact. |
| LEDs on star heatsinks: 4 blue 450 nm, 4 red 660 nm, about 1 W (350 mA) each | LED board strings | Check the string voltage stays below about 20 V (see `pcbs/led_driver/README.md`). |
| SWD probe with a 10-pin 1.27 mm cable (J-Link, or an nRF52 DK) | programming | Once per board |
| Enclosure printed in ASA, M12 cable gland, 4 x M2.5x6 and 4 x M3x10 self-tapping screws, 16 mm x 1.5 mm clear polycarbonate disc | enclosure | See `mechanical/README.md` |

## After the boards arrive

Follow `documentation/bring_up.md`.
