"""Regression check: the v1 and v2 cases through script 0.2.0 and the current script (no model, no cost).

Written after the 0.3.0 change, to test the second expectation in PREREGISTRATION.md: on the
v1 and v2 cases, the current script flags everything 0.2.0 flags. Each v1 sentence and each v2
draft item is checked against its gold quotes.

Run from the project root:  python eval/v3/regression.py   (writes eval/v3/results/regression.md)
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = {
    "0.2.0": ROOT / "eval" / "v2" / "frozen" / "check_evidence.py",
    "current": ROOT / "skills" / "evidence-check" / "scripts" / "check_evidence.py",
}


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(f"ce_{name.replace('.', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def v1_claims():
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    names = cases["sources"]
    for draft in cases["drafts"]:
        for n, s in enumerate(draft["sentences"], 1):
            yield s["type"], {"id": f'{draft["id"]}-{n}', "text": s["text"],
                              "evidence": [{"source": names[k], "quote": q} for k, q in s["gold"]]}


def v2_claims():
    cases = json.loads((ROOT / "eval" / "v2" / "cases.json").read_text(encoding="utf-8"))
    src = {name[:3]: name for name in cases["sources"]}
    for draft in cases["drafts"]:
        for n, item in enumerate(draft["items"], 1):
            yield item.get("type", "supported"), {"id": f'{draft["id"]}-{n}', "text": item["markers"][0],
                                                   "evidence": [{"source": src[k], "quote": q} for k, q in item["gold"]]}


ROUNDS = (("v1", ROOT / "eval" / "sources", v1_claims), ("v2", ROOT / "eval" / "v2" / "sources", v2_claims))


def main():
    modules = {name: load_script(name, path) for name, path in SCRIPTS.items()}
    lines = ["# Regression check: v1 and v2 cases, script 0.2.0 and current", "",
             'Each sentence or draft item is checked against its gold quotes. "Flagged" means any result other than supported.', ""]
    changed = []
    for label, folder, claims in ROUNDS:
        sources = {name: m.load_sources([str(folder)]) for name, m in modules.items()}
        counts = Counter()
        for kind, claim in claims():
            status = {name: m.check_claim(claim, sources[name])["status"] for name, m in modules.items()}
            counts[(kind, "n")] += 1
            for name in modules:
                counts[(kind, name)] += status[name] != "supported"
            if status["0.2.0"] != status["current"]:
                changed.append(f'| {label} {claim["id"]} | {kind} | {status["0.2.0"]} | {status["current"]} | {claim["text"]} |')
        kinds = sorted({k for k, _ in counts}, key=lambda k: (k != "supported", k))
        lines += [f"## {label}", "", "| Type | Items | Flagged by 0.2.0 | Flagged by current |", "|---|---|---|---|"]
        lines += [f"| {k} | {counts[(k, 'n')]} | {counts[(k, '0.2.0')]} | {counts[(k, 'current')]} |" for k in kinds]
        lines.append("")
    lines += ["## Items whose result changed", ""]
    lines += ["| Item | Type | 0.2.0 | Current | Text |", "|---|---|---|---|---|"] + changed if changed else ["None."]
    out = ROOT / "eval" / "v3" / "results" / "regression.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT).as_posix()}; {len(changed)} item(s) changed")


if __name__ == "__main__":
    main()
