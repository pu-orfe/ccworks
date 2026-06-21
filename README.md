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
2. **Playwright Setup**: Playwright must be installed locally along with chromium binaries (handled automatically by `./run.sh setup`).

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
./run.sh setup
```

---

## 📂 Run Options

### Command Table

| Run Mode | Command | Scope / Notes |
| :--- | :--- | :--- |
| **Containerized Unit Tests** | `./run.sh test-docker` | Runs mock tests in Docker (Offline, credentials not needed). |
| **Local Unit Tests** | `./run.sh test-local` | Runs mock tests locally using `.venv`. |
| **Live API Test** | `./run.sh run-live` | Tests token retrieval, report listing, and report creation. |
| **Headed Browser Login** | `./run.sh browser-login` | Boots browser window for manual login, saves authentication state. |
| **Headless Browser Creation**| `./run.sh browser-create` | Programmatically logs in using saved state and creates a draft report. |
| **Visible Browser Creation** | `./run.sh browser-create-headed` | Performs browser creation visibly on screen (useful for debugging). |

---

## 🔒 Handling Multi-Factor Authentication (MFA) & SSO in Browser Mode

Modern enterprise security often requires MFA or SSO login screens that standard automation cannot programmatically bypass. This project handles this using a **Session State Preservation** strategy:

1. Run the manual session setup:
   ```bash
   ./run.sh browser-login
   ```
2. A headed Chromium window will open. Enter your email/password, solve SSO if prompted, and complete the MFA authentication.
3. Once logged in and redirected to the SAP Concur dashboard page, return to your terminal and press **ENTER**.
4. Your authenticated session token, cookies, and local storage are saved into `concur_session.json`.
5. Subsequent automated actions (`./run.sh browser-create`) will load this file and run headlessly without requiring login or prompt parameters.

---

## 📂 Project Directory Structure

```
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Service orchestration for testing
├── requirements.txt        # Third-party Python dependencies
├── .env.example            # Environment variables configuration template
├── run.sh                  # Zsh shell helper script
├── src/
│   ├── __init__.py
│   ├── client.py           # Core Concur API Client Wrapper
│   ├── browser_client.py   # Playwright Browser Automation Client
│   └── cli.py              # Command-Line Access Tester Script
└── tests/
    ├── __init__.py
    └── test_client.py      # Unit tests using requests mocks
```
