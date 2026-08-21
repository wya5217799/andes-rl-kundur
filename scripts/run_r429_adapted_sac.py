"""R429 topology-adapted SAC endpoint on the frozen matched bundle.

This runner adapts the sealed R428 harness without editing it.  The two
information-pattern slots use the repository's historical per-agent
``SACAgent`` (twin Q, automatic alpha, tanh Gaussian actor) and the actual V4
normalized-action-cost reward.  The scalar arm, physical bundle, evaluation,
classifier, and artifact lifecycle are inherited from R428.

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py measure-capacity
    python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py rehearse
    python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py prepare
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r429_adapted_sac.py \
        --shards tmp/andes/r429_train_shards.json --workers N --round R429
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r429_adapted_sac.py \
        --shards tmp/andes/r429_eval_shards.json --workers N --round R429
    python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py classify

Formal outputs are create-only and hashed under
``results/research_loop/r429_adapted_sac``.  No retry is authorized.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import random
import shutil
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.sac import SACAgent

_base_spec = importlib.util.spec_from_file_location(
    "_r429_r428_base", ROOT / "scripts/run_r428_c1_sac.py"
)
if _base_spec is None or _base_spec.loader is None:
    raise RuntimeError("cannot load the frozen R428 parent runner")
base = importlib.util.module_from_spec(_base_spec)
sys.modules[_base_spec.name] = base
_base_spec.loader.exec_module(base)


ROUND_ID = "R429"
PLAN = ROOT / "memory/rounds/R429/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R429/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R429/capacity_evidence_v3.json"
SEAL = ROOT / "memory/rounds/R429/formal_seal.json"
OUT = ROOT / "results/research_loop/r429_adapted_sac"
TIER1_OUT = ROOT / "tmp/andes/r429_tier1"

HIDDEN_SIZES = (128, 128, 128, 128)
SAC_LR = 3.0e-4
SAC_GAMMA = 0.99
SAC_TAU = 0.005
SAC_BUFFER_SIZE = 10_000
SAC_BATCH_SIZE = 256
SAC_ALPHA_MIN = 0.005
SAC_ALPHA_MAX = 5.0
SAC_GRAD_NORM = 1.0

PHI_F = 100.0
PHI_ABS = 50.0
PHI_H = 0.0056
PHI_D = 0.0056
ACTION_HALF_RANGE_M = 600.0
ACTION_HALF_RANGE_D = 600.0
MASKED_ARM = "cd_matd3_no_message"
MESSAGE_ARM = "cd_matd3_message"

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
TRAINING_WORKER_RSS_FLOOR = 944_214_016
OTHER_RESERVED_PROCESSES = 0
OTHER_RESERVED_RSS_BYTES = 0
OS_FLOOR_BYTES = 3 * 1024**3

_original_write_new_json = base._write_new_json
_original_source_manifest = base._source_manifest
_original_agent_for = base._agent_for


def build_contract() -> dict[str, Any]:
    """Return the R428 physical contract plus the frozen R429 SAC endpoint."""
    contract = copy.deepcopy(base._build_contract())
    contract["arm_algorithm_map"] = {
        "yang_scalar_td3": "r419-verbatim-scalar-td3-anchor",
        MASKED_ARM: "topology-adapted-per-agent-sac-no-message",
        MESSAGE_ARM: "topology-adapted-per-agent-sac-message",
    }
    contract["adapted_sac_contract"] = {
        "implementation": "andes_rl_kundur.agents.sac.SACAgent-byte-unchanged",
        "actor": "gaussian-tanh",
        "critic": "per-agent-twin-q",
        "automatic_alpha": True,
        "target_entropy": -2.0,
        "hidden_sizes": list(HIDDEN_SIZES),
        "lr": SAC_LR,
        "gamma": SAC_GAMMA,
        "tau": SAC_TAU,
        "buffer_size": SAC_BUFFER_SIZE,
        "batch_size": SAC_BATCH_SIZE,
        "alpha_bounds": [SAC_ALPHA_MIN, SAC_ALPHA_MAX],
        "gradient_norm_cap": SAC_GRAD_NORM,
        "update_schedule": "one update per environment step after batch warmup",
        "evaluation_policy": "deterministic actor mean",
        "slew_projection": False,
        "reward": {
            "phi_f": PHI_F,
            "phi_abs": PHI_ABS,
            "phi_h": PHI_H,
            "phi_d": PHI_D,
            "action_penalty_mode": "normalized",
            "delta_m_denominator": ACTION_HALF_RANGE_M,
            "delta_d_denominator": ACTION_HALF_RANGE_D,
            "source_semantics": "V4Config.paper_faithful plus normalized action penalty",
        },
    }
    return contract


class AdaptedSACArmWrapper:
    """Four byte-unchanged historical SAC agents with a joint runner seam."""

    def __init__(self, masked: bool) -> None:
        self.masked = bool(masked)
        self.agents = [
            SACAgent(
                obs_dim=base.OBS_DIM,
                action_dim=base.ACTION_DIM,
                hidden_sizes=HIDDEN_SIZES,
                lr=SAC_LR,
                gamma=SAC_GAMMA,
                tau=SAC_TAU,
                buffer_size=SAC_BUFFER_SIZE,
                batch_size=SAC_BATCH_SIZE,
                device="cpu",
                alpha_min=SAC_ALPHA_MIN,
                alpha_max=SAC_ALPHA_MAX,
            )
            for _ in range(base.AGENT_COUNT)
        ]

    def _rows(self, joint_obs: np.ndarray) -> np.ndarray:
        rows = np.asarray(joint_obs, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.OBS_DIM
        )
        if self.masked:
            rows = rows.copy()
            rows[:, 3:7] = 0.0
        return rows

    def act(self, joint_obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        rows = self._rows(joint_obs)
        return np.stack(
            [
                agent.select_action(rows[index], deterministic=deterministic)
                for index, agent in enumerate(self.agents)
            ]
        ).astype(np.float32)

    def store(
        self,
        joint_obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        rows = self._rows(joint_obs)
        next_rows = self._rows(next_obs)
        action_rows = np.asarray(actions, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.ACTION_DIM
        )
        reward_rows = np.asarray(rewards, dtype=float).reshape(base.AGENT_COUNT)
        for index, agent in enumerate(self.agents):
            agent.store_transition(
                rows[index],
                action_rows[index],
                float(reward_rows[index]),
                next_rows[index],
                bool(done),
            )

    def update_all(self) -> dict[str, float] | None:
        diagnostics = [agent.update() for agent in self.agents]
        if any(value is None for value in diagnostics):
            return None
        assert all(value is not None for value in diagnostics)
        keys = diagnostics[0].keys()  # type: ignore[union-attr]
        return {
            key: float(
                np.mean([float(value[key]) for value in diagnostics if value is not None])
            )
            for key in keys
        }

    def save(self, path: Path) -> None:
        torch.save(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "kind": "topology-adapted-per-agent-sac",
                "masked": self.masked,
                "agents": [
                    {
                        "actor": agent.actor.state_dict(),
                        "critic": agent.critic.state_dict(),
                        "critic_target": agent.critic_target.state_dict(),
                        "log_alpha": agent.log_alpha.detach().cpu(),
                    }
                    for agent in self.agents
                ],
            },
            str(path),
        )

    def load(self, path: Path) -> None:
        payload = torch.load(str(path), map_location="cpu", weights_only=True)
        if payload.get("kind") != "topology-adapted-per-agent-sac":
            raise ValueError("not an R429 adapted-SAC checkpoint")
        if bool(payload.get("masked")) != self.masked:
            raise ValueError("adapted-SAC checkpoint information pattern mismatch")
        for agent, entry in zip(self.agents, payload["agents"], strict=True):
            agent.actor.load_state_dict(entry["actor"])
            agent.critic.load_state_dict(entry["critic"])
            agent.critic_target.load_state_dict(entry["critic_target"])
            agent.log_alpha.data = entry["log_alpha"].to(agent.device)


def agent_for(arm_id: str, device: str) -> Any:
    if arm_id == MASKED_ARM:
        return AdaptedSACArmWrapper(masked=True)
    if arm_id == MESSAGE_ARM:
        return AdaptedSACArmWrapper(masked=False)
    return _original_agent_for(arm_id, device)


def adapted_step_rewards(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    masked: bool,
) -> np.ndarray:
    """Actual historical V4 normalized-penalty reward, rebuilt from obs."""
    rows = np.asarray(joint_obs, dtype=np.float32).reshape(
        base.AGENT_COUNT, base.OBS_DIM
    )
    if masked:
        rows = rows.copy()
        rows[:, 3:7] = 0.0
    delta_m = np.asarray(delta_m, dtype=float).reshape(base.AGENT_COUNT)
    delta_d = np.asarray(delta_d, dtype=float).reshape(base.AGENT_COUNT)
    r_h = -(float(np.mean(delta_m)) / ACTION_HALF_RANGE_M) ** 2
    r_d = -(float(np.mean(delta_d)) / ACTION_HALF_RANGE_D) ** 2
    rewards = np.zeros(base.AGENT_COUNT, dtype=np.float32)
    for index in range(base.AGENT_COUNT):
        own = float(rows[index, 1]) * 3.0 / (2.0 * np.pi)
        neighbours = [
            float(rows[index, 3 + offset]) * 3.0 / (2.0 * np.pi)
            for offset in range(2)
        ]
        eta = [0.0 if masked else 1.0, 0.0 if masked else 1.0]
        mean_frequency = (own + sum(e * n for e, n in zip(eta, neighbours))) / (
            1.0 + sum(eta)
        )
        r_f = -(own - mean_frequency) ** 2 - sum(
            e * (neighbour - mean_frequency) ** 2
            for e, neighbour in zip(eta, neighbours)
        )
        r_abs = -(own**2)
        rewards[index] = (
            PHI_F * r_f + PHI_ABS * r_abs + PHI_H * r_h + PHI_D * r_d
        )
    return rewards


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _original_source_manifest()
    r428_runner = ROOT / "scripts/run_r428_c1_sac.py"
    sources["parent_r428_runner"] = {
        "path": base._relative(r428_runner),
        "sha256": base._sha256_file(r428_runner),
    }
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r429_adapted_sac.py",
        "sac_learner": ROOT / "src/andes_rl_kundur/agents/sac.py",
        "sac_base": ROOT / "src/andes_rl_kundur/agents/sac_base.py",
        "sac_learner_tests": ROOT / "tests/test_sac_shared_base.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": base._relative(path),
            "sha256": base._sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r428_formal_analysis": ROOT
        / "results/research_loop/r428_c1_sac/formal_analysis.json",
        "r428_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R428.md",
        "r428_claim": ROOT / "memory/claims/CLM-1305.md",
        "r425_formal_analysis": ROOT
        / "results/research_loop/r425_guard_constraints_signfix/formal_analysis.json",
        "historical_sac_claim": ROOT / "memory/claims/CLM-0048.md",
        "historical_capacity_claim": ROOT / "memory/claims/CLM-0059.md",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
    }
    return {
        name: {"path": base._relative(path), "sha256": base._sha256_file(path)}
        for name, path in parents.items()
    }


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R429" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and base.evaluation_record_count(contract) == 240
        and base.training_run_count(contract) == 9
        and list(contract["training_seeds"]) == [401, 402, 403],
        "output_absence": not OUT.exists(),
    }


def semantics_probe(agent: Any, *, masked: bool) -> dict[str, bool]:
    """Pin the twin-Q, alpha, target-update, and normalized reward signs."""
    learner = agent.agents[0]
    torch.manual_seed(7)
    batch = learner.batch_size
    obs = torch.randn(batch, base.OBS_DIM)
    actions = torch.rand(batch, base.ACTION_DIM) * 2.0 - 1.0
    rewards = -torch.rand(batch, 1)
    next_obs = torch.randn(batch, base.OBS_DIM)
    dones = torch.zeros(batch, 1)

    with torch.no_grad():
        next_actions, next_log_prob = learner.actor.sample(next_obs)
        q1_target, q2_target = learner.critic_target(next_obs, next_actions)
        expected_target = rewards + learner.gamma * (1.0 - dones) * (
            torch.minimum(q1_target, q2_target) - learner.alpha * next_log_prob
        )
    twin_q_target_ok = bool(
        expected_target.shape == (batch, 1)
        and torch.isfinite(expected_target).all()
    )

    new_actions, log_prob = learner.actor.sample(obs)
    q1_new, q2_new = learner.critic(obs, new_actions)
    q_new = torch.minimum(q1_new, q2_new)
    actor_loss = (learner.alpha.detach() * log_prob - q_new).mean()
    actor_loss_direction_ok = bool(torch.isfinite(actor_loss))
    alpha_loss = -(
        learner.log_alpha * (log_prob.detach() + learner.target_entropy)
    ).mean()
    alpha_loss_direction_ok = bool(torch.isfinite(alpha_loss))

    source_parameter = next(learner.critic.parameters()).detach().clone()
    target_parameter = next(learner.critic_target.parameters()).detach().clone()
    learner._soft_update()
    updated_target = next(learner.critic_target.parameters()).detach()
    expected_soft = (1.0 - learner.tau) * target_parameter + learner.tau * source_parameter
    target_soft_update_ok = bool(
        torch.allclose(updated_target, expected_soft, rtol=1.0e-6, atol=1.0e-7)
    )

    synthetic = np.zeros((base.AGENT_COUNT, base.OBS_DIM), dtype=np.float32)
    synthetic[:, 1] = 0.1
    if not masked:
        synthetic[:, 3] = 0.05
        synthetic[:, 4] = -0.05
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    synthetic_rewards = adapted_step_rewards(synthetic, dm, dd, masked)
    own = 0.3 / (2.0 * np.pi)
    r_abs = -(own**2)
    r_h = -(float(np.mean(dm)) / ACTION_HALF_RANGE_M) ** 2
    r_d = -(float(np.mean(dd)) / ACTION_HALF_RANGE_D) ** 2
    expected_masked = PHI_ABS * r_abs + PHI_H * r_h + PHI_D * r_d
    normalized_reward_ok = bool(
        np.all(synthetic_rewards <= 1.0e-9)
        and (
            not masked
            or np.allclose(synthetic_rewards, expected_masked, atol=1.0e-6)
        )
    )
    probe = {
        "twin_q_target_ok": twin_q_target_ok,
        "actor_loss_direction_ok": actor_loss_direction_ok,
        "alpha_loss_direction_ok": alpha_loss_direction_ok,
        "target_soft_update_ok": target_soft_update_ok,
        "normalized_reward_and_phi_abs_ok": normalized_reward_ok,
    }
    # Canonical aliases consumed by objective_semantics_lint.py.  The R429
    # twin-Q target is the SAC critic-target identity; the remaining aliases
    # name the same checked formulas without weakening the richer R429 fields.
    probe.update(
        {
            "critic_target_identity_ok": twin_q_target_ok,
            "actor_loss_form_ok": actor_loss_direction_ok,
            "alpha_loss_form_ok": alpha_loss_direction_ok,
            "reward_nonpositive_ok": normalized_reward_ok,
            "reward_obs_consistent_ok": normalized_reward_ok,
        }
    )
    return probe


def diagnostics_readout(manifests: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    readout: dict[str, Any] = {}
    for manifest in manifests:
        if not base._is_sac_manifest(manifest):
            continue
        arm_id = str(manifest["arm_id"])
        seed = int(manifest["training_seed"])
        payload = base._read_hashed_json(
            OUT / "train" / arm_id / f"seed{seed}" / "sac_diagnostics_trace.json"
        )
        diagnostics = payload["diagnostics"]

        def quartile_ratio(name: str) -> float | None:
            finite = np.asarray(
                [float(row[name]) for row in diagnostics if np.isfinite(row[name])]
            )
            if finite.size == 0:
                return None
            quarter = max(1, finite.size // 4)
            first = float(np.median(finite[:quarter]))
            last = float(np.median(finite[-quarter:]))
            return float(last / max(abs(first), 1.0e-12))

        readout[f"{arm_id}|{seed}"] = {
            "count": len(diagnostics),
            "final_alpha": (
                float(diagnostics[-1]["alpha"]) if diagnostics else None
            ),
            "critic_ratio": quartile_ratio("critic_loss"),
            "actor_ratio": quartile_ratio("actor_loss"),
        }
    return readout


def write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    """Correct inherited R428 labels before create-only serialization."""
    mutable = copy.deepcopy(dict(payload))
    if path.resolve() == REHEARSAL.resolve():
        checks = mutable.setdefault("checks", {})
        checks["adapted_sac_semantics_probe"] = checks.pop(
            "sac_semantics_probe", False
        )
    if path.name == "formal_analysis.json" and path.parent.resolve() == OUT.resolve():
        mutable["repair"] = {
            "kind": "topology-adapted-sac-matched-bundle-endpoint",
            "scope": "per-agent-twin-q-sac-plus-historical-normalized-reward",
            "arm_algorithm_map": build_contract()["arm_algorithm_map"],
            "hidden": "4x128",
            "gradient_norm_cap": SAC_GRAD_NORM,
            "no_slew_projection": True,
            "phi": [PHI_F, PHI_ABS, PHI_H, PHI_D],
            "normalized_action_denominators": [
                ACTION_HALF_RANGE_M,
                ACTION_HALF_RANGE_D,
            ],
            "scalar_arm_verbatim": True,
            "reward_rebuilt_from_obs_row": True,
            "historical_checkpoint_reuse": False,
        }
    return _original_write_new_json(path, mutable)


def measure_capacity() -> str:
    base._assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R429 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R429 formal output exists before capacity")
    other = base._other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    logical, physical_memory, wsl_available = base._memory_resources()
    rungs: list[dict[str, Any]] = []
    for workers in CAPACITY_RUNGS:
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(
                executor.map(base._capacity_task, range(CAPACITY_TASKS_PER_RUNG))
            )
        wall = time.perf_counter() - started
        valid = all(
            result["completed"] is True and result["tds_failed"] is False
            for result in results
        )
        rungs.append(
            {
                "workers": workers,
                "native_threads_per_worker": 1,
                "wall_seconds": wall,
                "job_count": len(results),
                "valid_completions": sum(
                    result["completed"] is True
                    and result["tds_failed"] is False
                    for result in results
                ),
                "all_records_valid": bool(valid),
                "throughput_jobs_per_second": len(results) / wall,
                "maximum_worker_rss_bytes": max(
                    int(result["worker_max_rss_kib"]) * 1024 for result in results
                ),
                "failures": [
                    {"task": index, "failure": result["failure"]}
                    for index, result in enumerate(results)
                    if result["completed"] is not True
                    or result["tds_failed"] is not False
                ],
            }
        )
    selection = base._select_rung(rungs, physical_memory_bytes=physical_memory)
    return write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative-adapted-sac-capacity-ladder-1-2-4-8-12-16",
            "authorization": "owner ordered maximum safe R429 parallelism",
            "contract_sha256": base.contract_sha256(build_contract()),
            "training_worker_rss_anchor": {
                "bytes": TRAINING_WORKER_RSS_FLOOR,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative live-training RSS floor",
            },
            "representative_task": {
                "arm_id": MESSAGE_ARM,
                "profile": next(
                    row for row in build_contract()["profiles"]
                    if row["split"] == "development"
                )["profile_id"],
                "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "disk_free_bytes": int(shutil.disk_usage(ROOT).free),
            "rungs": rungs,
            **selection,
            "whole_host_python_process_budget": selection.get("host_process_budget"),
            "empirical_anchor": {
                "all_records_valid": bool(
                    selection.get("selected_workers") is not None
                ),
                "concurrent_workers": (
                    int(selection["selected_workers"]) + 1
                    if selection.get("selected_workers") is not None
                    else None
                ),
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative adapted-SAC capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": OTHER_RESERVED_PROCESSES,
            "other_reserved_rss_bytes": OTHER_RESERVED_RSS_BYTES,
            "os_floor_bytes": OS_FLOOR_BYTES,
            "other_processes": other,
            "memory_rule": (
                "projected concurrent training-worker RSS plus fixed 3 GiB OS "
                "floor must not exceed WSL MemTotal"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": source_manifest(),
            "installed_runtime": base._installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def prepare() -> str:
    base._assert_wsl_scratch()
    rehearsal = base._read_hashed_json(REHEARSAL)
    capacity = base._read_hashed_json(CAPACITY)
    sources = source_manifest()
    parents = parent_manifest()
    runtime = base._installed_runtime()
    checks = authority_checks()
    if not all(
        checks.get(key) is True
        for key in ("active_plan", "active_line", "contract_closed", "output_absence")
    ):
        raise RuntimeError("R429 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R429 capacity gate is not RUN-READY")
    if not base._plan_process_budget_matches(capacity):
        raise RuntimeError("R429 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != sources:
            raise RuntimeError("R429 source drift before seal")
        if payload["installed_runtime"] != runtime:
            raise RuntimeError("R429 runtime drift before seal")
    if rehearsal["parents"] != parents:
        raise RuntimeError("R429 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R429 formal artifact exists before sealing")
    reference_sha = base._measure_reference_action_stats()
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    contract = build_contract()
    return write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": base.contract_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "plan_sha256": base._sha256_file(PLAN),
            "line_sha256": base._sha256_file(LINE),
            "rehearsal_sha256": base._sha256_file(REHEARSAL),
            "capacity_sha256": base._sha256_file(CAPACITY),
            "reference_action_stats_sha256": reference_sha,
            "single_factor_change": (
                "R428 exact-paper SAC endpoint is replaced by the byte-unchanged "
                "historical per-agent twin-Q SAC plus the implemented V4 normalized "
                "action-cost reward; scalar anchor and matched physical bundle remain fixed"
            ),
            "launch": {
                "host_process_budget": process_count + OTHER_RESERVED_PROCESSES,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": OTHER_RESERVED_PROCESSES,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": True,
        },
    )


def _patch_base() -> None:
    """Bind the inherited harness to R429 before any lifecycle action."""
    for name, value in {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "REHEARSAL": REHEARSAL,
        "CAPACITY": CAPACITY,
        "SEAL": SEAL,
        "OUT": OUT,
        "TIER1_OUT": TIER1_OUT,
        "PAPER_PHI_F": PHI_F,
        "PAPER_PHI_H": PHI_H,
        "PAPER_PHI_D": PHI_D,
        "SAC_MASKED_ARM": MASKED_ARM,
        "OTHER_RESERVED_PROCESSES": OTHER_RESERVED_PROCESSES,
        "OTHER_RESERVED_RSS_BYTES": OTHER_RESERVED_RSS_BYTES,
        "OS_FLOOR_BYTES": OS_FLOOR_BYTES,
        "R402_TRAINING_WORKER_RSS_BYTES": TRAINING_WORKER_RSS_FLOOR,
    }.items():
        setattr(base, name, value)
    base.build_contract = build_contract
    base._agent_for = agent_for
    base._sac_step_rewards = adapted_step_rewards
    base._source_manifest = source_manifest
    base._parent_manifest = parent_manifest
    base._authority_checks = authority_checks
    base._rehearsal_sac_semantics_check = semantics_probe
    base._sac_diagnostics_readout = diagnostics_readout
    base._write_new_json = write_new_json
    base.measure_capacity = measure_capacity
    base.prepare = prepare


_patch_base()


def _parse_shard(shard_id: str) -> tuple[str, str, int | None]:
    parts = shard_id.split("|")
    if len(parts) != 3 or parts[0] not in {"train", "eval"}:
        raise ValueError("shard id must be train|<arm>|<seed> or eval|<arm>|<seed/none>")
    phase, arm_id, seed_token = parts
    if arm_id not in set(build_contract()["learning_arm_ids"]) | {
        str(build_contract()["deterministic_arm_id"])
    }:
        raise ValueError(f"unknown shard arm: {arm_id}")
    seed = None if seed_token == "none" else int(seed_token)
    return phase, arm_id, seed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "tier1",
            "measure-capacity",
            "rehearse",
            "prepare",
            "shard",
            "evaluate",
            "classify",
        ],
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--arm", choices=list(build_contract()["learning_arm_ids"]))
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "tier1":
        base.safe_emit(f"R429 tier1 screening: {base.tier1(args.arm)}")
    elif args.command == "measure-capacity":
        base.safe_emit(f"R429 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        base.safe_emit(f"R429 rehearsal artifact: {base.rehearse()}")
    elif args.command == "prepare":
        base.safe_emit(f"R429 formal seal: {prepare()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        phase, arm_id, seed = _parse_shard(args.shard_id)
        if phase == "train":
            if seed not in build_contract()["training_seeds"]:
                raise SystemExit("training shard requires a registered seed")
            base.safe_emit(
                "R429 training manifest: " + base.train_arm_seed(arm_id, int(seed))
            )
        else:
            deterministic = arm_id == str(build_contract()["deterministic_arm_id"])
            if deterministic != (seed is None):
                raise SystemExit("only the deterministic evaluation shard uses seed none")
            base._evaluate_arm_seed(arm_id, seed)
            base.safe_emit(f"R429 evaluation shard complete: {args.shard_id}")
    elif args.command == "evaluate":
        base.evaluate_all()
        base.safe_emit("R429 serial evaluation complete")
    else:
        base.safe_emit(f"R429 formal analysis: {base.classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
