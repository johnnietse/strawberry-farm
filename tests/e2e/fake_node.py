"""Stands in for a sensor node: sends signed PACKET_V5 CoAP POSTs (rev 3.2, with a PAR reading) (same layout as the
firmware) to the receiver, waits for the reply and checks the LED command in it."""
import json
import os
import socket
import struct
import sys
import time

sys.path.insert(0, "/app/services")
import coap_receiver as rx  # noqa: E402

key = bytes.fromhex(json.load(open("/run/gos/node_keys.json"))["nodes"]["7"]["key"])
host = os.getenv("RX_HOST", "coap_receiver_e2e")
addr = socket.getaddrinfo(host, 5683, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)
epoch = int(time.time()) & 0xFFFF
eui = 0xF4CE360011223344
ok = 0
n = int(os.getenv("PACKETS", "12"))
for seq in range(n):
    counter = (epoch << 16) | seq
    temp, rh = 22.0 + 0.1 * seq, 68.0
    par = 450 + 10 * seq                    # quantum sensor on J6, umol m-2 s-1
    body = struct.pack("<BBQffHHHIB", 5, 7, eui, temp, rh, 8000, par, 3900, counter, 0x80)
    pkt = rx.sign_packet(body, key)
    token = os.urandom(4)
    req = bytes([(1 << 6) | (rx.TYPE_NON << 4) | len(token), rx.CODE_POST]) + struct.pack(">H", seq) + token
    req += bytes([(rx.OPTION_URI_PATH << 4) | 9]) + b"telemetry" + b"\xff" + pkt
    sock.sendto(req, addr)
    try:
        data, _ = sock.recvfrom(256)
        msg = rx.parse_coap(data)
        assert msg.token == token and msg.code == rx.CODE_CHANGED
        blue, red = rx.parse_led_command(key, msg.payload, counter)
        ok += 1
        print(f"packet {seq}: reply 2.04, LED command verified: blue {blue} %, red {red} %", flush=True)
    except Exception as e:
        print(f"packet {seq}: {type(e).__name__}: {e}", flush=True)
    time.sleep(float(os.getenv("PERIOD_S", "10")))
print(f"RESULT {ok}/{n} replies with a valid LED command", flush=True)
