# Sensor node bring-up (rev 3.1)

Step-by-step first power-on, once the assembled boards arrive (ordered as in `ordering.md`).
Each step says what "pass" looks like; stop at the first failure. Pin map: `nrf52840_pinout.md`.
Design reference: `pcbs/gos_sensor_node/HARDWARE.md`.

You need: an SWD probe with a 10-pin 1.27 mm Cortex cable (J-Link, or an nRF52 DK's debug
port), a USB-C cable, a 3.3 V USB-serial adapter for TP5/TP6, an 18650 cell with a JST-PH lead,
a multimeter, and the Raspberry Pi border router from `raspberry_pi_setup.md`. The parts bought
separately are listed in `ordering.md`.

## 0. On arrival, before any power

1. Look at every board under good light or a magnifier. Compare with
   `pcbs/gos_sensor_node/docs/gos_sensor_node_assembly_top.pdf` (and the LED board's). **Pass:**
   every part present, pin-1 marks on U1-U7, Q1 and Q2 match the drawing, LED and diode stripes on
   the cathode side, no solder bridges on U1, U2 or the module.
2. Meter, power off: resistance from VBUS (TP7), VSYS (TP2), +3V3 (TP1) and VBAT (TP3) to GND
   (TP4). **Pass:** none below about 100 ohm. A dead short means a bridge: stop.

## 1. Power, no cell

1. Plug in USB-C only. **Pass:** TP7 (VBUS) about 5 V, TP2 (VSYS) about 4.4 V, TP1 (+3V3) 3.3 V.
2. Current from USB with no firmware should be a few mA. Much more means a short: unplug and inspect.

## 2. Cell and charger

1. Check the lead: J5 pin 1 = positive. Connect the cell, keep USB plugged in.
2. **Pass:** TP3 (VBAT) reads the cell voltage, the yellow LED D1 lights while charging and goes out when full.
3. Unplug USB. **Pass:** +3V3 stays at 3.3 V on battery.

## 3. Provision and flash

On the gateway machine, from the repo root:

```
python gateway/tools/provision_node.py --index 1 --network-key <your Thread network key>
```

It registers the node's signing key in `gateway/secrets/node_keys.json` and prints a
`credentials.conf`. Save that text as `pcbs/gos_sensor_node/firmware/credentials.conf` (never
commit it), then build and flash through J2:

```
west build -b raytac_mdbt50q_db_40/nrf52840 pcbs/gos_sensor_node/firmware
west flash
```

Use the bench build first (debug console on). For nodes going into the phytotron add
`-- -DEXTRA_CONF_FILE=low_power.conf`.

## 4. Debug console

Connect the USB-serial adapter: its RX to TP5, its TX to TP6, GND to TP4. 115200 8N1.

**Pass:** at boot it prints `G.O.S. sensor node rev 3.1`, `uplink signing ready`, and
`node 1, EUI-64 XXXXXXXXXXXXXXXX`, then every 60 s a temperature, humidity, light, battery and
charger line. Pin the chip to its index:

```
python gateway/tools/provision_node.py --index 1 --eui64 XXXXXXXXXXXXXXXX
```

## 5. Sensors

- Breathe on the SHT40: humidity rises within a reading or two.
- Cover the TSL2591: light drops near 0 lux.
- Battery reading within about 2 % of a meter on TP3.

## 6. Thread and the database

1. Border router running (`raspberry_pi_setup.md`), same channel, PAN ID and network key as `credentials.conf`.
2. On the border router: `docker compose --profile hardware up coap_receiver` (needs `gateway/secrets/node_keys.json`).
3. **Pass:** the console stops printing "not attached to Thread yet"; the receiver logs
   `RF-NODE-01 EUI64:...`; and this returns rows:

```
SELECT time, node_id, temp_c, humidity_pct, battery_mv, payload->>'light_lux',
       payload->>'counter', payload->>'charging', payload->>'packet_version'
FROM raw_telemetry WHERE node_id = 'RF-NODE-01' ORDER BY time DESC LIMIT 5;
```

   `packet_version` is 4, and `charging` follows the yellow LED D1. With USB plugged in and the
   cell charging, note how far `temp_c` reads above a reference thermometer: that is the charger's
   heating (see `design_review.md`). Use `charging = false` rows for climate analysis.

4. **Security check:** reflash the node with a different `CONFIG_GOS_UPLINK_KEY`. The receiver must log
   `bad signature` and store nothing. Flash the right key back.

## 7. LED board

Check `pcbs/led_driver/docs/led_driver_assembly_top.pdf` as in step 0 first, and the input:
resistance from the jack centre pin to GND above about 100 ohm. Adapter: Mean Well GST36U24-P1J
(24 V, 5.5 x 2.1 mm centre-positive plug). LED strings: 4 stars in series per channel, mounted on
a heatsink, anode to pin 1 of J3 / J4, wired with twisted pair. Never plug or unplug a string
with the adapter connected.

1. 24 V in, J2 **unplugged**, strings connected. **Pass:** LEDs stay dark, and CTRL (R2 / R4 top
   end) reads below 0.2 V (simulation: at most 0.12 V with the 1.5 k pull-downs).
2. Connect J2 to the sensor node J4 with the 4-wire cable, pin 1 to pin 1. LEDs stay dark
   (firmware starts at 0 %).
3. Full brightness from firmware (`gos_set_spectral_mix(100, 100)`) on the bench build. **Pass:**
   current in each string 320 to 350 mA (meter in series, or the voltage across R1 / R3 is 96 to
   104 mV); simulation: 335 to 339 mA.
4. `gos_set_spectral_mix(50, 50)`. **Pass:** about half the current (simulation: 168 mA), no
   visible flicker.
5. After 10 minutes at full brightness, the AL8860s and inductors are warm, not hot (below about
   60 C by touch or an IR thermometer).

## 8. Sleep current (field build)

Flash with `low_power.conf`, unplug USB, measure battery current with a meter in series with the
cell. Expected average about 40 to 60 uA with Thread polling every second (estimate in
`HARDWARE.md`). A reading in the hundreds of uA means something is not sleeping: start with the TSL2591.

## 9. Into the enclosure

Print the base and lid (`mechanical/README.md`; the fit was checked against this board with
`mechanical/fit_check.py`).

1. Board on the four posts with M2.5x6 screws, USB-C socket in the front cut-out. **Pass:** a
   USB-C cable plugs in fully from outside.
2. Cell into the cradle, lead to J5 (pin 1 positive).
3. LED cable through the M12 gland to J4.
4. Glue the clear disc into the lid recess, then fit the lid with 4 x M3x10.
5. With the lid on, compare the lux reading with a reference meter and note the correction factor:
   the window changes what the TSL2591 sees.

### LED driver enclosure

Board on its four posts with M3x6 screws, jack and LED plugs through the side walls, the PWM
cable out through the slot beside J2, lid with 4 x M3x10. Screw the flanges to the light fixture
frame, away from water spray.

## 10. Optional: conformal coating

Phytotron humidity can condense on the boards. After the bench tests, coat both boards with an
acrylic conformal coating (for example MG Chemicals 419D spray), masking the SHT40, TSL2591, all
connectors and the buttons. Do not coat the SHT40: it must see the air.
