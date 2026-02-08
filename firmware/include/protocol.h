#ifndef GOS_PROTOCOL_H
#define GOS_PROTOCOL_H

#include <stdint.h>

/**
 * @brief G.O.S. Research Packet Format (v2)
 * Matches the specification in /documentation/hardware_protocol.md
 */
struct __attribute__((packed)) gos_research_packet_t {
  uint8_t protocol_ver;    // Always 0x02
  uint8_t node_index;      // 1-40
  uint64_t hardware_eui64; // Unique nRF52 ID
  float temp_c;            // Filtered Temperature
  float hum_pct;           // Relative Humidity
  uint16_t par_lux;        // Spectral Irradiance (Lux)
  uint16_t batt_mv;        // Battery Voltage
};

#endif // GOS_PROTOCOL_H
