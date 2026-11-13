#!/usr/bin/env python3
"""Check that each claim is backed, word for word, by the sources it cites.

For every claim in a claims file this script checks two things:
  1. every quote appears in the cited source file (spacing, letter case, curly
     quotes, dashes and full-width characters are ignored; if that fails, a
     second pass also ignores punctuation);
  2. every number the claim states also appears in its quotes. Dates, times
     and amounts are where invented or shifted facts hide most often.

It cannot tell whether a real quote actually means what the claim says. That
judgement stays with the agent and the reader.

Usage:
  python check_evidence.py CLAIMS.json --sources PATH [PATH ...]
                           [--format text|markdown|json] [--lang en|zh]

Exit codes: 0 = every claim is supported, 1 = at least one claim is not,
            2 = the input could not be read.
Standard library only; Python 3.9 or later.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

__version__ = "0.3.0"

TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".rst", ".csv", ".tsv", ".json", ".jsonl",
    ".yaml", ".yml", ".html", ".htm", ".xml", ".tex",
}
MAX_SOURCE_BYTES = 5_000_000

# Markdown table bars and code ticks are dropped in the loose pass, like punctuation,
# so a quote copied from a table row without its bars still matches.
LOOSE_DROP = {"|", "`"}

# Characters treated as the same when matching quotes.
CHAR_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"', "\u2033": '"',
    "\u300c": '"', "\u300d": '"', "\u300e": '"', "\u300f": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2015": "-", "\u2212": "-",
}

STATUS_ORDER = [
    "unknown_source",
    "quote_not_found",
    "quote_too_short",
    "no_evidence",
    "numbers_not_in_quote",
    "supported",
]

LABELS = {
    "en": {
        "supported": "Supported",
        "unknown_source": "Cited source not found",
        "quote_not_found": "Quote not in source",
        "quote_too_short": "Quote too short to check",
        "no_evidence": "No evidence given",
        "numbers_not_in_quote": "Numbers not in the quote",
        "missing": "missing numbers",
        "line": "line",
        "loose": "matched after ignoring punctuation",
        "summary": "{ok} of {n} claims supported; {bad} not supported.",
        "header": ["#", "Claim", "Result", "Evidence"],
    },
    "zh": {
        "supported": "有依据",
        "unknown_source": "找不到所引的资料",
        "quote_not_found": "原文里没有这句引文",
        "quote_too_short": "引文太短，无法核对",
        "no_evidence": "没有给出依据",
        "numbers_not_in_quote": "数字在引文里找不到",
        "missing": "找不到的数字",
        "line": "第 {n} 行",
        "loose": "忽略标点后对上",
        "summary": "{n} 条说法中 {ok} 条有依据，{bad} 条没有。",
        "header": ["#", "说法", "结果", "依据"],
    },
}


# ---------------------------------------------------------------- matching

def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x3400 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2FA1F
        or 0x3040 <= code <= 0x30FF
        or 0xAC00 <= code <= 0xD7AF
    )


def normalize_with_map(text: str, loose: bool = False):
    """Return (normalized text, map from each normalized char to its index in `text`).

    Strict form: NFKC, curly quotes and dashes unified, runs of whitespace become
    one space, lower case. Loose form additionally drops all whitespace and
    punctuation, so a missing comma or an extra space does not block a match.
    """
    out, index_map = [], []
    pending_space = False
    for i, ch in enumerate(text):
        for c in unicodedata.normalize("NFKC", ch):
            c = CHAR_MAP.get(c, c)
            if c.isspace():
                pending_space = bool(out)
                continue
            if loose and (unicodedata.category(c).startswith("P") or c in LOOSE_DROP):
                continue
            if pending_space and not loose:
                out.append(" ")
                index_map.append(i)
            pending_space = False
            for lc in c.lower():
                out.append(lc)
                index_map.append(i)
    return "".join(out), index_map


def _trim_quote(q: str) -> str:
    """Drop punctuation and spaces at both ends (a quote often loses its full stop)."""
    start, end = 0, len(q)
    while start < end and (q[start].isspace() or unicodedata.category(q[start]).startswith("P")):
        start += 1
    while end > start and (q[end - 1].isspace() or unicodedata.category(q[end - 1]).startswith("P")):
        end -= 1
    return q[start:end]


class Source:
    def __init__(self, source_id: str, path: Path, text: str):
        self.id = source_id
        self.path = path
        self.text = unicodedata.normalize("NFC", text)
        self.strict, self.strict_map = normalize_with_map(self.text)
        self.loose, self.loose_map = normalize_with_map(self.text, loose=True)

    def line_of(self, index: int) -> int:
        return self.text.count("\n", 0, index) + 1

    def find(self, quote: str):
        """Return (match_type, line) or (None, None)."""
        q = _trim_quote(normalize_with_map(unicodedata.normalize("NFC", quote))[0])
        if q:
            at = self.strict.find(q)
            if at != -1:
                return "exact", self.line_of(self.strict_map[at])
        ql = normalize_with_map(unicodedata.normalize("NFC", quote), loose=True)[0]
        if ql:
            at = self.loose.find(ql)
            if at != -1:
                return "loose", self.line_of(self.loose_map[at])
        return None, None


def quote_long_enough(quote: str) -> bool:
    ql = normalize_with_map(quote, loose=True)[0]
    if any(_is_cjk(c) for c in ql):
        return len(ql) >= 4
    return len(ql) >= 6


# ---------------------------------------------------------------- numbers

EN_NUMBER_WORDS = {
    "zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}
# "one" is left out on purpose: in prose it is usually a pronoun ("one of the ...").
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
# A lone 一 is usually "a" ("一封邮件" = an email); in a claim it counts only
# before a unit of time or quantity.
CN_ONE_UNITS = "月日号天周年岁人名位次场份条项倍"
CN_ONE_UNIT_WORDS = ("小时", "分钟", "星期", "个月", "个小时", "个星期", "个工作日", "个钟")
# Words whose numerals are not numbers: 十分 (very), 千万 (by all means),
# 万一 (in case), 一一 (one by one), 统一 (unify), 唯一 (only), 第一 (first) ...
CN_NOT_NUMBERS = [
    r"十分(?!钟)", r"千万", r"万一", r"一一", r"[统唯同之第专逐单划这那每哪某]一",
    r"一(?=[些样直定般切起共致旦边下律概并])", r"零(?=[基门成风距])",
    r"(?:周|星期|礼拜)[一二三四五六七日天]",  # weekdays: 周五 is Friday, not 5
    r"二维码", r"三明治", r"四处", r"十字",  # QR code, sandwich, everywhere, cross
    r"(?:没有|没|无|未)一(?=[次个件条项处位名回])",  # 没有一次: not once
    r"一[次个件条项处位名回]?(?=[都也](?:没|不|未|无))",  # 一次都没变: never changed
    r"(?<![零〇一二两三四五六七八九十\d.])[百千](?=[万亿])",  # 每百万: per million
    r"(?<=[数几上成])[百千]",  # 数百, 上千: hundreds, thousands
]


def _cn_to_int(s: str) -> int:
    total, current = 0, 0
    for ch in s:
        if ch in CN_DIGITS:
            current = CN_DIGITS[ch]
        else:
            total += (current or 1) * CN_UNITS[ch]
            current = 0
    return total + current


def _convert_chinese_numerals(text: str, generous: bool = False) -> str:
    # 百分之五十 -> 50%
    text = re.sub(r"百分之([零〇一二两三四五六七八九十百]+)", lambda m: str(_cn_to_int(m.group(1))) + "%", text)
    protected = set()
    for pattern in CN_NOT_NUMBERS:
        for m in re.finditer(pattern, text):
            protected.update(range(m.start(), m.end()))

    def repl(m: re.Match) -> str:
        run = m.group(0)
        if protected.intersection(range(m.start(), m.end())):
            return run
        if run == "一" and not generous:
            after = text[m.end():m.end() + 4]
            if not after or (after[0] not in CN_ONE_UNITS and not after.startswith(CN_ONE_UNIT_WORDS)):
                return run
        # Spaces keep a converted numeral from merging with digits next to it.
        if len(run) > 1 and all(c in CN_DIGITS for c in run):
            return " " + "".join(str(CN_DIGITS[c]) for c in run) + " "  # 二〇二六 -> 2026
        return f" {_cn_to_int(run)} "

    return re.sub(r"[零〇一二两三四五六七八九十百千]+", repl, text)


def _to_24h(text: str) -> str:
    def en(m: re.Match) -> str:
        hour, minute, ampm = int(m.group(1)), m.group(2) or "00", m.group(3).replace(".", "").lower()
        if hour > 12:
            return m.group(0)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour}:{minute}"

    text = re.sub(r"(?<![\d.:])(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", en, text, flags=re.I)

    def zh(m: re.Match) -> str:
        hour = int(m.group(2))
        if hour < 12:
            hour += 12
        return f"{m.group(1)}{hour}{m.group(3)}"  # the part of the day stays, so _zh_clock sees a time

    return re.sub(r"(下午|晚上|傍晚)\s*(\d{1,2})\s*([点時时:：])", zh, text)


# 10点半 -> 10:30, 10点15分 -> 10:15, and 10点 -> 10:00 where it reads as a clock time
# (after a part of the day, or before 前/后/到/截止 ...). "有3点要注意" (three points) stays 3.
ZH_DAY_PARTS = r"(?:上午|中午|下午|晚上|傍晚|早上|早晨|凌晨)"
ZH_AFTER_CLOCK = r"(?=整|钟|前|后|以前|之前|以后|之后|到|至|开|关|闭|起|截止|结束|左右|准时|$|[，。,.;；、!！?？)）\s])"


def _zh_clock(text: str) -> str:
    text = re.sub(r"(\d{1,2})\s*[点時时]\s*半", lambda m: f"{int(m.group(1))}:30", text)
    text = re.sub(r"(\d{1,2})\s*[点時时]\s*(\d{1,2})\s*分", lambda m: f"{int(m.group(1))}:{int(m.group(2)):02d}", text)
    text = re.sub(ZH_DAY_PARTS + r"\s*(\d{1,2})\s*[点時时]", lambda m: f"{int(m.group(1))}:00", text)
    return re.sub(r"(\d{1,2})\s*[点時时]" + ZH_AFTER_CLOCK, lambda m: f"{int(m.group(1))}:00", text)


# A clock time is compared as one token, so 13:30 does not pass on a quote that
# only has 13:00 and 14:30.
TIME_RE = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])")


def _canonical(token: str) -> str:
    if "." in token:
        whole, frac = token.split(".", 1)
        whole = str(int(whole))
        frac = frac.rstrip("0")
        return f"{whole}.{frac}" if frac else whole
    return str(int(token))


def _canon_dec(value: Decimal) -> str:
    return _canonical(format(value.normalize(), "f"))


# Fractions compare as fractions: 三分之一, one-third and (in a quote) 1/3 are all "1/3".
EN_NUMERATORS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9}
EN_DENOMINATORS = {"half": 2, "halves": 2, "third": 3, "thirds": 3, "quarter": 4, "quarters": 4,
                   "fourth": 4, "fourths": 4, "fifth": 5, "fifths": 5, "sixth": 6, "sixths": 6,
                   "eighth": 8, "eighths": 8, "tenth": 10, "tenths": 10}
CN_FRACTION_RE = re.compile(r"([零〇一二两三四五六七八九十百\d]+)分之([零〇一二两三四五六七八九十\d]+)")
EN_FRACTION_RE = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|an?)[\s-]+(" + "|".join(EN_DENOMINATORS) + r")\b", re.I)
# 万, 亿, thousand, million and billion scale the number before them: 4.3万 = 43,000.
SCALES = {"万": 10_000, "亿": 100_000_000, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
SCALE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万|亿|thousand\b|million\b|billion\b)", re.I)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b|per cent\b)", re.I)


def _cn_or_digits(s: str) -> int:
    return int(s) if s.isdigit() else _cn_to_int(s)


def _take_fractions(t: str, generous: bool, fractions: set) -> str:
    def cn(m: re.Match) -> str:
        if m.group(1) == "百":
            return m.group(0)  # 百分之 is a percentage, handled elsewhere
        fractions.add(f"{_cn_or_digits(m.group(2))}/{_cn_or_digits(m.group(1))}")
        return " "

    def en(m: re.Match) -> str:
        num = m.group(1).lower()
        if num in ("a", "an") and not re.match(r"\s+of\b", m.string[m.end():m.end() + 4], re.I):
            return m.group(0)  # "a quarter" alone may be three months; "a quarter of" is 1/4
        fractions.add(f"{EN_NUMERATORS[num]}/{EN_DENOMINATORS[m.group(2).lower()]}")
        return " "

    t = CN_FRACTION_RE.sub(cn, t)
    t = EN_FRACTION_RE.sub(en, t)
    if generous:
        for a, b in re.findall(r"(?<![\d/.])(\d{1,2})/(\d{1,2})(?![\d/])", t):
            fractions.add(f"{int(a)}/{int(b)}")
    return t


def _scale(t: str, generous: bool) -> str:
    def repl(m: re.Match) -> str:
        try:
            value = Decimal(m.group(1)) * SCALES[m.group(2).lower()]
        except InvalidOperation:
            return m.group(0)
        scaled = format(value.normalize(), "f")
        return f" {m.group(1)} {scaled} " if generous else f" {scaled} "

    return SCALE_RE.sub(repl, t)


def numbers_in(text: str, generous: bool = False) -> set:
    """Every number a sentence states, in a form that can be compared across languages.

    Claims are read strictly. Quotes are read generously (`generous=True`): "one",
    "a week", "none" and a lone 一 also count, so a claim is not flagged just because
    its source wrote the number as a word.
    """
    t = unicodedata.normalize("NFKC", text)
    fractions = set()
    t = _take_fractions(t, generous, fractions)
    t = _convert_chinese_numerals(t, generous)
    t = _to_24h(t)
    t = _zh_clock(t)
    t = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", t)  # 20,000 -> 20000
    t = _scale(t, generous)
    times = set()

    def take_time(m: re.Match) -> str:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 24 or minute > 59:
            return m.group(0)
        times.add(f"{hour}:{minute:02d}")
        return " "

    t = TIME_RE.sub(take_time, t)
    found = {_canonical(n) for n in re.findall(r"\d+(?:\.\d+)?", t)} | times | fractions
    low = t.lower()
    for word in re.findall(r"[a-z]+", low):
        if word in EN_NUMBER_WORDS:
            found.add(str(EN_NUMBER_WORDS[word]))
    if generous and re.search(r"\b(?:one|single|an?\s+(?:day|week|month|year|hour|minute|time|person|place))\b", low):
        found.add("1")
    if generous and re.search(r"\bnone\b", low):
        found.add("0")
    # Month names count only next to a day number or a year, so the verb "may" is never May.
    for m in re.finditer(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_RE})\b"
                         rf"|\b({MONTH_RE})\.?\s+\d{{1,2}}\b"
                         rf"|\b({MONTH_RE})\.?,?\s+(?:19|20)\d\d\b", low):
        found.add(str(MONTHS[m.group(1) or m.group(2) or m.group(3)]))
    return found


def percents_in(text: str) -> set:
    """Numbers written as percentages (99.6%, 百分之五十), so a claim's 99.6% can match a quote's 0.996."""
    t = _convert_chinese_numerals(unicodedata.normalize("NFKC", text), generous=True)
    return {_canonical(n) for n in PERCENT_RE.findall(t)}


# A name with digits attached (ranker-v3.2, echo-asr-2025-08-28, p90, B02) is a name,
# not a quantity, when it also appears in a cited source. Currency codes (RM4,350) and
# quarters or halves of a year (Q3, H1, FY2026) stay numbers.
IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*(?![A-Za-z0-9])")
NUMBER_PREFIXES = {"rm", "rmb", "myr", "usd", "us", "sgd", "hkd", "hk", "aud", "eur", "gbp", "cny", "jpy",
                   "cad", "nzd", "inr", "rs", "nt", "q", "h", "fy"}


def _names_with_numbers(text: str) -> list:
    out = []
    for m in IDENTIFIER_RE.finditer(unicodedata.normalize("NFKC", text)):
        token = m.group(0)
        prefix = re.match(r"[A-Za-z]+", token).group(0).lower()
        if any(ch.isdigit() for ch in token) and not (prefix in NUMBER_PREFIXES and token[len(prefix):][:1].isdigit()):
            out.append(token)
    return out


def _title_phrases(src) -> set:
    """The cited document's own name, from its file name and first heading: 'update notice 2'."""
    stem = re.sub(r"^[A-Za-z]*\d+[-_ ]+", "", Path(src.id).stem)
    names = {re.sub(r"[-_]+", " ", stem)}
    heading = re.search(r"^#{1,6}\s+(.+?)\s*$", src.text, re.M)
    if heading:
        names.add(heading.group(1))
        names.add(heading.group(1).rsplit(":", 1)[-1])
    phrases = set()
    for name in names:
        name = " ".join(unicodedata.normalize("NFKC", name).lower().split())
        if re.search(r"\d", name) and re.search(r"[a-z一-鿿]", name):
            phrases.add(name)
    return phrases


def _without_names(text: str, cited) -> str:
    """The claim with cited documents' titles and names-with-digits that the sources contain taken out."""
    t = unicodedata.normalize("NFKC", text)
    for src in cited:
        for phrase in _title_phrases(src):
            pattern = r"[\s_-]+".join(re.escape(w) for w in phrase.split())
            t = re.sub(r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])", " ", t, flags=re.I)
    haystack = " ".join(unicodedata.normalize("NFKC", s.text).lower() + " " + s.id.lower() for s in cited)
    for token in _names_with_numbers(t):
        if re.search(r"(?<![a-z0-9])" + re.escape(token.lower()) + r"(?![a-z0-9])", haystack):
            t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", " ", t)
    return t


# ---------------------------------------------------------------- loading

def load_sources(paths):
    sources = {}
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in TEXT_EXTENSIONS:
                    _add_source(sources, f.relative_to(p).as_posix(), f)
        elif p.is_file():
            _add_source(sources, p.name, p)
        else:
            raise ValueError(f"source path not found: {raw}")
    if not sources:
        raise ValueError("no readable source files were given")
    return sources


def _add_source(sources, source_id, path):
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"source file too large (over 5 MB): {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as err:
        raise ValueError(f"source file is not UTF-8 text: {path}") from err
    sources[source_id] = Source(source_id, path, text)


def resolve_source(sources, ref: str):
    ref = (ref or "").strip().replace("\\", "/")
    if ref in sources:
        return sources[ref]
    matches = [s for sid, s in sources.items() if sid.endswith("/" + ref) or Path(sid).name == ref or Path(sid).stem == ref]
    return matches[0] if len(matches) == 1 else None


def load_claims(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError as err:
        raise ValueError(f"claims file not found: {path}") from err
    except json.JSONDecodeError as err:
        raise ValueError(f"claims file is not valid JSON: {err}") from err
    claims = data.get("claims") if isinstance(data, dict) else data
    if not isinstance(claims, list):
        raise ValueError('claims file must be a list of claims or an object with a "claims" list')
    for n, c in enumerate(claims, 1):
        if not isinstance(c, dict) or not isinstance(c.get("text"), str):
            raise ValueError(f'claim {n} needs a "text" string')
        ev = c.get("evidence", [])
        if not isinstance(ev, list) or any(not isinstance(e, dict) for e in ev):
            raise ValueError(f'claim {n}: "evidence" must be a list of {{"source", "quote"}} objects')
        c.setdefault("id", str(n))
    return claims


# ---------------------------------------------------------------- checking

def _same_as_percent(n, claim_percents, quote_numbers, quote_percents) -> bool:
    """99.6% in a claim matches 0.996 in a quote, and 0.996 matches 99.6%."""
    if "/" in n or ":" in n:
        return False
    d = Decimal(n)
    if n in claim_percents and _canon_dec(d / 100) in quote_numbers:
        return True
    return d < 1 and _canon_dec(d * 100) in quote_percents


def check_claim(claim, sources):
    problems = set()
    evidence_out = []
    quote_numbers = set()
    quote_percents = set()
    cited = []
    years_in_sources = set()
    for e in claim.get("evidence", []):
        quote = str(e.get("quote", ""))
        src = resolve_source(sources, str(e.get("source", "")))
        item = {"source": e.get("source"), "quote": quote, "found": False, "match": None, "line": None}
        if src is None:
            problems.add("unknown_source")
        elif not quote_long_enough(quote):
            problems.add("quote_too_short")
        else:
            match, line = src.find(quote)
            if match:
                item.update(found=True, match=match, line=line, source=src.id)
                quote_numbers |= numbers_in(quote, generous=True)
                quote_percents |= percents_in(quote)
                if src not in cited:
                    cited.append(src)
                years_in_sources |= set(re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", unicodedata.normalize("NFKC", src.text)))
            else:
                problems.add("quote_not_found")
        evidence_out.append(item)

    if not evidence_out:
        problems.add("no_evidence")

    missing = []
    if not problems:
        claim_text = _without_names(claim["text"], cited)
        claim_percents = percents_in(claim_text)
        for n in sorted(numbers_in(claim_text), key=lambda x: (len(x), x)):
            if n in quote_numbers:
                continue
            if re.fullmatch(r"(19|20)\d\d", n) and n in years_in_sources:
                continue  # documents often state the year once, away from the date
            if _same_as_percent(n, claim_percents, quote_numbers, quote_percents):
                continue
            missing.append(n)
        if missing:
            problems.add("numbers_not_in_quote")

    status = next(s for s in STATUS_ORDER if s in problems or s == "supported")
    return {
        "id": str(claim["id"]),
        "text": claim["text"],
        "status": status,
        "problems": sorted(problems, key=STATUS_ORDER.index),
        "missing_numbers": missing,
        "evidence": evidence_out,
    }


def check(claims, sources):
    results = [check_claim(c, sources) for c in claims]
    ok = sum(r["status"] == "supported" for r in results)
    return {"summary": {"claims": len(results), "supported": ok, "not_supported": len(results) - ok}, "claims": results}


# ---------------------------------------------------------------- output

def _where(e, L):
    if not e["found"]:
        return f'{e["source"]}: "{e["quote"]}"'
    line = L["line"].format(n=e["line"]) if "{n}" in L["line"] else f'{L["line"]} {e["line"]}'
    loose = f' ({L["loose"]})' if e["match"] == "loose" else ""
    return f'{e["source"]}, {line}{loose}: "{e["quote"]}"'


def render(report, fmt="text", lang="en"):
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2)
    L = LABELS[lang]
    s = report["summary"]
    summary = L["summary"].format(n=s["claims"], ok=s["supported"], bad=s["not_supported"])
    lines = []
    if fmt == "markdown":
        lines += ["| " + " | ".join(L["header"]) + " |", "|---|---|---|---|"]
        for r in report["claims"]:
            result = L[r["status"]]
            if r["missing_numbers"]:
                result += f' ({L["missing"]}: {", ".join(r["missing_numbers"])})'
            ev = "<br>".join(_where(e, L) for e in r["evidence"]) or "—"
            cell = lambda x: x.replace("|", "\\|").replace("\n", " ")
            lines.append(f'| {r["id"]} | {cell(r["text"])} | {cell(result)} | {cell(ev)} |')
        lines += ["", summary]
    else:
        for r in report["claims"]:
            mark = "OK " if r["status"] == "supported" else "!! "
            lines.append(f'{mark}[{r["id"]}] {L[r["status"]]}: {r["text"]}')
            if r["missing_numbers"]:
                lines.append(f'     {L["missing"]}: {", ".join(r["missing_numbers"])}')
            for e in r["evidence"]:
                lines.append(f"     - {_where(e, L)}")
        lines += ["", summary]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check claims against the exact text of their sources.")
    parser.add_argument("claims", help="JSON file with the claims and their quotes")
    parser.add_argument("--sources", nargs="+", required=True, help="source files or folders")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    parser.add_argument("--lang", choices=["en", "zh"], default="en", help="language of the labels")
    args = parser.parse_args(argv)
    try:
        sources = load_sources(args.sources)
        claims = load_claims(args.claims)
    except (ValueError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    report = check(claims, sources)
    out = render(report, args.format, args.lang)
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return 0 if report["summary"]["not_supported"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
