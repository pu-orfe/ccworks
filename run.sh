#!/usr/bin/env zsh

# Helper script for running tests, CLI, and browser automation on macOS

set -euo pipefail

# Print usage helper
usage() {
    echo "Usage: ./run.sh [command]"
    echo "Commands:"
    echo "  setup                 Set up local virtual environment, install requirements, and Playwright browsers"
    echo "  test-local            Run mock unit tests locally on the host"
    echo "  test-docker           Build and run mock unit tests inside Docker container"
    echo "  test-browser-smoke    Run Playwright browser CRUD smoke tests (using local mock server)"
    echo "  test-reports-live     Run Playwright reports CRUD smoke test on your real Concur account"
    echo "  test-receipts-live    Run Playwright receipts list/delete smoke test on your real Concur account"
    echo "  run-live              Run live API integration test (requires configuring .env)"
    echo "  browser-login         Launch headed browser for manual Concur authentication and save session state"
    echo "  browser-query         Run Playwright query to list current reports and receipts (requires session)"
    echo "  browser-create        Run Playwright automation to create a draft report headlessly"
    echo "  browser-create-headed Run Playwright automation to create a draft report visibly (headed)"
    echo "  browser-delete \"Name\"  Run Playwright to delete a specific report by name"
    echo "  browser-delete-all-reports Run Playwright to delete all draft expense reports"
    echo "  browser-delete-all-receipts Run Playwright to delete all available receipts"
    echo "  browser-nuke          Run Playwright to delete all reports AND all receipts"
    echo "  browser-query-old [filter] Query and list historical/old expense reports (default: 'Last 90 Days')"
    echo "  browser-report-details \"Name\" [filter] Get detailed view of an expense report by name"
    echo "  browser-list-cards [filter] Query and list credit card transactions (default: 'All Corporate and Personal Cards')"
    echo "  browser-card-details \"Merchant/ID\" [filter] Get detailed view of a card transaction by merchant or ID"
    echo "  browser-add-delegate \"Name or Email\" [perms...] Add a new expense delegate (permissions: prepare, submit, approve)"
    echo "  browser-remove-delegate \"Name or Email\" Remove an expense delegate"
    echo "  browser-reconcile \"Name\" [rules.json] [--submit] Reconcile expense report transactions (default: review-only, --submit to submit)"
    echo "  browser-attach-receipt \"Name\" \"Merchant\" \"receipt.pdf\" Attach a local receipt file to a report transaction"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

CMD=$1

# Helper to activate local virtual env if it exists, or create it
ensure_venv() {
    if [ ! -d ".venv" ]; then
        echo "Virtual environment not found. Setting it up first..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        playwright install chromium
    else
        source .venv/bin/activate
    fi
}

case "$CMD" in
    setup)
        echo "=== Setting up local Python Virtual Environment ==="
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "=== Installing Playwright browser binaries ==="
        playwright install chromium
        echo "Setup complete! Activate using: source .venv/bin/activate"
        ;;
    test-local)
        echo "=== Running local unit tests ==="
        ensure_venv
        python3 -m unittest discover -s tests
        ;;
    test-docker)
        echo "=== Running containerized unit tests via Docker Compose ==="
        docker-compose build unit-tests
        docker-compose run --rm unit-tests
        ;;
    test-browser-smoke)
        echo "=== Running Playwright Browser CRUD Smoke Tests ==="
        ensure_venv
        python3 tests/test_browser_smoke.py
        ;;
    test-reports-live)
        echo "=== Running Live Concur Reports Smoke Test ==="
        ensure_venv
        python3 tests/smoke_test_reports.py
        ;;
    test-receipts-live)
        echo "=== Running Live Concur Receipts Smoke Test ==="
        ensure_venv
        python3 tests/smoke_test_receipts.py "${@:2}"
        ;;
    run-live)
        echo "=== Running live integration test ==="
        if [ ! -f ".env" ]; then
            echo "[ERROR] .env file not found. Please copy .env.example to .env and populate it with credentials."
            exit 1
        fi
        ensure_venv
        python3 src/cli.py --api
        ;;
    browser-login)
        echo "=== Launching browser login automation ==="
        ensure_venv
        python3 src/cli.py --browser-login
        ;;
    browser-query)
        echo "=== Querying reports and receipts via browser ==="
        ensure_venv
        python3 src/cli.py --browser-query
        ;;
    browser-create)
        echo "=== Running headless browser report creation ==="
        ensure_venv
        ARGS=()
        if [ $# -ge 2 ]; then
            ARGS+=("--name" "$2")
        fi
        if [ $# -ge 3 ]; then
            ARGS+=("--purpose" "$3")
        fi
        if [ $# -ge 4 ]; then
            ARGS+=("--comment" "$4")
        fi
        python3 src/cli.py --browser-create "${ARGS[@]}"
        ;;
    browser-create-headed)
        echo "=== Running headed browser report creation ==="
        ensure_venv
        ARGS=()
        if [ $# -ge 2 ]; then
            ARGS+=("--name" "$2")
        fi
        if [ $# -ge 3 ]; then
            ARGS+=("--purpose" "$3")
        fi
        if [ $# -ge 4 ]; then
            ARGS+=("--comment" "$4")
        fi
        python3 src/cli.py --browser-create-headed "${ARGS[@]}"
        ;;
    browser-delete)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the report name to delete."
            echo "Usage: ./run.sh browser-delete \"Report Name\""
            exit 1
        fi
        echo "=== Deleting report via browser ==="
        ensure_venv
        python3 src/cli.py --browser-delete "$2"
        ;;
    browser-delete-all-reports)
        ensure_venv
        python3 src/cli.py --browser-delete-all-reports
        ;;
    browser-delete-all-receipts)
        ensure_venv
        python3 src/cli.py --browser-delete-all-receipts
        ;;
    browser-nuke)
        ensure_venv
        python3 src/cli.py --browser-delete-all
        ;;
    browser-query-old)
        ensure_venv
        FILTER="${2:-Last 90 Days}"
        python3 src/cli.py --browser-query-old --filter-view "$FILTER"
        ;;
    browser-report-details)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the report name."
            echo "Usage: ./run.sh browser-report-details \"Report Name\" [filter]"
            exit 1
        fi
        ensure_venv
        FILTER="${3:-Last 90 Days}"
        python3 src/cli.py --browser-report-details "$2" --filter-view "$FILTER"
        ;;
    browser-list-cards)
        ensure_venv
        FILTER="${2:-All Corporate and Personal Cards}"
        python3 src/cli.py --browser-list-cards --filter-view "$FILTER"
        ;;
    browser-card-details)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the card transaction merchant name or transaction ID."
            echo "Usage: ./run.sh browser-card-details \"Merchant or ID\" [filter]"
            exit 1
        fi
        ensure_venv
        FILTER="${3:-All Corporate and Personal Cards}"
        python3 src/cli.py --browser-card-details "$2" --filter-view "$FILTER"
        ;;
    browser-add-delegate)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the delegate name/email."
            echo "Usage: ./run.sh browser-add-delegate \"Name or Email\" [permission1 permission2 ...]"
            exit 1
        fi
        ensure_venv
        NAME="$2"
        # Gather all permissions (arguments starting from $3)
        shift 2
        PERMS=("$@")
        if [ ${#PERMS[@]} -eq 0 ]; then
            PERMS=("prepare")
        fi
        python3 src/cli.py --browser-add-delegate "$NAME" --delegate-perms "${PERMS[@]}"
        ;;
    browser-remove-delegate)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the delegate name/email."
            echo "Usage: ./run.sh browser-remove-delegate \"Name or Email\""
            exit 1
        fi
        ensure_venv
        python3 src/cli.py --browser-remove-delegate "$2"
        ;;
    browser-reconcile)
        if [ $# -lt 2 ]; then
            echo "Error: Please specify the report name to reconcile."
            echo "Usage: ./run.sh browser-reconcile \"Report Name\" [rules.json] [--submit]"
            exit 1
        fi
        ensure_venv
        REPORT_NAME="$2"
        RULES_FILE=""
        SUBMIT_FLAG=""
        shift 2
        while [ $# -gt 0 ]; do
            if [ "$1" = "--submit" ]; then
                SUBMIT_FLAG="--submit"
            else
                RULES_FILE="$1"
            fi
            shift
        done
        if [ -n "$RULES_FILE" ] && [ -n "$SUBMIT_FLAG" ]; then
            python3 src/cli.py --browser-reconcile "$REPORT_NAME" --reconcile-rules "$RULES_FILE" --submit
        elif [ -n "$RULES_FILE" ]; then
            python3 src/cli.py --browser-reconcile "$REPORT_NAME" --reconcile-rules "$RULES_FILE"
        elif [ -n "$SUBMIT_FLAG" ]; then
            python3 src/cli.py --browser-reconcile "$REPORT_NAME" --submit
        else
            python3 src/cli.py --browser-reconcile "$REPORT_NAME"
        fi
        ;;
    browser-attach-receipt)
        if [ $# -lt 4 ]; then
            echo "Error: Please specify report name, merchant name, and local receipt file path."
            echo "Usage: ./run.sh browser-attach-receipt \"Report Name\" \"Merchant Name\" \"receipt.pdf\""
            exit 1
        fi
        ensure_venv
        python3 src/cli.py --browser-attach-receipt "$2" --merchant "$3" --receipt-path "$4"
        ;;
    *)
        usage
        ;;
esac
