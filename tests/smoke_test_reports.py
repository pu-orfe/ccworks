#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime

# Adjust path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ccworks.browser_client import ConcurBrowserClient


def run_live_reports_smoke_test():
    session_file = "concur_session.json"
    
    if not os.path.exists(session_file):
        print(f"[ERROR] Session file '{session_file}' not found.")
        print("Please authenticate first by running: ./ccworks login")
        sys.exit(1)

    print("=" * 60)
    print("   RUNNING LIVE SAP CONCUR REPORTS SMOKE TEST (PLAYWRIGHT)")
    print("=" * 60)

    try:
        # Initialize client targeting real Concur SOLUTIONS URL
        client = ConcurBrowserClient(
            session_file=session_file,
            base_url="https://www.concursolutions.com"
        )

        timestamp = datetime.now().strftime("%y%m%d%H%M")
        report_name = f"Live Smoke {timestamp}"
        updated_name = f"{report_name} U"

        # ----------------------------------------------------
        # 1. CREATE (Create Report)
        # ----------------------------------------------------
        print(f"\n[Step 1] Creating draft report '{report_name}'...")
        create_res = client.create_draft_report(
            name=report_name,
            purpose="Automated Live Smoke Test",
            comment="Created during Playwright CRUD validation run",
            headless=True
        )
        assert create_res["success"] is True, "Create draft report failed."
        print(f"         [PASS] Report created.")

        # ----------------------------------------------------
        # 2. READ (Query/Verify existence)
        # ----------------------------------------------------
        print(f"\n[Step 2] Listing reports to verify '{report_name}' exists...")
        reports = client.list_reports(headless=True)
        names = [r["name"] for r in reports]
        print(f"         Found {len(reports)} report(s): {names}")
        assert any(report_name in n for n in names), f"Expected '{report_name}' in dashboard list."
        print("         [PASS] Report verified in dashboard list.")

        # ----------------------------------------------------
        # 3. UPDATE (Edit/Rename)
        # ----------------------------------------------------
        print(f"\n[Step 3] Renaming report to '{updated_name}'...")
        update_res = client.update_report(
            old_name=report_name,
            new_name=updated_name,
            new_purpose="Automated Live Smoke Test - Edited",
            headless=True
        )
        assert update_res["success"] is True, "Update report failed."
        print("         [PASS] Report updated successfully.")

        # ----------------------------------------------------
        # 4. READ (Verify Updated Name)
        # ----------------------------------------------------
        print(f"\n[Step 4] Listing reports to verify updated name...")
        reports_after = client.list_reports(headless=True)
        names_after = [r["name"] for r in reports_after]
        print(f"         Found {len(reports_after)} report(s): {names_after}")
        assert any(updated_name in n for n in names_after), f"Expected updated name '{updated_name}' in dashboard list."
        print("         [PASS] Updated name verified in dashboard list.")

        # ----------------------------------------------------
        # 5. DELETE (Cleanup)
        # ----------------------------------------------------
        print(f"\n[Step 5] Deleting report '{updated_name}'...")
        delete_res = client.delete_report(
            name=updated_name,
            headless=True
        )
        assert delete_res["success"] is True, "Delete report failed."
        print("         [PASS] Report deleted successfully.")

        # ----------------------------------------------------
        # 6. READ (Verify Cleanup)
        # ----------------------------------------------------
        print(f"\n[Step 6] Listing reports to verify deletion...")
        reports_final = client.list_reports(headless=True)
        names_final = [r["name"] for r in reports_final]
        print(f"         Final report(s): {names_final}")
        assert not any(updated_name in n for n in names_final), f"Report '{updated_name}' should have been removed."
        print("         [PASS] Report cleanup verified.")

        print("\n" + "=" * 60)
        print(" [SUCCESS] LIVE REPORTS CRUD SMOKE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60 + "\n")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_live_reports_smoke_test()
