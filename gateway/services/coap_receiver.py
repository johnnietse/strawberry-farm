"""
G.O.S. CoAP Receiver
====================
Receives signed PACKET_V5 (and older V4 / V3) research packets that sensor nodes send over Thread,
checks each one against that node's key, and stores it in raw_telemetry.

Nodes send a CoAP POST to /telemetry on UDP 5683, by default to the
realm-local all-nodes multicast address ff03::1. Run this on the Thread
border router host (network_mode: host) so it can see the Thread interface.

PACKET_V5 (rev 3.2 firmware, src/uplink.c): V4 plus PAR u16 (umol m-2 s-1 from the quantum
sensor on J6, 0xFFFF = none) after the light field, 45 bytes: "<BBQffHHHIB16s". The node's PAR
sensor sees the LED board too, so it is stored in par_umol with payload.par_source = "node"
and the biology engine subtracts the LED share. V4 adds a flags byte to V3. V3 packet,
42 bytes,
little-endian: version u8 (=3), node index u8, EUI-64 u64, temperature f32 degC,
humidity f32 %RH, light u16 lux, battery u16 mV, counter u32, then a 16-byte tag
= first 16 bytes of HMAC-SHA256(node key, first 26 bytes). NaN / 0xFFFF =
failed reading.

LED commands (downlink): the reply to each accepted v4 packet carries the LED level for that
node, so a sleepy node gets its command the moment it is awake anyway (no CoAP server on the
node). 23 bytes: 0xC1, blue %, red %, the packet's counter (u32 LE), then the first 16 bytes
of HMAC-SHA256(node key, first 7 bytes). The node applies it only if the tag matches and the
counter is the one it just sent, so a command cannot be forged or replayed. The level is the
newest unexpired row in led_setpoints for the node, after led_safety.LedSafetyMonitor; every
command sent is logged in led_commands. A NON request gets a NON 2.04 response (RFC 7252 8.2,
responses to multicast requests), a CON request a piggybacked ACK.

A packet is stored only if
  - its node index has a key in the key file and the tag matches,
  - its EUI-64 matches the one registered for that index (when registered),
  - its counter is higher than the last one stored for that node (replays
    are rejected; after a restart the last counter is read from the database).

Environment:
  DATABASE_URL          postgresql://... (required unless --dry-run)
  COAP_PORT             default 5683
  COAP_URI_PATH         default "telemetry"
  COAP_MULTICAST_GROUP  default "ff03::1"; empty string to skip joining
  COAP_INTERFACE        Thread interface, default "wpan0". Packets from any
                        other interface are ignored. Empty = listen on all
                        interfaces (local testing only; also needed on
                        Windows, which cannot restrict by interface).
  GOS_NODE_KEYS         key file written by tools/provision_node.py
                        (default /run/gos/node_keys.json). Required.
  GOS_ALLOW_UNSIGNED    "1" accepts unsigned v2 packets and skips all checks.
                        For bench testing only; never on a real deployment.
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import socket
import struct
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

try:
    from led_safety import LedSafetyConfig, LedSafetyMonitor
except ImportError:  # imported as services.coap_receiver (tests)
    from services.led_safety import LedSafetyConfig, LedSafetyMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [COAP-RX] %(message)s")
logger = logging.getLogger("CoapReceiver")

V2_FORMAT = "<BBQffHH"                      # unsigned, bench testing only
V2_LEN = struct.calcsize(V2_FORMAT)          # 22
V3_FORMAT = "<BBQffHHI16s"                   # signed
V3_LEN = struct.calcsize(V3_FORMAT)          # 42
V3_BODY_LEN = V3_LEN - 16                    # bytes covered by the tag (verify uses len - 16)
V4_FORMAT = "<BBQffHHIB16s"                  # signed, adds a flags byte (current firmware)
V4_LEN = struct.calcsize(V4_FORMAT)          # 43
V4_BODY_LEN = V4_LEN - 16
V5_FORMAT = "<BBQffHHHIB16s"                 # signed, adds PAR (rev 3.2 firmware)
V5_LEN = struct.calcsize(V5_FORMAT)          # 45
FLAG_VALID, FLAG_USB, FLAG_CHARGING = 0x80, 0x01, 0x02
LED_CMD_VERSION = 0xC1
LED_CMD_BODY_LEN = 7
LED_CMD_LEN = LED_CMD_BODY_LEN + 16          # 23
TAG_LEN = 16
KEY_LEN = 16
U16_INVALID = 0xFFFF

# CoAP (RFC 7252)
COAP_VERSION = 1
TYPE_CON, TYPE_NON, TYPE_ACK, TYPE_RST = 0, 1, 2, 3
CODE_POST = 0x02            # 0.02
CODE_CHANGED = 0x44         # 2.04
CODE_BAD_REQUEST = 0x80     # 4.00
CODE_UNAUTHORIZED = 0x81    # 4.01
CODE_NOT_FOUND = 0x84       # 4.04
CODE_METHOD_NOT_ALLOWED = 0x85  # 4.05
OPTION_URI_PATH = 11
# RFC 7252 section 4.5: drop a repeated message from the same sender.
# NON_LIFETIME (145 s) covers retransmits and network duplicates. A packet
# counts as a repeat only if source address, port, message ID, token and
# payload all match, so a spoofed packet reusing a node's next message ID
# cannot suppress the real one. Only stored packets are remembered.
DEDUP_SECONDS = 145
DEDUP_MAX_ENTRIES = 4096


class CoapError(ValueError):
    pass


class AuthError(ValueError):
    """Packet failed authentication or replay checks."""


class NodeKeys:
    """Per-node signing keys: {"nodes": {"7": {"key": "<32 hex>", "eui64": "<16 hex>"}}}.
    eui64 is optional; when present the packet's EUI-64 must match it."""

    def __init__(self, nodes: dict):
        self.nodes = {}
        for index, entry in nodes.items():
            key = bytes.fromhex(entry["key"])
            if len(key) != KEY_LEN:
                raise ValueError(f"node {index}: key must be {KEY_LEN} bytes")
            eui = entry.get("eui64")
            self.nodes[int(index)] = (key, eui.upper() if eui else None)

    @classmethod
    def load(cls, path: str) -> "NodeKeys":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f)["nodes"])

    def key(self, index: int) -> Optional[bytes]:
        entry = self.nodes.get(index)
        return entry[0] if entry else None

    def verify(self, payload: bytes, index: int, eui: int, tag: bytes) -> None:
        if index not in self.nodes:
            raise AuthError(f"node {index} has no key")
        key, pinned = self.nodes[index]
        expected = hmac.new(key, payload[:-TAG_LEN], hashlib.sha256).digest()[:TAG_LEN]
        if not hmac.compare_digest(expected, tag):
            raise AuthError(f"node {index}: bad signature")
        if pinned and pinned != f"{eui:016X}":
            raise AuthError(f"node {index}: EUI-64 {eui:016X} is not the registered {pinned}")


def sign_packet(body: bytes, key: bytes) -> bytes:
    """Reference signer (same as the firmware); used by tests and tools."""
    return body + hmac.new(key, body, hashlib.sha256).digest()[:TAG_LEN]


def build_led_command(key: bytes, counter: int, blue_pct: int, red_pct: int) -> bytes:
    """Signed LED command, bound to the uplink counter it answers (firmware src/downlink.c)."""
    if not (0 <= blue_pct <= 100 and 0 <= red_pct <= 100):
        raise ValueError("LED levels must be 0..100")
    body = struct.pack("<BBBI", LED_CMD_VERSION, blue_pct, red_pct, counter & 0xFFFFFFFF)
    return body + hmac.new(key, body, hashlib.sha256).digest()[:TAG_LEN]


def parse_led_command(key: bytes, data: bytes, expected_counter: int) -> tuple:
    """Reference check, the same steps as the firmware. Raises AuthError."""
    if len(data) != LED_CMD_LEN or data[0] != LED_CMD_VERSION:
        raise AuthError("not an LED command")
    body, tag = data[:LED_CMD_BODY_LEN], data[LED_CMD_BODY_LEN:]
    if not hmac.compare_digest(hmac.new(key, body, hashlib.sha256).digest()[:TAG_LEN], tag):
        raise AuthError("bad LED command signature")
    _, blue, red, counter = struct.unpack("<BBBI", body)
    if counter != expected_counter:
        raise AuthError("LED command for another packet")
    if blue > 100 or red > 100:
        raise AuthError("LED level out of range")
    return blue, red


@dataclass
class CoapMessage:
    mtype: int
    code: int
    message_id: int
    token: bytes
    uri_path: str
    payload: bytes


def parse_coap(data: bytes) -> CoapMessage:
    if len(data) < 4:
        raise CoapError("shorter than a CoAP header")
    version = data[0] >> 6
    mtype = (data[0] >> 4) & 0x3
    tkl = data[0] & 0x0F
    if version != COAP_VERSION:
        raise CoapError(f"unsupported CoAP version {version}")
    if tkl > 8:
        raise CoapError("token length over 8")
    code = data[1]
    message_id = struct.unpack_from(">H", data, 2)[0]
    pos = 4 + tkl
    if pos > len(data):
        raise CoapError("truncated token")
    token = data[4:pos]

    path = []
    option = 0
    payload = b""
    while pos < len(data):
        if data[pos] == 0xFF:
            payload = data[pos + 1:]
            if not payload:
                raise CoapError("payload marker with no payload")
            break
        delta, length = data[pos] >> 4, data[pos] & 0x0F
        pos += 1
        values = []
        for nibble in (delta, length):
            if nibble < 13:
                values.append(nibble)
            elif nibble == 13:
                if pos + 1 > len(data):
                    raise CoapError("truncated option")
                values.append(data[pos] + 13)
                pos += 1
            elif nibble == 14:
                if pos + 2 > len(data):
                    raise CoapError("truncated option")
                values.append(struct.unpack_from(">H", data, pos)[0] + 269)
                pos += 2
            else:
                raise CoapError("reserved option nibble 15")
        option += values[0]
        end = pos + values[1]
        if end > len(data):
            raise CoapError("truncated option value")
        if option == OPTION_URI_PATH:
            path.append(data[pos:end].decode("utf-8", errors="replace"))
        pos = end
    return CoapMessage(mtype, code, message_id, token, "/".join(path), payload)


def build_reply(request: CoapMessage, code: int, payload: bytes = b"",
                message_id: Optional[int] = None) -> bytes:
    """Piggybacked ACK for a confirmable request, or (with message_id) a NON response
    to a non-confirmable one. Same token as the request."""
    if message_id is None:
        mtype, mid = TYPE_ACK, request.message_id
    else:
        mtype, mid = TYPE_NON, message_id & 0xFFFF
    first = (COAP_VERSION << 6) | (mtype << 4) | len(request.token)
    out = bytes([first, code]) + struct.pack(">H", mid) + request.token
    return out + (b"\xff" + payload if payload else b"")


def decode_packet(payload: bytes, keys: Optional[NodeKeys] = None) -> dict:
    """Decode a research packet. With keys, only a correctly signed v4 or v3
    packet from a registered node is accepted (raises AuthError otherwise).
    Without keys (bench mode), v2, v3 and v4 are decoded with no checks."""
    version = payload[0] if payload else None
    flags = None
    par = U16_INVALID
    if version == 5 and len(payload) == V5_LEN:
        _, index, eui, temp, hum, lux, par, batt, counter, flags, tag = struct.unpack(V5_FORMAT, payload)
        if keys is not None:
            keys.verify(payload, index, eui, tag)
        authenticated = keys is not None
    elif version == 4 and len(payload) == V4_LEN:
        _, index, eui, temp, hum, lux, batt, counter, flags, tag = struct.unpack(V4_FORMAT, payload)
        if keys is not None:
            keys.verify(payload, index, eui, tag)
        authenticated = keys is not None
    elif version == 3 and len(payload) == V3_LEN:
        _, index, eui, temp, hum, lux, batt, counter, tag = struct.unpack(V3_FORMAT, payload)
        if keys is not None:
            keys.verify(payload, index, eui, tag)
        authenticated = keys is not None
    elif version == 2 and len(payload) == V2_LEN:
        if keys is not None:
            raise AuthError("unsigned v2 packet")
        _, index, eui, temp, hum, lux, batt = struct.unpack(V2_FORMAT, payload)
        counter, authenticated = None, False
    else:
        raise ValueError(f"not a v2 ({V2_LEN} bytes), v3 ({V3_LEN} bytes), v4 ({V4_LEN} bytes) "
                         f"or v5 ({V5_LEN} bytes) "
                         f"packet: version {version}, {len(payload)} bytes")
    known = flags is not None and flags & FLAG_VALID
    return {
        "packet_version": version,
        "counter": counter,
        "authenticated": authenticated,
        "node_id": f"RF-NODE-{index:02d}",
        "node_index": index,
        "sample_identity": f"EUI64:{eui:016X}",
        "temp_c": None if math.isnan(temp) else round(temp, 3),
        "humidity_pct": None if math.isnan(hum) else round(hum, 3),
        "light_lux": None if lux == U16_INVALID else lux,
        "par_umol": None if par == U16_INVALID else par,
        "battery_mv": None if batt == U16_INVALID else batt,
        "usb_power": bool(flags & FLAG_USB) if known else None,
        "charging": bool(flags & FLAG_CHARGING) if known else None,
    }


class PostgresStore:
    """Inserts one reading per packet into raw_telemetry."""

    def __init__(self, db_url: str):
        import psycopg2  # imported here so tests and --dry-run need no driver

        self._connect = lambda: psycopg2.connect(db_url)
        self._conn = None

    def __call__(self, reading: dict, source: str) -> None:
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw_telemetry
                    (node_id, sample_identity, temp_c, humidity_pct, par_umol, battery_mv, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        reading["node_id"],
                        reading["sample_identity"],
                        reading["temp_c"],
                        reading["humidity_pct"],
                        reading.get("par_umol"),  # rev 3.2 quantum sensor, else None (lux only)
                        reading["battery_mv"],
                        json.dumps({"light_lux": reading["light_lux"], "source": source,
                                    # the node's PAR sensor sees the LED board as well as daylight
                                    "par_source": "node" if reading.get("par_umol") is not None else None,
                                    "node_index": reading["node_index"],
                                    "packet_version": reading["packet_version"],
                                    "counter": reading["counter"],
                                    "authenticated": reading["authenticated"],
                                    "usb_power": reading.get("usb_power"),
                                    "charging": reading.get("charging")}),
                    ),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _cursor(self):
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
        return self._conn.cursor()

    def led_setpoint(self, node_id: str) -> Optional[tuple]:
        """Newest unexpired LED setpoint for this node (a node-specific row wins over 'ALL')."""
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT blue_pct, red_pct FROM led_setpoints "
                    "WHERE node_id IN (%s, 'ALL') AND (expires_at IS NULL OR expires_at > NOW()) "
                    "ORDER BY (node_id = %s) DESC, time DESC LIMIT 1",
                    (node_id, node_id),
                )
                row = cur.fetchone()
            self._conn.commit()
        except Exception:
            if self._conn is not None and not self._conn.closed:
                self._conn.rollback()
            raise
        return None if row is None else (float(row[0]), float(row[1]))

    def log_led_command(self, node_id: str, decision, counter: int) -> None:
        try:
            with self._cursor() as cur:
                req = decision.requested
                cur.execute(
                    "INSERT INTO led_commands (node_id, blue_pct, red_pct, requested_blue, requested_red, "
                    "counter, safety_notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (node_id, decision.blue, decision.red, req[0] if req else None, req[1] if req else None,
                     counter, "; ".join(decision.notes) or None),
                )
            self._conn.commit()
        except Exception:
            if self._conn is not None and not self._conn.closed:
                self._conn.rollback()
            raise

    def last_counter(self, node_id: str) -> Optional[int]:
        """Highest authenticated counter stored for this node, or None."""
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT max((payload->>'counter')::bigint) FROM raw_telemetry "
                "WHERE node_id = %s AND payload->>'authenticated' = 'true'",
                (node_id,),
            )
            row = cur.fetchone()
        self._conn.commit()
        return None if row is None or row[0] is None else int(row[0])


class CoapReceiver(asyncio.DatagramProtocol):
    def __init__(self, store: Callable[[dict, str], None], uri_path: str = "telemetry",
                 clock: Callable[[], float] = time.monotonic, keys: Optional[NodeKeys] = None,
                 safety: Optional[LedSafetyMonitor] = None,
                 wallclock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.store = store
        self.safety = safety or LedSafetyMonitor()
        self._wallclock = wallclock
        self._next_mid = int.from_bytes(os.urandom(2), "big")
        self.commands_sent = 0
        self.uri_path = uri_path.strip("/")
        self.keys = keys
        self.transport = None
        self.stored = 0
        self.rejected = 0
        self.unauthorized = 0
        self.duplicates = 0
        self._counters = {}  # node_id -> last accepted counter
        self._clock = clock
        self._seen = OrderedDict()  # (source, port, message id) -> (time, fingerprint, reply)

    def _seen_reply(self, key):
        now = self._clock()
        while self._seen:
            oldest_key, (t, _, _) = next(iter(self._seen.items()))
            if now - t <= DEDUP_SECONDS and len(self._seen) <= DEDUP_MAX_ENTRIES:
                break
            del self._seen[oldest_key]
        return self._seen.get(key)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        reply = self.handle(data, addr[0], addr[1])
        if reply is not None and self.transport is not None:
            self.transport.sendto(reply, addr)

    def handle(self, data: bytes, source: str, port: int = 0) -> Optional[bytes]:
        """Process one datagram. Returns the reply to send, if any."""
        try:
            msg = parse_coap(data)
        except CoapError as e:
            self.rejected += 1
            logger.warning(f"Not CoAP from {source}: {e}")
            return None
        if msg.mtype in (TYPE_ACK, TYPE_RST):
            return None
        confirmable = msg.mtype == TYPE_CON

        key = (source, port, msg.message_id)
        fingerprint = (msg.token, hashlib.sha256(msg.payload).digest())
        seen = self._seen_reply(key)
        if seen is not None and seen[1] == fingerprint:
            self.duplicates += 1
            return seen[2]  # same answer as the first time, nothing stored again

        stored_before = self.stored
        reply = self._handle_new(msg, source, confirmable)
        if self.stored > stored_before:
            self._seen[key] = (self._clock(), fingerprint, reply)
        return reply or None

    def _handle_new(self, msg: CoapMessage, source: str, confirmable: bool):
        """Returns the reply (or None), or False if the store failed and a retry must be accepted."""

        if msg.uri_path != self.uri_path:
            code = CODE_NOT_FOUND
        elif msg.code != CODE_POST:
            code = CODE_METHOD_NOT_ALLOWED
        else:
            try:
                reading = decode_packet(msg.payload, self.keys)
                if reading["authenticated"]:
                    self._check_counter(reading)
            except AuthError as e:
                self.unauthorized += 1
                logger.warning(f"Rejected packet from {source}: {e}")
                code = CODE_UNAUTHORIZED
            except ValueError as e:
                self.rejected += 1
                logger.warning(f"Bad packet from {source}: {e}")
                code = CODE_BAD_REQUEST
            except Exception as e:  # counter lookup failed: database down
                logger.error(f"Counter lookup failed for {source}: {e}")
                return False
            else:
                try:
                    self.store(reading, source)
                except Exception as e:  # keep receiving if the database is down
                    logger.error(f"Store failed for {reading['node_id']}: {e}")
                    return False  # no ACK and not remembered, so a retry is processed
                if reading["authenticated"]:
                    self._counters[reading["node_id"]] = reading["counter"]
                self.stored += 1
                logger.info(f"{reading['node_id']} {reading['sample_identity']}: "
                            f"{reading['temp_c']} C, {reading['humidity_pct']} %RH, "
                            f"{reading['light_lux']} lux, {reading['battery_mv']} mV")
                command = self._led_command(reading)
                if confirmable:
                    return build_reply(msg, CODE_CHANGED, command)
                if command:
                    self._next_mid = (self._next_mid + 1) & 0xFFFF
                    return build_reply(msg, CODE_CHANGED, command, self._next_mid)
                return None
        return build_reply(msg, code) if confirmable else None

    def _led_command(self, reading: dict) -> bytes:
        """Signed LED command for this node after the safety checks, or b"" if none can be
        sent (bench mode without keys, or a v3 node that cannot apply it)."""
        if not reading["authenticated"] or reading["packet_version"] < 4 or self.keys is None:
            return b""
        node = reading["node_id"]
        try:
            lookup = getattr(self.store, "led_setpoint", None)
            requested = lookup(node) if lookup else None
        except Exception as e:  # database down: the safety fallback decides
            logger.error(f"LED setpoint lookup failed for {node}: {e}")
            requested = None
        decision = self.safety.check(node, requested, reading["temp_c"], self._wallclock())
        command = build_led_command(self.keys.key(reading["node_index"]), reading["counter"],
                                    decision.blue, decision.red)
        try:
            log = getattr(self.store, "log_led_command", None)
            if log:
                log(node, decision, reading["counter"])
        except Exception as e:
            logger.error(f"LED command log failed for {node}: {e}")
        self.commands_sent += 1
        logger.info(f"{node}: LED blue {decision.blue} %, red {decision.red} %"
                    + (f" ({'; '.join(decision.notes)})" if decision.notes else ""))
        return command


    def _check_counter(self, reading: dict) -> None:
        node = reading["node_id"]
        if node not in self._counters:
            lookup = getattr(self.store, "last_counter", None)
            self._counters[node] = lookup(node) if lookup else None
        last = self._counters[node]
        if last is not None and reading["counter"] <= last:
            raise AuthError(f"{node}: counter {reading['counter']} not above {last} (replay)")


def open_socket(port: int, group: str, interface: str) -> socket.socket:
    """Open the UDP socket. With an interface name, only packets arriving on
    that interface are accepted (Linux SO_BINDTODEVICE), so hosts on the LAN
    or the internet cannot write rows; only devices on the Thread network can.
    An empty interface listens everywhere and is meant for local testing."""
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if interface:
        if not hasattr(socket, "SO_BINDTODEVICE"):
            raise SystemExit(f"cannot restrict to {interface} on this OS; set COAP_INTERFACE= to listen everywhere")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())
        logger.info(f"Accepting packets from {interface} only")
    else:
        logger.warning("COAP_INTERFACE is empty: accepting packets from every interface")
    sock.bind(("::", port))
    if group:
        ifindex = socket.if_nametoindex(interface)
        mreq = socket.inet_pton(socket.AF_INET6, group) + struct.pack("@I", ifindex)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        logger.info(f"Joined {group} on {interface}")
    sock.setblocking(False)
    return sock


async def run(store, port: int, uri_path: str, group: str, interface: str, keys: Optional[NodeKeys]):
    loop = asyncio.get_running_loop()
    sock = open_socket(port, group, interface)
    safety = LedSafetyMonitor(LedSafetyConfig.from_env())
    await loop.create_datagram_endpoint(lambda: CoapReceiver(store, uri_path, keys=keys, safety=safety), sock=sock)
    logger.info(f"Listening for CoAP POST /{uri_path.strip('/')} on UDP {port}")
    await asyncio.Event().wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true", help="log packets, do not touch the database")
    args = parser.parse_args()

    if os.getenv("GOS_ALLOW_UNSIGNED") == "1":
        keys = None
        logger.warning("GOS_ALLOW_UNSIGNED=1: accepting unsigned packets with no checks (bench testing only)")
    else:
        keys_path = os.getenv("GOS_NODE_KEYS", "/run/gos/node_keys.json")
        try:
            keys = NodeKeys.load(keys_path)
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Cannot load node keys from {keys_path}: {e}")
            raise SystemExit(1)
        logger.info(f"Loaded keys for {len(keys.nodes)} node(s) from {keys_path}")

    if args.dry_run:
        store = lambda reading, source: None  # noqa: E731
    else:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL not set!")
            raise SystemExit(1)
        store = PostgresStore(db_url)

    asyncio.run(run(
        store,
        int(os.getenv("COAP_PORT", "5683")),
        os.getenv("COAP_URI_PATH", "telemetry"),
        os.getenv("COAP_MULTICAST_GROUP", "ff03::1"),
        os.getenv("COAP_INTERFACE", "wpan0"),
        keys,
    ))


if __name__ == "__main__":
    main()
