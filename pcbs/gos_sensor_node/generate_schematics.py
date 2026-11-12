#!/usr/bin/env python3
"""Generate KiCad 9.0 schematic files for G.O.S. Sensor Node power and MCU sheets.
Run once, then delete this script. The generated .kicad_sch files are the deliverables."""

import uuid as _uuid

def uid():
    return str(_uuid.uuid4())

# ============================================================
# Reusable symbol library definitions (compact)
# ============================================================
def sym_R():
    return '''(symbol "Device:R"
(pin_numbers (hide yes))(pin_names (offset 0)(hide yes))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "R" (at 2.032 0 90)(effects (font (size 1.27 1.27))))
(property "Value" "R" (at 0 0 90)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at -1.778 0 90)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "~" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "Resistor" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "R_0_1"(rectangle (start -1.016 -2.54)(end 1.016 2.54)(stroke (width 0.254)(type default))(fill (type none))))
(symbol "R_1_1"
(pin passive line (at 0 3.81 270)(length 1.27)(name "~" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27)))))
(pin passive line (at 0 -3.81 90)(length 1.27)(name "~" (effects (font (size 1.27 1.27))))(number "2" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''

def sym_C():
    return '''(symbol "Device:C"
(pin_numbers (hide yes))(pin_names (offset 0.254)(hide yes))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "C" (at 0.635 2.54 0)(effects (font (size 1.27 1.27))(justify left)))
(property "Value" "C" (at 0.635 -2.54 0)(effects (font (size 1.27 1.27))(justify left)))
(property "Footprint" "" (at 0.9652 -3.81 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "~" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "Capacitor" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "C_0_1"
(polyline (pts (xy -2.032 -0.762)(xy 2.032 -0.762))(stroke (width 0.508)(type default))(fill (type none)))
(polyline (pts (xy -2.032 0.762)(xy 2.032 0.762))(stroke (width 0.508)(type default))(fill (type none))))
(symbol "C_1_1"
(pin passive line (at 0 3.81 270)(length 2.794)(name "~" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27)))))
(pin passive line (at 0 -3.81 90)(length 2.794)(name "~" (effects (font (size 1.27 1.27))))(number "2" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''

def sym_L():
    return '''(symbol "Device:L"
(pin_numbers (hide yes))(pin_names (offset 1.016)(hide yes))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "L" (at -1.016 0 90)(effects (font (size 1.27 1.27))))
(property "Value" "L" (at 1.524 0 90)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "~" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "Inductor" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "L_0_1"
(arc (start 0 -2.54)(mid 0.6323 -1.905)(end 0 -1.27)(stroke (width 0)(type default))(fill (type none)))
(arc (start 0 -1.27)(mid 0.6323 -0.635)(end 0 0)(stroke (width 0)(type default))(fill (type none)))
(arc (start 0 0)(mid 0.6323 0.635)(end 0 1.27)(stroke (width 0)(type default))(fill (type none)))
(arc (start 0 1.27)(mid 0.6323 1.905)(end 0 2.54)(stroke (width 0)(type default))(fill (type none))))
(symbol "L_1_1"
(pin passive line (at 0 3.81 270)(length 1.27)(name "1" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27)))))
(pin passive line (at 0 -3.81 90)(length 1.27)(name "2" (effects (font (size 1.27 1.27))))(number "2" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''

def sym_D():
    return '''(symbol "Device:D_Schottky"
(pin_numbers (hide yes))(pin_names (offset 1.016)(hide yes))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "D" (at 0 2.54 0)(effects (font (size 1.27 1.27))))
(property "Value" "D_Schottky" (at 0 -2.54 0)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "~" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "Schottky diode" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "D_Schottky_0_1"
(polyline (pts (xy -1.27 -1.27)(xy -1.27 1.27))(stroke (width 0.254)(type default))(fill (type none)))
(polyline (pts (xy 1.27 -1.27)(xy 1.27 1.27)(xy -1.27 0)(xy 1.27 -1.27))(stroke (width 0.254)(type default))(fill (type none))))
(symbol "D_Schottky_1_1"
(pin passive line (at -3.81 0 0)(length 2.54)(name "K" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27)))))
(pin passive line (at 3.81 0 180)(length 2.54)(name "A" (effects (font (size 1.27 1.27))))(number "2" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''

def sym_pwr(name, direction="90", y_off=3.556):
    kw = "global power"
    if name == "GND":
        return f'''(symbol "power:GND"
(power)(pin_names (offset 0))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "#PWR" (at 0 -6.35 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Value" "GND" (at 0 -3.81 0)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "GND_0_1"(polyline (pts (xy 0 0)(xy 0 -1.27)(xy 1.27 -1.27)(xy 0 -2.54)(xy -1.27 -1.27)(xy 0 -1.27))(stroke (width 0)(type default))(fill (type none))))
(symbol "GND_1_1"(pin power_in line (at 0 0 270)(length 0)(hide yes)(name "GND" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''
    else:
        return f'''(symbol "power:{name}"
(power)(pin_names (offset 0))
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "#PWR" (at 0 -3.81 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Value" "{name}" (at 0 {y_off} 0)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "{name}_0_1"
(polyline (pts (xy -0.762 1.27)(xy 0 2.54))(stroke (width 0)(type default))(fill (type none)))
(polyline (pts (xy 0 2.54)(xy 0.762 1.27))(stroke (width 0)(type default))(fill (type none)))
(polyline (pts (xy 0 0)(xy 0 2.54))(stroke (width 0)(type default))(fill (type none))))
(symbol "{name}_1_1"(pin power_in line (at 0 0 90)(length 0)(hide yes)(name "{name}" (effects (font (size 1.27 1.27))))(number "1" (effects (font (size 1.27 1.27))))))
(embedded_fonts no))'''

def make_ic_sym(name, pins, w=7.62, h=7.62, desc=""):
    """Create inline IC symbol. pins = [(num, name, x, y, angle, ptype)]"""
    pin_lines = []
    for num, pname, px, py, angle, ptype in pins:
        pin_lines.append(
            f'(pin {ptype} line (at {px} {py} {angle})(length 2.54)'
            f'(name "{pname}" (effects (font (size 1.27 1.27))))'
            f'(number "{num}" (effects (font (size 1.27 1.27)))))')
    pstr = "\n".join(pin_lines)
    return f'''(symbol "Custom:{name}"
(exclude_from_sim no)(in_bom yes)(on_board yes)
(property "Reference" "U" (at -{w} {h+1.27} 0)(effects (font (size 1.27 1.27))(justify left)))
(property "Value" "{name}" (at 0 {h+1.27} 0)(effects (font (size 1.27 1.27))(justify left)))
(property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "~" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "{desc}" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))
(symbol "{name}_0_1"
(rectangle (start -{w} {h})(end {w} -{h})(stroke (width 0.254)(type default))(fill (type background))))
(symbol "{name}_1_1"
{pstr})
(embedded_fonts no))'''

def comp(lib_id, ref, val, x, y, fp, ds, desc, pins, path, rot=0):
    """Generate component placement."""
    pin_str = "\n".join(f'(pin "{p}" (uuid "{uid()}"))' for p in pins)
    rot_str = f"\n\t\t(at {x} {y} {rot})" if rot == 0 else f"\n\t\t(at {x} {y} {rot})"
    return f'''(symbol
(lib_id "{lib_id}"){rot_str}
(unit 1)(exclude_from_sim no)(in_bom yes)(on_board yes)(dnp no)
(uuid "{uid()}")
(property "Reference" "{ref}" (at {x} {y-3.81} 0)(effects (font (size 1.27 1.27))))
(property "Value" "{val}" (at {x} {y-6.35} 0)(effects (font (size 1.27 1.27))))
(property "Footprint" "{fp}" (at {x} {y} 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "{ds}" (at {x} {y} 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "{desc}" (at {x} {y} 0)(effects (font (size 1.27 1.27))(hide yes)))
{pin_str}
(instances (project "" (path "{path}" (reference "{ref}")(unit 1)))))'''

def pwr_comp(lib_id, ref, val, x, y, path):
    return f'''(symbol
(lib_id "{lib_id}")
(at {x} {y} 0)(unit 1)(exclude_from_sim no)(in_bom yes)(on_board yes)(dnp no)
(uuid "{uid()}")
(property "Reference" "{ref}" (at {x} {y+3.81} 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Value" "{val}" (at {x} {y-3.81} 0)(effects (font (size 1.27 1.27))))
(property "Footprint" "" (at {x} {y} 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Datasheet" "" (at {x} {y} 0)(effects (font (size 1.27 1.27))(hide yes)))
(property "Description" "" (at {x} {y} 0)(effects (font (size 1.27 1.27))))
(pin "1" (uuid "{uid()}"))
(instances (project "" (path "{path}" (reference "{ref}")(unit 1)))))'''

def wire(x1, y1, x2, y2):
    return f'(wire (pts (xy {x1} {y1})(xy {x2} {y2}))(stroke (width 0)(type default))(uuid "{uid()}"))'

def label(name, x, y, angle=0):
    return f'(label "{name}" (at {x} {y} {angle})(effects (font (size 1.27 1.27))(justify left bottom))(uuid "{uid()}"))'

def hlabel(name, shape, x, y, angle=0, just="left"):
    return f'(hierarchical_label "{name}" (shape {shape})(at {x} {y} {angle})(effects (font (size 1.27 1.27))(justify {just}))(uuid "{uid()}"))'

def note(txt, x, y):
    return f'(text "{txt}"\n(exclude_from_sim no)(at {x} {y} 0)(effects (font (size 1.27 1.27))(justify left))(uuid "{uid()}"))'

ROOT = "/c897bbcf-82b3-4b94-b14c-2b8219114053"
PWR_PATH = f"{ROOT}/e4cf0f50-5583-4471-a71d-bf2f85d44f31"
MCU_PATH = f"{ROOT}/4cf87c83-fa01-4d12-9c1c-c6c5074a6016"

# ===========================================================
# POWER SHEET
# ===========================================================
def generate_power():
    # TPS62740 pins: VIN, SW, VOUT, EN, PG, VSEL0-3, GND, PAD
    tps_pins = [
        ("1","VIN",  -10.16, 5.08, 0,"power_in"),
        ("2","EN",   -10.16, 0, 0,"input"),
        ("3","VSEL0",-10.16,-2.54,0,"input"),
        ("4","VSEL1",-10.16,-5.08,0,"input"),
        ("5","GND",   0,-10.16,90,"power_in"),
        ("6","SW",   10.16, 5.08,180,"output"),
        ("7","VOUT", 10.16, 2.54,180,"power_out"),
        ("8","PG",   10.16,-2.54,180,"open_collector"),
        ("9","PAD",   0,-10.16,90,"passive"),
    ]
    # BQ24075 pins (simplified)
    bq_pins = [
        ("1","IN",   -10.16, 5.08, 0,"power_in"),
        ("2","ILIM", -10.16, 2.54, 0,"input"),
        ("3","ISET", -10.16, 0,    0,"input"),
        ("4","CE",   -10.16,-2.54, 0,"input"),
        ("5","TS",   -10.16,-5.08, 0,"input"),
        ("6","VSS",   0,-10.16,90,"power_in"),
        ("7","OUT",  10.16, 5.08,180,"power_out"),
        ("8","PGOOD",10.16, 0,   180,"open_collector"),
        ("9","TMR",  10.16,-2.54,180,"passive"),
        ("10","SYSOFF",10.16,-5.08,180,"input"),
    ]
    # DW01A pins
    dw_pins = [
        ("1","OD",  -7.62, 2.54, 0,"output"),
        ("2","CS",  -7.62, 0,    0,"input"),
        ("3","OC",  -7.62,-2.54, 0,"output"),
        ("4","TD",   7.62,-2.54,180,"passive"),
        ("5","VCC",  0, 7.62,  270,"power_in"),
        ("6","GND",  0,-7.62,   90,"power_in"),
    ]

    parts = []
    parts.append(f'''(kicad_sch
(version 20250114)(generator "eeschema")(generator_version "9.0")
(uuid "0b291103-ecdc-4a66-a888-5023279286fe")
(paper "A4")
(title_block
(title "G.O.S. Sensor Node - Power Management")
(date "2026-02-17")(rev "2.0")
(company "Queen's University ePOWER Lab")
(comment 1 "BQ24075 charger (R8=1.2k, 742mA) + TPS62740 buck (3.3V)")
(comment 2 "DW01A protection (2.4V cutoff) + 18650 Li-Ion"))
(lib_symbols
{sym_R()}
{sym_C()}
{sym_L()}
{sym_D()}
{sym_pwr("+3.3V")}
{sym_pwr("GND")}
{sym_pwr("VBATT")}
{make_ic_sym("TPS62740", tps_pins, desc="3.3V 300mA buck, 360nA Iq")}
{make_ic_sym("BQ24075", bq_pins, desc="Li-Ion charger, USB power-path, 1.5A")}
{make_ic_sym("DW01A", dw_pins, 7.62, 7.62, "Battery protection OVP/ODP/OCP 2.4V cutoff")}
)''')

    # Notes
    parts.append(note("18650 Li-Ion Battery\\n3.0V-4.2V, 3000mAh\\nJ1: Battery connector", 20, 15))
    parts.append(note("BQ24075 Charger\\nR8=1.2k (ISET, 742mA)\\nR9=10k (ILIM, 500mA USB)\\nR10=10k NTC (TS)", 70, 15))
    parts.append(note("TPS62740 Buck\\nVIN=VBATT -> VOUT=3.3V\\nL1=2.2uH, C18=4.7uF, C19=10uF", 140, 15))
    parts.append(note("DW01A Protection\\nOVP=4.25V, ODP=2.40V\\nWith dual MOSFET Q1", 20, 100))

    # Wires - simplified topology connections
    wires = [
        # Battery connector to protection
        wire(35, 30, 50, 30), wire(35, 35, 50, 35),
        # Protection to charger
        wire(50, 30, 75, 30), wire(75, 30, 75, 35),
        # Charger output to buck input
        wire(100, 35, 120, 35), wire(120, 35, 135, 35),
        # Buck output
        wire(160, 42, 175, 42), wire(175, 42, 175, 35),
    ]
    parts.extend(wires)

    # Labels
    parts.append(label("VBATT", 50, 30))
    parts.append(label("VSYS", 120, 35))
    parts.append(label("VDD_3V3", 175, 35))
    parts.append(hlabel("VUSB", "input", 75, 25, 0))

    # Component instances
    fp02 = "Resistor_SMD:R_0402_1005Metric"
    fp06 = "Capacitor_SMD:C_0603_1608Metric"
    fp04c = "Capacitor_SMD:C_0402_1005Metric"

    # BQ24075
    parts.append(comp("Custom:BQ24075","U5","BQ24075RGTR",85,40,
        "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm",
        "https://www.ti.com/lit/ds/symlink/bq24075.pdf",
        "Li-Ion charger, USB power-path, R8=1.2k for 742mA",
        ["1","2","3","4","5","6","7","8","9","10"], PWR_PATH))

    # TPS62740
    parts.append(comp("Custom:TPS62740","U4","TPS62740DSSR",150,40,
        "Package_BGA:Texas_DSBGA-9_0.8x0.8mm_Layout3x3_P0.5mm",
        "https://www.ti.com/lit/ds/symlink/tps62740.pdf",
        "3.3V buck, 360nA Iq, 300mA",
        ["1","2","3","4","5","6","7","8","9"], PWR_PATH))

    # DW01A
    parts.append(comp("Custom:DW01A","U6","DW01A-G",40,115,
        "Package_TO_SOT_SMD:SOT-23-6",
        "https://datasheet.lcsc.com/szlcsc/DW01A-G_C181058.pdf",
        "Battery protection, ODP=2.40V",
        ["1","2","3","4","5","6"], PWR_PATH))

    # Passives
    parts.append(comp("Device:R","R8","1.2k",80,60,fp02,"~","BQ24075 ISET (742mA, KISET=890)",["1","2"],PWR_PATH))
    parts.append(comp("Device:R","R9","10k",88,60,fp02,"~","BQ24075 ILIM (500mA USB)",["1","2"],PWR_PATH))
    parts.append(comp("Device:R","R10","10k NTC",96,60,fp02,"~","BQ24075 TS battery temp",["1","2"],PWR_PATH))
    parts.append(comp("Device:R","R7","10k",165,55,fp02,"~","TPS62740 PG pull-up",["1","2"],PWR_PATH))
    parts.append(comp("Device:R","R1","1M",45,75,fp02,"~","ADC voltage divider upper (batt monitor)",["1","2"],PWR_PATH))
    parts.append(comp("Device:R","R2","1M",45,90,fp02,"~","ADC voltage divider lower (batt monitor)",["1","2"],PWR_PATH))

    # Caps
    parts.append(comp("Device:C","C18","4.7uF",135,55,fp06,"~","TPS62740 input CIN, X5R 10V",["1","2"],PWR_PATH))
    parts.append(comp("Device:C","C19","10uF",175,55,fp06,"~","TPS62740 output COUT, X5R 10V",["1","2"],PWR_PATH))
    parts.append(comp("Device:C","C20","10uF",70,55,fp06,"~","BQ24075 input PMID, X5R 10V",["1","2"],PWR_PATH))
    parts.append(comp("Device:C","C21","10uF",105,55,fp06,"~","BQ24075 output BAT, X5R 10V",["1","2"],PWR_PATH))
    parts.append(comp("Device:C","C22","1uF",113,55,fp04c,"~","BQ24075 bypass, X7R",["1","2"],PWR_PATH))

    # Inductor
    parts.append(comp("Device:L","L1","2.2uH",155,55,"Inductor_SMD:L_0805_2012Metric","~","TPS62740 buck inductor, Isat>500mA",["1","2"],PWR_PATH))

    # Diodes
    parts.append(comp("Device:D_Schottky","D3","PMEG2010AEH",55,45,"Diode_SMD:D_SOD-323","~","Reverse polarity BAT protect",["1","2"],PWR_PATH))
    parts.append(comp("Device:D_Schottky","D4","PMEG2010AEH",60,80,"Diode_SMD:D_SOD-323","~","LED_VIN reverse protect",["1","2"],PWR_PATH))

    # Power symbols
    parts.append(pwr_comp("power:GND","#PWR010","GND",85,60, PWR_PATH))
    parts.append(pwr_comp("power:GND","#PWR011","GND",150,55, PWR_PATH))
    parts.append(pwr_comp("power:+3.3V","#PWR012","+3.3V",175,30, PWR_PATH))
    parts.append(pwr_comp("power:VBATT","#PWR013","VBATT",35,25, PWR_PATH))

    parts.append("(embedded_fonts no)\n)")

    return "\n".join(parts)


# ===========================================================
# MCU SHEET
# ===========================================================
def generate_mcu():
    # nRF52840 pins - key functional pins only
    nrf_pins = [
        # Power
        ("B1","VDDH",    -17.78, 15.24, 0,"power_in"),
        ("A13","VDD",    -17.78, 12.7,  0,"power_in"),
        ("B15","VDD",    -17.78, 10.16, 0,"power_in"),
        ("C11","VDD",    -17.78, 7.62,  0,"power_in"),
        ("D12","VDD",    -17.78, 5.08,  0,"power_in"),
        ("D23","VSS",     0,   -20.32, 90,"power_in"),
        ("E25","VSS_PAD", 0,   -20.32, 90,"passive"),
        # Decoupling
        ("D1","DEC1",    -17.78, 0,     0,"passive"),
        ("B4","DEC3",    -17.78,-2.54,  0,"passive"),
        ("A3","DEC4",    -17.78,-5.08,  0,"passive"),
        ("D2","DEC5",    -17.78,-7.62,  0,"passive"),
        ("B2","DEC6",    -17.78,-10.16, 0,"passive"),
        ("D3","DECUSB",  -17.78,-12.7,  0,"passive"),
        # Crystal
        ("B16","XC1",    -17.78,-17.78, 0,"passive"),
        ("A15","XC2",    -17.78,-20.32, 0,"passive"),
        # GPIO - I2C
        ("W2","P0.26",   17.78, 15.24,180,"bidirectional"),
        ("W3","P0.27",   17.78, 12.7, 180,"bidirectional"),
        # GPIO - PWM
        ("Y5","P0.13",   17.78, 7.62, 180,"output"),
        ("W6","P0.14",   17.78, 5.08, 180,"output"),
        # GPIO - Interrupt
        ("Y7","P0.15",   17.78, 2.54, 180,"input"),
        # ADC
        ("B9","AIN0/P0.02",17.78, 0,  180,"passive"),
        # UART
        ("T2","P0.06",   17.78,-5.08, 180,"output"),
        ("U1","P0.08",   17.78,-7.62, 180,"input"),
        # SWD
        ("AC24","SWDIO", 17.78,-12.7, 180,"bidirectional"),
        ("AC20","SWDCLK",17.78,-15.24,180,"input"),
        # Reset
        ("AD8","P0.18/nRESET",17.78,-17.78,180,"bidirectional"),
        # Antenna
        ("H23","ANT",    17.78,-22.86,180,"passive"),
    ]

    parts = []
    parts.append(f'''(kicad_sch
(version 20250114)(generator "eeschema")(generator_version "9.0")
(uuid "555b6b80-e86d-4852-bec7-6d53debe662e")
(paper "A3")
(title_block
(title "G.O.S. Sensor Node - nRF52840 MCU")
(date "2026-02-17")(rev "2.0")
(company "Queen's University ePOWER Lab")
(comment 1 "nRF52840-QIAA-R7 (aQFN-73, 7x7mm)")
(comment 2 "13 decoupling caps, 2 crystals, ADC voltage divider"))
(lib_symbols
{sym_R()}
{sym_C()}
{sym_pwr("+3.3V")}
{sym_pwr("GND")}
{make_ic_sym("nRF52840", nrf_pins, 17.78, 20.32, "Cortex-M4F, 802.15.4, BLE, aQFN-73")}
)''')

    # Notes
    parts.append(note("nRF52840-QIAA-R7\\naQFN-73 (7x7mm)\\nCortex-M4F @ 64MHz\\n802.15.4 + BLE 5.0\\n1MB Flash, 256KB RAM", 180, 20))
    parts.append(note("Decoupling per Nordic PS v1.8 section 6.6:\\nC1=4.7uF VDDH | C2-C5=100nF VDD x4\\nC6=100nF DEC1 | C7=1uF DEC4\\nC8=47nF DEC4 | C9=100nF DEC3\\nC10=1uF DEC5 | C11=4.7uF DEC6\\nC12=4.7uF DECUSB | C13=1uF GPIO", 180, 60))
    parts.append(note("32MHz HFXO: Y1 NX3225GD\\nCL=8pF, C14=C15=12pF (C0G)\\nCstray ~2pF", 180, 100))
    parts.append(note("32.768kHz LFXO: Y2 ABS07\\nCL=7pF, C16=C17=6.8pF (C0G)\\nCstray ~4pF", 180, 120))

    fp02 = "Resistor_SMD:R_0402_1005Metric"
    fp04c = "Capacitor_SMD:C_0402_1005Metric"

    # nRF52840 MCU
    parts.append(comp("Custom:nRF52840","U1","nRF52840-QIAA-R7",80,65,
        "Package_DFN_QFN:QFN-73-1EP_7x7mm_P0.4mm_EP5.3x5.3mm",
        "https://infocenter.nordicsemi.com/pdf/nRF52840_PS_v1.8.pdf",
        "Cortex-M4F MCU, 802.15.4 + BLE, aQFN-73",
        [p[0] for p in nrf_pins], MCU_PATH))

    # Decoupling caps C1-C13
    caps = [
        ("C1","4.7uF","VDDH supply decouple, X5R"),
        ("C2","100nF","VDD pin 1 decouple, X7R"),
        ("C3","100nF","VDD pin 2 decouple, X7R"),
        ("C4","100nF","VDD pin 3 decouple, X7R"),
        ("C5","100nF","VDD pin 4 decouple, X7R"),
        ("C6","100nF","DEC1 internal reg, X7R"),
        ("C7","1uF","DEC4 REG1 1.3V bulk, X7R"),
        ("C8","47nF","DEC4 HF bypass, X7R"),
        ("C9","100nF","DEC3 internal reg, X7R"),
        ("C10","1uF","DEC5 DC/DC output, X5R"),
        ("C11","4.7uF","DEC6 DC/DC bulk, X5R"),
        ("C12","4.7uF","DECUSB 3.3V LDO, X5R"),
        ("C13","1uF","GPIO port decouple, X7R"),
    ]
    for i, (ref, val, desc) in enumerate(caps):
        x = 140 + (i % 4) * 12
        y = 45 + (i // 4) * 15
        parts.append(comp("Device:C", ref, val, x, y, fp04c, "~", desc, ["1","2"], MCU_PATH))

    # Crystal caps
    parts.append(comp("Device:C","C14","12pF",35,90,fp04c,"~","32MHz HFXO load, C0G/NP0",["1","2"],MCU_PATH))
    parts.append(comp("Device:C","C15","12pF",45,90,fp04c,"~","32MHz HFXO load, C0G/NP0",["1","2"],MCU_PATH))
    parts.append(comp("Device:C","C16","6.8pF",35,115,fp04c,"~","32.768kHz LFXO load, C0G/NP0",["1","2"],MCU_PATH))
    parts.append(comp("Device:C","C17","6.8pF",45,115,fp04c,"~","32.768kHz LFXO load, C0G/NP0",["1","2"],MCU_PATH))

    # Ferrite bead
    parts.append(comp("Device:R","FB1","600R@100MHz",140,85,fp02,"~","Analog VDD filter for ADC, BLM15AG601",["1","2"],MCU_PATH))

    # Hierarchical labels
    parts.append(hlabel("I2C_SDA","bidirectional",110,80,0))
    parts.append(hlabel("I2C_SCL","input",110,83,0))
    parts.append(hlabel("PWM_BLUE","output",110,86,0))
    parts.append(hlabel("PWM_RED","output",110,89,0))
    parts.append(hlabel("TSL_INT","input",110,92,0))
    parts.append(hlabel("BATT_ADC","passive",110,95,0))
    parts.append(hlabel("UART_TX","output",110,100,0))
    parts.append(hlabel("UART_RX","input",110,103,0))
    parts.append(hlabel("SWDIO","bidirectional",110,108,0))
    parts.append(hlabel("SWDCLK","input",110,111,0))
    parts.append(hlabel("NRESET","bidirectional",110,114,0))
    parts.append(hlabel("ANT","output",110,119,0))

    # Power symbols
    parts.append(pwr_comp("power:+3.3V","#PWR031","+3.3V",55,35, MCU_PATH))
    parts.append(pwr_comp("power:GND","#PWR032","GND",80,95, MCU_PATH))

    # Wires - key connections
    wires = [
        wire(55, 35, 55, 45),  # VDD rail
        wire(80, 90, 80, 95),  # GND
    ]
    parts.extend(wires)

    parts.append("(embedded_fonts no)\n)")
    return "\n".join(parts)


# ===========================================================
# MAIN
# ===========================================================
if __name__ == "__main__":
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))

    pwr = generate_power()
    with open(os.path.join(script_dir, "power.kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write(pwr)
    print(f"[OK] power.kicad_sch  ({len(pwr)} bytes)")

    mcu = generate_mcu()
    with open(os.path.join(script_dir, "MCU.kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write(mcu)
    print(f"[OK] MCU.kicad_sch    ({len(mcu)} bytes)")

    print("\nDone! Open gos_sensor_node.kicad_sch in KiCad 9.0 to verify.")
