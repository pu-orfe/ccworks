#!/usr/bin/env python3
import os
import sys
import argparse

# Adjust path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.browser_client import ConcurBrowserClient


def run_live_receipts_smoke_test():
    parser = argparse.ArgumentParser(description="Live Concur Receipts Smoke Test")
    parser.add_argument("--delete", type=str, help="Name of a test receipt to delete from Available Receipts")
    args = parser.parse_args()

    session_file = "concur_session.json"
    
    if not os.path.exists(session_file):
        print(f"[ERROR] Session file '{session_file}' not found.")
        print("Please authenticate first by running: ./ccworks login")
        sys.exit(1)

    print("=" * 60)
    print("   RUNNING LIVE SAP CONCUR RECEIPTS SMOKE TEST (PLAYWRIGHT)")
    print("=" * 60)

    try:
        # Initialize client
        client = ConcurBrowserClient(
            session_file=session_file,
            base_url="https://www.concursolutions.com"
        )

        # ----------------------------------------------------
        # 1. READ (Query/List available receipts)
        # ----------------------------------------------------
        print("\n[Step 1] Querying available receipts store...")
        receipts = client.list_available_receipts(headless=True)
        print(f"[SUCCESS] Discovered {len(receipts)} receipt(s) in your gallery:")
        for idx, r in enumerate(receipts, 1):
            print(f"  {idx}. {r}")

        # ----------------------------------------------------
        # 2. DELETE (Only if user supplied a target name)
        # ----------------------------------------------------
        if args.delete:
            target = args.delete
            print(f"\n[Step 2] Attempting to delete available receipt '{target}'...")
            
            if target not in receipts:
                print(f"[ERROR] Receipt '{target}' was not found in the initial list. Aborting delete step.")
                sys.exit(1)
                
            delete_res = client.delete_available_receipt(
                receipt_name=target,
                headless=True
            )
            assert delete_res["success"] is True, "Delete available receipt failed."
            print(f"         [PASS] Receipt '{target}' deleted successfully.")

            # Verify deletion in list
            print(f"\n[Step 3] Querying receipts list again to verify deletion...")
            receipts_after = client.list_available_receipts(headless=True)
            print(f"         Remaining receipts: {receipts_after}")
            assert target not in receipts_after, f"Expected '{target}' to be removed from gallery."
            print("         [PASS] Verification complete.")
        else:
            print("\n[*] Note: To test the delete receipt workflow on a specific file, run:")
            print("    python3 tests/smoke_test_receipts.py --delete \"filename.pdf\"")

        print("\n" + "=" * 60)
        print(" [SUCCESS] LIVE RECEIPTS SMOKE TEST COMPLETED!")
        print("=" * 60 + "\n")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_live_receipts_smoke_test()
