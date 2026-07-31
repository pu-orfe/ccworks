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

### Install with Homebrew (recommended on macOS)

```bash
brew tap pu-orfe/tap
brew install ccworks
```

This gives you a `ccworks` command anywhere on your PATH. The first time you
run a browser-based command (e.g. `ccworks session login`), ccworks will prompt to
download Playwright's chromium browser (~180 MB) into
`~/Library/Caches/ms-playwright` — a one-time step.

Session state (login cookies, screenshots) is written to
`~/Library/Application Support/ccworks` (macOS) or
`$XDG_STATE_HOME/ccworks` (Linux). Override with `CCWORKS_STATE_DIR=/some/path`.

### Install from source (developers)

```bash
git clone https://github.com/pu-orfe/ccworks.git
cd ccworks
./ccworks setup       # creates .venv, `pip install -e .`, installs chromium
```

### One command surface

`ccworks` exposes a single set of commands, grouped by resource as
`<group> <subcommand>` — the convention used by `gh`, `kubectl`, and modern
`docker`:

```bash
ccworks report list
ccworks report show "Q1 Travel" --deep
ccworks card show "Office Depot"
ccworks session status
```

The two entry points accept identical arguments, **provided the installed
package is new enough to have this surface**:

| | `ccworks <group> <sub>` | `./ccworks <group> <sub>` |
| :--- | :--- | :--- |
| Source | Entry point from Homebrew / `pip install` | The zsh launcher in a repo checkout |
| Behaviour | The CLI itself | Manages `.venv`, then forwards **verbatim** to the CLI |
| Tracks | The released version you installed | Your working tree, always current |

An installation predating the noun-verb surface rejects these commands with
`invalid choice: 'report'` and lists the old flat names instead. That is a stale
binary, not a bug — check with `ccworks --help`, and either upgrade
(`brew upgrade ccworks`) or use `./ccworks` from the checkout, which always
reflects your working tree.

The launcher owns only the checkout-only chores that cannot work from an
installed package — `setup`, `test-local`, `test-docker`,
`test-browser-smoke`, `test-reports-live`, `test-receipts-live`. Everything else
it passes straight through, so the two forms behave identically.

Run `ccworks` for the grouped reference, or `ccworks <group> <sub> --help` for a
command's flags.

### Retired command names

The earlier flat names (and the launcher's separate aliases for them) were
removed in favour of the single surface. They now exit `2` and name their
replacement:

```
$ ccworks query-old
ccworks: error: unrecognized command 'query-old'

  Did you mean:  ccworks report list --historical
```

| Retired | Replacement |
| :--- | :--- |
| `query` | `report list` |
| `query-old`, `list-old-reports` | `report list --historical` |
| `report-details` | `report show` |
| `create`, `create-report` | `report create` |
| `create-headed` | `report create --headed` |
| `update-report` | `report update` |
| `submit-report` | `report submit` |
| `delete`, `delete-report` | `report delete` |
| `delete-all-reports` | `report delete --all-drafts` |
| `reconcile` | `report reconcile` |
| `apply-json` | `report apply-json` |
| `update-transaction` | `txn update` |
| `allocations` | `txn allocations` |
| `add-allocation` | `txn allocate` |
| `attach-receipt` | `txn attach-receipt` |
| `list-cards` | `card list` |
| `card-details` | `card show` |
| `delete-all-receipts` | `receipt delete --all` |
| `add-delegate` | `delegate add` |
| `remove-delegate` | `delegate remove` |
| `login` | `session login` |
| `check-session` | `session status` |
| `api-test`, `run-live` | `api test` |

Flags were renamed to match: `--filter-view` is now `--view`,
`--receipt-path` is `--file`, `--reconcile-rules` is `--rules`, and
`--delegate-perms` is `--can`.

### Configure credentials

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

`ccworks` searches upward from the directory you invoke it in to find a
`.env`, so keep one per working folder (e.g. per fiscal-year records folder).

---

## 📂 Command Reference

### Dev-checkout tasks (`./ccworks` only)

| Command | Scope / Notes |
| :--- | :--- |
| `./ccworks setup` | Create `.venv`, install the package editable, install chromium. |
| `./ccworks test-local` | Run mock unit tests locally using `.venv`. |
| `./ccworks test-docker` | Run mock unit tests in Docker (offline, no credentials needed). |
| `./ccworks test-browser-smoke` | Playwright browser CRUD smoke tests against the local mock server. |
| `./ccworks test-reports-live` | Playwright reports CRUD smoke test against your real Concur account. |
| `./ccworks test-receipts-live` | Playwright receipts smoke test against your real Concur account. |

### Commands

| Group | Command | Scope / Notes |
| :--- | :--- | :--- |
| **report** | `report list [--historical] [--view F]` | List draft reports, or historical ones with `--historical`. |
| | `report show NAME [--deep] [--view F]` | Line-item details. `--deep` opens each transaction (slower, fully accurate). |
| | `report create [--name N] [--purpose P] [--comment C] [--headed]` | Create a draft report. |
| | `report update NAME [--name --purpose --comment --justification]` | Update header fields. |
| | `report reconcile NAME [--rules PATH] [--submit]` | Reconcile transactions; review-only unless `--submit`. |
| | `report submit NAME` | Submit for approval. |
| | `report delete NAME` / `report delete --all-drafts` | Delete one report, or every draft. |
| | `report apply-json PATH` | Apply an edited `report show` JSON back to Concur. |
| **txn** | `txn update NAME IDX... [--type --purpose --comment --justification]` | Update one or more transactions by 1-based index. |
| | `txn allocations NAME [--view F]` | List chartstring allocations (Dept, Fund, Program). |
| | `txn allocate NAME IDX --dept D --fund F [--prog P]` | Add a chartstring to a transaction. |
| | `txn attach-receipt NAME --merchant M --file PATH` | Attach a local receipt file to a transaction row. |
| **card** | `card list [--view F]` | List credit-card transactions. |
| | `card show MERCHANT_OR_ID [--view F]` | Details for one card transaction. |
| **receipt** | `receipt delete --all` | Delete every available receipt. `--all` is required. |
| **delegate** | `delegate add WHO [--can prepare submit approve]` | Add an expense delegate (default: `prepare`). |
| | `delegate remove WHO` | Remove an expense delegate. |
| **session** | `session login` | Headed browser for manual SSO; saves session state. |
| | `session status` | Check whether the saved session is still valid. |
| **api** | `api test` | Run the API client test suite (needs `.env` OAuth creds). |
| — | `nuke` | Delete ALL draft reports **and** all available receipts. |

Global flags work anywhere in the argument list: `-v/--verbose` (logs to
stderr), `--output {json,text}` (default `json`).

**stdout is data, stderr is diagnostics.** Query commands print JSON on stdout
while logs, spinners, and session warnings go to stderr, so `2>/dev/null` is
safe when piping to `jq`.

---

## 🔍 Detailed Usage Examples

### 1. Expense reports

Concur separates active drafts from older submitted/processed reports behind
dropdown filters. `--historical` switches to the latter, and `--view` picks the
filter.

```bash
# Current drafts (and available receipts)
ccworks report list

# Historical reports, default 'Last 90 Days'
ccworks report list --historical

# Historical reports under a specific filter
ccworks report list --historical --view "All Reports"

# Line items for one report; --deep opens each transaction
ccworks report show "Old Lodging Report 2025" --deep
```

`--view` applies only with `--historical`; passing it to a draft listing is a
usage error rather than a silently ignored flag.

```bash
# Create, retitle, then submit
ccworks report create --name "Q3 Travel" --purpose "INFORMS 2026"
ccworks report update "Q3 Travel" --justification "Conference travel"
ccworks report submit "Q3 Travel"

# Delete one report, or clear every draft
ccworks report delete "Q3 Travel"
ccworks report delete --all-drafts
```

### 2. Credit card transactions

```bash
ccworks card list
ccworks card list --view "All Purchasing Cards"
ccworks card show "Office Depot" --view "All Purchasing Cards"
```

### 3. Expense delegates

```bash
ccworks delegate add "John Doe" --can prepare submit
ccworks delegate add "jane@example.com" --can prepare approve
ccworks delegate remove "John Doe"
```

### 4. Month-end reconciliation

`report reconcile` is review-only by default, leaving the report in draft so you
can inspect it before submitting.

```bash
# Review-only
ccworks report reconcile "Reconciliation Report A"

# With explicit rules
ccworks report reconcile "Reconciliation Report A" --rules my_recon_rules.json

# Reconcile and submit in one step
ccworks report reconcile "Reconciliation Report A" --rules my_recon_rules.json --submit
```

Rules are a JSON object keyed by **merchant substring**, matched
case-insensitively; the first matching key wins, so order the most specific
first. Transactions matching no rule are skipped with a warning on stderr —
check those rather than assuming full coverage.

```json
{
  "United Airlines": {
    "expense_type": "Airfare",
    "business_purpose": "INFORMS 2026 travel",
    "comment": "Economy, booked in advance",
    "allocation_code": "(25605) ORF-Technical Support",
    "receipt_path": "/Users/you/receipts/united.pdf"
  }
}
```

All fields are optional; `receipt` is accepted as an alias for `receipt_path`.

### 5. Attach a receipt to a transaction

```bash
ccworks txn attach-receipt "Receipt Upload Report A" \
    --merchant "Uber" \
    --file receipts/uber_ride_receipt.pdf
```

### 6. Report and transaction fields (CRUD)

Transaction indices are **1-based**, and `txn update` accepts several at once —
batch them rather than looping the command, since each invocation drives a
browser.

```bash
# Header fields
ccworks report update "Transaction Report" --justification "Project Alpha research"
ccworks report update "Old Name" --name "New Name" --purpose "Updated purpose"

# Several transactions at once
ccworks txn update "Transaction Report" 1 2 3 --type "Software" --justification "Required for project X"

# A single transaction, distinct purpose and comment
ccworks txn update "Transaction Report" 1 --type "Ground Transportation" \
    --purpose "Meeting client" --comment "Uber ride"

# Clear a field
ccworks txn update "Transaction Report" 1 --comment ""
```

Round-trip a whole report through JSON:

```bash
ccworks report show "Statement Report 06/16 - 07/31" --deep --output json > report.json
# edit report.json
ccworks report apply-json report.json
```

#### Indices, and what `apply-json` will refuse

`index` is **1-based and dense** — position among the report's expense line
items, counting every one of them. The same number addresses the same expense in
`report show`, `txn update`, `txn allocate`, and `report apply-json`.

Before editing a row, `apply-json` checks that the row at that index actually
carries the amount (and vendor) of the expense you described. On a mismatch it
**refuses that row** and tells you to re-run `report show`, rather than writing
to a different expense:

```json
{ "index": 7, "success": false,
  "error": "Row does not match supplied expense (expected amount '$45.00' not present in row). Re-run `report show` to get current indices." }
```

That matters because a positional index is only valid while the report is
unchanged. Add, delete, or re-sort a line item in Concur after producing the
JSON and the index still resolves — to the wrong expense.

**Regenerate JSON captured before 0.3.0.** Earlier versions numbered rows by
their position among raw HTML matches, so the numbers were sparse and did not
line up with what the write paths counted.

#### Knowing the capture was complete

`report show` reports what it did *not* return, so `"success": true` no longer
hides omissions:

```json
"extraction": {
  "candidates_seen": 17,
  "expenses_returned": 15,
  "skipped_candidates": [
    { "candidate_position": 0,  "reason": "column header row" },
    { "candidate_position": 16, "reason": "too short to be an expense row" }
  ],
  "identical_line_items": [
    { "raw_text": "... Shipping & Freight, $23.28 ... ESHIPGLOBAL INC ...", "count": 2 }
  ],
  "deep_scan_failures": [],
  "complete": true
}
```

`identical_line_items` flags rows whose text matches exactly. These are **kept**
— two shipments booked the same day for the same amount are two expenses, and
earlier versions deduplicated by text and silently dropped the second, which
understated report totals. Check them against Concur if you did not expect them.

With `--deep`, `deep_scan_failures` lists rows whose detail pane would not open;
those keep their shallow fields, and `complete` is `false`.

### 7. Transaction allocations (chartstrings)

```bash
# Read current allocations
ccworks txn allocations "Project Alpha Report"

# Add a chartstring to transaction 1
ccworks txn allocate "Project Alpha Report" 1 \
    --dept "(25605) ORF-Technical Support" \
    --fund "(A0001) General Fund" \
    --prog "(P999) Research"
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

1. ~~Receipt-to-Report Attachment~~ *(Already implemented — see `txn attach-receipt` / `concur_attach_receipt`).*
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
   ./ccworks session login
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
