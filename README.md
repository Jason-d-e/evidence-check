# evidence-check

An [Agent Skill](https://agentskills.io) that makes an AI back every factual sentence with a word-for-word quote from your own documents, and a script that checks those quotes.

[中文说明](README.zh-CN.md)

Answers and drafts written from documents go wrong in small, costly ways: a deadline moves by a day, a duration is worked out instead of copied, a detail appears that no document states. evidence-check has the agent quote its source for every fact, then runs a script that confirms:

1. **the quote is really in the cited file** (case, spacing, curly quotes and punctuation are forgiven);
2. **every date, time, amount and count in the claim is also in its quotes**, across English and Chinese: `下午2点` matches `14:00`, `五位` matches `Five`, `4.3万` matches `43,000`, `13:30` does not pass on a quote that says `13:00`.

The script cannot judge meaning: a real sentence can be cited for its opposite. So the skill also tells the agent to read every passing claim against its quotes.

## Two modes

- **Answer from documents.** "Answer only from handbook.md and faq.md, with a quote for every fact." Claims that fail the script are fixed or dropped before you see the answer.
- **Check a draft.** "Check this announcement against the rules folder." The agent splits the draft into claims, quotes a source for each, runs the script, and reports each problem with the document's own words and one suggested fix. It does not rewrite your draft.

## Install

Claude Code, as a plugin:

```
/plugin marketplace add Jason-d-e/evidence-check
/plugin install evidence-check@evidence-check
```

Any other agent that reads Agent Skills: copy `skills/evidence-check/` into its skills folder (for Claude Code without the plugin, `~/.claude/skills/evidence-check/`).

The script needs Python 3.9 or later and nothing else.

## Run the script yourself

A claims file lists each claim with the quotes that support it:

```json
{"claims": [
  {"id": "2", "text": "Projects must be submitted by 13:30 on Sunday.",
   "evidence": [{"source": "B02-update-notice-1.md",
                 "quote": "Project submission now closes on Sunday 17 January 2027 at 14:00 MYT instead of 13:00."}]}
]}
```

```bash
python skills/evidence-check/scripts/check_evidence.py claims.json --sources eval/v2/sources --format markdown
```

Output for four claims against the example documents in `eval/v2/sources`:

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | Registration closes on 3 January 2027 at 23:59 MYT. | Supported | B01-build-weekend-handbook.md, line 35: "Registration opens on 1 December 2026 and closes on 3 January 2027 at 23:59 MYT, or earlier if all 120 places are taken." |
| 2 | Projects must be submitted by 13:30 on Sunday. | Numbers not in the quote (missing numbers: 13:30) | B02-update-notice-1.md, line 6: "Project submission now closes on Sunday 17 January 2027 at 14:00 MYT instead of 13:00." |
| 3 | 押金是50令吉。 | Supported | B01-build-weekend-handbook.md, line 35: "A place is confirmed only after a refundable deposit of RM 50 is paid." |
| 4 | Every participant gets a free T-shirt. | No evidence given | — |

Exit code 0 means every claim passed, 1 that at least one did not, 2 that the input could not be read. `--format json` gives the full report, `--lang zh` Chinese labels. Field reference and matching rules: [`references/claims-format.md`](skills/evidence-check/references/claims-format.md).

## What it catches

| | Script | Agent's reading | Not handled |
|---|---|---|---|
| A quote that was edited, merged or invented | ✓ | | |
| A changed date, time, amount or count | ✓ | | |
| A number worked out instead of quoted ("two hours" for 19:00 to 20:30) | ✓ | | |
| A claim with no source | ✓ | | |
| A real sentence used for its opposite, a dropped condition, a wider scope | | ✓ | |
| A value replaced by a later document, when the old one is still among the sources | | ✓ in the v2 cases | |
| Rounding, sums and conversions (`约 4 万` for `43,000`), Roman numerals: flagged for you to check | | | ✓ |

## Related tools

- **[Citations](https://platform.claude.com/docs/en/build-with-claude/citations) in the Claude API** extracts each quote straight from your documents, so the quote is always really there. If you build on that API, use it. It cites the answer Claude is writing in the Messages API. It does not check a claim's numbers against its quote, it is not available to agents that read files through tools or to other models, and it does not split a draft someone already wrote into claims to check. evidence-check covers those.
- **Grounding checks in cloud platforms** (Vertex AI check grounding, Azure AI Content Safety groundedness detection, Amazon Bedrock Guardrails contextual grounding check) and **open checker models** (LettuceDetect, MiniCheck, HHEM) use a model to judge whether text is supported. evidence-check gives the exact quote and line for each claim and compares numbers without a model, a cloud account or extra packages.
- **Evaluation frameworks** (RAGAS, DeepEval, TruLens, promptfoo) score a test set after the fact. This project's evaluation runs on promptfoo.

## Evaluation

Two rounds on fictional documents, Claude Haiku 5.5 with and without the skill, each case run twice:

- **v1, 84 pre-split sentences.** A plain prompt already got 167 of 168 judgements right; the script caught the one it missed, a duration worked out wrongly ("two hours" for 19:00 to 20:30).
- **v2, held out: 16 free answers and 8 unsplit drafts.** Every arm flagged all 30 planted errors. The only invented numbers were a calculated "32 hours" (4 of 32 plain answers, none with SKILL.md v0.2), and the script flags each one. Run afterwards on a plain prompt's output, the script also rejected 12 of 150 correct facts, because the quotes were incomplete; with the skill, the agent repairs its quotes and 2 to 3 false alarms remain. The skill costs about three times as much per task.
- **Script 0.3.0, from real use.** Nine matching rules for false alarms seen on real files (`December 2025`, `三分之一`, `4.3万`, `99.6%` against `0.996`, versioned model names). On 36 new cases fixed before the change, correct claims passed went from 3 of 16 to 16 of 16, and all 17 changed numbers are still flagged; no v1 or v2 result changed.

Full report: [`eval/EVALUATION.md`](eval/EVALUATION.md). The test documents and drafts are synthetic and were written by the same author as the skill.

## Develop

```bash
python -m unittest discover -s tests -v     # offline tests, no model calls
python eval/script_only.py                  # the script alone on the v1 cases
python eval/v2/score.py --check             # validate the v2 cases
python eval/v3/run.py                       # matching rules, script 0.2.0 against current
```

The model comparisons use [promptfoo](https://www.promptfoo.dev) and need Node.js and an Anthropic API key in `eval/.env` (`ANTHROPIC_API_KEY=...`); the commands are at the top of each `promptfooconfig.yaml`.

## License

MIT. See [LICENSE](LICENSE).
