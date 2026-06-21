#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.client import ConcurClient, ConcurError
from src.browser_client import ConcurBrowserClient


def run_tests():
    # Load .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="SAP Concur API & Browser Access Tester")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--api", action="store_true", help="Run the API client test suite")
    group.add_argument("--browser-login", action="store_true", help="Launch a headed browser for manual authentication and save session state")
    group.add_argument("--browser-query", action="store_true", help="Query and list current reports and available receipts via browser automation")
    group.add_argument("--browser-create", action="store_true", help="Run the browser automation to create a draft report headlessly")
    group.add_argument("--browser-create-headed", action="store_true", help="Run the browser automation to create a draft report in a headed browser (visible)")
    group.add_argument("--browser-delete", type=str, help="Delete an expense report by name using browser automation")
    group.add_argument("--browser-delete-all-reports", action="store_true", help="Delete all draft expense reports via browser")
    group.add_argument("--browser-delete-all-receipts", action="store_true", help="Delete all available receipts via browser")
    group.add_argument("--browser-delete-all", action="store_true", help="Delete all draft expense reports AND all available receipts via browser")
    group.add_argument("--browser-query-old", action="store_true", help="Query and list historical/old expense reports")
    group.add_argument("--browser-report-details", type=str, help="Get detailed view of an expense report by name")
    group.add_argument("--browser-list-cards", action="store_true", help="Query and list credit card transactions")
    group.add_argument("--browser-card-details", type=str, help="Get detailed view of a card transaction by merchant or ID")
    group.add_argument("--browser-add-delegate", type=str, help="Add a new expense delegate by name or email")
    group.add_argument("--browser-remove-delegate", type=str, help="Remove an expense delegate by name or email")
    group.add_argument("--browser-reconcile", type=str, help="Reconcile transactions of an expense report by name (uses mock rules or JSON config)")
    group.add_argument("--browser-attach-receipt", type=str, help="Attach a receipt file to a transaction in a report. Specify report name as value.")

    # Helper arguments
    parser.add_argument("--filter-view", type=str, default="Last 90 Days", help="Filter view for reports or card transactions (default: 'Last 90 Days' or 'All Corporate and Personal Cards')")
    parser.add_argument("--delegate-perms", nargs="+", default=["prepare"], help="Permissions for delegate adding (prepare, submit, approve) (default: ['prepare'])")
    parser.add_argument("--reconcile-rules", type=str, help="Path to a JSON file containing reconciliation rules")
    parser.add_argument("--merchant", type=str, help="Merchant name or transaction ID to match receipt against")
    parser.add_argument("--receipt-path", type=str, help="Local file path of the receipt (PDF or image)")
    parser.add_argument("--submit", action="store_true", help="Submit the report after reconciling (default: False, review-only)")
    parser.add_argument("--name", type=str, help="Name of report to create")
    parser.add_argument("--purpose", type=str, help="Business purpose of report to create")
    parser.add_argument("--comment", type=str, help="Additional comment for report to create")

    args = parser.parse_args()

    # ----------------------------------------------------
    # Flow A: Live API Client Tester
    # ----------------------------------------------------
    if args.api:
        client_id = os.getenv("CONCUR_CLIENT_ID")
        client_secret = os.getenv("CONCUR_CLIENT_SECRET")
        token_url = os.getenv("CONCUR_TOKEN_URL", "https://us.api.concursolutions.com/oauth2/v0/token")
        base_url = os.getenv("CONCUR_BASE_URL", "https://us.api.concursolutions.com")
        user_login_id = os.getenv("CONCUR_USER_LOGIN_ID")

        print("=" * 60)
        print("           SAP Concur API Access Tester Script")
        print("=" * 60)

        missing_vars = []
        if not client_id or client_id == "your_client_id_here":
            missing_vars.append("CONCUR_CLIENT_ID")
        if not client_secret or client_secret == "your_client_secret_here":
            missing_vars.append("CONCUR_CLIENT_SECRET")
        if not user_login_id or user_login_id == "user@example.com":
            missing_vars.append("CONCUR_USER_LOGIN_ID")

        if missing_vars:
            print("\n[!] Configuration Missing.")
            print("Please configure your credentials in the '.env' file.")
            print("Required variables missing:")
            for var in missing_vars:
                print(f"  - {var}")
            print("\nYou can copy '.env.example' to '.env' and update it:")
            print("  cp .env.example .env")
            print("=" * 60)
            sys.exit(1)

        print(f"[*] Base URL:  {base_url}")
        print(f"[*] Token URL: {token_url}")
        print(f"[*] Test User: {user_login_id}")
        print(f"[*] Client ID: {client_id[:6]}... (truncated)")
        print("-" * 60)

        try:
            client = ConcurClient(
                client_id=client_id,
                client_secret=client_secret,
                token_url=token_url,
                base_url=base_url
            )

            print("\n[Phase 1] Attempting authentication...")
            token = client.get_token()
            print("[SUCCESS] Authentication succeeded!")
            print(f"          Access token acquired (starts with: '{token[:12]}...')")

            print("\n[Phase 2] Attempting to list existing reports...")
            reports = client.list_reports(user_login_id=user_login_id, limit=5)
            print(f"[SUCCESS] Successfully connected to report list API!")
            print(f"          Retrieved {len(reports)} recent report(s):")
            
            for idx, report in enumerate(reports, 1):
                report_name = report.get("Name", "Unnamed Report")
                report_id = report.get("ReportID") or report.get("ID") or "N/A"
                report_status = report.get("ReportStatus") or report.get("ApprovalStatus") or "N/A"
                total = report.get("Total", 0.0)
                currency = report.get("CurrencyCode", "")
                print(f"            {idx}. [{report_id}] {report_name} - Status: {report_status} ({total} {currency})")

            print("\n[Phase 3] Attempting to create draft report...")
            report_name = f"API Test Draft {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            purpose = "Validating programmatic creation of draft reports"
            comment = "Created automatically via SAP Concur Python API Access Tester"

            created_report = client.create_draft_report(
                user_login_id=user_login_id,
                name=report_name,
                purpose=purpose,
                comment=comment
            )

            print("[SUCCESS] Programmatic report creation succeeded!")
            print(f"          New Report Name: {created_report.get('Name')}")
            print(f"          Report ID:       {created_report.get('ReportID') or created_report.get('ID')}")
            print(f"          Status:          {created_report.get('ReportStatus', 'Draft / Not Submitted')}")
            print("-" * 60)
            print("\n[SUMMARY] All API tests passed! You have full read/write access.")

        except ConcurError as e:
            print(f"\n[ERROR] An API error occurred during testing:")
            print(f"        {str(e)}")
            print("-" * 60)
            sys.exit(1)
        except Exception as e:
            print(f"\n[UNEXPECTED ERROR] An unexpected error occurred:")
            print(f"        {str(e)}")
            print("-" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow B: Browser Manual Login Session Save
    # ----------------------------------------------------
    elif args.browser_login:
        print("=" * 60)
        print("       SAP Concur Browser Authentication Session Setup")
        print("=" * 60)
        
        try:
            browser_client = ConcurBrowserClient()
            browser_client.run_headed_login()
            print("\n[SUCCESS] Setup complete. You can now run browser-based automations.")
            print("To run the draft creator, use: python3 src/cli.py --browser-create")
        except Exception as e:
            print(f"\n[ERROR] Failed to run manual login setup: {str(e)}")
            sys.exit(1)

    # ----------------------------------------------------
    # Flow C: Browser Query (List Reports + List Receipts)
    # ----------------------------------------------------
    elif args.browser_query:
        print("=" * 60)
        print("     SAP Concur Browser-Based Expense & Receipt Query")
        print("=" * 60)
        
        try:
            browser_client = ConcurBrowserClient()
            
            # Query reports
            print("\n[*] Querying active expense reports...")
            reports = browser_client.list_reports(headless=True)
            print(f"[SUCCESS] Discovered {len(reports)} expense report(s):")
            for idx, r in enumerate(reports, 1):
                print(f"  {idx}. {r.get('name')} (Purpose: {r.get('purpose', 'None')})")

            # Query available receipts
            print("\n[*] Querying available receipts gallery...")
            receipts = browser_client.list_available_receipts(headless=True)
            print(f"[SUCCESS] Discovered {len(receipts)} uploaded receipt(s):")
            for idx, name in enumerate(receipts, 1):
                print(f"  {idx}. {name}")
                
            print("\n" + "=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Browser query failed: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow D: Browser Draft Report Creation (Headless/Headed)
    # ----------------------------------------------------
    elif args.browser_create or args.browser_create_headed:
        print("=" * 60)
        print("     SAP Concur Browser-Based Draft Report Creation")
        print("=" * 60)
        
        headless = not args.browser_create_headed
        report_name = args.name or f"Browser Test Draft {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        purpose = args.purpose or "Validating browser-based creation of draft reports"
        comment = args.comment or "Created automatically via SAP Concur Python Playwright Tester"

        try:
            browser_client = ConcurBrowserClient()
            result = browser_client.create_draft_report(
                name=report_name,
                purpose=purpose,
                comment=comment,
                headless=headless
            )
            print("\n[SUCCESS] Browser automation completed successfully!")
            print(f"          Report Created: {result.get('report_name')}")
            print(f"          Screenshots folder: {result.get('screenshot_folder')}")
            print(f"          Notes:          {result.get('notes')}")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Browser automation failed:")
            print(f"        {str(e)}")
            print("        Screenshots on failure are saved in the 'screenshots' folder.")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow E: Browser Delete Report
    # ----------------------------------------------------
    elif args.browser_delete:
        report_name = args.browser_delete
        print("=" * 60)
        print(f"     SAP Concur Browser-Based Delete Report: '{report_name}'")
        print("=" * 60)
        
        try:
            browser_client = ConcurBrowserClient()
            browser_client.delete_report(name=report_name, headless=True)
            print(f"\n[SUCCESS] Successfully deleted report: '{report_name}'")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to delete report: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow F: Delete All Reports
    # ----------------------------------------------------
    elif args.browser_delete_all_reports:
        print("=" * 60)
        print("   SAP Concur Browser-Based Delete All Reports")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            print("[*] Querying reports...")
            reports = browser_client.list_reports(headless=True)
            print(f"[*] Discovered {len(reports)} report(s).")
            for r in reports:
                name = r.get("name")
                print(f"[*] Deleting report: '{name}'...")
                browser_client.delete_report(name=name, headless=True)
            print("\n[SUCCESS] All reports deleted.")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to delete all reports: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow G: Delete All Receipts
    # ----------------------------------------------------
    elif args.browser_delete_all_receipts:
        print("=" * 60)
        print("   SAP Concur Browser-Based Delete All Receipts")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            print("[*] Querying available receipts...")
            receipts = browser_client.list_available_receipts(headless=True)
            print(f"[*] Discovered {len(receipts)} receipt(s).")
            for r_name in receipts:
                print(f"[*] Deleting receipt: '{r_name}'...")
                browser_client.delete_available_receipt(receipt_name=r_name, headless=True)
            print("\n[SUCCESS] All available receipts deleted.")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to delete all receipts: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow H: Delete All Reports AND Receipts (Nuke)
    # ----------------------------------------------------
    elif args.browser_delete_all:
        print("=" * 60)
        print("   SAP Concur Browser-Based Nuke (Delete All Reports & Receipts)")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            
            # Reports
            print("[*] Querying reports...")
            reports = browser_client.list_reports(headless=True)
            print(f"[*] Discovered {len(reports)} report(s).")
            for r in reports:
                name = r.get("name")
                print(f"[*] Deleting report: '{name}'...")
                browser_client.delete_report(name=name, headless=True)
                
            # Receipts
            print("\n[*] Querying available receipts...")
            receipts = browser_client.list_available_receipts(headless=True)
            print(f"[*] Discovered {len(receipts)} receipt(s).")
            for r_name in receipts:
                print(f"[*] Deleting receipt: '{r_name}'...")
                browser_client.delete_available_receipt(receipt_name=r_name, headless=True)
                
            print("\n[SUCCESS] All reports and receipts deleted.")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to delete all items: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow I: Query Historical (Old) Reports
    # ----------------------------------------------------
    elif args.browser_query_old:
        filter_val = args.filter_view or "Last 90 Days"
        print("=" * 60)
        print(f"     SAP Concur Browser-Based Historical Reports (Filter: {filter_val})")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            reports = browser_client.list_reports(filter_view=filter_val, headless=True)
            print(f"[SUCCESS] Discovered {len(reports)} historical report(s):")
            for idx, r in enumerate(reports, 1):
                print(f"  {idx}. {r.get('name')} (Purpose: {r.get('purpose', 'None')})")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Historical reports query failed: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow J: Report Details of a Report
    # ----------------------------------------------------
    elif args.browser_report_details:
        report_name = args.browser_report_details
        filter_val = args.filter_view
        print("=" * 60)
        print(f"     SAP Concur Report Details: '{report_name}'")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            details = browser_client.get_report_details(name=report_name, filter_view=filter_val, headless=True)
            print(f"[SUCCESS] Details retrieved:")
            print(f"  Name:     {details.get('report_name')}")
            print(f"  Number:   {details.get('report_number')}")
            print(f"  Purpose:  {details.get('purpose')}")
            print(f"  Comment:  {details.get('comment')}")
            print(f"  Expenses: ({len(details.get('expenses'))} items)")
            for item in details.get('expenses'):
                print(f"    - {item.get('raw_text')}")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to get report details: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow K: List Card Transactions
    # ----------------------------------------------------
    elif args.browser_list_cards:
        filter_val = args.filter_view or "All Corporate and Personal Cards"
        print("=" * 60)
        print(f"     SAP Concur Card Transactions (Filter: {filter_val})")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            txs = browser_client.list_card_transactions(card_type_filter=filter_val, headless=True)
            print(f"[SUCCESS] Discovered {len(txs)} transaction(s):")
            for idx, t in enumerate(txs, 1):
                print(f"  {idx}. {t.get('raw_text')}")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Listing card transactions failed: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow L: Get Card Transaction Details
    # ----------------------------------------------------
    elif args.browser_card_details:
        tx_id = args.browser_card_details
        filter_val = args.filter_view
        print("=" * 60)
        print(f"     SAP Concur Card Transaction Details: '{tx_id}'")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            details = browser_client.get_card_transaction_details(merchant_or_id=tx_id, card_type_filter=filter_val, headless=True)
            print(f"[SUCCESS] Transaction details:")
            print(f"  Merchant:     {details.get('merchant')}")
            print(f"  Date:         {details.get('date')}")
            print(f"  Amount:       {details.get('amount')}")
            print(f"  ID:           {details.get('transaction_id')}")
            print(f"  Card Program: {details.get('card_program')}")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to get transaction details: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow M: Add Delegate
    # ----------------------------------------------------
    elif args.browser_add_delegate:
        name = args.browser_add_delegate
        perms = args.delegate_perms or ["prepare"]
        print("=" * 60)
        print(f"     SAP Concur Add Expense Delegate: '{name}'")
        print(f"     Permissions: {perms}")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            browser_client.add_expense_delegate(name_or_email=name, permissions=perms, headless=True)
            print(f"\n[SUCCESS] Delegate '{name}' added successfully!")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to add delegate: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow N: Remove Delegate
    # ----------------------------------------------------
    elif args.browser_remove_delegate:
        name = args.browser_remove_delegate
        print("=" * 60)
        print(f"     SAP Concur Remove Expense Delegate: '{name}'")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            browser_client.remove_expense_delegate(name_or_email=name, headless=True)
            print(f"\n[SUCCESS] Delegate '{name}' removed successfully!")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to remove delegate: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow O: Reconcile Report Transactions
    # ----------------------------------------------------
    elif args.browser_reconcile:
        report_name = args.browser_reconcile
        rules_path = args.reconcile_rules
        import json
        
        reconciliation_rules = {
            "Uber": {
                "expense_type": "Ground Transportation",
                "business_purpose": "Client dinner ride",
                "comment": "Uber Ride",
                "allocation_code": "COST-01"
            },
            "Office Depot": {
                "expense_type": "Office Supplies",
                "business_purpose": "Team materials",
                "comment": "Pens and notebooks",
                "allocation_code": "COST-02"
            }
        }
        
        if rules_path:
            try:
                with open(rules_path, "r") as f:
                    reconciliation_rules = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load reconciliation rules JSON from '{rules_path}': {str(e)}")
                sys.exit(1)
                
        print("=" * 60)
        print(f"     SAP Concur Report Reconciliation: '{report_name}'")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            res = browser_client.reconcile_report(
                report_name=report_name,
                reconciliation_rules=reconciliation_rules,
                headless=True,
                submit=args.submit
            )
            if args.submit:
                print(f"\n[SUCCESS] Report '{report_name}' reconciled and submitted successfully!")
            else:
                print(f"\n[SUCCESS] Report '{report_name}' reconciled successfully! (Draft mode, not submitted)")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Reconciliation failed: {str(e)}")
            print("=" * 60)
            sys.exit(1)

    # ----------------------------------------------------
    # Flow P: Attach Receipt to Transaction
    # ----------------------------------------------------
    elif args.browser_attach_receipt:
        report_name = args.browser_attach_receipt
        merchant = args.merchant
        receipt_path = args.receipt_path

        if not merchant or not receipt_path:
            print("[ERROR] Please specify both --merchant and --receipt-path when attaching a receipt.")
            sys.exit(1)

        print("=" * 60)
        print(f"     SAP Concur Attach Receipt: '{receipt_path}' to '{merchant}' in '{report_name}'")
        print("=" * 60)
        try:
            browser_client = ConcurBrowserClient()
            browser_client.attach_receipt_to_transaction(
                report_name=report_name,
                merchant_or_id=merchant,
                receipt_file_path=receipt_path,
                headless=True
            )
            print(f"\n[SUCCESS] Receipt '{receipt_path}' attached successfully!")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Failed to attach receipt: {str(e)}")
            print("=" * 60)
            sys.exit(1)


if __name__ == "__main__":
    run_tests()
