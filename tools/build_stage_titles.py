"""Build English overlays for the stage opening captions."""

import csv
import hashlib

from PIL import Image

from build_ui_textures import PACK, ROOT, average_light, faded, text_layer
from packed_ui import packed_texture, paletted_image

CAMPAIGN = (
    "Training", "First Battle", "Front Line", "The Unseen Enemy",
    "Mountain of the Gods", "Across the Lake", "Recon Unit", "Ruins Base",
    "Wall of Western Europa", "Enemy Raid", "Irvine the Outlaw", "Barricade",
    "Destroy the Ogre", "Death Stinger Rampage", "Break the Encirclement", "Hold to the Death",
    "Road to GaiGalos", "Strike the Supply Unit", "Wild Zoids", "Sea Route",
    "Lost Ruins", "Time Limit", "Guardian", "Final Mission",
    "Training", "Declaration of War", "First Strike", "Lost Technology",
    "Red River", "Imperial Capital GaiGalos", "Pursuit", "Land Blockade",
    "Stronghold", "Intelligence Unit", "Mountain Zone", "Ambush",
    "Destroy Death Saurer!", "Schwarz Returns", "Activation", "Last Land",
    "Surprise Attack", "Recon Unit Approaching", "Rare Hertz", "Brachios Assault",
    "Treacherous Road", "Landing", "Decisive Battle", "Prologue",
)
FREE = ("Ocean World", "Island Park", "Rocky Area", "Forest Lake",
        "Title Logo", "Ancient", "Tightrope", "Octagon")
ARCHIVE_SHA256 = "ffee8a8970e831be11d356be5f222e3933383cf3f251141ce61d01359f72476d"


def render(base, title, ratio, training_footer):
    ink = faded((255, 255, 255, 255), ratio)
    edge = (0, 0, 0, 0)
    base.paste((0, 0, 0, 0), (0, 30, 256, min(72, base.height)))
    base.alpha_composite(text_layer(title.upper(), (252, 34), "timesbi.ttf", 27, ink, edge), (2, 34))
    if training_footer and base.height > 72:
        base.paste((0, 0, 0, 0), (0, 72, 256, base.height))
        footer = text_layer("TRAINING", (250, 34), "timesbi.ttf", 26, ink, edge)
        base.alpha_composite(footer, (3, 74))
    return base


def main():
    data = (ROOT / "extracted/TIM/ST.TIM").read_bytes()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("The stage texture keys were indexed for a different archive")
    with (ROOT / "analysis/STAGE_TEXTURE_KEYS.csv").open(encoding="utf-8") as source:
        keys = list(csv.DictReader(source))
    titles = CAMPAIGN + FREE + FREE
    if len(keys) != len(titles):
        raise ValueError("Stage key and caption counts differ")
    output = PACK / "replacements"
    output.mkdir(parents=True, exist_ok=True)
    for index, (key, title) in enumerate(zip(keys, titles)):
        words, height, p8, pixels, palettes = packed_texture(data, index)
        if (int(key["index"]), words, height, p8) != (index, 64, 112, False):
            raise ValueError(f"Unexpected stage texture at {index}")
        source = paletted_image((256, 112), pixels, palettes[:32], p8=False, semitransparent=True)
        upload, palette = key["upload_hash"], key["palette_hash"]
        prefix = f"texupload-STP4-{upload}"
        name = f"{prefix}-{palette}-64x112-0-0-256x112-P0-15.png"
        render(source.copy(), title, 1, index < len(CAMPAIGN)).save(output / name)
        for path in (PACK / "dumps").glob(f"{prefix}-*-64x112-0-0-256x*-P0-15.png"):
            with Image.open(path) as dump:
                if dump.height not in (72, 112):
                    continue
                frame = dump.convert("RGBA")
            reference = source.crop((0, 0, 256, frame.height))
            ratio = min(1.0, average_light(frame) / average_light(reference))
            render(frame, title, ratio, index < len(CAMPAIGN)).save(output / path.name)
    print(f"Rendered {len(set(key['upload_hash'] for key in keys))} stage captions and captured fades.")


if __name__ == "__main__":
    main()
