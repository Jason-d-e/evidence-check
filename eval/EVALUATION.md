# evidence-check: evaluation brief

*12–13 November 2026 · automatic checks on small fictional datasets; this is not an accuracy study*

## Question

When an AI answers from documents or checks a draft against them, does the evidence-check skill (instructions plus a quote-checking script) produce fewer unsupported statements than a plain "use the documents" prompt, and what does it cost?

Every run below uses the same model (Claude Haiku 5.5, effort `medium`), the same documents and the same JSON output in every arm; only the instructions differ. "+ script" means the checking script was also run on every claim afterwards. Each case was run twice with promptfoo 0.125.1; no call failed.

## v1: twelve pre-split drafts

Three short DemoClub documents (about 450 words); 84 numbered sentences to check, 37 of them unsupported. The skill (SKILL.md v0.1) could not run the script itself.

| Two runs, 168 judgements | plain | plain + script | skill v0.1 | skill v0.1 + script |
|---|---|---|---|---|
| Unsupported sentences flagged | 73/74 | **74/74** | 74/74 | 74/74 |
| Supported sentences wrongly flagged | 0/94 | 0/94 | 2/94 | 2/94 |
| Cost of 24 calls | US$0.011 | | US$0.021 | |

**A ceiling effect.** The plain prompt got 167 of 168 judgements right. Its one miss, "the session lasts two hours" for 19:00 to 20:30, was caught by the script because "2" is not in the quote. The v0.1 instructions added two false alarms, both faithful Chinese paraphrases of an English sentence, and doubled the cost. On its own, the script caught 0 of 10 sentences that reverse what a real quote says: that check needs a reader.

## v2: free answers and unsplit drafts, held out

Changes from v1, all made before the v2 cases were written and recorded in [`v2/PREREGISTRATION.md`](v2/PREREGISTRATION.md): SKILL.md v0.2 (paraphrases and translations of the same fact count as supported; give figures as the document gives them, not calculated ones; 30% shorter), and four script fixes (clock times compared whole, table bars ignored, Chinese clock times, 二维码 no longer read as 2).

**Cases.** Four new fictional documents (about 1,230 English words, a Chinese FAQ, Markdown tables, and an update notice that supersedes three handbook values). 16 questions to answer (8 English, 8 Chinese) and 8 drafts given as running text, with 30 planted errors and 75 correct facts. Both skill arms could run the real script through a tool, as an agent with a shell would. 144 conversations.

| Two runs per case | plain | plain + script | skill v0.1 | skill v0.2 |
|---|---|---|---|---|
| **Free answers (32 per arm)** | | | | |
| Answers with a number found in no document | 4 | 0 | 2 | 0 |
| Answers that use a superseded value | 0/14 | 0/14 | 0/14 | 0/14 |
| Reply type right (answered / not in the documents) | 32 | 32 | 32 | 31 |
| Key facts present (32) | 32 | 29 | 32 | 32 |
| Claims that fail the script | 21/128 | dropped | 8/160 | 6/133 |
| **Unsplit drafts** | | | | |
| Planted errors flagged | 60/60 | 60/60 | 60/60 | 60/60 |
| Correct facts wrongly flagged | 0/150 | **12/150** | 2/150 | 3/150 |
| **Cost of 48 conversations / median latency** | US$0.052 / 4.8 s | | US$0.169 / 12.2 s | US$0.160 / 9.8 s |

With the script also run afterwards, the skill arms' invented numbers drop to 0 and their key facts to 29 (v0.1) and 31 (v0.2); their draft scores do not change. All columns: [`v2/results/run-2026-11-12.summary.md`](v2/results/run-2026-11-12.summary.md).

**What v2 shows.**

1. **The model still catches nearly everything on its own.** Every arm extracted and flagged all 30 planted errors in both runs, superseded values included, and no answer used a superseded value. Our expectation that unsplit drafts would make the plain prompt miss errors did not hold.
2. **The only invented numbers were a calculated duration.** "32 hours", from Saturday 09:00 to Sunday 17:00 (the building closes overnight): 4 plain answers, 2 with v0.1, none with v0.2, whose instructions say to give the document's own figures. The script flags every one.
3. **The script on its own is a blunt filter; the skill makes it workable.** The plain prompt often quotes only part of what a claim says, for example a number that sits in the next sentence. Run afterwards, the script then rejected 21 of its 128 answer claims, losing 3 key facts, and 12 correct facts in the drafts. When the model runs the script itself, it repairs most of its quotes before answering (6 to 8 failing claims left instead of 21), and the drafts show 2 to 3 false alarms instead of 12.
4. **It costs about three times as much.** The skill arms make about two and a half API calls per task and resend the documents each time. v0.2 is 5% cheaper and 20% faster than v0.1, with the same catches and one more false alarm, which is within noise.
5. **Script false alarms to fix next,** found in this run and not changed after it: a document name with a number in a claim ("update notice 1"), and "two days" inferred from two dates. Script 0.3.0 handles the first; the second stays flagged on purpose (below).

## Script 0.3.0: false alarms from real use

Using the skill on real project files (status pages, research notes, evaluation reports) showed the script flagging correct claims in ways the fictional documents had not: `2025 年 12 月` against `December 2025`, `三分之一` against `one-third`, `一次都没变` read as 1, `4.3万` against `43,000`, `99.6%` against `0.996`, model names with a version or date. Nine matching rules were added. 36 new script-only cases, with their labels, were fixed before the change and recorded in [`v3/PREREGISTRATION.md`](v3/PREREGISTRATION.md).

| 36 claims, no model | 0.2.0 | 0.3.0 |
|---|---|---|
| Correct claims passed | 3/16 | **16/16** |
| Claims with a changed number flagged | 16/17 | **17/17** |
| True claims with a number the document does not state, flagged on purpose | 3/3 | 3/3 |

The one changed number 0.2.0 missed was `November 2025` for `October 2025`: a month next to a year was not read. On the v1 sentences and v2 draft items with their gold quotes (84 and 105), no result changed ([`v3/results/regression.md`](v3/results/regression.md), a check written after the change). SKILL.md is still v0.2, so the model comparisons above still describe the instructions.

Still flagged on purpose: sums, differences, ratios, rounding, currency conversions, counts of listed items, and day counts worked out from two dates ("a two-day event"). The document does not state these numbers, and accepting worked-out figures would also let through a wrong one like "32 hours"; the reader decides.

## Script 0.4.0: rounding and names

After 0.3.0, use on real files still showed correct claims flagged, most often for rounding (`0.31` for `0.314`, `17%` for `16.5%`), and for ordinals (`第 6 条`), quoted group names, `a third` without `of`, times with seconds and names such as `SigLIP 2`. Six rules were added. 28 new script-only cases, with their labels, were fixed before the change and recorded in [`v4/PREREGISTRATION.md`](v4/PREREGISTRATION.md).

| 28 claims, no model | 0.3.0 | 0.4.0 |
|---|---|---|
| Correct claims passed | 0/11 | **11/11** |
| Claims with a changed number or name flagged | 13/13 | 13/13 |
| True claims rounded to one significant digit or worked out, flagged on purpose | 4/4 | 4/4 |

Rounding changes what the section above leaves flagged: a claim's number now also matches a more precise number in its quotes that rounds to it, if the claim keeps at least two significant digits, and the report lists each rounded match. `0.3` for `0.314`, `120` for `123` and `约 4 万` for `43,000` are still flagged; sums, ratios and conversions still are too. An ordinal counts as a name only when it is in the quote's paragraph or the heading above it, so a rule quoted from under `第 6 条` and cited as `第 7 条` is still flagged. The v3 results are unchanged, and no v1 sentence or v2 draft item changed result ([`v3/results/regression.md`](v3/results/regression.md)).

## Limits

- The documents and drafts are synthetic and were written by the same author as the skill, with the labels fixed when the cases were written. Planted errors may be easier to spot than real ones.
- The automatic flag "number outside the passages relevant to the question" is only a pointer; every case is listed in the summary. Read against the documents, the flagged numbers other than the 32-hour calculation and its parts are correct details from passages the list left out (age limit, team size, a deposit or prize rule named as the closest passage), the "1" in "update notice 1", "two" in "where the two differ", and "a two-day event".
- Claude's [Citations](https://platform.claude.com/docs/en/build-with-claude/citations) feature, which extracts quotes straight from the documents, was not one of the arms: it cannot be combined with the structured JSON output that every arm used.
- One model at one effort level, two runs of each case, one day. With these counts, a difference of one or two items is noise.
