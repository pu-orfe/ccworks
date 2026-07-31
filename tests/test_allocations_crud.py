#!/usr/bin/env python3
"""Chartstring allocation CRUD against the mock Concur server.

Rewritten from a script into unittest. As a script it had four problems, each of
which meant it provided no protection:

* it imported `tests.mock_concur_server`, which only resolves when invoked as a
  module, so `python tests/test_allocations_crud.py` died on ImportError;
* it expected a report named "Existing Report" that nothing ever created, so it
  failed at the first step even when invoked correctly;
* on failure it printed "[FAIL]" and returned, exiting 0 -- so it could not have
  failed CI even if CI had run it; and
* it exposed no TestCase, so `unittest discover` never collected it, and the only
  reference to it was a docker-compose service nothing invokes.

It now seeds its own report and asserts, so `discover` picks it up and the
docker-tests job runs it.
"""
import os
import sys
import threading
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("CCWORKS_SKIP_BROWSER_BOOTSTRAP", "1")

from mock_concur_server import MockConcurServer  # noqa: E402
from ccworks.browser_client import ConcurBrowserClient  # noqa: E402

PORT = 8096

DEPT = "(25605) ORF-Technical Support"
FUND = "(A0001) General Fund"
PROG = "(P999) Research"


class TestTransactionAllocations(unittest.TestCase):
    """get_transaction_allocations / add_transaction_allocation take a 0-based
    index; the CLI exposes 1-based and subtracts one. Both resolve rows through
    _collect_expense_rows, so position 0 here is `report show` index 1."""

    @classmethod
    def setUpClass(cls):
        cls.server = MockConcurServer(host="127.0.0.1", port=PORT)
        cls.thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.thread.start()
        time.sleep(1)

        cls.client = ConcurBrowserClient(base_url=f"http://127.0.0.1:{PORT}")
        cls.client.session_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "concur_session_mock.json"
        )
        if not os.path.exists(cls.client.session_file):
            with open(cls.client.session_file, "w") as f:
                f.write('{"cookies": [], "origins": []}')

        # Seed the report under test rather than assuming one exists.
        cls.report_name = "Allocation CRUD Report"
        cls.client.create_draft_report(cls.report_name, "allocation test", "", headless=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.stop()
        except Exception:
            pass

    # The mock server has no allocation UI: the client drives a per-row
    # [aria-label='Actions'] kebab -> an 'Allocate' menu item -> an allocations
    # modal -> an 'Add' modal with #custom6/7/8 searchable comboboxes -> two
    # nested Save buttons. The mock only has an `allocation_code` text input on
    # its reconcile form, so these two cannot run here yet. They are skipped
    # loudly rather than deleted: `txn allocate` writes chartstrings to
    # financial records and currently has no end-to-end coverage at all.
    NEEDS_MOCK_ALLOCATION_UI = (
        "mock server lacks the allocation UI (Actions kebab -> Allocate modal -> "
        "#custom6/7/8 comboboxes); see _get_transaction_rows callers in "
        "browser_client.get_transaction_allocations"
    )

    @unittest.skip(NEEDS_MOCK_ALLOCATION_UI)
    def test_01_initial_allocations_are_empty(self):
        res = self.client.get_transaction_allocations(self.report_name, 0, headless=True)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(
            [], res["allocations"],
            f"a freshly created report should have no allocations, got {res['allocations']}",
        )

    @unittest.skip(NEEDS_MOCK_ALLOCATION_UI)
    def test_02_add_then_read_back_the_allocation(self):
        add = self.client.add_transaction_allocation(
            self.report_name, 0, DEPT, FUND, PROG, headless=True
        )
        self.assertTrue(add["success"], add.get("error"))

        verify = self.client.get_transaction_allocations(self.report_name, 0, headless=True)
        self.assertTrue(verify["success"], verify.get("error"))
        found = verify["allocations"]
        self.assertTrue(
            any(DEPT in a["raw_text"] and FUND in a["raw_text"] for a in found),
            f"expected dept+fund in one allocation, got {found}",
        )

    def test_03_out_of_range_index_is_refused(self):
        """Runs without the allocation UI: the bounds check precedes the kebab click.

        An index past the end must not resolve to some other row -- the same
        class of defect as the read/write index mismatch. The IndexError is
        caught and surfaced as an error dict rather than propagating.
        """
        res = self.client.get_transaction_allocations(self.report_name, 99, headless=True)
        self.assertFalse(res["success"])
        self.assertIn("out of bounds", res["error"].lower())

    def test_04_negative_index_is_refused(self):
        # -1 would otherwise index the last row via Python's negative indexing.
        res = self.client.get_transaction_allocations(self.report_name, -1, headless=True)
        self.assertFalse(res["success"])
        self.assertIn("out of bounds", res["error"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
