"""Dump / probe guest RAM through the recomp debug server.

Usage:
  python tools/ram_probe.py dump --port 4371 --lo 0x800F7000 --hi 0x80200000 --out work/ram_after_boot.bin
  python tools/ram_probe.py write --port 4371 --addr 0x801F0000 --hex deadbeef
  python tools/ram_probe.py read --port 4371 --addr 0x801F0000 --len 16
"""
import argparse
import json
import socket
import sys


def cmd(port, payload, timeout=20):
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    data = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
        if data.endswith(b"\n"):
            break
    s.close()
    return json.loads(data.decode("utf-8", "replace"))


def dump(port, lo, hi, out, chunk=0x4000):
    buf = bytearray(hi - lo)
    for addr in range(lo, hi, chunk):
        n = min(chunk, hi - addr)
        r = cmd(port, {"id": 1, "cmd": "read_ram", "addr": addr, "len": n})
        if not r.get("ok"):
            print("read failed at", hex(addr), r, file=sys.stderr)
            return 1
        b = bytes.fromhex(r["hex"])
        if len(b) != n:
            print("short read at", hex(addr), len(b), n, file=sys.stderr)
            return 1
        buf[addr - lo:addr - lo + n] = b
        print(f"\r{addr - lo + n:6d}/{hi - lo} bytes", end="", file=sys.stderr)
    print(file=sys.stderr)
    with open(out, "wb") as f:
        f.write(buf)
    print(f"wrote {out} ({len(buf)} bytes)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    d = sub.add_parser("dump")
    d.add_argument("--port", type=int, default=4371)
    d.add_argument("--lo", type=lambda s: int(s, 0), required=True)
    d.add_argument("--hi", type=lambda s: int(s, 0), required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--chunk", type=lambda s: int(s, 0), default=0x4000)

    w = sub.add_parser("write")
    w.add_argument("--port", type=int, default=4371)
    w.add_argument("--addr", type=lambda s: int(s, 0), required=True)
    w.add_argument("--hex", required=True)

    r = sub.add_parser("read")
    r.add_argument("--port", type=int, default=4371)
    r.add_argument("--addr", type=lambda s: int(s, 0), required=True)
    r.add_argument("--len", type=int, default=16)

    g = sub.add_parser("regs")
    g.add_argument("--port", type=int, default=4371)

    a = ap.parse_args()
    if a.mode == "dump":
        return dump(a.port, a.lo, a.hi, a.out, a.chunk)
    if a.mode == "write":
        data = bytes.fromhex(a.hex)
        print(cmd(a.port, {"id": 1, "cmd": "write_ram", "addr": a.addr, "hex": data.hex()}))
        return 0
    if a.mode == "read":
        res = cmd(a.port, {"id": 1, "cmd": "read_ram", "addr": a.addr, "len": a.len})
        print(json.dumps(res, indent=2))
        return 0
    if a.mode == "regs":
        res = cmd(a.port, {"id": 1, "cmd": "get_registers"})
        if res.get("ok"):
            print("pc", res.get("pc"), "sp", res["gpr"][29], "ra", res["gpr"][31])
            print("gpr", res["gpr"])
        else:
            print(res)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())