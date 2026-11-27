"""Render English lettering onto local SLPS-03255 texture dumps."""

import argparse
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

from packed_ui import packed_texture, paletted_image

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "work/localization-textures/SLPS-03255"
BUILD_DUMPS = (Path.home() / "zoids-recomp/zoids-battle-card-game/build-reference"
               / "mods/texture-packs/SLPS-03255/dumps")
ATLAS_ROWS = (
    ("SCENARIO MODE", "NEW DATA"),
    ("FREE MODE", "CARD ALBUM"),
    ("TRADE MODE", "ZOID ALBUM"),
    ("ALBUM MODE", "MOVIE ALBUM"),
    ("OPTIONS", "~ MODE SELECT ~"),
    ("LOAD GAME", "~ SCENARIO MODE ~"),
    ("NEW GAME", "~ FREE MODE ~"),
    ("CONTINUE", "~ ALBUM MODE ~"),
    ("LOAD DATA", None),
)


def text_layer(text, size, font_name, font_size, color, outline, *, align="center"):
    font = ImageFont.truetype(font_name, font_size)
    left, top, right, bottom = font.getbbox(text, stroke_width=1)
    glyphs = Image.new("RGBA", (right - left, bottom - top))
    ImageDraw.Draw(glyphs).text(
        (-left, -top), text, font=font, fill=color, stroke_width=1, stroke_fill=outline
    )
    width, height = size
    if glyphs.width > width or glyphs.height > height:
        glyphs = glyphs.resize((min(width, glyphs.width), min(height, glyphs.height)),
                              Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", size)
    x = 0 if align == "left" else (width - glyphs.width) // 2
    layer.paste(glyphs, (x, (height - glyphs.height) // 2))
    return layer


def faded(color, ratio):
    return tuple(round(channel * ratio) for channel in color[:3]) + (color[3],)


def average_light(image):
    return sum(ImageStat.Stat(image.convert("RGB")).mean)


def mode_atlas(image, ratio, font):
    ink = faded((246, 246, 246, 255), ratio)
    outline = (0, 0, 0, 255)
    for row, labels in enumerate(ATLAS_ROWS):
        y = row * 16
        for col, label in enumerate(labels):
            if label is None:
                continue
            x = col * 96
            width = 96 if col == 0 or row < 4 else 120
            lettering = text_layer(label, (width - 2, 15), font, 13, ink, outline, align="left")
            image.paste((0, 0, 0, 0), (x, y, x + width, y + 16))
            image.alpha_composite(lettering, (x + 1, y))
    return image


def memory_card(image, ratio, font):
    box = (0, 16, 76, 31)
    image.paste((0, 0, 0, 0), box)
    ink = faded((211, 211, 226, 255), ratio)
    lettering = text_layer("- SAVE DATA -", (70, 12), font, 10, ink, (0, 0, 0, 255), align="left")
    image.alpha_composite(lettering, (0, 17))
    return image


def name_banner(image, ratio, font):
    captions = (
        (160, 32, 72, "CHOOSE NATION"),
        (160, 48, 72, "ENTER NAME"),
        (160, 64, 72, "DEPLOY ZOIDS"),
        (0, 80, 72, "SELECT ZOID"),
        (72, 80, 72, "BUILD DECK"),
        (144, 80, 72, "ZOID INFO"),
        (0, 96, 72, "SELECT DECK"),
        (72, 96, 72, "ZOID ABILITIES"),
        (144, 96, 72, "CARD TRADE"),
        (0, 112, 72, "DECK NAME"),
        (72, 112, 72, "ZOID EQUIPMENT"),
        (144, 112, 72, "SELECT CARD"),
    )
    for x, y, width, label in captions:
        transparent_caption(image, (x, y, x + width, y + 16), f"- {label} -", ratio, font)
    return image


def transparent_caption(image, box, label, ratio, font):
    x, y, right, bottom = box
    image.paste((0, 0, 0, 0), box)
    ink = faded((211, 211, 226, 255), ratio)
    lettering = text_layer(label, (right - x, bottom - y - 2), font, 10, ink, (0, 0, 0, 255))
    image.alpha_composite(lettering, (x, y + 1))


def button_label(image, box, label, ratio, font):
    button = image.crop(box)
    pixels = list(struct.iter_unpack("4B", button.tobytes()))
    mask = Image.new("L", button.size)
    mask.putdata([255 if a and r >= 40 and r <= g * 1.2 and g <= b * 1.35 else 0
                  for r, g, b, a in pixels])
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask.putdata([0 if r > g * 1.2 and g > b * 1.2 else erase
                  for (r, g, b, _), erase in zip(pixels, mask.tobytes())])
    underline = button.crop((36, 0, 37, button.height)).resize(button.size, Image.Resampling.NEAREST)
    x, y = box[:2]
    image.paste(underline, (x, y), mask)
    white = faded((243, 241, 226, 255), ratio)
    lettering = text_layer(label, (74, 15), font, 13, white, (0, 0, 0, 255))
    image.alpha_composite(lettering, (x + 3, y))


def free_mode(image, ratio, font):
    for box, label in (
        ((0, 24, 73, 40), "- SELECT STAGE -"),
        ((174, 128, 249, 144), "- GAME SETTINGS -"),
        ((174, 144, 249, 160), "- CARD TRADE -"),
    ):
        transparent_caption(image, box, label, ratio, font)
    for column, labels in enumerate((
        ("SORTIE", "ZOIDS", "HAND", "INFO", "EXIT"),
        ("SORTIE", "ZOIDS", "HAND", "INFO", "EXIT"),
        ("SAVE", "SAVE"),
    )):
        for row, label in enumerate(labels):
            x, y = column * 80, 48 + row * 16
            button_label(image, (x, y, x + 80, y + 16), label, ratio, font)
    return image


def operations_base_textures(output, dumps, font):
    # Each display palette uploads the Sortie button and the lower six
    # buttons separately. Their siblings contain the original English art.
    labels = {
        (176, 0, 80, 16): (("SORTIE",),),
        (0, 24, 240, 32): (("INFO", "HAND", "SUPPLY"), ("SAVE", "BUY", "CANCEL")),
        (80, 40, 80, 16): (("BUY",),),
        (160, 40, 80, 16): (("CANCEL",),),
    }
    variants = {}
    for name, path in dumps.items():
        fields = name.split("-")
        if fields[2] != "35930441D5B04801":
            continue
        with Image.open(path) as source:
            image = source.convert("RGBA")
        key = (*map(int, fields[5:7]), *image.size)
        if key in labels:
            variants.setdefault(key, []).append((name, image))
    for key, images in variants.items():
        reference = max(average_light(image) for _, image in images)
        if not reference:
            continue
        for name, image in images:
            ratio = average_light(image) / reference
            for row, buttons in enumerate(labels[key]):
                for col, label in enumerate(buttons):
                    x, y = col * 80, row * 16
                    button_label(image, (x, y, x + 80, y + 16), label, ratio, font)
            image.save(output / name)

    city = "texupload-P4-A6F8A51A32F094E4-EA65DF42BAF81E9F-64x248-128-80-128x24-P0-15.png"
    if city in dumps:
        with Image.open(dumps[city]) as source:
            plate = source.convert("RGBA")
        box = (3, 3, 125, 19)
        background = plate.crop(box)
        for y in range(background.height):
            row = [background.getpixel((x, y)) for x in range(background.width)]
            wood = Counter(color for color in row if 48 <= color[0] <= 164 and color[2] <= 49)
            if wood:
                fill = wood.most_common(1)[0][0]
                for x, color in enumerate(row):
                    if color not in wood:
                        background.putpixel((x, y), fill)
        plate.paste(background, box[:2])
        lettering = text_layer("NEW HELIC CITY", background.size, font, 14,
                               (255, 247, 230, 255), (32, 14, 4, 255))
        plate.alpha_composite(lettering, box[:2])
        plate.save(output / city)


def title_screen(image, reference, ratio):
    bands = (
        ((45, 22, 275, 41), (45, 0, 275, 19), "ZOIDS BATTLE CARD GAME", "arialbd.ttf", 15),
        ((60, 135, 260, 171), (60, 174, 260, 210), "WESTERN CONTINENTAL WAR", "impact.ttf", 23),
    )
    for box, donor, label, font, font_size in bands:
        sample = reference.crop(box)
        mask = Image.new("L", sample.size)
        pixels = struct.iter_unpack("4B", sample.tobytes())
        mask.putdata([255 if r >= 35 and r * 5 >= b * 4 else 0 for r, _, b, _ in pixels])
        mask = mask.filter(ImageFilter.MaxFilter(5))
        background = image.crop(donor).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        image.paste(background, box[:2], mask)
        ink = faded((248, 246, 234, 255), ratio)
        edge = faded((43, 34, 28, 255), ratio)
        lettering = text_layer(label, sample.size, font, font_size, ink, edge)
        image.alpha_composite(lettering, box[:2])
    return image


def card_trade(image, ratio, font):
    box = (223, 16, 297, 31)
    # The blank section of this header is a horizontal gradient in rows.
    background = image.crop((176, box[1], 182, box[3]))
    image.paste(background.resize((box[2] - box[0], background.height)),
                box[:2])
    ink = faded((223, 229, 243, 255), ratio)
    lettering = text_layer("- CARD EXCHANGE -", (72, 12), font, 9, ink, (0, 0, 0, 255))
    image.alpha_composite(lettering, (224, 17))
    return image


def battle_result(image, ratio, font):
    # The frame, numerals, arrow sprites, engraving and rules line are shared.
    labels = (
        ((65, 24, 256, 48), (63, 24, 64, 48), "BATTLE RESULTS", 17, "center"),
        ((29, 63, 122, 80), (133, 63, 226, 80), "ASSAULT POINTS", 11, "left"),
        ((29, 87, 122, 104), (133, 87, 226, 104), "DEFEAT POINTS", 11, "left"),
        ((78, 111, 125, 128), (139, 111, 186, 128), "ZOIDS", 11, "center"),
        ((92, 135, 125, 152), (139, 135, 172, 152), "BASE", 11, "center"),
        ((29, 166, 122, 185), (133, 166, 226, 185), "TOTAL POINTS", 11, "left"),
    )
    for box, donor, label, size, align in labels:
        original = image.crop(box)
        background = image.crop(donor).resize(original.size)
        if label == "BATTLE RESULTS":
            image.paste(background, box[:2])
        else:
            # Remove lettering and its stroke while retaining the red underline.
            raw = list(struct.iter_unpack("4B", original.tobytes()))
            mask = Image.new("L", original.size)
            mask.putdata([255 if r >= 65 and r * 5 >= b * 4 else 0 for r, _, b, _ in raw])
            mask = mask.filter(ImageFilter.MaxFilter(5))
            mask.putdata([0 if r > g * 1.30 and r > b * 1.30 else erase
                          for (r, g, b, _), erase in zip(raw, mask.tobytes())])
            image.paste(background, box[:2], mask)
        ink = faded((247, 243, 225, 255), ratio)
        lettering = text_layer(label, original.size, font, size, ink, (0, 0, 0, 255), align=align)
        image.alpha_composite(lettering, box[:2])
    return image


def battle_phase_header(image, ratio, font):
    headings = (
        ((0, 0, 48, 16), "DRAW"),
        ((48, 0, 112, 16), "CUSTOM"),
        ((112, 0, 192, 16), "MOVE & FIGHT"),
        ((192, 0, 224, 16), "END"),
        ((0, 16, 64, 32), "PHASE"),
    )
    ink = faded((250, 250, 250, 255), ratio)
    edge = faded((28, 28, 34, 255), ratio)
    for box, heading in headings:
        x, y, right, bottom = box
        image.paste((0, 0, 0, 0), box)
        glyph = text_layer(heading, (right - x - 1, bottom - y), font, 15, ink, edge)
        image.alpha_composite(glyph, (x, y))
    return image


def battle_phase_plaques(image, _ratio, font):
    labels = ("DRAW PHASE", "CUSTOM PHASE", "MOVE PHASE", "BATTLE PHASE",
              "END PHASE", "ENEMY TURN", "PLAYER TURN", "PLAY CARD")
    for row, label in enumerate(labels):
        y = row * 32
        left, right = (9, 86) if row < 5 else (14, 113)
        box = (left, y + 5, right, y + 28)
        region = image.crop(box)
        # The darkest interior shade fills the existing plaque behind its lettering.
        visible = [pixel for pixel in struct.iter_unpack("4B", region.tobytes()) if pixel[3]]
        if not visible:
            continue
        shade = min(visible, key=lambda rgb: sum(rgb[:3]))
        original = max(visible, key=lambda rgb: max(rgb[:3]) - min(rgb[:3]))
        ink = tuple(max(0, min(255, int(v * 1.1))) for v in original[:3]) + (255,)
        image.paste(shade, box)
        glyph = text_layer(label, (right - left, 22), font, 12, ink, (5, 5, 12, 255))
        image.alpha_composite(glyph, box[:2])
    return image


ROSTER_ICONS = {
    (16, 104): "DP",
    (112, 104): "ALL",
    (176, 104): "R",
    (192, 104): "M",
    (208, 104): "FWD",
    (224, 104): "STR",
    (240, 104): "AFT",
    (0, 120): "SIDE",
    (16, 120): "WTR",
    (32, 120): "MTN",
    (48, 120): "FOR",
    (64, 120): "SND",
    (80, 120): "AIR",
    (96, 120): "WTR",
    (160, 120): "ATK",
    (176, 120): "RNG",
    (192, 120): "MOV",
    (48, 160): "SP",
    (200, 184): "REM",
    (128, 224): "PLN",
    (144, 224): "SHL",
    (160, 224): "DEP",
}


def roster_icons(output, dumps, font):
    for name, path in dumps.items():
        fields = name.split("-")
        if fields[2] != "CDD59CCE015C972A":
            continue
        x, y = map(int, fields[5:7])
        with Image.open(path) as source:
            image = source.convert("RGBA")
        changed = False
        for (icon_x, icon_y), label in ROSTER_ICONS.items():
            left, top = icon_x - x, icon_y - y
            if not (0 <= left <= image.width - 16 and 0 <= top <= image.height - 16):
                continue
            box = (left + 2, top + 2, left + 14, top + 14)
            center = image.crop(box)
            if center.getchannel("A").getbbox() is None:
                # Some atlas variants use a transparent palette for this tile.
                continue
            edge = center.crop((0, 0, 1, 12))
            image.paste(edge.resize(center.size, Image.Resampling.NEAREST), box[:2])
            _, level = center.convert("L").getextrema()
            ink = (level, level, level, 255)
            glyph = text_layer(label, center.size, font, 10, ink, (0, 0, 0, 255))
            image.alpha_composite(glyph, box[:2])
            changed = True
        if (x, y, image.width, image.height) == (72, 168, 160, 16):
            # The compact Size caption sits immediately after its badge.
            box = (144, 0, 160, 16)
            _, level = image.crop(box).convert("L").getextrema()
            image.paste((0, 0, 0, 0), box)
            glyph = text_layer("SIZE", (16, 14), font, 8, (level, level, level, 255), (0, 0, 0, 255))
            image.alpha_composite(glyph, (144, 1))
            changed = True
        if changed:
            image.save(output / name)


def packed_variants(file, entry, upload, palette_keys, *, semitransparent=True):
    words, height, p8, pixels, palettes = packed_texture(file.read_bytes(), entry)
    mode, factor, stride = ("P8", 2, 512) if p8 else ("P4", 4, 32)
    width = words * factor
    variants = {}
    prefix = f"ST{mode}" if semitransparent else mode
    for index, key in enumerate(palette_keys):
        palette = palettes[index * stride:(index + 1) * stride]
        maximum = stride // 2 - 1
        name = f"texupload-{prefix}-{upload}-{key}-{words}x{height}-0-0-{width}x{height}-P0-{maximum}.png"
        variants[name] = paletted_image((width, height), pixels, palette, p8=p8,
                                        semitransparent=semitransparent)
    return variants


def result_variants(path, entry, upload, palette):
    return {
        **packed_variants(path, entry, upload, (palette,)),
        **packed_variants(path, entry, upload, (palette,), semitransparent=False),
    }


def briefing_map_labels(image, _ratio, font):
    typeface = ImageFont.truetype(font, 8)
    draw = ImageDraw.Draw(image)
    for box, label in (((1, 1, 35, 15), "Gaigalus"), ((21, 33, 79, 47), "New Helic City")):
        left, top, right, bottom = box
        background = image.getpixel((left, top))
        _, level = image.crop(box).convert("L").getextrema()
        image.paste(background, box)
        x0, y0, x1, y1 = typeface.getbbox(label)
        x = (left + right - x1 - x0) // 2
        y = (top + bottom - y1 - y0) // 2
        draw.text((x, y), label, font=typeface, fill=(level, level, level, 255))
    return image


def battle_phase_textures(output, tim_dir, font):
    targets = (
        (1, "0D4796B6C01E2BF8", ("AADDEBE587988EE9",), battle_phase_header),
        (7, "65BB4E37AD741CAB",
         ("ADA57F44DA5C7B41", "F59956196F338B81", "70B9F1A3F3400002"), battle_phase_plaques),
    )
    archive = tim_dir / "GAME.TIM"
    for entry, upload, palettes, render in targets:
        variants = {}
        for semi in (False, True):
            variants.update(packed_variants(archive, entry, upload, palettes, semitransparent=semi))
        for name, original in variants.items():
            localized = render(original, 1, font)
            localized.save(output / name)
            if entry == 7 and "-ADA57F44DA5C7B41-" in name:
                # The Player Turn draw requests a separate crop of the atlas.
                player_turn = localized.crop((0, 192, 128, 224))
                crop_name = name.replace("-0-0-128x256-", "-0-192-128x32-")
                player_turn.save(output / crop_name)
        print(f"{render.__name__}: {len(variants)} full-palette replacements")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-dir", action="append", type=Path,
                        help="Texture dump source (repeatable)")
    args = parser.parse_args()
    dump_dirs = args.dump_dir or (BUILD_DUMPS, PACK / "dumps")
    dumps = {p.name: p for directory in dump_dirs for p in directory.glob("texupload-*.png")}
    output = PACK / "replacements"
    output.mkdir(parents=True, exist_ok=True)
    font = "arialbd.ttf"
    roster_icons(output, dumps, font)
    operations_base_textures(output, dumps, font)
    tim_dir = ROOT / "extracted/TIM"
    battle_phase_textures(output, tim_dir, font)
    data = (tim_dir / "CARD_T.TIM").read_bytes()
    native_trade = paletted_image((320, 240), data[0x220:], data[20:532], p8=True, semitransparent=True)
    name_palettes = ("7CBD707322EDD1A9", "0A6C13463C31C65A", "B597D20C389A9477",
                     "AA0E879BE88C966E", "3D83B302374031D5")
    trade_key = "texupload-STP8-30D4BEA33BB38122-7DBF66BB68759093-160x240-0-0-320x240-P0-255.png"
    briefing_upload = "6406868784A31B5B"
    briefing_palettes = ("C7718B80FD3E1185", "8EA415BE1C8CF65E", "84785383870A1486")
    briefing_variants = {}
    for semi in (False, True):
        briefing_variants.update(packed_variants(tim_dir / "W_MES.TIM", 1, briefing_upload,
                                                 briefing_palettes, semitransparent=semi))
    targets = (
        ("F599271AE8C30811", (320, 240), title_screen, {}),
        ("17FAC7112EA5B272", (256, 216), mode_atlas, {}),
        ("7A8E8AC87388FF57", (176, 104), memory_card, {}),
        ("A4E7A14D76276FD0", (232, 192), name_banner,
         packed_variants(tim_dir / "NAMEE.TIM", 1, "A4E7A14D76276FD0", name_palettes)),
        ("9F3DDEFED6A65324", (256, 240), free_mode,
         packed_variants(tim_dir / "FREE.TIM", 1, "9F3DDEFED6A65324", ("7CB0F98E291D9225",))),
        ("30D4BEA33BB38122", (320, 240), card_trade, {trade_key: native_trade}),
        (briefing_upload, (144, 56), briefing_map_labels, briefing_variants),
        ("79154A56B51A7D00", (320, 240), battle_result,
         result_variants(tim_dir / "W_MES2.TIM", 2, "79154A56B51A7D00", "5B530EA479C453E2")),
        ("9AAE8862C1D40981", (320, 240), battle_result,
         result_variants(tim_dir / "W_MES2.TIM", 1, "9AAE8862C1D40981", "053F70E87E9361D7")),
    )
    for upload, dimensions, render, native_files in targets:
        variants = {}
        for name, path in sorted(dumps.items()):
            parts = name.split("-")
            if parts[2] != upload:
                continue
            with Image.open(path) as source:
                x, y = map(int, parts[5:7])
                right, bottom = x + source.width, y + source.height
                if render in (mode_atlas, name_banner, free_mode):
                    # The menu also uploads the already-English PUSH START
                    # strip by itself. Its rectangle contains no edits.
                    if (x, y, source.width, source.height) == (96, 128, 136, 16):
                        continue
                    if right > dimensions[0] or bottom > dimensions[1]:
                        continue
                elif x or y or source.width != dimensions[0] or bottom not in (dimensions[1] - 1, dimensions[1]):
                    continue
                variants[name] = (source.convert("RGBA"), (x, y, right, bottom))
        count = len(variants)
        # Complete CLUT keys can also match partial draw queries.
        for name, native in native_files.items():
            variants.setdefault(name, (native, (0, 0, *dimensions)))
        if not variants:
            parser.error(f"No {dimensions} texture dumps found for {upload}")
        full_images = [image for image, _ in variants.values() if image.size == dimensions]
        reference = max(full_images, key=average_light, default=None)
        if reference is None:
            parser.error(f"Missing the full {dimensions} reference for {upload}")
        output.mkdir(parents=True, exist_ok=True)
        for name, (original, box) in variants.items():
            max_light = average_light(reference.crop(box))
            ratio = min(1, average_light(original) / max_light) if max_light else 0
            edited = Image.new("RGBA", dimensions)
            edited.paste(original, box[:2])
            if render is title_screen:
                render(edited, reference, ratio)
            else:
                render(edited, ratio, font)
            edited.crop(box).save(output / name)
        print(f"{render.__name__}: {count} dumps, {len(variants)} replacements")
    print(f"Replacements: {output}")


if __name__ == "__main__":
    main()
