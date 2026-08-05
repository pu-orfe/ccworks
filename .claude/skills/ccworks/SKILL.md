---
name: ccworks
description: Drive SAP Concur through the ccworks CLI — list, inspect, reconcile, and submit expense reports; attach receipts; manage chartstring allocations, card transactions, and delegates. Use whenever the user asks about Concur expense reports, receipts, corporate card transactions, chartstrings/cost centers, expense delegates, or mentions ccworks.
---

# ccworks — SAP Concur automation

`ccworks` drives Concur via Playwright browser automation against a saved
session. Commands are grouped by resource: `ccworks <group> <subcommand>`.

## Invocation

`ccworks <group> <sub>` (installed) and `./ccworks <group> <sub>` (repo checkout)
take identical arguments — the launcher forwards verbatim. The launcher
additionally owns checkout-only chores that do not exist in the CLI: `setup`,
`test-local`, `test-docker`, `test-browser-smoke`, `test-reports-live`,
`test-receipts-live`.

**A stale install is the common trap.** The installed binary tracks whatever
version was released, not the working tree. If a command fails with
`invalid choice: 'report'` and the error lists flat names (`query`,
`report-details`, …), the binary on PATH predates this surface — do not rewrite
the command to the old names. Prefer `./ccworks` from the checkout, and tell the
user their install is stale.

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

Concur's JWT lasts about 60 minutes. Every command writes the refreshed cookies
back on a clean exit, so ordinary use keeps the session alive; a gap longer than
the JWT's life does not. `session status` reports `expires_in_minutes`, so check
it before starting a long run rather than discovering the expiry partway
through — and prefer one `report apply-json` pass over many single-row commands,
which is one cookie lifecycle instead of N.

`session login` always starts from an empty cookie jar, so it shows the Concur
login screen even when the saved session is healthy. That is not a symptom of a
broken session; it warns you what it is about to discard and lets you Ctrl-C.
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
- Transaction indices are **1-based and dense**, and mean the same row in
  `report show`, `txn update`, `txn allocate`, and `report apply-json`. Several
  at once: `ccworks txn update "Report A" 1 2 5 --justification "Conference travel"`
- Indices are positional, so they are only valid while the report is unchanged.
  Re-run `report show` before acting on numbers from an earlier capture; do not
  reuse indices from a JSON file written by ccworks before 0.3.0.

## Check `extraction` before trusting a capture

`report show` returns an `extraction` block; `"success": true` alone does not
mean the data is complete. Read it and tell the user what it says:

- `identical_line_items` — rows with byte-identical text. They are **kept** (two
  shipments the same day for the same amount are two expenses). Mention them; do
  not treat them as errors or dedupe them yourself.
- `skipped_candidates` — non-expense rows filtered out, with a reason each.
- `deep_scan_failures` (with `--deep`) — rows whose detail pane never opened;
  they carry shallow fields only.
- `complete` — false when anything above means the capture is partial.

Never sum amounts or reconcile from a capture where `complete` is false without
saying so.

An expense whose type is `Undefined` cannot be saved at all: Concur rejects the
save with "you must provide valid information for: Expense Type", so a business
purpose or comment written to that row will not persist until a valid type is
set. Set the type in the same `apply-json` row and both land together.

`report apply-json` verifies that the row at each index carries the expense's
amount and vendor, and **refuses** that row otherwise. If you see
"Row does not match supplied expense", the JSON is stale — re-run `report show`
and rebuild it. Do not try to guess a corrected index.

Two more write rules for `apply-json`:

- **Omit a field to leave it alone; pass `""` to clear it.** When changing one
  field, send only that field. Do not helpfully round-trip every field you read —
  and never fill a blank with `""` to "normalize" the payload, since that clears
  real data in Concur.
- **Rows in `extraction.deep_scan_failures` are withheld** and reported as
  `[SKIP]`. Their captured fields are empty only because the pane never opened.
  Do not reach for `--include-incomplete` to silence that; tell the user the row
  needs setting in the Concur UI.
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
`unallocate NAME IDX`, `attach-receipt NAME --merchant M --file PATH`

`--justification` sets business purpose *and* comment to the same text.

`txn allocate` **adds** an allocation; it never replaces one. A second
allocation splits the expense by percentage (two become 50/50), so allocating an
already-allocated expense does not supersede the old chartstring — it divides
the money between them, and both writes report success. To *replace* a
chartstring, `txn unallocate NAME IDX` first, then allocate. Clearing an
expense that has none is a reported no-op, not an error.

`txn allocations` lists chartstrings for the whole report from the print view.
Its `index` is deliberately `null` and its `section_number` is **not** the
shared row index — correlate on date + amount instead. Its chartstring column
shows only `dept-fund`; the program segment is written and verified but not
displayed there, so confirm a program by the `verified` array `txn allocate`
returns.

Editing any field on an **allocated** expense makes Concur ask "Update Other
Items?" before it will commit. ccworks answers "Do Not Update", saving the
expense-level change and leaving the allocations' own text alone. Allocate
last: doing it before the text edits means every later write pays for that
dialog.

**card** — `list [--view F]`, `show MERCHANT_OR_ID [--view F]` (default view
`"All Corporate and Personal Cards"`)

**receipt** — `delete --all` (the `--all` flag is required; there is no
per-receipt delete)

**delegate** — `add WHO [--can prepare submit approve]` (default `prepare`),
`remove WHO`

**session** — `login`, `status`

**api** — `test` (needs `.env` OAuth creds)

**nuke** — top-level; deletes all drafts and all receipts

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
