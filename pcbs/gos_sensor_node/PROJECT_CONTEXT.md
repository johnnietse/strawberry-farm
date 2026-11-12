# G.O.S. Sensor Node — Project Context Document

> **Project**: G.O.S. (Growth Optimization System) Sensor Node  
> **Institution**: Queen's University ePOWER Lab  
> **Target Hardware**: Custom PCB with nRF52840-QIAA (AQFN-73)  
> **Firmware**: Zephyr RTOS v3.x with OpenThread (Thread/CoAP)  
> **Revision**: 2.0 (2026-02-19)  
> **Location**: `C:\Users\Johnnie\Documents\Stawberry_Farm\pcbs\gos_sensor_node\`

---

## 1. Project Overview & Goals

The G.O.S. Sensor Node is a battery-powered, wireless environmental monitoring platform designed for precision agriculture (phytotron/greenhouse deployment). Each node measures temperature, humidity, light (PAR), and battery health, then transmits data via **Thread (802.15.4)** mesh network using **CoAP** to a border router.

### Key Design Targets
| Parameter | Target |
|-----------|--------|
| **MCU** | Nordic nRF52840-QIAA-R7 (Cortex-M4F, 64 MHz, 1 MB Flash, 256 KB RAM) |
| **Radio** | IEEE 802.15.4 (Thread) + BLE 5.0 + Semtech SX1262 (LoRa backup) |
| **GNSS** | Quectel L76K (GPS/GLONASS/BeiDou/Galileo/QZSS) |
| **Power** | 18650 Li-Ion (3.0–4.2 V), USB-C charging (BQ24075), 3.3 V buck (TPS62740) |
| **Battery Life** | >6 months (sleepy end device, 1 Hz sensor poll, 10 min TX interval) |
| **Sensors** | SHT40-AD1B-R2 (±0.1°C, ±1.8% RH), TSL2591FN (600M:1 dynamic range) |
| **Indicators** | Dual-channel LED driver (AL8860): Blue 450 nm, Red 660 nm (PWM dimming) |
| **Protection** | DW01A + dual FS8205A (OVP 4.25 V, ODP 2.40 V, OCP) |
| **Connectors** | USB-C (power), 4-pin I2C expansion (2.54 mm), 5-pin SWD (1.27 mm) |

---

## 2. Hardware Architecture

### 2.1 PCB Schematic Sheets (8 Hierarchical Sheets)

| Sheet | File | Description | Key Components |
|-------|------|-------------|----------------|
| **1** | `power.kicad_sch` | Power Management | BQ24075 (U5), TPS62740 (U4), DW01A (U6), FS8205A (Q1/Q2) |
| **2** | `MCU.kicad_sch` | nRF52840 Core | nRF52840-QIAA (U1), 32 MHz + 32.768 kHz crystals, 13 decoupling caps |
| **3** | `sensors.kicad_sch` | I²C Sensors | SHT40 (U2, 0x44), TSL2591 (U3, 0x29), I²C pull-ups + damping |
| **4** | `radio.kicad_sch` | RF Section | SX1262 (U1, LoRa), L76K (U2, GNSS), RF matching (L4, C31, C32) |
| **5** | `leds.kicad_sch` | LED Drivers | AL8860WT (U7/U8), 47 µH inductors, SS34 Schottky, PWM control |
| **6** | `protection.kicad_sch` | Battery/ESD Protection | DW01A (U6), FS8205A (Q1/Q2), ESD diodes (USB, I2C) |
| **7** | `connectors.kicad_sch` | External Connectors | J2 USB-C, J3 I2C header, J4 SWD header |
| **8** | `gos_sensor_node.kicad_sch` | Root (hierarchical) | Inter-sheet net binding, global labels |

### 2.2 Component Reference Designators by Sheet

| Range | Sheet | Components |
|-------|-------|------------|
| U1 | MCU | nRF52840 |
| U2 | Sensors | SHT40 |
| U3 | Sensors | TSL2591 |
| U4 | Power | TPS62740 |
| U5 | Power | BQ24075 |
| U6 | Power/Protection | DW01A |
| U7 | LEDs | AL8860 (Blue) |
| U8 | LEDs | AL8860 (Red) |
| U1 | Radio | SX1262 |
| U2 | Radio | L76K |
| Q1, Q2 | Protection | FS8205A (dual N-MOS) |
| J2 | Connectors | USB-C receptacle |
| J3 | Connectors | I2C expansion (4-pin) |
| J4 | Connectors | SWD (5-pin, 1.27 mm) |
| J1 | Power | Battery connector (2-pin JST-PH) |

---

## 3. Firmware Architecture (Zephyr RTOS)

### 3.1 Build System
```
firmware/
├── CMakeLists.txt          # Zephyr app definition
├── prj.conf                # Kconfig configuration
├── boards/
│   └── nrf52840_phytotron.overlay  # Devicetree overlay
├── src/
│   └── main.c              # Application entry
├── drivers/
│   └── led_control.c       # PWM LED driver
└── include/
    ├── protocol.h          # Research packet format
    ├── power_mgmt.h        # Power state machine (C++)
    ├── pahlevani_power.h   # DC/DC + WPT simulation
    ├── pahlevani_filters.h # Adaptive notch filter (ANF)
    ├── muise_mesh.h        # Mesh routing with relevance logic
    ├── muise_epistemic.h   # Epistemic knowledge base
    └── sensor_sim.h        # Sensor simulation + LittleFS buffer
```

### 3.2 Key Kconfig Options (`prj.conf`)

```kconfig
# Core
CONFIG_MAIN_STACK_SIZE=4096
CONFIG_SYSTEM_WORKQUEUE_STACK_SIZE=2048
CONFIG_HEAP_MEM_POOL_SIZE=16384

# Networking: OpenThread (Thread 1.2)
CONFIG_NETWORKING=y
CONFIG_NET_L2_OPENTHREAD=y
CONFIG_OPENTHREAD_NORDIC_LIBRARY_MTD=y
CONFIG_OPENTHREAD_MTD=y
CONFIG_OPENTHREAD_FTD=n
CONFIG_OPENTHREAD_MTD_SED=y              # Sleepy End Device
CONFIG_OPENTHREAD_POLL_PERIOD=1000       # 1 second poll

# Thread Network
CONFIG_OPENTHREAD_CHANNEL=15
CONFIG_OPENTHREAD_PANID=0x1234
CONFIG_OPENTHREAD_NETWORK_NAME="GOS_PHYTOTRON"
CONFIG_OPENTHREAD_XPANID="de:ad:00:be:ef:00:ca:fe"
CONFIG_OPENTHREAD_NETWORKKEY="00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff"

# CoAP
CONFIG_OPENTHREAD_COAP=y
CONFIG_COAP=y
CONFIG_COAP_CLIENT=y

# Sensors (I2C)
CONFIG_I2C=y
CONFIG_SENSOR=y
CONFIG_SHT4X=y
CONFIG_SHT4X_TRIGGER_NONE=y
CONFIG_TSL2591=y
```

### 3.3 Devicetree Overlay (`nrf52840_phytotron.overlay`)

**I²C Bus (I2C0)**: P0.26=SDA, P0.27=SCL, 100 kHz standard mode
- `sht4x@44` — Sensirion SHT40, high repeatability
- `tsl2591@29` — AMS TSL2591, INT on P0.15 (active low)

**PWM (PWM0)**: P0.13=OUT0 (Blue), P0.14=OUT1 (Red)

**ADC (SAADC)**: Channel 0 = AIN0/P0.02, gain 1/6, internal ref, 12-bit
- Used for VBATT_SENSE (via 1M/1M divider on P0.28)

**IEEE 802.15.4 Radio**: Enabled for OpenThread

**UART0**: 115200 baud, P0.06=TX, P0.08=RX (debug/logging)

---

## 4. Pin Assignment Matrix (nRF52840 AQFN-73)

| Pin | Ball | Function | Net Label | Connected To |
|-----|------|----------|-----------|--------------|
| **Power** | | | | |
| B1, A13, B15, C11, D12 | — | VDD | VDD_3V3 | TPS62740 VOUT |
| D23, E25 | — | VSS | GND | Ground plane |
| D1, B4, A3, D2, B2, D3 | — | DEC1–DEC6, DECUSB | VDD_3V3 | Decoupling caps (C1–C13) |
| B16, A15 | — | XC1, XC2 | Y1 (32.768 kHz) | ABS07 crystal |
| T2, U1 | — | XL1, XL2 | Y2 (32 MHz) | NX3225GD crystal |
| **I²C** | | | | |
| W2 | P0.26 | I2C0_SDA | I2C0_SDA | SHT40, TSL2591, J3 |
| W3 | P0.27 | I2C0_SCL | I2C0_SCL | SHT40, TSL2591, J3 |
| **SWD** | | | | |
| AC24 | SWDIO | SWDIO | SWDIO | J4, pull-up R11 |
| AC20 | SWDCLK | SWCLK | SWCLK | J4, pull-up R12 |
| **UART** | | | | |
| T2 | P0.06 | UART_TX | UART_TX | L76K RXD |
| U1 | P0.08 | UART_RX | UART_RX | L76K TXD |
| **SX1262 (SPI)** | | | | |
| Y5 | P0.09 | SPI_NSS | SX1262_NSS | SX1262 pin 22 |
| W6 | P0.10 | SPI_SCK | SX1262_SCK | SX1262 pin 23 |
| Y7 | P0.11 | SPI_MISO | SX1262_MISO | SX1262 pin 24 |
| W7 | P0.12 | SPI_MOSI | SX1262_MOSI | SX1262 pin 25 |
| Y8 | P0.15 | GPIO_IN | SX1262_BUSY | SX1262 pin 24 |
| W8 | P0.16 | GPIO_IN | SX1262_DIO1 | SX1262 pin 25 |
| Y9 | P0.17 | GPIO_IN | SX1262_DIO2 | SX1262 pin 26 |
| W9 | P0.19 | GPIO_OUT | SX1262_DIO3 | SX1262 pin 27 |
| Y10 | P0.20 | GPIO_OUT | SX1262_NRESET | SX1262 pin 23 |
| **L76K GNSS (UART)** | | | | |
| W10 | P0.21 | UART_TX | L76K_TXD | L76K pin 3 |
| Y11 | P0.22 | UART_RX | L76K_RXD | L76K pin 4 |
| W11 | P0.23 | GPIO_IN | L76K_PPS | L76K pin 5 |
| **RF / Antenna** | | | | |
| H23 | ANT | RF_SWITCH | ANT | RF matching → J3 test point |
| **PWM (LED Drivers)** | | | | |
| Y12 | P0.13 | PWM_OUT0 | PWM_BLUE | AL8860 U7 EN |
| W12 | P0.14 | PWM_OUT1 | PWM_RED | AL8860 U8 EN |
| **ADC / Power Monitor** | | | | |
| B9 | P0.02/AIN0 | ADC_IN | VBATT_SENSE | Divider (R1/R2 1M/1M) from VBATT |
| B11 | P0.28/AIN4 | ADC_IN | VBUS_SENSE | Divider from VBUS |
| A10 | P0.29/AIN5 | ADC_IN | VSYS_SENSE | Divider from VSYS |
| **Control / Status** | | | | |
| AC13 | P0.18 | nRESET | RESET | SW1, J4 |
| G1 | P0.26 | GPIO | I2C0_SDA | (shared) |
| H2 | P0.27 | GPIO | I2C0_SCL | (shared) |
| B11 | P0.28 | GPIO | VBATT_SENSE | (shared with ADC) |
| A10 | P0.29 | GPIO | BAT_EN | DW01A control / protection enable |

> **Note**: P0.26/P0.27 serve dual role as I²C and GPIO. P0.28/P0.29 serve as ADC and GPIO.

---

## 5. Power Domain Mapping

| Domain | Net Name | Source | Voltage | Consumers | Protection |
|--------|----------|--------|---------|-----------|------------|
| **VBUS** | `VBUS` | USB-C (J2) | 5 V (4.5–5.5 V) | BQ24075 IN, CC1/CC2 | ESD diodes, C31 100 nF |
| **VSYS** | `VSYS` | BQ24075 OUT | 3.0–4.4 V (battery) | TPS62740 VIN, LED drivers (U7/U8 VIN), Q4 load switch | DW01A + FS8205A |
| **VDD_3V3** | `VDD_3V3` | TPS62740 VOUT | 3.3 V ±3% | nRF52840 VDD, all sensors, radio, I²C pull-ups | TPS62740 PG (nPG) |
| **VBATT** | `VBATT` | Battery (J1) | 3.0–4.2 V | DW01A VCC, protection FETs, ADC divider | DW01A OVP/ODP/OCP |
| **AVDD_3V3** | `AVDD_3V3` | VDD_3V3 (ferrite) | 3.3 V filtered | SX1262 VDD, nRF52840 VDDH | FB1 (600 Ω @ 100 MHz) |
| **LED_VIN** | `LED_VIN` | VSYS (via Q4) | VSYS (3.0–4.4 V) | AL8860 U7/U8 VIN | Q4 PMOS load switch, D4 Schottky |

### Power Sequencing
1. **VBUS present** → BQ24075 charges battery, powers VSYS via power-path
2. **VSYS > UVLO** → TPS62740 enabled (EN=VSYS) → VDD_3V3 ramps
3. **VDD_3V3 PG** → nRF52840 releases reset, firmware boots
4. **BAT_EN (P0.29) high** → DW01A enables protection FETs (Q1/Q2)
5. **LED_VIN** controlled by Q4 (PMOS) gated by MCU for LED power savings

### Key Power Component Parameters
| Component | Key Config | Value |
|-----------|------------|-------|
| BQ24075 (U5) | ISET (R8) | 1.2 kΩ → 742 mA charge current |
| | ILIM (R9) | 10 kΩ → 500 mA input current limit |
| | TS (R10) | 10 kΩ NTC to VDD_3V3 (battery temp) |
| TPS62740 (U4) | VSEL0, VSEL1 | Both GND → 3.3 V fixed output |
| | L1 | 2.2 µH, Isat > 500 mA |
| | CIN (C18) | 4.7 µF X5R 10 V |
| | COUT (C19) | 10 µF X5R 10 V |
| DW01A (U6) | OVP | 4.25 V ±50 mV |
| | ODP | 2.40 V ±80 mV |
| | OCP | ~3 A (via R1 sense) |
| AL8860 (U7/U8) | R5/R6 (sense) | 0.33 Ω → ~1 A LED current |
| | R7/FB1 | 600 Ω / 1 MΩ → current setting |

---

## 6. Communication Interfaces

### 6.1 I²C (I2C0 / TWIM0)
- **Pins**: P0.26=SDA, P0.27=SCL
- **Speed**: 100 kHz (standard mode)
- **Pull-ups**: R3/R4 = 4.7 kΩ to VDD_3V3
- **Series Damping**: R12/R13 = 100 Ω (SDA/SCL lines to sensors)
- **Devices**:
  - `0x44` — SHT40-AD1B-R2 (temp/humidity)
  - `0x29` — TSL2591FN (light), INT on P0.15

### 6.2 SPI (SPIM3) — SX1262 LoRa
| Signal | Pin | SX1262 Pin |
|--------|-----|------------|
| SCK | P0.10 | 23 |
| MOSI | P0.12 | 25 |
| MISO | P0.11 | 24 |
| NSS | P0.09 | 22 |
| BUSY | P0.15 | 24 |
| DIO1 | P0.16 | 25 |
| DIO2 | P0.17 | 26 |
| DIO3 | P0.19 | 27 |
| NRESET | P0.20 | 23 |

### 6.3 UART0 — Debug Console
- **TX**: P0.06 → USB/debug header
- **RX**: P0.08 → USB/debug header
- **Baud**: 115200 8N1

### 6.4 UART1 — L76K GNSS
- **TX**: P0.21 → L76K RXD
- **RX**: P0.22 → L76K TXD
- **PPS**: P0.23 → L76K PPS (1 Hz time pulse)
- **Baud**: 9600 8N1 (default)

### 6.5 PWM (PWM0) — LED Drivers
- **OUT0 (P0.13)** → AL8860 U7 EN (Blue channel)
- **OUT1 (P0.14)** → AL8860 U8 EN (Red channel)
- **Frequency**: 1 kHz (configurable), duty cycle = spectral mix

### 6.6 ADC (SAADC) — Power Monitoring
| Channel | Pin | Signal | Divider | Formula |
|---------|-----|--------|---------|---------|
| AIN0 | P0.02 | VBATT_SENSE | 1M/1M (÷2) | VBATT = ADC × 2 × (3.6/4095) |
| AIN4 | P0.28 | VBUS_SENSE | 1M/1M (÷2) | VBUS = ADC × 2 × (3.6/4095) |
| AIN5 | P0.29 | VSYS_SENSE | 1M/1M (÷2) | VSYS = ADC × 2 × (3.6/4095) |

---

## 7. Power Management ICs & Control Interfaces

### 7.1 BQ24075RGTR (U5) — USB Li-Ion Charger + Power Path
| Pin | Net | Control |
|-----|-----|---------|
| IN (1) | VBUS | Input from USB-C |
| ILIM (2) | ILIM | R9=10k to GND (500 mA) |
| ISET (3) | ISET | R8=1.2k to GND (742 mA) |
| CE (4) | GND | Active LOW = charging enabled |
| TS (5) | TS | R10=10k NTC to VDD_3V3 |
| OUT (7) | VSYS | System output (power path) |
| PGOOD (8) | NC | Open collector, not monitored |
| SYSOFF (10) | GND | LOW = system enabled |

### 7.2 TPS62740DSSR (U4) — 3.3 V Buck Converter
| Pin | Net | Control |
|-----|-----|---------|
| VIN (1) | VSYS | From BQ24075 OUT |
| EN (2) | VSYS | HIGH = enabled (always on when VSYS present) |
| VSEL0 (3) | GND | 3.3 V select |
| VSEL1 (4) | GND | 3.3 V select |
| VOUT (7) | VDD_3V3 | 3.3 V output |
| PG (8) | nPG | Open collector, not connected to MCU |

### 7.3 DW01A-G (U6) — Battery Protection IC
| Pin | Net | Function |
|-----|-----|----------|
| OD (1) | PACK_N | Drives FS8205A gates (over-discharge) |
| CS (2) | R1 (1k to VBATT) | Current sense |
| OC (3) | Q1/Q2 gates | Over-current protection output |
| TD (4) | R2 (1k to GND) | Delay capacitor |
| VCC (5) | VBATT | Power from battery |
| GND (6) | GND | Ground |

### 7.4 FS8205A (Q1, Q2) — Dual N-MOSFET Protection
- **Q1 (High-side)**: Source=VBATT, Drain=PACK_N, Gate=U6 OC/OD
- **Q2 (Low-side)**: Source=PACK_N, Drain=GND, Gate=U6 OC/OD
- **Protection**: OVP 4.25 V, ODP 2.40 V, OCP ~3 A

### 7.5 AL8860WT (U7, U8) — Constant-Current Buck LED Drivers
| Pin | U7 (Blue) | U8 (Red) |
|-----|-----------|----------|
| VIN (1/5) | VSYS | VSYS |
| GND (2/3) | GND | GND |
| EN/PWM (3/4) | PWM_BLUE | PWM_RED |
| SW (2/1) | L1 → D1/D2 anode | L2 → D3/D4 anode |
| FB/SET (4/6) | R5=0.33Ω sense | R6=0.33Ω sense |

---

## 8. Protection Circuits & Fault Handling

### 8.1 Battery Protection (DW01A + FS8205A)
| Fault | Threshold | Action | Recovery |
|-------|-----------|--------|----------|
| Over-Voltage (OVP) | 4.25 V ±50 mV | Q1/Q2 OFF (disconnect battery) | VBATT < 4.1 V |
| Over-Discharge (ODP) | 2.40 V ±80 mV | Q1/Q2 OFF (disconnect load) | VBUS present (charging) |
| Over-Current (OCP) | ~3 A (R1 sense) | Q1/Q2 OFF | Load removal + delay (R2/C1) |
| Short Circuit | Very high dI/dt | Q1/Q2 OFF (µs) | Power cycle |

### 8.2 USB Input Protection
- **D3 (PMEG2010AEH)**: Schottky, reverse polarity protection on VBUS
- **C31 (100 nF)**: VBUS decoupling at USB-C connector
- **CC1/CC2**: 5.1 kΩ pull-downs (integrated in USB-C receptacle) for UFP role

### 8.3 LED Driver Protection
- **D4 (PMEG2010AEH)**: Reverse polarity on LED_VIN
- **Q4 (PMOS)**: Load switch, gate controlled by MCU (BAT_EN) to disable LEDs in deep sleep
- **Schottky D1/D2 (SS34)**: Freewheeling for buck LED drivers

### 8.4 ESD Protection
- **USB-C**: D+/D- lines have internal ESD in receptacle
- **I²C Expansion (J3)**: Series 100 Ω damping (R12/R13) + TVS (optional, not populated)
- **SWD (J4)**: Direct to MCU (internal ESD)

---

## 9. Communication Protocols

### 9.1 Thread (OpenThread) — Primary Mesh Network
- **Role**: MTD (Minimal Thread Device) → SED (Sleepy End Device)
- **Poll Period**: 1000 ms (configurable via `CONFIG_OPENTHREAD_POLL_PERIOD`)
- **Channel**: 15 (2.4 GHz, IEEE 802.15.4)
- **PAN ID**: 0x1234
- **Network Name**: `GOS_PHYTOTRON`
- **XPAN ID**: `de:ad:00:be:ef:00:ca:fe`
- **Network Key**: `00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff`
- **Security**: AES-CCM-128 (Thread 1.2)

### 9.2 CoAP — Application Layer
- **Protocol**: Constrained Application Protocol (RFC 7252)
- **Transport**: UDP over 6LoWPAN over Thread
- **Method**: POST (sensor data upload)
- **Path**: `/sensor/data`
- **Payload**: Binary `gos_research_packet_t` (28 bytes)
- **Confirmable**: Yes (ACK required)

### 9.3 LoRa (SX1262) — Backup/Long-Range
- **Frequency**: 915 MHz (NA) / 868 MHz (EU) — configurable
- **Modulation**: LoRa (CSS), SF7–SF12, BW 125/250/500 kHz
- **Use Case**: Gateway out of Thread range, or firmware update
- **Control**: SPI + GPIOs (NSS, BUSY, DIO1–3, NRESET)

### 9.4 GNSS (L76K) — Location/Time
- **Constellations**: GPS + GLONASS + BeiDou + Galileo + QZSS
- **Interface**: UART1 @ 9600 baud
- **Output**: NMEA 0183 + PPS (1 Hz, P0.23)
- **Time Sync**: PPS used for RTC calibration / TDMA slot alignment

### 9.5 Research Packet Format (`protocol.h`)

```c
struct __attribute__((packed)) gos_research_packet_t {
    uint8_t  protocol_ver;      // 0x02
    uint8_t  node_index;        // 1–40
    uint64_t hardware_eui64;    // nRF52840 FICR->DEVICEID
    float    temp_c;            // Filtered temperature (°C)
    float    hum_pct;           // Relative humidity (%)
    uint16_t par_lux;           // Spectral irradiance (lux)
    uint16_t batt_mv;           // Battery voltage (mV)
};  // Total: 28 bytes
```

---

## 10. Build System & Dependencies

### 10.1 Zephyr RTOS
- **Version**: 3.x (tested with 3.4+)
- **Toolchain**: Zephyr SDK (arm-zephyr-eabi-gcc)
- **West**: Meta-build tool for workspace management

### 10.2 Key Dependencies
| Component | Source | Version |
|-----------|--------|---------|
| Zephyr Kernel | `zephyrproject-rtos/zephyr` | 3.4+ |
| Nordic HAL | `zephyrproject-rtos/nrfx` | Included |
| OpenThread | `openthread/openthread` | Nordic lib |
| MCUboot | `juulabs/mcuboot` | For DFU |
| LittleFS | `ARMmbed/littlefs` | Flash logging |

### 10.3 Build Commands
```bash
# Setup (once)
west init -m https://github.com/zephyrproject-rtos/zephyr --mr v3.4.0 ~/zephyrproject
cd ~/zephyrproject
west update
west zephyr-export

# Build
cd C:\Users\Johnnie\Documents\Stawberry_Farm\firmware
west build -b nrf52840dk/nrf52840 -- -DBOARD_ROOT=.

# Flash
west flash --runner nrfjprog

# Debug
west debug
```

### 10.4 Board Definition
Custom board overlay: `boards/nrf52840_phytotron.overlay`
- Extends `nrf52840dk_nrf52840`
- Adds I²C sensors, PWM LEDs, ADC channels, SX1262 SPI, L76K UART

---

## 11. Known Issues & TODOs

### 11.1 Hardware (PCB Rev 2.0)
| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| LED_VIN net name mismatch (VSYS vs LED_VIN) | Medium | **Fixed in schematic** | WIRING_GUIDE shows LED_VIN = VSYS |
| TPS62740 PG (nPG) not connected to MCU | Low | Open | Could enable power-good monitoring |
| BQ24075 PGOOD not monitored | Low | Open | Could detect USB present/absent |
| SX1262 TCXO pin (28) tied to GND | Medium | **By design** | Using internal 32 MHz XO |
| L76K PPS not connected to RTC | Low | Open | P0.23 available, needs firmware |
| No external flash for LittleFS | Medium | **Known limitation** | Using internal flash (limited) |
| I²C pull-ups on sensor sheet only | Low | **By design** | Root sheet has no pull-ups |

### 11.2 Firmware
| Task | Priority | Status |
|------|----------|--------|
| Implement real SHT40/TSL2591 drivers (replace sim) | High | TODO |
| Implement OpenThread CoAP client with confirmable POST | High | TODO |
| Add battery voltage ADC reading + calibration | High | TODO |
| Implement PWM LED spectral mixing (gos_set_spectral_mix) | Medium | Stub only |
| Add Deep Sleep (SYSTEM_OFF) with GPIO wake (button/accel) | Medium | TODO |
| Implement SX1262 LoRa driver + fallback logic | Low | TODO |
| Add LittleFS on internal flash for store-and-forward | Medium | TODO |
| Implement Muise mesh relevance routing (simulation → real) | Low | Research |
| Add Pahlevani ANF filter for sensor noise reduction | Low | Research |
| DFU over Thread (MCUboot + CoAP) | Medium | TODO |

### 11.3 Documentation
- [ ] Create `hardware_protocol.md` with packet format spec
- [ ] Document PCB assembly guide (BOM, footprints, DNP)
- [ ] Add Zephyr devicetree binding for custom board
- [ ] Create production test firmware (LED, sensor, radio, ADC)

---

## 12. File Index

### Schematic (KiCad 9.0)
```
gos_sensor_node/
├── gos_sensor_node.kicad_sch      # Root schematic
├── gos_sensor_node.kicad_pro      # Project file
├── gos_sensor_node.kicad_pcb      # PCB layout
├── power.kicad_sch                # Sheet 1: Power
├── MCU.kicad_sch                  # Sheet 2: MCU
├── sensors.kicad_sch              # Sheet 3: Sensors
├── radio.kicad_sch                # Sheet 4: Radio
├── leds.kicad_sch                 # Sheet 5: LEDs
├── protection.kicad_sch           # Sheet 6: Protection
├── connectors.kicad_sch           # Sheet 7: Connectors
├── WIRING_GUIDE.md                # Pin-to-label wiring guide
├── generate_schematics.py         # Generator script (one-time)
├── libraries/Custom.kicad_sym     # Custom symbols
├── sym-lib-table                  # Symbol library table
└── fp-lib-table                   # Footprint library table
```

### Firmware (Zephyr)
```
firmware/
├── CMakeLists.txt
├── prj.conf
├── boards/nrf52840_phytotron.overlay
├── src/main.c
├── drivers/led_control.c
└── include/
    ├── protocol.h
    ├── power_mgmt.h
    ├── pahlevani_power.h
    ├── pahlevani_filters.h
    ├── muise_mesh.h
    ├── muise_epistemic.h
    └── sensor_sim.h
```

---

## 13. Revision History

| Rev | Date | Author | Changes |
|-----|------|--------|---------|
| 1.0 | 2026-02-15 | ePOWER Lab | Initial schematic capture |
| 1.1 | 2026-02-17 | ePOWER Lab | Power sheet: BQ24075 + TPS62740 + DW01A |
| 1.2 | 2026-02-19 | ePOWER Lab | MCU, Sensors, Radio, LEDs, Protection, Connectors sheets |
| 2.0 | 2026-02-19 | ePOWER Lab | Full hierarchical schematic, WIRING_GUIDE, Zephyr firmware scaffold |
| 2.1 | 2026-07-18 | ContextOrg | **This document** — comprehensive context extraction |

---

> **Generated by**: ContextOrganizer agent  
> **Source**: KiCad 9.0 schematics + Zephyr firmware + WIRING_GUIDE.md  
> **Purpose**: Single-source-of-truth for hardware/firmware co-development