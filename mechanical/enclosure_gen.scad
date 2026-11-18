// ==============================================================
// G.O.S. PHYTOTRON SENSOR NODE ENCLOSURE (rev 3.1 board)
// ==============================================================
// Material: ASA (UV resistant) for the phytotron, PETG for prototypes.
// Holds: G.O.S. sensor node rev 3.1 (40 x 65 mm, 4-layer) + one 18650 cell.
//
// Board positions come from pcb_layout.scad, which mechanical/fit_check.py
// generates from the KiCad board. Rerun fit_check.py after any board change;
// it also checks the fit and renders the board inside the enclosure.
//
// Coordinates (mm): origin at the centre of the outer footprint, on the
// underside of the floor. X across, Y along (USB-C in the front wall at -Y), Z up.
//
// Render parts:   openscad -D 'part="base"' -o base.stl enclosure_gen.scad
//                 openscad -D 'part="lid"' -o lid.stl enclosure_gen.scad
// ==============================================================

include <pcb_layout.scad>

$fn = 72;

part = "assembly";       // "assembly", "base" or "lid"
show_pcb = false;        // assembly view: import pcb_assembly.stl (from fit_check.py)
show_lid = true;         // assembly view: lid in place
lid_lift = 0;            // assembly view: raise the lid (exploded view)
pcb_lift = 0;            // assembly view: raise the board (exploded view)
cell_lift = 0;           // assembly view: raise the 18650 cell (exploded view)
only = "all";            // assembly view: "all", "base", "lid", "pcb" or "cell" (drawings)
lid_alpha = 0.5;        // assembly view: lid transparency (1 = opaque, for drawings)
wall_view = "none";     // drawings: "front" keeps only the -Y wall (y < slab_y), "right" only the +X wall (x > slab_x)
slab_y = 0;
slab_x = 0;
cut = false;             // assembly view: cut away the -X half to see inside

// === OUTER DIMENSIONS ===
enclosure_width = 85;
enclosure_length = 130;
enclosure_height = 45;   // base, floor underside to rim
wall = 2.5;
corner_radius = 5;

// === BOARD MOUNTING ===
post_d = 5;
post_pilot_d = 2.2;      // M2.5 self-tapping screw (board holes are 2.7 mm)

// === BATTERY ===
battery_d = 19;          // 18650 with sleeve
battery_len = 68;
cradle_wall = 2;
cradle_len = 60;         // shorter than the cell: the ends stay free for the lead

// === LID ===
lid_t = 3;
lid_lip = 4;             // lip that drops inside the rim
lid_fit = 0.3;           // clearance per side
boss_d = 7;
boss_pilot_d = 2.5;      // M3 self-tapping
lid_screw_d = 3.4;
window_d = 10;           // light window over the TSL2591
window_disc_d = 16;      // clear PC/acrylic disc, glued into a recess from inside
window_disc_t = 1.5;     // glued into a recess on the outside of the lid
tube_wall = 1.5;         // light tube wall; print the lid in black so the tube does not glow
tube_bottom = pcb_z + pcb_thickness + 3;   // 3 mm above the board, clear of the TSL2591 (0.65 mm tall)

inner_x = enclosure_width / 2 - wall;
inner_y = enclosure_length / 2 - wall;
boss_xy = [[-(inner_x - boss_d / 2), -(inner_y - boss_d / 2)], [inner_x - boss_d / 2, -(inner_y - boss_d / 2)],
           [-(inner_x - boss_d / 2), 30], [inner_x - boss_d / 2, 30]];

module rounded_box(w, l, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (w / 2 - r), sy * (l / 2 - r), 0]) cylinder(r = r, h = h);
}

// --- base -------------------------------------------------------
module shell() {
    difference() {
        rounded_box(enclosure_width, enclosure_length, enclosure_height, corner_radius);
        translate([0, 0, wall])
            rounded_box(enclosure_width - 2 * wall, enclosure_length - 2 * wall, enclosure_height, corner_radius - wall);
    }
}

module pcb_posts() {
    for (h = pcb_holes) translate([h[0], h[1], wall - 0.01])
        difference() {
            cylinder(d = post_d, h = pcb_z - wall + 0.01);
            translate([0, 0, 1]) cylinder(d = post_pilot_d, h = pcb_z);
        }
}

module battery_cradle() {
    axis_z = wall + cradle_wall + battery_d / 2;
    difference() {
        union() {
            translate([0, battery_center_y, axis_z]) rotate([0, 90, 0])
                cylinder(d = battery_d + 2 * cradle_wall, h = cradle_len, center = true);
            translate([-cradle_len / 2, battery_center_y - battery_d / 2 - cradle_wall, wall - 0.01])
                cube([cradle_len, battery_d + 2 * cradle_wall, axis_z - wall]);
        }
        translate([0, battery_center_y, axis_z]) rotate([0, 90, 0])
            cylinder(d = battery_d + 0.5, h = cradle_len + 2, center = true);
        // snap opening: narrower than the cell, so it clips in
        translate([-cradle_len / 2 - 1, battery_center_y - battery_d * 0.42, axis_z + battery_d * 0.25])
            cube([cradle_len + 2, battery_d * 0.84, battery_d]);
    }
}

module lid_bosses() {
    for (b = boss_xy) translate([b[0], b[1], wall - 0.01])
        difference() {
            cylinder(d = boss_d, h = enclosure_height - wall + 0.01 - lid_lip - 0.5);
            cylinder(d = boss_pilot_d, h = enclosure_height);
        }
}

module usb_cutout() {   // fits a USB-C plug overmold up to 12 x 7 mm
    translate([usb_center[0], -enclosure_length / 2 - 1, usb_center[1]]) rotate([-90, 0, 0])
        hull() for (sx = [-1, 1], sz = [-1, 1])
            translate([sx * (12 / 2 - 1.5), sz * (7 / 2 - 1.5), 0]) cylinder(d = 3, h = wall + 2);
}

module sensor_vents() { // vertical slots in both side walls beside the SHT40, at board height
    for (sx = [-1, 1]) for (i = [-3 : 3])
        translate([sx * (enclosure_width / 2 - wall / 2), sht40[1] + i * 3.5, pcb_z + 1])
            rotate([0, 90, 0]) hull() {
                cylinder(d = 2, h = wall + 2, center = true);
                translate([-10, 0, 0]) cylinder(d = 2, h = wall + 2, center = true);
            }
}

module led_cable_gland() { // M12 gland for the cable to the LED driver board, beside J4
    translate([enclosure_width / 2 - wall - 1, j4_led_cable[1], 25]) rotate([0, 90, 0]) cylinder(d = 12.2, h = wall + 2);
}

module floor_holes() {
    for (sx = [-1, 1]) translate([sx * 30, 15, -1]) cylinder(d = 4, h = wall + 2);       // pole/rail mounting
    for (sx = [-1, 1], y = [-55, 30]) translate([sx * 33, y, -1]) cylinder(d = 2, h = wall + 2);  // drainage
}

module base() {
    difference() {
        union() { shell(); pcb_posts(); battery_cradle(); lid_bosses(); }
        usb_cutout();
        sensor_vents();
        led_cable_gland();
        floor_holes();
    }
}

// --- lid --------------------------------------------------------
module lid() {
    difference() {
        union() {
            rounded_box(enclosure_width, enclosure_length, lid_t, corner_radius);
            translate([0, 0, -lid_lip]) difference() {
                rounded_box(enclosure_width - 2 * (wall + lid_fit), enclosure_length - 2 * (wall + lid_fit),
                            lid_lip + 0.01, corner_radius - wall);
                translate([0, 0, -1]) rounded_box(enclosure_width - 2 * (wall + lid_fit) - 4,
                                                  enclosure_length - 2 * (wall + lid_fit) - 4, lid_lip + 2,
                                                  corner_radius - wall - 2);
            }
            // light tube from the window down to just above the TSL2591: the sensor sees a
            // defined cone of outside light, not light reflected around inside the box
            translate([tsl2591[0], tsl2591[1], tube_bottom - enclosure_height])
                cylinder(d = window_d + 2 * tube_wall, h = enclosure_height - tube_bottom + 0.01);
        }
        for (b = boss_xy) translate([b[0], b[1], -lid_lip - 1]) cylinder(d = lid_screw_d, h = lid_t + lid_lip + 2);
        // light window over the TSL2591, through the tube, with a recess on top for the clear disc
        translate([tsl2591[0], tsl2591[1], tube_bottom - enclosure_height - 1])
            cylinder(d = window_d, h = enclosure_height - tube_bottom + lid_t + 2);
        translate([tsl2591[0], tsl2591[1], lid_t - window_disc_t]) cylinder(d = window_disc_d, h = window_disc_t + 0.01);
    }
}

// --- views ------------------------------------------------------
if (part == "base") base();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) lid();
else if (wall_view == "front") intersection() { assembly(); translate([-1000, -1000, -1000]) cube([2000, 1000 + slab_y, 3000]); }
else if (wall_view == "right") intersection() { assembly(); translate([slab_x, -1000, -1000]) cube([1000, 2000, 3000]); }
else difference() {
    union() { assembly(); }
    if (cut) translate([-enclosure_width, -enclosure_length, -10]) cube([enclosure_width, 2 * enclosure_length, 100]);
}

module assembly() {
    if (only == "all" || only == "base") color("SlateGray") base();
    if (show_lid && (only == "all" || only == "lid"))
        color("LightSteelBlue", lid_alpha) translate([0, 0, enclosure_height + lid_lift]) lid();
    if (show_pcb && (only == "all" || only == "pcb"))
        color("DarkGreen") translate([pcb_origin[0], pcb_origin[1], pcb_z + pcb_thickness + pcb_lift])
            import("pcb_assembly.stl");  // STL: board top at z = 0
    if (only == "all" || only == "cell")
        color("SteelBlue", lid_alpha < 1 ? 0.6 : 1) translate([0, battery_center_y, wall + cradle_wall + battery_d / 2 + cell_lift])
            rotate([0, 90, 0]) cylinder(d = 18.5, h = 65, center = true);
}

echo("=== G.O.S. sensor node enclosure ===");
echo("Material: ASA (UV stable); PETG for prototypes. Layer 0.2 mm, 4 walls, 25 % infill.");
echo("Hardware: 4 x M2.5x6 self-tapping (board), 4 x M3x10 self-tapping (lid), 1 x M12 cable gland,");
echo("          16 mm x 1.5 mm clear polycarbonate disc for the light window.");
