# v2 held-out evaluation: plan fixed before the run

Written 12 November 2026, 05:46 MYT, before any model saw the v2 cases. After the run, nothing in the cases, sources or scoring rules below changes. Any later fix to the scorer is listed under "Changes after the run" with its reason, and the run is re-scored from the stored outputs, with no new model calls.

## Why v2

v1 hit a ceiling: pre-split, short sentences checked against three short documents, and the plain prompt got 167 of 168 judgements right. v2 makes the task closer to real use:

- **Free answers (Mode A).** 16 questions (8 English, 8 Chinese). The model writes the answer itself, so it can add dates and numbers that the documents do not give. Two questions are not answered by the documents; two invite a calculated duration; five touch a fact that an update notice changed.
- **Unsplit drafts (Mode B).** 8 drafts (4 English of 107 to 127 words, 4 Chinese of 203 to 249 characters), given as running text. The model has to find the claims itself. 30 planted errors (9 changed numbers, 4 superseded values, 5 invented details, 11 contradictions, 1 calculated duration) and 75 correct facts.
- **Longer documents.** Four fictional DemoClub files (about 1,230 English words plus a Chinese FAQ, nearly three times v1), with Markdown tables, an update notice that supersedes three handbook values, and a Chinese FAQ that already includes the update.
- **The skill runs its own script.** In v1 the skill could not run the script. In v2 the skill arms get a `check_evidence` tool that runs the real script on the claims they pass, as an agent with a shell would.

## Arms

Same model (`claude-haiku-5-5`, effort `medium`, adaptive thinking by default), same documents, same JSON output schema:

| Arm | System prompt | Tool |
|---|---|---|
| plain | one sentence (in `provider.mjs`) | none |
| skill-v0.1 | body of SKILL.md v0.1, the version evaluated in v1 | `check_evidence`, at most 4 runs |
| skill-v0.2 | body of SKILL.md v0.2 | the same |

**Which version saw what.** v0.1 was written before any evaluation. v0.2 was written after reading the v1 results and before the v2 cases existed (frozen 05:32 MYT; cases written after). Its changes come from v1 only: paraphrases and translations that state the same fact count as supported (both v1 false alarms were such paraphrases), figures the document gives instead of calculated ones (the one v1 error the model missed was a calculated duration), and a shorter text (v1 cost was about double). v0.2 and the v2 cases have the same author.

**Script changes before v2**, all with offline tests, all made before the run: clock times are compared whole (13:30 no longer passes on a quote with 13:00 and 14:30); Markdown table bars are ignored in the loose pass; Chinese clock times such as 下午2点 and 晚上11点 are read as 14:00 and 23:00; 二维码 (QR code) is no longer read as the number 2. On the v1 cases the script-only results are unchanged by these fixes.

## What is measured (rules in `score.py`)

"Model only" scores the model's output as returned. "+ script" also runs the checking script on every claim the model returned: in an answer, claims that fail are dropped (what an agent following the skill must do); in a draft check, a claim that fails counts as flagged.

Free answers, per answer (32 per arm):
1. **Answers with an invented number**: a number in the answer that appears in no source file and not in the question. Fully automatic.
2. **Answers that use a superseded value**: the old value of an amended fact appears without the new one (questions that touch an amended fact).
3. Answers with a number outside the relevant passages: automatic flag, every case listed for a person to review.
4. Reply type right (answered / not in the documents), and key facts present.

Unsplit drafts (60 planted-error judgements and 150 correct-fact judgements per arm):
1. **Planted errors flagged**, by type;
2. **Correct facts wrongly flagged**;
3. Planted errors the model never extracted as a claim.

Also: cost, median latency, API calls and script runs per arm.

## Expectations, written down before the run

1. In free answers, the plain prompt will state at least one number that its passages do not give in some answers. The skill arms, which run the script, will have fewer invented numbers. Because an invented number fails the script, "+ script" should remove them in every arm.
2. Superseded values will not be caught by the script in any arm: the old handbook sentence is still a real quote. Any difference between arms there comes from the model's reading.
3. Unsplit drafts will be harder than v1. The plain prompt will miss more errors than in v1, partly because it never extracts some of them as claims.
4. v0.2 will raise fewer false alarms and cost less than v0.1, without catching fewer errors.

With two runs per case, a difference of one or two answers or items between arms is treated as noise. Expectations that do not hold are reported as not holding.

## Run

From `eval/v2/`: `npx -y promptfoo@0.125.1 eval -c promptfooconfig.yaml --no-cache --repeat 2 -o results/run-2026-11-12.json`, then `python eval/v2/score.py eval/v2/results/run-2026-11-12.json` from the project root. 3 arms × 24 cases × 2 runs = 144 conversations.

Harness check before the run (not scored, `smoke-cases.json`, two cases that are not in the evaluation): the first attempt showed that the tool could not start Python in its minimal environment; the provider now resolves the real interpreter first. The second attempt ran cleanly.

## Frozen files (sha256, first 12 characters)

Hashes are of the files with LF line endings, as stored in the repository.

| File | sha256 |
|---|---|
| `cases.json` | `296001e2d167` |
| `sources/B01-build-weekend-handbook.md` | `676818d9d365` |
| `sources/B02-update-notice-1.md` | `b1cc415360fe` |
| `sources/B03-faq-zh.md` | `15036339bbff` |
| `sources/B04-venue-and-access.md` | `34ebde5defa2` |
| `skill-versions/SKILL-v0.1.md` | `9aec983a7522` |
| `skill-versions/SKILL-v0.2.md` | `8dcadfc8cd45` |
| `frozen/check_evidence.py` | `f820b173a356` |
| `provider.mjs` | `5f78b54a5424` |
| `score.py` | `6dc6040d86a7` |
| `tests.mjs` | `fb89be92e4c6` |
| `promptfooconfig.yaml` | `3420a1b301b3` |

## Changes after the run

The run finished at 05:56 MYT: 144 conversations, none failed. Two scorer bugs showed up in the first scoring and were fixed; the run was then re-scored from the stored outputs, with no new model calls. Cases, sources, prompts and scoring rules did not change. `score.py` is now `9398184a7136`.

1. **Arm names.** promptfoo stored the label `skill` for both skill arms. The scorer now takes the arm from the provider id (`evidence-check-v2:skill-v0.1`, `…:skill-v0.2`), which every result carries; each id matches its SKILL.md hash in the result metadata.
2. **Reply type.** `cases.json` says `answer` where the output schema says `answered`, so every answered question first counted as the wrong reply type. The scorer now maps one to the other. The self-check missed this because its perfect answers used the same spelling as the cases; it now uses the schema's value.
3. **Description text.** The `about` line at the top of `cases.json` was reworded; no question, draft, label, marker or gold quote changed, and the model never sees that line. `cases.json` is now `76b55e4120e0`.
