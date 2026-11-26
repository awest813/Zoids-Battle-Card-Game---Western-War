"""Card identities and rule records drawn by the retail SLPS-03255 UI."""

import csv
import struct
from pathlib import Path

from card_text_table import RAM_BASE

ZOID_COUNT = 81
CEP_COUNT = 193
CEP_RULE_MAP = 0x800F1A80
ZOID_TYPE_TABLE = 0x800ECB10
ZOID_TYPE_COUNT = 34
ZOID_ABILITY_TABLE = 0x800EC8CC
ZOID_ABILITY_COUNT = 48
FACE_STRIDE = 0x5800


def card_records():
    for kind, count, stride, id_offset, face_offset in (
        ("zoid", ZOID_COUNT, 104, 0x64, 0),
        ("cep", CEP_COUNT, 80, 0x4C, ZOID_COUNT),
    ):
        data = Path(f"extracted/{'ZOIDCARD' if kind == 'zoid' else 'CEPCARD'}.DAT").read_bytes()
        if len(data) != count * stride:
            raise ValueError(f"Unexpected {kind} card table size")
        for index in range(count):
            start = index * stride
            record = data[start:start + stride]
            stored_id, = struct.unpack_from("<H", record, id_offset)
            if stored_id != index:
                raise ValueError(f"Unexpected ID {stored_id} for {kind} record {index}")
            name = record[:0x26].split(b"\0", 1)[0].decode("shift_jis")
            yield kind, index, index + face_offset, name, record


def cep_rule_indices(executable):
    offset = CEP_RULE_MAP - RAM_BASE
    return executable[offset:offset + CEP_COUNT]


def zoid_label_slots(executable):
    for kind, table, count in (
        ("type", ZOID_TYPE_TABLE, ZOID_TYPE_COUNT),
        ("ability", ZOID_ABILITY_TABLE, ZOID_ABILITY_COUNT),
    ):
        for index in range(count):
            address = table + index * 4
            source, = struct.unpack_from("<I", executable, address - RAM_BASE)
            yield kind, address, source


def english_names():
    with Path("analysis/CARD_NAMES_EN.tsv").open(encoding="utf-8") as file:
        return {row["japanese"]: row["english"] for row in csv.DictReader(file, delimiter="\t")}


def face_data(archive, index):
    offset = index * FACE_STRIDE
    flags, width, height = struct.unpack_from("<IHH", archive, offset)
    if (flags, width, height) != (0x11, 64, 160):
        raise ValueError(f"Unexpected format for card face {index}")
    start = offset + 8
    end = start + width * height * 2
    return archive[start:end], archive[end:end + 512]
