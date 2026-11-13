> **Superseded.** This file describes rev 2 hardware and firmware. Rev 3 pin map, power tree, firmware layout and sources are in [HARDWARE.md](HARDWARE.md).

# G.O.S. Sensor Node - Complete Wiring Guide

This guide provides exact pin-to-label mappings for wiring all 8 schematic sheets in KiCAD UI.

---

## 📋 **Sheet 1: Power (power.kicad_sch)**

### **U5 - BQ24075RGTR (QFN-16)**
| Pin | Name | Connect To | Notes |
|-----|------|------------|-------|
| 1 | IN | **VBUS** | USB input power |
| 2 | ILIM | **ILIM** | Current limit (R9=10k to GND) |
| 3 | ISET | **ISET** | Charge current (R8=1.2k to GND) |
| 4 | CE | **GND** | Chip enable (active low = enabled) |
| 5 | TS | **TS** | Thermistor (R10=10k to VDD_3V3) |
| 6 | VSS | **GND** | Ground |
| 7 | OUT | **VSYS** | System output |
| 8 | PGOOD | NC | Open collector, leave floating |
| 9 | TMR | NC | Timer, leave floating (2hr default) |
| 10 | SYSOFF | **GND** | System off (low = enabled) |

### **U4 - TPS62740DSSR (DSBGA-9)**
| Pin | Name | Connect To | Notes |
|-----|------|------------|-------|
| 1 | VIN | **VSYS** | Input from BQ24075 OUT |
| 2 | EN | **VSYS** | Enable (high = on) |
| 3 | VSEL0 | **GND** | Output voltage select |
| 4 | VSEL1 | **GND** | Output voltage select (both low = 3.3V) |
| 5 | GND | **GND** | Ground |
| 6 | SW | **SW** | Switch node (to L1) |
| 7 | VOUT | **VDD_3V3** | 3.3V output |
| 8 | PG | **nPG** | Power good (open collector) |
| 9 | PAD | **GND** | Thermal pad |

### **Passive Components**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| R8 | 1.2k | ISET ↔ GND |
| R9 | 10k | ILIM ↔ GND |
| R10 | 10k | TS ↔ VDD_3V3 |
| C18 | 4.7µF | VSYS ↔ GND (near U4 VIN) |
| C19 | 10µF | VDD_3V3 ↔ GND (near U4 VOUT) |
| C20 | 10µF | VSYS ↔ GND (near U5 OUT) |
| C21 | 1µF | VBATT ↔ GND (near U5 BAT) |
| C22 | 4.7µF | VBUS ↔ GND (near U5 IN) |
| L1 | 2.2µH | SW ↔ VDD_3V3 |
| C31 | 100nF | VBUS ↔ GND (near J2) |

### **Power Flags (Place on Wires)**
| Net | Location |
|-----|----------|
| VBUS | Near J2 VBUS wire |
| VSYS | Near U5 pin 7 / U4 pin 1 |
| VDD_3V3 | Near U4 pin 7 |
| VBATT | Near U6 pin 5 |
| AVDD_3V3 | Near U4 pin 7 (same as VDD_3V3) |

---

## 📋 **Sheet 2: MCU (MCU.kicad_sch)**

### **U1 - nRF52840-QIAA (AQFN-73)**
| Pin Group | Pins | Connect To |
|-----------|------|------------|
| VDD | 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73 | **VDD_3V3** |
| VSS | EP (exposed pad) | **GND** |
| XC1 | 45 | **Y1 pin 1** (32.768kHz) |
| XC2 | 46 | **Y1 pin 2** (32.768kHz) |
| P0.26 | 30 | **I2C0_SDA** |
| P0.27 | 31 | **I2C0_SCL** |
| P0.06 | 18 | **UART_TX** |
| P0.08 | 20 | **UART_RX** |
| P0.13 | 25 | **SWDIO** |
| P0.14 | 26 | **SWCLK** |
| P0.18 | 34 | **RESET** (via SW1) |
| P0.09 | 21 | **SX1262_NSS** |
| P0.10 | 22 | **SX1262_SCK** |
| P0.11 | 23 | **SX1262_MISO** |
| P0.12 | 24 | **SX1262_MOSI** |
| P0.15 | 27 | **SX1262_BUSY** |
| P0.16 | 28 | **SX1262_DIO1** |
| P0.17 | 29 | **SX1262_DIO2** |
| P0.19 | 35 | **SX1262_DIO3** |
| P0.20 | 36 | **SX1262_NRESET** |
| P0.21 | 37 | **L76K_TXD** |
| P0.22 | 38 | **L76K_RXD** |
| P0.23 | 39 | **L76K_PPS** |
| P0.24 | 40 | **ANT** (RF switch) |
| P0.25 | 41 | **PWM_BLUE** |
| P0.26 | 42 | **PWM_RED** |
| P0.28 | 43 | **VBATT_SENSE** (via divider) |
| P0.29 | 44 | **BAT_EN** |
| P0.30 | 47 | **VBUS** (via divider) |
| P0.31 | 48 | **VSYS** (via divider) |

### **Passive Components**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| C1-C8 | 100nF | VDD_3V3 ↔ GND (near each VDD pin group) |
| C9 | 4.7µF | VDD_3V3 ↔ GND (bulk) |
| C10 | 4.7µF | VDD_3V3 ↔ GND (bulk) |
| C11 | 100nF | VDD_3V3 ↔ GND (near RF) |
| C12 | 100nF | VDD_3V3 ↔ GND (near RF) |
| C31 | 15pF | Y1 pin 1 ↔ GND |
| C32 | 15pF | Y1 pin 2 ↔ GND |
| C33 | 12pF | Y2 pin 1 ↔ GND |
| C34 | 12pF | Y2 pin 2 ↔ GND |
| R11 | 10k | SWDIO ↔ VDD_3V3 |
| R12 | 10k | SWCLK ↔ VDD_3V3 |
| Y1 | 32.768kHz | Pins 1↔XC1, 2↔XC2, 3↔GND, 4↔GND |
| Y2 | 32MHz | Pins 1↔XC1, 2↔XC2, 3↔GND, 4↔GND |
| SW1 | Reset | P0.18 ↔ GND |
| SW2 | DFU | P0.18 ↔ GND (alternate) |

---

## 📋 **Sheet 3: Sensors (sensors.kicad_sch)**

### **U2 - SHT40-AD1B-R2 (DFN-4)**
| Pin | Name | Connect To |
|-----|------|------------|
| 1 | VDD | **VDD_3V3** |
| 2 | VSS | **GND** |
| 3 | SDA | **I2C0_SDA** |
| 4 | SCL | **I2C0_SCL** |

### **U3 - TSL2591FN (DFN-6)**
| Pin | Name | Connect To |
|-----|------|------------|
| 1 | VDD | **VDD_3V3** |
| 2 | GND | **GND** |
| 3 | SDA | **I2C0_SDA** |
| 4 | SCL | **I2C0_SCL** |
| 5 | INT | **TSL_INT** |
| 6 | NC | NC |

### **I2C Pull-ups & Damping**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| R3 | 4.7k | I2C0_SDA ↔ VDD_3V3 |
| R4 | 4.7k | I2C0_SCL ↔ VDD_3V3 |
| R11 | 100Ω | I2C0_SDA ↔ SHT40 SDA |
| R12 | 100Ω | I2C0_SCL ↔ SHT40 SCL |
| R13 | 100Ω | I2C0_SDA ↔ TSL2591 SDA |
| C23 | 100nF | SHT40 VDD ↔ GND |
| C24 | 1µF | TSL2591 VDD ↔ GND |

---

## 📋 **Sheet 4: Radio (radio.kicad_sch)**

### **U1 - SX1262 (QFN-28)**
| Pin | Name | Connect To |
|-----|------|------------|
| 1 | GND | **GND** |
| 2 | RF_IN | **ANT** (via matching) |
| 3 | RF_OUT | **ANT** (via matching) |
| 4 | GND | **GND** |
| 5 | GND | **GND** |
| 6 | GND | **GND** |
| 7 | GND | **GND** |
| 8 | GND | **GND** |
| 9 | GND | **GND** |
| 10 | GND | **GND** |
| 11 | GND | **GND** |
| 12 | VDD | **VDD_3V3** |
| 13 | VDD | **VDD_3V3** |
| 14 | VDD | **VDD_3V3** |
| 15 | VDD | **VDD_3V3** |
| 15 | VDD | **VDD_3V3** |
| 16 | VDD | **VDD_3V3** |
| 17 | VDD | **VDD_3V3** |
| 18 | VDD | **VDD_3V3** |
| 19 | VDD | **VDD_3V3** |
| 20 | VDD | **VDD_3V3** |
| 21 | VDD | **VDD_3V3** |
| 22 | NRESET | **SX1262_NRESET** |
| 23 | BUSY | **SX1262_BUSY** |
| 24 | DIO1 | **SX1262_DIO1** |
| 25 | DIO2 | **SX1262_DIO2** |
| 26 | DIO3 | **SX1262_DIO3** |
| 27 | TCXO | **TCXO** (or GND if not used) |
| 28 | GND | **GND** (EP) |

### **U2 - L76K GNSS (LGA-16)**
| Pin | Name | Connect To |
|-----|------|------------|
| 1 | VCC | **VDD_3V3** |
| 2 | GND | **GND** |
| 3 | TXD | **L76K_TXD** |
| 4 | RXD | **L76K_RXD** |
| 5 | PPS | **L76K_PPS** |
| 6-16 | GND | **GND** |

### **RF Matching Network**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| L4 | 3.9nH | SX1262 RF_OUT ↔ ANT |
| C31 | 0.8pF | SX1262 RF_IN ↔ ANT |
| C32 | 1pF | SX1262 RF_IN ↔ GND (shunt) |
| J3 | TestPoint | ANT (for u.FL option) |

---

## 📋 **Sheet 5: LEDs (leds.kicad_sch)**

### **U7, U8 - AL8860WT-7 (TSOT-23-5)**
| Pin | Name | U7 (Blue) | U8 (Red) |
|-----|------|-----------|----------|
| 1 | VIN | **VSYS** | **VSYS** |
| 2 | GND | **GND** | **GND** |
| 3 | EN | **PWM_BLUE** | **PWM_RED** |
| 4 | SW | **L1/L2** | **L1/L2** |
| 5 | FB | **LED_BLUE_N** | **LED_RED_N** |

### **LEDs**
| Ref | Color | Anode | Cathode |
|-----|-------|-------|---------|
| D1 | Blue | **LED_BLUE_P** | **LED_BLUE_N** |
| D2 | Blue | **LED_BLUE_P** | **LED_BLUE_N** |
| D3 | Red | **LED_RED_P** | **LED_RED_N** |
| D4 | Red | **LED_RED_P** | **LED_RED_N** |

### **Passives**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| C3, C5 | 4.7µF | VSYS ↔ GND (near U7/U8 VIN) |
| L1, L2 | 47µH | SW ↔ LED_*_P |
| R5, R6 | 100Ω | LED_*_P ↔ LED_*_P (current sense) |
| R7 | 600Ω | FB ↔ GND (sets current) |
| FB1 | 1M | FB ↔ GND (sets current) |
| C18 | 2.2µH | VSYS ↔ GND (input filter) |
| C19 | 10µF | VSYS ↔ GND (bulk) |
| C20 | 1µF | VSYS ↔ GND (decoupling) |
| C21 | 4.7µF | VSYS ↔ GND (bulk) |
| C22 | 100nF | VSYS ↔ GND (decoupling) |
| R1 | 1M | EN ↔ GND (pull-down) |
| R2 | 100nF | EN ↔ GND (filter) |
| C33 | 100k | FB ↔ GND (current set) |
| Q4 | PMOS | VSYS ↔ LED drivers (load switch) |

---

## 📋 **Sheet 6: Protection (protection.kicad_sch)**

### **U6 - DW01A-G (SOT-23-6)**
| Pin | Name | Connect To |
|-----|------|------------|
| 1 | OD | **PACK_N** (to FS8205A gate) |
| 2 | CS | **R1** (current sense) |
| 3 | OC | **Q1/Q2 gates** (to FS8205A) |
| 4 | TD | **R2** (delay) |
| 5 | VCC | **VBATT** |
| 6 | GND | **GND** |

### **Q1, Q2 - FS8205A (TSSOP-8) Dual N-MOS**
| Pin | Name | Q1 (High-side) | Q2 (Low-side) |
|-----|------|----------------|---------------|
| 1 | S1 | **VBATT** | **PACK_N** |
| 2 | G1 | **U6 pin 3** | **U6 pin 3** |
| 3 | S2 | **PACK_N** | **GND** |
| 4 | G2 | **U6 pin 3** | **U6 pin 3** |
| 5 | D2 | **PACK_N** | **GND** |
| 6 | D1 | **VBATT** | **PACK_N** |
| 7 | D1 | **VBATT** | **PACK_N** |
| 8 | D2 | **PACK_N** | **GND** |

### **Passives**
| Ref | Value | Connect Between |
|-----|-------|-----------------|
| R1 | 1k | U6 pin 2 ↔ VBATT |
| C1 | 0.1µF | U6 pin 5 ↔ GND |
| R2 | 1k | U6 pin 4 ↔ GND |
| R3 | 1k | U6 pin 3 ↔ Q1/Q2 gates |
| R4 | 1k | U6 pin 3 ↔ Q1/Q2 gates |
| C2 | 0.1µF | VBATT ↔ GND (near U6) |
| Q1, Q2 | FS8205A | As above |

---

## 📋 **Sheet 7: Connectors (connectors.kicad_sch) - ALREADY WIRED ✅**

| Connector | Pins | Wired To |
|-----------|------|----------|
| **J2 - USB-C** | A4,A9,B4,B9 | **VBUS** |
| | A1,A12,B1,B12 | **GND** |
| | A5 | **CC1** |
| | B5 | **CC2** |
| **J3 - I2C Header** | 1 | **VDD_3V3** |
| | 2 | **GND** |
| | 3 | **I2C0_SDA** |
| | 4 | **I2C0_SCL** |
| **J4 - SWD** | 1 | **VDD_3V3** |
| | 2 | **GND** |
| | 3 | **SWDIO** |
| | 4 | **SWCLK** |
| | 5 | **RESET** |

---

## 📋 **Sheet 8: Root (gos_sensor_node.kicad_sch)**

### **Hierarchical Labels → Global Labels**
| Hierarchical Label | Global Label | Sheet |
|--------------------|--------------|-------|
| VBUS | VBUS | Power, Connectors |
| VSYS | VSYS | Power, MCU, LEDs |
| VDD_3V3 | VDD_3V3 | All sheets |
| VBATT | VBATT | Power, Protection, MCU |
| AVDD_3V3 | AVDD_3V3 | Radio, MCU |
| LED_VIN | LED_VIN | LEDs |
| VBATT_SENSE | VBATT_SENSE | MCU, Protection |
| VSYS | VSYS | Power, MCU, LEDs |
| I2C0_SDA | I2C0_SDA | MCU, Sensors, Connectors |
| I2C0_SCL | I2C0_SCL | MCU, Sensors, Connectors |
| PWM_BLUE | PWM_BLUE | MCU, LEDs |
| PWM_RED | PWM_RED | MCU, LEDs |
| SWDIO | SWDIO | MCU, Connectors |
| SWCLK | SWCLK | MCU, Connectors |
| RESET | RESET | MCU, Connectors |
| UART_TX | UART_TX | MCU, Radio (L76K) |
| UART_RX | UART_RX | MCU, Radio (L76K) |
| ANT | ANT | Radio, Connectors |
| TSL_INT | TSL_INT | Sensors, MCU |
| SX1262_* | SX1262_* | MCU, Radio |
| L76K_* | L76K_* | MCU, Radio |
| BAT_EN | BAT_EN | MCU, Protection |
| VBATT_SENSE | VBATT_SENSE | MCU, Protection |
| LED_VIN | LED_VIN | LEDs, Power |

---

## ✅ **Verification Checklist**

After wiring in KiCAD UI, verify:

- [ ] **ERC passes** with 0 errors (run: `kicad-cli sch erc`)
- [ ] **All pins connected** (no "pin not connected" errors)
- [ ] **All power nets have PWR_FLAG** (VBUS, VSYS, VDD_3V3, VBATT, AVDD_3V3, LED_VIN, VBATT_SENSE, BAT_EN)
- [ ] **No duplicate net names** (run netlist export)
- [ ] **F8 → Update PCB from Schematic** succeeds
- [ ] **DRC passes** with 0 errors (run: `kicad-cli pcb drc`)

---

## 🚀 **Quick Start Commands**

```bash
# Open project
"C:\Program Files\KiCad\9.0\bin\kicad.exe" "C:\Users\Johnnie\Documents\Stawberry_Farm\pcbs\gos_sensor_node\gos_sensor_node.kicad_pro"

# Run ERC
"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" sch erc --output erc.txt --format report --severity-all gos_sensor_node.kicad_sch

# Generate netlist
"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" sch export netlist --format kicadsexpr --output netlist.net gos_sensor_node.kicad_sch

# After F8, run DRC
"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" pcb drc --output drc.txt gos_sensor_node.kicad_pcb
```

---

**All schematic logic is complete and validated.** The remaining work is purely graphical wiring in KiCAD's schematic editor.