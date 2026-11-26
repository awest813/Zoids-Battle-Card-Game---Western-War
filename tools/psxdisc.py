"""Minimal PSX BIN/CUE + ISO9660 reader for auditing.

Single-track MODE2/2352 images are assumed, with fallback for MODE1/2048 ISOs.
"""
import os
import struct
import sys

SECTOR = 2352
DATA_OFF = 24
DATA_LEN = 2048


class Disc:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        self.size = os.path.getsize(path)
        self.bin_mode = True
        # Detect raw 2352 vs cooked 2048 by checking PVD at sector 16
        self.f.seek(16 * SECTOR + DATA_OFF)
        head = self.f.read(8)
        if head[1:6] != b"CD001":
            self.f.seek(16 * DATA_LEN)
            head = self.f.read(8)
            if head[1:6] == b"CD001":
                self.bin_mode = False
            else:
                raise SystemExit("Not an ISO9660 image (PVD not found)")
        self.sectors = self.size // (SECTOR if self.bin_mode else DATA_LEN)

    def read_sector(self, lba, count=1):
        """Return user data for `count` sectors starting at lba."""
        if self.bin_mode:
            self.f.seek(lba * SECTOR + DATA_OFF)
            out = bytearray()
            for _ in range(count):
                out += self.f.read(DATA_LEN)
                self.f.seek(SECTOR - DATA_LEN, 1)
            return bytes(out)
        self.f.seek(lba * DATA_LEN)
        return self.f.read(count * DATA_LEN)

    def read(self, lba, offset, length):
        start = lba * (SECTOR if self.bin_mode else DATA_LEN) + (DATA_OFF if self.bin_mode else 0) + offset
        self.f.seek(start)
        return self.f.read(length)


def parse_record(rec):
    """Parse one ISO9660 directory record. rec is bytes starting with length byte."""
    if not rec or rec[0] == 0:
        return None
    ln = rec[0]
    rec = rec[:ln]
    ext_attr_len = rec[1]
    lba = struct.unpack("<I", rec[2:6])[0]
    size = struct.unpack("<I", rec[10:14])[0]
    flags = rec[25]
    name_len = rec[32]
    name = rec[33:33 + name_len]
    return {
        "lba": lba,
        "size": size,
        "flags": flags,
        "ext_attr_len": ext_attr_len,
        "name": name,
    }


def walk(disc, lba=None, size=None, path="", out=None, depth=0):
    """Recursively list ISO9660 tree. Returns list of dicts."""
    if out is None:
        out = []
    root = disc.read_sector(lba, 1)
    # Root dir record is at offset 156 of PVD; caller may pass it directly.
    pos = 0
    while pos < len(root):
        ln = root[pos]
        if ln == 0:
            # advance to next sector boundary
            pos = (pos // DATA_LEN + 1) * DATA_LEN
            continue
        rec = parse_record(root[pos:pos + ln])
        pos += ln
        if rec is None:
            break
        name = rec["name"]
        if name in (b"\x00", b"\x01"):
            continue
        try:
            name_s = name.decode("ascii")
        except UnicodeDecodeError:
            name_s = name.hex()
        if name_s.endswith(";1"):
            name_s = name_s[:-2]
        full = (path + "/" + name_s) if path else name_s
        entry = {"path": full, "lba": rec["lba"], "size": rec["size"],
                 "dir": bool(rec["flags"] & 2)}
        out.append(entry)
        if entry["dir"] and depth < 32:
            # read whole directory: size bytes
            data = disc.read_sector(rec["lba"], (rec["size"] + DATA_LEN - 1) // DATA_LEN)
            walk_records(disc, data, full, out, depth + 1)
    return out


def walk_records(disc, data, path, out, depth):
    pos = 0
    while pos < len(data):
        ln = data[pos]
        if ln == 0:
            pos = (pos // DATA_LEN + 1) * DATA_LEN
            continue
        rec = parse_record(data[pos:pos + ln])
        pos += ln
        if rec is None:
            break
        name = rec["name"]
        if name in (b"\x00", b"\x01"):
            continue
        name_s = name.decode("ascii", "replace")
        if name_s.endswith(";1"):
            name_s = name_s[:-2]
        full = path + "/" + name_s
        entry = {"path": full, "lba": rec["lba"], "size": rec["size"],
                 "dir": bool(rec["flags"] & 2)}
        out.append(entry)
        if entry["dir"] and depth < 32:
            sub = disc.read_sector(rec["lba"], (rec["size"] + DATA_LEN - 1) // DATA_LEN)
            walk_records(disc, sub, full, out, depth + 1)


def main():
    disc = Disc(sys.argv[1])
    # PVD root dir record at offset 156
    pvd = disc.read_sector(16, 1)
    root = parse_record(pvd[156:156 + 255])
    print(f"Image: {disc.path} ({disc.size} bytes, {disc.sectors} sectors, {'2352' if disc.bin_mode else '2048'})")
    print(f"Root dir LBA {root['lba']} size {root['size']}")
    entries = walk(disc, root["lba"], root["size"])
    print(f"{len(entries)} entries")
    for e in entries:
        print(f"{'d' if e['dir'] else 'f'} {e['size']:>10} {e['lba']:>7}  {e['path']}")


if __name__ == "__main__":
    main()