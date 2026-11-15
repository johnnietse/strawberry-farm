// ==============================================================
// G.O.S. LED DRIVER BOARD ENCLOSURE (rev 1.0 board, 60 x 45 mm)
// ==============================================================
// Mounts beside the grow light, out of the plants' drip zone. Holds the LED driver board;
// the 24 V jack and the two LED plugs face out through the side walls, the PWM cable
// from the sensor node leaves through a slot beside J2.
//
// Board positions come from led_layout.scad, written by fit_check.py from the KiCad board.
// Coordinates (mm): origin at the centre of the outer footprint, on the underside of the floor.
//
// Render parts:   openscad -D 'part="base"' -o led_base.stl led_enclosure.scad
//                 openscad -D 'part="lid"' -o led_lid.stl led_enclosure.scad
// ==============================================================

include <led_layout.scad>

$fn = 64;
part = "assembly";      // "assembly", "base" or "lid"
show_pcb = false;       // assembly view: import led_assembly.stl (from fit_check.py)
show_lid = true;        // assembly view: lid in place
lid_lift = 0;           // assembly view: raise the lid (exploded view)
cut = false;            // assembly view: cut away the -Y half

wall = 2.5;
corner_radius = 3;
side_gap = 6.0;         // board edge to wall on the long sides: room for the lid bosses beside the board
inner_w = pcb_size[0] + 2 * conn_gap;    // connectors on both short sides sit at the walls
inner_l = pcb_size[1] + 2 * side_gap;
enclosure_width = inner_w + 2 * wall;
enclosure_length = inner_l + 2 * wall;
enclosure_height = pcb_z + pcb_thickness + headroom;   // base, floor underside to rim

post_d = 6.5;
post_pilot_d = 2.5;     // M3 self-tapping (board holes 3.2 mm)
boss_d = 6;
boss_pilot_d = 2.5;
lid_t = 2.5;
lid_lip = 3;
lid_fit = 0.3;
lid_screw_d = 3.4;
flange_w = 10;          // mounting flanges on the long sides, 2 x 4.5 mm slots each

module rounded_box(w, l, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (w / 2 - r), sy * (l / 2 - r), 0]) cylinder(r = r, h = h);
}

boss_xy = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (inner_w / 2 - boss_d / 2), sy * (inner_l / 2 - boss_d / 2)]];

module shell() {
    difference() {
        union() {
            rounded_box(enclosure_width, enclosure_length, enclosure_height, corner_radius);
            // mounting flanges along the long sides, at floor level
            translate([0, 0, 0]) rounded_box(enclosure_width, enclosure_length + 2 * flange_w, 3, corner_radius);
        }
        translate([0, 0, wall]) rounded_box(inner_w, inner_l, enclosure_height, max(0.5, corner_radius - wall));
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * enclosure_width / 4, sy * (enclosure_length / 2 + flange_w / 2), -1])
                hull() { translate([-2, 0, 0]) cylinder(d = 4.5, h = 5); translate([2, 0, 0]) cylinder(d = 4.5, h = 5); }
    }
}

module posts() {
    for (h = pcb_holes) translate([h[0], h[1], wall - 0.01]) difference() {
        cylinder(d = post_d, h = pcb_z - wall + 0.01);
        translate([0, 0, 1]) cylinder(d = post_pilot_d, h = pcb_z);
    }
}

module bosses() {
    for (b = boss_xy) translate([b[0], b[1], wall - 0.01]) difference() {
        cylinder(d = boss_d, h = enclosure_height - wall - lid_lip - 0.5);
        cylinder(d = boss_pilot_d, h = enclosure_height);
    }
}

module cutouts() {
    top = pcb_z + pcb_thickness;
    // 24 V jack: round opening for the plug, left wall
    translate([-enclosure_width / 2 - 1, jack[1], top + jack_center_h]) rotate([0, 90, 0]) cylinder(d = 10, h = wall + 2);
    // LED string plugs: one rectangular opening per terminal, right wall
    for (t = terminals) translate([enclosure_width / 2 - wall - 1, t[1] - 6, top + 0.5]) cube([wall + 2, 12, 11]);
    // PWM cable from the sensor node: slot in the wall beside J2
    translate([header[0] - 7, -enclosure_length / 2 - 1, top + 10]) cube([14, wall + 2, 5]);
    // heat vents: slots along the long walls, high up (AL8860s about 0.25 W each)
    for (sy = [-1, 1]) for (i = [-3 : 3])
        translate([i * 6 - 1, sy * (enclosure_length / 2 - wall / 2) - (wall + 2) / 2, enclosure_height - lid_lip - 7])
            cube([2, wall + 2, 5]);
}

module base() {
    difference() {
        union() { shell(); posts(); bosses(); }
        cutouts();
    }
}

module lid() {
    difference() {
        union() {
            rounded_box(enclosure_width, enclosure_length, lid_t, corner_radius);
            translate([0, 0, -lid_lip]) difference() {
                rounded_box(inner_w - 2 * lid_fit, inner_l - 2 * lid_fit, lid_lip + 0.01, max(0.5, corner_radius - wall));
                translate([0, 0, -1]) rounded_box(inner_w - 2 * lid_fit - 3, inner_l - 2 * lid_fit - 3, lid_lip + 2, 0.5);
            }
        }
        for (b = boss_xy) translate([b[0], b[1], -lid_lip - 1]) cylinder(d = lid_screw_d, h = lid_t + lid_lip + 2);
    }
}

module assembly() {
    color("SlateGray") base();
    if (show_lid) color("LightSteelBlue", 0.5) translate([0, 0, enclosure_height + lid_lift]) lid();
    if (show_pcb) color("DarkGreen") translate([pcb_origin[0], pcb_origin[1], pcb_z + pcb_thickness]) import("led_assembly.stl");
}

if (part == "base") base();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) lid();
else difference() {
    assembly();
    if (cut) translate([-enclosure_width, -enclosure_length - flange_w, -10]) cube([2 * enclosure_width, enclosure_length + flange_w, 100]);
}

echo(str("LED enclosure outer ", enclosure_width, " x ", enclosure_length, " x ", enclosure_height + lid_t, " mm"));
