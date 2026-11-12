---
name: evidence-check
description: Makes sure what an AI writes is backed, word for word, by the user's own documents. Use it whenever an answer must come only from given files (policies, FAQs, rules, handbooks, contracts, reports, notes, data sheets), and whenever the user asks to fact-check, verify, cite, or source-check a draft against documents, or says things like "don't make things up", "where does it say that", "quote the source", "有出处", "核对一下", "不要编". Two modes - answer a question from sources with a verbatim quote for every fact, or check an existing draft claim by claim. A bundled script confirms that each quote really appears in the cited file and that every date, time and number in a claim also appears in its quote, so invented or shifted details are caught before anyone reads them.
metadata:
  version: "0.2.0"
---

# Evidence check

Every factual sentence you hand over must rest on a quote that is really in the user's documents. The bundled script checks the quotes and the numbers; you check the meaning.

Use it when answering from documents, when checking a draft against them, and whenever you state dates, deadlines, amounts, counts, names or promises taken from them. Skip it for opinions and brainstorming.

## The script

```bash
python <this-skill-folder>/scripts/check_evidence.py claims.json --sources <files or folders> --format markdown --lang en
```

Python 3.9+, standard library only. Use `--lang zh` for a user who writes in Chinese. A claim passes only when:

1. every quote appears in its source file (case, spacing, curly quotes, dashes and punctuation are forgiven);
2. every date, time, amount and count in the claim also appears in its quotes. Digits, number words, Chinese numerals, month names and 12-hour times are compared across languages.

Exit code 0: every claim passed; 1: at least one did not; 2: the input could not be read.

The claims file, written to a working folder rather than the user's project:

```json
{"claims": [
  {"id": "1", "text": "Registration closes on 11 November at 18:00 MYT.",
   "evidence": [{"source": "workshop.md", "quote": "Registration closes on 11 November 2026 at 18:00 MYT."}]},
  {"id": "2", "text": "Every participant gets a certificate.", "evidence": []}
]}
```

`source` is the path relative to the `--sources` folder, or the file name if it is unique. A claim may have several quotes. Copy each quote character for character; do not translate or shorten it. For PDFs, web pages or Word files, save the text as `.txt` or `.md` first and cite that file. Field reference and what each result means: `references/claims-format.md`.

## Judging a claim

The script cannot see meaning: a real sentence can be cited for its opposite. After it passes a claim, read the claim against its quotes.

A claim is **supported** when its quotes state the same fact. The wording may differ: a paraphrase, a summary or a translation is fine.

It is **not supported** when the quotes say less, more or something else:

- a different number, date, time, name or place;
- a condition or negation dropped or reversed (only, if, unless, not, 仅, 不);
- a wider scope (all instead of some, always instead of usually, guaranteed instead of possible);
- a detail that is in none of its quotes, including one you worked out yourself. Give the figures the document gives ("19:00 to 20:30"), not a duration or total you calculated ("90 minutes").

Never fill a gap from general knowledge.

## Mode A: answer a question

1. Write the answer as short claims, one fact each, each with its quote.
2. Run the script. Fix or drop every claim that does not pass, and run it again until every claim you keep passes.
3. Judge each passing claim as above.
4. Answer with each fact followed by its quote and source. If the documents do not answer the question, say so and name the closest passage.

## Mode B: check a draft

1. Split the draft into claims, one fact each. Keep what can be wrong: dates, times, deadlines, numbers, amounts, names, places, eligibility, promises ("free", "guaranteed", "包退") and comparisons. Leave out greetings, opinions and instructions.
2. For each claim, find the sentence that states it and copy it. If there is none, leave `evidence` empty; do not stretch a loosely related sentence to fit.
3. Run the script, then judge each passing claim as above.
4. Report without rewriting the draft yourself: the outcome first, then each problem with the document's own words and one suggested fix (correct it, soften it, add a source, or delete it).

```markdown
**3 of 5 claims are backed by the documents; 2 are not.**

| Claim | Result | Source |
|---|---|---|
| Registration closes on 10 November | Number not in the quote: the document says 11 November | workshop.md, line 6: "Registration closes on 11 November 2026 at 18:00 MYT." |
| Participants get a certificate | No evidence | — |

Suggested fixes: change "10 November" to "11 November"; delete the certificate sentence.
```

Keep quotes in the source language and reply in the user's language. If Python is not available, say that the quotes could not be checked automatically, follow every other step, and label the result as unchecked.
