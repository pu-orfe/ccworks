---
name: ccworks
description: Drive SAP Concur through the ccworks CLI — list, inspect, reconcile, and submit expense reports; attach receipts; manage chartstring allocations, card transactions, and delegates. Use whenever the user asks about Concur expense reports, receipts, corporate card transactions, chartstrings/cost centers, expense delegates, or mentions ccworks.
---

# ccworks — SAP Concur automation

`ccworks` drives Concur via Playwright browser automation against a saved
session. Commands are grouped by resource: `ccworks <group> <subcommand>`.

## Invocation

`ccworks <group> <sub>` (installed) and `./ccworks <group> <sub>` (repo checkout)
are interchangeable — the launcher forwards arguments verbatim. The launcher
additionally owns checkout-only chores that do not exist in the CLI: `setup`,
`test-local`, `test-docker`, `test-browser-smoke`, `test-reports-live`,
`test-receipts-live`.

From a checkout without the package on PATH, use `.venv/bin/python -m
ccworks.cli` (or just `./ccworks`).

Global flags work anywhere in the argument list: `-v/--verbose`,
`--output {json,text}` (default `json`).

## Read stdout, ignore stderr

**stdout is JSON. stderr is logs, spinners, and session warnings.** Parse only
stdout; use `--output text` when the user wants prose rather than data:

```sh
ccworks report list --historical --view "Last 90 Days" 2>/dev/null | jq '.'
```

## Session first — you cannot log in yourself

Run `ccworks session status` before any Concur operation.

`session login` opens a **headed browser for manual SSO** and needs a human. On
an expired session the CLI offers interactive re-login *only if stdin is a TTY* —
under agent Bash it is not, so it prints `[SESSION EXPIRED]` to stderr and exits
`1`.

Do not retry and do not script around it. Ask the user:

> Your Concur session expired. Run `! ./ccworks session login` and complete the
> SSO prompt, then I'll re-run the command.

Session state is `$CCWORKS_STATE_DIR/concur_session.json`, defaulting to
`~/Library/Application Support/ccworks` (macOS) or `$XDG_STATE_HOME/ccworks`
(Linux). It holds live auth cookies — never print, copy, or commit it.
`CCWORKS_SKIP_BROWSER_BOOTSTRAP=1` skips the runtime Chromium bootstrap.

## Confirm before anything outward-facing or destructive

These touch real financial records or notify real people. Say exactly what will
happen and get explicit confirmation **before** running them — never as a side
effect of a broader request. Never run one as a smoke test; use `--help` to
check that a command parses.

| Command | Why |
|---|---|
| `report submit`, `report reconcile --submit` | Sends the report to approvers. Outward-facing, not silently undoable. |
| `report delete NAME` | Deletes one report. |
| `report delete --all-drafts` | Deletes **every** draft report. |
| `receipt delete --all` | Deletes **every** available receipt. |
| `nuke` | Both of the above at once. |

`report reconcile` without `--submit` is review-only and leaves the report in
draft. Prefer it, show the user the result, then ask before submitting.

## Addressing things

- Reports are addressed **by name**, not ID. Always quote:
  `ccworks report show "Reconciliation Report A"`
- Transaction indices are **1-based**, and `txn update` accepts several:
  `ccworks txn update "Report A" 1 2 5 --justification "Conference travel"`
- If a name is ambiguous or unverified, run `report list` (drafts) or
  `report list --historical` and confirm the exact string first.

## Commands

**report** — `list [--historical] [--view F]`, `show NAME [--deep] [--view F]`,
`create [--name --purpose --comment --headed]`,
`update NAME [--name --purpose --comment --justification]`,
`reconcile NAME [--rules PATH] [--submit]`, `submit NAME`,
`delete NAME | --all-drafts`, `apply-json PATH`

`--deep` opens every transaction for full detail; much slower, so use it only
when row summaries are insufficient. `--view` is valid only with `--historical`
— passing it to a draft listing is a usage error, not a silent no-op.

**txn** — `update NAME IDX... [--type --purpose --comment --justification]`,
`allocations NAME [--view F]`, `allocate NAME IDX --dept D --fund F [--prog P]`,
`attach-receipt NAME --merchant M --file PATH`

`--justification` sets business purpose *and* comment to the same text.

**card** — `list [--view F]`, `show MERCHANT_OR_ID [--view F]` (default view
`"All Corporate and Personal Cards"`)

**receipt** — `delete --all` (the `--all` flag is required; there is no
per-receipt delete)

**delegate** — `add WHO [--can prepare submit approve]` (default `prepare`),
`remove WHO`

**session** — `login`, `status`

**api** — `test` (needs `.env` OAuth creds)

**nuke** — top-level; deletes all drafts and all receipts

## Retired names

The old flat commands were removed. They exit `2` and name their replacement, so
if you see `unrecognized command`, read the suggestion rather than guessing:
`query`→`report list`, `query-old`/`list-old-reports`→`report list --historical`,
`report-details`→`report show`, `create`/`create-report`→`report create`,
`delete`/`delete-report`→`report delete`, `check-session`→`session status`,
`login`→`session login`, `add-allocation`→`txn allocate`,
`list-cards`→`card list`, `card-details`→`card show`, `api-test`→`api test`.

Flags moved too: `--filter-view`→`--view`, `--receipt-path`→`--file`,
`--reconcile-rules`→`--rules`, `--delegate-perms`→`--can`.

## Reconcile rules JSON

`--rules PATH` takes an object keyed by **merchant substring**, matched
case-insensitively; the first key that matches wins, so order most-specific
first:

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

All fields optional; `receipt` is an accepted alias for `receipt_path`.
Unmatched transactions are **skipped with a warning on stderr** — after
reconciling, report which rows were skipped instead of implying full coverage.

## Working style

- Read before write: `report show` first, then update.
- One report at a time; these are browser-driven and slow. Batch indices into a
  single `txn update` rather than looping the command.
- Report failures verbatim, including stderr skip warnings. A command that
  "succeeded" while matching zero transactions did nothing.
