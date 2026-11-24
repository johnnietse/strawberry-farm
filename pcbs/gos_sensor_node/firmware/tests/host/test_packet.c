/*
 * Host-side test of the research packet body (src/packet.c, PACKET_V5). The expected bytes
 * are what the gateway's decoder format makes from the same reading
 * (struct.pack("<BBQffHHHIB", ...) in Python, gateway/services/coap_receiver.py V5_FORMAT),
 * so a layout change on either side fails here. gateway/tests/test_coap_receiver.py pins the
 * same bytes.
 *
 *   gcc -Wall -Wextra -Werror -I . -I ../../include -I ../../src -o test_packet test_packet.c ../../src/packet.c
 *   ./test_packet
 */
#include <stdio.h>
#include <string.h>

#include "packet.h"

static int failures;

static void check(const char *name, const struct gos_sensor_data *d, const char *want_hex)
{
	static const uint8_t eui[8] = { 0xF4, 0xCE, 0x36, 0x00, 0x11, 0x22, 0x33, 0x44 };
	uint8_t body[GOS_PACKET_BODY_LEN];
	char got[2 * GOS_PACKET_BODY_LEN + 1];

	gos_packet_build_body(body, eui, 7, d, 0x00050003);
	for (int i = 0; i < GOS_PACKET_BODY_LEN; i++) {
		sprintf(&got[2 * i], "%02x", body[i]);
	}
	int ok = strcmp(got, want_hex) == 0;
	printf("%-34s %s\n", name, ok ? "ok" : "FAIL");
	if (!ok) {
		printf("  got  %s\n  want %s\n", got, want_hex);
	}
	failures += !ok;
}

int main(void)
{
	struct gos_sensor_data d = {
		.temp_mc = -1250, .humidity_mpct = 55500, .light_lux = 70000, .battery_mv = 3712,
		.par_umol = 1234, .usb_power = true, .charging = true,
		.valid = GOS_VALID_CLIMATE | GOS_VALID_LIGHT | GOS_VALID_BATTERY | GOS_VALID_CHARGER | GOS_VALID_PAR,
	};

	check("V5 with PAR, charging on USB", &d, "0507443322110036cef40000a0bf00005e42feffd204800e0300050083");
	d.valid &= ~GOS_VALID_PAR;
	check("V5 without PAR sensor", &d, "0507443322110036cef40000a0bf00005e42feffffff800e0300050083");
	d.valid = 0;
	check("V5 every reading failed", &d, "0507443322110036cef40000c07f0000c07fffffffffffff0300050000");
	check("body length 29, packet 45", &d,
	      (GOS_PACKET_BODY_LEN == 29 && GOS_PACKET_LEN == 45)
		      ? "0507443322110036cef40000c07f0000c07fffffffffffff0300050000" : "length");
	printf("%s\n", failures ? "FAILED" : "ALL PASS");
	return failures != 0;
}
