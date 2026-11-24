"""Shared lightweight YAML loader (uses PyYAML if installed, else clean stdlib parser)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_scalar(raw: str) -> Any:
    val = raw.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        return val


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Load simple flat/list YAML configuration without external dependencies."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except ImportError:
        pass

    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_key is not None:
            if not isinstance(result.get(current_key), list):
                result[current_key] = []
            result[current_key].append(_parse_scalar(stripped[2:]))
            continue
        if ":" in line:
            key, rest = line.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                result[key] = []
                current_key = key
            else:
                result[key] = _parse_scalar(rest)
                current_key = key
    return result
