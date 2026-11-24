"""Reference patch A* for task_002_ledger_reconcile."""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path


def apply_patch(workspace_dir: Path) -> dict[str, int]:
    world_dir = workspace_dir / "world"
    sql_path = world_dir / "ledger.db.sql"
    bak_path = world_dir / "ledger.db.sql.bak"
    db_path = world_dir / "reconciled.db"
    report_path = world_dir / "reconcile_report.json"

    sql_script = sql_path.read_text(encoding="utf-8")
    shutil.copy2(sql_path, bak_path)

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.executescript(sql_script)
    conn.execute(
        "UPDATE invoices SET total_cents = amount_cents + tax_cents, status = 'RECONCILED' WHERE invoice_id = 'INV-2026-042'"
    )
    conn.commit()
    total_sum = int(conn.execute("SELECT SUM(total_cents) FROM invoices").fetchone()[0])
    conn.close()

    report_path.write_text(
        json.dumps({"reconciled_total_cents": total_sum}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"reconciled_total_cents={total_sum}")
    return {"reconciled_total_cents": total_sum}


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    apply_patch(ws)
