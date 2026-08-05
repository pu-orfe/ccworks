# Allocation performance — work plan

Allocation is **91% of the cost of a reconciliation pass** and is the reason a
teardown plus a re-apply cannot fit inside one Concur session. This is the plan
for reducing it, and the constraints any change has to respect.

Nothing here is implemented. It is written down so the next person (or the next
session) starts from the measurements rather than re-deriving them.

## Where the time goes

Measured against a live 16-row statement, per transaction:

| Phase | Cost | Share |
| :--- | ---: | ---: |
| Business purpose, comment, receipt upload, save | ~10s | 9% |
| Allocation — clear, then add | ~103s | 91% |
| **Total** | **~113s** | |

A 16-row statement is therefore ~30 min with allocations and ~3 min without.
The allocation-only re-run measured **103s per row**, consistently, across 15
consecutive rows (11:44:27 → 11:46:10 → 11:47:53 → 11:49:35).

Inside that 103s, the dominant cost is **two full report reloads**:

- `_clear_allocations_on_page` verifies by calling `_verify_allocations_cleared`,
  which navigates to `/nui/expense`, waits for the dashboard, re-opens the
  report, and re-opens the allocations modal.
- `_add_allocation_on_page` then verifies by calling `_verify_allocation`, which
  does the same again.

Each reload is a dashboard wait plus a report open plus a modal open. Two of
them, back to back, per row.

## Why it is built that way

The verification is not decoration. It exists because of a specific defect:
`txn allocate` **adds** rather than replaces, so allocating an already-allocated
expense splits it by percentage — a live row ended up 50/50 across two
chartstrings while *both* writes reported success. The clear step's verification
is what guarantees the old chartstring is actually gone before the new one is
added.

Any change here is changing verification semantics on a financial write. That is
the bar to clear.

## Proposed work, in order

### 1. Collapse the intermediate verification (largest win)

When clear and add run **back to back in the same pass**, the intermediate
verification is arguably redundant: the final verification confirms the end
state, and the end state is what matters. Verify once, after the add, asserting:

- exactly **one** allocation row is present, and
- it carries every requested value (dept, fund, and program when given).

That assertion is strictly stronger than what is checked today, because today's
final check does not assert the *count*. A leftover allocation from a failed
clear would currently pass the add's verification (the new chartstring is
present) and be caught only by the clear's own check.

Expected: ~103s → ~55s per row; a 16-row pass from ~30 min to ~16 min.

Keep `remove_transaction_allocations` (the standalone `txn unallocate`)
verifying independently — there is no subsequent add to confirm the end state.

### 2. Do not re-open the modal between clear and add

`_clear_allocations_on_page` and `_add_allocation_on_page` each call
`_open_allocations_modal`. Run back to back, the modal is already open after the
clear. Detect that and skip the second open.

Expected: a few seconds per row. Small, but it also removes one opportunity for
the post-save re-render race that broke every row of the first one-shot.

### 3. Reduce redundant row collection

`_collect_expense_rows` runs 3–4 times per row: once in the write loop, once per
retry attempt in `_open_allocations_modal`, and again inside each verification.
Each is a full DOM scan (18 candidates filtered to 16). Cache within a row where
the page has demonstrably not navigated.

Expected: small, but it compounds across 16 rows.

### 4. Consider a per-report allocation pass

`apply-json` currently reloads the report before every row (necessary — a stale
viewer otherwise attributes one expense's receipt to the next). If allocations
were applied in a second sweep after all the field writes, the reload could be
amortised. This is speculative and should only be attempted after 1–3 are
measured.

## Constraints

- **Verification cannot be weakened.** The end state must still be asserted
  against a fresh read of what Concur holds, not the modal left on screen. The
  measurable requirement is that the deep verification after a full pass still
  reports `complete: true`, `failures: 0`.
- **A partial failure must be reported.** If the clear succeeds and the add
  fails, the row must fail loudly — it is now *unallocated*, which is worse than
  when it started.
- **The mock cannot validate the gain.** Its timings are unrelated to Concur's.
  Correctness is testable in the suite; the speedup is only measurable live.

## How to verify a change here

1. Suite green (`unittest discover -s tests`), including
   `tests/test_allocations_crud.py`.
2. A live before/after on one row, comparing the `Updating Row N` timestamps in
   a `-v` log.
3. A full pass on a 16-row statement, then `report show --deep`, asserting
   `complete: true`, `failures: 0`, and the expected chartstring on every row.
4. `scratchpad/timing.py`-style parsing of the verbose log to produce the new
   per-row median, and update the figures in `README.md` and the skill doc.

## Related

- Session lifetime (#3). The Concur JWT is ~60 minutes from login and is **not**
  extended by use — measured: across a 24-minute run the session file's mtime
  advanced while the JWT expiry did not move. Halving allocation cost is what
  would make a teardown *and* a re-apply fit one session, so this work is the
  practical mitigation for that issue.
