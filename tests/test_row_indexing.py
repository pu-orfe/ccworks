#!/usr/bin/env python3
"""Row identity and index-space guarantees, against the mock Concur server.

Three defects motivated these tests, all of them silent:

1. Rows were deduplicated by their text content, so two genuinely distinct line
   items with the same date/vendor/amount collapsed into one. On a purchasing
   card that is ordinary (two shipments, same day, same price) and the loss was
   invisible -- the payload still said "success": true.

2. `report show` numbered rows by their position among *raw selector matches*,
   while the write paths numbered them by position in their own *filtered* list,
   and each path filtered slightly differently. Index N therefore did not denote
   the same expense across commands, so a `report show` -> edit ->
   `report apply-json` round-trip could write to the wrong expense.

3. `apply_json_updates` trusted the index blindly. If the report changed in
   Concur after the JSON was produced, the index still resolved -- to a
   different expense -- and the edit was applied anyway.
"""
import os
import sys
import threading
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CCWORKS_SKIP_BROWSER_BOOTSTRAP", "1")

from mock_concur_server import MockConcurServer  # noqa: E402
from ccworks.browser_client import ConcurBrowserClient  # noqa: E402

PORT = 8095
BASE_URL = f"http://127.0.0.1:{PORT}"


class RowIndexingTestCase(unittest.TestCase):
    server = None
    client = None

    @classmethod
    def setUpClass(cls):
        cls.server = MockConcurServer(host="127.0.0.1", port=PORT)
        cls.thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.thread.start()
        cls.client = ConcurBrowserClient(base_url=BASE_URL)
        # The mock accepts any session; write a throwaway state file.
        cls.client.session_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "concur_session_mock.json"
        )
        if not os.path.exists(cls.client.session_file):
            with open(cls.client.session_file, "w") as f:
                f.write('{"cookies": [], "origins": []}')

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.stop()
        except Exception:
            pass


class TestIdenticalRowsArePreserved(RowIndexingTestCase):
    REPORT = "Identical Shipping DUPES"

    def setUp(self):
        self.client.create_draft_report(self.REPORT, "dup test", "", headless=True)

    def test_both_identical_line_items_are_returned(self):
        details = self.client.get_report_details(self.REPORT, headless=True)
        expenses = details["expenses"]

        # Match on raw_text, not the parsed `vendor`: the mock's row markup does
        # not populate the vendor field the way Concur's grid does, so asserting
        # on `vendor` would test the mock's fidelity rather than the dedup fix.
        eship = [e for e in expenses if "ESHIPGLOBAL" in (e.get("raw_text") or "")]
        self.assertEqual(
            2, len(eship),
            "both identical ESHIPGLOBAL line items must survive; dropping one is "
            f"silent data loss. Got raw_texts: {[e.get('raw_text') for e in expenses]}",
        )
        self.assertEqual(3, len(expenses), "all three seeded rows must be returned")

        # And they really are byte-identical, i.e. the case the old text-based
        # dedup would have collapsed.
        self.assertEqual(
            eship[0]["raw_text"], eship[1]["raw_text"],
            "the two rows must be textually identical for this to be a regression test",
        )

    def test_indices_are_dense_and_one_based(self):
        details = self.client.get_report_details(self.REPORT, headless=True)
        indices = [e["index"] for e in details["expenses"]]
        self.assertEqual(
            list(range(1, len(indices) + 1)), indices,
            "indices must be dense and 1-based so they address the same row in "
            f"the write paths. Got: {indices}",
        )

    def test_identical_rows_are_reported_not_hidden(self):
        details = self.client.get_report_details(self.REPORT, headless=True)
        groups = details["extraction"]["identical_line_items"]
        self.assertTrue(
            any(g["count"] == 2 for g in groups),
            f"textually identical rows should be surfaced, got {groups}",
        )

    def test_extraction_block_reports_what_was_skipped(self):
        details = self.client.get_report_details(self.REPORT, headless=True)
        extraction = details["extraction"]
        for key in ("candidates_seen", "expenses_returned", "skipped_candidates", "complete"):
            self.assertIn(key, extraction)
        self.assertEqual(len(details["expenses"]), extraction["expenses_returned"])
        self.assertTrue(extraction["complete"])


class TestApplyJsonRefusesMismatch(RowIndexingTestCase):
    REPORT = "Apply Json Guard DUPES"

    def setUp(self):
        self.client.create_draft_report(self.REPORT, "guard test", "", headless=True)

    def test_wrong_amount_at_index_is_refused(self):
        # Index 3 is Office Depot $189.99. Claiming a different amount there is
        # what a stale JSON looks like after the report changed in Concur.
        result = self.client.apply_json_updates(
            self.REPORT,
            [{"index": 3, "vendor": "Office Depot", "amount": "$999.99",
              "expense_type": "Software", "business_purpose": "should not be written"}],
            headless=True,
        )
        entries = result.get("results", result if isinstance(result, list) else [])
        self.assertTrue(entries, f"expected a per-row result, got {result}")
        self.assertFalse(entries[0]["success"])
        self.assertIn("does not match", entries[0]["error"])

    def test_out_of_range_index_is_refused(self):
        result = self.client.apply_json_updates(
            self.REPORT,
            [{"index": 99, "vendor": "Office Depot", "amount": "$189.99"}],
            headless=True,
        )
        entries = result.get("results", result if isinstance(result, list) else [])
        self.assertTrue(entries)
        self.assertFalse(entries[0]["success"])
        self.assertIn("out of bounds", entries[0]["error"].lower())

    def test_index_zero_is_refused_now_that_indices_are_one_based(self):
        # A 0 would previously have been accepted as the first row.
        result = self.client.apply_json_updates(
            self.REPORT,
            [{"index": 0, "vendor": "ESHIPGLOBAL INC", "amount": "$53.77"}],
            headless=True,
        )
        entries = result.get("results", result if isinstance(result, list) else [])
        self.assertTrue(entries)
        self.assertFalse(entries[0]["success"])


class TestApplyJsonLeavesOmittedFieldsAlone(RowIndexingTestCase):
    """An absent key must mean "leave unchanged", not "set to empty".

    apply_json_updates read fields with `exp.get("business_purpose", "")`, so an
    omitted key became "" -- which is not None, so the `is not None` guard fired
    and the field was overwritten with empty. Editing one field in a JSON file
    therefore silently wiped every field you did not mention, and applying a row
    whose deep scan failed would clear a real business purpose.
    """

    REPORT = "Omitted Fields DUPES"

    def setUp(self):
        self.client.create_draft_report(self.REPORT, "omit test", "", headless=True)
        # Give row 1 a purpose and comment to protect.
        self.client.update_report_transaction(
            self.REPORT, transaction_indices=[1],
            business_purpose="Keep this purpose",
            comment="Keep this comment",
            headless=True,
        )

    def _row1(self):
        # deep=True is required: the mock's row markup carries only merchant,
        # amount, and status, so a shallow read reports business_purpose and
        # comment as "" no matter what they hold. Asserting against a shallow
        # read would make these tests pass vacuously.
        return self.client.get_report_details(self.REPORT, deep=True, headless=True)["expenses"][0]

    def test_omitting_purpose_and_comment_preserves_them(self):
        before = self._row1()
        self.assertEqual("Keep this purpose", before["business_purpose"])

        # Only expense_type is specified; purpose and comment are absent.
        self.client.apply_json_updates(
            self.REPORT,
            [{"index": 1, "vendor": before["vendor"], "amount": before["amount"],
              "expense_type": "Software"}],
            headless=True,
        )

        after = self._row1()
        self.assertEqual(
            "Keep this purpose", after["business_purpose"],
            "omitting business_purpose must not clear it",
        )
        self.assertEqual(
            "Keep this comment", after["comment"],
            "omitting comment must not clear it",
        )

    def test_explicit_empty_string_still_clears(self):
        # "" remains the documented way to clear a field, so it must still work.
        before = self._row1()
        self.client.apply_json_updates(
            self.REPORT,
            [{"index": 1, "vendor": before["vendor"], "amount": before["amount"],
              "comment": ""}],
            headless=True,
        )
        self.assertEqual("", self._row1()["comment"], 'an explicit "" must clear the field')


if __name__ == "__main__":
    unittest.main(verbosity=2)
