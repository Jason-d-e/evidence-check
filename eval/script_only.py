"""Check the script alone, with no model involved and no cost.

Every sentence in cases.json is checked against its 'gold' quotes:
- supported sentences carry their correct quotes, so the script should pass all of them
  (anything else is a false alarm of the script itself);
- unsupported sentences carry the real sentence a careless checker would most likely cite,
  so this shows which kinds of error the script catches on its own.

Run from the project root:  python eval/script_only.py
"""
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ce", ROOT / "skills/evidence-check/scripts/check_evidence.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

cases = json.loads((ROOT / "eval/cases.json").read_text(encoding="utf-8"))
sources = ce.load_sources([str(ROOT / "eval/sources")])
names = cases["sources"]

rows, by_type = [], defaultdict(Counter)
for draft in cases["drafts"]:
    for n, s in enumerate(draft["sentences"], 1):
        claim = {"id": f'{draft["id"]}-{n}', "text": s["text"],
                 "evidence": [{"source": names[k], "quote": q} for k, q in s["gold"]]}
        r = ce.check_claim(claim, sources)
        flagged = r["status"] != "supported"
        by_type[s["type"]]["total"] += 1
        by_type[s["type"]]["flagged"] += flagged
        rows.append((claim["id"], s["type"], r["status"], ", ".join(r["missing_numbers"]), s["text"]))

lines = ["# Script-only check (gold quotes, no model)", "",
         "| Sentence type | Sentences | Flagged by the script |", "|---|---|---|"]
for t in ["supported", "number", "outdated", "invented", "contradiction"]:
    c = by_type[t]
    lines.append(f"| {t} | {c['total']} | {c['flagged']} |")
lines += ["", "| Sentence | Type | Script result | Missing numbers | Text |", "|---|---|---|---|---|"]
for row in rows:
    lines.append("| " + " | ".join(row) + " |")
out = "\n".join(lines) + "\n"
(ROOT / "eval/results/script-only.md").write_text(out, encoding="utf-8")
print("\n".join(lines[:9]))
for row in rows:
    if (row[1] == "supported") == (row[2] != "supported"):
        print("  attention:", row)
