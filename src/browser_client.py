import os
import time
import logging
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ConcurBrowserClient")


class ConcurBrowserClient:
    """Browser automation client for SAP Concur using Playwright."""

    def __init__(
        self,
        session_file: str = "concur_session.json",
        base_url: str = "https://www.concursolutions.com"
    ):
        self.session_file = session_file
        self.base_url = base_url.rstrip("/")
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _take_screenshot(self, page: Any, name: str) -> str:
        """Helper to capture screenshots for debugging."""
        path = os.path.join(self.screenshot_dir, f"{name}.png")
        try:
            page.screenshot(path=path)
            logger.info(f"Captured screenshot: {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to capture screenshot {name}: {str(e)}")
            return ""

    def _wait_for_dashboard(self, page: Any) -> None:
        """Helper to wait for Concur's dynamic SPA dashboard elements to load."""
        logger.info("Waiting for Concur dashboard to render (handling loading spinners)...")
        try:
            # Wait for standard load state
            page.wait_for_load_state("load", timeout=15000)
        except Exception:
            pass

        # Combined selectors representing that the dashboard loading is complete
        # (Either reports list empty state, any report card, or the create report buttons)
        combined_selectors = [
            "#create-report-btn",
            "button:has-text('Create New Report')",
            "button:has-text('Create Report')",
            "button:has-text('Create Expense Report')",
            "span:has-text('Create Expense Report')",
            ".no-reports",
            ".report-card",
            ".cnqr-report-card",
            ".sapMCard",
            "h2:has-text('Available Receipts')"
        ]
        combined_str = ", ".join(combined_selectors)

        try:
            # Generous 30 second timeout for the dynamic components
            page.locator(combined_str).first.wait_for(state="visible", timeout=30000)
            logger.info("Dashboard components loaded and visible.")
        except Exception as e:
            logger.warning(f"Proceeding after dashboard load timeout: {str(e)}")

    def run_headed_login(self) -> None:
        """
        Launches a headed browser instance to let the user log in manually
        and handle MFA/2FA or SSO. Once logged in, it saves the session state.
        """
        logger.info("Starting headed browser for login...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            logger.info(f"Navigating to login page: {self.base_url}")
            page.goto(self.base_url)

            print("\n" + "=" * 80)
            print(" ACTION REQUIRED:")
            print(" 1. In the opened browser window, log in to SAP Concur.")
            print(" 2. Complete any MFA/2FA, Single Sign-On (SSO), or Captchas if prompted.")
            print(" 3. Once you see the Concur Homepage / Dashboard (fully logged in),")
            print("    return to this terminal and press ENTER to save your session.")
            print("=" * 80 + "\n")

            input("Press ENTER here after you have logged in and see the Concur home page...")

            context.storage_state(path=self.session_file)
            logger.info(f"Session state successfully saved to {self.session_file}")
            browser.close()
            logger.info("Browser closed.")

    def create_draft_report(
        self,
        name: str,
        purpose: Optional[str] = None,
        comment: Optional[str] = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Loads the saved session and attempts to create a draft expense report.
        Captures screenshots at each step for verification and debugging.
        """
        if not os.path.exists(self.session_file):
            raise FileNotFoundError(
                f"Session file '{self.session_file}' not found. "
                "Please run login configuration first using: python3 src/cli.py --browser-login"
            )

        logger.info(f"Launching browser (headless={headless}) using session from {self.session_file}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                storage_state=self.session_file,
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            try:
                dashboard_url = f"{self.base_url}/nui/expense"
                logger.info(f"Navigating to Concur Expense page: {dashboard_url}")
                page.goto(dashboard_url, timeout=30000)
                
                # Check for login redirection
                current_url = page.url
                if "login" in current_url.lower() or "signin" in current_url.lower():
                    self._take_screenshot(page, "session_expired_error")
                    raise RuntimeError("Session appears to have expired. Please re-run '--browser-login'.")

                # Wait for SPA widgets to load
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "01_expense_dashboard")

                # Step 1: Click "Create New Report"
                logger.info("Locating 'Create New Report' button...")
                create_button = None
                selectors = [
                    # Real Concur selector strategies
                    lambda p: p.get_by_text("Create Expense Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create Expense Report", exact=False),
                    lambda p: p.locator("text=Create Expense Report"),
                    lambda p: p.locator("button:has-text('Create Expense Report')"),
                    
                    # Alternative selector fallbacks
                    lambda p: p.get_by_role("button", name="Create New Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create Report", exact=False),
                    lambda p: p.locator("button:has-text('Create New Report')"),
                    lambda p: p.locator("button:has-text('Create Report')"),
                    lambda p: p.locator("a:has-text('Create New Report')"),
                    lambda p: p.locator("a:has-text('Create Report')"),
                    lambda p: p.locator("#create-report-btn"),
                    lambda p: p.locator(".sapMBtnContent:has-text('Create New Report')")
                ]

                for idx, get_sel in enumerate(selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            create_button = loc
                            logger.info(f"Found 'Create New Report' using selector strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not create_button:
                    self._take_screenshot(page, "create_button_not_found")
                    raise RuntimeError("Could not locate 'Create New Report' button.")

                create_button.click()
                logger.info("Clicked 'Create New Report' button.")
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "02_create_report_dialog")

                # Step 2: Fill in the Report Header Form
                logger.info("Filling out the report header form...")

                # Name input selector
                name_input = page.get_by_role("textbox", name="Report Name", exact=False)
                if not name_input.is_visible(timeout=2000):
                    name_input = page.locator("#reportname, input[id*='reportname'], input[id*='ReportName'], input[name*='name']")
                
                if name_input.is_visible(timeout=2000):
                    name_input.fill(name)
                    logger.info(f"Filled Report Name: {name}")
                else:
                    raise RuntimeError("Could not find standard Report Name input field.")

                # Purpose input
                if purpose:
                    purpose_input = page.get_by_role("textbox", name="Purpose", exact=False)
                    if not purpose_input.is_visible(timeout=1000):
                        purpose_input = page.locator("#purpose, textarea[id*='purpose'], input[id*='purpose']")
                    
                    if purpose_input.is_visible(timeout=1000):
                        purpose_input.fill(purpose)
                        logger.info("Filled Purpose field.")

                # Comment input
                if comment:
                    comment_input = page.get_by_role("textbox", name="Comment", exact=False)
                    if not comment_input.is_visible(timeout=1000):
                        comment_input = page.locator("#comment, textarea[id*='comment'], input[id*='comment']")
                    
                    if comment_input.is_visible(timeout=1000):
                        comment_input.fill(comment)
                        logger.info("Filled Comment field.")

                self._take_screenshot(page, "03_filled_form")

                # Step 3: Click "Create Report" / "Next" / "Save"
                logger.info("Submitting the report form...")
                submit_button = None
                submit_selectors = [
                    lambda p: p.get_by_role("button", name="Create Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create", exact=True),
                    lambda p: p.get_by_role("button", name="Next", exact=True),
                    lambda p: p.get_by_role("button", name="Save", exact=True),
                    lambda p: p.locator("#submit-report-btn"),
                    lambda p: p.locator("button:has-text('Create Report')")
                ]

                for idx, get_sel in enumerate(submit_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            submit_button = loc
                            logger.info(f"Found submit button using selector strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not submit_button:
                    self._take_screenshot(page, "submit_button_not_found")
                    raise RuntimeError("Could not locate Create/Next/Save button in report form.")

                submit_button.click()
                logger.info("Clicked form submission button.")
                page.wait_for_timeout(3000)

                self._take_screenshot(page, "04_after_creation_completed")
                logger.info("Report creation completed!")

                return {
                    "success": True,
                    "report_name": name,
                    "screenshot_folder": os.path.abspath(self.screenshot_dir),
                    "notes": "Verify details in screenshots/04_after_creation_completed.png"
                }

            except PlaywrightTimeoutError as e:
                self._take_screenshot(page, "timeout_error")
                raise RuntimeError(f"Playwright operation timed out: {str(e)}")
            except Exception as e:
                self._take_screenshot(page, "unexpected_browser_error")
                raise e
            finally:
                browser.close()

    def list_reports(self, headless: bool = True) -> List[Dict[str, Any]]:
        """
        [READ] Navigates to the Expense page and retrieves all visible reports.
        """
        logger.info(f"Listing expense reports via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            reports = []
            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "list_reports_dashboard")

                # Handle empty state
                if page.locator(".no-reports").is_visible(timeout=2000):
                    logger.info("No reports found on dashboard.")
                    return []

                # Selector options to locate report containers (supports Mock UI and standard Concur UIs)
                card_selectors = [".report-card", ".cnqr-report-card", ".sapMCard"]
                cards = None
                for selector in card_selectors:
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        cards = loc
                        logger.info(f"Found report cards using selector '{selector}'.")
                        break

                if not cards:
                    cards = page.locator(".sapMListUl .sapMLIB")
                
                count = cards.count()
                logger.info(f"Discovered {count} report item(s) on page.")

                for i in range(count):
                    card = cards.nth(i)
                    
                    # Extract Name
                    name_selectors = [".report-name", ".cnqr-report-name", ".sapMObjLTitle", "h3"]
                    name = "Unknown Report"
                    for ns in name_selectors:
                        sub = card.locator(ns)
                        if sub.count() > 0:
                            name = sub.first.text_content().strip()
                            break

                    # Extract Purpose / Info
                    purpose_selectors = [".report-purpose", ".sapMObjLDescription", "p"]
                    purpose = ""
                    for ps in purpose_selectors:
                        sub = card.locator(ps)
                        if sub.count() > 0:
                            purpose = sub.first.text_content().strip()
                            break

                    reports.append({
                        "index": i,
                        "name": name,
                        "purpose": purpose
                    })
                    logger.info(f"  Report {i+1}: {name} ({purpose})")

            except Exception as e:
                logger.error(f"Error listing reports: {str(e)}")
            finally:
                browser.close()
            return reports

    def update_report(
        self,
        old_name: str,
        new_name: str,
        new_purpose: Optional[str] = None,
        new_comment: Optional[str] = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        [UPDATE] Locates an expense report by its current name, enters edit mode,
        modifies its headers, and saves it.
        """
        logger.info(f"Updating report '{old_name}' -> '{new_name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "update_report_pre")

                # Find the card containing the old name
                card = page.locator(".report-card").filter(has_text=old_name)
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=old_name)
                
                if card.count() == 0:
                    raise FileNotFoundError(f"No report named '{old_name}' found to edit.")

                # Click "Edit" or open the report
                edit_btn = card.get_by_role("button", name="Edit", exact=False)
                if edit_btn.is_visible(timeout=2000):
                    edit_btn.click()
                else:
                    card.first.click()
                    page.wait_for_timeout(2000)
                    page.get_by_role("button", name="Report Details", exact=False).click()
                    page.get_by_role("menuitem", name="Edit Report Info", exact=False).click()

                page.wait_for_timeout(2000)
                self._take_screenshot(page, "update_report_dialog")

                # Refill form fields
                name_input = page.locator("#reportname, input[id*='reportname'], input[id*='ReportName']")
                name_input.fill(new_name)

                if new_purpose:
                    page.locator("#purpose, textarea[id*='purpose'], input[id*='purpose']").fill(new_purpose)
                if new_comment:
                    page.locator("#comment, textarea[id*='comment']").fill(new_comment)

                self._take_screenshot(page, "update_report_form_filled")

                # Save changes
                save_btn = page.get_by_role("button", name="Save", exact=True)
                if not save_btn.is_visible(timeout=2000):
                    save_btn = page.locator("#submit-report-btn, button:has-text('Save')")
                save_btn.click()
                
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "update_report_post")
                logger.info(f"Report '{old_name}' successfully updated to '{new_name}'!")
                return {"success": True, "name": new_name}

            except Exception as e:
                self._take_screenshot(page, "update_error")
                raise e
            finally:
                browser.close()

    def delete_report(self, name: str, headless: bool = True) -> Dict[str, Any]:
        """
        [DELETE] Locates an expense report by its name, clicks delete, and confirms.
        """
        logger.info(f"Deleting report '{name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "delete_report_pre")

                # Find target report card
                card = page.locator(".report-card").filter(has_text=name)
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=name)

                if card.count() == 0:
                    raise FileNotFoundError(f"No report named '{name}' found to delete.")

                # Set up listener for dialog popups (like window.confirm prompt)
                page.on("dialog", lambda dialog: dialog.accept())

                # Click Delete
                delete_btn = card.get_by_role("button", name="Delete", exact=False)
                if delete_btn.is_visible(timeout=2000):
                    delete_btn.click()
                else:
                    checkbox = card.locator("input[type='checkbox'], .sapMCb")
                    checkbox.first.click()
                    page.get_by_role("button", name="Delete Report", exact=False).click()
                    page.get_by_role("button", name="Yes, Delete", exact=False).click()

                page.wait_for_timeout(3000)
                self._take_screenshot(page, "delete_report_post")
                logger.info(f"Report '{name}' successfully deleted!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "delete_error")
                raise e
            finally:
                browser.close()

    def list_available_receipts(self, headless: bool = True) -> List[str]:
        """
        [READ RECEIPTS] Navigates to the Expense page and lists names of available receipts.
        """
        logger.info(f"Listing available receipts via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            receipts = []
            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "list_receipts_dashboard")

                # Selector for thumbnails (try most specific class first)
                thumb_selectors = [".receipt-name", ".available-receipt-thumbnail", "[class*='receipt']"]
                thumbnails = None
                for sel in thumb_selectors:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        thumbnails = loc
                        break

                if thumbnails:
                    count = thumbnails.count()
                    for i in range(count):
                        txt = thumbnails.nth(i).text_content().strip()
                        if "\n" in txt:
                            txt = txt.split("\n")[-1].strip()
                        if txt:
                            receipts.append(txt)
                            logger.info(f"  Receipt {i+1}: {txt}")

            except Exception as e:
                logger.error(f"Error listing receipts: {str(e)}")
            finally:
                browser.close()
            return list(set(receipts))  # Remove duplicates

    def delete_available_receipt(self, receipt_name: str, headless: bool = True) -> Dict[str, Any]:
        """
        [DELETE RECEIPT] Navigates to the Expense page, locates the receipt thumbnail
        in the 'Available Receipts' section, opens it, clicks delete, and confirms.
        """
        logger.info(f"Deleting available receipt '{receipt_name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "delete_receipt_dashboard_pre")

                # Find the receipt thumbnail
                thumb_selectors = [
                    ".available-receipt-thumbnail",
                    ".available-receipt-card",
                    ".receipt-thumbnail",
                    ".cnqr-receipt-card",
                    "[class*='receipt']"
                ]

                thumbnail = None
                for selector in thumb_selectors:
                    loc = page.locator(selector).filter(has_text=receipt_name)
                    if loc.count() > 0:
                        thumbnail = loc.first
                        logger.info(f"Found receipt thumbnail using selector '{selector}'.")
                        break

                if not thumbnail:
                    raise FileNotFoundError(f"No available receipt named '{receipt_name}' found.")

                page.on("dialog", lambda dialog: dialog.accept())

                thumbnail.click()
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "delete_receipt_viewer_open")

                # Click the Delete button inside the viewer
                delete_btn = None
                delete_selectors = [
                    lambda p: p.get_by_role("button", name="Delete Receipt", exact=False),
                    lambda p: p.get_by_role("button", name="Delete", exact=False),
                    lambda p: p.locator("#delete-receipt-btn"),
                    lambda p: p.locator("button:has-text('Delete')")
                ]

                for idx, get_sel in enumerate(delete_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            delete_btn = loc
                            logger.info(f"Found receipt delete button using strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not delete_btn:
                    raise RuntimeError("Could not locate Delete button in receipt viewer.")

                delete_btn.click()
                logger.info("Clicked delete button in receipt viewer.")
                
                try:
                    confirm_btn = page.get_by_role("button", name="Yes, Delete", exact=False)
                    if confirm_btn.is_visible(timeout=1000):
                        confirm_btn.click()
                        logger.info("Clicked confirmation confirmation button.")
                except Exception:
                    pass

                page.wait_for_timeout(3000)
                self._take_screenshot(page, "delete_receipt_post")
                logger.info(f"Receipt '{receipt_name}' successfully deleted!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "delete_receipt_error")
                raise e
            finally:
                browser.close()
