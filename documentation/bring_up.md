# Sensor node bring-up (rev 3.1)

Step-by-step first power-on, once boards exist. Each step says what "pass" looks like; stop at
the first failure. Pin map: `nrf52840_pinout.md`. Design reference:
`pcbs/gos_sensor_node/HARDWARE.md`.

You need: an SWD probe with a 10-pin 1.27 mm Cortex cable (J-Link, or an nRF52 DK's debug
port), a USB-C cable, a 3.3 V USB-serial adapter for TP5/TP6, an 18650 cell with a JST-PH lead,
and the Raspberry Pi border router from `raspberry_pi_setup.md`.

## 1. Power, no cell

1. Plug in USB-C only. **Pass:** TP7 (VBUS) about 5 V, TP2 (VSYS) about 4.4 V, TP1 (+3V3) 3.3 V.
2. Current from USB with no firmware should be a few mA. Much more means a short: unplug and inspect.

## 2. Cell and charger

1. Check the lead: J5 pin 1 = positive. Connect the cell, keep USB plugged in.
2. **Pass:** TP3 (VBAT) reads the cell voltage, amber LED D1 lights while charging and goes out when full.
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
SELECT time, node_id, temp_c, humidity_pct, battery_mv, payload->>'light_lux', payload->>'counter'
FROM raw_telemetry WHERE node_id = 'RF-NODE-01' ORDER BY time DESC LIMIT 5;
```

4. **Security check:** reflash the node with a different `CONFIG_GOS_UPLINK_KEY`. The receiver must log
   `bad signature` and store nothing. Flash the right key back.

## 7. LED board

1. 24 V adapter into the LED board, J2 **unplugged**, LED strings connected. **Pass:** LEDs stay dark.
2. Connect J2 to the sensor node J4. LEDs stay dark (firmware starts at 0 %).
3. Set a mix from firmware (`gos_set_spectral_mix(50, 50)`) on the bench build. **Pass:** both strings at half brightness, no visible flicker.

## 8. Sleep current (field build)

Flash with `low_power.conf`, unplug USB, measure battery current with a meter in series with the
cell. Expected average about 40 to 60 uA with Thread polling every second (estimate in
`HARDWARE.md`). A reading in the hundreds of uA means something is not sleeping: start with the TSL2591.
