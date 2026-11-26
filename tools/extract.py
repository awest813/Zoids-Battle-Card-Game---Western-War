"""Extract files from the Zoids PSX image using psxdisc."""
import os
import sys
import psxdisc

BIN = r"Zoids - Battle Card Game - Seihou Tairiku Senki (Japan).bin"
OUT = r"extracted"

disc = psxdisc.Disc(BIN)
pvd = disc.read_sector(16, 1)
root = psxdisc.parse_record(pvd[156:156 + 255])
entries = psxdisc.walk(disc, root["lba"], root["size"])

for e in entries:
    if e["dir"]:
        continue
    dest = os.path.join(OUT, *e["path"].split("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) == e["size"]:
        continue
    data = disc.read_sector(e["lba"], (e["size"] + 2047) // 2048)[:e["size"]]
    with open(dest, "wb") as f:
        f.write(data)
    print(f"{e['size']:>10} {e['path']}")
print("done")