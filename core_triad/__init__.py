"""Core triad (TCAI / TGAI / TSAI) package for Stage a VCSW."""

from .tgai_ebpf_tea import audit_trajectory, compute_exo_brevity
from .tgai_svp_ora import run_ora, run_svp
from .tsai_sandbox_runner import SandboxWorldHandle, run_episode
from .yaml_util import load_simple_yaml

__all__ = [
    "load_simple_yaml",
    "run_svp",
    "run_ora",
    "audit_trajectory",
    "compute_exo_brevity",
    "SandboxWorldHandle",
    "run_episode",
]
