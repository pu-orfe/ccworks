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

    # The mock now models the allocation UI -- per-row Actions kebab, an
    # 'Allocate' menu item, the allocations modal, and an Add form whose
    # chartstring fields are the same combobox widget Concur uses for the
    # expense type. These two ran as skips for as long as `txn allocate` had no
    # end-to-end coverage at all, while it wrote chartstrings to real records.
    def test_01_initial_allocations_are_empty(self):
        res = self.client.get_transaction_allocations(self.report_name, 0, headless=True)
        self.assertTrue(res["success"], res.get("error"))
        self.assertEqual(
            [], res["allocations"],
            f"a freshly created report should have no allocations, got {res['allocations']}",
        )

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

    def test_02b_a_chartstring_the_picker_does_not_offer_fails(self):
        """The point of the exercise: a failed allocation must report failure.

        This path used to end in an unconditional {"success": True}; the one
        check it had logged a warning that never reached the caller, so an
        allocation that set nothing was indistinguishable from one that worked.
        """
        # These tests share one report and run in name order, so count the rows
        # before and after rather than asserting the list is empty.
        before = self.client.get_transaction_allocations(
            self.report_name, 0, headless=True)["allocations"]

        res = self.client.add_transaction_allocation(
            self.report_name, 0, "(99999) No Such Department", FUND, None, headless=True
        )
        self.assertFalse(res["success"],
                         f"an unofferable chartstring must fail, got {res}")
        self.assertIn("Department", res["error"])

        after = self.client.get_transaction_allocations(
            self.report_name, 0, headless=True)["allocations"]
        self.assertEqual(len(before), len(after),
                         "a failed allocation must not leave a partial row behind")

    def test_02c_success_reports_what_it_verified(self):
        res = self.client.add_transaction_allocation(
            self.report_name, 0, DEPT, FUND, None, headless=True
        )
        self.assertTrue(res["success"], res.get("error"))
        self.assertIn(DEPT, res.get("verified", []),
                      "a successful allocation should say what it confirmed")

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
