"""Record the verified card image and CEP rule relations in the tracker."""

import csv
from pathlib import Path

from build_card_faces import LIGER_ZERO_CARDS, REVIEWED_RULES, ZOID_SPECIAL
from card_catalog import card_records, cep_rule_indices, english_names
from card_text_table import EXE

tracker = Path("analysis/CARD_TRACKER.csv")
with tracker.open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    fields = reader.fieldnames
    rows = {(row["kind"], int(row["card_id"])): row for row in reader}

names = english_names()
rules = cep_rule_indices(EXE.read_bytes())
for kind, index, face, japanese, _ in card_records():
    row = rows[kind, index]
    row.update(jp_name=japanese, en_name=names[japanese], image_index=face,
               image_method="English lettering on original face and thumbnail",
               needs_generated_image="no")
    if kind == "cep":
        row.update(text_method=f"DAT name + CEP rule record {rules[index]}",
                   status="face_rendered_pending_review",
                   notes="Confirm rule fit and wording in the album.")
        if rules[index] in REVIEWED_RULES:
            row.update(status="face_rule_reviewed",
                       notes="English wording checked against the Japanese game text.")
    elif index in ZOID_SPECIAL:
        row.update(text_method="DAT name + printed special",
                   status="face_rendered_pending_review",
                   notes="English stat labels and printed special rendered.")
        if index in LIGER_ZERO_CARDS:
            row["notes"] = "English special wording rendered. Verify the preserved frontal melee bonus amount."
    else:
        row.update(text_method="DAT name + baked stat labels",
                   status="face_labels_rendered",
                   notes="Check any remaining Japanese in the printed special or stat icons.")

with tracker.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows.values())
print(f"Updated {len(rows)} card tracker rows.")
