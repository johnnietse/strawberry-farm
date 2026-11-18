# G.O.S. Hardware-Software Protocol Specification

To fulfill the **"Preserved Sample Identity"** requirement, all nRF52 nodes must follow this packet structure. This bridges the physical C++ firmware to the Python/Postgres backbone.

## 📡 1. The Research Packet (PACKET_V2)
Sent via UDP (MQTT-SN / CoAP) from the nRF52 node to the Raspberry Pi.

*Table 1. The original PACKET_V2 layout from node to Pi: byte offset, field, type and unit. The current signed PACKET_V4 layout is in pcbs/gos_sensor_node/HARDWARE.md.*

| Offset | Field | Type | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0x00** | PROTOCOL_VER | uint8 | - | Always `0x02` |
| **0x01** | DEVICE_INDEX | uint8 | - | 1-40 (Mapped to Phytotron Row) |
| **0x02** | HW_ID | uint64 | - | Unique nRF52 Hardware EUI64 |
| **0x0A** | TEMPERATURE  | float32| °C | SHT4x Filtered Value |
| **0x0E** | HUMIDITY     | float32| %RH | SHT4x Raw Value |
| **0x12** | LUX_LEVEL    | uint16 | lux | TSL2591 Light Level |
| **0x14** | BATT_VOLTAGE | uint16 | mV | ADC reading of 18650 cell |

### Transport, encoding and signing (as implemented, PACKET_V4)

- Node firmware `pcbs/gos_sensor_node/firmware/src/uplink.c` sends a non-confirmable CoAP POST to `/telemetry`, UDP 5683, default destination `ff03::1`.
- The 22 bytes above are followed by a 32-bit message counter (offset 0x16), a flags byte (0x1A) and a 16-byte tag (0x1B), 43 bytes in total, with the version byte set to 4. Flags: bit 7 = charger state valid, bit 0 = USB power present, bit 1 = charging. The charger warms the board, so climate readings taken while charging read high; the gateway stores the flags so they can be filtered. The tag is the first 16 bytes of HMAC-SHA256 over bytes 0 to 26, keyed with the node's own 128-bit key.
- The receiver still accepts PACKET_V3 (42 bytes, no flags byte, version 3) from nodes on older firmware.
- All fields are little-endian. The EUI-64 is an integer whose most significant byte is the first byte of the EUI-64. Decode with `struct.unpack("<BBQffHHIB16s", payload)`.
- A failed reading is sent as NaN (floats) or 0xFFFF (integers) and stored as NULL.
- The gateway receiver `gateway/services/coap_receiver.py` stores a packet only if the tag verifies, the counter is higher than the last stored for that node, and (when registered) the EUI-64 matches. It writes `node_id = RF-NODE-<index>`, `sample_identity = EUI64:<16 hex digits>`, temperature, humidity and battery to `raw_telemetry`. Lux, the counter, `authenticated`, `usb_power` and `charging` go in `payload`; `par_umol` stays NULL because the node measures lux, not PAR.
- Keys are provisioned with `gateway/tools/provision_node.py`; see `pcbs/gos_sensor_node/HARDWARE.md`.

### LED command (downlink, in the reply)

The gateway answers every accepted PACKET_V4 with CoAP 2.04 (a NON response to the NON request,
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
RAs can verify the "Identity" by connecting to the node [UART console](file:///c:/Users/Johnnie/Documents/Stawberry_Farm/firmware/drivers/console_uart.cpp) and sending command `I` (Identity).
```text
> I
--- G.O.S. IDENTITY REPORT ---
NODE_INDEX: 12
MAC_ADDR: F0:F1:F2:F3:F4:F5
HW_PLATFORM: nRF52840-QIAA
UPTIME: 12450s
```

## 📦 4. Sample Persistence
Even if the Mesh fails, the node uses its **QSPI Flash** to queue up to 5000 samples. When the Raspberry Pi comes back online, the node performs a "Bulk Sync", ensuring no gaps in the research dataset.
