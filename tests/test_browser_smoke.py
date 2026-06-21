#!/usr/bin/env python3
import os
import sys
import json
import time

# Adjust path to import src and tests modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.mock_concur_server import MockConcurServer
from src.browser_client import ConcurBrowserClient

DUMMY_SESSION = {
    "cookies": [
        {
            "name": "concur_mock_session",
            "value": "active_state",
            "domain": "127.0.0.1",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax"
        }
    ],
    "origins": []
}


def run_browser_smoke_test():
    session_file = "concur_session_mock.json"
    
    # 1. Write dummy session file to act as "already authenticated"
    with open(session_file, "w") as f:
        json.dump(DUMMY_SESSION, f)
    
    # 2. Start mock Concur server
    server = MockConcurServer(host="127.0.0.1", port=8090)
    server.start()

    print("\n" + "=" * 60)
    print("        RUNNING BROWSER CRUD SMOKE TESTS (MOCK WORKFLOW)")
    print("=" * 60)

    try:
        # Initialize client targeting the mock server
        client = ConcurBrowserClient(
            session_file=session_file,
            base_url="http://127.0.0.1:8090"
        )

        # ----------------------------------------------------
        # 1. READ (Initial List - Empty)
        # ----------------------------------------------------
        print("\n[Step 1] Reading report list (Should be empty)...")
        reports = client.list_reports(headless=True)
        print(f"         Reports found: {len(reports)}")
        assert len(reports) == 0, f"Expected 0 reports, found {len(reports)}"
        print("         [PASS] Initial empty check.")

        # ----------------------------------------------------
        # 2. CREATE (Create Report A)
        # ----------------------------------------------------
        print("\n[Step 2] Creating draft report 'Smoke Test Report A'...")
        create_res = client.create_draft_report(
            name="Smoke Test Report A",
            purpose="Validation Purpose",
            comment="Smoke Test Comment",
            headless=True
        )
        assert create_res["success"] is True, "Create draft report failed."
        print(f"         [PASS] Report created: {create_res['report_name']}")

        # ----------------------------------------------------
        # 3. READ (Verify Report A exists)
        # ----------------------------------------------------
        print("\n[Step 3] Reading report list to verify 'Smoke Test Report A'...")
        reports = client.list_reports(headless=True)
        print(f"         Reports found: {len(reports)}")
        assert len(reports) == 1, f"Expected 1 report, found {len(reports)}"
        assert reports[0]["name"] == "Smoke Test Report A", f"Expected 'Smoke Test Report A', got '{reports[0]['name']}'"
        print("         [PASS] Report verified in list.")

        # ----------------------------------------------------
        # 4. UPDATE (Rename Report A -> Report B)
        # ----------------------------------------------------
        print("\n[Step 4] Updating report 'Smoke Test Report A' to 'Smoke Test Report A Updated'...")
        update_res = client.update_report(
            old_name="Smoke Test Report A",
            new_name="Smoke Test Report A Updated",
            new_purpose="Updated Purpose",
            new_comment="Updated Comment",
            headless=True
        )
        assert update_res["success"] is True, "Update report failed."
        print(f"         [PASS] Report updated: {update_res['name']}")

        # ----------------------------------------------------
        # 5. READ (Verify Name is Updated)
        # ----------------------------------------------------
        print("\n[Step 5] Reading report list to verify updated name...")
        reports = client.list_reports(headless=True)
        assert len(reports) == 1, f"Expected 1 report, found {len(reports)}"
        assert reports[0]["name"] == "Smoke Test Report A Updated", f"Expected 'Smoke Test Report A Updated', got '{reports[0]['name']}'"
        print("         [PASS] Updated report name verified in list.")

        # ----------------------------------------------------
        # 6. DELETE (Delete Report A Updated)
        # ----------------------------------------------------
        print("\n[Step 6] Deleting report 'Smoke Test Report A Updated'...")
        delete_res = client.delete_report(
            name="Smoke Test Report A Updated",
            headless=True
        )
        assert delete_res["success"] is True, "Delete report failed."
        print("         [PASS] Report deleted.")

        # ----------------------------------------------------
        # 7. READ (Verify List is Empty again)
        # ----------------------------------------------------
        print("\n[Step 7] Reading report list to verify it is empty again...")
        reports = client.list_reports(headless=True)
        print(f"         Reports found: {len(reports)}")
        assert len(reports) == 0, f"Expected 0 reports, found {len(reports)}"
        print("         [PASS] Final empty check.")

        # ----------------------------------------------------
        # 8. READ RECEIPTS (Verify Available Receipts list)
        # ----------------------------------------------------
        print("\n[Step 8] Listing available receipts...")
        receipts = client.list_available_receipts(headless=True)
        print(f"         Receipts found: {receipts}")
        assert len(receipts) == 3, f"Expected 3 receipts, found {len(receipts)}"
        assert "lunch_receipt.png" in receipts, "Expected 'lunch_receipt.png' in receipts list"
        print("         [PASS] List receipts verified.")

        # ----------------------------------------------------
        # 9. DELETE RECEIPT (Delete a specific receipt)
        # ----------------------------------------------------
        print("\n[Step 9] Deleting available receipt 'taxi_receipt.png'...")
        del_receipt_res = client.delete_available_receipt(
            receipt_name="taxi_receipt.png",
            headless=True
        )
        assert del_receipt_res["success"] is True, "Delete available receipt failed."
        
        # Verify receipt list contains only 2 receipts now
        receipts_after = client.list_available_receipts(headless=True)
        print(f"         Receipts remaining: {receipts_after}")
        assert len(receipts_after) == 2, f"Expected 2 receipts remaining, found {len(receipts_after)}"
        assert "taxi_receipt.png" not in receipts_after, "Expected 'taxi_receipt.png' to be deleted"
        print("         [PASS] Receipt deletion verified.")

        print("\n" + "=" * 60)
        print(" [SUCCESS] BROWSER CRUD & RECEIPT SMOKE TEST PASSED SUCCESSFULLY!")
        print("=" * 60 + "\n")
        exit_code = 0

    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {str(e)}")
        exit_code = 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error occurred: {str(e)}")
        exit_code = 1
    finally:
        # Cleanup
        server.stop()
        if os.path.exists(session_file):
            os.remove(session_file)

    sys.exit(exit_code)


if __name__ == "__main__":
    run_browser_smoke_test()
