/*
 * Host-side test of the LED command checks (src/downlink.c), with commands made by the
 * gateway (gateway/services/coap_receiver.py build_led_command, key 00 01 .. 0f,
 * counter 0x00050003). gateway/tests/test_led_control.py pins the same bytes.
 *
 *   gcc -Wall -Wextra -Werror -I ../../src -o test_downlink test_downlink.c ../../src/downlink.c
 *   ./test_downlink
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "downlink.h"

static int hex(const char *s, uint8_t *out, size_t n)
{
	for (size_t i = 0; i < n; i++) {
		unsigned v;
		if (sscanf(s + 2 * i, "%2x", &v) != 1) {
			return -1;
		}
		out[i] = (uint8_t)v;
	}
	return 0;
}

static int failures;

static void expect(const char *name, int got, int want)
{
	printf("%-40s %s (got %d, want %d)\n", name, got == want ? "ok" : "FAIL", got, want);
	failures += got != want;
}

int main(void)
{
	const uint32_t counter = 0x00050003;
	uint8_t cmd[GOS_LED_CMD_LEN], tag[GOS_LED_CMD_TAG_LEN], bad[GOS_LED_CMD_LEN];
	struct gos_led_cmd led = { 0 };

	/* blue 30 %, red 70 % */
	hex("c11e4603000500b164775eb9c072c59ceccd347072416e", cmd, sizeof(cmd));
	/* HMAC-SHA256(key, cmd[0..6])[:16], as the node computes it with PSA */
	hex("b164775eb9c072c59ceccd347072416e", tag, sizeof(tag));

	expect("valid command", gos_led_command_parse(cmd, sizeof(cmd), counter, tag, &led), 0);
	expect("blue level", led.blue_pct, 30);
	expect("red level", led.red_pct, 70);

	expect("answers another packet", gos_led_command_parse(cmd, sizeof(cmd), counter + 1, tag, &led), -ESTALE);

	/* The node computes the expected tag over the body it received, so a changed level gives a
	 * different expected tag (checked on the gateway side in test_led_control.py); here: a
	 * received tag that does not match the expected one. */
	memcpy(bad, cmd, sizeof(bad));
	bad[GOS_LED_CMD_BODY_LEN + 5] ^= 0x01;
	expect("bad tag", gos_led_command_parse(bad, sizeof(bad), counter, tag, &led), -EACCES);

	memcpy(bad, cmd, sizeof(bad));
	bad[0] = 0x04;
	expect("wrong version", gos_led_command_parse(bad, sizeof(bad), counter, tag, &led), -EINVAL);
	expect("short payload", gos_led_command_parse(cmd, sizeof(cmd) - 1, counter, tag, &led), -EINVAL);
	expect("no payload", gos_led_command_parse(NULL, 0, counter, tag, &led), -EINVAL);

	printf("%s\n", failures ? "FAILED" : "all passed");
	return failures != 0;
}
