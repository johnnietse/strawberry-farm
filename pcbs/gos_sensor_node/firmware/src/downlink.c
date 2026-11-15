/*
 * LED command (downlink) checks. The gateway answers each uplink packet with a CoAP 2.04
 * whose payload is a signed LED command:
 *
 *   offset  size  field
 *   0x00    1     0xC1 (LED command, version 1)
 *   0x01    1     blue level, 0..100 %
 *   0x02    1     red level, 0..100 %
 *   0x03    4     counter of the uplink packet this answers (u32 LE)
 *   0x07    16    first 16 bytes of HMAC-SHA256(node key, bytes 0x00..0x06)
 *
 * The caller (uplink.c, which holds the key) computes the expected tag over the first
 * GOS_LED_CMD_BODY_LEN bytes; this file only checks the fields, so it can be tested on a PC.
 * Binding the command to the counter just sent means an old command cannot be replayed and
 * a forged one has no valid tag.
 */
#include <errno.h>
#include <stddef.h>
#include <stdint.h>

#include "downlink.h"

static uint32_t get_le32(const uint8_t *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

int gos_led_command_parse(const uint8_t *cmd, size_t len, uint32_t expected_counter,
			  const uint8_t expected_tag[GOS_LED_CMD_TAG_LEN], struct gos_led_cmd *out)
{
	uint8_t diff = 0;

	if (cmd == NULL || len != GOS_LED_CMD_LEN || cmd[0] != GOS_LED_CMD_VERSION) {
		return -EINVAL;
	}
	/* constant-time tag comparison */
	for (size_t i = 0; i < GOS_LED_CMD_TAG_LEN; i++) {
		diff |= cmd[GOS_LED_CMD_BODY_LEN + i] ^ expected_tag[i];
	}
	if (diff != 0) {
		return -EACCES;
	}
	if (get_le32(&cmd[3]) != expected_counter) {
		return -ESTALE;
	}
	if (cmd[1] > 100 || cmd[2] > 100) {
		return -ERANGE;
	}
	out->blue_pct = cmd[1];
	out->red_pct = cmd[2];
	return 0;
}
