# v4 plan: script 0.4.0, checked before it is written

Written 14 November 2026, 17:51 MYT. The cases, sources, runner and the frozen copy of script 0.3.0 below were fixed before `check_evidence.py` was changed, and their hashes are recorded here. Hashes are of the files with LF line endings, as stored in the repository.

## Why

After 0.3.0, the usage log of real project files (19 entries) still showed correct claims flagged. Re-run on 0.3.0, the kinds that a fixed rule can handle are, by how often they came up:

| Rule | Entries | Example of a correct claim flagged by 0.3.0 |
|---|---|---|
| A number rounded from a more precise one in the quote counts, if it keeps at least two significant digits; the report marks it as rounded | 7 | `0.31` against `0.314`, `17%` against `16.5%`, `8.5 万` against `85,252` |
| A Chinese ordinal (`第 6 条`, `第二轮`) is a name when it appears in the quote's paragraph or the nearest heading above it | 4 | `第 6 条` for a rule quoted from under the heading `第 6 条` |
| Text in quotation marks in the claim is a name when it appears in a cited source | 3 | `“一次提示词”组` |
| `a third` and similar count as fractions without a following `of`; only `quarter` and `half` still need it | 1 | `三分之一` against `just under a third (8.3 of 25)` |
| A time with seconds in a quote also counts as the minute | 1 | `22:18` against `22:18:30` |
| A mixed-case or all-capital name followed by a space and a number (`SigLIP 2`) is a name when it appears in a cited source; currency codes are excluded | 1 | `SigLIP 2` named in the claim, not in the quoted sentence |

Rounding changes an earlier decision: 0.3.0 left every rounded number flagged. In real use it was the most common false alarm, and each one was right when read, so 0.4.0 accepts it under the two-significant-digit condition and reports it. Numbers worked out by arithmetic, counting or conversion stay flagged.

## Cases

`cases.json`: 28 claims against two new fictional documents in `sources/`. 11 correct claims (should pass), 13 wrong claims with a changed number or name (must be flagged), 4 limit claims (true, but rounded to a single significant digit or worked out by arithmetic; flagged on purpose). The traps include a quote under `第 6 条` cited for `第 7 条` (both rules are in the same document), `0.32` and `18%` against `0.314` and `16.5%`, `120` against an integer `123`, `a quarter` meaning a period of time, `22:18:45` against `22:18:30`, and a quoted group name that is not in the source. `run.py` runs every claim through script 0.3.0 (frozen in `frozen/`) and the current script, with no model.

Before any change, both versions are the same script: 0 of 11 correct claims pass, 13 of 13 wrong claims and 4 of 4 limit claims are flagged.

## Expectations

- 0.4.0 passes all 11 correct claims and still flags all 13 wrong claims and all 4 limit claims.
- On the v3 cases 0.4.0 gives the same results as 0.3.0, and on the v1 and v2 cases the same results as 0.2.0.

## Frozen files

| File | sha256 (first 12) |
|---|---|
| `cases.json` | `37e8a280454c` |
| `run.py` | `c84f1fbef535` |
| `sources/D01-scoring-results.md` | `edfe5e1aacca` |
| `sources/D02-rules-zh.md` | `3903c2f41ae8` |
| `frozen/check_evidence.py` (0.3.0) | `d95bbbcd1a18` |

## Limits

The cases target the rules above and were written by the same author as the script, so passing them shows the rules work as intended, not how often they help. Whether 0.4.0 removes false alarms in real use is measured by new rows in the usage log.

## Changes after the run

None yet.
