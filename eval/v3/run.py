"""Script-only check of check_evidence.py on the v3 cases: no model, no cost.

Runs the cases through two versions of the script, the one frozen for the v2 run
(eval/v2/frozen/check_evidence.py, 0.2.0) and the current one, and writes a table
of what each version passes and flags.

Run from the project root:
  python eval/v3/run.py --check   # every quote is in its source, every id is unique
  python eval/v3/run.py           # writes eval/v3/results/script-only.md
"""
import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "eval" / "v3"
SCRIPTS = {
    "0.2.0": ROOT / "eval" / "v2" / "frozen" / "check_evidence.py",
    "current": ROOT / "skills" / "evidence-check" / "scripts" / "check_evidence.py",
}
KIND_ORDER = ["correct", "wrong", "limit"]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(f"ce_{name.replace('.', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases():
    return json.loads((V3 / "cases.json").read_text(encoding="utf-8"))["cases"]


def run(module, cases):
    sources = module.load_sources([str(V3 / "sources")])
    return {c["id"]: module.check_claim(c, sources) for c in cases}


def check_cases(cases):
    module = load_script("current", SCRIPTS["current"])
    sources = module.load_sources([str(V3 / "sources")])
    errors = []
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case ids")
    for c in cases:
        if c["kind"] not in KIND_ORDER:
            errors.append(f'{c["id"]}: unknown kind {c["kind"]}')
        for e in c["evidence"]:
            src = module.resolve_source(sources, e["source"])
            if src is None or not src.find(e["quote"])[0]:
                errors.append(f'{c["id"]}: quote not found in {e["source"]}')
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate the cases only")
    args = ap.parse_args(argv)
    cases = load_cases()
    errors = check_cases(cases)
    if args.check or errors:
        print("\n".join(errors) if errors else f"cases OK: {len(cases)} claims, " + ", ".join(
            f"{n} {k}" for k, n in Counter(c["kind"] for c in cases).items()))
        return 1 if errors else 0

    results = {name: run(load_script(name, path), cases) for name, path in SCRIPTS.items()}
    flagged = {name: {cid: r["status"] != "supported" for cid, r in res.items()} for name, res in results.items()}

    lines = ["# v3 script-only check", "",
             f"{len(cases)} claims from `eval/v3/cases.json`, written before the script change. "
             "A correct claim should pass; a wrong claim (a changed number) must be flagged; "
             "a limit claim is true but states a number the document does not, and is flagged on purpose.", "",
             "| Rule | Correct claims passed (0.2.0 → current) | Wrong claims flagged (0.2.0 → current) | Limit claims flagged |",
             "|---|---|---|---|"]
    by_rule = defaultdict(list)
    for c in cases:
        by_rule[c["rule"]].append(c)
    totals = Counter()
    for rule, group in by_rule.items():
        cells = []
        for kind, want_flag in (("correct", False), ("wrong", True)):
            members = [c for c in group if c["kind"] == kind]
            if not members:
                cells.append("—")
                continue
            old = sum(flagged["0.2.0"][c["id"]] == want_flag for c in members)
            new = sum(flagged["current"][c["id"]] == want_flag for c in members)
            totals[(kind, "old")] += old
            totals[(kind, "new")] += new
            totals[(kind, "n")] += len(members)
            cells.append(f"{old}/{len(members)} → {new}/{len(members)}")
        limits = [c for c in group if c["kind"] == "limit"]
        if limits:
            new = sum(flagged["current"][c["id"]] for c in limits)
            totals[("limit", "new")] += new
            totals[("limit", "n")] += len(limits)
            cells.append(f"{new}/{len(limits)}")
        else:
            cells.append("—")
        lines.append(f"| {rule} | " + " | ".join(cells) + " |")
    lines.append(f"| **Total** | **{totals[('correct', 'old')]}/{totals[('correct', 'n')]} → {totals[('correct', 'new')]}/{totals[('correct', 'n')]}** "
                 f"| **{totals[('wrong', 'old')]}/{totals[('wrong', 'n')]} → {totals[('wrong', 'new')]}/{totals[('wrong', 'n')]}** "
                 f"| **{totals[('limit', 'new')]}/{totals[('limit', 'n')]}** |")

    lines += ["", "## Every claim", "",
              "| ID | Kind | Claim | 0.2.0 | Current | Missing numbers (current) |", "|---|---|---|---|---|---|"]
    for c in cases:
        old, new = results["0.2.0"][c["id"]], results["current"][c["id"]]
        lines.append(f'| {c["id"]} | {c["kind"]} | {c["text"]} | {old["status"]} | {new["status"]} | '
                     f'{", ".join(new["missing_numbers"]) or "—"} |')
    out = V3 / "results" / "script-only.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
