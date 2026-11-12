# Claims file and checking rules

## Command

```bash
python scripts/check_evidence.py CLAIMS.json --sources PATH [PATH ...] [--format text|markdown|json] [--lang en|zh]
```

- `--sources` takes files, folders, or both. Folders are read recursively; only text files are read (`.md .markdown .txt .rst .csv .tsv .json .jsonl .yaml .yml .html .htm .xml .tex`), up to 5 MB each, as UTF-8 (a byte-order mark is fine).
- `--format json` returns the full report for further processing.
- Exit codes: `0` every claim supported, `1` at least one claim not supported, `2` the claims file or a source could not be read (the reason is printed on stderr).

## Claims file

Either an object with a `claims` list, or the list itself.

| Field | Required | Meaning |
|---|---|---|
| `id` | no | Any string; defaults to the claim's position (1, 2, ...) |
| `text` | yes | The claim, one fact, in any language |
| `evidence` | no | List of `{"source": ..., "quote": ...}`; an empty or missing list means "no evidence" |
| `evidence[].source` | yes | Path relative to a `--sources` folder (for example `policies/leave.md`), the file name, or the file name without extension, as long as it is unique |
| `evidence[].quote` | yes | Text copied character for character from that source |

## How quotes are matched

1. **Exact pass.** Both texts are normalised the same way: Unicode NFKC (full-width letters and digits become ordinary ones), curly quotes and corner brackets become straight quotes, all dashes become `-`, runs of whitespace become one space, letters become lower case. Punctuation and spaces at the two ends of the quote are ignored.
2. **Loose pass.** If the exact pass fails, all whitespace, punctuation, Markdown table bars (`|`) and code ticks are removed from both texts and the search is repeated, so a table row quoted without its bars still matches. A match here is reported as "matched after ignoring punctuation".
3. The report gives the line number in the source where the quote starts.

A quote must be at least 6 characters long after the loose normalisation (4 if it contains Chinese, Japanese or Korean characters).

## How numbers are compared

Numbers are collected from the claim and from all of its verified quotes, then compared as sets. Every number in the claim must be in the quotes.

- Digits, including decimals (`4.30` equals `4.3`) and thousands separators (`20,000` equals `20000`).
- English number words from *two* to *twenty*, the tens, and *hundred*. *One* is not read from a claim, because in prose it is usually a pronoun; in a quote, *one*, *a single*, and *a day/week/month/year/hour* do count as 1.
- English month names next to a day number (`12 November`, `Nov 12`) add the month number. The verb *may* is never read as May.
- Clock times are compared whole: `13:30` is not matched by a quote that has only `13:00` and `14:30`. 12-hour and Chinese times are converted first: `6 pm`, `6.00pm` and `下午6点` all become 18:00, `10点半` becomes 10:30. A bare `3点` counts as a time only after a part of the day (`上午`) or before words such as `前`, `到`, `开始`, `截止`; otherwise it is the number 3.
- Chinese numerals: `三十` is 30, `两` is 2, `二〇二六` is 2026, `百分之五十` is 50. A lone `一` counts in a claim only before a unit of time or quantity (`一个月`, `一周`, `一次`); words such as `一封`, `统一`, `这一点`, `十分`, `千万` are not read as numbers.
- A four-digit year (1900–2099) may also come from anywhere in the same source file.

Not converted: units (`4.3万` is not matched to `43,000`), Roman numerals, and spelled-out numbers above *hundred*. Such a claim is reported as "numbers not in the quote"; a person should then compare it by hand.

## Result order

A claim gets the first status that applies: cited source not found, quote not in source, quote too short, no evidence, numbers not in the quote, supported. The JSON report also lists every problem found for the claim and the missing numbers.

## What each result means and what to do

| Result | Meaning | What to do |
|---|---|---|
| Supported | Quote found and every number in the claim is in it | Still read the claim against the quote: the script cannot see meaning |
| Quote not in source | The quote was changed, merged from two places, or invented | Copy the exact sentence, or drop the claim |
| Numbers not in the quote | The claim states a number the quote does not | Correct the number from the quote, or add the quote that states it |
| No evidence given | No quote for this claim | Find one, or report the claim as unsupported |
| Cited source not found | The `source` name does not match any file | Use a file name the report lists |
| Quote too short to check | Under 6 characters (4 for Chinese) | Quote the whole sentence |
