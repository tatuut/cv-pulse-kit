"""WriteInAdapter abstract contract and Stage a/b implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillRule:
    """Single behavioral rule stored in Stage b external control package P."""

    rule_id: str
    scope: str
    directive: str
    score: float = 1.00
    token_cost: int = 30
    validated_holdout_hits: list[int] = field(default_factory=list)


@dataclass
class SoftPackageState:
    """External control state P_t = (skills, tools) for Stage b Soft Write-in."""

    generation: int = 0
    max_token_budget: int = 1500
    decay_gamma: float = 0.90
    prune_threshold: float = 0.30
    rules: list[SkillRule] = field(default_factory=list)


class WriteInAdapter(ABC):
    """Universal Stage a plugin contract separating VCSW core from write-in target."""

    @abstractmethod
    def bind_to_actor(self, base_model: str, state_w: Any) -> dict[str, Any]:
        """Attach current control state W_t to base model and return agnostic actor config."""

    @abstractmethod
    def step_up_and_write_in(
        self,
        state_w: Any,
        verified_trajectories: list[dict[str, Any]],
        exo_constraints: dict[str, Any],
    ) -> Any:
        """Consume TGAI-verified trajectories and Exo constraints to emit W_{t+1}."""


class NullAdapter(WriteInAdapter):
    """Stage a No-Op adapter for clean baseline benchmarking and trajectory mining."""

    def bind_to_actor(self, base_model: str, state_w: Any) -> dict[str, Any]:
        return {
            "adapter": "NullAdapter",
            "base_model": base_model,
            "injected_rules": [],
            "state_snapshot": state_w or {},
        }

    def step_up_and_write_in(
        self,
        state_w: Any,
        verified_trajectories: list[dict[str, Any]],
        exo_constraints: dict[str, Any],
    ) -> Any:
        passed = [t for t in verified_trajectories if t.get("v_score") == 1 and t.get("tea_pass")]
        return {
            "mode": "null_benchmark",
            "total_trajectories": len(verified_trajectories),
            "pure_verified_count": len(passed),
            "exo_constraints": exo_constraints,
        }


class SoftAdapter(WriteInAdapter):
    """Stage b skeleton adapter with exponential text Weight Decay and holdout reinforcement."""

    def bind_to_actor(self, base_model: str, state_w: SoftPackageState) -> dict[str, Any]:
        return {
            "adapter": "SoftAdapter",
            "base_model": base_model,
            "generation": state_w.generation,
            "injected_rules": [
                {"rule_id": r.rule_id, "scope": r.scope, "directive": r.directive}
                for r in state_w.rules
            ],
        }

    def step_up_and_write_in(
        self,
        state_w: SoftPackageState,
        verified_trajectories: list[dict[str, Any]],
        exo_constraints: dict[str, Any],
    ) -> SoftPackageState:
        gamma = float(exo_constraints.get("soft_decay_gamma", state_w.decay_gamma))
        prune_th = float(exo_constraints.get("soft_prune_threshold", state_w.prune_threshold))
        delta = float(exo_constraints.get("soft_reinforce_delta", 0.45))
        cap = float(exo_constraints.get("soft_score_cap", 5.0))

        holdout_hits_by_rule: dict[str, int] = {}
        for traj in verified_trajectories:
            if traj.get("v_score") == 1 and traj.get("tea_pass"):
                for rid in traj.get("used_rule_ids", []):
                    holdout_hits_by_rule[rid] = holdout_hits_by_rule.get(rid, 0) + 1

        next_rules: list[SkillRule] = []
        next_gen = state_w.generation + 1
        for rule in state_w.rules:
            decayed = rule.score * gamma
            hits = holdout_hits_by_rule.get(rule.rule_id, 0)
            reinforced = min(cap, decayed + delta * hits)
            if reinforced >= prune_th:
                new_hits = list(rule.validated_holdout_hits)
                if hits > 0:
                    new_hits.append(next_gen)
                next_rules.append(
                    SkillRule(
                        rule_id=rule.rule_id,
                        scope=rule.scope,
                        directive=rule.directive,
                        score=round(reinforced, 4),
                        token_cost=rule.token_cost,
                        validated_holdout_hits=new_hits,
                    )
                )

        return SoftPackageState(
            generation=next_gen,
            max_token_budget=state_w.max_token_budget,
            decay_gamma=gamma,
            prune_threshold=prune_th,
            rules=next_rules,
        )
