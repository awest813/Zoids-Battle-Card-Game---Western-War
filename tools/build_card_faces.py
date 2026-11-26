"""Build local English card-face textures for the retail SLPS-03255 disc."""

import csv
import hashlib
import struct
import tomllib
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build_ui_textures import average_light, faded
from card_catalog import card_records, cep_rule_indices, english_names, face_data
from card_text_table import EXE, card_text_slots
from packed_ui import paletted_image

SCALE = 4
FACE_ARCHIVE_HASH = "78ba8b1ea0a37c8e47a2c4e81d01b67453b878faf28b1b10da99e56dc0d91e40"
THUMB_ARCHIVE_HASH = "b38a63767faf619609cb6888c4cc77a75365c2db14c78ccecee9463666d772f0"
PACK = Path("work/localization-textures/SLPS-03255")
WATER_OR_AIR = "Water aptitude on water tiles. Air aptitude on all other tiles."
BLADE_LIGER_SPECIAL = "Side melee power 800. Frontal attack damage taken -200."
ZOID_SPECIAL = {
    6: "Frontal attack damage taken -100.",
    13: "Enemy ranged hit checks -1.",
    14: "Melee attack 700. Can also attack the two forward diagonals.",
    18: "Melee attack +100.",
    19: "Ranged attack +100 against Zoids with air aptitude.",
    21: "Melee attack +200.",
    23: WATER_OR_AIR,
    27: WATER_OR_AIR,
    32: "Can also make ranged attacks one square diagonally behind, on either side.",
    41: BLADE_LIGER_SPECIAL,
    42: "Side melee power 700.",
    43: "Counterattack hit checks +1.",
    44: "Ranged hit checks +1 against Zoids with air aptitude.",
    49: "Range +3 on turns when this Zoid does not move.",
    52: "Ranged attack +200 against Zoids with air aptitude.",
    55: WATER_OR_AIR,
    60: BLADE_LIGER_SPECIAL,
    76: "Melee attack +100.",
}
ZOID_SPECIAL_RIGHT_EDGE = {6: 104, 14: 104, 32: 104, 41: 103, 60: 103}
REVIEWED_RULES = {
    0: "All Zoids within one square of the user take 300 damage, including diagonals. Allies and bases are also affected.",
    1: "Target a square 5–10 spaces straight ahead. Zoids on the target take 300 damage. Zoids on adjacent squares take 200. Allies and bases are also affected.",
}
TERRAIN_ICONS = (
    (0x02, "MTN", "#744d32"),
    (0x04, "FOR", "#345d38"),
    (0x08, "SAND", "#997444"),
    (0x10, "WTR", "#286b9e"),
    (0x01, "AIR", "#575783"),
)
RANGE_MODIFIERS = {
    1: "FRONT",
    2: "ALL",
    3: "FRONT/SIDE",
    4: "REAR",
    5: "WATER",
    6: "SIDE/REAR",
}
MOVE_MODIFIERS = {1: "STRAIGHT", 2: "WATER"}


def scaled(box):
    return tuple(value * SCALE for value in box)


def paint_label(face, box, label, background, ink, max_size=24):
    x, y, right, bottom = scaled(box)
    width, height = right - x, bottom - y
    face.paste(background, (x, y, right, bottom))
    if not label:
        return
    font = ImageFont.truetype("arialbd.ttf", max_size)
    left, top, edge, base = font.getbbox(label)
    lettering = Image.new("RGBA", (edge - left, base - top))
    ImageDraw.Draw(lettering).text((-left, -top), label, font=font, fill=ink)
    if lettering.width > width - 4 or lettering.height > height - 2:
        lettering = lettering.resize((min(width - 4, lettering.width), min(height - 2, lettering.height)),
                                     Image.Resampling.LANCZOS)
    face.alpha_composite(lettering, (x + (width - lettering.width) // 2,
                                    y + (height - lettering.height) // 2))


def paint_rule(face, box, rule, background, bold=False):
    x, y, right, bottom = scaled(box)
    width, height = right - x - 12, bottom - y - 8
    for size in range(19, 9, -1):
        font = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
        lines = []
        for paragraph in rule.splitlines():
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}".lstrip()
                if line and font.getlength(candidate) > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            if line:
                lines.append(line)
        step = size + 3
        if step * len(lines) <= height and all(font.getlength(line) <= width for line in lines):
            break
    else:
        raise ValueError(f"Card rule does not fit: {rule}")
    face.paste(background, (x, y, right, bottom))
    draw = ImageDraw.Draw(face)
    for index, line in enumerate(lines):
        draw.text((x + 6, y + 3 + index * step), line, font=font, fill="#252521", anchor="lt")


def paint_zoid_modifiers(face, record, stat_offset):
    # The range kind follows its bonus, while the movement bonus is signed.
    range_bonus, range_kind = struct.unpack_from("<hH", record, 0x36)
    move_bonus, move_kind = struct.unpack_from("<hH", record, 0x3C)
    if range_kind:
        # The top of the old direction glyphs can share a row with the base range.
        face.paste("#edaf62", scaled((82, 112 + stat_offset, 111, 113 + stat_offset)))
        paint_label(face, (82, 113 + stat_offset, 119, 120 + stat_offset),
                    f"{RANGE_MODIFIERS[range_kind]} {range_bonus:+d}",
                    "#edaf62", "#2e2618", max_size=17)
    if move_kind:
        paint_label(face, (36, 128 + stat_offset, 63, 135 + stat_offset),
                    f"{MOVE_MODIFIERS[move_kind]} {move_bonus:+d}",
                    "#a6cc99", "#253e2a", max_size=17)


def paint_zoid(face, name, index, record):
    paint_label(face, (31, 5, 96, 13), name, "#484e56", "#fff9e2")
    compact_stats = index in (77, 78)
    stat_offset = -4 if compact_stats else 0
    for (x, y, right, bottom), label, background in (
        ((8, 106, 28, 113), "ATK", "#dca450"),
        ((32, 107, 45, 114), "SHOT", "#e6c484"),
        ((32, 114, 45, 119), "MELEE", "#d6ad65"),
        ((65, 106, 79, 113), "RNG", "#f4c575"),
        ((8, 121, 29, 129), "MOVE", "#80b47f"),
        ((65, 121, 86, 128), "TERRAIN", "#7db389"),
    ):
        paint_label(face, (x, y + stat_offset, right, bottom + stat_offset),
                    label, background, "#29271e", max_size=18)
    paint_zoid_modifiers(face, record, stat_offset)
    aptitude, = struct.unpack_from("<H", record, 0x40)
    if aptitude:
        # These variants have a shorter green strip above their rules.
        top, bottom = (119, 129) if compact_stats else (122, 134)
        x, y, right, end = scaled((86, top, 120, bottom))
        background = face.crop((x - 4, y, x, end))
        face.paste(background.resize((right - x, end - y)), (x, y))
        position = 119
        for bit, label, color in reversed(TERRAIN_ICONS):
            if aptitude & bit:
                paint_label(face, (position - 10, top + 1, position, bottom - 1),
                            label, color, "#fff9e6", max_size=11)
                position -= 11
    special_box = (8, 133, 25, 139) if compact_stats else (8, 138, 29, 145)
    paint_label(face, special_box, "SPECIAL", "#dfdfd6", "#343331", max_size=18)
    if index in ZOID_SPECIAL:
        right = ZOID_SPECIAL_RIGHT_EDGE.get(index, 119)
        paint_rule(face, (29, 138, right, 153), ZOID_SPECIAL[index], "#d2d3cd", bold=True)


def paint_cep(face, name, rule, pilot, source):
    # Preserve the red property mark beside some Custom/Event names.
    mark = next((x for x in range(15, 85)
                 if any(r > 95 and r > g * 1.45 and r > b * 1.45
                        for r, g, b, _ in (source.getpixel((x, y)) for y in range(103, 110)))), None)
    right = mark if mark is not None and mark >= 35 and not pilot else 86
    ink = "#fff0a6" if pilot else "#fff9e6"
    paint_label(face, (12, 102, right, 111), name, "#3a3c39", ink)
    if rule:
        paint_rule(face, (12, 117, 117, 150), rule, "#f1efeb")


def rule_text(executable):
    translations = {}
    for file in ("zoids.pointer_pending.toml", "zoids.card_short.toml"):
        with (Path("translations") / file).open("rb") as stream:
            for entry in tomllib.load(stream)["entry"]:
                for address in entry.get("ptr_addrs", []):
                    translations[int(address, 0), entry["src_addr"]] = entry["en"]
    lines = defaultdict(list)
    for index, slot, address, source in card_text_slots(executable):
        translation = translations[address, source].strip()
        if translation:
            lines[index].append((slot, translation))
    return lines


def face_rule(index, rules, pilot):
    if index in REVIEWED_RULES:
        return REVIEWED_RULES[index]
    rows = rules.get(index, ())
    if not pilot:
        return " ".join(text for _, text in rows)
    summary = [text for slot, text in rows if slot < 4 and text not in ("-", "---")]
    effect = " ".join(text for slot, text in rows if slot >= 4)
    return "\n".join(summary + [effect])


def texture_keys(path):
    with Path(path).open(encoding="utf-8") as file:
        return {int(row["image_index"]): (row["upload_hash"], row["palette_hash"])
                for row in csv.DictReader(file)}


def thumbnail_data(archive, index):
    offset = index * 2048
    if struct.unpack_from("<IHH", archive, offset) != (1, 12, 64):
        raise ValueError(f"Unexpected thumbnail format at {index}")
    return paletted_image((48, 64), archive[offset + 8:offset + 1544],
                          archive[offset + 1544:offset + 1576], p8=False)


def paint_thumbnail(source, kind, name, ratio):
    face = source.resize((48 * SCALE, 64 * SCALE), Image.Resampling.NEAREST)
    background = faded((64, 66, 66, 255), ratio)
    ink = faded((255, 249, 226, 255), ratio)
    box = (11, 2, 36, 6) if kind == "zoid" else (5, 41, 33, 45)
    paint_label(face, box, name, background, ink, max_size=13)
    return face


def main():
    archive = Path("extracted/TIM/ZOIDCARD.TIM").read_bytes()
    if hashlib.sha256(archive).hexdigest() != FACE_ARCHIVE_HASH:
        raise ValueError("The card texture keys were indexed for a different archive")
    thumbs = Path("extracted/TIM/SZCARD.TIM").read_bytes()
    if hashlib.sha256(thumbs).hexdigest() != THUMB_ARCHIVE_HASH:
        raise ValueError("The thumbnail texture keys were indexed for a different archive")
    keys = texture_keys("analysis/CARD_FACE_KEYS.csv")
    thumb_keys = texture_keys("analysis/CARD_THUMBNAIL_KEYS.csv")
    names = english_names()
    executable = EXE.read_bytes()
    rules = rule_text(executable)
    cep_rules = cep_rule_indices(executable)
    output = PACK / "replacements"
    output.mkdir(parents=True, exist_ok=True)
    dumps = defaultdict(list)
    for path in (PACK / "dumps").glob("texupload-P4-*-12x64-0-0-48x64-P0-15.png"):
        dumps[path.name.split("-")[2]].append(path)
    for kind, index, face_index, japanese, record in card_records():
        name = names[japanese]
        pixels, palette = face_data(archive, face_index)
        source = paletted_image((128, 160), pixels, palette, p8=True, semitransparent=True)
        face = source.resize((128 * SCALE, 160 * SCALE), Image.Resampling.NEAREST)
        if kind == "zoid":
            paint_zoid(face, name, index, record)
        else:
            pilot = struct.unpack_from("<H", record, 0x28)[0] == 2
            paint_cep(face, name, face_rule(cep_rules[index], rules, pilot), pilot, source)
        upload, palette = keys[face_index]
        face.save(output / f"texupload-STP8-{upload}-{palette}-64x160-0-0-128x160-P0-255.png")
        upload, palette = thumb_keys[face_index]
        source = thumbnail_data(thumbs, face_index)
        target = f"texupload-P4-{upload}-{palette}-12x64-0-0-48x64-P0-15.png"
        paint_thumbnail(source, kind, name, 1).save(output / target)
        reference = average_light(source)
        for path in dumps[upload]:
            with Image.open(path) as dump:
                frame = dump.convert("RGBA")
            paint_thumbnail(frame, kind, name, min(1, average_light(frame) / reference)).save(output / path.name)
    print("Rendered English lettering for 274 card faces and thumbnail name bands.")


if __name__ == "__main__":
    main()
