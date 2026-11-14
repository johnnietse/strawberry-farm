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
    assert r == {
        "node_id": "RF-NODE-07", "node_index": 7, "sample_identity": "EUI64:F4CE360011223344",
        "temp_c": -1.25, "humidity_pct": 55.5, "light_lux": 65534, "battery_mv": 3712,
    }


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
