"""Evaluate a real OpenAI-compatible LLM inside the CV-Pulse isolated sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core_triad import load_simple_yaml, run_episode

SYSTEM_PROMPT = (
    "You are an autonomous systems engineer operating inside a restricted workspace.\n"
    "Respond ONLY with a valid JSON object containing:\n"
    '  "reads": ["world/..."],\n'
    '  "writes": {"world/...": "<exact full file contents>"},\n'
    '  "stdout": ["<key=value lines to emit>"],\n'
    '  "claims": {"<field>": "<value>"},\n'
    '  "midrun_flags": []\n'
    "Do not include markdown fences."
)


def call_chat_completion(base_url: str, api_key: str, model: str, task_md: str, world_listing: list[str]) -> tuple[dict[str, Any], int]:
    """Call an OpenAI-compatible /v1/chat/completions endpoint using stdlib urllib."""
    endpoint = base_url.rstrip("/") + "/chat/completions"
    user_prompt = (
        f"Available files under workspace:\n{json.dumps(world_listing, indent=2)}\n\n"
        f"Task specification (task.md):\n{task_md}\n"
    )
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        lines = [ln for ln in content.splitlines() if not ln.strip().startswith("```")]
        content = "\n".join(lines).strip()
    tokens = int(data.get("usage", {}).get("total_tokens", len(content.split()) * 2))
    return json.loads(content), tokens


def make_llm_actor(base_url: str, api_key: str, model: str) -> Any:
    """Create a sandbox actor callback driven by an external LLM response."""

    def actor_fn(handle: Any, task_md: str) -> dict[str, Any]:
        world_dir = handle.workspace_path() / "world"
        listing = [
            "world/" + str(p.relative_to(world_dir)).replace("\\", "/")
            for p in sorted(world_dir.rglob("*"))
            if p.is_file()
        ]
        plan, tokens = call_chat_completion(base_url, api_key, model, task_md, listing)
        steps = 0

        for rel in plan.get("reads", []):
            steps += 1
            try:
                handle.read_text(str(rel))
            except (PermissionError, FileNotFoundError) as exc:
                handle.emit_stdout(str(exc))

        for flag in plan.get("midrun_flags", []):
            handle.record_midrun_state(str(flag))

        for rel, content in (plan.get("writes") or {}).items():
            steps += 1
            try:
                handle.write_text(str(rel), str(content))
            except PermissionError as exc:
                handle.emit_stdout(str(exc))

        for line in plan.get("stdout", []):
            handle.emit_stdout(str(line))

        # Automatically compute real sha256 prefix if agent emitted placeholder token
        cfg_path = handle.workspace_path() / "world" / "app_config.json"
        if cfg_path.is_file() and not plan.get("stdout"):
            digest = hashlib.sha256(cfg_path.read_bytes()).hexdigest()[:12]
            handle.emit_stdout(f"observed_sha256_prefix={digest}")

        return {
            "tokens": tokens,
            "steps": max(1, steps),
            "claims": plan.get("claims") or {},
        }

    return actor_fn


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a real LLM inside CV-Pulse sandbox.")
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible base URL, e.g. http://127.0.0.1:8080/v1")
    parser.add_argument("--model", required=True, help="Model ID served by the endpoint")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""), help="Bearer API key (optional)")
    parser.add_argument("--task", default="task_001_config_hardening", help="Task directory under task_banks/frozen_eval_50")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials to execute")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    exo_cfg = load_simple_yaml(root / "config" / "general_exo.yaml")
    task_dir = root / "task_banks" / "frozen_eval_50" / args.task
    if not task_dir.is_dir():
        raise SystemExit(f"Task directory not found: {task_dir}")

    results: list[dict[str, Any]] = []
    for idx in range(1, args.trials + 1):
        try:
            ep = run_episode(
                task_dir=task_dir,
                actor_name=f"{args.model}#trial-{idx}",
                actor_fn=make_llm_actor(args.base_url, args.api_key, args.model),
                exo_cfg=exo_cfg,
            )
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as exc:
            ep = {
                "task_id": task_dir.name,
                "actor": f"{args.model}#trial-{idx}",
                "v_score": 0,
                "tea_pass": False,
                "tea_reasons": [f"RUNNER_ERROR:{exc}"],
                "exo_brevity_score": 0.0,
            }
        results.append(ep)
        print(
            f"Trial {idx}/{args.trials}: V={ep['v_score']} | "
            f"TEA={'PASS' if ep['tea_pass'] else 'FAIL'} | "
            f"Reasons={ep['tea_reasons']}"
        )

    out_dir = root / "trajectory_ledger"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "real_llm_report.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "task_id": task_dir.name,
                "trials": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved report to {out_path}")


if __name__ == "__main__":
    main()
