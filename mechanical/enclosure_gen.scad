// ==============================================================
// G.O.S. PHYTOTRON SENSOR NODE ENCLOSURE - PRODUCTION VERSION
// ==============================================================
// Material: ASA (UV Resistant) or PETG for prototypes
// Hardware: Custom G.O.S. PCB (nRF52840 aQFN-73) + SHT4x + TSL2591 + 18650 Battery
// Author: G.O.S. Team | Queen's University EPOWER Lab
// ==============================================================

$fn = 120; // High resolution for production

// === PARAMETRIC DIMENSIONS (mm) ===
enclosure_width = 85;
enclosure_length = 130;
enclosure_height = 45;
wall_thickness = 2.5;
corner_radius = 5;

// Component mounting dimensions
pcb_width = 40;      // Custom G.O.S. PCB width (per PCB spec §12.1)
pcb_length = 65;     // Custom G.O.S. PCB length
battery_diameter = 19; // 18650 battery
battery_length = 68;

// === MAIN ENCLOSURE BODY ===
module enclosure_base() {
    difference() {
        // Outer shell with rounded corners
        minkowski() {
            cube([enclosure_width - corner_radius*2, 
                  enclosure_length - corner_radius*2, 
                  enclosure_height/2], center=true);
            cylinder(r=corner_radius, h=1);
        }
        
        // Inner cavity
        translate([0, 0, wall_thickness])
        minkowski() {
            cube([enclosure_width - wall_thickness*2 - corner_radius*2,
                  enclosure_length - wall_thickness*2 - corner_radius*2,
                  enclosure_height], center=true);
            cylinder(r=corner_radius-1, h=0.5);
        }
    }
}

// === SENSOR VENTILATION GRILLE ===
// Allows airflow for accurate temperature/humidity readings
module ventilation_grille() {
    vent_spacing = 4;
    vent_width = 2;
    vent_count = 8;
    
    for(i = [0 : vent_count-1]) {
        translate([enclosure_width/2 - wall_thickness/2, 
                   -vent_count*vent_spacing/2 + i*vent_spacing, 
                   enclosure_height/4])
        rotate([0, 90, 0])
        hull() {
            cylinder(d=vent_width, h=wall_thickness*2);
            translate([0, 0, 0])
            cylinder(d=vent_width, h=wall_thickness*2);
        }
    }
    
    // Mirror to other side
    mirror([1, 0, 0])
    for(i = [0 : vent_count-1]) {
        translate([enclosure_width/2 - wall_thickness/2, 
                   -vent_count*vent_spacing/2 + i*vent_spacing, 
                   enclosure_height/4])
        rotate([0, 90, 0])
        hull() {
            cylinder(d=vent_width, h=wall_thickness*2);
        }
    }
}

// === USB PORT CUTOUT ===
// For programming and power connection
module usb_cutout() {
    usb_width = 12;
    usb_height = 7;
    
    translate([0, -enclosure_length/2, enclosure_height/4])
    rotate([90, 0, 0])
    hull() {
        translate([-usb_width/2 + 1.5, 0, 0]) cylinder(d=3, h=wall_thickness*2);
        translate([usb_width/2 - 1.5, 0, 0]) cylinder(d=3, h=wall_thickness*2);
        translate([-usb_width/2 + 1.5, usb_height-3, 0]) cylinder(d=3, h=wall_thickness*2);
        translate([usb_width/2 - 1.5, usb_height-3, 0]) cylinder(d=3, h=wall_thickness*2);
    }
}

// === SENSOR PROBE PORT ===
// External connector for SHT4x extender cable
module sensor_port() {
    translate([enclosure_width/2 - wall_thickness, 0, 0])
    rotate([0, 90, 0])
    cylinder(d=8, h=wall_thickness*2);
}

// === LED INDICATOR WINDOW ===
// Transparent section for status LEDs
module led_window() {
    window_size = 15;
    translate([0, enclosure_length/2 - wall_thickness, enclosure_height/3])
    rotate([90, 0, 0])
    hull() {
        translate([-window_size/2, 0, 0]) cylinder(d=4, h=wall_thickness*2);
        translate([window_size/2, 0, 0]) cylinder(d=4, h=wall_thickness*2);
    }
}

// === PCB MOUNTING POSTS ===
module pcb_mounts() {
    post_height = 5;
    post_diameter = 5;
    hole_diameter = 2.5;
    
    mount_positions = [
        [-pcb_width/2 + 5, -pcb_length/2 + 5],
        [pcb_width/2 - 5, -pcb_length/2 + 5],
        [-pcb_width/2 + 5, pcb_length/2 - 5],
        [pcb_width/2 - 5, pcb_length/2 - 5]
    ];
    
    for(pos = mount_positions) {
        translate([pos[0], pos[1], -enclosure_height/2 + wall_thickness])
        difference() {
            cylinder(d=post_diameter, h=post_height);
            cylinder(d=hole_diameter, h=post_height + 1);
        }
    }
}

// === BATTERY HOLDER ===
module battery_cradle() {
    translate([0, enclosure_length/4, -enclosure_height/2 + wall_thickness + battery_diameter/2])
    rotate([0, 90, 0])
    difference() {
        // Outer cradle
        cylinder(d=battery_diameter + 4, h=battery_length, center=true);
        // Battery cavity
        cylinder(d=battery_diameter + 0.5, h=battery_length + 2, center=true);
        // Top opening
        translate([0, battery_diameter/2 + 2, 0])
        cube([battery_diameter + 5, battery_diameter, battery_length + 2], center=true);
    }
}

// === LID WITH SNAP CLIPS ===
module snap_clip() {
    clip_width = 8;
    clip_depth = 3;
    clip_height = 4;
    
    translate([0, 0, 0])
    hull() {
        cube([clip_width, clip_depth, 1]);
        translate([0, clip_depth, clip_height])
        cube([clip_width, 0.5, 0.5]);
    }
}

module lid() {
    lid_height = 8;
    
    difference() {
        // Lid body
        translate([0, 0, enclosure_height/2 + 2])
        minkowski() {
            cube([enclosure_width - corner_radius*2 - 2,
                  enclosure_length - corner_radius*2 - 2,
                  lid_height/2], center=true);
            cylinder(r=corner_radius - 0.5, h=0.5);
        }
        
        // Inner lip
        translate([0, 0, enclosure_height/2])
        cube([enclosure_width - wall_thickness*4,
              enclosure_length - wall_thickness*4,
              lid_height], center=true);
    }
    
    // Snap clips
    clip_positions = [
        [enclosure_width/2 - wall_thickness*2, 0, enclosure_height/2],
        [-enclosure_width/2 + wall_thickness*2, 0, enclosure_height/2],
        [0, enclosure_length/2 - wall_thickness*2, enclosure_height/2],
        [0, -enclosure_length/2 + wall_thickness*2, enclosure_height/2]
    ];
}

// === CABLE GLAND PORT ===
// IP65-rated cable entry
module cable_gland_port() {
    gland_diameter = 12; // M12 cable gland
    translate([-enclosure_width/4, -enclosure_length/2, 0])
    rotate([90, 0, 0])
    cylinder(d=gland_diameter, h=wall_thickness*2);
}

// === MOUNTING BRACKET HOLES ===
// For pole/rail mounting in greenhouse
module mounting_holes() {
    hole_diameter = 4;
    hole_spacing = 60;
    
    translate([0, 0, -enclosure_height/2])
    for(x = [-hole_spacing/2, hole_spacing/2]) {
        translate([x, enclosure_length/3, 0])
        cylinder(d=hole_diameter, h=wall_thickness*2, center=true);
    }
}

// === DRAINAGE HOLES ===
// Prevents condensation buildup
module drainage_holes() {
    drain_diameter = 2;
    
    positions = [
        [-enclosure_width/3, -enclosure_length/3],
        [enclosure_width/3, -enclosure_length/3],
        [-enclosure_width/3, enclosure_length/3],
        [enclosure_width/3, enclosure_length/3]
    ];
    
    for(pos = positions) {
        translate([pos[0], pos[1], -enclosure_height/2])
        cylinder(d=drain_diameter, h=wall_thickness*2);
    }
}

// === FINAL ASSEMBLY ===
module complete_enclosure() {
    difference() {
        union() {
            enclosure_base();
            pcb_mounts();
            battery_cradle();
        }
        
        // Cutouts
        ventilation_grille();
        usb_cutout();
        sensor_port();
        led_window();
        cable_gland_port();
        mounting_holes();
        drainage_holes();
    }
}

// === RENDER ===
// Comment/uncomment to render different parts

// Full enclosure
complete_enclosure();

// Lid (print separately)
// translate([enclosure_width + 20, 0, 0]) lid();

// === PRINT SETTINGS ===
echo("=== G.O.S. Phytotron Node Enclosure ===");
echo("Recommended Material: ASA (UV stable, heat resistant)");
echo("Layer Height: 0.2mm");
echo("Infill: 20% for base, 100% for lid");
echo("Supports: Yes, for ventilation grilles");
echo("Print Time: ~4 hours per unit");
echo("IP Rating: IP54 with gasket, IP65 with cable glands");
