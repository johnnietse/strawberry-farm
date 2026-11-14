/*
 * Thread / CoAP uplink: sends one PACKET_V2 research packet per sample.
 *
 * Packet layout (documentation/hardware_protocol.md), 22 bytes, every field
 * little-endian:
 *
 *   offset  size  field
 *   0x00    1     protocol version, always 0x02
 *   0x01    1     node index (CONFIG_GOS_NODE_INDEX)
 *   0x02    8     factory EUI-64 as an unsigned integer; byte 0 of the
 *                 EUI-64 is the most significant byte
 *   0x0A    4     temperature, IEEE 754 float, degC   (NaN if the read failed)
 *   0x0E    4     relative humidity, float, %RH       (NaN if the read failed)
 *   0x12    2     light, lux, clamped to 65534        (0xFFFF if the read failed)
 *   0x14    2     battery, mV                         (0xFFFF if the read failed)
 *
 * Python decode: struct.unpack("<BBQffHH", payload)
 *
 * Sent as a non-confirmable CoAP POST so a sleepy end device does not have
 * to stay awake for an acknowledgement.
 */
#include <math.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/byteorder.h>

#include <openthread.h>
#include <openthread/coap.h>
#include <openthread/link.h>
#include <openthread/message.h>
#include <openthread/thread.h>

#include "gos_main.h"
#include "uplink.h"

LOG_MODULE_REGISTER(gos_uplink, LOG_LEVEL_INF);

#define PACKET_VERSION 0x02
#define PACKET_LEN     22
#define U16_INVALID    0xFFFFU

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

static void build_packet(uint8_t pkt[PACKET_LEN], const otExtAddress *eui,
			 const struct gos_sensor_data *d)
{
	bool climate = d->valid & GOS_VALID_CLIMATE;
	uint64_t id = 0;

	for (size_t i = 0; i < sizeof(eui->m8); i++) {
		id = (id << 8) | eui->m8[i];
	}

	pkt[0] = PACKET_VERSION;
	pkt[1] = CONFIG_GOS_NODE_INDEX;
	sys_put_le64(id, &pkt[2]);
	put_float(climate ? d->temp_mc / 1000.0f : NAN, &pkt[10]);
	put_float(climate ? d->humidity_mpct / 1000.0f : NAN, &pkt[14]);
	sys_put_le16((d->valid & GOS_VALID_LIGHT) ? clamp_u16(d->light_lux) : U16_INVALID, &pkt[18]);
	sys_put_le16((d->valid & GOS_VALID_BATTERY) ? clamp_u16(d->battery_mv) : U16_INVALID, &pkt[20]);
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

	if (ot == NULL) {
		return -ENODEV;
	}

	openthread_mutex_lock();

	if (otThreadGetDeviceRole(ot) < OT_DEVICE_ROLE_CHILD) {
		ret = -ENOTCONN;
		goto out;
	}

	otLinkGetFactoryAssignedIeeeEui64(ot, &eui);
	build_packet(pkt, &eui, d);

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
