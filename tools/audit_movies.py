"""Inventory Zoids STR movies from the retail Mode 2 BIN, including XA audio."""

import argparse
import csv
import hashlib
import struct
import sys
from collections import defaultdict
from pathlib import Path

from psxdisc import DATA_LEN, DATA_OFF, SECTOR, Disc, parse_record, walk


STR_MAGIC = b"\x60\x01\x01\x80"
XA_AUDIO = 0x04
CD_SECTORS_PER_SECOND = 150
FIELDS = (
    "path", "start_lba", "sector_count", "width", "height", "frame_count",
    "nominal_fps", "duration_seconds", "xa_sector_count", "xa_streams", "matching_xa",
)
EXE_SHA256 = "0cf561e0050e80ae57bf7ca3e3f30914e1a5ebc837738118158049198b56f0bb"
EXE_ADDRESS_BASE = 0x8000F800
ALBUM_FLAGS = 0x800113FC
MOVIE_TABLE = 0x800C23CC
ALBUM_GROUPS = (
    ("melee", 5, 81, 0x01),
    ("ranged", 86, 81, 0x02),
    ("special", 167, 81, 0x04),
    ("custom_event", 248, 193, 0x08),
)
BOOT_MOVIES = {"M/OP_MOVIE.STR", "M/TOMYLOGO.STR"}


def movie_entries(disc):
    root = parse_record(disc.read_sector(16)[156:])
    return sorted(
        (entry for entry in walk(disc, root["lba"], root["size"])
         if not entry["dir"] and entry["path"].upper().endswith(".STR")),
        key=lambda entry: entry["path"],
    )


def movie_sectors(disc, entry):
    count, remainder = divmod(entry["size"], DATA_LEN)
    if remainder or entry["lba"] + count > disc.sectors:
        raise ValueError(f"{entry['path']}: invalid ISO extent")
    disc.f.seek(entry["lba"] * SECTOR)
    for _ in range(count):
        sector = disc.f.read(SECTOR)
        if len(sector) != SECTOR:
            raise ValueError(f"{entry['path']}: incomplete sector")
        yield sector


def audit_movie(disc, entry):
    frames = set()
    dimensions = set()
    audio = defaultdict(hashlib.sha256)
    xa_sectors = 0
    for sector in movie_sectors(disc, entry):
        if sector[18] & XA_AUDIO:
            xa_sectors += 1
            stream = (sector[16], sector[17], sector[19])
            # Only the 18 XA sound groups, so a different file/channel does
            # not make identical encoded audio appear unique.
            audio[stream].update(sector[DATA_OFF:DATA_OFF + 18 * 128])
        elif sector[DATA_OFF:DATA_OFF + 4] == STR_MAGIC:
            frames.add(struct.unpack_from("<I", sector, DATA_OFF + 8)[0])
            dimensions.add(struct.unpack_from("<HH", sector, DATA_OFF + 16))

    frame_count = len(frames)
    if not frames or min(frames) != 1 or max(frames) != frame_count or len(dimensions) != 1:
        raise ValueError(f"{entry['path']}: irregular STR frame headers")
    width, height = dimensions.pop()
    sector_count = entry["size"] // DATA_LEN
    # Use double-speed transport plus the frame count to distinguish the two
    # cadences on this disc. Allow trailing padding, including partial seconds.
    span = sector_count / CD_SECTORS_PER_SECOND
    fps = min((15, 30), key=lambda rate: abs(span - frame_count / rate))
    if abs(span - frame_count / fps) > 0.15:
        raise ValueError(f"{entry['path']}: unsupported STR cadence")
    streams = " ".join(f"{file_id}:{channel}:0x{coding:02X}"
                       for file_id, channel, coding in sorted(audio))
    return {
        "path": entry["path"], "start_lba": entry["lba"], "sector_count": sector_count,
        "width": width, "height": height, "frame_count": frame_count,
        "nominal_fps": fps, "duration_seconds": f"{frame_count / fps:.3f}",
        "xa_sector_count": xa_sectors, "xa_streams": streams,
    }, tuple(sorted((key[2], digest.digest()) for key, digest in audio.items()))


def write_inventory(disc, entries, output):
    rows = []
    audio_groups = defaultdict(list)
    for entry in entries:
        row, audio_key = audit_movie(disc, entry)
        if audio_key:
            audio_groups[audio_key].append(row["path"])
        rows.append((row, audio_key))
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row, audio_key in rows:
        row["matching_xa"] = " ".join(path for path in audio_groups.get(audio_key, ())
                                      if path != row["path"])
        writer.writerow(row)


def write_album_inventory(executable, entries, output):
    if hashlib.sha256(executable).hexdigest() != EXE_SHA256:
        raise ValueError("the Movie Album table requires the original SLPS_032.55 executable")
    flag_offset = ALBUM_FLAGS - EXE_ADDRESS_BASE
    # The game clears the save's movie flags and seeds only the first 103 bytes.
    flags = executable[flag_offset:flag_offset + 103].ljust(193, b"\0")
    extents = {entry["path"]: entry["lba"] for entry in entries}
    rows = []
    seen = set()
    for category, first_record, count, bit in ALBUM_GROUPS:
        for card_index in range(count):
            if not flags[card_index] & bit:
                continue
            record = MOVIE_TABLE - EXE_ADDRESS_BASE + 16 * (first_record + card_index)
            pointer, = struct.unpack_from("<I", executable, record)
            start = pointer - EXE_ADDRESS_BASE
            end = executable.index(0, start, start + 32)
            # The B2Z0010 path has a period after the ISO version suffix.
            path = executable[start:end].decode("ascii").removeprefix("\\")
            path = path.removesuffix(".").removesuffix(";1").replace("\\", "/")
            if path not in extents or path in seen:
                raise ValueError(f"invalid or repeated Movie Album clip: {path}")
            seen.add(path)
            page, tile = divmod(len(rows), 9)
            rows.append((page + 1, tile + 1, category, card_index, path, extents[path]))
    if seen != extents.keys() - BOOT_MOVIES:
        raise ValueError("the Movie Album does not cover all non-boot STR files")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("page", "tile", "category", "card_index", "path", "start_lba"))
    writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disc", type=Path, help="single-track retail Mode 2/2352 BIN")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--extract", metavar="CLIP", help="disc path to extract for local review")
    mode.add_argument("--album-exe", type=Path, help="original SLPS_032.55 to audit the Movie Album grid")
    parser.add_argument("--output", type=Path, help="new local STR file for --extract")
    args = parser.parse_args()
    if bool(args.extract) != bool(args.output):
        parser.error("--extract and --output must be used together")
    try:
        disc = Disc(args.disc)
        with disc.f:
            if not disc.bin_mode:
                raise ValueError("a raw Mode 2/2352 BIN is needed to read XA audio")
            entries = movie_entries(disc)
            if not entries:
                raise ValueError("no STR files found")
            if args.extract:
                clip = args.extract.replace("\\", "/").upper()
                entry = next((item for item in entries if item["path"].upper() == clip), None)
                if entry is None:
                    raise ValueError(f"unknown STR clip: {args.extract}")
                with args.output.open("xb") as output:
                    for sector in movie_sectors(disc, entry):
                        output.write(sector)
            elif args.album_exe:
                write_album_inventory(args.album_exe.read_bytes(), entries, sys.stdout)
            else:
                write_inventory(disc, entries, sys.stdout)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
