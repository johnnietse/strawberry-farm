#ifndef GOS_DOWNLINK_H
#define GOS_DOWNLINK_H

#include <errno.h>
#include <stddef.h>
#include <stdint.h>

#ifndef ESTALE /* host builds (MinGW) only; Zephyr defines it */
#define ESTALE 116
#endif

#define GOS_LED_CMD_VERSION  0xC1
#define GOS_LED_CMD_BODY_LEN 7
#define GOS_LED_CMD_TAG_LEN  16
#define GOS_LED_CMD_LEN      (GOS_LED_CMD_BODY_LEN + GOS_LED_CMD_TAG_LEN)

struct gos_led_cmd {
	uint8_t blue_pct;
	uint8_t red_pct;
};

/*
 * Check a received LED command. `expected_tag` is HMAC-SHA256(node key, cmd[0..6]),
 * truncated to 16 bytes, computed by the caller. Returns 0 and fills `out` if the command
 * is valid; -EINVAL (wrong length or version), -EACCES (bad tag), -ESTALE (answers another
 * packet) or -ERANGE (level above 100 %) otherwise.
 */
int gos_led_command_parse(const uint8_t *cmd, size_t len, uint32_t expected_counter,
			  const uint8_t expected_tag[GOS_LED_CMD_TAG_LEN], struct gos_led_cmd *out);

/* Uptime (ms) of the last valid LED command, or -1 if none since boot. */
int64_t gos_downlink_last_command_ms(void);

#endif /* GOS_DOWNLINK_H */
