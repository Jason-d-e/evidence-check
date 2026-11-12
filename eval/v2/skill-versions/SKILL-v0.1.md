---
name: evidence-check
description: Makes sure what an AI writes is backed, word for word, by the user's own documents. Use it whenever an answer must come only from given files (policies, FAQs, rules, handbooks, contracts, reports, notes, data sheets), and whenever the user asks to fact-check, verify, cite, or source-check a draft against documents, or says things like "don't make things up", "where does it say that", "quote the source", "有出处", "核对一下", "不要编". Two modes - answer a question from sources with a verbatim quote for every fact, or check an existing draft claim by claim. A bundled script confirms that each quote really appears in the cited file and that every date, time and number in a claim also appears in its quote, so invented or shifted details are caught before anyone reads them.
metadata:
  version: "0.1.0"
---

# Evidence check

Every factual sentence you hand over must rest on a quote that is really in the user's documents. A script checks the quotes, so a made-up or shifted detail cannot slip through.

## When to use it

- The user gives documents and asks a question that must be answered from them.
- The user gives a draft (an email, a summary, a report, an application, an FAQ answer) and wants to know whether the documents support it.
- You are about to state dates, deadlines, amounts, counts, names or promises taken from documents, and getting them wrong would hurt someone.

Skip it for opinions, brainstorming, and questions the documents are not meant to answer.

## What the script checks, and what it cannot

`scripts/check_evidence.py` (Python 3.9+, standard library only) reads a claims file and the source files, then checks each claim:

1. **The quote is in the source.** Case, spacing, curly quotes, dashes and full-width characters are ignored. If that fails, a second pass also ignores punctuation; the report says so.
2. **The claim's numbers are in its quotes.** Every day, month, year, time, amount and count stated in the claim must appear in the quotes. Chinese numerals, English number words, month names and 12-hour times are converted, so a Chinese claim can rest on an English quote. A year may also come from elsewhere in the same file, because documents often state it once.

It **cannot** tell whether a real quote actually says what the claim says. "Submitting the form does not guarantee a place" is a real sentence; a claim that "submitting guarantees a place" can still cite it. That check is yours: see step 4 below.

## Mode A: answer a question from the sources

1. Read the sources. If a source is a PDF, web page or Word file, save its text as a `.txt` or `.md` file first and cite that file.
2. Write the answer as short claims, one fact each. For each claim, copy the supporting sentence **character for character** from the source. Do not translate, shorten or correct it; a quote may be in another language than the answer.
3. Write the claims file (format below) to a working folder, not into the user's project, and run the script:
   ```bash
   python <this-skill-folder>/scripts/check_evidence.py claims.json --sources <files or folders> --format markdown --lang en
   ```
   Use `--lang zh` when talking to the user in Chinese.
4. **Read each supported claim against its quote** and ask: does the quote state exactly this, including negations (not, no, 不, 没有), conditions (if, only, 仅), and scope (all, some, 每个)? If not, fix the claim or drop it.
5. Fix every claim the script did not pass (table below), run the script again, and repeat until every claim you keep passes.
6. Answer the user. Put the quote and its source under each fact. If nothing in the sources answers the question, say so plainly and name the closest passage; do not fill the gap from general knowledge.

## Mode B: check a draft

1. Split the draft into claims, one fact per claim. Keep facts that can be wrong: dates, times, deadlines, numbers, amounts, names, places, eligibility, promises ("free", "guaranteed", "always", "包退"), comparisons and superlatives. Leave out opinions, greetings and instructions.
2. For each claim, look for a sentence in the sources that states it. Copy it character for character. If you cannot find one, give the claim an empty `evidence` list; do not stretch a loosely related sentence to fit.
3. Run the script as in Mode A, step 3.
4. Do Mode A, step 4 for every claim the script passed.
5. Report back (format below). **Do not silently rewrite the user's draft.** For each problem, suggest one fix: correct the detail to match the quote, soften it, add the missing source, or delete the claim.

## The claims file

```json
{
  "claims": [
    {
      "id": "1",
      "text": "Registration closes on 11 November at 18:00 MYT.",
      "evidence": [
        {"source": "workshop.md", "quote": "Registration closes on 11 November 2026 at 18:00 MYT."}
      ]
    },
    {"id": "2", "text": "Every participant receives a certificate.", "evidence": []}
  ]
}
```

- `source` is the file's path relative to the folder passed to `--sources`, or just its file name when it is unique.
- One claim may have several quotes; its numbers may be spread across them.
- Full field reference, matching rules and exit codes: `references/claims-format.md`.

## What each result means and what to do

| Result | Meaning | What to do |
|---|---|---|
| Supported | Quote found and every number in the claim is in it | Still do the meaning check (Mode A, step 4) |
| Quote not in source | The quote was changed, merged from two places, or invented | Copy the exact sentence, or drop the claim |
| Numbers not in the quote | The claim states a number the quote does not | Correct the number from the quote, or find the quote that states it |
| No evidence given | No quote for this claim | Find one, or mark the claim as unsupported |
| Cited source not found | The `source` name does not match any file | Use the file name the report lists |
| Quote too short to check | Under 6 characters (4 for Chinese) | Quote the whole sentence |

Exit code 0 means every claim passed, 1 means at least one did not, 2 means the input could not be read.

## Reporting to the user

Lead with the outcome, then the problems, then the supported claims. Keep quotes in the source language.

```markdown
**3 of 5 claims are backed by the documents; 2 are not.**

| Claim | Result | Source |
|---|---|---|
| Registration closes on 10 November | Number not in the quote: the document says 11 November | workshop.md, line 6: "Registration closes on 11 November 2026 at 18:00 MYT." |
| Participants get a certificate | No evidence | — |

Suggested fixes: change "10 November" to "11 November"; delete the certificate sentence.
```

If Python is not available, say that the quotes could not be checked automatically, still follow every other step, and label the answer as unchecked.
