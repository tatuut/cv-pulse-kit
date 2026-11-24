"""TSAI isolated sandbox runner enforcing the Wall of Ignorance and recording traces."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from .tgai_ebpf_tea import audit_trajectory, compute_exo_brevity, merge_tea_policy
from .yaml_util import load_simple_yaml


class SandboxWorldHandle:
    """Controlled interface exposed to TSAI inside the isolated sandbox."""

    def __init__(self, workspace_dir: Path, forbidden_paths: set[str]) -> None:
        self._ws = workspace_dir
        self._forbidden = forbidden_paths
        self.syscalls: list[dict[str, Any]] = []
        self.midrun_states: list[str] = []
        self.stdout_logs: list[str] = []

    def _guard_path(self, rel_path: str, op: str) -> Path:
        norm = rel_path.replace("\\", "/").lstrip("./")
        if any(fp in norm for fp in self._forbidden) or ".." in norm.split("/"):
            self.syscalls.append({"op": op, "path": norm, "result": "EACCES"})
            raise PermissionError(f"AppArmor EACCES: {norm}")
        return self._ws / norm

    def read_text(self, rel_path: str) -> str:
        target = self._guard_path(rel_path, "openat")
        self.syscalls.append({"op": "read", "path": rel_path.replace("\\", "/"), "result": "OK"})
        return target.read_text(encoding="utf-8")

    def write_text(self, rel_path: str, content: str) -> None:
        target = self._guard_path(rel_path, "write")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.syscalls.append({"op": "write", "path": rel_path.replace("\\", "/"), "result": "OK"})

    def record_midrun_state(self, state_marker: str) -> None:
        self.midrun_states.append(state_marker)

    def emit_stdout(self, line: str) -> None:
        self.syscalls.append({"op": "execve", "path": "stdout", "result": "OK"})
        self.stdout_logs.append(line)

    def workspace_path(self) -> Path:
        return self._ws


def run_episode(
    task_dir: Path,
    actor_name: str,
    actor_fn: Callable[[SandboxWorldHandle, str], dict[str, Any]],
    exo_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Run one TSAI episode in an isolated sandbox, then score with V and TGAI TEA."""
    world_src = task_dir / "world"
    task_md = (task_dir / "task.md").read_text(encoding="utf-8")
    policy_path = task_dir / "tea_policy.yaml"
    raw_policy = load_simple_yaml(policy_path) if policy_path.is_file() else None
    policy = merge_tea_policy(raw_policy)
    verifier_path = task_dir / "verify.py"
    forbidden = set(policy.get("forbidden_paths", []))

    with tempfile.TemporaryDirectory(prefix="vcsw_tsai_") as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copytree(world_src, ws / "world")
        handle = SandboxWorldHandle(ws, forbidden)

        actor_meta = actor_fn(handle, task_md)

        proc = subprocess.run(
            [sys.executable, str(verifier_path), str(ws)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        out_lines = proc.stdout.strip().splitlines()
        v_score = int(out_lines[-1].strip()) if out_lines and out_lines[-1].strip() in ("0", "1") else 0

        trace = {
            "syscalls": handle.syscalls,
            "midrun_states": handle.midrun_states,
            "stdout_logs": handle.stdout_logs,
            "final_report_claims": actor_meta.get("claims", {}),
        }
        tea_res = audit_trajectory(trace, policy)
        tokens = int(actor_meta.get("tokens", 0))
        steps = int(actor_meta.get("steps", 0))
        brevity_score = compute_exo_brevity(
            v_score=v_score,
            tea_pass=tea_res["tea_pass"],
            tokens=tokens,
            steps=steps,
            b_ref=int(exo_cfg.get("b_ref", 800)),
            t_max=int(exo_cfg.get("t_max", 12)),
            alpha=float(exo_cfg.get("alpha_tokens", 0.15)),
            beta=float(exo_cfg.get("beta_steps", 0.15)),
        )

        return {
            "task_id": task_dir.name,
            "actor": actor_name,
            "v_score": v_score,
            "tea_pass": tea_res["tea_pass"],
            "tea_reasons": tea_res["reasons"],
            "tokens": tokens,
            "steps": steps,
            "exo_brevity_score": brevity_score,
            "syscall_count": tea_res["syscall_count"],
            "syscalls": handle.syscalls,
            "midrun_states": handle.midrun_states,
        }
