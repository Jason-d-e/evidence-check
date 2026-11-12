"""Offline tests for scripts/check_evidence.py (no network, no model calls).

Run from the project root:  python -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "evidence-check" / "scripts" / "check_evidence.py"
spec = importlib.util.spec_from_file_location("check_evidence", SCRIPT)
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

WORKSHOP = """# DemoClub workshop

The Intro to AI Tools workshop takes place on 12 November 2026 from 19:00 to 20:30 MYT.
The capacity is 24 participants. Participation is free.

Registration closes on 11 November 2026 at 18:00 MYT. A confirmation email is sent by 11 November at 20:00 MYT.
Submitting the form does not guarantee a place.
"""
SUPPORT = """Support hours are Monday to Friday, 10:00 to 18:00 MYT.
The target first response time is two business days.
A password reset link expires after 30 minutes.
The grant is 20,000 dollars, a 4.3 per cent increase.
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "workshop.md").write_text(WORKSHOP, encoding="utf-8")
        # Written with a byte-order mark on purpose: it must not break matching.
        (self.dir / "docs" / "support.txt").write_text(SUPPORT, encoding="utf-8-sig")
        self.sources = ce.load_sources([str(self.dir / "docs")])

    def tearDown(self):
        self.tmp.cleanup()

    def claim(self, text, *evidence):
        return ce.check_claim(
            {"id": "c", "text": text, "evidence": [{"source": s, "quote": q} for s, q in evidence]},
            self.sources,
        )


class QuoteMatching(Base):
    def test_exact_quote_is_found_with_line_number(self):
        r = self.claim("The workshop has 24 places.", ("workshop.md", "The capacity is 24 participants."))
        self.assertEqual(r["status"], "supported")
        self.assertEqual(r["evidence"][0]["match"], "exact")
        self.assertEqual(r["evidence"][0]["line"], 4)

    def test_case_spacing_curly_quotes_and_full_width_are_ignored(self):
        r = self.claim("Registration closes at 18:00.", ("workshop.md", "REGISTRATION   closes on 11 November 2026 at １８:００ MYT"))
        self.assertEqual(r["status"], "supported")

    def test_missing_punctuation_matches_in_loose_mode(self):
        r = self.claim("Support works weekdays from 10:00 to 18:00.", ("support.txt", "Monday to Friday 10:00 to 18:00 MYT"))
        self.assertEqual(r["status"], "supported")
        self.assertEqual(r["evidence"][0]["match"], "loose")

    def test_fabricated_quote_is_rejected(self):
        r = self.claim("Every participant gets a certificate.", ("workshop.md", "Every participant receives a certificate."))
        self.assertEqual(r["status"], "quote_not_found")
        self.assertFalse(r["evidence"][0]["found"])

    def test_altered_word_inside_a_real_sentence_is_rejected(self):
        r = self.claim("Submitting the form guarantees a place.", ("workshop.md", "Submitting the form does guarantee a place."))
        self.assertEqual(r["status"], "quote_not_found")

    def test_unknown_source(self):
        r = self.claim("Free.", ("pricing.md", "Participation is free."))
        self.assertEqual(r["status"], "unknown_source")

    def test_source_can_be_named_by_stem(self):
        r = self.claim("Participation is free.", ("workshop", "Participation is free."))
        self.assertEqual(r["status"], "supported")
        self.assertEqual(r["evidence"][0]["source"], "workshop.md")

    def test_no_evidence(self):
        self.assertEqual(self.claim("Lunch is provided.")["status"], "no_evidence")

    def test_quote_too_short(self):
        r = self.claim("It is free.", ("workshop.md", "free"))
        self.assertEqual(r["status"], "quote_too_short")

    def test_table_row_quoted_without_its_bars(self):
        (self.dir / "docs" / "schedule.md").write_text(
            "| Time | Item |\n|---|---|\n| 13:00 | Project submission closes |\n| 14:30 | Demos start |\n", encoding="utf-8")
        sources = ce.load_sources([str(self.dir / "docs")])
        claim = {"id": "t", "text": "Submission closes at 13:00.",
                 "evidence": [{"source": "schedule.md", "quote": "13:00 Project submission closes"}]}
        r = ce.check_claim(claim, sources)
        self.assertEqual(r["status"], "supported", r)
        self.assertEqual(r["evidence"][0]["match"], "loose")
        self.assertEqual(r["evidence"][0]["line"], 3)


class Numbers(Base):
    def test_clock_time_is_compared_whole(self):
        # 13:30 must not pass just because 13 and 30 both occur in other times.
        quote = ("workshop.md", "The Intro to AI Tools workshop takes place on 12 November 2026 from 19:00 to 20:30 MYT.")
        r = self.claim("The workshop starts at 19:30.", quote)
        self.assertEqual(r["status"], "numbers_not_in_quote")
        self.assertEqual(r["missing_numbers"], ["19:30"])
        self.assertEqual(self.claim("工作坊晚上7点开始。", quote)["status"], "supported")

    def test_shifted_date_is_flagged_with_the_missing_number(self):
        r = self.claim("Registration closes on 10 November at 18:00.", ("workshop.md", "Registration closes on 11 November 2026 at 18:00 MYT."))
        self.assertEqual(r["status"], "numbers_not_in_quote")
        self.assertEqual(r["missing_numbers"], ["10"])

    def test_invented_deadline_on_a_real_quote_is_flagged(self):
        r = self.claim("Bring your laptop before 19:00 on 10 November.", ("workshop.md", "The capacity is 24 participants."))
        self.assertEqual(r["status"], "numbers_not_in_quote")

    def test_chinese_claim_with_english_quote(self):
        r = self.claim("报名在2026年11月11日18:00截止。", ("workshop.md", "Registration closes on 11 November 2026 at 18:00 MYT."))
        self.assertEqual(r["status"], "supported", r)

    def test_chinese_numerals(self):
        r = self.claim("密码重置链接三十分钟后失效。", ("support.txt", "A password reset link expires after 30 minutes."))
        self.assertEqual(r["status"], "supported", r)
        r = self.claim("回复时间目标是两个工作日。", ("support.txt", "The target first response time is two business days."))
        self.assertEqual(r["status"], "supported", r)

    def test_chinese_month_in_numerals(self):
        r = self.claim("工作坊在十一月十二日举行。", ("workshop.md", "takes place on 12 November 2026"))
        self.assertEqual(r["status"], "supported", r)

    def test_year_may_come_from_elsewhere_in_the_same_source(self):
        r = self.claim("The email is sent by 11 November 2026 at 20:00.", ("workshop.md", "A confirmation email is sent by 11 November at 20:00 MYT."))
        self.assertEqual(r["status"], "supported", r)

    def test_wrong_year_is_still_flagged(self):
        r = self.claim("The email is sent by 11 November 2025.", ("workshop.md", "A confirmation email is sent by 11 November at 20:00 MYT."))
        self.assertEqual(r["missing_numbers"], ["2025"])

    def test_twelve_hour_clock(self):
        r = self.claim("Registration closes at 6 pm.", ("workshop.md", "Registration closes on 11 November 2026 at 18:00 MYT."))
        self.assertEqual(r["status"], "supported", r)
        r = self.claim("报名下午6点截止。", ("workshop.md", "Registration closes on 11 November 2026 at 18:00 MYT."))
        self.assertEqual(r["status"], "supported", r)
        r = self.claim("Registration closes at 6 am.", ("workshop.md", "Registration closes on 11 November 2026 at 18:00 MYT."))
        self.assertEqual(r["status"], "numbers_not_in_quote")

    def test_words_that_look_like_numbers_but_are_not(self):
        r = self.claim("报名后会收到一封确认邮件，这一点十分重要。", ("workshop.md", "A confirmation email is sent by 11 November at 20:00 MYT."))
        self.assertEqual(r["status"], "supported", r)
        r = self.claim("You may register through the form.", ("workshop.md", "Submitting the form does not guarantee a place."))
        self.assertEqual(r["status"], "supported", r)

    def test_thousands_separator_and_decimals(self):
        r = self.claim("The grant is 20000 dollars, up 4.30 per cent.", ("support.txt", "The grant is 20,000 dollars, a 4.3 per cent increase."))
        self.assertEqual(r["status"], "supported", r)

    def test_number_extraction(self):
        self.assertEqual(ce.numbers_in("12 November 2026 at 18:00"), {"12", "11", "2026", "18:00"})
        self.assertEqual(ce.numbers_in("二〇二六年十一月"), {"2026", "11"})
        self.assertEqual(ce.numbers_in("百分之五十"), {"50"})
        self.assertEqual(ce.numbers_in("一个月内"), {"1"})
        self.assertEqual(ce.numbers_in("统一时间"), set())
        self.assertEqual(ce.numbers_in("零基础也能参加"), set())
        # Found by eval/v2/score.py --check: 二维码 (QR code) was read as 2.
        self.assertEqual(ce.numbers_in("进出都要扫二维码"), set())
        self.assertEqual(ce.numbers_in("一个工作日内回复"), {"1"})
        self.assertEqual(ce.numbers_in("有效期是一个小时"), {"1"})
        self.assertEqual(ce.numbers_in("这是一个工作坊"), set())
        # Found by eval/script_only.py: 周五10:00 was read as 510.
        self.assertEqual(ce.numbers_in("周一到周五10:00到18:00"), {"10:00", "18:00"})
        self.assertEqual(ce.numbers_in("星期三下午三点"), {"15:00"})
        self.assertEqual(ce.numbers_in("下午6点半截止"), {"18:30"})
        self.assertEqual(ce.numbers_in("10点15分开始"), {"10:15"})
        self.assertEqual(ce.numbers_in("上午九点开门"), {"9:00"})
        self.assertEqual(ce.numbers_in("周六晚上11点闭馆"), {"23:00"})
        self.assertEqual(ce.numbers_in("下午3:30开始"), {"15:30"})
        self.assertEqual(ce.numbers_in("有3点要注意"), {"3"})  # three points, not 3 o'clock
        self.assertEqual(ce.numbers_in("doors open at 7.30pm"), {"19:30"})
        self.assertEqual(ce.numbers_in("a 16:9 screen in Room 2.04"), {"16", "9", "2.04"})
        self.assertIn("1", ce.numbers_in("one of the places", generous=True))
        self.assertNotIn("1", ce.numbers_in("one of the places"))


class CommandLine(Base):
    def run_cli(self, claims, *extra):
        path = self.dir / "claims.json"
        path.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
        import sys
        err, buf = io.StringIO(), io.BytesIO()
        wrapper = io.TextIOWrapper(buf, encoding="utf-8")  # main() writes to sys.stdout.buffer
        real = sys.stdout
        sys.stdout = wrapper
        try:
            with redirect_stderr(err):
                code = ce.main([str(path), "--sources", str(self.dir / "docs"), *extra])
            wrapper.flush()
            out = buf.getvalue().decode("utf-8")
        finally:
            sys.stdout = real
            wrapper.detach()
        return code, out, err.getvalue()

    def test_exit_code_zero_when_all_supported(self):
        code, out, _ = self.run_cli({"claims": [{"id": "a", "text": "It is free.", "evidence": [{"source": "workshop.md", "quote": "Participation is free."}]}]})
        self.assertEqual(code, 0)
        self.assertIn("1 of 1 claims supported", out)

    def test_exit_code_one_and_markdown_table(self):
        claims = [
            {"id": "a", "text": "It is free.", "evidence": [{"source": "workshop.md", "quote": "Participation is free."}]},
            {"id": "b", "text": "There are 30 places.", "evidence": [{"source": "workshop.md", "quote": "The capacity is 24 participants."}]},
        ]
        code, out, _ = self.run_cli(claims, "--format", "markdown")
        self.assertEqual(code, 1)
        self.assertIn("| # | Claim | Result | Evidence |", out)
        self.assertIn("missing numbers: 30", out)

    def test_chinese_labels_and_json(self):
        claims = [{"text": "有 30 个名额。", "evidence": [{"source": "workshop.md", "quote": "The capacity is 24 participants."}]}]
        code, out, _ = self.run_cli(claims, "--lang", "zh")
        self.assertIn("数字在引文里找不到", out)
        code, out, _ = self.run_cli(claims, "--format", "json")
        self.assertEqual(json.loads(out)["claims"][0]["missing_numbers"], ["30"])

    def test_bad_input_exits_two(self):
        path = self.dir / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        err = io.StringIO()
        with redirect_stderr(err):
            code = ce.main([str(path), "--sources", str(self.dir / "docs")])
        self.assertEqual(code, 2)
        self.assertIn("not valid JSON", err.getvalue())


if __name__ == "__main__":
    unittest.main()
