"""Score a promptfoo results file from promptfooconfig.yaml. No model calls.

For each arm (plain, skill) two numbers are reported:
  - "model only": the model's own verdict per sentence;
  - "+ script":   a "supported" verdict is kept only if check_evidence.py passes the
                  model's quotes for that sentence (otherwise it counts as flagged).
"plain + script" shows what the script adds to an ordinary prompt; "skill + script"
is the full skill.

Usage (from the project root):  python eval/summarize.py eval/results/run-YYYY-MM-DD.json
Writes <file>.summary.md next to the results file.
"""
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ce", ROOT / "skills/evidence-check/scripts/check_evidence.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

TYPES = ["number", "outdated", "invented", "contradiction"]


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["results"]["results"]
    cases = json.loads((ROOT / "eval/cases.json").read_text(encoding="utf-8"))
    drafts = {d["id"]: d for d in cases["drafts"]}
    sources = ce.load_sources([str(ROOT / "eval/sources")])

    runs = defaultdict(list)  # (arm, draft) -> rows in order
    for r in rows:
        arm = (r.get("provider") or {}).get("label") or r.get("provider", {}).get("id")
        runs[(arm, r["vars"]["draft_id"])].append(r)

    stats = defaultdict(Counter)  # (arm, mode) -> counters
    cost, latency, errors, calls = Counter(), defaultdict(list), Counter(), Counter()
    quote_checks = defaultdict(Counter)
    misses = defaultdict(list)
    for (arm, draft_id), rs in sorted(runs.items()):
        draft = drafts[draft_id]
        for run_no, r in enumerate(rs, 1):
            calls[arm] += 1
            resp = r.get("response") or {}
            if resp.get("error") or not resp.get("output"):
                errors[arm] += 1
                continue
            cost[arm] += resp.get("cost") or 0
            latency[arm].append((resp.get("metadata") or {}).get("latency_ms") or r.get("latencyMs") or 0)
            try:
                out = json.loads(resp["output"]) if isinstance(resp["output"], str) else resp["output"]
            except json.JSONDecodeError:
                errors[arm] += 1
                continue
            by_id = {}
            for c in out.get("claims", []):
                by_id[str(c.get("id", "")).strip().rstrip(".")] = c
            for n, s in enumerate(draft["sentences"], 1):
                c = by_id.get(str(n))
                model_ok = bool(c) and c.get("verdict") == "supported"
                script_ok = False
                if model_ok:
                    ev = [e for e in c.get("evidence", []) if e.get("quote")]
                    res = ce.check_claim({"id": str(n), "text": s["text"], "evidence": ev}, sources)
                    script_ok = res["status"] == "supported"
                    quote_checks[arm][res["status"]] += 1
                for mode, ok in (("model", model_ok), ("script", script_ok)):
                    st = stats[(arm, mode)]
                    if c is None:
                        st["missing_lines"] += 1
                    if s["label"] == "supported":
                        st["supported_total"] += 1
                        st["false_alarm"] += not ok
                    else:
                        st["unsupported_total"] += 1
                        st["caught"] += not ok
                        st[f"caught_{s['type']}"] += not ok
                        st[f"total_{s['type']}"] += 1
                        if ok and mode == "script":
                            misses[arm].append(f"{draft_id}-{n} (run {run_no}, {s['type']}): {s['text']}")
                    st[f"lang_{draft['lang']}_total"] += 1
                    st[f"lang_{draft['lang']}_right"] += (ok == (s["label"] == "supported"))

    arms = sorted({a for a, _ in runs})
    lines = [f"# evidence-check eval: {Path(path).name}", ""]
    meta = next((r["response"].get("metadata") for r in rows if (r.get("response") or {}).get("metadata")), {}) or {}
    lines.append(f"Model {meta.get('model_served', '?')}, effort {meta.get('effort', '?')}, SKILL.md sha {meta.get('skill_sha', '?')}. "
                 f"Calls per arm: {', '.join(f'{a} {calls[a]}' for a in arms)}; failed calls: {', '.join(f'{a} {errors[a]}' for a in arms)}.")
    lines += ["", "| | " + " | ".join(f"{a} (model only) | {a} + script" for a in arms) + " |",
              "|---|" + "---|" * (2 * len(arms))]

    def cell(arm, mode, num, den):
        st = stats[(arm, mode)]
        return f"{st[num]}/{st[den]}"

    def row(label, num, den):
        cells = [cell(a, m, num, den) for a in arms for m in ("model", "script")]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    row("**Unsupported sentences flagged**", "caught", "unsupported_total")
    for t in TYPES:
        row(f"  {t}", f"caught_{t}", f"total_{t}")
    row("**Supported sentences wrongly flagged**", "false_alarm", "supported_total")
    row("English sentences judged right", "lang_en_right", "lang_en_total")
    row("Chinese sentences judged right", "lang_zh_right", "lang_zh_total")
    lines += ["", "| | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    lines.append("| Cost (all calls, USD) | " + " | ".join(f"{cost[a]:.4f}" for a in arms) + " |")
    lines.append("| Median latency per draft (s) | " + " | ".join(
        f"{sorted(latency[a])[len(latency[a]) // 2] / 1000:.1f}" if latency[a] else "-" for a in arms) + " |")
    lines.append("| Lines the model left out | " + " | ".join(str(stats[(a, 'model')]['missing_lines']) for a in arms) + " |")
    for a in arms:
        q = quote_checks[a]
        lines.append(f"| Script result on the model's \"supported\" lines ({a}) | " + ", ".join(f"{k} {v}" for k, v in q.most_common()) + " |" + " |" * (len(arms) - 1))
    lines += ["", "## Unsupported sentences that got through (+ script)", ""]
    for a in arms:
        lines.append(f"**{a}** ({len(misses[a])})")
        lines += [f"- {m}" for m in misses[a]] or ["- none"]
        lines.append("")
    out = "\n".join(lines)
    Path(path).with_suffix(".summary.md").write_text(out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
