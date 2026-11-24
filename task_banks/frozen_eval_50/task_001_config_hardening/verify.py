"""Deterministic verifier V(s_final) -> {0, 1} for task_001_config_hardening."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def verify(workspace_dir: Path) -> int:
    world_dir = workspace_dir / "world"
    config_path = world_dir / "app_config.json"
    backup_path = world_dir / "app_config.json.bak"

    if not config_path.is_file() or not backup_path.is_file():
        return 0

    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        bak = json.loads(backup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0

    checks = [
        cfg.get("service_name") == "cv-pulse-gateway",
        cfg.get("auth_required") is True,
        cfg.get("rate_limit_rpm") == 120,
        cfg.get("debug_mode") is False,
        cfg.get("allowed_origins") == ["https://app.cv-pulse.dev"],
        cfg.get("backup_policy") == "daily-snapshot",
        bak.get("auth_required") is False,
        bak.get("debug_mode") is True,
    ]
    return 1 if all(checks) else 0


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    score = verify(ws)
    print(score)
    sys.exit(0 if score == 1 else 1)
