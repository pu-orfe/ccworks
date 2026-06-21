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
    echo "  run-live              Run live API integration test (requires configuring .env)"
    echo "  browser-login         Launch headed browser for manual Concur authentication and save session state"
    echo "  browser-query         Run Playwright query to list current reports and receipts (requires session)"
    echo "  browser-create        Run Playwright automation to create a draft report headlessly"
    echo "  browser-create-headed Run Playwright automation to create a draft report visibly (headed)"
    echo "  browser-delete \"Name\"  Run Playwright to delete a specific report by name"
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
        python3 src/cli.py --browser-create
        ;;
    browser-create-headed)
        echo "=== Running headed browser report creation ==="
        ensure_venv
        python3 src/cli.py --browser-create-headed
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
    *)
        usage
        ;;
esac
