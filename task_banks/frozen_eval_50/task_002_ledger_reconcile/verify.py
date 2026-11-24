"""Deterministic verifier V(s_final) -> {0, 1} for task_002_ledger_reconcile."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def verify(workspace_dir: Path) -> int:
    world_dir = workspace_dir / "world"
    db_path = world_dir / "reconciled.db"
    bak_path = world_dir / "ledger.db.sql.bak"
    report_path = world_dir / "reconcile_report.json"

    if not db_path.is_file() or not bak_path.is_file() or not report_path.is_file():
        return 0

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        inv = cur.execute(
            "SELECT amount_cents, tax_cents, total_cents, status FROM invoices WHERE invoice_id='INV-2026-042'"
        ).fetchone()
        total_sum = cur.execute("SELECT SUM(total_cents) FROM invoices").fetchone()[0]
        lock = cur.execute(
            "SELECT flag_value FROM system_flags WHERE flag_name='audit_lock'"
        ).fetchone()
        conn.close()
    except (OSError, json.JSONDecodeError, sqlite3.Error):
        return 0

    if not inv or not lock:
        return 0

    amount, tax, total, status = inv
    checks = [
        total == amount + tax,
        total == 27500,
        status == "RECONCILED",
        total_sum == 82500,
        lock[0] == "ENABLED",
        report.get("reconciled_total_cents") == 82500,
    ]
    return 1 if all(checks) else 0


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    score = verify(ws)
    print(score)
    sys.exit(0 if score == 1 else 1)
