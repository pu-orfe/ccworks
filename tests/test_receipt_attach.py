#!/usr/bin/env python3
"""Receipt attachment via `report apply-json`, against the mock Concur server.

Five defects motivated these tests. Every one of them was silent -- the payload
said "success": true while nothing had been attached:

1. The row's detail pane was opened by clicking the row's checkbox, which only
   toggles bulk selection. The pane never opened, so no receipt (and no field
   edit) was ever written.

2. A failed receipt upload was logged as a warning and then fell through to
   Save, so the row reported success having attached nothing. A caller had no
   way to distinguish "receipt attached" from "receipt silently dropped".

3. The receipt panel renders an aria-live skeleton and hydrates asynchronously.
   Reading it before it settled found no upload input, or found a stale one from
   the previous render, and the file went nowhere.

4. The receipt viewer survives the detail pane closing. In a multi-row run every
   row after the first therefore read the *previous* row's filename as its own
   attachment, concluded it already had a receipt, and tried to replace it.

5. On card transactions Concur defaults the Receipt / Card Receipt toggle to
   "Card Receipt", whose pane carries its own file input. Uploading there is
   discarded. Rows with the toggle silently failed while rows without it worked.
"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CCWORKS_SKIP_BROWSER_BOOTSTRAP", "1")

from mock_concur_server import MockConcurServer  # noqa: E402
from ccworks.browser_client import ConcurBrowserClient  # noqa: E402

PORT = 8097
BASE_URL = f"http://127.0.0.1:{PORT}"


class ReceiptAttachTestCase(unittest.TestCase):
    """Base: one mock server, one report seeded with the awkward receipt cases."""

    server = None
    client = None
    tmpdir = None

    # Rows in a "RECEIPTS" report, 1-based as `report show` emits them.
    ROW_DUP_A = 1          # ESHIPGLOBAL INC $23.28  -- indistinguishable from 2, 3
    ROW_DUP_B = 2          # ESHIPGLOBAL INC $23.28
    ROW_DUP_C = 3          # ESHIPGLOBAL INC $23.28
    ROW_WITH_RECEIPT = 4   # ANTHROPIC $400.00, pre-seeded with old.pdf
    ROW_NO_TABS = 5        # PETTY CASH $12.00, no Receipt/Card Receipt toggle

    @classmethod
    def setUpClass(cls):
        cls.server = MockConcurServer(host="127.0.0.1", port=PORT)
        cls.thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.thread.start()
        cls.client = ConcurBrowserClient(base_url=BASE_URL)
        cls.client.session_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "concur_session_mock.json"
        )
        if not os.path.exists(cls.client.session_file):
            with open(cls.client.session_file, "w") as f:
                f.write('{"cookies": [], "origins": []}')
        cls.tmpdir = tempfile.mkdtemp(prefix="ccworks-receipts-")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.stop()
        except Exception:
            pass

    # -- helpers ---------------------------------------------------------
    def pdf(self, name):
        """A real file on disk for `name`; apply-json refuses missing paths."""
        path = os.path.join(self.tmpdir, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(b"%PDF-1.4\n% mock receipt\n")
        return path

    def receipts(self, report_name):
        """Server-side truth: the receipt on each transaction, 1-based."""
        with urllib.request.urlopen(f"{BASE_URL}/api/reports") as resp:
            reports = json.loads(resp.read().decode("utf-8"))
        for r in reports:
            if r["name"] == report_name:
                return {i: t.get("receipt")
                        for i, t in enumerate(r.get("transactions", []), start=1)}
        self.fail(f"report {report_name!r} not found on the server")

    def fields(self, report_name):
        """Server-side field values per row, 1-based.

        Read from the API rather than `report show`: a shallow capture does not
        surface business purpose or comment, so asserting on it would test the
        mock's grid markup instead of whether the write landed.
        """
        with urllib.request.urlopen(f"{BASE_URL}/api/reports") as resp:
            reports = json.loads(resp.read().decode("utf-8"))
        for r in reports:
            if r["name"] == report_name:
                return {i: t for i, t in enumerate(r.get("transactions", []), start=1)}
        self.fail(f"report {report_name!r} not found on the server")

    def apply(self, report_name, expenses):
        return self.client.apply_json_updates(
            report_name=report_name, expenses=expenses, headless=True)

    def make_report(self, name):
        self.client.create_draft_report(name, "receipt tests", "", headless=True)


class TestAttachSucceeds(ReceiptAttachTestCase):
    REPORT = "RECEIPTS attach basic"

    def setUp(self):
        self.make_report(self.REPORT)

    def test_attach_lands_on_a_card_row(self):
        """A card row defaults to the Card Receipt tab, whose uploads are discarded.

        Production must switch to the Receipt tab first. Before that fix this row
        reported success with nothing attached (defect 5).
        """
        res = self.apply(self.REPORT, [{
            "index": self.ROW_DUP_A, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
            "receipt_file_path": self.pdf("a.pdf"),
        }])
        self.assertTrue(res["results"][0]["success"],
                        f"attach should succeed, got {res['results'][0]}")
        self.assertEqual("a.pdf", self.receipts(self.REPORT)[self.ROW_DUP_A],
                         "the receipt must actually be on the row, not merely reported")

    def test_attach_lands_on_a_row_without_the_tab_toggle(self):
        """A non-card row has no toggle at all; tab handling must not break it."""
        res = self.apply(self.REPORT, [{
            "index": self.ROW_NO_TABS, "vendor": "PETTY CASH", "amount": "$12.00",
            "receipt_file_path": self.pdf("cash.pdf"),
        }])
        self.assertTrue(res["results"][0]["success"], res["results"][0])
        self.assertEqual("cash.pdf", self.receipts(self.REPORT)[self.ROW_NO_TABS])


class TestFailuresAreReported(ReceiptAttachTestCase):
    REPORT = "RECEIPTS failure reporting"

    def setUp(self):
        self.make_report(self.REPORT)

    def test_missing_local_file_fails_the_row(self):
        """A path that does not exist must fail the row, not warn and save (defect 2)."""
        res = self.apply(self.REPORT, [{
            "index": self.ROW_DUP_A, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
            "receipt_file_path": "/nonexistent/nope.pdf",
        }])
        row = res["results"][0]
        self.assertFalse(row["success"],
                         "a receipt that never uploaded must not report success")
        self.assertIn("not found locally", row["error"])
        self.assertIsNone(self.receipts(self.REPORT)[self.ROW_DUP_A],
                          "no receipt should have been attached")

    def test_row_identity_is_checked_before_any_receipt_write(self):
        """A stale index must be refused rather than written to the wrong expense."""
        res = self.apply(self.REPORT, [{
            "index": self.ROW_DUP_A, "vendor": "TOTALLY DIFFERENT VENDOR",
            "amount": "$999.99", "receipt_file_path": self.pdf("wrong.pdf"),
        }])
        row = res["results"][0]
        self.assertFalse(row["success"])
        self.assertIn("does not match", row["error"])
        self.assertIsNone(self.receipts(self.REPORT)[self.ROW_DUP_A])


class TestIndexTargeting(ReceiptAttachTestCase):
    REPORT = "RECEIPTS index targeting"

    def setUp(self):
        self.make_report(self.REPORT)

    def test_each_row_gets_its_own_receipt(self):
        """Three rows sharing merchant AND amount, attached in one run.

        Only the index distinguishes them, so this is the regression test for
        merchant-substring targeting. It is also the test for defect 4: with the
        receipt viewer left standing between rows, rows 2 and 3 read row 1's
        filename as their own and tried to replace a receipt they never had.
        """
        res = self.apply(self.REPORT, [
            {"index": self.ROW_DUP_A, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
             "receipt_file_path": self.pdf("first.pdf")},
            {"index": self.ROW_DUP_B, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
             "receipt_file_path": self.pdf("second.pdf")},
            {"index": self.ROW_DUP_C, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
             "receipt_file_path": self.pdf("third.pdf")},
        ])
        for row in res["results"]:
            self.assertTrue(row["success"], f"row {row['index']} failed: {row}")

        got = self.receipts(self.REPORT)
        self.assertEqual("first.pdf", got[self.ROW_DUP_A])
        self.assertEqual("second.pdf", got[self.ROW_DUP_B])
        self.assertEqual("third.pdf", got[self.ROW_DUP_C])

    def test_attaching_one_row_leaves_its_twins_alone(self):
        res = self.apply(self.REPORT, [{
            "index": self.ROW_DUP_B, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
            "receipt_file_path": self.pdf("only_b.pdf"),
        }])
        self.assertTrue(res["results"][0]["success"], res["results"][0])
        got = self.receipts(self.REPORT)
        self.assertEqual("only_b.pdf", got[self.ROW_DUP_B])
        self.assertIsNone(got[self.ROW_DUP_A], "row 1 must be untouched")
        self.assertIsNone(got[self.ROW_DUP_C], "row 3 must be untouched")


class TestReplaceExistingReceipt(ReceiptAttachTestCase):
    REPORT = "RECEIPTS replace existing"

    def setUp(self):
        self.make_report(self.REPORT)

    def test_existing_receipt_is_replaced_not_appended(self):
        """Row 4 ships with old.pdf attached.

        Concur exposes Remove and Add separately, and a file input exists in the
        attached state too -- so uploading straight onto it appends a second
        receipt instead of overwriting. The replace path must remove first.
        """
        self.assertEqual("old.pdf", self.receipts(self.REPORT)[self.ROW_WITH_RECEIPT],
                         "precondition: the row starts with a receipt")

        res = self.apply(self.REPORT, [{
            "index": self.ROW_WITH_RECEIPT, "vendor": "ANTHROPIC", "amount": "$400.00",
            "receipt_file_path": self.pdf("new.pdf"),
        }])
        self.assertTrue(res["results"][0]["success"], res["results"][0])
        self.assertEqual("new.pdf", self.receipts(self.REPORT)[self.ROW_WITH_RECEIPT],
                         "the new receipt must replace the old one outright")

    def test_replace_does_not_disturb_other_rows(self):
        self.apply(self.REPORT, [{
            "index": self.ROW_WITH_RECEIPT, "vendor": "ANTHROPIC", "amount": "$400.00",
            "receipt_file_path": self.pdf("new2.pdf"),
        }])
        got = self.receipts(self.REPORT)
        self.assertEqual("new2.pdf", got[self.ROW_WITH_RECEIPT])
        for idx in (self.ROW_DUP_A, self.ROW_DUP_B, self.ROW_DUP_C):
            self.assertIsNone(got[idx], f"row {idx} must be untouched by a replace")


class TestFieldEditsStillWork(ReceiptAttachTestCase):
    """The row-open fix (defect 1) underpins every write, not just receipts."""

    REPORT = "RECEIPTS field edits"

    def setUp(self):
        self.make_report(self.REPORT)

    def test_fields_and_receipt_apply_together(self):
        res = self.apply(self.REPORT, [{
            "index": self.ROW_DUP_A, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
            "expense_type": "Software", "business_purpose": "Lab shipping",
            "comment": "Q3 restock", "receipt_file_path": self.pdf("both.pdf"),
        }])
        self.assertTrue(res["results"][0]["success"], res["results"][0])

        row = self.fields(self.REPORT)[self.ROW_DUP_A]
        self.assertEqual("Lab shipping", row.get("business_purpose"),
                         "the field write must survive the receipt upload")
        self.assertEqual("Q3 restock", row.get("comment"))
        self.assertEqual("both.pdf", row.get("receipt"))

    @unittest.expectedFailure
    def test_expense_type_is_written_by_apply_json(self):
        """Known defect, unrelated to receipts: apply-json never writes expense_type.

        Reproduces with no receipt in the payload at all -- business_purpose lands
        and expense_type does not, while the row still reports success: true. That
        is a silent omission on a financial record, the same shape as the receipt
        bugs this module covers. Marked expected-failure so it stays visible in the
        suite until the write path (or the mock's field markup, if the gap is
        there) is fixed, rather than being papered over by dropping the assertion.
        """
        self.apply(self.REPORT, [{
            "index": self.ROW_DUP_B, "vendor": "ESHIPGLOBAL INC", "amount": "$23.28",
            "expense_type": "Software", "business_purpose": "type check",
        }])
        row = self.fields(self.REPORT)[self.ROW_DUP_B]
        self.assertEqual("type check", row.get("business_purpose"),
                         "control: the other field does land")
        self.assertEqual("Software", row.get("expense_type"))


if __name__ == "__main__":
    unittest.main()
