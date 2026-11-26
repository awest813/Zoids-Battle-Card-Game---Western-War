"""Build local English card-face textures for the retail SLPS-03255 disc."""

import csv
import hashlib
import struct
import tomllib
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

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
LIGER_ZERO_SPECIAL = "Frontal melee power\nMelee power 700 against L-types."
LIGER_ZERO_CARDS = (79, 80)
FOCUSED_CANNON = "Focused Charged Particle Cannon. Spend 200 HP. Deal 700 piercing damage to 2 Zoids in front range."
TRANSPORT = "When moving, carry up to 2 adjacent allied M-types or 4 adjacent allied S-types."
WEAPON_DESTROY = "On a hit, discard 1 target Custom Card instead of dealing damage."
BERSERK_CANNON = ("Built-in Charged Particle Cannon. Deal 700 piercing damage to 2 Zoids in front or rear range. "
                 "Berserk. Roll 1 on a hit check and attack an ally in range.")
AMBUSH = "Ambush. When attacked by a Zoid in range, attack first. No counterattack after an ambush."
ALL_DIRECTION_SHOT = ("Built-in All-Direction Shot. Deal 400 damage to all Zoids within 2 tiles, "
                      "including allies and bases. Melee hit checks -1.")
ZOID_SPECIAL = {
    6: "Frontal attack damage taken -100.",
    10: FOCUSED_CANNON,
    13: "Enemy ranged hit checks -1.",
    14: "Melee attack 700. Can also attack the two forward diagonals.",
    15: "Red Parts armor reduces damage from frontal attacks by 100.",
    16: "Charged Particle Cannon. Spend 200 HP. Deal 900 piercing damage to 2 Zoids in range.",
    17: TRANSPORT,
    18: "Frontal melee power +100.",
    19: "Ranged attack +100 against Zoids with air aptitude.",
    20: f"Weapon Destroy. {WEAPON_DESTROY}\n{FOCUSED_CANNON}",
    21: "Frontal melee power +200.",
    22: "Booster Cannon. Ranged power 500, range 5.",
    23: WATER_OR_AIR,
    24: f"Equipment Destroy. {WEAPON_DESTROY}\n"
        "Focused Charged Particle Cannon. Spend 200 HP. Deal 800 piercing damage to 2 Zoids in front range.",
    25: BERSERK_CANNON,
    26: AMBUSH,
    27: WATER_OR_AIR,
    29: "In forest, can attack and counterattack the two rear diagonal tiles.",
    30: FOCUSED_CANNON,
    32: "Can also make ranged attacks one square diagonally behind, on either side.",
    41: BLADE_LIGER_SPECIAL,
    42: "Side melee power 700.",
    43: "Counterattack hit checks +1.",
    44: "Ranged hit checks +1 against Zoids with air aptitude.",
    45: "Long Range Rifle. Ranged power 600, range 7, hit checks +1. Lose 200 HP on a roll of 1.",
    46: "Melee power 700 against L-types. Hit checks +1 against Zoids with air aptitude.",
    47: "Melee 2 adjacent Zoids at once. Lose 200 HP on a roll of 1.",
    48: TRANSPORT,
    49: "Range +3 on turns when this Zoid does not move.",
    50: "Strike Nose. Melee attacks and counters can also reach 2 tiles straight ahead.",
    51: "Underwater Shot. While in water, ranged power 500, range 5.",
    52: "Ranged attack +200 against Zoids with air aptitude.",
    53: "Large-Caliber Beam Cannon. Ranged power 600, range 9, straight ahead only.",
    54: "Sniper Rifle. Ranged power 600, range 5, straight back only.",
    55: WATER_OR_AIR,
    56: ALL_DIRECTION_SHOT,
    57: "After moving straight, frontal melee power +200.",
    60: BLADE_LIGER_SPECIAL,
    63: ALL_DIRECTION_SHOT,
    64: BERSERK_CANNON,
    66: AMBUSH,
    67: "Frontal damage taken -200. A hit roll of 6 against Geno Breaker doubles damage without the +100 crit bonus.",
    73: "Twin Fangs. Melee up to 2 Zoids across the 3 forward tiles.",
    74: "Instead of a normal move, move twice as far on sand. You cannot leave sand.",
    76: "Frontal melee power +100.",
    77: "ATK +400 vs Van's Zoid. On hit, discard 1 target Custom instead of damage. "
        "Use Shadow here for +700 HP, +300 ATK. Shadow's revival effect is unavailable.",
    78: "Side melee +100. ATK +300 vs Raven's Zoid. Energy Shield cuts frontal damage by 300. "
        "Use Zeke here for +800 HP, +200 ATK. Zeke's revival effect is unavailable.",
    **dict.fromkeys(LIGER_ZERO_CARDS, LIGER_ZERO_SPECIAL),
}
ZOID_SPECIAL_RIGHT_EDGE = {
    6: 104, 14: 104, 29: 103, 32: 104, 41: 103, 47: 103, 50: 104, 60: 103, 67: 102, 73: 103,
}
ZOID_BUILT_IN_WEAPONS = {10, 16, 20, 24, 30, 45}
REVIEWED_RULES = {
    0: "All Zoids within one square of the user take 300 damage, including diagonals. Allies and bases are also affected.",
    1: "Target a square 5–10 spaces straight ahead. Zoids on the target take 300 damage. Zoids on adjacent squares take 200. Allies and bases are also affected.",
    2: "Jump straight ahead up to 5 squares over Zoids or any terrain except bases. You cannot also move normally this turn.",
    3: "Instead of counterattacking, roll a die and recover 100 HP per point rolled, up to max HP.",
    4: "Range +2. Attack +100 for M-types or +200 for L-types. Attack and counterattack only straight ahead. Discard this card to resume normal attacks and counters. M- and L-types only. Water and Air types cannot equip it.",
    5: "Attack the same enemy twice in a row. It can counterattack once after both attacks. S-types only.",
    6: "Reduce damage from enemy attacks by 100.",
    7: "Gain 300 HP up to max HP and +1 straight movement. Lose 300 HP when this card is discarded.",
    8: "Attack +200.",
    9: "Attack +100.",
    10: "Attack +100. Range +1.",
    11: "You can also attack or counterattack one square diagonally behind you.",
    12: "Mountains and forests cost 1 movement point per square, even without Mountain aptitude. S- and M-types only.",
    13: "Cross water without Water aptitude. Saboteur cannot discard this card. S- and M-types only.",
    14: "Movement +2. M- and L-types only.",
    15: "Reduce damage from enemy attacks by 200. S-types only.",
    16: "Subtract 1 from enemy rolls to hit this Zoid. S- and M-types only.",
    17: "Move one of your Zoids 6 squares, ignoring terrain movement restrictions.",
    18: "Move one enemy Zoid 6 squares under normal terrain restrictions, then choose its facing.",
    19: "Return 1 Custom Card from your discard pile to your hand.",
    20: "Give one of your Zoids +200 Attack for a single attack.",
    21: "Set one of your Zoids' HP to 0. Deal 300 damage 1 square away and 200 damage 2 squares away, including diagonals. Allies and bases are also affected.",
    22: "Look at your opponent's hand and choose 1 card for them to discard.",
    23: "Choose one of your Zoids with 300 HP or less and discard 1 Custom Card to restore 600 HP, up to max HP. Bases are excluded.",
    24: "Discard 1 Custom Card equipped to an enemy Zoid.",
    25: "Draw 3 cards. Use only on your turn.",
    26: "Restore 300 HP each to up to 2 of your Zoids, up to their max HP. Bases are excluded.",
    27: "Place a barricade on any empty square except water. Only flying Zoids can enter or cross it.",
    28: "Remove 1 barricade from the map.",
    29: "Piercing. Declare before attacking. Deal 500 damage to 2 Zoids in range straight ahead. On a roll of 1, lose 300 HP. Guard has no effect. M-types only.",
    77: "Sand: HP +200\nCommand Wolf AS: Movement +3\nOn a hit check, you may spend 300 HP to add 1 to the roll.",
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
    return font


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


def paint_liger_zero_special(face):
    # The tiny digits cannot reliably distinguish +200 and +300. Retain the
    # disc's bonus amount and raise its contrast alongside the English rule.
    amount_box = (42, 138, 55, 144)
    native_size = (amount_box[2] - amount_box[0], amount_box[3] - amount_box[1])
    source = face.crop(scaled(amount_box)).resize(native_size, Image.Resampling.NEAREST)
    red, green, _, _ = source.split()
    amount = ImageChops.subtract(red, green).point(lambda shade: min(255, max(0, (shade - 9) * 3)))
    amount = amount.resize(tuple(dimension * SCALE for dimension in native_size), Image.Resampling.BICUBIC)
    box = (29, 138, 119, 153)
    font = paint_rule(face, box, LIGER_ZERO_SPECIAL, "#d2d3cd", bold=True)
    label = LIGER_ZERO_SPECIAL.splitlines()[0]
    x = box[0] * SCALE + 12 + round(font.getlength(label))
    face.paste("#252521", (x, box[1] * SCALE), amount)


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
    if index in LIGER_ZERO_CARDS:
        paint_liger_zero_special(face)
    elif index in ZOID_SPECIAL:
        right = ZOID_SPECIAL_RIGHT_EDGE.get(index, 119)
        bottom = 154 if index in (20, 24, 56, 63, 67, 77, 78) else 153
        if index in ZOID_BUILT_IN_WEAPONS:
            paint_label(face, (8, 144, 29, bottom), "BUILT-IN", "#bc492e", "#fff0dd", max_size=15)
        if compact_stats:
            face.paste("#d2d3cd", scaled((8, special_box[3], special_box[2], bottom)))
        paint_rule(face, (special_box[2], special_box[1], right, bottom), ZOID_SPECIAL[index], "#d2d3cd", bold=True)


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
