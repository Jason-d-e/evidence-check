"""Offline tests for the v2 evaluation cases and scorer (no network, no model calls).

Run from the project root:  python -m unittest discover -s tests -v
"""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("score_v2", ROOT / "eval" / "v2" / "score.py")
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class Cases(unittest.TestCase):
    def test_cases_are_consistent(self):
        # Gold quotes exist, markers occur once, a perfect output scores perfectly.
        self.assertEqual(score.check_cases(), [])

    def test_frozen_script_is_the_one_the_v2_run_used(self):
        # The script has moved on since v2 (0.3.0); the frozen copy must stay as recorded in PREREGISTRATION.md.
        frozen = (ROOT / "eval" / "v2" / "frozen" / "check_evidence.py").read_bytes()
        self.assertEqual(hashlib.sha256(frozen).hexdigest()[:12], "f820b173a356")


class Answers(unittest.TestCase):
    def answer(self, qid, *texts, status="answered"):
        q = score.QUESTIONS[qid]
        return score.score_answer(q, {"status": status, "claims": [{"text": t, "evidence": []} for t in texts]}, False)

    def test_reply_type_uses_the_output_schema_values(self):
        # Found in the first scoring of run-2026-11-12: "answer" in cases.json vs "answered" in the schema.
        self.assertTrue(self.answer("FQ02", "Submission closes at 14:00.")["type_ok"])
        self.assertFalse(self.answer("FQ02", "Not stated.", status="not_in_documents")["type_ok"])
        self.assertTrue(self.answer("FQ07", status="not_in_documents")["type_ok"])

    def test_arm_comes_from_the_provider_id(self):
        # Found in the same scoring: promptfoo stored the label "skill" for both skill arms.
        self.assertEqual(score.arm_of({"provider": {"id": "evidence-check-v2:skill-v0.1", "label": "skill"}}), "skill-v0.1")
        self.assertEqual(score.arm_of({"provider": {"id": "evidence-check-v2:plain", "label": "plain"}}), "plain")

    def test_a_calculated_duration_is_an_invented_number(self):
        r = self.answer("FQ06", "Build Weekend lasts 32 hours, from 09:00 on Saturday to 17:00 on Sunday.")
        self.assertEqual(r["invented"], ["32"])
        self.assertEqual(r["keys"], [("start and end", True)])

    def test_the_superseded_deadline_is_caught_unless_the_new_one_is_given(self):
        self.assertEqual(self.answer("FQ02", "Submission closes at 13:00 on Sunday.")["outdated"], ["submission deadline"])
        self.assertEqual(self.answer("FQ02", "Submission now closes at 14:00 instead of 13:00.")["outdated"], [])

    def test_a_deadline_from_another_passage_is_outside_the_relevant_passages(self):
        r = self.answer("FQ02", "Submission closes at 14:00.", "Bring your laptop by 08:15.")
        self.assertEqual(r["outside"], ["8:15"])
        self.assertEqual(r["invented"], [])

    def test_script_mode_drops_claims_that_fail(self):
        q = score.QUESTIONS["FQ03"]
        out = {"status": "answered", "claims": [
            {"text": "The grant is up to RM 400.", "evidence": [{"source": "B02-update-notice-1.md",
                                                                  "quote": "The maximum travel grant rises from RM 300 to RM 400 per participant."}]},
            {"text": "Flights are covered up to RM 900.", "evidence": []}]}
        self.assertEqual(score.score_answer(q, out, False)["invented"], ["900"])
        self.assertEqual(score.score_answer(q, out, True)["invented"], [])


class Drafts(unittest.TestCase):
    def test_a_merged_claim_counts_for_the_error_not_as_a_false_alarm(self):
        d = score.DRAFTS["DE1"]
        out = {"claims": [{"draft_text": "The event runs from Saturday 16 January at 09:00 to Sunday 17 January at 17:00 MYT in Hall B",
                           "text": "The event is in Hall B from 16 January at 09:00.", "verdict": "unsupported", "evidence": []}]}
        r = score.score_draft(d, out, False)
        self.assertEqual(r["caught"], {0})
        self.assertEqual(r["false_alarm"], set())

    def test_script_mode_flags_a_claim_whose_number_is_not_in_its_quote(self):
        d = score.DRAFTS["DE2"]
        out = {"claims": [{"draft_text": "That's 32 hours of non-stop hacking!", "text": "The event is 32 hours long.",
                           "verdict": "supported", "evidence": [{"source": "B01-build-weekend-handbook.md",
                           "quote": "Build Weekend runs from Saturday 16 January 2027 at 09:00 to Sunday 17 January 2027 at 17:00 MYT."}]}]}
        self.assertEqual(score.score_draft(d, out, False)["caught"], set())
        self.assertEqual(score.score_draft(d, out, True)["caught"], {2})


if __name__ == "__main__":
    unittest.main()
