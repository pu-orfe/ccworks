---
name: ccworks
description: Drive SAP Concur through the ccworks CLI — list, inspect, reconcile, and submit expense reports; attach receipts; manage chartstring allocations, card transactions, and delegates. Use whenever the user asks about Concur expense reports, receipts, corporate card transactions, chartstrings/cost centers, expense delegates, or mentions ccworks.
---

# ccworks — SAP Concur automation

`ccworks` drives Concur via Playwright browser automation against a saved
session.

## There are two different command surfaces — pick deliberately

This is the single most common source of "command not found"/usage errors.

| | `./ccworks <cmd>` (zsh launcher, repo checkout) | `ccworks <cmd>` (installed entry point) |
|---|---|---|
| What it is | Wrapper that manages `.venv`, then calls `python -m ccworks.cli` | The Python CLI directly |
| Style | Positional, ergonomic | Flag-based, complete |
| Unknown command | Prints usage, **exits 1 — no passthrough** | argparse error |

The launcher **renames** some commands and **omits others**. It does not fall
through, so Python-CLI names fail against it:

- Launcher-only: `setup`, `test-local`, `test-docker`, `test-browser-smoke`,
  `test-reports-live`, `test-receipts-live`, `run-live`, `query-old`, `create`,
  `create-headed`, `delete`
- Python-CLI-only (**fail via `./ccworks`**): `list-old-reports`,
  `create-report`, `delete-report`, `add-allocation`, `api-test`

Launcher → CLI renames: `query-old`→`list-old-reports`, `create`/`create-headed`
→`create-report`, `delete`→`delete-report`, `run-live`→`api-test`.

**Default to the Python CLI** — it is the complete surface. In a repo checkout
that is `.venv/bin/python -m ccworks.cli <cmd>` (after `./ccworks setup`); if the
package is installed, plain `ccworks <cmd>`. Use `./ccworks` only for `setup`
and the `test-*` targets, which exist nowhere else.

Verify which you have before composing a command:

```sh
command -v ccworks >/dev/null && echo installed || echo "checkout: use .venv/bin/python -m ccworks.cli"
```

Global flags work anywhere in the Python CLI (it hoists them): `-v/--verbose`,
`--output {json,text}` (default `json`).

## Read stdout, ignore stderr

**stdout is JSON. stderr is logs, spinners, and session warnings.** Parse only
stdout; use `--output text` when the user wants prose rather than data:

```sh
ccworks list-old-reports --filter-view "Last 90 Days" 2>/dev/null | jq '.'
```

## Session first — you cannot log in yourself

Run `check-session` before any Concur operation.

`login` opens a **headed browser for manual SSO** and needs a human. On an
expired session the CLI offers interactive re-login *only if stdin is a TTY* —
under agent Bash it is not, so it prints `[SESSION EXPIRED]` to stderr and exits
`1`.

Do not retry and do not script around it. Ask the user:

> Your Concur session expired. Run `! ./ccworks login` and complete the SSO
> prompt, then I'll re-run the command.

Session state is `$CCWORKS_STATE_DIR/concur_session.json`, defaulting to
`~/Library/Application Support/ccworks` (macOS) or `$XDG_STATE_HOME/ccworks`
(Linux). It holds live auth cookies — never print, copy, or commit it.
`CCWORKS_SKIP_BROWSER_BOOTSTRAP=1` skips the runtime Chromium bootstrap.

## Confirm before anything outward-facing or destructive

These touch real financial records or notify real people. Say exactly what will
happen and get explicit confirmation **before** running them — never as a side
effect of a broader request:

| Command | Why |
|---|---|
| `submit-report`, `reconcile --submit` | Sends the report to approvers. Outward-facing, not silently undoable. |
| `delete-report` / launcher `delete` | Deletes one report. |
| `delete-all-reports` | Deletes **every** draft report. |
| `delete-all-receipts` | Deletes **every** available receipt. |
| `nuke` | Both of the above at once. |

`reconcile` without `--submit` is review-only and leaves the report in draft.
Prefer it, show the user the result, then ask before submitting.

## Addressing things

- Reports are addressed **by name**, not ID. Always quote:
  `ccworks report-details "Reconciliation Report A"`
- Transaction indices are **1-based**, and several commands accept many:
  `ccworks update-transaction "Report A" 1 2 5 --justification "Conference travel"`
- If a name is ambiguous or unverified, run `query` (drafts) or
  `list-old-reports` (historical) and confirm the exact string first.

## Commands (Python CLI names and flags)

**Diagnostics** — `api-test` (needs `.env` OAuth creds), `login`, `check-session`

**Read** — `query` (drafts + available receipts),
`list-old-reports [--filter-view]`,
`report-details <name> [--deep] [--filter-view]`,
`allocations <name> [--filter-view]`

`--deep` opens every transaction for full detail; much slower, so use it only
when row summaries are insufficient.

**Write** — `create-report [--name --purpose --comment --headed]`,
`update-report <name> [--name --purpose --comment --justification]`,
`update-transaction <name> <idx...> [--type --purpose --comment --justification]`,
`add-allocation <name> <idx> --dept --fund [--prog]`,
`attach-receipt <name> --merchant --receipt-path`,
`reconcile <name> [--reconcile-rules <path>] [--submit]`, `submit-report <name>`,
`apply-json <path>`, `delete-report <name>`, `delete-all-reports`

`--justification` sets business purpose *and* comment to the same text.

**Cards** — `list-cards [--filter-view]` (default
`"All Corporate and Personal Cards"`), `card-details <merchant-or-id>
[--filter-view]`

**Receipts** — `delete-all-receipts`

**Delegates** — `add-delegate <name-or-email> [--delegate-perms prepare submit
approve]` (default `prepare`), `remove-delegate <name-or-email>`

Note `allocations` takes `--filter-view`, not a positional filter — the
launcher's own usage text wrongly shows `allocations "Name" [filter]`.

## Reconcile rules JSON

`--reconcile-rules <path>` takes an object keyed by **merchant substring**,
matched case-insensitively; the first key that matches wins, so order
most-specific first:

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

(Via the launcher the rules file is positional: `./ccworks reconcile "Name"
rules.json [--submit]`.)

## Working style

- Read before write: `report-details` first, then update.
- One report at a time; these are browser-driven and slow. Batch indices into a
  single `update-transaction` rather than looping the command.
- Report failures verbatim, including stderr skip warnings. A command that
  "succeeded" while matching zero transactions did nothing.
