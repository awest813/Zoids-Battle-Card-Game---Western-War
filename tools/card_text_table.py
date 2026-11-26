"""Read the verified card text table in the local SLPS-03255 executable."""

import struct
from pathlib import Path

EXE = Path("extracted/SLPS_032.55")
RAM_BASE = 0x8000F800
TABLE_START = 0x800EAB2C
CARD_COUNT = 274


def card_text_slots(executable):
    for card in range(CARD_COUNT):
        start = TABLE_START + card * 0x40
        for slot in range(8):
            slot_address = start + slot * 4
            source, = struct.unpack_from("<I", executable, slot_address - RAM_BASE)
            if 0x80010000 <= source < RAM_BASE + len(executable):
                yield card, slot, slot_address, source
