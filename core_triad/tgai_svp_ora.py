"""TGAI Solvability Verification Pipeline (SVP) and Oracle Regret Anchor (ORA)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _run_verifier(verifier_path: Path, workspace_dir: Path) -> tuple[int | None, str]:
    proc = subprocess.run(
        [sys.executable, str(verifier_path), str(workspace_dir)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    out = proc.stdout.strip().splitlines()
    if not out:
        return None, proc.stderr.strip() or "empty verifier output"
    last = out[-1].strip()
    if last not in ("0", "1"):
        return None, f"unexpected verifier output: {last!r} ({proc.stderr.strip()})"
    return int(last), proc.stderr.strip()


def run_svp(task_dir: Path, verifier_override: Path | None = None) -> dict[str, Any]:
    """Execute SVP Step 1 (Zero-Check) and Step 2 (Solvability-Check) in isolated temp sandboxes."""
    world_src = task_dir / "world"
    verifier_path = verifier_override or (task_dir / "verify.py")
    ref_patch_path = task_dir / "reference_patch.py"

    if not world_src.is_dir() or not verifier_path.is_file():
        return {"svp_pass": False, "stage": "PRECHECK", "reason": "missing world/ or verify.py"}

    # Step 1: Zero-Check on untouched initial state s_init
    with tempfile.TemporaryDirectory(prefix="vcsw_svp_zero_") as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copytree(world_src, ws / "world")
        v_init, err = _run_verifier(verifier_path, ws)
        if v_init is None:
            return {
                "svp_pass": False,
                "stage": "STEP_1_ZERO_CHECK",
                "v_init": None,
                "reason": f"CORRUPTED_VERIFIER_EXCEPTION: {err}",
            }
        if v_init != 0:
            return {
                "svp_pass": False,
                "stage": "STEP_1_ZERO_CHECK",
                "v_init": v_init,
                "reason": "CORRUPTED_VERIFIER_INIT_PASS: V(s_init) == 1 without action",
            }

    # Step 2: Solvability-Check using reference patch A*
    if not ref_patch_path.is_file():
        return {"svp_pass": False, "stage": "STEP_2_SOLVABILITY", "reason": "missing reference_patch.py"}

    with tempfile.TemporaryDirectory(prefix="vcsw_svp_solve_") as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copytree(world_src, ws / "world")
        patch_proc = subprocess.run(
            [sys.executable, str(ref_patch_path), str(ws)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if patch_proc.returncode != 0:
            return {
                "svp_pass": False,
                "stage": "STEP_2_SOLVABILITY",
                "reason": f"REFERENCE_PATCH_FAILED: {patch_proc.stderr.strip()}",
            }
        v_ref, err = _run_verifier(verifier_path, ws)
        if v_ref != 1:
            return {
                "svp_pass": False,
                "stage": "STEP_2_SOLVABILITY",
                "v_init": 0,
                "v_ref": v_ref,
                "reason": f"FALSE_NEGATIVE_VERIFIER: A* got V={v_ref} ({err})",
            }

    return {
        "svp_pass": True,
        "stage": "SVP_VERIFIED",
        "v_init": 0,
        "v_ref": 1,
        "reason": "Zero-Check V(s_init)=0 and Solvability-Check V(A*)=1",
    }


def run_ora(
    p_oracle: float,
    p_current: float,
    oracle_min: float = 0.80,
    zpd_min: float = 0.10,
    zpd_max: float = 0.30,
    regret_min: float = 0.50,
) -> dict[str, Any]:
    """Evaluate Oracle Regret Anchor (ORA) acceptance gate."""
    regret = round(p_oracle - p_current, 4)
    if p_oracle < oracle_min:
        status = "REJECTED_LOW_ORACLE"
        adopted = False
    elif p_current > zpd_max:
        status = "DEFERRED_TOO_EASY"
        adopted = False
    elif p_current < zpd_min or regret < regret_min:
        status = "REJECTED_LOW_REGRET_OR_TOO_HARD"
        adopted = False
    else:
        status = "ADOPTED_ZPD"
        adopted = True

    return {
        "ora_adopted": adopted,
        "status": status,
        "p_oracle": p_oracle,
        "p_current": p_current,
        "regret": regret,
    }
