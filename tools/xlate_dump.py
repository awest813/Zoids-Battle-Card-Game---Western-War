"""Dump the PSXRecomp runtime's captured string inventory over TCP.

Usage:
  python tools/xlate_dump.py --port 4370 --out analysis/runtime_strings.json
"""
import argparse
import json
import socket
import sys


def query(port, cmd, timeout=10.0):
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((json.dumps(cmd) + "\n").encode())
    data = bytearray()
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break
    s.close()
    line = bytes(data).split(b"\n", 1)[0]
    return json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4370)
    ap.add_argument("--out", default="analysis/runtime_strings.json")
    ap.add_argument("--sub", default="dump", choices=["dump", "todo", "stats", "glyph", "vpatch"])
    args = ap.parse_args()

    resp = query(args.port, {"id": 1, "cmd": "xlate", "sub": args.sub})
    if not resp.get("ok"):
        print("error:", resp, file=sys.stderr)
        return 1
    payload = resp.get("xlate")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    n = len(payload) if isinstance(payload, list) else 1
    print(f"wrote {args.out}: {n} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())