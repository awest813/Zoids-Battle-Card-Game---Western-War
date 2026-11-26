"""Build the master translation TOML, pointer-redirection plan, and Phase 2 tables.

IMPORTANT: Zoids' memory-card text is corrupted by in-place `ram_addr` patches
(the game rewrites/expects the original record layout). The master table therefore
contains `src_addr` + `ptr_addr` metadata but NO `ram_addr`. Use:
  - zoids.phase2_hash.toml       safe hash-only test table
  - zoids.pointer_pending.toml   translations waiting for pointer redirection
  - zoids.master.toml            full inventory, no unsafe in-place patches
"""
import csv
import os
from collections import Counter, defaultdict

from card_catalog import card_records, english_names, zoid_label_slots
from card_text_table import EXE
from translations_memory import MEMORY, MEMORY_DISPLAY
from translations_tutorial import TUTORIAL
from translations_ui import UI
from translations_menu import MENU, MENU_DISPLAY, PACKED_MENU
from translations_story_open import STORY_OPEN
from translations_voice import VOICE
from translations_story_1 import STORY_1
from translations_story_2 import STORY_2
from translations_story_3 import STORY_3
from translations_story_4 import STORY_4
from translations_story_5 import STORY_5
from translations_story_6 import STORY_6
from translations_story_7 import STORY_7
from translations_story_8 import STORY_8
from translations_card_labels import CARD_LABELS, COMPACT_CARD_LABELS, ZOID_LABELS_OUTSIDE_TRACKER
from translations_card_text_1 import CARD_TEXT_1
from translations_card_text_2 import CARD_TEXT_2
from translations_card_text_3 import CARD_TEXT_3
from translations_card_text_4 import CARD_TEXT_4
from translations_card_names_2 import CARD_NAMES_2
from translations_polish import POLISH
from translations_objectives import OBJECTIVES, fits_objective

RAM_BASE = 0x8000F800
ALL_TR = {}
ALL_TR.update(MEMORY)
ALL_TR.update(TUTORIAL)
ALL_TR.update(UI)
ALL_TR.update(MENU)
ALL_TR.update(VOICE)
ALL_TR.update(STORY_OPEN)
ALL_TR.update(STORY_1)
ALL_TR.update(STORY_2)
ALL_TR.update(STORY_3)
ALL_TR.update(STORY_4)
ALL_TR.update(STORY_5)
ALL_TR.update(STORY_6)
ALL_TR.update(STORY_7)
ALL_TR.update(STORY_8)
ALL_TR.update(CARD_LABELS)
ALL_TR.update(CARD_TEXT_1)
ALL_TR.update(CARD_TEXT_2)
ALL_TR.update(CARD_TEXT_3)
ALL_TR.update(CARD_TEXT_4)
ALL_TR.update(CARD_NAMES_2)
ALL_TR.update(POLISH)  # last: shorten long story lines
ALL_TR.update(OBJECTIVES)


def toml_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def clean_visible(s):
    return s.rstrip("　")


tracker = list(csv.DictReader(open("analysis/TEXT_TRACKER.csv", encoding="utf-8")))
by_id = {r["id"]: r for r in tracker}
for text_id, english in OBJECTIVES.items():
    if text_id not in by_id or not fits_objective(english):
        raise ValueError(f"{text_id} does not fit the battle objective buffer")
for text_id, parts in PACKED_MENU.items():
    if "".join(japanese for japanese, _ in parts) != by_id[text_id]["japanese"]:
        raise ValueError(f"{text_id} packed label boundaries do not match the source")
missing = [k for k in ALL_TR if k not in by_id]
if missing:
    print("WARNING missing IDs:", missing)

HASH_SAFE_OVERRIDES = {"TXT-0003", "TXT-0066"}
# The English launcher rotates the existing Latin page to the front.
KEYPAD_LABEL_SLOTS = {"TXT-1892": "8001f38c", "TXT-1893": "8001f3ac"}
ALBUM_CATEGORY_IDS = {"TXT-1884", "TXT-1885", "TXT-1886", "TXT-1887"}
# DAT names also appear as standalone rule and roster labels in the EXE.
# Keep their dispatch spelling consistent when both tables know the same key.
COMPACT_CARD_NAMES = {name: COMPACT_CARD_LABELS.get(english, english.upper())
                      for name, english in english_names().items()}
for name, label in COMPACT_CARD_NAMES.items():
    if not label.isascii() or len(label) > 13:
        raise ValueError(f"{name} does not fit the compact card name field: {label}")
for row in tracker:
    if row["id"] in ALL_TR and row["japanese"] in COMPACT_CARD_NAMES:
        ALL_TR[row["id"]] = COMPACT_CARD_NAMES[row["japanese"]]

# Phase 2 worksheet
phase2 = []
for r in tracker:
    en = ALL_TR.get(r["id"], "")
    if not en:
        continue
    visible = clean_visible(r["japanese"])
    max_cells = int(r["max_fullwidth_cells"])
    fit = len(en) <= max_cells
    method = "hash" if r["id"] in HASH_SAFE_OVERRIDES else r["method"]
    phase2.append({
        "id": r["id"],
        "category": r["category"],
        "priority": r["priority"],
        "method": method,
        "offset": r["offset"],
        "record_addr": f"0x{int(r['offset'], 16) + RAM_BASE:08x}",
        "ptr_addr": r["primary_ptr_source"],
        "slot_bytes": r["slot_bytes"],
        "max_fullwidth_cells": max_cells,
        "japanese": r["japanese"],
        "english": en,
        "english_cells": len(en),
        "fit_inplace": "yes" if fit else "no",
        "status": "draft",
        "notes": ("hash-safe; no in-place patch" if method == "hash"
                  else "table-driven; use pointer redirection"),
    })

with open("analysis/PHASE2_TRANSLATIONS.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(phase2[0].keys()))
    w.writeheader()
    w.writerows(phase2)

# Pointer redirection plan
ptr_rows = list(csv.DictReader(open("analysis/text_pointer_map.csv", encoding="utf-8")))
ptrs_by_offset = defaultdict(list)
for p in ptr_rows:
    ptrs_by_offset[p["string_offset"]].append(p)

plan = []
for r in tracker:
    ptrs = ptrs_by_offset.get(r["offset"], [])
    if not ptrs:
        continue
    plan.append({
        "text_id": r["id"],
        "category": r["category"],
        "japanese": r["japanese"],
        "record_addr": f"0x{int(r['offset'], 16) + RAM_BASE:08x}",
        "ptr_count": len(ptrs),
        "ptr_ram_addrs": ";".join(p["ptr_ram_addr"] for p in ptrs),
        "slot_bytes": r["slot_bytes"],
        "max_fullwidth_cells": r["max_fullwidth_cells"],
        "english": ALL_TR.get(r["id"], ""),
    })

with open("analysis/POINTER_REDIRECT_PLAN.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(plan[0].keys()))
    w.writeheader()
    w.writerows(plan)

# Master TOML — metadata only, no ram_addr.
os.makedirs("translations", exist_ok=True)
master_lines = [
    "# Zoids master translation table (generated).",
    "# Metadata: src_addr = record VA, ptr_addr = pointer-table slot for redirection.",
    "# NO ram_addr: in-place patching corrupts this title's memory-card text.",
    "# en = \"\" means untranslated; the runtime skips empty entries.",
    "schema = 1",
    'default_lang = "en"',
    'langs = ["en"]',
    "",
]
safe_lines = [
    "# Hash-only safe table (argument-passed strings; no in-place patches).",
    "schema = 1",
    'default_lang = "en"',
    'langs = ["en"]',
    "",
]
pending_lines = [
    "# Table-driven translations waiting for pointer redirection.",
    "# These have ptr_addr metadata and no ram_addr; do not load until the",
    "# pointer-redirection path is implemented and verified.",
    "schema = 1",
    'default_lang = "en"',
    'langs = ["en"]',
    "",
]

for r in tracker:
    en = ALL_TR.get(r["id"], "")
    method = r["method"]
    if r["id"] in HASH_SAFE_OVERRIDES:
        method = "hash"
    visible = clean_visible(r["japanese"])
    if r["id"] in ALBUM_CATEGORY_IDS:
        visible = r["japanese"]
    raw = (visible if method == "hash" else r["japanese"]).encode("shift_jis")
    max_cells = int(r["max_fullwidth_cells"])
    ptr = KEYPAD_LABEL_SLOTS.get(r["id"], r["primary_ptr_source"])
    pad = "slot" if r["category"] in ("system", "menu") else "none"
    lines = [
        "[[entry]]",
        f'src_hex = "{raw.hex()}"',
        f'src_jp = {toml_quote(r["japanese"])}',
        f'src_addr = 0x{int(r["offset"], 16) + RAM_BASE:08x}',
        f'record_addr = 0x{int(r["offset"], 16) + RAM_BASE:08x}',
    ]
    if ptr:
        lines.append(f'ptr_addr = 0x{int(ptr, 16):08x}')
    ptr_addrs = sorted({p["ptr_ram_addr"] for p in ptrs_by_offset.get(r["offset"], [])})
    if r["id"] in KEYPAD_LABEL_SLOTS:
        ptr_addrs = [ptr]
    if ptr_addrs:
        lines.append("ptr_addrs = [" + ", ".join(f'"0x{a}"' for a in ptr_addrs) + "]")
    lines += [
        'term = "nul"',
        f'pad = "{pad}"',
        f'orig_w = {len(visible)}',
        f'en = {toml_quote(en)}',
        f'note = "{r["category"]} {method} max={max_cells}"',
        "",
    ]
    master_lines += lines
    if en and method == "hash":
        safe_lines += lines
    elif en and method == "inplace":
        pending_lines += lines

pending_lines += [
    "[[entry]]",
    'src_hex = "82bb82cc91bc"',
    'src_jp = "その他"',
    "src_addr = 0x800f6d98",
    'ptr_addrs = ["0x8001f36c"]',
    'term = "nul"',
    'pad = "none"',
    'en = "ABC"',
    'note = "English launcher Latin-first page caption"',
    "",
]

# The short strings near the end of retail data were outside the tracker scan.
executable = EXE.read_bytes()
added_labels = set()
tracked_sources = {int(row["ram_addr"], 16) for row in tracker}
for kind, slot, source in zoid_label_slots(executable):
    if source in tracked_sources:
        continue
    offset = source - RAM_BASE
    raw = executable[offset:executable.index(b"\0", offset)]
    japanese = raw.decode("shift_jis")
    added_labels.add(japanese)
    pending_lines += [
        "[[entry]]",
        f'src_hex = "{raw.hex()}"',
        f'src_jp = {toml_quote(japanese)}',
        f"src_addr = {source:#010x}",
        f'ptr_addrs = ["{slot:#010x}"]',
        'term = "nul"',
        'pad = "none"',
        f'en = {toml_quote(ZOID_LABELS_OUTSIDE_TRACKER[japanese])}',
        f'note = "Zoid {kind} outside static tracker"',
        "",
    ]
if added_labels != ZOID_LABELS_OUTSIDE_TRACKER.keys():
    raise ValueError("The retail Zoid label tables do not match the supplemental labels")

for japanese, english in (MEMORY_DISPLAY | MENU_DISPLAY).items():
    safe_lines += [
        "[[entry]]",
        f'src_hex = "{japanese.encode("shift_jis").hex()}"',
        f'src_jp = {toml_quote(japanese)}',
        'term = "nul"',
        f'en = {toml_quote(english)}',
        'note = "UI display string outside static tracker"',
        "",
    ]

displayed_names = set()
for _, _, _, japanese, _ in card_records():
    source = japanese.encode("shift_jis")
    if source in displayed_names:
        continue
    displayed_names.add(source)
    safe_lines += [
        "[[entry]]",
        f'src_hex = "{source.hex()}"',
        f'src_jp = {toml_quote(japanese)}',
        'term = "nul"',
        f'en = {toml_quote(COMPACT_CARD_NAMES[japanese])}',
        'note = "Exact DAT card name field. The compact font uses uppercase Latin."',
        "",
    ]

with open("translations/zoids.master.toml", "w", encoding="utf-8") as f:
    f.write("\n".join(master_lines))
with open("translations/zoids.phase2_hash.toml", "w", encoding="utf-8") as f:
    f.write("\n".join(safe_lines))
with open("translations/zoids.pointer_pending.toml", "w", encoding="utf-8") as f:
    f.write("\n".join(pending_lines))

cats = Counter(r["category"] for r in phase2)
print(f"phase2 translations: {len(phase2)} by category {dict(cats)}")
print("  hash-safe:", sum(1 for r in phase2 if r["method"] == "hash"))
print("  pointer-pending:", sum(1 for r in phase2 if r["method"] == "inplace"))
print(f"master entries: {len(tracker)}")
print(f"hash table entries: {safe_lines.count('[[entry]]')}")
print(f"pointer-pending entries: {pending_lines.count('[[entry]]')}")
print("wrote analysis/PHASE2_TRANSLATIONS.csv, analysis/POINTER_REDIRECT_PLAN.csv")
print("wrote translations/zoids.master.toml, zoids.phase2_hash.toml, zoids.pointer_pending.toml")
