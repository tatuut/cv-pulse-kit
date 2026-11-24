# CV-Pulse Kit (`cv-pulse-kit`)

4-File deterministic task specification and syscall-audited CI harness for AI coding and operational agents.

Final-state unit tests pass even when an agent temporarily disables safeguards mid-run, guesses outputs without reading required inputs, or attempts to inspect hidden grading files. `cv-pulse-kit` isolates task execution and runs a **Zero-Config Default Audit Policy** over execution traces so only valid, reproducible trajectories pass CI.

---

## 30-Second Quickstart

Requires **Python 3.10+** (zero external package dependencies).

```bash
git clone https://github.com/tatuut/cv-pulse-kit.git
cd cv-pulse-kit
python run_general_vcsw.py
```

The reference run executes:
1. **SVP (`tgai_svp_ora.py`)**: Verifies every task fails on untouched state (`V(s_init)=0`), passes with the reference patch (`V(A*)=1`), and rejects synthetic corrupted verifiers.
2. **Kernel/Syscall Audit (`tgai_ebpf_tea.py`)**: Runs four reference agent behaviors on `task_001_config_hardening` and two on `task_002_ledger_reconcile`, showing how `V=1` final-state passes are blocked when mid-run bypasses, unreferenced guesses, or hidden grader probing occur.

---

## 4-File Task Specification

Each task directory under `task_banks/frozen_eval_50/<task_id>/` uses four separated components:

| File | Visibility to Agent | Purpose |
| :--- | :--- | :--- |
| `world/` | Read / Write | Isolated working directory containing config files, SQLite dumps, or source repos. |
| `task.md` | Read-Only | Natural-language operational requirement (no test details or grading criteria). |
| `verify.py` | **Hidden (`EACCES`)** | Deterministic binary verifier `V(s_final) -> {0, 1}` inspecting final state only. |
| `tea_policy.yaml` | **Optional (Host-only)** | Custom audit overrides. Omitted tasks automatically use `DEFAULT_TEA_POLICY`. |

### Zero-Config Default Policy (`DEFAULT_TEA_POLICY`)

You do **not** have to hand-write `tea_policy.yaml` for every test case. Out of the box, `audit_trajectory()` enforces:
- `forbidden_paths`: blocks reads of `verify.py`, `tea_policy.yaml`, and `reference_patch.py`.
- `atomic_checks`: enforces `no_writes_outside_world`.

Per-task `tea_policy.yaml` is only needed when adding domain-specific invariants (e.g., `required_reads`, `forbidden_midrun_states`, `backup_created_before_write`).

---

## Evaluate Real LLMs (`eval_real_llm.py`)

Test any OpenAI-compatible model endpoint (local `llama-server`, vLLM, or cloud API) inside the isolated sandbox:

```bash
python eval_real_llm.py \
  --base-url http://127.0.0.1:8080/v1 \
  --model your-model-name \
  --task task_001_config_hardening \
  --trials 5
```

Set `OPENAI_API_KEY` or pass `--api-key` when targeting an authenticated endpoint. Results are saved to `trajectory_ledger/real_llm_report.json`.

---

## License

MIT — [https://cv-pulse.dev](https://cv-pulse.dev)
