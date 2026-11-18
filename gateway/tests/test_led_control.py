"""LED downlink: command format, safety monitor, and the receiver's reply. Run from gateway/:
python -m pytest tests"""
import os
import struct
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
import assistant  # noqa: E402
import coap_receiver as rx  # noqa: E402
from led_safety import LedSafetyConfig, LedSafetyMonitor  # noqa: E402

from test_coap_receiver import FIRMWARE_V3_BODY, FIRMWARE_V4_BODY, KEY, coap, keys, signed  # noqa: E402

V4_COUNTER = 0x00050003          # counter inside FIRMWARE_V4_BODY
NOON = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 11, 15, 23, 30, tzinfo=timezone.utc)

# Same bytes as pcbs/gos_sensor_node/firmware/tests/host/test_downlink.c (key 00 01 .. 0f)
VECTOR_KEY = bytes(range(16))
VECTOR_CMD = bytes.fromhex("c11e4603000500b164775eb9c072c59ceccd347072416e")


def test_command_matches_firmware_test_vector():
    assert rx.build_led_command(VECTOR_KEY, V4_COUNTER, 30, 70) == VECTOR_CMD
    assert len(VECTOR_CMD) == rx.LED_CMD_LEN == 23


def test_command_round_trip_and_tamper_checks():
    cmd = rx.build_led_command(KEY, 1234, 40, 60)
    assert rx.parse_led_command(KEY, cmd, 1234) == (40, 60)
    with pytest.raises(rx.AuthError):        # level changed in transit
        rx.parse_led_command(KEY, cmd[:1] + bytes([100]) + cmd[2:], 1234)
    with pytest.raises(rx.AuthError):        # answers another packet (replay)
        rx.parse_led_command(KEY, cmd, 1235)
    with pytest.raises(rx.AuthError):        # another node's key
        rx.parse_led_command(bytes(16), cmd, 1234)
    with pytest.raises(ValueError):
        rx.build_led_command(KEY, 1, 101, 0)


# --- safety monitor ---------------------------------------------------------

def monitor(**kw):
    return LedSafetyMonitor(LedSafetyConfig(tz="UTC", **kw))


def test_safety_passes_normal_request_within_ramp():
    m = monitor()
    d = m.check("n", (20, 25), 24.0, NOON)
    assert (d.blue, d.red) == (20, 25) and not d.notes


def test_safety_ramp_limits_increase_but_not_decrease():
    m = monitor(max_step_pct=25)
    steps = [m.check("n", (100, 100), 24.0, NOON) for _ in range(5)]
    assert [(s.blue, s.red) for s in steps] == [(25, 25), (50, 50), (75, 75), (100, 100), (100, 100)]
    d = m.check("n", (0, 0), 24.0, NOON)     # switching off is immediate
    assert (d.blue, d.red) == (0, 0)


def test_safety_dark_period_and_over_temperature():
    m = monitor(max_step_pct=100)
    assert (m.check("n", (80, 80), 24.0, NIGHT).blue, m.last["n"]) == (0, (0.0, 0.0))
    d = m.check("n", (80, 80), 33.0, NOON)
    assert (d.blue, d.red) == (0, 0) and "above" in d.notes[0]


def test_safety_unknown_temperature_caps_level():
    d = monitor(max_step_pct=100).check("n", (90, 30), None, NOON)
    assert (d.blue, d.red) == (50, 30)


def test_safety_no_setpoint_uses_fallback_and_clamps():
    m = monitor(fallback=(10, 20), max_step_pct=100)
    d = m.check("n", None, 24.0, NOON)
    assert (d.blue, d.red) == (10, 20) and "fallback" in d.notes[0]
    d = m.check("n2", (150, -5), 24.0, NOON)
    assert (d.blue, d.red) == (100, 0) and "clamped" in d.notes[0]


def test_dark_period_that_does_not_cross_midnight():
    m = monitor(dark_start_h=1, dark_end_h=5, max_step_pct=100)
    assert m.check("n", (50, 50), 20.0, datetime(2026, 1, 1, 3, tzinfo=timezone.utc)).blue == 0
    assert m.check("n", (50, 50), 20.0, datetime(2026, 1, 1, 6, tzinfo=timezone.utc)).blue == 50


# --- receiver reply ---------------------------------------------------------

class LedStore:
    def __init__(self, setpoint=(30, 70), fail_lookup=False):
        self.rows, self.logged, self.setpoint, self.fail_lookup = [], [], setpoint, fail_lookup

    def __call__(self, reading, source):
        self.rows.append(reading)

    def led_setpoint(self, node_id):
        if self.fail_lookup:
            raise RuntimeError("database down")
        return self.setpoint

    def log_led_command(self, node_id, decision, counter):
        self.logged.append((node_id, decision.blue, decision.red, counter, decision.notes))


def receiver(store, when=NOON):
    return rx.CoapReceiver(store, keys=keys(), safety=LedSafetyMonitor(LedSafetyConfig(tz="UTC", max_step_pct=100)),
                           wallclock=lambda: when)


def payload_of(reply):
    msg = rx.parse_coap(reply)
    return msg, msg.payload


def test_non_v4_packet_gets_signed_led_command_in_non_response():
    store = LedStore((30, 70))
    reply = receiver(store).handle(coap(signed(body=FIRMWARE_V4_BODY), mtype=rx.TYPE_NON, token=b"\xab\xcd"), "fe80::1")
    msg, payload = payload_of(reply)
    assert msg.mtype == rx.TYPE_NON and msg.code == rx.CODE_CHANGED and msg.token == b"\xab\xcd"
    assert rx.parse_led_command(KEY, payload, V4_COUNTER) == (30, 70)
    assert store.logged == [("RF-NODE-07", 30, 70, V4_COUNTER, [])]


def test_confirmable_v4_packet_gets_command_in_piggybacked_ack():
    reply = receiver(LedStore((10, 0))).handle(coap(signed(body=FIRMWARE_V4_BODY), mtype=rx.TYPE_CON, mid=77), "x")
    msg, payload = payload_of(reply)
    assert msg.mtype == rx.TYPE_ACK and msg.message_id == 77
    assert rx.parse_led_command(KEY, payload, V4_COUNTER) == (10, 0)


def test_safety_applies_to_the_sent_command():
    store = LedStore((90, 90))
    _, payload = payload_of(receiver(store, NIGHT).handle(coap(signed(body=FIRMWARE_V4_BODY)), "x"))
    assert rx.parse_led_command(KEY, payload, V4_COUNTER) == (0, 0)
    assert "dark period" in store.logged[0][4][0]


def test_database_failure_still_sends_safe_fallback():
    store = LedStore(fail_lookup=True)
    _, payload = payload_of(receiver(store).handle(coap(signed(body=FIRMWARE_V4_BODY)), "x"))
    assert rx.parse_led_command(KEY, payload, V4_COUNTER) == (0, 0)


def test_v3_nodes_and_bench_mode_get_no_command():
    assert receiver(LedStore()).handle(coap(signed(body=FIRMWARE_V3_BODY), mtype=rx.TYPE_NON), "x") is None
    bench = rx.CoapReceiver(LedStore(), keys=None)
    assert bench.handle(coap(signed(body=FIRMWARE_V4_BODY), mtype=rx.TYPE_NON), "x") is None


def test_duplicate_packet_gets_the_same_command_and_is_logged_once():
    store = LedStore((30, 70))
    r = receiver(store)
    pkt = coap(signed(body=FIRMWARE_V4_BODY), mid=5)
    first, second = r.handle(pkt, "x", 1), r.handle(pkt, "x", 1)
    assert first == second and len(store.logged) == 1 and len(store.rows) == 1


# --- research assistant (rules backend; the LLM backends are checked by hand) ----

@pytest.mark.parametrize("note, event_type, sector", [
    ("Aphids on the young leaves in row 3, spreading fast", "PEST", "row 3"),
    ("LED driver on bench 2 is dead, no light since this morning", "EQUIPMENT_FAIL", "bench 2"),
    ("Added calcium nitrate, EC now 1.8 in sector B", "FERTILIZER", "sector B"),
    ("Picked 1.2 kg from row 5, brix 9", "HARVEST", "row 5"),
    ("grey mould on fruit in row 1", "DISEASE", "row 1"),
    ("Plants look fine today", "OBSERVATION", "unknown"),
])
def test_assistant_rules(note, event_type, sector, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    event, backend = assistant.parse_note(note)
    assert backend == "rules" and event["event_type"] == event_type and event["sector"] == sector


def test_assistant_falls_back_to_rules_when_llm_unreachable(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")   # nothing listens there
    monkeypatch.setenv("OLLAMA_TIMEOUT_S", "2")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    event, backend = assistant.parse_note("thrips on bench 4")
    assert backend == "rules" and event["event_type"] == "PEST"


def test_assistant_rejects_invalid_model_output():
    with pytest.raises(ValueError):
        assistant.validate({"event_type": "PARTY", "severity": 3})
    with pytest.raises(ValueError):
        assistant.validate({"event_type": "PEST", "severity": 9})
