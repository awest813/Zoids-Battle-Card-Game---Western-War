"""Export both languages in card display order, including short fragments."""

import csv
import tomllib
from collections import defaultdict
from pathlib import Path

from card_catalog import card_records, cep_rule_indices
from card_text_table import EXE, RAM_BASE, card_text_slots

with open("analysis/TEXT_TRACKER.csv", encoding="utf-8") as tracker:
    ids = {int(row["ram_addr"], 16): row["id"] for row in csv.DictReader(tracker)}

english = {}
for name in ("zoids.pointer_pending.toml", "zoids.card_short.toml"):
    with open(Path("translations") / name, "rb") as table:
        for entry in tomllib.load(table)["entry"]:
            for address in entry.get("ptr_addrs", []):
                english[int(address, 0), entry["src_addr"]] = entry["en"]

executable = EXE.read_bytes()
effects = defaultdict(list)
for card, slot, address, source in card_text_slots(executable):
    offset = source - RAM_BASE
    end = executable.index(b"\0", offset)
    japanese = executable[offset:end].decode("shift_jis")
    translation = english.get((address, source), "[MISSING]")
    label = ids.get(source, f"{source:#010x}")
    effects[card].append((slot, label, japanese, translation))

output = Path("work/card_effects_display.txt")
cards_by_rule = defaultdict(list)
rules = cep_rule_indices(executable)
for kind, index, _, name, _ in card_records():
    if kind == "cep":
        cards_by_rule[rules[index]].append(f"CEP {index} {name}")
with output.open("w", encoding="utf-8") as report:
    for index, rows in effects.items():
        uses = ", ".join(cards_by_rule[index]) or "no CEP card mapping"
        report.write(f"=== RULE RECORD {index} / {uses} ===\n")
        for slot, label, japanese, translation in rows:
            report.write(f"{slot}\t{label}\t{japanese}\t{translation}\n")
        report.write("\n")
print(f"{len(effects)} rule records in ascending screen-row order: {output}")
