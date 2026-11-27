"""Build the English lettering for the five ending-credit texture pages."""

import hashlib

from PIL import Image, ImageDraw, ImageFont

from build_ui_textures import PACK, ROOT
from packed_ui import packed_texture, paletted_image


ARCHIVE_SHA256 = "a3da5e7c374c4cf2bfccad2da709439bf44bc18893bdaddd1e5eed7d5c2a5cb9"
PALETTE = "AB5B1C149C6E3DE2"
UPLOADS = (
    "35C7DD1091D29CB6", "27050DAF75F37962", "247647ADCD997211",
    "7BD154F28D5BF72E", "D9888835697358CC",
)

# Each pair follows the two columns of one texture. Uppercase rows are roles,
# except for the original Latin labels that are left in place.
COLUMNS = (
    ((6, "Zoids Battle Card Game"), (21, "Western Continental War"),
     (79, "SR. EXECUTIVE PRODUCER"), (96, "Kantaro Tomiyama"),
     (126, "EXECUTIVE PRODUCER"), (144, "Shigeki Yanagisawa"),
     (175, "GENERAL MANAGER"), (192, "Shunji Kamio"),
     (223, "MANAGER"), (240, "Toshihiro Morioka")),
    ((14, "ASSISTANT MANAGER"), (32, "Suguru Yokota"),
     (63, "PRODUCER"), (81, "Taiji Koyama"),
     (111, "MARKETING LEAD"), (129, "Toshihiro Morioka"),
     (159, "MARKETING"), (176, "Yasujiro Ito"), (201, "Fumihiko Ozawa"), (225, "Masaomi Kobayashi")),
    ((0, "PROMOTION"), (18, "Nasen Ishihara"), (47, "SALES PROMOTION"),
     (65, "Hiroyuki Ouchi"), (89, "Hiroyuki Usami"), (112, "Masayoshi Inose"),
     (137, "Izuru Ishida"), (161, "Takamitsu Miyazawa"), (184, "Tomohiro Ito"),
     (215, "DIRECTION"), (233, "Taro Sasahara")),
    ((6, "PLANNING"), (25, "Toshiyuki Miyazawa"), (54, "PROGRAMMING"),
     (73, "Jun Urashima"), (98, "Ken Masamura"), (121, "Junichi Watanabe"),
     (151, "GRAPHICS"), (169, "Masanori Kitsuta"), (193, "Takahide Nakayama"),
     (218, "Reiko Hirota"), (241, "Kouichi Mashimo")),
    ((9, "Koji Ryusekidou"), (39, "3D GRAPHICS"), (57, "Seiichiro Kuroki"),
     (80, "Takahiro Asano"), (100, "(Will Co., Ltd.)"),
     (127, "SOUND"), (174, "CHARACTER DESIGN"), (192, "Makoto Mizobuchi"),
     (216, "Michiro Ueyama"), (240, "Hiroyuki Hataike")),
    ((30, "TOMY TD2"), (49, "Masahito Ujiie"), (72, "Nobuta Okino"),
     (97, "Naruko Nishikubo"), (120, "Hiroshi Hagiwara"), (144, "Miho Nii"),
     (169, "Kaname Matsuzawa"), (192, "Eiko Fujimoto"),
     (223, "ADVISER"), (240, "Takashi Nango")),
    ((15, "THANKS"), (32, "Tomy Zoids Team"), (56, "Yutaka Tajima"),
     (80, "Fumiaki Sonoda"), (104, "Hisanao Takahashi"), (128, "Norio Ogawara"),
     (153, "Masamichi Okutsu"), (177, "Haruki Osaki"),
     (207, "SPECIAL THANKS"), (225, "Shogakukan"), (241, "CoroCoro Comic Editors")),
    ((32, "Toshihiro Nakazawa"), (56, "Atsushi Fujii"), (86, "WITH SUPPORT FROM"),
     (104, "Shogakukan Production"), (128, "Mainichi Broadcasting"), (153, "JR East Marketing & Comms.")),
    ((143, "DEV. & PRODUCTION"), (161, "Natsume Co., Ltd."), (184, "Act Japan Co., Ltd.")),
    ((103, "PUBLISHING & SALES"), (121, "Tomy Co., Ltd.")),
)


def paint_column(image, column, index):
    left = (index % 2) * 128
    background = image.getpixel((left + 127, 0))
    for top, label in column:
        title = index == 0 and top < 32
        heading = title or label.isupper()
        height = 12 if heading else 17
        bottom = min(top + height, 256)
        image.paste(background, (left, max(0, top - 1), left + 128, bottom))
        color = (239, 33, 49) if title else (255, 166, 46) if heading else (32, 178, 244)
        face = "arialbd.ttf" if heading else "arial.ttf"
        for size in range(15 if not heading else 11, 7, -1):
            font = ImageFont.truetype(face, size)
            bounds = font.getbbox(label)
            if bounds[2] - bounds[0] <= 118 and bounds[3] - bounds[1] <= bottom - top:
                break
        else:
            raise ValueError(f"Credit will not fit column {index}: {label}")
        ImageDraw.Draw(image).text((left + 8 - bounds[0], top - bounds[1]), label, font=font,
                                   fill=(*color, background[3]))


def main():
    data = (ROOT / "extracted/TIM/W_MES3.TIM").read_bytes()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("The credit texture keys were indexed for a different archive")
    output = PACK / "replacements"
    output.mkdir(parents=True, exist_ok=True)
    for index, upload in enumerate(UPLOADS):
        words, height, p8, pixels, palette = packed_texture(data, index + 1)
        if (words, height, p8, len(palette)) != (64, 256, False, 32):
            raise ValueError(f"Unexpected credits texture at {index + 1}")
        for mode in ("P4", "STP4"):
            image = paletted_image((256, 256), pixels, palette, p8=p8, semitransparent=mode == "STP4")
            for column in range(2 * index, 2 * index + 2):
                paint_column(image, COLUMNS[column], column)
            image.save(output / f"texupload-{mode}-{upload}-{PALETTE}-64x256-0-0-256x256-P0-15.png")
    print("Rendered English lettering for five ending-credit pages.")


if __name__ == "__main__":
    main()
