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
        report_name = f"Browser Test Draft {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        purpose = "Validating browser-based creation of draft reports"
        comment = "Created automatically via SAP Concur Python Playwright Tester"

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


if __name__ == "__main__":
    run_tests()
