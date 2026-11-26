"""Audit translation tables, TOML metadata, and card text coverage."""
import csv
import re
import tomllib
from collections import Counter

from battle_script import short_dialogue_slots
from card_catalog import zoid_label_slots
from card_text_table import EXE, RAM_BASE, card_text_slots
from translations_dialogue_short import SHORT_DIALOGUE
from translations_objectives import OBJECTIVES, fits_objective

print("== TEXT_TRACKER ==")
rows = list(csv.DictReader(open("analysis/TEXT_TRACKER.csv", encoding="utf-8")))
print("rows", len(rows))
ids = [r["id"] for r in rows]
print("duplicate ids", [i for i, n in Counter(ids).items() if n > 1])
translated = [r for r in rows if r["status"] == "translated"]
layout = [r for r in rows if r["status"] == "input_layout"]
remaining = [r for r in rows if r["status"] not in ("translated", "input_layout")]
print("translated", len(translated), "input layout", len(layout), "remaining", len(remaining))

jp_re = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
token_re = re.compile(r"[@αβγδ]")
empty, jp_left, too_long = [], [], []
for r in translated:
    en = r["english"]
    if not en.strip():
        empty.append(r["id"])
    if jp_re.search(en):
        jp_left.append((r["id"], en))
    # flag very long story/UI lines (not card fragments)
    if r["category"] in ("story", "ui", "system") and len(en) > 44:
        too_long.append((r["id"], len(en), en))
print("empty en", empty[:20], "count", len(empty))
print("Japanese left in en", len(jp_left), jp_left[:10])
print("very long lines", len(too_long))
for x in too_long[:15]:
    print("  ", x)

print("\n== category counts ==")
print(dict(Counter(r["category"] for r in translated)))
print("remaining by category", dict(Counter(r["category"] for r in remaining)))

print("\n== TOML ==")
live_files = (
    "translations/zoids.phase2_hash.toml",
    "translations/zoids.pointer_pending.toml",
    "translations/zoids.card_short.toml",
)
executable = EXE.read_bytes()
covered = set()
objective_addresses = {int(row["ram_addr"], 16): row["id"] for row in rows
                       if row["id"] in OBJECTIVES}
objective_entries = set()
errors = bool(empty or jp_left or remaining or len(ids) != len(set(ids)))
for row in translated:
    source_tokens = Counter(token_re.findall(row["japanese"].replace("＠", "@")))
    if source_tokens and source_tokens != Counter(token_re.findall(row["english"])):
        print(f"  {row['id']} dropped or changed a dialogue token")
        errors = True
for f in ("translations/zoids.master.toml", *live_files):
    with open(f, "rb") as table:
        d = tomllib.load(table)["entry"]
    no_ptr = [e for e in d if "ptr_addrs" not in e]
    no_src = [e for e in d if "src_addr" not in e]
    no_pad = [e for e in d if "pad" not in e]
    ram = [e for e in d if "ram_addr" in e]
    bad_addrs = []
    for e in d:
        objective = objective_addresses.get(e.get("src_addr"))
        if f in live_files and objective:
            objective_entries.add(objective)
            if not fits_objective(e.get("en", "")):
                print(f"  {objective} exceeds the battle panel's text buffer in {f}")
                errors = True
        for a in e.get("ptr_addrs", []):
            slot_address = int(a, 0)
            if not (0x80000000 <= slot_address <= 0x801FFFFC) or slot_address % 4:
                bad_addrs.append((e.get("src_jp", "")[:20], a))
            elif f in live_files and e.get("en") and "src_addr" in e:
                source = e["src_addr"]
                offset = source - RAM_BASE
                source_bytes = bytes.fromhex(e["src_hex"])
                if executable[offset:offset + len(source_bytes)] == source_bytes:
                    covered.add((slot_address, source))
    errors |= bool(ram or bad_addrs)
    print(f, "entries", len(d), "en", sum(bool(e.get("en")) for e in d),
          "no_ptr", len(no_ptr), "no_src", len(no_src), "no_pad", len(no_pad),
          "ram_addr", len(ram), "bad_ptr", len(bad_addrs))
    if bad_addrs[:3]:
        print("   bad sample", bad_addrs[:3])

missing_objectives = OBJECTIVES.keys() - objective_entries
print("\n== battle objectives ==")
print("checked", len(objective_entries), "uncovered", len(missing_objectives))
if missing_objectives:
    print("  missing objective rows", sorted(missing_objectives))
    errors = True

print("\n== card records ==")
slots = list(card_text_slots(executable))
missing = [(card, slot, source) for card, slot, address, source in slots
           if (address, source) not in covered]
print("card text slots", len(slots), "uncovered", len(missing))
for card, slot, source in missing:
    offset = source - RAM_BASE
    end = executable.find(b"\0", offset)
    japanese = executable[offset:end].decode("shift_jis", "replace")
    print(f"  card {card} slot {slot} {source:#010x} {japanese!r}")
zoid_slots = list(zoid_label_slots(executable))
for kind in ("type", "ability"):
    slots = [(address, source) for group, address, source in zoid_slots if group == kind]
    missing_labels = [(address, source) for address, source in slots if (address, source) not in covered]
    print(f"Zoid {kind} slots", len(slots), "uncovered", len(missing_labels))
    for address, source in missing_labels:
        print(f"  slot {address:#010x}, source {source:#010x}")
    errors |= bool(missing_labels)

print("\n== short dialogue outside the tracker ==")
short_sources = {}
checked_short = 0
missing_short = []
for address, source in short_dialogue_slots(executable, {int(row["ram_addr"], 16) for row in rows}):
    if source not in short_sources:
        offset = source - RAM_BASE
        short_sources[source] = executable[offset:executable.index(b"\0", offset)].decode("shift_jis")
    if short_sources[source] in SHORT_DIALOGUE:
        checked_short += 1
        if (address, source) not in covered:
            missing_short.append(address)
print("translated pointer slots", checked_short, "uncovered", len(missing_short))
remaining_short = sorted(set(short_sources.values()) - SHORT_DIALOGUE.keys())
print("remaining sources", len(remaining_short), remaining_short)
for address in missing_short:
    print(f"  slot {address:#010x}")
for japanese, english in SHORT_DIALOGUE.items():
    if Counter(token_re.findall(japanese.replace("＠", "@"))) != Counter(token_re.findall(english)):
        print(f"  short dialogue changed a token in {japanese!r}")
        errors = True
errors |= bool(missing_short or remaining_short)
raise SystemExit(1 if errors or missing else 0)
