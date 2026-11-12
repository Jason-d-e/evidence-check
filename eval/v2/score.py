"""evidence-check v2: check the cases, run the script alone, or score a run. No model calls.

Usage (from the project root):
  python eval/v2/score.py --check          validate cases.json (gold quotes, markers, perfect-oracle scores)
  python eval/v2/score.py --script-only    the script alone on every draft item's gold quotes
  python eval/v2/score.py RESULTS.json     score a promptfoo run; writes RESULTS.summary.md and RESULTS.outputs.json

Scoring rules (fixed before the run, see PREREGISTRATION.md):

Questions (Mode A). The answer is the list of claim texts the model returned.
  - reply type: status equals the expected one (answered / not_in_documents);
  - invented number: a number in the answer that appears in no source file and not in the question;
  - number outside the relevant passages: not in the question, not a year used in the sources, and not
    in the question's gold passages. These are listed in full for a person to review;
  - outdated value: the old value of an amended fact appears and the new one does not;
  - key facts: every token of the fact appears in the answer.
Drafts (Mode B). Each item has markers, short strings copied from the draft.
  - a claim covers the items whose marker is in its text; if none is, those whose marker is in its draft_text;
  - an error is caught when a flagged claim covers it; a correct fact is a false alarm when a flagged claim
    covers it and covers no error; an error is never extracted when no claim covers it.
"model only" uses the model's own output. "+ script" also runs check_evidence.py on every claim: in a
question, claims that fail are dropped; in a draft, a claim that fails counts as flagged.
"""
import argparse
import importlib.util
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("ce_v2", HERE / "frozen" / "check_evidence.py")
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)

CASES = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
SOURCES = ce.load_sources([str(HERE / "sources")])
SRC = {name[:3]: name for name in CASES["sources"]}
QUESTIONS = {q["id"]: q for q in CASES["questions"]}
DRAFTS = {d["id"]: d for d in CASES["drafts"]}
YEARS = {y for s in SOURCES.values() for y in re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", s.text)}
ALL_SOURCE_NUMBERS = set().union(*(ce.numbers_in(s.text, generous=True) for s in SOURCES.values()))
NUMBER_TOKEN = re.compile(r"^\d+(?:\.\d+)?$|^\d{1,2}:\d{2}$")
ARMS = ["plain", "skill-v0.1", "skill-v0.2"]
MODES = ["model", "script"]
DRAFT_TYPES = ["number", "outdated", "invented", "contradiction", "computed"]
# cases.json says "answer"; the output schema says "answered" (fixed after the run, see PREREGISTRATION.md).
STATUS_FOR = {"answer": "answered", "not_in_documents": "not_in_documents"}


def arm_of(row) -> str:
    """The arm name. promptfoo stored the label "skill" for both skill arms, so use the provider id
    (evidence-check-v2:plain, evidence-check-v2:skill-v0.1, ...), which is distinct (fixed after the run)."""
    provider = row.get("provider") or {}
    pid = provider.get("id") or ""
    return pid.split(":", 1)[1] if pid.startswith("evidence-check-v2:") else provider.get("label")


def norm(text: str) -> str:
    """Lower case, NFKC, unified quotes and dashes, no whitespace."""
    return re.sub(r"\s+", "", ce.normalize_with_map(unicodedata.normalize("NFC", text or ""))[0])


def canonical(token: str) -> str:
    if ":" in token:
        h, m = token.split(":")
        return f"{int(h)}:{m}"
    return ce._canonical(token)


def present(token, numbers, ntext) -> bool:
    for alt in token if isinstance(token, list) else [token]:
        if NUMBER_TOKEN.match(alt):
            if canonical(alt) in numbers:
                return True
        elif norm(alt) in ntext:
            return True
    return False


def all_present(tokens, numbers, ntext) -> bool:
    return all(present(t, numbers, ntext) for t in tokens)


def evidence_of(claim):
    return [e for e in claim.get("evidence") or [] if isinstance(e, dict) and e.get("quote")]


def script_status(claim) -> str:
    return ce.check_claim({"id": "c", "text": claim.get("text") or "", "evidence": evidence_of(claim)}, SOURCES)["status"]


def gold_numbers(q) -> set:
    out = ce.numbers_in(q["question"], generous=True) | YEARS
    for _, quote in q["gold"]:
        out |= ce.numbers_in(quote, generous=True)
    return out


# ---------------------------------------------------------------- questions

def score_answer(q, out, use_script):
    claims = [c for c in out.get("claims") or [] if isinstance(c, dict)]
    statuses = [script_status(c) for c in claims]
    kept = [c for c, s in zip(claims, statuses) if s == "supported"] if use_script else claims
    text = " ".join(c.get("text") or "" for c in kept)
    numbers, ntext = ce.numbers_in(text), norm(text)
    qnums = ce.numbers_in(q["question"], generous=True)
    return {
        "type_ok": out.get("status") == STATUS_FOR[q["expect"]],
        "invented": sorted(numbers - ALL_SOURCE_NUMBERS - qnums),
        "outside": sorted(numbers - gold_numbers(q)),
        "outdated": [o["name"] for o in q["outdated"]
                     if all_present(o["old"], numbers, ntext) and not all_present(o["new"], numbers, ntext)],
        "keys": [(k["name"], all_present(k["all"], numbers, ntext)) for k in q["key_facts"]],
        "claims": len(claims),
        "kept": len(kept),
        "script_passed": sum(s == "supported" for s in statuses),
        "text": text,
    }


# ---------------------------------------------------------------- drafts

def covered_items(claim, items):
    t, d = norm(claim.get("text")), norm(claim.get("draft_text"))
    found = {i for i, it in enumerate(items) if any(norm(m) in t for m in it["markers"])}
    if not found:
        found = {i for i, it in enumerate(items) if any(norm(m) in d for m in it["markers"])}
    return found


def score_draft(draft, out, use_script):
    items = draft["items"]
    errors = {i for i, it in enumerate(items) if it["label"] == "unsupported"}
    extracted, caught, false_alarm = set(), set(), set()
    unmatched_flagged = []
    for c in (c for c in out.get("claims") or [] if isinstance(c, dict)):
        flagged = c.get("verdict") != "supported"
        if use_script and not flagged:
            flagged = script_status(c) != "supported"
        cov = covered_items(c, items)
        extracted |= cov
        if not flagged:
            continue
        if not cov:
            unmatched_flagged.append(c.get("text") or c.get("draft_text") or "")
        elif cov & errors:
            caught |= cov & errors
        else:
            false_alarm |= cov
    return {"errors": errors, "caught": caught, "false_alarm": false_alarm,
            "not_extracted": errors - extracted, "unmatched_flagged": unmatched_flagged}


# ---------------------------------------------------------------- checks

def check_cases():
    problems = []
    for q in CASES["questions"]:
        for key, quote in q["gold"]:
            if SOURCES[SRC[key]].find(quote)[0] is None:
                problems.append(f"{q['id']}: gold quote not in {key}: {quote}")
    for d in CASES["drafts"]:
        nd = norm(d["text"])
        for n, it in enumerate(d["items"], 1):
            for key, quote in it["gold"]:
                if SOURCES[SRC[key]].find(quote)[0] is None:
                    problems.append(f"{d['id']} item {n}: gold quote not in {key}: {quote}")
            for m in it["markers"]:
                if nd.count(norm(m)) != 1:
                    problems.append(f"{d['id']} item {n}: marker {m!r} occurs {nd.count(norm(m))} times in the draft")
    # A perfect answer built from the gold passages must score perfectly.
    for q in CASES["questions"]:
        claims = [{"text": quote, "evidence": [{"source": SRC[key], "quote": quote}]} for key, quote in q["gold"]]
        if q["expect"] == "not_in_documents":
            claims = []
        for use_script in (False, True):
            r = score_answer(q, {"status": STATUS_FOR[q["expect"]], "claims": claims}, use_script)
            if not r["type_ok"] or r["invented"] or r["outside"] or r["outdated"] or not all(ok for _, ok in r["keys"]):
                problems.append(f"{q['id']}: oracle answer does not score perfectly (script={use_script}): {r}")
    # A perfect draft check must score perfectly; flagging everything must catch every error and flag every fact.
    for d in CASES["drafts"]:
        items = d["items"]
        oracle = {"claims": [{"draft_text": it["markers"][0], "text": it["markers"][0],
                              "verdict": it["label"],
                              "evidence": [] if it["label"] == "unsupported" else
                              [{"source": SRC[k], "quote": q} for k, q in it["gold"]]} for it in items]}
        for use_script in (False, True):
            r = score_draft(d, oracle, use_script)
            if r["caught"] != r["errors"] or r["false_alarm"] or r["not_extracted"]:
                problems.append(f"{d['id']}: oracle does not score perfectly (script={use_script}): "
                                f"caught {sorted(r['caught'])}, false alarms {sorted(r['false_alarm'])}")
        everything = {"claims": [dict(c, verdict="unsupported") for c in oracle["claims"]]}
        r = score_draft(d, everything, False)
        if r["caught"] != r["errors"] or len(r["false_alarm"]) != len(items) - len(r["errors"]):
            problems.append(f"{d['id']}: flagging everything does not flag everything")
    return problems


def script_only():
    rows, by_type = [], defaultdict(Counter)
    for d in CASES["drafts"]:
        for n, it in enumerate(d["items"], 1):
            t = it.get("type", "supported")
            claim = {"text": it["markers"][0], "evidence": [{"source": SRC[k], "quote": q} for k, q in it["gold"]]}
            st = script_status(claim)
            by_type[t]["items"] += 1
            by_type[t]["flagged"] += st != "supported"
            rows.append(f"| {d['id']}-{n} | {t} | {st} | {it['markers'][0]} |")
    lines = ["# v2 script-only check (gold quotes, no model)", "",
             "Each draft item's marked detail is checked against its gold quotes: the supporting quotes for a",
             "correct fact, the sentence a careless checker would most likely cite for an error.", "",
             "| Item type | Items | Flagged by the script |", "|---|---|---|"]
    for t in ["supported"] + DRAFT_TYPES:
        lines.append(f"| {t} | {by_type[t]['items']} | {by_type[t]['flagged']} |")
    lines += ["", "| Item | Type | Script result | Marked detail |", "|---|---|---|---|"] + rows
    out = "\n".join(lines) + "\n"
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "script-only.md").write_text(out, encoding="utf-8")
    return out


# ---------------------------------------------------------------- scoring a run

def score_run(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["results"]["results"]
    runs = defaultdict(list)
    for r in rows:
        runs[(arm_of(r), r["vars"]["case_id"])].append(r)

    calls, errors, cost, latency, api_calls, tool_calls = Counter(), Counter(), Counter(), defaultdict(list), Counter(), Counter()
    broken = Counter()
    meta_by_arm, outputs = {}, []
    fq = defaultdict(Counter)            # (arm, mode) -> counters for questions
    fd = defaultdict(Counter)            # (arm, mode) -> counters for drafts
    review = defaultdict(list)           # arm -> lines to review
    missed, alarms, unmatched = defaultdict(list), defaultdict(list), defaultdict(list)
    for (arm, cid), rs in sorted(runs.items()):
        for run_no, r in enumerate(rs, 1):
            calls[arm] += 1
            resp = r.get("response") or {}
            meta = resp.get("metadata") or {}
            if resp.get("error") or not resp.get("output"):
                errors[arm] += 1
                outputs.append({"arm": arm, "case": cid, "run": run_no, "error": resp.get("error") or "no output"})
                continue
            try:
                out = json.loads(resp["output"]) if isinstance(resp["output"], str) else resp["output"]
            except json.JSONDecodeError:
                errors[arm] += 1
                outputs.append({"arm": arm, "case": cid, "run": run_no, "error": "output is not JSON"})
                continue
            meta_by_arm.setdefault(arm, meta)
            cost[arm] += resp.get("cost") or 0
            latency[arm].append(meta.get("latency_ms") or 0)
            api_calls[arm] += meta.get("api_calls") or 1
            tool_calls[arm] += meta.get("tool_calls") or 0
            broken[arm] += sum(bool(t.get("broken")) for t in meta.get("tool_log") or [])
            outputs.append({"arm": arm, "case": cid, "run": run_no, "cost_usd": round(resp.get("cost") or 0, 6),
                            "latency_ms": meta.get("latency_ms"), "api_calls": meta.get("api_calls"),
                            "tool_calls": meta.get("tool_calls"), "tool_exit_codes": [t.get("exit") for t in meta.get("tool_log") or []],
                            "output": out})
            if cid in QUESTIONS:
                q = QUESTIONS[cid]
                for mode in MODES:
                    s = score_answer(q, out, mode == "script")
                    st = fq[(arm, mode)]
                    st["answers"] += 1
                    st["type_ok"] += s["type_ok"]
                    st["nid_total"] += q["expect"] == "not_in_documents"
                    st["nid_ok"] += q["expect"] == "not_in_documents" and s["type_ok"]
                    st["invented"] += bool(s["invented"])
                    st["outside"] += bool(s["outside"])
                    st["outdated_total"] += bool(q["outdated"])
                    st["outdated"] += bool(s["outdated"])
                    st["keys_total"] += len(s["keys"])
                    st["keys_ok"] += sum(ok for _, ok in s["keys"])
                    st["claims"] += s["claims"]
                    st["script_passed"] += s["script_passed"]
                    st["kept"] += s["kept"]
                    if mode == "model" and (s["invented"] or s["outside"] or s["outdated"] or not s["type_ok"]):
                        review[arm].append(
                            f"- {cid} run {run_no}: status {out.get('status')} (expected {q['expect']}); "
                            f"invented {s['invented'] or '-'}; outside the relevant passages {s['outside'] or '-'}; "
                            f"outdated {s['outdated'] or '-'}; script passed {s['script_passed']}/{s['claims']} claims. "
                            f"Answer: {s['text'][:600]}")
            else:
                d = DRAFTS[cid]
                for mode in MODES:
                    s = score_draft(d, out, mode == "script")
                    st = fd[(arm, mode)]
                    st["errors"] += len(s["errors"])
                    st["caught"] += len(s["caught"])
                    st["supported"] += len(d["items"]) - len(s["errors"])
                    st["false_alarm"] += len(s["false_alarm"])
                    st["not_extracted"] += len(s["not_extracted"])
                    st["unmatched_flagged"] += len(s["unmatched_flagged"])
                    st["claims"] += len(out.get("claims") or [])
                    for i in s["errors"]:
                        t = d["items"][i]["type"]
                        st[f"total_{t}"] += 1
                        st[f"caught_{t}"] += i in s["caught"]
                    if mode == "script":
                        for i in sorted(s["errors"] - s["caught"]):
                            it = d["items"][i]
                            why = "never extracted" if i in s["not_extracted"] else "passed"
                            missed[arm].append(f"- {cid}-{i + 1} run {run_no} ({it['type']}, {why}): {it['markers'][0]}")
                        for i in sorted(s["false_alarm"]):
                            alarms[arm].append(f"- {cid}-{i + 1} run {run_no}: {d['items'][i]['markers'][0]}")
                        unmatched[arm] += [f"- {cid} run {run_no}: {t}" for t in s["unmatched_flagged"]]

    arms = [a for a in ARMS if calls[a]]
    head = "| | " + " | ".join(f"{a} | {a} + script" for a in arms) + " |"
    sep = "|---|" + "---|" * (2 * len(arms))

    def row(label, table, num, den):
        cells = []
        for a in arms:
            for m in MODES:
                st = table[(a, m)]
                cells.append(f"{st[num]}/{st[den]}" if den else f"{st[num]}")
        return f"| {label} | " + " | ".join(cells) + " |"

    meta0 = next(iter(meta_by_arm.values()), {})
    lines = [f"# evidence-check v2 (held-out): {Path(path).name}", "",
             f"Model {meta0.get('model_served', '?')}, effort {meta0.get('effort', '?')}, script {meta0.get('script_sha', '?')}. "
             + "; ".join(f"{a}: {calls[a]} conversations, {errors[a]} failed"
                         + (f", SKILL.md sha {meta_by_arm[a].get('skill_sha')}" if meta_by_arm.get(a, {}).get("skill_sha") else "")
                         for a in arms) + ".", "",
             "## Free answers (Mode A): 16 questions, each run twice", "", head, sep,
             row("Reply type right (answered / not in the documents)", fq, "type_ok", "answers"),
             row("  of which 'not in the documents' questions", fq, "nid_ok", "nid_total"),
             row("**Answers with an invented number**", fq, "invented", "answers"),
             row("Answers with a number outside the relevant passages (review list below)", fq, "outside", "answers"),
             row("**Answers that use a superseded value**", fq, "outdated", "outdated_total"),
             row("Key facts present", fq, "keys_ok", "keys_total"),
             row("Claims kept (+ script drops claims that fail)", fq, "kept", "claims"),
             "", "## Unsplit drafts (Mode B): 8 drafts, 30 planted errors, 75 correct facts, each run twice", "", head, sep,
             row("**Planted errors flagged**", fd, "caught", "errors")]
    for t in DRAFT_TYPES:
        lines.append(row(f"  {t}", fd, f"caught_{t}", f"total_{t}"))
    lines += [row("**Correct facts wrongly flagged**", fd, "false_alarm", "supported"),
              row("Planted errors the model never extracted as a claim", fd, "not_extracted", "errors"),
              row("Flagged claims that match no marked fact (review)", fd, "unmatched_flagged", None),
              row("Claims returned", fd, "claims", None),
              "", "## Cost and speed (all 48 conversations per arm)", "",
              "| | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms),
              "| Cost (USD) | " + " | ".join(f"{cost[a]:.4f}" for a in arms) + " |",
              "| Median latency per conversation (s) | " + " | ".join(
                  f"{statistics.median(latency[a]) / 1000:.1f}" if latency[a] else "-" for a in arms) + " |",
              "| API calls | " + " | ".join(str(api_calls[a]) for a in arms) + " |",
              "| Script runs by the model | " + " | ".join(str(tool_calls[a]) for a in arms) + " |",
              "| Script runs that failed to start (harness fault) | " + " | ".join(str(broken[a]) for a in arms) + " |",
              "", "## Answers to review (model only)", ""]
    for a in arms:
        lines.append(f"**{a}** ({len(review[a])})")
        lines += review[a] or ["- none"]
        lines.append("")
    lines += ["## Planted errors that got through (+ script)", ""]
    for a in arms:
        lines.append(f"**{a}** ({len(missed[a])})")
        lines += missed[a] or ["- none"]
        lines.append("")
    lines += ["## Correct facts wrongly flagged (+ script)", ""]
    for a in arms:
        lines.append(f"**{a}** ({len(alarms[a])})")
        lines += alarms[a] or ["- none"]
        lines.append("")
    lines += ["## Flagged claims that match no marked fact (+ script, for review)", ""]
    for a in arms:
        lines.append(f"**{a}** ({len(unmatched[a])})")
        lines += unmatched[a] or ["- none"]
        lines.append("")
    summary = "\n".join(lines)
    base = Path(path).with_suffix("")
    Path(str(base) + ".summary.md").write_text(summary + "\n", encoding="utf-8")
    Path(str(base) + ".outputs.json").write_text(json.dumps(outputs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("results", nargs="?")
    p.add_argument("--check", action="store_true")
    p.add_argument("--script-only", action="store_true")
    args = p.parse_args(argv)
    out = sys.stdout.buffer
    if args.check:
        problems = check_cases()
        nq, nd = len(CASES["questions"]), len(CASES["drafts"])
        ne = sum(it["label"] == "unsupported" for d in CASES["drafts"] for it in d["items"])
        ns = sum(it["label"] == "supported" for d in CASES["drafts"] for it in d["items"])
        msg = "\n".join(problems) if problems else f"cases OK: {nq} questions, {nd} drafts, {ne} planted errors, {ns} correct facts"
        out.write((msg + "\n").encode("utf-8"))
        return 1 if problems else 0
    if args.script_only:
        out.write(script_only().encode("utf-8"))
        return 0
    if not args.results:
        p.print_help()
        return 2
    out.write((score_run(args.results) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
