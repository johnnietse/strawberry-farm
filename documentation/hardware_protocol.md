# G.O.S. Hardware-Software Protocol Specification

To fulfill the **"Preserved Sample Identity"** requirement, all nRF52 nodes must follow this packet structure. This bridges the physical C++ firmware to the Python/Postgres backbone.

## 📡 1. The Research Packet (PACKET_V2)
Sent via UDP (MQTT-SN / CoAP) from the nRF52 node to the Raspberry Pi.

| Offset | Field | Type | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0x00** | PROTOCOL_VER | uint8 | - | Always `0x02` |
| **0x01** | DEVICE_INDEX | uint8 | - | 1-40 (Mapped to Phytotron Row) |
| **0x02** | HW_ID | uint64 | - | Unique nRF52 Hardware EUI64 |
| **0x0A** | TEMPERATURE  | float32| °C | SHT4x Filtered Value |
| **0x0E** | HUMIDITY     | float32| %RH | SHT4x Raw Value |
| **0x12** | LUX_LEVEL    | uint16 | lux | TSL2591 Light Level |
| **0x14** | BATT_VOLTAGE | uint16 | mV | ADC reading of 18650 cell |

### Transport and encoding (as implemented)

- Node firmware `pcbs/gos_sensor_node/firmware/src/uplink.c` sends the packet as a non-confirmable CoAP POST to `/telemetry`, UDP 5683, default destination `ff03::1`.
- All fields are little-endian. The EUI-64 is an integer whose most significant byte is the first byte of the EUI-64. Decode with `struct.unpack("<BBQffHH", payload)`.
- A failed reading is sent as NaN (floats) or 0xFFFF (integers) and stored as NULL.
- The gateway receiver is `gateway/services/coap_receiver.py`. It writes `node_id = RF-NODE-<index>`, `sample_identity = EUI64:<16 hex digits>`, temperature, humidity and battery to `raw_telemetry`. Lux goes in `payload.light_lux`; `par_umol` stays NULL because the node measures lux, not PAR.

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
