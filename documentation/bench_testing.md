# G.O.S. Hardware Bench Testing & Commissioning Manual

This document is the "Hands-on" guide for researchers. It ensures every node in the 40-unit fleet is physically ready for the Queen's Phytotron.

## 🛠 1. Physical Assembly (PCB & Soldering)
*Requirement: Hands-on soldering (through-hole, SMD asset)*
1.  **SMD Reflow**: Validate the **nRF52840-QIAA** alignment. Check for solder bridges between GND and VCC.
2.  **SHT4x Mounting**: Solder the sensor cable. Observe the color-code:
    - **Red**: 3.3V (VCC)
    - **Black**: GND
    - **Green**: P0.26 (I2C SDA)
    - **Yellow**: P0.27 (I2C SCL)

## 🧪 2. Bench Validation (The "Cold Test")
*Requirement: Read simple schematics and use a multimeter/oscilloscope*
1.  **Continuity Check**: Measure 0Ω between the **nRF52 Ground** and the **18650 Battery Negative**.
2.  **Multimeter Power Rail**:
    - With battery connected, measure **3.3V** at the output of the LDO regulator.
    - Measure **1.8V** at the internal DEC4 pin of the nRF (ensures the internal DCDC is healthy).
3.  **Oscilloscope Signal Integrity**:
    - Probe **P0.06 (UART TX)**. During boot, you should see a packet of 115200bps data pulses. 
    - Probe **P0.27 (I2C SCL)**. You should see a stable 100kHz clock during sensor polling.

## 🔗 3. Raspberry Pi Integration (The "Commissioning")
*Requirement: Assist with implementing and debugging communication (Rasp Pi)*
1.  **Attach RCP**: Connect the flasher-adapter to the Raspberry Pi's USB port.
2.  **Terminal Check**: Run `sudo ot-ctl state`. 
    - If it says `disabled`, run `sudo ot-ctl thread start`.
3.  **Joiner Command**: On the G.O.S. Dashboard, click "Add Node". The Pi will start looking for your nRF52 node's **EUI64 ID**.
4.  **Verification**: Once the node serial log shows `[MESH] Attached`, confirm the node appears on the [Command Center](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/dashboard/index.html).

## 📦 4. 3D Printing & Sealing
1.  Print the [Enclosure](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/mechanical/enclosure_gen.scad) using **ASA filament** (UV resistant).
2.  Apply an O-ring or silicone bead to the lid before deployment.

---
*Follow the [Pinout Map](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/documentation/nrf52840_pinout.md) for final wiring.*
