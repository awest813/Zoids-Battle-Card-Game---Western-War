"""Locate retail dialogue groups and their short text outside the main table."""

import struct

from card_text_table import RAM_BASE, TABLE_START


def dialogue_groups(executable):
    limit = TABLE_START - RAM_BASE
    for offset in range(0x800C0000 - RAM_BASE, limit - 12, 2):
        opcode, mode, count = struct.unpack_from("<3I", executable, offset)
        if opcode != 0x12 or mode not in (0, 1) or not 1 <= count <= 3:
            continue
        if offset + 12 + (count + 1) * 4 > limit:
            continue
        *sources, followup = struct.unpack_from(f"<{count + 1}I", executable, offset + 12)
        if followup in (6, 0x0C, 0x13):
            yield offset + RAM_BASE, followup, sources


def short_dialogue_slots(executable, tracked):
    def is_short(address):
        return 0x800F6B44 <= address < 0x800F6CDC

    for group, _, sources in dialogue_groups(executable):
        if all(source in tracked or is_short(source) for source in sources):
            for index, source in enumerate(sources):
                if is_short(source) and source not in tracked:
                    yield group + 12 + index * 4, source
