import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_use_cli_workday as workday
from draft_guard import load_state, save_state


URL = "https://company.myworkdayjobs.com/Careers/job/Developer/apply/applyManually"
SESSION = "hidden-application"
SCHOOL = "primaryQuestionnaire--school"
DETAIL = "primaryQuestionnaire--schoolName"


class HiddenWorkday:
    def __init__(self):
        self.elapsed = 0
        self.step = 3
        self.answers = {SCHOOL: "Other"}
        self.missing_at = None
        self.reject_save = False
        self.discard_dialog = False
        self.disabled = False
        self.frames = 0
        self.next_frame_callback = None
        self.actions = []
        self.invalid = []

    def snapshot(self):
        if self.missing_at is not None and self.elapsed >= self.missing_at:
            self.answers.setdefault(DETAIL, "")
        missing = [field_id for field_id, answer in self.answers.items() if not answer]
        return {
            "url": URL, "step": self.step, "hidden": True, "busy": False,
            "canContinue": self.step < 5, "footerDisabled": self.disabled,
            "ready": self.step < 5 and not self.disabled and not self.discard_dialog,
            "dialog": "discard" if self.discard_dialog else None,
            "errors": ["University is required"] if self.invalid else [],
            "invalid": self.invalid, "missing": missing,
            "questions": list(self.answers.items()), "signIn": False,
        }

    def change_step(self):
        self.disabled = False
        if self.reject_save:
            self.invalid = [DETAIL]
        else:
            self.step += 1

    def cdp(self, method, *, session_id, **params):
        if session_id != SESSION:
            raise AssertionError(session_id)
        if method == "Page.captureScreenshot":
            self.frames += 1
            if self.next_frame_callback:
                callback, self.next_frame_callback = self.next_frame_callback, None
                callback()
            return {}
        if method != "Runtime.evaluate":
            raise AssertionError(f"Unexpected Chrome action: {method}")
        expression = params["expression"]
        if expression == f"({workday.SAVE_VIEW})()":
            value = self.snapshot()
        elif expression.startswith(f"({workday.CLICK_SAVE})("):
            if not self.snapshot()["ready"]:
                raise AssertionError("The helper clicked a disabled or final control.")
            self.actions.append("Save and Continue")
            self.disabled = True
            self.next_frame_callback = self.change_step
            value = True
        elif expression.startswith(f"({workday.KEEP_DRAFT})("):
            self.actions.append("Keep draft")
            self.next_frame_callback = lambda: setattr(self, "discard_dialog", False)
            value = True
        else:
            raise AssertionError(expression)
        return {"result": {"value": json.loads(json.dumps(value))}}

    def sleep(self, seconds):
        self.elapsed += seconds


class WorkdaySaveTests(unittest.TestCase):
    def test_waits_for_required_follow_up_before_first_save(self):
        page = HiddenWorkday()
        page.missing_at = 0.4
        result, active = self.run_saves(page)[0]
        self.assertEqual(result["status"], "needs_repair")
        self.assertEqual(result["missing"], [DETAIL])
        self.assertFalse(page.actions)
        self.assertNotIn("save", active)

    def test_validation_releases_continue_while_tab_stays_hidden(self):
        page = HiddenWorkday()
        page.reject_save = True

        def repair():
            page.answers[DETAIL] = "Example University"
            page.invalid = []
            page.reject_save = False

        (rejected, after_error), (saved, after_save) = self.run_saves(page, repair)
        self.assertEqual(rejected["status"], "needs_repair")
        self.assertEqual(rejected["invalid"], [DETAIL])
        self.assertNotIn("save", after_error)
        self.assertEqual(saved["status"], "advanced")
        self.assertEqual(saved["step"], 4)
        self.assertNotIn("save", after_save)
        self.assertEqual(page.actions, ["Save and Continue", "Save and Continue"])
        self.assertEqual(page.frames, 2)

    def test_dismisses_existing_discard_dialog_and_preserves_answers(self):
        page = HiddenWorkday()
        page.discard_dialog = True
        page.answers[DETAIL] = "Example University"
        result, _ = self.run_saves(page)[0]
        self.assertEqual(page.actions, ["Keep draft", "Save and Continue"])
        self.assertEqual(result["status"], "advanced")
        self.assertEqual(page.answers[DETAIL], "Example University")

    def run_saves(self, page, between=None):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "active-draft.json"
            save_state(state, {"active": {"tab_id": "42", "url": URL},
                               "pending_confirmations": [], "deferred": []})
            clock = SimpleNamespace(monotonic=lambda: page.elapsed, time=lambda: 10000 + page.elapsed,
                                    sleep=page.sleep)
            with patch.object(workday, "time", clock):
                results = []
                for repair in ([None, between] if between else [None]):
                    if repair:
                        repair()
                    result = workday.save_and_continue(page.cdp, SESSION, "42", URL, 3, state_path=state)
                    results.append((result, load_state(state)["active"]))
                return results
