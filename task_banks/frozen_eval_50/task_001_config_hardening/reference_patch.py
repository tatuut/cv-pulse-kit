"""Reference patch A* for task_001_config_hardening."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


def apply_patch(workspace_dir: Path) -> dict[str, str]:
    world_dir = workspace_dir / "world"
    config_path = world_dir / "app_config.json"
    backup_path = world_dir / "app_config.json.bak"

    raw_bytes = config_path.read_bytes()
    shutil.copy2(config_path, backup_path)

    cfg = json.loads(raw_bytes.decode("utf-8"))
    cfg["auth_required"] = True
    cfg["rate_limit_rpm"] = 120
    cfg["debug_mode"] = False
    cfg["allowed_origins"] = ["https://app.cv-pulse.dev"]
    cfg["backup_policy"] = "daily-snapshot"

    new_text = json.dumps(cfg, indent=2) + "\n"
    config_path.write_text(new_text, encoding="utf-8")
    digest_prefix = hashlib.sha256(new_text.encode("utf-8")).hexdigest()[:12]
    print(f"config_sha256_prefix={digest_prefix}")
    return {"config_sha256_prefix": digest_prefix}


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    apply_patch(ws)
