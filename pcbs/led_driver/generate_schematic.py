#!/usr/bin/env python3
"""G.O.S. LED driver board rev 1.0 schematic generator (KiCad 9).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" generate_schematic.py --verify

Reuses the sensor node generator (pcbs/gos_sensor_node/generate_schematics.py),
so --verify runs the same checks: ERC with every severity, exported netlist
equal to the nets declared here, and every symbol pin present as a footprint pad.

Two constant-current channels (blue 450 nm, red 660 nm), each an AL8860 buck
driver, from a 24 V adapter. LED strings are off-board on star heatsinks and
plug into J3 / J4. The sensor node's J4 header drives CTRL directly with 3.3 V
PWM. Ratings and the reasons for each value: README.md.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gos_sensor_node"))
import generate_schematics as gs  # noqa: E402

gs.HERE = HERE
gs.PROJECT = "led_driver"
gs.ROOT_UUID = "6b1c2e8a-6f0e-4d53-9a7e-2f4c4d1a0b01"
gs.REV = "1.0"

# ---------------------------------------------------------------- design values
R_SENSE = "0R30 1%"     # AL8860: I = 0.1 V / R -> 333 mA per channel (datasheet table: 0.3 ohm = 333 mA)
L_VALUE = "100uH"       # datasheet range 33 to 100 uH; 47 uH would switch above the 1 MHz limit at 333 mA (simulation/led_channel.cir)
R_CTRL_PULLDOWN = "1.5k"  # holds CTRL below 0.2 V (off) when unplugged: AL8860 shutdown current is 80 uA max,
                          # so any internal pull-up gives at most 80 uA x 1.5k = 0.12 V (simulation/ctrl_failsafe.cir)


def channel(s, name, x):
    """One AL8860 buck channel at sheet column x."""
    u = "U1" if name == "BLUE" else "U2"
    s.part(u, "Driver_LED:AL8860MP", x + 30.48, 76.2, "AL8860MP",
           "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.5x1.8mm",
           {"VIN": "VIN", "GND": "GND", "SET": f"SET_{name}", "CTRL": f"CTRL_{name}", "SW": f"SW_{name}"},
           nc=["NC"], MPN="AL8860MP-13", Manufacturer="Diodes Incorporated")
    s.R(R_SENSE, "VIN", f"SET_{name}", x + 60.96, 63.5)
    s.part(gs.next_ref("D"), "Diode:SS34", x + 60.96, 101.6, "SS34", "Diode_SMD:D_SMA",
           {"A": f"SW_{name}", "K": "VIN"}, stub=2.54,
           Description="Schottky 40 V 3 A, freewheel diode")
    s.part(gs.next_ref("L"), "Device:L", x + 78.74, 101.6, L_VALUE, "Inductor_SMD:L_Bourns_SRN6045TA",
           {"1": f"LEDK_{name}", "2": f"SW_{name}"}, MPN="SRN6045TA-101M", Manufacturer="Bourns",
           Description="100 uH shielded inductor, 0.92 A rated, peak current about 0.4 A")
    j = "J3" if name == "BLUE" else "J4"
    s.part(j, "Connector_Generic:Conn_01x02", x + 88.9, 76.2, f"LED {name.lower()} string",
           "Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal",
           {"1": f"SET_{name}", "2": f"LEDK_{name}"}, stub=2.54,
           Description="Pin 1 LED string anode, pin 2 cathode. Both float near the supply voltage.")
    s.C("10uF 50V X7R", "VIN", "GND", x + 7.62, 101.6, fp="Capacitor_SMD:C_1210_3225Metric")
    s.C("100nF 50V X7R", "VIN", "GND", x + 22.86, 101.6)
    s.R(R_CTRL_PULLDOWN, f"CTRL_{name}", "GND", x + 7.62, 63.5)


def build():
    s = gs.Sheet("root", "Root", "led_driver.kicad_sch", None, "A3", "G.O.S. LED driver board")
    s.text("Two AL8860 constant-current buck channels from a 24 V adapter. 333 mA per channel (0.1 V / 0.30 ohm).\n"
           "Each channel drives one off-board string of 4 LEDs on a star heatsink: blue 450 nm on J3, red 660 nm on J4.\n"
           "J2 takes the sensor node's PWM (3.3 V logic, 250 Hz). CTRL above 2.5 V = full current, below 0.2 V = off;\n"
           "the 1.5k pull-downs keep the LEDs off when J2 is unplugged or the node is in reset.\n"
           "J1: centre-positive 24 V barrel jack. F1 + D1 protect against overload and a reversed adapter.", 25.4, 20.32)
    s.part("J1", "Connector:Barrel_Jack", 30.48, 152.4, "24V DC jack", "Connector_BarrelJack:BarrelJack_CUI_PJ-063AH_Horizontal",
           {"1": "VIN_JACK", "2": "GND"}, stub=2.54, MPN="PJ-063AH", Manufacturer="CUI Devices",
           Description="DC jack, 5.5 mm, 2.0 mm centre pin (takes 5.5 x 2.1 mm plugs), centre positive, 24 V 8 A")
    s.part("F1", "Device:Polyfuse_Small", 50.8, 152.4, "PTC 1.1A 30V", "Fuse:Fuse_1206_3216Metric",
           {"1": "VIN_JACK", "2": "VIN_FUSED"})
    s.part(gs.next_ref("D"), "Diode:SS34", 66.04, 152.4, "SS34", "Diode_SMD:D_SMA",
           {"A": "VIN_FUSED", "K": "VIN"}, stub=2.54,
           Description="Schottky 40 V 3 A, reverse-polarity protection")
    s.part("C1", "Device:C_Polarized", 81.28, 152.4, "47uF 50V", "Capacitor_SMD:CP_Elec_6.3x7.7",
           {"1": "VIN", "2": "GND"}, Description="Bulk input capacitor")
    gs.COUNTER["C"] = 1
    channel(s, "BLUE", 25.4)
    channel(s, "RED", 160.02)
    s.part("J2", "Connector_Generic:Conn_01x04", 121.92, 152.4, "PWM from sensor node",
           "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
           {"1": "GND", "2": "CTRL_BLUE", "3": "CTRL_RED", "4": "GND"},
           Description="Mates with sensor node J4: 1 GND, 2 PWM blue, 3 PWM red, 4 GND")
    for i in range(4):
        s.part(f"H{i + 1}", "Mechanical:MountingHole", 160.02 + 15.24 * i, 152.4, "M3",
               "MountingHole:MountingHole_3.2mm_M3", {})
    s.flag("VIN", 254.0, 152.4)
    s.flag("GND", 269.24, 152.4)
    for net, pins in gs.NETS.items():
        if len(pins) < 2:
            raise SystemExit(f"net {net} has a single pin {pins}")
    return s


def main():
    s = build()
    s.write('(sheet_instances (path "/" (page "1")))\n')
    pro = os.path.join(HERE, "led_driver.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"meta": {"filename": "led_driver.kicad_pro", "version": 1}}, f, indent=2)
            f.write("\n")
    print(f"wrote led_driver.kicad_sch: {len(gs.PARTS)} parts, {len(gs.NETS)} nets")
    if "--verify" in sys.argv:
        sys.exit(gs.verify())


if __name__ == "__main__":
    main()
