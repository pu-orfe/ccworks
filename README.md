# SAP Concur API & Browser Automation Test Suite

This project provides a unified Python integration client and test suite to verify connectivity and support programmatically creating draft expense reports in SAP Concur.

It supports two modes of interaction:
1. **API Integration (Direct)**: Uses SAP Concur REST APIs with OAuth 2.0 Client Credentials authentication (requires API permissions and administrative licensing).
2. **Browser Automation (Playwright)**: Automates a browser session to perform UI clicks (useful if your organization doesn't have Web Services API access or if direct API keys are unavailable).

---

## 🛠️ Prerequisites

### For API-Based Access
1. **Client Web Services License**: A valid license to enable API access.
2. **App Registration**: A registered application in the SAP Concur App Center to obtain a `Client ID` and `Client Secret`.
3. **Scopes**: Your application must have the `EXPRPT` (Expense Report) scope enabled.
4. **Target User Account**: A valid SAP Concur Login ID.

### For Browser-Based Automation
1. **Login Credentials**: Standard Concur username/password or SSO login.
2. **Playwright Setup**: Playwright must be installed locally along with chromium binaries (handled automatically by `./ccworks setup`).

---

## 🚀 Getting Started

### 1. Configuration

Copy the template `.env.example` file to `.env`, and populate it with your credentials:

```bash
cp .env.example .env
```

Open `.env` and fill in the details:
```env
CONCUR_CLIENT_ID=your_actual_client_id
CONCUR_CLIENT_SECRET=your_actual_client_secret
CONCUR_USER_LOGIN_ID=target_user_email@company.com
```

### 2. Setup Local Environment

Build the Python environment, install requirements, and download Playwright chromium browser binaries:

```bash
./ccworks setup
```

---

## 📂 Run Options

### Command Table

| Run Mode | Command | Scope / Notes |
| :--- | :--- | :--- |
| **Containerized Unit Tests** | `./ccworks test-docker` | Runs mock tests in Docker (Offline, credentials not needed). |
| **Local Unit Tests** | `./ccworks test-local` | Runs mock tests locally using `.venv`. |
| **Live API Test** | `./ccworks run-live` | Tests token retrieval, report listing, and report creation. |
| **Headed Browser Login** | `./ccworks login` | Boots browser window for manual login, saves authentication state. |
| **Headless Browser Creation**| `./ccworks create` | Programmatically logs in using saved state and creates a draft report. |
| **Visible Browser Creation** | `./ccworks create-headed` | Performs browser creation visibly on screen (useful for debugging). |
| **List Historical Reports** | `./ccworks query-old [filter]` | Query and list historical reports (e.g. "Last 90 Days"). |
| **Report Details** | `./ccworks report-details "Name" [--deep]` | Fetch line-item details of a specific report. Use `--deep` for full accuracy. |
| **List Card Transactions** | `./ccworks list-cards [filter]` | List credit card transactions under specific activity filters. |
| **Card Transaction Details** | `./ccworks card-details "Merchant/ID" [filter]` | Fetch details for a card transaction by name or ID. |
| **Add Expense Delegate** | `./ccworks add-delegate "Name" [perms...]` | Add delegate and assign permissions (prepare, submit, approve). |
| **Remove Expense Delegate** | `./ccworks remove-delegate "Name"` | Remove expense delegate from settings page. |
| **Reconcile Report** | `./ccworks reconcile "Name" [rules.json] [--submit]` | Reconcile report transactions with rules (review-only by default). |
| **Attach Receipt to Transaction** | `./ccworks attach-receipt "Name" "Merchant" "receipt.pdf"` | Attach local receipt file directly to a transaction row in a report. |
| **Update Report Transaction** | `./ccworks update-transaction "Name" [indices...] [args...]` | Bulk update fields (type, justification) of transaction rows in a report. |
| **Update Report Header** | `./ccworks update-report "Name" [--name "New"] [--purpose "P"] [--comment "C"]` | Update report header fields like name, purpose, and comment. |
| **Submit Report** | `./ccworks submit-report "Name"` | Finalize and submit an expense report for approval. |
| **List Transaction Allocations** | `./ccworks allocations "Name"` | List chartstring allocations (Dept, Fund, etc) for a report. |
| **Add Transaction Allocation** | `./ccworks add-allocation "Name" [idx] --dept "D" --fund "F"` | Programmatically set chartstring values for a transaction. |

---

## 🔍 Detailed Usage Examples & API Reference

### 1. Historical Expense Reports

Concur separates active draft reports from older, submitted, or processed reports via dropdown filters. The browser client automates navigating the reports grid, updating the view filter, and clicking individual cards to extract details.

* **List Old Reports:**
  ```bash
  # Query using the default 'Last 90 Days' filter
  ./ccworks query-old
  
  # Specify a custom filter (e.g., 'All Reports')
  ./ccworks query-old "All Reports"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Discovered 2 historical report(s):
    1. Old Lodging Report 2025 (Purpose: FY2025 Conference)
    2. Q1 Travel Report (Purpose: Client Visits Q1)
  ```

* **Get Report Details:**
  ```bash
  # Get line items and header details for a specific report
  ./ccworks report-details "Old Lodging Report 2025" --deep
  ```
  *Output Example:*
  ```text
  [SUCCESS] Details retrieved:
    Name:     Old Lodging Report 2025
    Number:   REP-100200
    Purpose:  FY2025 Conference
    Comment:  Approved & Paid
    Expenses: (2 items)
      - Date: 2026-06-12 | Type: Lodging | Amount: $150.00 | Merchant: Hilton
      - Date: 2026-06-13 | Type: Meal | Amount: $45.20 | Merchant: Italian Bistro
  ```

### 2. Credit Card Transactions

Automates listing and viewing credit card transactions inside the **Available Expenses** dashboard section. Supports selecting view activities such as "All Corporate and Personal Cards" or "All Purchasing Cards".

* **List Card Transactions:**
  ```bash
  # List corporate and personal cards (default)
  ./ccworks list-cards "All Corporate and Personal Cards"
  
  # List purchasing cards
  ./ccworks list-cards "All Purchasing Cards"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Discovered 1 transaction(s):
    1. Office Depot - $189.99
  ```

* **Get Transaction Details:**
  ```bash
  ./ccworks card-details "Office Depot" "All Purchasing Cards"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Transaction details:
    Merchant:     Office Depot
    Date:         2026-06-18
    Amount:       $189.99
    Transaction ID: TX_5002
    Card Program: Purchasing Card
  ```

### 3. Expense Delegates Settings

Automates adding and removing delegates, plus managing permissions in the profile settings (`/profile/editdelegates.asp`).

* **Add Expense Delegate:**
  Add a delegate by name or email, specifying checkboxes for permissions (`prepare`, `submit`, `approve`).
  ```bash
  # Add John Doe with Prepare and Submit permissions
  ./ccworks add-delegate "John Doe" prepare submit
  
  # Add Jane Smith with Prepare and Approve permissions
  ./ccworks add-delegate "Jane Smith" prepare approve
  ```

* **Remove Expense Delegate:**
  Remove a delegate by selecting their checkbox, triggering 'Delete', and saving the profiles page.
  ```bash
  ./ccworks remove-delegate "John Doe"
  ```

### 4. Month-End Expense Reconciliation

Reconciliation is a critical month-end task. The client navigates inside a report, reads the merchant list, and maps matching rules to fill in Expense Types, Business Purposes, Comments, and Allocation Codes for every transaction row. By default, it runs in **review-only mode** (leaving the report as a draft for your manual review). To automatically submit the report, pass the `--submit` flag.

* **Reconcile Report (Review-Only / Default):**
  ```bash
  # Reconcile using default built-in matching rules (does not submit)
  ./ccworks reconcile "Reconciliation Report A"
  
  # Reconcile using custom rules (does not submit)
  ./ccworks reconcile "Reconciliation Report A" my_recon_rules.json
  ```

* **Reconcile and Automatically Submit Report:**
  ```bash
  # Reconcile and submit immediately
  ./ccworks reconcile "Reconciliation Report A" --submit
  
  # Reconcile using custom rules and submit
  ./ccworks reconcile "Reconciliation Report A" my_recon_rules.json --submit
  ```
  
  *Example `my_recon_rules.json` file:*
  ```json
  {
    "Uber": {
      "expense_type": "Ground Transportation",
      "business_purpose": "Client travel to office",
      "comment": "Uber Ride",
      "allocation_code": "COST-CENTER-101"
    },
    "Office Depot": {
      "expense_type": "Office Supplies",
      "business_purpose": "Team whiteboard supplies",
      "comment": "Pens and notebooks",
      "allocation_code": "COST-CENTER-102"
    }
  }
  ```

### 5. Match & Attach Receipt Directly to Transaction

Matching receipt PDFs or images to individual card transactions can be automated. Playwright navigates into the expense report detail row matching your merchant name, locates the hidden file input element, and uploads the local file.

* **Attach Local Receipt to Report Expense:**
  ```bash
  ./ccworks attach-receipt "Receipt Upload Report A" "Uber" "receipts/uber_ride_receipt.pdf"
  ```

### 6. Read and Write Report & Transaction Fields (CRUD)

You can read or write individual transaction fields (Expense Type, Business Purpose, and Comments) as well as the main report header fields.

* **Update Report Header (Write/Update):**
  ```bash
  # Update report purpose and comment using the justification shortcut
  ./ccworks update-report "Transaction Report" --justification "Project Alpha research"

  # Rename a report and update its purpose
  ./ccworks update-report "Old Name" --name "New Name" --purpose "Updated purpose"
  ```

* **Update Transaction fields (Write/Update):**
  ```bash
  # Update Expense Type and Justification for multiple items (indices 1, 2, and 3)
  ./ccworks update-transaction "Transaction Report" 1 2 3 --type "Software" --justification "Required for project X"

  # Update specific fields for a single item
  ./ccworks update-transaction "Transaction Report" 1 --type "Ground Transportation" --purpose "Meeting client" --comment "Uber ride"
  ```

* **Remove/Clear fields (Delete/Remove):**
  ```bash
  # Clear a transaction comment field by passing an empty string
  ./ccworks update-transaction "Transaction Report" 1 --comment ""
  ```

* **Verify / Read details (Read):**
  ```bash
  # Use --deep to see full line-item justifications
  ./ccworks report-details "Transaction Report" --deep
  ```

* **Submit Report (Finalize):**
  ```bash
  # Finalize and submit the report for approval
  ./ccworks submit-report "Transaction Report"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Details retrieved:
    Name:     Transaction Report
    Number:   REP-8899
    Purpose:  Client lunch
    Comment:  N/A
    Expenses: (2 items)
      - Date: 2026-06-12 | Type: Ground Transportation | Amount: $24.50 | Merchant: Uber
        Type:             Ground Transportation
        Business Purpose: Meeting client for lunch
        Comment:          Test comment
   ```

### 7. Transaction Allocations (Chartstrings)

Automates reading and writing **Chartstrings** (Department, Fund, Program, etc.) for individual transaction rows. This is essential for organizations that require granular cost-center tracking.

* **List Current Allocations:**
  ```bash
  # List all allocations for every transaction in a report
  ./ccworks allocations "Project Alpha Report"
  ```
  *Output Example:*
  ```json
  [
    {
      "index": 0,
      "merchant": "Uber",
      "allocations": [
        {
          "raw_text": "(25605) ORF-Technical Support | (A0001) General Fund | (P999) Research"
        }
      ]
    }
  ]
  ```

* **Add a New Allocation (Chartstring):**
  ```bash
  # Add a specific chartstring to transaction index 1
  ./ccworks add-allocation "Project Alpha Report" 1 \
      --dept "(25605) ORF-Technical Support" \
      --fund "(A0001) General Fund" \
      --prog "(P999) Research"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Allocation added to transaction 1 in 'Project Alpha Report'!
    - Dept: (25605) ORF-Technical Support
    - Fund: (A0001) General Fund
    - Prog: (P999) Research
  ```

---

## 🤖 Integration with Pi Coding Agent (pi.dev)

This project includes a project-local extension for the **Pi** coding agent (an open-source terminal-based AI coding assistant at [pi.dev](https://pi.dev)).

The extension is written in TypeScript and is saved at `.pi/extensions/concur.ts`. It registers custom tools that allow the Pi agent to interact directly with your SAP Concur session.

### Registered Tools

1. **`concur_list_reports(filter_view, is_old)`**: Queries and lists active or historical expense reports.
2. **`concur_report_details(report_name, filter_view)`**: Fetches line-item details of a report.
3. **`concur_list_card_transactions(filter_view)`**: Lists card transactions from Available Expenses.
4. **`concur_reconcile_report(report_name, rules, submit)`**: Automatically reconciles transactions using JSON rules, and optionally submits the report (default: `submit` is false, leaving it in draft mode for review).
5. **`concur_attach_receipt(report_name, merchant, receipt_path)`**: Uploads and attaches a local receipt file to an expense.
6. **`concur_create_report(name, purpose, comment)`**: Creates a new draft expense report headlessly.
7. **`concur_delete_report(report_name)`**: Deletes a draft expense report by name.
8. **`concur_card_transaction_details(merchant_or_id, filter_view)`**: Fetches details of a specific credit card transaction by merchant or ID.
9. **`concur_add_delegate(name_or_email, permissions)`**: Adds a new expense delegate in settings with specified permissions.
10. **`concur_remove_delegate(name_or_email)`**: Removes an expense delegate from settings by name or email.
11. **`concur_nuke_drafts_and_receipts()`**: Deletes all draft reports and available receipts inside Concur (intended for testing cleanup).
12. **`concur_check_session()`**: Checks whether the currently saved browser session state is active and valid (returns true if authenticated, false if expired or missing).
13. **`concur_update_transaction(report_name, transaction_index, type, purpose, comment)`**: Updates fields (type, business purpose, comment) of a specific transaction inside an expense report.

### How to Enable

If you use Pi within this repository, it will automatically discover the extension located in the `.pi/extensions/` folder. You can also manually load it or reload your active session by running `/reload` inside the Pi terminal client.

> **Note:** `concur_check_session()` returns exit code **0** (authenticated) or **2** (invalid/expired session). It catches a non-zero exit and reports `false` instead of raising.

---

## 🔮 Recommended Future Features & Integrations

1. ~~Receipt-to-Report Attachment~~ *(Already implemented — see `attach-receipt` / `concur_attach_receipt`).*
2. **Expense Itemization Automation:**
   * *Description:* Parse lodging/hotel folios or receipt text (using OCR/LLM) and programmatically itemize room rates, room taxes, parking, and meals.
   * *Value:* Eliminates tedious manual breakdowns of hotel checkout bills.
3. **Approval workflows for Managers:**
   * *Description:* Scan pending approval reports, display total summaries, and click approve or send back to employees with custom comments.
   * *Value:* Streamlines managers' review process via CLI/Slack commands.
4. **Export to ERP/Accounting Formats:**
   * *Description:* Export queried reports and transactions directly to CSV, JSON, or standard ERP formats (SAP, NetSuite, QuickBooks).
   * *Value:* Syncs Concur expense data directly into business accounting books.

---

## ⚙️ CI/CD Pipeline

This project includes a fully automated **GitHub Actions CI/CD Pipeline** defined in `.github/workflows/ci.yml`. On every push and pull request to the `main` branch, it runs:

1. **Host-Based Unit Tests**: Runs mock API tests directly on the runner.
2. **Containerized Unit Tests**: Builds and executes mock unit tests inside a Docker container using `docker-compose`.
3. **End-to-End Browser Smoke & Regression Tests**: Launches a stateful mock server and runs headless Playwright tests, including full CRUD and justification/classification regression suites.

---

## 🔒 Handling Multi-Factor Authentication (MFA) & SSO in Browser Mode

Modern enterprise security often requires MFA or SSO login screens that standard automation cannot programmatically bypass. This project handles this using a **Session State Preservation** strategy:

1. Run the manual session setup:
   ```bash
   ./ccworks login
   ```
2. A headed Chromium window will open. Enter your email/password, solve SSO if prompted, and complete the MFA authentication.
3. Once logged in and redirected to the SAP Concur dashboard page, return to your terminal and press **ENTER**.
4. Your authenticated session token, cookies, and local storage are saved into `concur_session.json`.
5. Subsequent automated actions will load this file and run headlessly without requiring login or prompt parameters.

---

## 📂 Project Directory Structure

```
├── .env.example                          # Environment variables configuration template
├── .pi/
│   └── extensions/
│       └── concur.ts                     # Pi coding agent extension (13 tools)
├── Dockerfile                            # Docker container definition
├── docker-compose.yml                    # Service orchestration for testing
├── ccworks                                   # Zsh shell helper script (CLI entry point)
├── requirements.txt                      # Third-party Python dependencies
├── src/
│   ├── __init__.py
│   ├── browser_client.py                 # Playwright Browser Automation Client
│   ├── client.py                         # SAP Concur REST API integration (OAuth2)    
│   └── cli.py                            # Argument parsing, signal handling, command routing
├── tests/
│   ├── __init__.py
│   ├── mock_concur_server.py             # Stateful local mock SAP Concur Server
│   ├── smoke_test_reports.py             # Live reports CRUD smoke test (Playwright)
│   ├── smoke_test_receipts.py            # Live receipts list/delete smoke test
│   ├── test_allocations_crud.py          # Allocations read/write regression tests
│   ├── test_browser_smoke.py             # E2E local browser smoke tests against mock server
│   ├── test_client.py                    # Unit tests using requests mocks
│   ├── test_justification.py             # Justification & classification regression tests
│   └── test_transaction_fields_crud.py   # Transaction field (type/purpose/comment) CRUD tests
└── .github/
    └── workflows/
        └── ci.yml                        # GitHub Actions CI/CD workflow configuration
```
