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

        # ----------------------------------------------------
        # 10. NEW FEATURE: List Historical (Old) Reports
        # ----------------------------------------------------
        print("\n[Step 10] Listing historical reports (filter='Last 90 Days')...")
        old_reports = client.list_reports(filter_view="Last 90 Days", headless=True)
        print(f"         Old reports found: {len(old_reports)}")
        assert len(old_reports) == 2, f"Expected 2 historical reports, found {len(old_reports)}"
        assert any("Old Lodging Report 2025" in r["name"] for r in old_reports), "Expected Old Lodging Report 2025"
        print("         [PASS] List historical reports verified.")

        # ----------------------------------------------------
        # 11. NEW FEATURE: Get Details of a Report
        # ----------------------------------------------------
        print("\n[Step 11] Fetching details for 'Old Lodging Report 2025'...")
        details = client.get_report_details(name="Old Lodging Report 2025", filter_view="Last 90 Days", headless=True)
        print(f"         Details: {details}")
        assert details["success"] is True, "Expected success to be True"
        assert details["report_number"] == "REP-100200", f"Expected REP-100200, got {details['report_number']}"
        assert len(details["expenses"]) == 2, f"Expected 2 expense line items, got {len(details['expenses'])}"
        print("         [PASS] Report details verification passed.")

        # ----------------------------------------------------
        # 12. NEW FEATURE: List Card Transactions
        # ----------------------------------------------------
        print("\n[Step 12] Listing Available Expenses (Card Transactions)...")
        # Default: All Corporate and Personal Cards
        txs_corp = client.list_card_transactions(card_type_filter="All Corporate and Personal Cards", headless=True)
        print(f"         Corporate transactions: {txs_corp}")
        assert len(txs_corp) == 2, f"Expected 2 corporate/personal transactions, found {len(txs_corp)}"
        assert any("Uber Rides" in t["raw_text"] for t in txs_corp), "Expected Uber Rides in list"

        # Purchasing Cards
        txs_purch = client.list_card_transactions(card_type_filter="All Purchasing Cards", headless=True)
        print(f"         Purchasing transactions: {txs_purch}")
        assert len(txs_purch) == 1, f"Expected 1 purchasing transaction, found {len(txs_purch)}"
        assert any("Office Depot" in t["raw_text"] for t in txs_purch), "Expected Office Depot in list"
        print("         [PASS] List card transactions filtering verified.")

        # ----------------------------------------------------
        # 13. NEW FEATURE: Get Card Transaction Details
        # ----------------------------------------------------
        print("\n[Step 13] Fetching details for transaction 'Office Depot'...")
        tx_details = client.get_card_transaction_details(merchant_or_id="Office Depot", card_type_filter="All Purchasing Cards", headless=True)
        print(f"         Transaction details: {tx_details}")
        assert tx_details["success"] is True, "Expected success to be True"
        assert tx_details["merchant"] == "Office Depot", f"Expected Office Depot, got {tx_details['merchant']}"
        assert tx_details["transaction_id"] == "TX_5002", f"Expected TX_5002, got {tx_details['transaction_id']}"
        assert tx_details["card_program"] == "Purchasing Card", f"Expected Purchasing Card, got {tx_details['card_program']}"
        print("         [PASS] Card transaction details verified.")

        # ----------------------------------------------------
        # 14. NEW FEATURE: Add Expense Delegate
        # ----------------------------------------------------
        print("\n[Step 14] Adding expense delegate 'John Doe'...")
        add_del_res = client.add_expense_delegate(name_or_email="John Doe", permissions=["prepare", "submit"], headless=True)
        assert add_del_res["success"] is True, "Expected delegate creation to succeed"
        print("         [PASS] Expense delegate 'John Doe' successfully added.")

        # ----------------------------------------------------
        # 15. NEW FEATURE: Remove Expense Delegate
        # ----------------------------------------------------
        print("\n[Step 15] Removing expense delegate 'John Doe'...")
        rem_del_res = client.remove_expense_delegate(name_or_email="John Doe", headless=True)
        assert rem_del_res["success"] is True, "Expected delegate removal to succeed"
        print("         [PASS] Expense delegate 'John Doe' successfully removed.")

        # ----------------------------------------------------
        # 16. NEW FEATURE: Reconcile Report Transactions (Month-End)
        # ----------------------------------------------------
        print("\n[Step 16] Creating report and reconciling its transactions...")
        client.create_draft_report(
            name="Reconciliation Report A",
            purpose="Reconcile Test",
            comment="Test Comment",
            headless=True
        )
        
        # Create a dummy receipt to test attachment during reconciliation
        dummy_recon_receipt = "tests/dummy_recon_receipt.pdf"
        with open(dummy_recon_receipt, "w") as f:
            f.write("RECON MOCK RECEIPT")

        try:
            recon_rules = {
                "Uber": {
                    "expense_type": "Ground Transportation",
                    "business_purpose": "Client dinner ride",
                    "comment": "Uber Ride",
                    "allocation_code": "COST-01",
                    "receipt_path": dummy_recon_receipt
                },
                "Office Depot": {
                    "expense_type": "Office Supplies",
                    "business_purpose": "Team materials",
                    "comment": "Pens and notebooks",
                    "allocation_code": "COST-02"
                }
            }
            recon_res = client.reconcile_report(
                report_name="Reconciliation Report A",
                reconciliation_rules=recon_rules,
                headless=True,
                submit=True
            )
            assert recon_res["success"] is True, "Expected reconciliation to succeed"
            assert recon_res.get("submitted") is True, "Expected report to be submitted"
            print("         [PASS] Report transactions reconciled, receipt attached, and report submitted successfully.")
        finally:
            if os.path.exists(dummy_recon_receipt):
                os.remove(dummy_recon_receipt)

        # ----------------------------------------------------
        # 17. NEW FEATURE: Attach Receipt directly to Report transaction
        # ----------------------------------------------------
        print("\n[Step 17] Creating draft report and attaching a receipt directly to transaction...")
        client.create_draft_report(
            name="Receipt Upload Report A",
            purpose="Direct Receipt Upload Test",
            comment="Test direct attachment",
            headless=True
        )
        
        # Create a dummy file on the host to upload
        dummy_receipt = "tests/dummy_receipt.pdf"
        with open(dummy_receipt, "w") as f:
            f.write("MOCK RECEIPT CONTENT")
            
        try:
            attach_res = client.attach_receipt_to_transaction(
                report_name="Receipt Upload Report A",
                merchant_or_id="Uber",
                receipt_file_path=dummy_receipt,
                headless=True
            )
            assert attach_res["success"] is True, "Expected receipt upload to succeed"
            print("         [PASS] Direct receipt attachment verified.")
        finally:
            if os.path.exists(dummy_receipt):
                os.remove(dummy_receipt)

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
