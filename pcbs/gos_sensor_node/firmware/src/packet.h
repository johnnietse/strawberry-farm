#ifndef GOS_PACKET_H
#define GOS_PACKET_H

/*
 * Research packet body (PACKET_V5), kept free of Zephyr and OpenThread so the host-side test
 * (tests/host/test_packet.c) builds exactly this code and checks the bytes against the
 * gateway's decoder. Layout: src/uplink.c.
 */
#include <stdint.h>

#include "gos_main.h"

#define GOS_PACKET_VERSION  0x05
#define GOS_PACKET_BODY_LEN 29
#define GOS_PACKET_TAG_LEN  16
#define GOS_PACKET_LEN      (GOS_PACKET_BODY_LEN + GOS_PACKET_TAG_LEN)
#define GOS_U16_INVALID     0xFFFFU

/* Fill bytes 0..GOS_PACKET_BODY_LEN-1. eui: the factory EUI-64, byte 0 most significant. */
void gos_packet_build_body(uint8_t body[GOS_PACKET_BODY_LEN], const uint8_t eui[8], uint8_t node_index,
			   const struct gos_sensor_data *d, uint32_t counter);

#endif /* GOS_PACKET_H */
