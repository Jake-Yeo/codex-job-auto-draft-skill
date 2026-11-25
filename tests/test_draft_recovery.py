import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from attach_documents import attach
from draft_guard import draft_url


BACK_END = "https://example.icims.com/jobs/27217/back-end/candidate"
BACK_END_QUESTIONS = "https://example.icims.com/jobs/27217/back-end/questions?csrf=private"
FRONT_END = "https://example.icims.com/jobs/27216/front-end/questions"


class DraftRecoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name).resolve()
        self.state = self.directory / "active-draft.json"

    def guard(self, *args, error=None):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "draft_guard.py"), "--state", str(self.state), *args],
            capture_output=True, text=True,
        )
        if error:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stderr)
            return None
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def start(self, url, tab="42"):
        return self.guard("start", "--tab-id", tab, "--url", url,
                          "--employer", "Example", "--role", "Internship", "--next", "Fill the form")

    def defer(self, tab="42"):
        return self.guard("defer", "--tab-id", tab, "--reason", "form", "--next", "Check the active role")

    def test_reused_tab_can_be_filled_without_losing_the_original_marker(self):
        self.start(BACK_END)
        self.defer()
        self.start(FRONT_END)
        self.defer()
        self.guard("resume", "--tab-id", "42", error="More than one draft")
        active = self.guard("resume", "--tab-id", "42", "--url", FRONT_END)["active"]
        self.assertEqual(active["url"], FRONT_END)
        self.guard("finish", "--tab-id", "42", "--url", FRONT_END, "--verified")
        active = self.guard("resume", "--tab-id", "42", "--url", BACK_END_QUESTIONS)["active"]
        self.assertEqual(active["url"], BACK_END)
        self.assertNotIn("private", self.state.read_text())

    def test_rebind_checks_the_reopened_requisition(self):
        self.start(BACK_END)
        self.guard("rebind", "--tab-id", "42", "--new-tab-id", "43", "--url", FRONT_END,
                   error="different application")
        active = self.guard("rebind", "--tab-id", "42", "--new-tab-id", "43",
                            "--url", BACK_END_QUESTIONS)["active"]
        self.assertEqual(active["tab_id"], "43")
        self.assertEqual(active["url"], BACK_END_QUESTIONS.split("?")[0])

    def test_attachment_helper_uses_the_current_step_but_rejects_the_other_role(self):
        self.start(BACK_END)
        materials = self.directory / "materials"
        materials.mkdir()
        letter = materials / "Back_End.pdf"
        letter.write_bytes(b"%PDF-1.4 test fixture")
        store = SimpleNamespace(directory=self.directory, read_module=lambda key: {"fields": {}})
        args = SimpleNamespace(
            tab_id=42, url=BACK_END_QUESTIONS, frame_url="https://example.icims.com/jobs/candidate",
            resume_field=None, cover_letter_field="Cover Letter", cover_letter=letter,
            autoapply_dir=self.directory,
        )
        with patch("attach_documents.connect", return_value={"receipts": []}) as connect:
            attach(store, args)
            target = connect.call_args.args[2]
            self.assertEqual(target["expected_url"], BACK_END_QUESTIONS)
            self.assertEqual([doc["name"] for doc in target["documents"]], [letter.name])
            args.url = FRONT_END
            with self.assertRaisesRegex(ValueError, "match the active draft"):
                attach(store, args)
            connect.assert_called_once()

    def test_known_workday_route_still_matches_and_shared_profiles_stay_separate(self):
        workday = "https://company.myworkdayjobs.com/Careers/job/Engineer/apply"
        self.assertEqual(draft_url(workday + "/autofillWithResume"), draft_url(workday))
        self.assertNotEqual(draft_url(BACK_END), draft_url(FRONT_END))
        self.assertNotEqual(draft_url(BACK_END), draft_url("https://example.icims.com/jobs/candidate"))
        self.assertNotEqual(draft_url(BACK_END), draft_url(BACK_END.replace("example.", "other.")))


if __name__ == "__main__":
    unittest.main()
