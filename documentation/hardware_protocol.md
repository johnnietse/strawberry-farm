# G.O.S. Hardware-Software Protocol Specification

To fulfill the **"Preserved Sample Identity"** requirement, all nRF52 nodes must follow this packet structure. This bridges the physical C++ firmware to the Python/Postgres backbone.

## 📡 1. The Research Packet (PACKET_V2)
Sent via UDP (MQTT-SN / CoAP) from the nRF52 node to the Raspberry Pi.

*Table 1. The original PACKET_V2 layout from node to Pi: byte offset, field, type and unit. The current signed PACKET_V5 layout (rev 3.2 firmware, with PAR) is in pcbs/gos_sensor_node/HARDWARE.md.*

| Offset | Field | Type | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0x00** | PROTOCOL_VER | uint8 | - | Always `0x02` |
| **0x01** | DEVICE_INDEX | uint8 | - | 1-40 (Mapped to Phytotron Row) |
| **0x02** | HW_ID | uint64 | - | Unique nRF52 Hardware EUI64 |
| **0x0A** | TEMPERATURE  | float32| °C | SHT4x Filtered Value |
| **0x0E** | HUMIDITY     | float32| %RH | SHT4x Raw Value |
| **0x12** | LUX_LEVEL    | uint16 | lux | TSL2591 Light Level |
| **0x14** | BATT_VOLTAGE | uint16 | mV | ADC reading of 18650 cell |

### Transport, encoding and signing (as implemented, PACKET_V5)

- Node firmware `pcbs/gos_sensor_node/firmware/src/uplink.c` sends a non-confirmable CoAP POST to `/telemetry`, UDP 5683, default destination `ff03::1`.
- PACKET_V5 (rev 3.2 firmware, `src/packet.c`): the 22 bytes above with a PAR field inserted after the light field (u16, umol m-2 s-1 from the quantum sensor on J6, 0xFFFF = none), then the battery, a 32-bit message counter (offset 0x18), a flags byte (0x1C) and a 16-byte tag (0x1D): 45 bytes, version byte 5. Flags: bit 7 = charger state valid, bit 0 = USB power present, bit 1 = charging.
- The receiver still accepts PACKET_V4 (43 bytes, no PAR) and PACKET_V3 (42 bytes, no flags byte) from nodes on older firmware.
- All fields are little-endian. The EUI-64 is an integer whose most significant byte is the first byte of the EUI-64. Decode with `struct.unpack("<BBQffHHHIB16s", payload)` (V5).
- A failed reading is sent as NaN (floats) or 0xFFFF (integers) and stored as NULL.
- The gateway receiver `gateway/services/coap_receiver.py` stores a packet only if the tag verifies, the counter is higher than the last stored for that node, and (when registered) the EUI-64 matches. It writes `node_id = RF-NODE-<index>`, `sample_identity = EUI64:<16 hex digits>`, temperature, humidity and battery to `raw_telemetry`. Lux, the counter, `authenticated`, `usb_power` and `charging` go in `payload`; `par_umol` stays NULL because the node measures lux, not PAR.
- Keys are provisioned with `gateway/tools/provision_node.py`; see `pcbs/gos_sensor_node/HARDWARE.md`.

### LED command (downlink, in the reply)

The gateway answers every accepted PACKET_V5 (or V4) with CoAP 2.04 (a NON response to the NON request,
RFC 7252 section 8.2) whose payload is the node's LED command, 23 bytes:

*Table 2. The LED command the Pi returns in the CoAP reply: 23 bytes, signed with the node's key and bound to the reading it answers.*

| Offset | Size | Field |
|---|---|---|
| 0x00 | 1 | 0xC1 (LED command, version 1) |
| 0x01 | 1 | blue level, 0 to 100 % |
| 0x02 | 1 | red level, 0 to 100 % |
| 0x03 | 4 | counter of the packet this answers (u32 LE) |
| 0x07 | 16 | first 16 bytes of HMAC-SHA256(node key, bytes 0x00 to 0x06) |

- The node (`src/downlink.c`, called from the response handler in `src/uplink.c`) applies it only
  if the tag verifies with its own key and the counter is the one it just sent, so a command
  cannot be forged, sent to another node or replayed. The sleepy end device polls its parent
  every second, so the reply arrives within about a second.
- The level is the newest unexpired row in `led_setpoints` for that node (or `ALL`), after the
  safety monitor `gateway/services/led_safety.py`: off in the dark period (default 22:00 to
  06:00, `LED_TZ`), off above 32 C, at most 50 % without a temperature reading, at most +25 %
  per command, fallback 0 % without a setpoint. Each command sent is logged in `led_commands`.
- If no valid command arrives for `CONFIG_GOS_LED_HOLD_S` (default 900 s), the node switches the
  LED board to `CONFIG_GOS_LED_FALLBACK_BLUE` / `_RED` (default 0 %).
- Test vector (key 00 01 .. 0f, counter 0x00050003, blue 30, red 70):
  `c11e4603000500b164775eb9c072c59ceccd347072416e`, pinned in
  `firmware/tests/host/test_downlink.c` and `gateway/tests/test_led_control.py`.

## 🔗 2. The Database Sink (Integration)
The Gateway translates the binary packet above into the following SQL Insert:

```sql
INSERT INTO raw_telemetry (node_id, sample_identity, payload) 
VALUES ('RF-NODE-12', 'EUI64:0011223344556677', '{"temp": 24.5, "par": 800, "batt": 3700}');
```

## 🧪 3. Hardware Debug Interface
RAs can verify the identity on the node's debug console (TP5 / TP6, 115200 8N1): at boot the rev 3 firmware prints its node index and factory EUI-64 (`node 1, EUI-64 ...`); see `documentation/bring_up.md`, step 4.
```text
G.O.S. sensor node rev 3.2 firmware
uplink signing ready, counter epoch 5
node 1, EUI-64 F4CE360011223344
```

## 📦 4. Sample Persistence
Rev 3 nodes do not queue samples: no external flash is fitted (the QSPI peripheral is disabled
in the board overlay), and only the boot epoch of the message counter is kept in the module's
own flash. A packet sent while the gateway is down is lost; the counter in every stored packet
shows such a gap in the dataset. (The rev 2 design planned a QSPI flash queue; it was not built.)
