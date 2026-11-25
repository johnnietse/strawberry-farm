/*
 * Thread / CoAP uplink: sends one signed research packet (PACKET_V5) per sample.
 *
 * Packet, 45 bytes, every field little-endian (V5 = V4 plus the PAR field at 0x14):
 *
 *   offset  size  field
 *   0x00    1     protocol version, 0x05
 *   0x01    1     node index (CONFIG_GOS_NODE_INDEX)
 *   0x02    8     factory EUI-64 as an unsigned integer; byte 0 of the
 *                 EUI-64 is the most significant byte
 *   0x0A    4     temperature, IEEE 754 float, degC   (NaN if the read failed)
 *   0x0E    4     relative humidity, float, %RH       (NaN if the read failed)
 *   0x12    2     light, lux, clamped to 65534        (0xFFFF if the read failed)
 *   0x14    2     PAR, umol m-2 s-1, from the quantum sensor on J6 (rev 3.2)
 *                 (0xFFFF if no sensor is configured or the read failed)
 *   0x16    2     battery, mV                         (0xFFFF if the read failed)
 *   0x18    4     message counter: boot epoch << 16 | sequence. Strictly
 *                 increasing for the life of the node, so the gateway can
 *                 reject replayed packets.
 *   0x1C    1     flags: bit 7 charger state valid, bit 0 USB power present,
 *                 bit 1 charging (the charger warms the board: climate readings
 *                 taken while charging read high)
 *   0x1D    16    tag: first 16 bytes of HMAC-SHA256(node key, bytes 0x00..0x1C)
 *
 * Python decode: struct.unpack("<BBQffHHHIB16s", payload)
 *
 * The node key (CONFIG_GOS_UPLINK_KEY, 32 hex digits) comes from the
 * git-ignored credentials.conf and must match the gateway's key file
 * (gateway/tools/provision_node.py writes both). Without a valid key the
 * node does not send at all.
 *
 * The boot epoch is kept in flash (settings key "gos/epoch") and written once
 * per boot and once every 65536 packets, not once per packet.
 *
 * Sent as a non-confirmable CoAP POST so a sleepy end device does not have
 * to stay awake for an acknowledgement. The gateway's 2.04 reply carries a signed LED
 * command (downlink.c). The parent holds it until this node polls; the normal poll period
 * is 30 s to save power, so after each send the node polls fast (FAST_POLL_DELAYS_MS)
 * until the reply arrives. It is applied only if its tag is valid and it answers the
 * counter just sent.
 */
#include <math.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#include <psa/crypto.h>

#include <openthread.h>
#include <openthread/coap.h>
#include <openthread/link.h>
#include <openthread/message.h>
#include <openthread/thread.h>

#include "downlink.h"
#include "gos_main.h"
#include "packet.h"
#include "uplink.h"

LOG_MODULE_REGISTER(gos_uplink, LOG_LEVEL_INF);

/* body builder and sizes: src/packet.c (also built by tests/host/test_packet.c) */
#define BODY_LEN       GOS_PACKET_BODY_LEN
#define TAG_LEN        GOS_PACKET_TAG_LEN
#define PACKET_LEN     GOS_PACKET_LEN
#define KEY_LEN        16
#define U16_INVALID    0xFFFFU
#define EPOCH_KEY      "gos/epoch"
#define EPOCH_MAX      0xFFFFU

static psa_key_id_t key_id;
static bool ready;
static uint32_t epoch;
static uint32_t sequence;
static atomic_t sent_counter;      /* counter of the last packet sent */
static atomic_t has_sent;
static atomic_t last_command_s;     /* uptime in s + 1 of the last valid command, 0 = none */
static atomic_t reply_received;     /* set by the response handler; stops the fast polls */

/* Data requests to the parent after each packet: the reply is usually waiting within
 * 100 to 300 ms. Cumulative from the send: 0.15, 0.4, 0.8, 1.5, 2.5 s. */
static const uint16_t FAST_POLL_DELAYS_MS[] = { 150, 250, 400, 700, 1000 };
static atomic_t fast_poll_index;

static void fast_poll_handler(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(fast_poll_work, fast_poll_handler);

static void fast_poll_handler(struct k_work *work)
{
	otInstance *ot = openthread_get_default_instance();
	atomic_val_t i;

	ARG_UNUSED(work);
	if (ot == NULL || atomic_get(&reply_received)) {
		return;
	}
	openthread_mutex_lock();
	(void)otLinkSendDataRequest(ot);
	openthread_mutex_unlock();
	i = atomic_inc(&fast_poll_index) + 1;
	if (i < (atomic_val_t)ARRAY_SIZE(FAST_POLL_DELAYS_MS)) {
		k_work_schedule(&fast_poll_work, K_MSEC(FAST_POLL_DELAYS_MS[i]));
	}
}

static int epoch_load(const char *key, size_t len, settings_read_cb read_cb, void *cb_arg, void *param)
{
	ARG_UNUSED(key);
	if (len != sizeof(uint32_t)) {
		return 0;
	}
	return read_cb(cb_arg, param, len) == (ssize_t)len ? 0 : -EIO;
}

static int epoch_advance(void)
{
	if (epoch >= EPOCH_MAX) {
		LOG_ERR("message counter exhausted; re-provision this node");
		return -ENOSPC;
	}
	epoch++;
	sequence = 0;
	return settings_save_one(EPOCH_KEY, &epoch, sizeof(epoch));
}

int gos_uplink_init(void)
{
	static const char key_hex[] = CONFIG_GOS_UPLINK_KEY;
	psa_key_attributes_t attr = PSA_KEY_ATTRIBUTES_INIT;
	uint8_t key[KEY_LEN];
	int err;

	if (strlen(key_hex) != 2 * KEY_LEN || hex2bin(key_hex, 2 * KEY_LEN, key, sizeof(key)) != KEY_LEN) {
		LOG_ERR("CONFIG_GOS_UPLINK_KEY missing or not 32 hex digits: uplink disabled");
		return -EINVAL;
	}

	if (psa_crypto_init() != PSA_SUCCESS) {
		return -EIO;
	}
	psa_set_key_type(&attr, PSA_KEY_TYPE_HMAC);
	psa_set_key_bits(&attr, 8 * KEY_LEN);
	psa_set_key_usage_flags(&attr, PSA_KEY_USAGE_SIGN_MESSAGE);
	psa_set_key_algorithm(&attr, PSA_ALG_HMAC(PSA_ALG_SHA_256));
	err = psa_import_key(&attr, key, sizeof(key), &key_id) == PSA_SUCCESS ? 0 : -EIO;
	memset(key, 0, sizeof(key));
	if (err) {
		return err;
	}

	err = settings_subsys_init();
	if (!err) {
		err = settings_load_subtree_direct(EPOCH_KEY, epoch_load, &epoch);
	}
	if (!err) {
		err = epoch_advance();
	}
	if (err) {
		LOG_ERR("cannot store the message counter (%d): uplink disabled", err);
		return err;
	}

	ready = true;
	LOG_INF("uplink signing ready, counter epoch %u", epoch);
	return 0;
}

static int sign(uint8_t pkt[PACKET_LEN])
{
	uint8_t mac[PSA_HASH_LENGTH(PSA_ALG_SHA_256)];
	size_t mac_len;

	if (psa_mac_compute(key_id, PSA_ALG_HMAC(PSA_ALG_SHA_256), pkt, BODY_LEN,
			    mac, sizeof(mac), &mac_len) != PSA_SUCCESS || mac_len < TAG_LEN) {
		return -EIO;
	}
	memcpy(&pkt[BODY_LEN], mac, TAG_LEN);
	return 0;
}

int64_t gos_downlink_last_command_ms(void)
{
	atomic_val_t v = atomic_get(&last_command_s);

	return v == 0 ? -1 : (int64_t)(v - 1) * 1000;
}

/* Called by OpenThread for the gateway's reply (and with an error when the wait for
 * more replies to the multicast request ends). Runs in the OpenThread thread. */
static void response_handler(void *ctx, otMessage *msg, const otMessageInfo *info, otError result)
{
	uint8_t cmd[GOS_LED_CMD_LEN + 1];
	uint8_t mac[PSA_HASH_LENGTH(PSA_ALG_SHA_256)];
	struct gos_led_cmd led;
	size_t mac_len;
	uint16_t len;
	int err;

	ARG_UNUSED(ctx);
	ARG_UNUSED(info);
	if (result != OT_ERROR_NONE || msg == NULL || otCoapMessageGetCode(msg) != OT_COAP_CODE_CHANGED) {
		return;
	}
	atomic_set(&reply_received, 1);
	len = otMessageRead(msg, otMessageGetOffset(msg), cmd, sizeof(cmd));
	if (len != GOS_LED_CMD_LEN || !atomic_get(&has_sent)) {
		return;
	}
	if (psa_mac_compute(key_id, PSA_ALG_HMAC(PSA_ALG_SHA_256), cmd, GOS_LED_CMD_BODY_LEN,
			    mac, sizeof(mac), &mac_len) != PSA_SUCCESS || mac_len < GOS_LED_CMD_TAG_LEN) {
		return;
	}
	err = gos_led_command_parse(cmd, len, (uint32_t)atomic_get(&sent_counter), mac, &led);
	if (err) {
		LOG_WRN("LED command rejected: %d", err);
		return;
	}
	err = gos_set_spectral_mix(led.blue_pct, led.red_pct);
	if (err) {
		LOG_ERR("LED board PWM failed: %d", err);
		return;
	}
	atomic_set(&last_command_s, (atomic_val_t)(k_uptime_get() / 1000 + 1));
	LOG_INF("LED blue %u %%, red %u %%", led.blue_pct, led.red_pct);
}

int gos_uplink_send(const struct gos_sensor_data *d)
{
	otInstance *ot = openthread_get_default_instance();
	uint8_t pkt[PACKET_LEN];
	otMessageInfo info;
	otExtAddress eui;
	otMessage *msg;
	otError err;
	int ret = 0;

	if (!ready) {
		return -EACCES;
	}
	if (ot == NULL) {
		return -ENODEV;
	}

	openthread_mutex_lock();

	if (otThreadGetDeviceRole(ot) < OT_DEVICE_ROLE_CHILD) {
		ret = -ENOTCONN;
		goto out;
	}

	if (sequence > 0xFFFFU) {
		ret = epoch_advance();
		if (ret) {
			ready = false;
			goto out;
		}
	}

	otLinkGetFactoryAssignedIeeeEui64(ot, &eui);
	gos_packet_build_body(pkt, eui.m8, CONFIG_GOS_NODE_INDEX, d, (epoch << 16) | sequence);
	atomic_set(&sent_counter, (atomic_val_t)((epoch << 16) | sequence));
	atomic_set(&has_sent, 1);
	sequence++; /* never reuse a counter, even if the send below fails */
	ret = sign(pkt);
	if (ret) {
		goto out;
	}

	memset(&info, 0, sizeof(info));
	if (otIp6AddressFromString(CONFIG_GOS_UPLINK_PEER_ADDR, &info.mPeerAddr) != OT_ERROR_NONE) {
		ret = -EINVAL;
		goto out;
	}
	info.mPeerPort = CONFIG_GOS_UPLINK_PEER_PORT;

	msg = otCoapNewMessage(ot, NULL);
	if (msg == NULL) {
		ret = -ENOMEM;
		goto out;
	}

	otCoapMessageInit(msg, OT_COAP_TYPE_NON_CONFIRMABLE, OT_COAP_CODE_POST);
	otCoapMessageGenerateToken(msg, OT_COAP_DEFAULT_TOKEN_LENGTH);
	err = otCoapMessageAppendUriPathOptions(msg, CONFIG_GOS_UPLINK_URI_PATH);
	if (err == OT_ERROR_NONE) {
		err = otCoapMessageSetPayloadMarker(msg);
	}
	if (err == OT_ERROR_NONE) {
		err = otMessageAppend(msg, pkt, sizeof(pkt));
	}
	if (err == OT_ERROR_NONE) {
		err = otCoapSendRequest(ot, msg, &info, response_handler, NULL);
	}
	if (err != OT_ERROR_NONE) {
		otMessageFree(msg);
		LOG_WRN("CoAP send failed: %s", otThreadErrorToString(err));
		ret = -EIO;
	} else {
		atomic_set(&reply_received, 0);
		atomic_set(&fast_poll_index, 0);
		k_work_reschedule(&fast_poll_work, K_MSEC(FAST_POLL_DELAYS_MS[0]));
	}

out:
	openthread_mutex_unlock();
	return ret;
}

void gos_uplink_log_identity(void)
{
	otInstance *ot = openthread_get_default_instance();
	otExtAddress eui;

	if (ot == NULL) {
		return;
	}
	openthread_mutex_lock();
	otLinkGetFactoryAssignedIeeeEui64(ot, &eui);
	openthread_mutex_unlock();
	LOG_INF("node %d, EUI-64 %02X%02X%02X%02X%02X%02X%02X%02X", CONFIG_GOS_NODE_INDEX,
		eui.m8[0], eui.m8[1], eui.m8[2], eui.m8[3], eui.m8[4], eui.m8[5], eui.m8[6], eui.m8[7]);
}
