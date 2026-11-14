"""
Provision a G.O.S. sensor node signing key.

    python tools/provision_node.py --index 7
    python tools/provision_node.py --index 7 --eui64 F4CE360011223344   # pin the chip after first boot
    python tools/provision_node.py --index 7 --rotate                    # new key (reflash the node)

Writes the node's key to the gateway key file (default secrets/node_keys.json,
git-ignored) and prints the matching firmware credentials.conf. Put that text
in pcbs/gos_sensor_node/firmware/credentials.conf, build and flash that node,
and keep a copy only where the gateway can read it.

The node prints its EUI-64 on the debug console at boot. Registering it with
--eui64 makes the gateway reject packets for this index from any other chip.
"""
import argparse
import json
import os
import re
import secrets
import sys

DEFAULT_KEYS = os.path.join(os.path.dirname(__file__), "..", "secrets", "node_keys.json")
NETWORK_KEY_PLACEHOLDER = "REPLACE_WITH_THREAD_NETWORK_KEY"


def load(path):
    if not os.path.exists(path):
        return {"nodes": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def credentials_conf(index, key_hex, network_key):
    return (f'# credentials.conf for node {index}. Keep out of git.\n'
            f'CONFIG_OPENTHREAD_NETWORKKEY="{network_key}"\n'
            f'CONFIG_GOS_NODE_INDEX={index}\n'
            f'CONFIG_GOS_UPLINK_KEY="{key_hex}"\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description="Provision a sensor node signing key.")
    ap.add_argument("--index", type=int, required=True, help="node index, 1 to 40")
    ap.add_argument("--keys", default=DEFAULT_KEYS, help="gateway key file")
    ap.add_argument("--eui64", help="register the node's EUI-64 (16 hex digits)")
    ap.add_argument("--rotate", action="store_true", help="replace an existing key")
    ap.add_argument("--network-key", default=NETWORK_KEY_PLACEHOLDER,
                    help='Thread network key, "aa:bb:..." (16 bytes)')
    args = ap.parse_args(argv)

    if not 1 <= args.index <= 40:
        ap.error("--index must be 1 to 40")
    eui = args.eui64.upper() if args.eui64 else None
    if eui and not re.fullmatch(r"[0-9A-F]{16}", eui):
        ap.error("--eui64 must be 16 hex digits")

    data = load(args.keys)
    entry = data["nodes"].get(str(args.index))
    if entry and not args.rotate and not eui:
        ap.error(f"node {args.index} already has a key; use --rotate for a new one or --eui64 to pin it")
    if entry is None or args.rotate:
        entry = {"key": secrets.token_hex(16)}
    if eui:
        entry["eui64"] = eui
    data["nodes"][str(args.index)] = entry
    save(args.keys, data)

    print(f"Registered node {args.index} in {args.keys}", file=sys.stderr)
    sys.stdout.write(credentials_conf(args.index, entry["key"], args.network_key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
