# Design review: G.O.S. sensor node rev 3.1, LED driver rev 1.0, enclosures

A review of the whole hardware path as an electrical, firmware and mechanical engineer would do it
before ordering. Each finding says what was checked, how, and what was done. Date: 2026-11-15.

**Evidence used:** KiCad DRC at every severity with schematic parity (both boards clean),
`pcbs/gos_sensor_node/review_layout.py` (layout measurements), LTspice simulations
(`simulation/README.md`), the firmware build (Zephyr main, no warnings: 214 KB flash, 62 KB RAM)
and host-side packet test, 44 gateway tests, and `mechanical/fit_check.py`. Nothing has been built
yet, so every result below is a design check, not a measurement.

## System: how the pieces work together

```
 18650 cell ──J5─┐                                   24 V adapter ──J1─┐
 USB-C (charge)──┤ SENSOR NODE  (40 x 65 mm, 4 layers)                  │ LED DRIVER (60 x 45 mm, 4 layers)
                 │  BQ24074 charger + DW01A/FS8205A protection          │  2 x AL8860 constant-current buck
                 │  TPS62740 3.3 V buck                                 │  blue string on J3, red on J4
                 │  Raytac MDBT50Q (nRF52840, Zephyr, OpenThread)       │
                 │  SHT40 temperature/humidity, TSL2591 light           │
                 │  J4: 2 x 250 Hz PWM ───── 4-wire cable ─────────► J2: CTRL inputs
                 └── Thread radio (802.15.4, 2.4 GHz)
                           │  signed CoAP PACKET_V4 every 60 s, to ff03::1
                           ▼
   Raspberry Pi + nRF52840 Dongle (OpenThread border router, RCP)
     └── coap_receiver (Docker): verify HMAC + counter ──► TimescaleDB ──► API / dashboard / ML
```

Two custom boards: the **sensor node** (one per measurement point, battery powered, in its own
enclosure near the plants) and the **LED driver** (one per grow light, in its own enclosure at the
light). They connect only through the 4-wire PWM cable. The border router is off-the-shelf
hardware. The earlier rev 2 design put LoRa, GNSS and the LED drivers on one board; rev 3.1
dropped LoRa and GNSS (Thread covers the phytotron) and moved the LED drivers to their own board,
which keeps 24 V switching currents away from the sensors and the radio.

## Electrical: sensor node

| Area | Check | Result |
|---|---|---|
| Power path | BQ24074 input limit 0.54 A (R_ILIM 3.0 k), charge current about 0.49 A (R_ISET 1.8 k), 0.22 C for a 2200 mAh cell | OK |
| 3.3 V buck | TPS62740 loop: input cap was 4.5 mm from VIN, switch node went through 2 vias | **Fixed**: L1, C4, C5 placed and the loop routed by hand: switch node 2.6 mm on one layer, no vias; input cap 2.1 mm from VIN; GND pins tied straight to the exposed pad and its thermal vias |
| Cell protection | DW01A + FS8205A: over-current trip 150 mV / (2 x 25 mOhm max) = at least 3 A | OK |
| Reversed cell | Q2 AO3401A in the positive lead | **Simulated**: reversed cell gives 0 V on the board, 8 pA drawn; correct cell: 29 mV drop, 15 mW at 500 mA |
| Battery measurement | 2.2 M / 2.2 M divider with 100 nF into the SAADC | **Simulated**: +/-1.1 % worst case from 1 % resistors, 0.38 s settling, 0.96 uA drain (0.7 mAh a month) |
| USB | USBLC6 ESD, 0.75 A PTC, 5.1 k CC pull-downs, 27 ohm series resistors | OK. Pair routed 0.1 mm matched; at 12 Mbit/s (83 ns bits) length matching has no effect, but it costs nothing |
| Radio | Antenna on the board edge, full-width copper keep-out on all four layers, solid ground under the module, 18650 can 35.6 mm away, plastic enclosure | OK: no copper, via or pour in the keep-out (measured) |
| Crystal | 9 pF crystal, 12 pF caps: 12/2 + about 3 pF stray = 9 pF | OK |
| Noise | 4 layers, two solid ground planes 0.076 mm under the outer layers, ground stitching every 1.6 mm (one twentieth of the 2.4 GHz wavelength in FR-4 is about 3 mm) | OK |
| Thermal coupling | The charger dissipates up to about 0.65 W while charging; that warms the whole 40 x 65 mm board, including the SHT40 | **Mitigated in firmware and gateway**: PACKET_V4 adds a charging flag; filter `payload->>'charging'` when analysing temperature. A milled slot around the SHT40 would reduce it further (see open items) |
| Charger thermistor | TH1 sits on the board, not on the cell, so charge temperature limits follow board temperature | Accepted for a first build: the board stays close to the cell's temperature in a 15 to 35 C phytotron. A cell with a built-in 10 k NTC wired to TS would sense the cell itself |
| Humidity | Phytotron humidity can condense on the board | **Recommendation**: conformal coating (acrylic, for example MG Chemicals 419D) after assembly, masking the SHT40, TSL2591, connectors and buttons. JLCPCB does not coat; spray it yourself or use a coating service |

## Electrical: LED driver

| Area | Check | Result |
|---|---|---|
| Switching frequency | AL8860 limit 1 MHz, on-time at least 500 ns for 4 % accuracy | **Fixed after simulation**: 47 uH ran at up to 1.27 MHz; 100 uH runs at 435 to 672 kHz over 20 to 28 V, both colours, typical and maximum LED voltage |
| LED current | 0.1 V / 0.30 ohm = 333 mA | **Simulated**: 335 to 339 mA; PWM dimming linear (33.7 / 168 / 303 mA at 10 / 50 / 90 %) |
| Fail-safe | Floating CTRL turns the LEDs fully on | **Fixed after simulation**: pull-down 2.2 k to 1.5 k; worst case 0.12 V with the cable unplugged (off below 0.2 V) |
| Switching loops | Input caps were 5 mm from VIN, switch nodes 12 to 14 mm | **Fixed**: input caps 2.9 mm from VIN, diode anode and inductor at the SW pins, routed by hand on one layer |
| Protection | 1.1 A PTC, SS34 against a reversed adapter; AL8860 open-LED, short and over-temperature protection | OK |
| Losses | about 0.25 W per channel; LTspice efficiency 94 to 97 % | OK |
| Connector | PJ-063AH has a 2.0 mm pin (CUI datasheet); takes 5.5 x 2.1 mm plugs | Documented; recommended adapter Mean Well GST36U24-P1J has that plug |

## Firmware and gateway

| Area | Check | Result |
|---|---|---|
| Build | Zephyr main f8da8ea, SDK 1.0.1 | Builds with no warnings |
| Packet | PACKET_V4 (43 bytes) adds charger flags; HMAC-SHA256 tag over the body, per-node key, counter never repeats | Encoder compiled on a PC; its bytes are decoded in the gateway tests; receiver still accepts PACKET_V3 |
| Gateway | Signature, EUI-64 pinning, replay counter across restarts, interface binding to the Thread interface | 44 tests pass |
| Border router doc | `raspberry_pi_setup.md` described an unused MQTT-SN bridge and network settings that did not match the firmware | **Fixed**: now matches `prj.conf` (channel 15, PAN 0x1234, GOS_PHYTOTRON) |

## Mechanical

| Area | Check | Result |
|---|---|---|
| Sensor enclosure | Old model: no floor, battery over the board, USB-C 30 mm from its cut-out, no light path | **Rebuilt** around the board; fit generated from the KiCad file and checked by `fit_check.py` (8 checks pass) |
| Light sensor | Opaque box | Window plus a printed light tube down to 3 mm above the TSL2591, so it sees outside light in a defined cone; lid printed black. Calibrate lux once with the lid on |
| Humidity sensor | Air must reach the SHT40 | Vent slots in both side walls at board height beside it |
| LED driver enclosure | Did not exist | **New**: jack and LED plugs through the walls, cable slot by J2, vents, mounting flanges; 4 checks pass |
| Material | Warm, humid, lit phytotron | ASA (UV-stable, 95 C); PETG acceptable; not PLA (creeps near 55 C) |
| Sealing | Vents and the USB cut-out are open | Not waterproof by design (the sensor needs air). Use the USB-C dust plug and the cable gland; keep the node out of direct spray |

## Open items (need hardware or a decision)

1. Bench measurements in `documentation/bring_up.md`: sleep current, charge behaviour, Thread
   range, the on-chip HMAC, the LED current and the CTRL fail-safe with the real AL8860.
2. Temperature offset of the SHT40 while charging; if it matters, add a milled slot around the
   SHT40 (a later board revision) or only use readings with `charging = false`.
3. Lux calibration factor with the lid on.
4. Thread range across the phytotron: if nodes cannot reach the border router, add a mains-powered
   router node (any nRF52840 board with a full-Thread-device build).
5. Supply: re-check the pre-order and low-stock parts on the day of ordering (`ordering.md`).
