"""Tests for services/coap_receiver.py. Run from gateway/: python -m pytest tests"""
import asyncio
import os
import socket
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
import coap_receiver as rx  # noqa: E402

# Bytes produced by the node firmware's packet encoder (src/uplink.c), compiled
# on a PC: node 7, EUI-64 F4CE360011223344, -1.25 C, 55.5 %RH, light clamped
# to 65534, 3712 mV; then the same node with every reading failed.
FIRMWARE_GOOD = bytes.fromhex("0207443322110036cef40000a0bf00005e42feff800e")
FIRMWARE_FAILED = bytes.fromhex("0207443322110036cef40000c07f0000c07fffffffff")


def coap(payload=b"", path="telemetry", mtype=rx.TYPE_NON, code=rx.CODE_POST, token=b"\x12\x34", mid=0xBEEF):
    """Build a request the way OpenThread lays it out: header, token, Uri-Path, 0xFF, payload."""
    out = bytes([(1 << 6) | (mtype << 4) | len(token), code]) + struct.pack(">H", mid) + token
    option = 0
    for segment in filter(None, path.split("/")):
        value = segment.encode()
        delta = rx.OPTION_URI_PATH - option
        assert delta < 13 and len(value) < 13
        out += bytes([(delta << 4) | len(value)]) + value
        option = rx.OPTION_URI_PATH
    return out + (b"\xff" + payload if payload else b"")


class Recorder:
    def __init__(self, fail=False):
        self.rows, self.fail = [], fail

    def __call__(self, reading, source):
        if self.fail:
            raise RuntimeError("database down")
        self.rows.append((reading, source))


def test_decodes_firmware_packet():
    r = rx.decode_packet(FIRMWARE_GOOD)
    assert {k: r[k] for k in ("node_id", "node_index", "sample_identity", "temp_c", "humidity_pct",
                              "light_lux", "battery_mv", "authenticated")} == {
        "node_id": "RF-NODE-07", "node_index": 7, "sample_identity": "EUI64:F4CE360011223344",
        "temp_c": -1.25, "humidity_pct": 55.5, "light_lux": 65534, "battery_mv": 3712,
        "authenticated": False,
    }


# Body produced by the firmware's signed-packet builder (src/uplink.c,
# gos_uplink_build_body) compiled on a PC: same reading, counter epoch 5,
# sequence 3. The tag is added here with the reference signer.
FIRMWARE_V3_BODY = bytes.fromhex("0307443322110036cef40000a0bf00005e42feff800e03000500")
# PACKET_V4 bodies from the current src/uplink.c compiled on a PC the same way: the same
# reading taken while charging on USB power (flags 0x83), and with the charger unread (0x00).
FIRMWARE_V4_BODY = bytes.fromhex("0407443322110036cef40000a0bf00005e42feff800e0300050083")
FIRMWARE_V4_NO_CHARGER = bytes.fromhex("0407443322110036cef40000a0bf00005e42feff800e0300050000")
KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
EUI = "F4CE360011223344"


def keys(**kwargs):
    entry = {"key": KEY.hex(), **kwargs}
    return rx.NodeKeys({"7": entry})


def signed(counter=None, body=FIRMWARE_V3_BODY, key=KEY):
    if counter is not None:
        body = body[:22] + struct.pack("<I", counter) + body[26:]
    return rx.sign_packet(body, key)


def flip(payload, i):
    """Change one bit of byte i."""
    return payload[:i] + bytes([payload[i] ^ 1]) + payload[i + 1:]


class CountingStore(Recorder):
    def __init__(self, last=None):
        super().__init__()
        self.last = last

    def last_counter(self, node_id):
        return self.last


def test_signed_packet_from_firmware_body_is_accepted():
    r = rx.decode_packet(signed(), keys(eui64=EUI))
    assert r["authenticated"] and r["counter"] == (5 << 16) | 3 and r["battery_mv"] == 3712
    assert len(signed()) == rx.V3_LEN == 42


def test_signed_v4_packet_carries_charger_flags():
    r = rx.decode_packet(signed(body=FIRMWARE_V4_BODY), keys(eui64=EUI))
    assert len(signed(body=FIRMWARE_V4_BODY)) == rx.V4_LEN == 43
    assert r["authenticated"] and r["packet_version"] == 4 and r["counter"] == (5 << 16) | 3
    assert r["usb_power"] is True and r["charging"] is True and r["temp_c"] == -1.25


def test_v4_without_charger_state_reports_unknown():
    r = rx.decode_packet(signed(body=FIRMWARE_V4_NO_CHARGER), keys())
    assert r["usb_power"] is None and r["charging"] is None


def test_v3_packet_has_no_charger_state():
    r = rx.decode_packet(signed(), keys())
    assert r["usb_power"] is None and r["charging"] is None


@pytest.mark.parametrize("i", [12, 26, 42])   # reading, flags byte, tag
def test_v4_any_altered_byte_fails_signature(i):
    with pytest.raises(rx.AuthError, match="bad signature"):
        rx.decode_packet(flip(signed(body=FIRMWARE_V4_BODY), i), keys())


def test_v4_charger_flags_are_stored():
    store = CountingStore()
    r = rx.CoapReceiver(store, keys=keys())
    r.handle(coap(signed(body=FIRMWARE_V4_BODY), mtype=rx.TYPE_NON, mid=9), "x")
    assert store.rows[0][0]["charging"] is True


@pytest.mark.parametrize("payload, keyset, why", [
    (signed(key=bytes(16)), None, "bad signature"),                 # wrong key
    (flip(signed(), 41), None, "bad signature"),                    # tag altered
    (flip(signed(), 12), None, "bad signature"),                    # reading altered
    (signed(), rx.NodeKeys({"8": {"key": KEY.hex()}}), "has no key"),  # unregistered node
    (signed(), "pinned", "is not the registered"),                    # EUI-64 mismatch
    (FIRMWARE_GOOD, None, "unsigned"),                               # v2 with keys configured
])
def test_unauthenticated_packets_are_rejected(payload, keyset, why):
    if keyset is None:
        keyset = keys()
    elif keyset == "pinned":
        keyset = keys(eui64="0000000000000001")
    with pytest.raises(rx.AuthError, match=why):
        rx.decode_packet(payload, keyset)


def test_receiver_stores_signed_and_answers_unauthorized():
    store = CountingStore()
    r = rx.CoapReceiver(store, keys=keys())
    assert r.handle(coap(signed(), mtype=rx.TYPE_CON, mid=1), "x")[1] == rx.CODE_CHANGED
    assert r.handle(coap(signed(key=bytes(16), counter=999999), mtype=rx.TYPE_CON, mid=2), "x")[1] == rx.CODE_UNAUTHORIZED
    assert r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON, mid=3), "x")[1] == rx.CODE_UNAUTHORIZED
    assert len(store.rows) == 1 and store.rows[0][0]["authenticated"] and r.unauthorized == 2


def test_replayed_or_old_counter_is_rejected():
    store = CountingStore()
    r = rx.CoapReceiver(store, keys=keys())
    r.handle(coap(signed(counter=10), mid=1), "x")
    r.handle(coap(signed(counter=10), mid=2), "x")   # exact replay, new CoAP message ID
    r.handle(coap(signed(counter=9), mid=3), "x")    # older
    r.handle(coap(signed(counter=11), mid=4), "x")   # next one: fine
    assert [row[0]["counter"] for row in store.rows] == [10, 11] and r.unauthorized == 2


def test_counter_survives_receiver_restart_via_store():
    store = CountingStore(last=500)  # database already holds counter 500 for this node
    r = rx.CoapReceiver(store, keys=keys())
    r.handle(coap(signed(counter=500), mid=1), "x")
    r.handle(coap(signed(counter=501), mid=2), "x")
    assert [row[0]["counter"] for row in store.rows] == [501]


def test_failed_store_does_not_advance_counter():
    store = CountingStore()
    store.fail = True
    r = rx.CoapReceiver(store, keys=keys())
    r.handle(coap(signed(counter=20), mid=1), "x")
    store.fail = False
    r.handle(coap(signed(counter=20), mid=2), "x")  # same packet retried after the outage
    assert [row[0]["counter"] for row in store.rows] == [20]


def test_failed_readings_become_null():
    r = rx.decode_packet(FIRMWARE_FAILED)
    assert (r["temp_c"], r["humidity_pct"], r["light_lux"], r["battery_mv"]) == (None, None, None, None)
    assert r["sample_identity"] == "EUI64:F4CE360011223344"


@pytest.mark.parametrize("payload", [FIRMWARE_GOOD[:-1], FIRMWARE_GOOD + b"\0", b"\x03" + FIRMWARE_GOOD[1:]])
def test_rejects_wrong_length_or_version(payload):
    with pytest.raises(ValueError):
        rx.decode_packet(payload)


def test_parses_openthread_style_request():
    msg = rx.parse_coap(coap(FIRMWARE_GOOD))
    assert (msg.mtype, msg.code, msg.message_id, msg.token, msg.uri_path, msg.payload) == \
        (rx.TYPE_NON, rx.CODE_POST, 0xBEEF, b"\x12\x34", "telemetry", FIRMWARE_GOOD)


def test_parses_extended_option_length():
    long_segment = "x" * 20  # needs the 13 + 1-byte extended length form
    data = bytes([0x52, rx.CODE_POST, 0, 1, 0xAA, 0xBB, 0xBD, 20 - 13]) + long_segment.encode() + b"\xff\x01"
    msg = rx.parse_coap(data)
    assert msg.uri_path == long_segment and msg.payload == b"\x01"


@pytest.mark.parametrize("data", [b"\x50\x02", b"\x90\x02\x00\x01", b"\x59\x02\x00\x01", coap() + b"\xff"])
def test_rejects_malformed_coap(data):
    with pytest.raises(rx.CoapError):
        rx.parse_coap(data)


def test_non_confirmable_post_is_stored_without_reply():
    store = Recorder()
    r = rx.CoapReceiver(store)
    assert r.handle(coap(FIRMWARE_GOOD), "fd00::7") is None
    assert len(store.rows) == 1 and store.rows[0][1] == "fd00::7"
    assert store.rows[0][0]["node_id"] == "RF-NODE-07"


def test_confirmable_post_gets_changed_ack():
    r = rx.CoapReceiver(Recorder())
    reply = r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON), "fd00::7")
    assert reply == bytes([0x62, rx.CODE_CHANGED, 0xBE, 0xEF, 0x12, 0x34])


@pytest.mark.parametrize("kwargs, code", [
    ({"path": "other"}, rx.CODE_NOT_FOUND),
    ({"code": 0x01}, rx.CODE_METHOD_NOT_ALLOWED),
    ({"payload": b"short"}, rx.CODE_BAD_REQUEST),
])
def test_bad_requests_are_answered_and_not_stored(kwargs, code):
    store = Recorder()
    reply = rx.CoapReceiver(store).handle(coap(**{"payload": FIRMWARE_GOOD, **kwargs}, mtype=rx.TYPE_CON), "x")
    assert reply[1] == code and store.rows == []


def test_database_failure_does_not_ack_or_crash():
    r = rx.CoapReceiver(Recorder(fail=True))
    assert r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON), "x") is None
    assert r.stored == 0


def test_duplicate_message_id_is_stored_once():
    store = Recorder()
    r = rx.CoapReceiver(store)
    r.handle(coap(FIRMWARE_GOOD, mid=5), "fd00::7")
    r.handle(coap(FIRMWARE_GOOD, mid=5), "fd00::7")
    r.handle(coap(FIRMWARE_GOOD, mid=5), "fd00::9")  # same ID, other node: new
    r.handle(coap(FIRMWARE_GOOD, mid=6), "fd00::7")  # next message: new
    assert len(store.rows) == 3 and r.duplicates == 1


def test_duplicate_confirmable_gets_same_ack_again():
    r = rx.CoapReceiver(Recorder())
    first = r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON, mid=9), "x")
    again = r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON, mid=9), "x")
    assert first == again and r.stored == 1


def test_same_message_id_with_different_content_is_not_a_duplicate():
    """A spoofed packet reusing a node's message ID must not suppress the real one."""
    store = Recorder()
    r = rx.CoapReceiver(store)
    r.handle(coap(FIRMWARE_FAILED, mid=5, token=bytes([0xDE, 0xAD])), "fd00::7", 5683)  # spoof first
    r.handle(coap(FIRMWARE_GOOD, mid=5), "fd00::7", 5683)                       # real packet
    assert len(store.rows) == 2 and store.rows[1][0]["battery_mv"] == 3712


def test_rejected_packet_is_not_remembered():
    store = Recorder()
    r = rx.CoapReceiver(store)
    r.handle(coap(b"short", mid=5, token=b""), "fd00::7")
    r.handle(coap(b"short", mid=5, token=b""), "fd00::7")
    assert r.duplicates == 0 and r.rejected == 2


def test_duplicate_window_expires():
    now = [0.0]
    store = Recorder()
    r = rx.CoapReceiver(store, clock=lambda: now[0])
    r.handle(coap(FIRMWARE_GOOD, mid=5), "x")
    now[0] = rx.DEDUP_SECONDS + 1
    r.handle(coap(FIRMWARE_GOOD, mid=5), "x")  # message IDs wrap; old entry forgotten
    assert len(store.rows) == 2


def test_retry_after_database_failure_is_stored():
    store = Recorder(fail=True)
    r = rx.CoapReceiver(store)
    assert r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON, mid=3), "x") is None
    store.fail = False
    assert r.handle(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON, mid=3), "x")[1] == rx.CODE_CHANGED
    assert len(store.rows) == 1


def test_garbage_is_ignored():
    r = rx.CoapReceiver(Recorder())
    assert r.handle(b"\x00", "x") is None and r.rejected == 1


@pytest.mark.skipif(not socket.has_ipv6, reason="no IPv6")
def test_end_to_end_over_udp():
    """Real UDP socket on ::1 (multicast join skipped), confirmable post, ACK back."""
    store = Recorder()

    async def scenario():
        loop = asyncio.get_running_loop()
        sock = rx.open_socket(0, "", "")
        port = sock.getsockname()[1]
        server, _ = await loop.create_datagram_endpoint(lambda: rx.CoapReceiver(store), sock=sock)
        replies = asyncio.Queue()

        class Client(asyncio.DatagramProtocol):
            def datagram_received(self, data, addr):
                replies.put_nowait(data)

        client, _ = await loop.create_datagram_endpoint(Client, remote_addr=("::1", port))
        client.sendto(coap(FIRMWARE_GOOD, mtype=rx.TYPE_CON))
        reply = await asyncio.wait_for(replies.get(), 5)
        client.close()
        server.close()
        return reply

    reply = asyncio.run(scenario())
    assert reply[1] == rx.CODE_CHANGED
    assert store.rows[0][0]["battery_mv"] == 3712


def test_provisioning_tool_round_trip(tmp_path, capsys):
    """Key written by the tool verifies a packet signed with the key it prints for the firmware."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import provision_node

    keyfile = str(tmp_path / "node_keys.json")
    assert provision_node.main(["--index", "7", "--keys", keyfile]) == 0
    conf = capsys.readouterr().out
    key_hex = conf.split('CONFIG_GOS_UPLINK_KEY="')[1].split('"')[0]
    assert "CONFIG_GOS_NODE_INDEX=7" in conf and len(key_hex) == 32

    with pytest.raises(SystemExit):  # refuses to overwrite silently
        provision_node.main(["--index", "7", "--keys", keyfile])
    assert provision_node.main(["--index", "7", "--keys", keyfile, "--eui64", EUI.lower()]) == 0

    registry = rx.NodeKeys.load(keyfile)
    good = rx.decode_packet(signed(key=bytes.fromhex(key_hex)), registry)
    assert good["authenticated"]
    with pytest.raises(rx.AuthError):
        rx.decode_packet(signed(), registry)  # some other key
