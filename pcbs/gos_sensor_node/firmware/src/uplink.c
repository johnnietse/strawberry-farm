/*
 * Thread / CoAP uplink: sends one signed research packet (PACKET_V4) per sample.
 *
 * Packet, 43 bytes, every field little-endian:
 *
 *   offset  size  field
 *   0x00    1     protocol version, 0x04
 *   0x01    1     node index (CONFIG_GOS_NODE_INDEX)
 *   0x02    8     factory EUI-64 as an unsigned integer; byte 0 of the
 *                 EUI-64 is the most significant byte
 *   0x0A    4     temperature, IEEE 754 float, degC   (NaN if the read failed)
 *   0x0E    4     relative humidity, float, %RH       (NaN if the read failed)
 *   0x12    2     light, lux, clamped to 65534        (0xFFFF if the read failed)
 *   0x14    2     battery, mV                         (0xFFFF if the read failed)
 *   0x16    4     message counter: boot epoch << 16 | sequence. Strictly
 *                 increasing for the life of the node, so the gateway can
 *                 reject replayed packets.
 *   0x1A    1     flags: bit 7 charger state valid, bit 0 USB power present,
 *                 bit 1 charging (the charger warms the board: climate readings
 *                 taken while charging read high)
 *   0x1B    16    tag: first 16 bytes of HMAC-SHA256(node key, bytes 0x00..0x1A)
 *
 * Python decode: struct.unpack("<BBQffHHIB16s", payload)
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
 * to stay awake for an acknowledgement.
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

#include "gos_main.h"
#include "uplink.h"

LOG_MODULE_REGISTER(gos_uplink, LOG_LEVEL_INF);

#define PACKET_VERSION 0x04
#define BODY_LEN       27
#define TAG_LEN        16
#define PACKET_LEN     (BODY_LEN + TAG_LEN)
#define KEY_LEN        16
#define U16_INVALID    0xFFFFU
#define EPOCH_KEY      "gos/epoch"
#define EPOCH_MAX      0xFFFFU

static psa_key_id_t key_id;
static bool ready;
static uint32_t epoch;
static uint32_t sequence;

static void put_float(float v, uint8_t *dst)
{
	uint32_t bits;

	memcpy(&bits, &v, sizeof(bits));
	sys_put_le32(bits, dst);
}

static uint16_t clamp_u16(int v)
{
	if (v < 0) {
		return 0;
	}
	return v >= (int)U16_INVALID ? (uint16_t)(U16_INVALID - 1U) : (uint16_t)v;
}

/* Fills bytes 0..BODY_LEN-1. Exposed for the host-side packet test. */
void gos_uplink_build_body(uint8_t body[BODY_LEN], const otExtAddress *eui,
			   const struct gos_sensor_data *d, uint32_t counter)
{
	bool climate = d->valid & GOS_VALID_CLIMATE;
	uint64_t id = 0;

	for (size_t i = 0; i < sizeof(eui->m8); i++) {
		id = (id << 8) | eui->m8[i];
	}

	body[0] = PACKET_VERSION;
	body[1] = CONFIG_GOS_NODE_INDEX;
	sys_put_le64(id, &body[2]);
	put_float(climate ? d->temp_mc / 1000.0f : NAN, &body[10]);
	put_float(climate ? d->humidity_mpct / 1000.0f : NAN, &body[14]);
	sys_put_le16((d->valid & GOS_VALID_LIGHT) ? clamp_u16(d->light_lux) : U16_INVALID, &body[18]);
	sys_put_le16((d->valid & GOS_VALID_BATTERY) ? clamp_u16(d->battery_mv) : U16_INVALID, &body[20]);
	sys_put_le32(counter, &body[22]);
	/* bit 7: charger state read; bit 0: USB power present; bit 1: charging. The charger
	 * warms the board, so the gateway can flag climate readings taken while charging. */
	body[26] = (d->valid & GOS_VALID_CHARGER)
			   ? (uint8_t)(0x80U | (d->usb_power ? 0x01U : 0U) | (d->charging ? 0x02U : 0U))
			   : 0U;
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
	gos_uplink_build_body(pkt, &eui, d, (epoch << 16) | sequence);
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
		err = otCoapSendRequest(ot, msg, &info, NULL, NULL);
	}
	if (err != OT_ERROR_NONE) {
		otMessageFree(msg);
		LOG_WRN("CoAP send failed: %s", otThreadErrorToString(err));
		ret = -EIO;
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
