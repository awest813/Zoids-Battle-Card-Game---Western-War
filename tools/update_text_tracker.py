"""Fill the master TEXT_TRACKER.csv from PHASE2_TRANSLATIONS.csv."""
import csv

from translations_menu import KEYPAD_LAYOUT_IDS

tracker_path = "analysis/TEXT_TRACKER.csv"
trans_path = "analysis/PHASE2_TRANSLATIONS.csv"

trans = {r["id"]: r for r in csv.DictReader(open(trans_path, encoding="utf-8"))}
rows = list(csv.DictReader(open(tracker_path, encoding="utf-8")))
fields = list(rows[0].keys())

done = 0
for r in rows:
    t = trans.get(r["id"])
    if not t:
        if r["id"] in KEYPAD_LAYOUT_IDS:
            r["status"] = "input_layout"
            r["notes"] = "Original input keys retained. The English launcher opens the Latin page first."
        elif not r.get("english"):
            r["status"] = "todo"
        continue
    r["english"] = t["english"]
    r["status"] = "translated"
    method = t["method"]
    note = r.get("notes", "")
    if method == "inplace":
        note = note.replace("patch record in place", "pointer redirection")
        if "pointer redirection" not in note:
            note = (note + "; pointer redirection").strip("; ")
    elif method == "hash":
        if "hash" not in note:
            note = (note + "; hash substitution").strip("; ")
    r["notes"] = note
    done += 1

with open(tracker_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"updated {done} rows in {tracker_path}")
print(f"original keypad rows: {sum(r['status'] == 'input_layout' for r in rows)}")
print(f"remaining without English or keypad disposition: {sum(r['status'] == 'todo' for r in rows)}")
