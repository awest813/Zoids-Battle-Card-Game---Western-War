"""Decode the texture entries used by the Zoids UI packs."""

import struct

from PIL import Image


def decompress(data):
    # The game's decoder at 0x80034728 uses an LSB-first LZSS flag byte,
    # a 4 KiB ring and 3-to-18-byte references.
    window = bytearray(4096)
    cursor = 0xFEE
    source = iter(data)
    decoded = bytearray()
    for flags in source:
        for bit in range(8):
            value = next(source, None)
            if value is None:
                return bytes(decoded)
            if flags & (1 << bit):
                values = (value,)
            else:
                marker = next(source, None)
                if marker is None:
                    return bytes(decoded)
                offset = value | ((marker & 0xF0) << 4)
                count = 3 + (marker & 0xF)
                values = (window[(offset + i) & 0xFFF] for i in range(count))
            for value in values:
                decoded.append(value)
                window[cursor] = value
                cursor = (cursor + 1) & 0xFFF
    return bytes(decoded)


def packed_texture(data, index):
    table_size, = struct.unpack_from("<I", data)
    if table_size < 8 or table_size % 4 or table_size > len(data):
        raise ValueError("Invalid texture offset table")
    offsets = struct.unpack_from(f"<{table_size // 4}I", data)
    start, end = offsets[index:index + 2]
    flags, words, height = struct.unpack_from("<IHH", data, start)
    pixels = start + 8
    if flags & 0x80:
        length, = struct.unpack_from("<H", data, pixels)
        payload = decompress(data[pixels + 2:pixels + 2 + length])
    else:
        payload = data[pixels:end]
    pixel_bytes = words * height * 2
    return words, height, bool(flags & 0x10), payload[:pixel_bytes], payload[pixel_bytes:]


def paletted_image(dimensions, pixels, palette, *, p8, semitransparent=False):
    if not p8:
        pixels = bytes(index for word in pixels for index in (word & 15, word >> 4))
    image = Image.frombytes("P", dimensions, pixels)
    rgba = []
    for (word,) in struct.iter_unpack("<H", palette):
        rgb = [(value << 3) | (value >> 2) for value in ((word >> shift) & 31 for shift in (0, 5, 10))]
        alpha = 0 if not word else 143 if semitransparent and word & 0x8000 else 255
        rgba.extend((*rgb, alpha))
    image.putpalette(bytes(rgba), rawmode="RGBA")
    return image.convert("RGBA")
