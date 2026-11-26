"""Small PSXRecomp debug-server input/screenshot helper (one command per socket)."""
import argparse
import json
import socket
import time

BUTTONS = {
    "select": 0x0001, "l3": 0x0002, "r3": 0x0004, "start": 0x0008,
    "up": 0x0010, "right": 0x0020, "down": 0x0040, "left": 0x0080,
    "l2": 0x0100, "r2": 0x0200, "l1": 0x0400, "r1": 0x0800,
    "triangle": 0x1000, "circle": 0x2000, "cross": 0x4000, "square": 0x8000,
}
NEUTRAL = 0xFFFF


def cmd(obj, port=4370, timeout=15):
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((json.dumps(obj) + "\n").encode())
    data = bytearray()
    while b"\n" not in data:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    line = bytes(data).split(b"\n", 1)[0]
    return json.loads(line)


def press(name, hold=0.4, port=4370):
    cmd({"id": 1, "cmd": "set_input", "buttons": NEUTRAL & ~BUTTONS[name]}, port)
    try:
        time.sleep(hold)
    finally:
        cmd({"id": 2, "cmd": "clear_input"}, port)
    time.sleep(0.3)


def shot(path, port=4370):
    return cmd({"id": 3, "cmd": "screenshot_file", "path": path}, port)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4370)
    ap.add_argument("--press", action="append", default=[], help="button[:hold]")
    ap.add_argument("--shot", default="")
    ap.add_argument("--wait", type=float, default=0)
    args = ap.parse_args()
    if args.wait:
        time.sleep(args.wait)
    for p in args.press:
        name, _, hold = p.partition(":")
        print("press", name)
        press(name, float(hold) if hold else 0.4, args.port)
    if args.shot:
        print(shot(args.shot, args.port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
