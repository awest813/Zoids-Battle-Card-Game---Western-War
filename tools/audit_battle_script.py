"""Find English lines exceeding the original battle script panel width."""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from battle_script import dialogue_groups
from card_text_table import EXE
from translations_objectives import OBJECTIVE_CELLS


def script_rows(executable, tracker, followup):
    """Read recognized opcode 0x12 groups followed by the selected command."""
    sources = {}
    for address, next_opcode, lines in dialogue_groups(executable):
        if next_opcode != followup or any(source not in tracker for source in lines):
            continue
        for source in lines:
            sources.setdefault(source, address)
    for source, group in sources.items():
        yield tracker[source], group


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", action="store_true", help="Write details for every overlong row")
    parser.add_argument("--choices", action="store_true", help="Audit prompts followed by a Yes/No choice")
    args = parser.parse_args()
    with Path("analysis/TEXT_TRACKER.csv").open(encoding="utf-8", newline="") as inventory:
        tracker = {int(row["ram_addr"], 16): row for row in csv.DictReader(inventory)}
    lines = list(script_rows(EXE.read_bytes(), tracker, 0x13 if args.choices else 6))
    oversize = [(row, group) for row, group in lines if len(row["english"]) > OBJECTIVE_CELLS]
    if args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(("id", "category", "script_address", "cells", "english"))
        for row, group in sorted(oversize, key=lambda item: item[0]["id"]):
            writer.writerow((row["id"], row["category"], f"{group:#010x}",
                             len(row["english"]), row["english"]))
    else:
        counts = defaultdict(int)
        for row, _ in oversize:
            counts[row["category"]] += 1
        print(f"{len(oversize)} of {len(lines)} recognized script rows exceed {OBJECTIVE_CELLS} cells.")
        for category, count in sorted(counts.items()):
            print(f"{category}: {count}")


if __name__ == "__main__":
    main()
