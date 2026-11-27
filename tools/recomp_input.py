"""Small PSXRecomp debug-server input/screenshot helper (one command per socket)."""
import argparse
import json
import math
import socket
import time

BUTTONS = {
    "select": 0x0001, "l3": 0x0002, "r3": 0x0004, "start": 0x0008,
    "up": 0x0010, "right": 0x0020, "down": 0x0040, "left": 0x0080,
    "l2": 0x0100, "r2": 0x0200, "l1": 0x0400, "r1": 0x0800,
    "triangle": 0x1000, "circle": 0x2000, "cross": 0x4000, "square": 0x8000,
}
NEUTRAL = 0xFFFF
DEFAULT_PORT = 4371


class DebugRequestError(RuntimeError):
    pass


def cmd(obj, port=DEFAULT_PORT, timeout=15):
    command = obj["cmd"]
    if command == "xlate" and "op" in obj:
        raise ValueError("xlate expects 'sub', such as sub='reload'")

    data = bytearray()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as connection:
            connection.sendall((json.dumps(obj) + "\n").encode())
            while b"\n" not in data:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                data.extend(chunk)
    except OSError as exc:
        raise OSError(f"{command} on port {port}: {exc}") from exc

    line = bytes(data).split(b"\n", 1)[0]
    if not line:
        raise OSError(f"{command} on port {port}: debug server closed without a response")
    try:
        response = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DebugRequestError(f"{command} on port {port}: invalid JSON response") from exc
    if not isinstance(response, dict):
        raise DebugRequestError(f"{command} on port {port}: expected a JSON object")
    return response


def checked_cmd(obj, port=DEFAULT_PORT):
    response = cmd(obj, port)
    if response.get("ok") is not True:
        reason = response.get("error") or response.get("err") or response
        raise DebugRequestError(f"{obj['cmd']} on port {port}: {reason}")
    return response


def press(name, hold=0.4, port=DEFAULT_PORT):
    if not math.isfinite(hold) or hold < 0:
        raise ValueError("button hold must be a finite nonnegative number")
    checked_cmd({"id": 1, "cmd": "set_input", "buttons": NEUTRAL & ~BUTTONS[name]}, port)
    try:
        time.sleep(hold)
    finally:
        checked_cmd({"id": 2, "cmd": "clear_input"}, port)
    time.sleep(0.3)


def shot(path, port=DEFAULT_PORT):
    return checked_cmd({"id": 3, "cmd": "screenshot_file", "path": path}, port)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--press", action="append", default=[], help="button[:hold]")
    ap.add_argument("--shot", default="")
    ap.add_argument("--wait", type=float, default=0)
    args = ap.parse_args()
    if args.wait:
        time.sleep(args.wait)
    try:
        for p in args.press:
            name, _, hold = p.partition(":")
            if name not in BUTTONS:
                ap.error(f"unknown button {name!r}")
            print("press", name)
            press(name, float(hold) if hold else 0.4, args.port)
        if args.shot:
            print(shot(args.shot, args.port))
    except (DebugRequestError, OSError, ValueError) as exc:
        ap.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
