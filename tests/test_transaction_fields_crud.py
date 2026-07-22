#!/usr/bin/env python3
import os
import sys
import json
import time

# Adjust path to import src and tests modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.mock_concur_server import MockConcurServer
from ccworks.browser_client import ConcurBrowserClient

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


def run_transaction_crud_test():
    session_file = "concur_session_transaction_crud.json"
    
    # 1. Write dummy session file to act as "already authenticated"
    with open(session_file, "w") as f:
        json.dump(DUMMY_SESSION, f)
    
    # 2. Start mock Concur server
    server = MockConcurServer(host="127.0.0.1", port=8091)
    server.start()

    print("\n" + "=" * 60)
    print("      RUNNING REPORT TRANSACTION COMMENT CRUD TESTS")
    print("=" * 60)

    try:
        # Initialize client targeting the mock server on port 8091
        client = ConcurBrowserClient(
            session_file=session_file,
            base_url="http://127.0.0.1:8091"
        )

        # Step 1: Create a draft report
        report_name = "Transaction CRUD Report"
        print(f"\n[Step 1] Creating draft report '{report_name}'...")
        create_res = client.create_draft_report(
            name=report_name,
            purpose="Transaction Fields CRUD Testing",
            comment="Main report comment",
            headless=True
        )
        assert create_res["success"] is True, "Create draft report failed."
        print(f"         [PASS] Report created: {create_res['report_name']}")

        # Step 2: Read initial transactions and verify they are empty
        print(f"\n[Step 2] Reading initial transaction details for '{report_name}'...")
        details = client.get_report_details(name=report_name, headless=True)
        assert details["success"] is True, "Failed to get report details."
        expenses = details["expenses"]
        assert len(expenses) == 2, f"Expected 2 transactions, got {len(expenses)}"
        
        # Verify initial fields are blank/empty in draft status
        first_tx = expenses[0]
        print(f"         First transaction parsed: {first_tx}")
        assert first_tx["business_purpose"] == "", f"Expected empty business purpose, got '{first_tx['business_purpose']}'"
        assert first_tx["comment"] == "", f"Expected empty comment, got '{first_tx['comment']}'"
        print("         [PASS] Initial empty fields verified.")

        # Step 3: Write (Create) fields on transaction 0
        print(f"\n[Step 3] Writing type, purpose, and comment to transaction 0...")
        update_res = client.update_report_transaction(
            report_name=report_name,
            transaction_index=0,
            expense_type="Ground Transportation",
            business_purpose="Lunch meeting with Anthropic partner",
            comment="First test comment",
            headless=True
        )
        assert update_res["success"] is True, "Failed to write transaction fields."
        print("         [PASS] Update transaction method succeeded.")

        # Step 4: Read and Verify written fields
        print(f"\n[Step 4] Reading details again to verify written fields...")
        details = client.get_report_details(name=report_name, deep=True, headless=True)
        first_tx = details["expenses"][0]
        print(f"         Transaction 0 after write: {first_tx}")
        assert first_tx["type"] == "Ground Transportation", f"Expected 'Ground Transportation', got '{first_tx['type']}'"
        assert first_tx["business_purpose"] == "Lunch meeting with Anthropic partner", f"Expected purpose, got '{first_tx['business_purpose']}'"
        assert first_tx["comment"] == "First test comment", f"Expected comment, got '{first_tx['comment']}'"
        print("         [PASS] Write fields successfully read and verified.")

        # Step 5: Update the comment on transaction 0
        print(f"\n[Step 5] Updating the comment on transaction 0...")
        update_res = client.update_report_transaction(
            report_name=report_name,
            transaction_index=0,
            comment="Updated test comment",
            headless=True
        )
        assert update_res["success"] is True, "Failed to update transaction fields."
        
        # Read and verify updated comment
        details = client.get_report_details(name=report_name, deep=True, headless=True)
        first_tx = details["expenses"][0]
        print(f"         Transaction 0 after comment update: {first_tx}")
        assert first_tx["comment"] == "Updated test comment", f"Expected updated comment, got '{first_tx['comment']}'"
        print("         [PASS] Comment update successfully read and verified.")

        # Step 6: Delete/Remove the comment on transaction 0
        print(f"\n[Step 6] Removing the comment on transaction 0 (setting to empty)...")
        update_res = client.update_report_transaction(
            report_name=report_name,
            transaction_index=0,
            comment="",
            headless=True
        )
        assert update_res["success"] is True, "Failed to remove transaction comment."
        
        # Read and verify comment is removed (empty)
        details = client.get_report_details(name=report_name, deep=True, headless=True)
        first_tx = details["expenses"][0]
        print(f"         Transaction 0 after comment removal: {first_tx}")
        assert first_tx["comment"] == "", f"Expected empty comment, got '{first_tx['comment']}'"
        print("         [PASS] Comment removal successfully read and verified.")

        print("\n" + "=" * 60)
        print(" [SUCCESS] REPORT TRANSACTION COMMENT CRUD TESTS PASSED SUCCESSFULLY!")
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
    run_transaction_crud_test()
