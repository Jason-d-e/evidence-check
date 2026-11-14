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


NOTICE = """# Season notes: update notice 3

Answers were scored with ranker-v3.2.
Agreement was 0.996.
Venue hire cost RM 4,350.
"""


class Rules030(Base):
    """Rules added in 0.3.0 after real use; each passes the right claim and still flags a changed number."""

    def setUp(self):
        super().setUp()
        (self.dir / "docs" / "R07-update-notice-3.md").write_text(NOTICE, encoding="utf-8")
        self.sources = ce.load_sources([str(self.dir / "docs")])

    def test_month_before_a_year_counts_as_the_month(self):
        self.assertEqual(ce.numbers_in("published in December 2025"), {"12", "2025"})
        self.assertEqual(ce.numbers_in("You may join"), set())

    def test_fractions_compare_as_fractions(self):
        self.assertEqual(ce.numbers_in("约三分之一的会员"), {"1/3"})
        self.assertEqual(ce.numbers_in("about one-third of members"), {"1/3"})
        self.assertEqual(ce.numbers_in("two thirds"), {"2/3"})
        self.assertEqual(ce.numbers_in("a quarter of the budget"), {"1/4"})
        self.assertEqual(ce.numbers_in("paid in a quarter"), set())
        self.assertIn("1/3", ce.numbers_in("1/3 of the seats", generous=True))
        self.assertEqual(ce.numbers_in("百分之五十"), {"50"})

    def test_negated_one_is_not_one(self):
        self.assertEqual(ce.numbers_in("结果一次都没变"), set())
        self.assertEqual(ce.numbers_in("没有一次失败"), set())
        self.assertEqual(ce.numbers_in("有一次失败"), {"1"})

    def test_none_in_a_quote_is_zero(self):
        self.assertIn("0", ce.numbers_in("none of the runs failed", generous=True))
        self.assertEqual(ce.numbers_in("none of the runs failed"), set())

    def test_hundred_before_wan_without_a_numeral_is_not_a_number(self):
        self.assertEqual(ce.numbers_in("每百万 token 收费 0.10 美元"), {"0.1"})
        self.assertEqual(ce.numbers_in("数百人"), set())
        self.assertEqual(ce.numbers_in("三百人"), {"300"})

    def test_wan_and_million_scale_the_number(self):
        self.assertEqual(ce.numbers_in("4.3万人"), {"43000"})
        self.assertEqual(ce.numbers_in("三万人"), {"30000"})
        self.assertEqual(ce.numbers_in("4.3 million people"), {"4300000"})
        self.assertEqual(ce.numbers_in("4.3万人", generous=True), {"4.3", "43000"})
        self.assertEqual(ce.numbers_in("千万不要"), set())

    def test_percent_matches_decimal(self):
        quote = ("R07-update-notice-3.md", "Agreement was 0.996.")
        self.assertEqual(self.claim("Agreement was 99.6%.", quote)["status"], "supported")
        self.assertEqual(self.claim("Agreement was 96.6%.", quote)["missing_numbers"], ["96.6"])
        self.assertEqual(self.claim("The increase was 0.043.", ("support.txt", "a 4.3 per cent increase"))["status"], "supported")

    def test_name_with_digits_is_a_name_when_a_cited_source_has_it(self):
        quote = ("R07-update-notice-3.md", "Agreement was 0.996.")
        self.assertEqual(self.claim("ranker-v3.2 reached an agreement of 0.996.", quote)["status"], "supported")
        self.assertEqual(self.claim("ranker-v4.1 reached an agreement of 0.996.", quote)["missing_numbers"], ["4.1"])
        not_in_source = self.claim("ranker-v3.2 is free.", ("workshop.md", "Participation is free."))
        self.assertEqual(not_in_source["missing_numbers"], ["3.2"])
        self.assertEqual(ce._names_with_numbers("Q3, FY2026, RM50 and v2"), ["v2"])

    def test_currency_code_before_digits_is_still_an_amount(self):
        quote = ("R07-update-notice-3.md", "Venue hire cost RM 4,350.")
        self.assertEqual(self.claim("Venue hire cost RM4,350.", quote)["status"], "supported")
        self.assertEqual(self.claim("Venue hire cost RM4,530.", quote)["missing_numbers"], ["4530"])

    def test_cited_document_title_is_a_name(self):
        quote = ("R07-update-notice-3.md", "Agreement was 0.996.")
        self.assertEqual(self.claim("Update notice 3 says agreement was 0.996.", quote)["status"], "supported")
        self.assertEqual(self.claim("Update notice 4 says agreement was 0.996.", quote)["missing_numbers"], ["4"])


RULES_ZH = """# 评分规则

## 第 6 条 截止时间

作品要在周日下午 2 点前提交。

## 第 7 条 迟交

迟交的作品不参加评审。

## Results

Agreement was 0.314. The refusal rate was 16.5%. The sample held 123 answers. Membership reached 85,252 people.
Scoring started at 22:18:30.
Just under a third (8 of 25) were rejected. Results are published once a quarter.
SigLIP 2 was the image model. It found 5 violations.
“一次提示词”组只看广告本身。这一组拦下了 30 条。
"""


class Rules040(Base):
    """Rules added in 0.4.0 after real use; each passes the right claim and still flags a changed one."""

    def setUp(self):
        super().setUp()
        (self.dir / "docs" / "rules.md").write_text(RULES_ZH, encoding="utf-8")
        self.sources = ce.load_sources([str(self.dir / "docs")])

    def test_rounding_keeps_two_significant_digits_and_is_reported(self):
        quote = ("rules.md", "Agreement was 0.314.")
        r = self.claim("Agreement was 0.31.", quote)
        self.assertEqual(r["status"], "supported")
        self.assertEqual(r["rounded"], [{"claim": "0.31", "quote": "0.314"}])
        self.assertEqual(self.claim("Agreement was 0.32.", quote)["missing_numbers"], ["0.32"])
        self.assertEqual(self.claim("Agreement was 0.3.", quote)["missing_numbers"], ["0.3"])
        self.assertEqual(self.claim("The refusal rate was 17%.", ("rules.md", "The refusal rate was 16.5%."))["status"], "supported")

    def test_rounding_never_turns_an_integer_into_tens(self):
        self.assertEqual(self.claim("The sample held 120 answers.", ("rules.md", "The sample held 123 answers."))["missing_numbers"], ["120"])

    def test_rounding_with_wan(self):
        quote = ("rules.md", "Membership reached 85,252 people.")
        self.assertEqual(self.claim("会员约 8.5 万人。", quote)["rounded"], [{"claim": "85000", "quote": "85252"}])
        self.assertEqual(self.claim("会员约 9 万人。", quote)["missing_numbers"], ["90000"])

    def test_rounded_match_is_shown_in_the_report(self):
        report = ce.check([{"id": "1", "text": "Agreement was 0.31.", "evidence": [{"source": "rules.md", "quote": "Agreement was 0.314."}]}], self.sources)
        self.assertIn("四舍五入后对上: 0.31 ← 0.314", ce.render(report, "markdown", "zh"))

    def test_ordinal_in_the_heading_above_the_quote_is_a_name(self):
        quote = ("rules.md", "作品要在周日下午 2 点前提交。")
        self.assertEqual(self.claim("第 6 条规定作品要在周日下午 2 点前提交。", quote)["status"], "supported")
        self.assertEqual(self.claim("第六条规定作品要在周日下午 2 点前提交。", quote)["status"], "supported")
        # 第 7 条 is in the same document, but not above this quote.
        self.assertEqual(self.claim("第 7 条规定作品要在周日下午 2 点前提交。", quote)["missing_numbers"], ["7"])

    def test_quoted_name_in_the_source_is_a_name(self):
        quote = ("rules.md", "这一组拦下了 30 条。")
        self.assertEqual(self.claim("“一次提示词”组拦下了 30 条。", quote)["status"], "supported")
        self.assertEqual(self.claim("“两次提示词”组拦下了 30 条。", quote)["missing_numbers"], ["2"])

    def test_a_third_without_of_is_a_fraction_but_a_quarter_is_not(self):
        self.assertEqual(self.claim("不到三分之一被拒绝。", ("rules.md", "Just under a third (8 of 25) were rejected."))["status"], "supported")
        self.assertEqual(self.claim("四分之一的结果已公布。", ("rules.md", "Results are published once a quarter."))["missing_numbers"], ["1/4"])

    def test_quote_time_with_seconds_also_gives_the_minute(self):
        quote = ("rules.md", "Scoring started at 22:18:30.")
        self.assertEqual(self.claim("Scoring started at 22:18.", quote)["status"], "supported")
        self.assertEqual(self.claim("Scoring started at 22:18:45.", quote)["missing_numbers"], ["22:18:45"])
        self.assertEqual(ce.numbers_in("at 22:18:30"), {"22:18:30"})

    def test_mixed_case_name_with_a_spaced_version(self):
        quote = ("rules.md", "It found 5 violations.")
        self.assertEqual(self.claim("SigLIP 2 found 5 violations.", quote)["status"], "supported")
        self.assertEqual(self.claim("SigLIP 3 found 5 violations.", quote)["missing_numbers"], ["3"])


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
