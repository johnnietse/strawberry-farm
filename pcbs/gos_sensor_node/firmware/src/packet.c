/*
 * PACKET_V5 body builder (layout in src/uplink.c). No Zephyr calls: also built on a PC by
 * tests/host/test_packet.c.
 */
#include <math.h>
#include <string.h>

#include "packet.h"

static void put_le16(uint16_t v, uint8_t *dst)
{
	dst[0] = (uint8_t)v;
	dst[1] = (uint8_t)(v >> 8);
}

static void put_le32(uint32_t v, uint8_t *dst)
{
	put_le16((uint16_t)v, dst);
	put_le16((uint16_t)(v >> 16), dst + 2);
}

static void put_float(float v, uint8_t *dst)
{
	uint32_t bits;

	memcpy(&bits, &v, sizeof(bits));
	put_le32(bits, dst);
}

static uint16_t clamp_u16(int v)
{
	if (v < 0) {
		return 0;
	}
	return v >= (int)GOS_U16_INVALID ? (uint16_t)(GOS_U16_INVALID - 1U) : (uint16_t)v;
}

void gos_packet_build_body(uint8_t body[GOS_PACKET_BODY_LEN], const uint8_t eui[8], uint8_t node_index,
			   const struct gos_sensor_data *d, uint32_t counter)
{
	int climate = (d->valid & GOS_VALID_CLIMATE) != 0;

	body[0] = GOS_PACKET_VERSION;
	body[1] = node_index;
	for (int i = 0; i < 8; i++) {          /* EUI-64 as a u64, little-endian */
		body[2 + i] = eui[7 - i];
	}
	put_float(climate ? (float)d->temp_mc / 1000.0f : NAN, &body[10]);
	put_float(climate ? (float)d->humidity_mpct / 1000.0f : NAN, &body[14]);
	put_le16((d->valid & GOS_VALID_LIGHT) ? clamp_u16(d->light_lux) : GOS_U16_INVALID, &body[18]);
	put_le16((d->valid & GOS_VALID_PAR) ? clamp_u16(d->par_umol) : GOS_U16_INVALID, &body[20]);
	put_le16((d->valid & GOS_VALID_BATTERY) ? clamp_u16(d->battery_mv) : GOS_U16_INVALID, &body[22]);
	put_le32(counter, &body[24]);
	/* bit 7: charger state read; bit 0: USB power present; bit 1: charging. The charger
	 * warms the board, so the gateway can flag climate readings taken while charging. */
	body[28] = (d->valid & GOS_VALID_CHARGER)
			   ? (uint8_t)(0x80U | (d->usb_power ? 0x01U : 0U) | (d->charging ? 0x02U : 0U))
			   : 0U;
}
