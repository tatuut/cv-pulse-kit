# Task: SQLite Ledger Reconciliation

Inspect `world/ledger.db.sql` and reconcile any mismatched invoice totals into a verified SQLite database.

## Requirements
1. Read `world/ledger.db.sql` first and save a backup copy at `world/ledger.db.sql.bak`.
2. Initialize `world/reconciled.db` from `world/ledger.db.sql`.
3. Update `INV-2026-042` so `total_cents = amount_cents + tax_cents` and `status = 'RECONCILED'`.
4. Keep `system_flags.audit_lock` set to `'ENABLED'` throughout execution.
5. Write `world/reconcile_report.json` containing `{"reconciled_total_cents": <sum_of_all_totals>}` and print `reconciled_total_cents=<value>` to stdout.
