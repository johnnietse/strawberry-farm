"""
G.O.S. CoAP Receiver
====================
Receives PACKET_V2 research packets that sensor nodes send over Thread and
stores them in raw_telemetry.

Nodes send a CoAP POST to /telemetry on UDP 5683, by default to the
realm-local all-nodes multicast address ff03::1. Run this on the Thread
border router host (network_mode: host) so it can see the Thread interface.

Packet (documentation/hardware_protocol.md, firmware src/uplink.c), 22 bytes,
little-endian: version u8 (=2), node index u8, EUI-64 u64, temperature f32 degC,
humidity f32 %RH, light u16 lux, battery u16 mV. NaN / 0xFFFF = failed reading.

Environment:
  DATABASE_URL          postgresql://... (required unless --dry-run)
  COAP_PORT             default 5683
  COAP_URI_PATH         default "telemetry"
  COAP_MULTICAST_GROUP  default "ff03::1"; empty string to skip joining
  COAP_INTERFACE        interface to join the group on, default "wpan0"
"""

import argparse
import asyncio
import json
import logging
import math
import os
import socket
import struct
from dataclasses import dataclass
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [COAP-RX] %(message)s")
logger = logging.getLogger("CoapReceiver")

PACKET_FORMAT = "<BBQffHH"
PACKET_LEN = struct.calcsize(PACKET_FORMAT)  # 22
PACKET_VERSION = 2
U16_INVALID = 0xFFFF

# CoAP (RFC 7252)
COAP_VERSION = 1
TYPE_CON, TYPE_NON, TYPE_ACK, TYPE_RST = 0, 1, 2, 3
CODE_POST = 0x02            # 0.02
CODE_CHANGED = 0x44         # 2.04
CODE_BAD_REQUEST = 0x80     # 4.00
CODE_NOT_FOUND = 0x84       # 4.04
CODE_METHOD_NOT_ALLOWED = 0x85  # 4.05
OPTION_URI_PATH = 11


class CoapError(ValueError):
    pass


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


def build_reply(request: CoapMessage, code: int) -> bytes:
    """Piggybacked ACK for a confirmable request."""
    first = (COAP_VERSION << 6) | (TYPE_ACK << 4) | len(request.token)
    return bytes([first, code]) + struct.pack(">H", request.message_id) + request.token


def decode_packet(payload: bytes) -> dict:
    if len(payload) != PACKET_LEN:
        raise ValueError(f"expected {PACKET_LEN} bytes, got {len(payload)}")
    version, index, eui, temp, hum, lux, batt = struct.unpack(PACKET_FORMAT, payload)
    if version != PACKET_VERSION:
        raise ValueError(f"unsupported packet version {version}")
    return {
        "node_id": f"RF-NODE-{index:02d}",
        "node_index": index,
        "sample_identity": f"EUI64:{eui:016X}",
        "temp_c": None if math.isnan(temp) else round(temp, 3),
        "humidity_pct": None if math.isnan(hum) else round(hum, 3),
        "light_lux": None if lux == U16_INVALID else lux,
        "battery_mv": None if batt == U16_INVALID else batt,
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
                        None,  # the node measures lux, not PAR; see payload.light_lux
                        reading["battery_mv"],
                        json.dumps({"light_lux": reading["light_lux"], "source": source,
                                    "node_index": reading["node_index"], "packet_version": PACKET_VERSION}),
                    ),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise


class CoapReceiver(asyncio.DatagramProtocol):
    def __init__(self, store: Callable[[dict, str], None], uri_path: str = "telemetry"):
        self.store = store
        self.uri_path = uri_path.strip("/")
        self.transport = None
        self.stored = 0
        self.rejected = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        reply = self.handle(data, addr[0])
        if reply is not None and self.transport is not None:
            self.transport.sendto(reply, addr)

    def handle(self, data: bytes, source: str) -> Optional[bytes]:
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

        if msg.uri_path != self.uri_path:
            code = CODE_NOT_FOUND
        elif msg.code != CODE_POST:
            code = CODE_METHOD_NOT_ALLOWED
        else:
            try:
                reading = decode_packet(msg.payload)
            except ValueError as e:
                self.rejected += 1
                logger.warning(f"Bad packet from {source}: {e}")
                code = CODE_BAD_REQUEST
            else:
                try:
                    self.store(reading, source)
                except Exception as e:  # keep receiving if the database is down
                    logger.error(f"Store failed for {reading['node_id']}: {e}")
                    return None  # no ACK, so a confirmable sender retries
                self.stored += 1
                logger.info(f"{reading['node_id']} {reading['sample_identity']}: "
                            f"{reading['temp_c']} C, {reading['humidity_pct']} %RH, "
                            f"{reading['light_lux']} lux, {reading['battery_mv']} mV")
                code = CODE_CHANGED
        return build_reply(msg, code) if confirmable else None


def open_socket(port: int, group: str, interface: str) -> socket.socket:
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("::", port))
    if group:
        ifindex = socket.if_nametoindex(interface)
        mreq = socket.inet_pton(socket.AF_INET6, group) + struct.pack("@I", ifindex)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        logger.info(f"Joined {group} on {interface}")
    sock.setblocking(False)
    return sock


async def run(store, port: int, uri_path: str, group: str, interface: str):
    loop = asyncio.get_running_loop()
    sock = open_socket(port, group, interface)
    await loop.create_datagram_endpoint(lambda: CoapReceiver(store, uri_path), sock=sock)
    logger.info(f"Listening for CoAP POST /{uri_path.strip('/')} on UDP {port}")
    await asyncio.Event().wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true", help="log packets, do not touch the database")
    args = parser.parse_args()

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
    ))


if __name__ == "__main__":
    main()
