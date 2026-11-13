# v3 plan: script 0.3.0, checked before it is written

Written 13 November 2026, 03:52 MYT. The cases, sources and runner below were fixed before `check_evidence.py` was changed, and their hashes are recorded here. Hashes are of the files with LF line endings, as stored in the repository.

## Why

Using the skill on real project files (status pages, research notes, evaluation reports) showed the script flagging correct claims in ways the fictional v1 and v2 documents never did. The kinds that came up are listed below. Some can be fixed with a fixed rule; the others are numbers the document does not state, which the script flags on purpose.

## Planned changes to the script

| Rule | Example of a correct claim flagged by 0.2.0 |
|---|---|
| A month name before a year counts as the month | `2025 年 12 月` against `December 2025` |
| Fractions compare as fractions | `三分之一` against `one-third` |
| A negated 一 is not 1 | `一次都没变`, `没有一次` |
| `none` in a quote counts as 0 | `0 failed` against `none failed` |
| 百 or 千 directly before 万 or 亿, with no numeral before it, is not a number | `每百万` |
| 万, 亿, thousand, million and billion scale the number before them | `4.3万` against `43,000` |
| In a quote, a decimal below 1 also counts as a percentage, and a percentage as a decimal | `99.6%` against `0.996` |
| A name with digits attached (`ranker-v3.2`, `echo-asr-2025-08-28`, `p90`) is a name when it appears in a cited source | a model version named in the claim but not in the quoted sentence |
| The cited document's own title is a name | `update notice 2` |

Not changed, and still flagged on purpose: a count of days worked out from two dates, sums, differences, ratios, rounding, currency conversion, counts of listed items, and names with a space before the number. Each is a number the document does not state; the reader decides whether it is right.

## Cases

`cases.json`: 36 claims against three new fictional documents in `sources/`. 16 correct claims (should pass), 17 wrong claims with a changed number (must be flagged), 3 limit claims (true, but with a number the document does not state; flagged on purpose). `run.py` runs every claim through the script frozen for v2 (0.2.0) and the current script, with no model.

Before any change, both versions are the same script: 3 of 16 correct claims pass and 16 of 17 wrong claims are flagged (A04, `November 2025` for `October 2025`, passes because a month next to a year was not read).

## Expectations

- 0.3.0 passes all 16 correct claims and still flags all 17 wrong claims and all 3 limit claims.
- On the v1 and v2 cases, 0.3.0 flags every unsupported sentence and planted error that 0.2.0 flags.

## Frozen files

| File | sha256 (first 12) |
|---|---|
| `cases.json` | `af893525b7eb` |
| `run.py` | `510c652355f3` |
| `sources/C01-season-report-2025.md` | `4b4c3322b777` |
| `sources/C02-update-notice-2.md` | `c92ff51dce76` |
| `sources/C03-faq-zh.md` | `78947dd750ed` |

## Limits

The cases target the rules above and were written by the same author as the script, so passing them shows the rules work as intended, not how often they help. Whether 0.3.0 removes false alarms in real use is measured by the usage log, in new rows written after this change.

## Changes after the run

The run matched both expectations: 16 of 16 correct claims pass, 17 of 17 wrong claims and 3 of 3 limit claims are flagged ([`results/script-only.md`](results/script-only.md)). Nothing in the cases, sources or `run.py` changed. `regression.py` was written after the change to test the second expectation; no v1 sentence or v2 draft item changed result ([`results/regression.md`](results/regression.md)).
