"""R435: causal test of the R432 budget-mechanism hypothesis (multiplier floor).

R432 (CLM-1320) persisted full B3 telemetry on the frozen R410 repaired
bundle (no-message + message arms, seeds 401-403, 43,200 steps) and showed
the lagrange multiplier decaying from ~0.97 to ~0.0 in 4/6 runs while the
per-episode common cost never systematically improved (flat 0.7-3.8, with
81-480 of 1,440 episodes above the 3.0 budget).  Its bounded hypothesis:
"the budget mechanism stops pressing early in training, so nothing drives
the common-frequency cost down" — registered for a future single-factor
round, no such round authorized by that outcome.

This round (owner-authorized 2026-08-19, hardware-saturation order) is that
causal test with ONE single factor: the frozen dual update keeps its exact
formula, but the multiplier is clipped at a pre-registered floor
``LAGRANGE_FLOOR = 1.0`` (its starting level) instead of 0.0, so the
mechanism keeps pressing at the initial pressure for the whole run.  The
learner is the frozen R410 ``CDMATD3`` subclassed by the R435 floor module
(separate module, frozen learner byte-unchanged); the training loop and the
B3 diagnostics are R432-verbatim (the R432 runner is imported read-only and
only its ``_agent_for`` is rebound to the floored factory).  Same bundle,
same seeds, same RNG streams — the paired R432 runs are the no-floor
control.

Pre-registered judgement (computed by ``classify``, never offline):
1. Mechanical: ``lagrange_final >= floor`` in all 6 runs (the floor held).
2. Causal primary (paired vs R432, same arm+seed): mean per-episode common
   cost over the final 360 episodes (1081-1440) of R435 < 0.8 x the same
   window of R432 in >= 4/6 pairs.
3. Causal secondary: within-run final-quarter mean < 0.8 x initial-quarter
   mean in >= 4/6 runs; critic Q4/Q1 (divergence) vs R432; episodes above
   the 3.0 budget.
Verdict: mechanical fails -> CANARY-INVALID; primary holds -> SUPPORTED
(the live multiplier drives the common cost down); primary fails but the
multiplier stayed live -> REFUTED (the mechanism, kept alive, does not
drive the cost down — the causal claim fails; the bottleneck is elsewhere).

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py reuse-capacity
    python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py rehearse
    python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py prepare
    python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py shards
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r435_multiplier_floor.py \
        --shards tmp/andes/r435_train_shards.json --workers 15 --round R435
    python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py classify

Formal outputs are create-only and hashed under
``results/research_loop/r435_multiplier_floor``.  No retry is authorized.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np
import torch

_r432_spec = importlib.util.spec_from_file_location(
    "_r435_r432_parent", ROOT / "scripts/run_r432_b3_diagnostics.py"
)
if _r432_spec is None or _r432_spec.loader is None:
    raise RuntimeError("cannot load the frozen R432 parent runner")
r432 = importlib.util.module_from_spec(_r432_spec)
sys.modules[_r432_spec.name] = r432
_r432_spec.loader.exec_module(r432)
base = r432.base  # the frozen R410 module

ROUND_ID = "R435"
PLAN = ROOT / "memory/rounds/R435/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R435/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R435/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R435/formal_seal.json"
OUT = ROOT / "results/research_loop/r435_multiplier_floor"
R433_CAPACITY = ROOT / "memory/rounds/R433/capacity_evidence.json"
R432_OUT = ROOT / "results/research_loop/r432_b3_diagnostics"

# Frozen single factor: the multiplier floor (its starting level).  The
# frozen dual update is otherwise verbatim (clip [floor, maximum]).
LAGRANGE_FLOOR = 1.0

_EVAL_QUARTER = slice(-360, None)  # final 360 of 1,440 episodes
_INITIAL_QUARTER = slice(0, 360)
PAIRED_RATIO = 0.8
PAIRED_MAJORITY = 4  # >= 4 of 6 pairs
WITHIN_RATIO = 0.8
WITHIN_MAJORITY = 4

_R432_BUILD_CONTRACT = r432.build_contract
_R432_SOURCE_MANIFEST = r432.source_manifest
_R432_PARENT_MANIFEST = r432.parent_manifest

# Names the lifecycle needs from the frozen chain (module globals).
for _name in (
    "PerVSGMDActionProjector",
    "YangScalarTD3",
    "_build_env",
    "_joint_obs",
    "_mask_actor_obs",
    "_save_agent_snapshot",
    "_write_new_json",
    "contract_sha256",
    "safe_emit",
    "_assert_wsl_scratch",
    "_installed_runtime",
    "_memory_resources",
    "_relative",
    "_sha256_file",
    "_read_hashed_json",
    "random",
):
    globals()[_name] = getattr(r432, _name, None) or getattr(base, _name, None)


def _floored_agent_for(arm_id: str, device: str) -> Any:
    """R410 ``_agent_for`` verbatim with the R435-SEAM class swap: the CD
    arms use ``FlooredCDMATD3`` (frozen CDMATD3 + multiplier floor)."""
    from andes_rl_kundur.agents.cd_matd3_multiplier_floor import (  # R435-SEAM
        FlooredCDMATD3,  # R435-SEAM
    )  # R435-SEAM

    contract = build_contract()
    learner = contract["learner_contract"]
    kwargs = dict(
        hidden_sizes=list(learner["actor"]["hidden_sizes"]),
        lr=float(learner["lr"]),
        gamma=float(learner["gamma"]),
        tau=float(learner["tau"]),
        buffer_size=int(learner["buffer_size"]),
        batch_size=int(learner["batch_size"]),
        policy_noise=float(learner["policy_noise"]),
        noise_clip=float(learner["noise_clip"]),
        explore_noise=float(learner["explore_noise"]),
        policy_delay=int(learner["policy_delay"]),
        device=device,
    )
    if arm_id == "yang_scalar_td3":
        return YangScalarTD3(**kwargs)
    if arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
        return FlooredCDMATD3(  # R435-SEAM
            lagrange_initial=1.0,  # R435-SEAM
            lagrange_floor=LAGRANGE_FLOOR,  # R435-SEAM
            actor_neighbour_mask=(arm_id == "cd_matd3_no_message"),  # R435-SEAM
            **kwargs,  # R435-SEAM
        )  # R435-SEAM
    raise ValueError(f"unknown learning arm: {arm_id}")


def load_seal() -> dict[str, Any]:
    """Verify the R435 seal (round, contract, launch budget, learner and
    floor-module source hashes)."""
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract") != build_contract():
        raise RuntimeError("sealed contract drifted from the frozen module")
    if seal.get("contract_sha256") != contract_sha256(build_contract()):
        raise RuntimeError("sealed contract hash mismatch")
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) + int(
        launch.get("other_reserved_processes", 0)
    ) != int(launch.get("host_process_budget", -1)):
        raise RuntimeError("sealed launch budget is inconsistent")
    for name in ("learner", "learner_floor"):
        source_sha = (seal.get("sources") or {}).get(name, {}).get("sha256")
        expected = (
            _sha256_file(ROOT / "src/andes_rl_kundur/agents/cd_matd3.py")
            if name == "learner"
            else _sha256_file(
                ROOT / "src/andes_rl_kundur/agents/cd_matd3_multiplier_floor.py"
            )
        )
        if source_sha != expected:
            raise RuntimeError(f"{name} source drifted from the R435 seal")
    return seal


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_R432_BUILD_CONTRACT())
    contract["engineering_successor"] = {
        "successor_of": "R432",
        "single_change": "lagrange-multiplier-floor-1.0",
        "training_authorized": True,
    }
    contract["multiplier_floor_test"] = {
        "hypothesis": (
            "R432 bounded hypothesis: the budget mechanism stops pressing "
            "(lagrange decays to ~0), so nothing drives the common-frequency "
            "cost down"
        ),
        "single_factor": (
            "frozen dual update with the multiplier clipped at "
            f"floor={LAGRANGE_FLOOR} (never decays below the starting "
            "level); all else R432-verbatim"
        ),
        "floor": LAGRANGE_FLOOR,
        "arms": ["cd_matd3_no_message", "cd_matd3_message"],
        "seeds": [401, 402, 403],
        "control": "R432 paired runs (same bundle, same seeds, no floor)",
        "judgement": {
            "mechanical": "lagrange_final >= floor in all 6 runs",
            "primary": (
                "R435 final-quarter mean common cost < 0.8 x R432 same-window "
                "mean in >= 4/6 arm-seed pairs"
            ),
            "secondary": [
                "within-run final-quarter < 0.8 x initial-quarter in >= 4/6",
                "critic Q4/Q1 vs R432 (6.2-30.5)",
                "episodes above the 3.0 budget",
            ],
        },
    }
    return contract


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R435" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and list(contract["training_seeds"]) == [401, 402, 403]
        and contract["multiplier_floor_test"]["floor"] == LAGRANGE_FLOOR,
        "output_absence": not OUT.exists(),
    }


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _R432_SOURCE_MANIFEST()
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r435_multiplier_floor.py",
        "parent_r432_runner": ROOT / "scripts/run_r432_b3_diagnostics.py",
        "learner_floor": ROOT / "src/andes_rl_kundur/agents/cd_matd3_multiplier_floor.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": _relative(path),
            "sha256": _sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r432_plan": ROOT / "memory/rounds/R432/plan.md",
        "r432_seal": ROOT / "memory/rounds/R432/formal_seal.json",
        "r432_capacity": ROOT / "memory/rounds/R432/capacity_evidence.json",
        "r433_capacity": R433_CAPACITY,
        "r410_analysis": ROOT
        / "results/research_loop/r410_message_repair/formal_analysis.json",
        "program_b3": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
    }
    for arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
        for seed in (401, 402, 403):
            paths[f"r432_diag_{arm_id}_{seed}"] = (
                R432_OUT / "train" / arm_id / f"seed{seed}" / "diagnostics_summary.json"
            )
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in paths.items()
    }


def _plan_process_budget_matches(capacity: dict[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    host = expected + int(capacity.get("other_reserved_processes", 0))
    return bool(
        f"host_process_budget: {host}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and f"other_reserved_processes: {capacity.get('other_reserved_processes', 0)}"
        in plan_text
    )


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    mutable = copy.deepcopy(payload)
    if path.resolve() == REHEARSAL.resolve():
        probe = _floor_semantics_probe()
        mutable.setdefault("checks", {})["floor_semantics_probe"] = bool(
            probe["passed"]
        )
        mutable["floor_semantics_probe"] = probe
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "R432-verbatim training (same bundle, seeds, B3 telemetry) with "
            "the frozen dual update's lower clip moved from 0.0 to the "
            "pre-registered floor 1.0 via the separate FlooredCDMATD3 module; "
            "learner and R410/R432 sources byte-unchanged"
        )
    return _write_new_json(path, mutable)


def _floor_semantics_probe() -> dict[str, Any]:
    """On a short real training window: the multiplier never drops below
    the floor; when the frozen update would keep it above the floor, the
    floored update equals the frozen one exactly; the actor-loss weighting
    is unchanged."""
    contract = build_contract()
    result: dict[str, Any] = {
        "passed": False,
        "floor": LAGRANGE_FLOOR,
        "min_lagrange": None,
        "max_abs_diff_vs_frozen_above_floor": None,
        "steps_checked": 0,
    }
    # Frozen reference: the unfloored dual update on the same signals.
    def frozen_update(lagrange: float, cost: float, budget: float, step: float) -> float:
        return float(np.clip(lagrange + step * (cost - budget), 0.0, 10.0))

    env = _build_env(contract["profiles"][0])
    agent = _floored_agent_for("cd_matd3_message", "cpu")
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    min_lagrange = float("inf")
    max_diff = 0.0
    checked = 0
    try:
        torch.manual_seed(7)
        np.random.seed(7)
        random.seed(7)
        observation = env.reset(
            delta_u=dict(contract["profiles"][0]["scenarios"][0]["delta_u"])
        )
        lagrange = float(agent.lagrange)
        for episode in range(3):
            episode_common = 0.0
            for _ in range(30):
                joint = _joint_obs(observation)
                actor_joint = _mask_actor_obs("cd_matd3_message", joint)
                raw = agent.act(actor_joint, deterministic=False)
                action = projector.project(raw)
                action_dict = {
                    actor: np.asarray(action[actor], dtype=np.float32)
                    for actor in range(4)
                }
                observation, _rewards, _done, info = env.step(action_dict)
                common = 50.0 if info["tds_failed"] else 0.0
                if not info["tds_failed"]:
                    differential, common_c = base.physical_costs(
                        np.asarray(info["freq_hz_physical"], dtype=float)[None, :],
                        np.zeros((1, 4), dtype=float),
                        np.asarray(info["P_es"], dtype=float)[None, :],
                        contract=contract,
                    )
                    common = float(common_c[0])
                episode_common += common
            reward = contract["reward_contract"]["cd_matd3"]
            updated = agent.lagrange_step(
                episode_common,
                budget=float(reward["common_budget_per_episode"]),
                step=float(reward["lagrange_step"]),
                maximum=float(reward["lagrange_maximum"]),
            )
            min_lagrange = min(min_lagrange, float(agent.lagrange))
            frozen_above = frozen_update(
                lagrange,
                episode_common,
                float(reward["common_budget_per_episode"]),
                float(reward["lagrange_step"]),
            )
            # When the frozen update stays above the floor, both must agree.
            if frozen_above >= LAGRANGE_FLOOR:
                max_diff = max(max_diff, abs(updated - frozen_above))
            checked += 1
            lagrange = float(agent.lagrange)
        result["min_lagrange"] = min_lagrange
        result["max_abs_diff_vs_frozen_above_floor"] = max_diff
        result["steps_checked"] = checked
        result["passed"] = bool(
            min_lagrange >= LAGRANGE_FLOOR - 1e-9
            and max_diff <= 1e-9
            and checked == 3
        )
    finally:
        try:
            env.close()
        except Exception:
            pass
    return result


def rehearse() -> str:
    """Pre-attempt verification through the formal entry path."""
    _assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R435 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_closed",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R435 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = source_manifest()
    parents = parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "checks": checks,
        "training_authorized": True,
    }
    return write_new_json(REHEARSAL, payload)


def reuse_capacity() -> str:
    """Reuse the R433 (R431 rung-16 chain) capacity after a fresh
    no-other-process host check; solo run, reserved 0."""
    _assert_wsl_scratch()
    if CAPACITY.exists() or REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R435 pre-attempt artifact already exists")
    other = base._r410_other_research_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    logical, physical_memory, wsl_available = _memory_resources()
    inherited = _read_hashed_json(R433_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) < 15:
        raise RuntimeError(
            "R433 capacity evidence is not the registered rung-16 anchor"
        )
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner approved R435 (multiplier-floor causal test, 2026-08-19 "
                "hardware-saturation order); R431/R433 rung-16 ladder reused "
                "after a fresh no-load host check; solo round, "
                "other_reserved_processes=0"
            ),
            "contract_sha256": contract_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "other_processes": other,
            "readiness": "RUN-READY",
            "selected_workers": 15,
            "wsl_python_processes": 16,
            "host_process_budget": 16,
            "other_reserved_processes": 0,
            "native_threads_per_process": 1,
            "whole_host_python_process_budget": 16,
            "sources": source_manifest(),
            "installed_runtime": _installed_runtime(),
            "inherited_capacity": {
                "path": _relative(R433_CAPACITY),
                "sha256": _sha256_file(R433_CAPACITY),
                "reuse_basis": (
                    "identical CD-family training task class; R435 = R432 "
                    "protocol with the floor module (same per-worker RSS "
                    "envelope)"
                ),
            },
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        }
    )
    payload["empirical_anchor"]["source"] = (
        "R429 v3 selected representative rung plus fresh R431/R433 no-load host checks"
    )
    payload["empirical_anchor"]["concurrent_workers"] = 16
    return _write_new_json(CAPACITY, payload)


def prepare() -> str:
    """Formal seal: training round, create-only artifacts, no retry."""
    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    sources = source_manifest()
    parents = parent_manifest()
    runtime = _installed_runtime()
    checks = authority_checks()
    if not all(
        checks.get(key) is True
        for key in ("active_plan", "active_line", "contract_closed", "output_absence")
    ):
        raise RuntimeError("R435 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R435 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R435 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != sources:
            raise RuntimeError("R435 source drift before seal")
        if payload["installed_runtime"] != runtime:
            raise RuntimeError("R435 runtime drift before seal")
    if rehearsal["parents"] != parents:
        raise RuntimeError("R435 parent drift before seal")
    if not rehearsal["checks"].get("floor_semantics_probe"):
        raise RuntimeError("R435 floor semantics probe did not pass")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R435 formal artifact exists before sealing")
    contract = build_contract()
    return write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": contract_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "launch": {
                "host_process_budget": 16,
                "wsl_python_processes": 16,
                "worker_processes": 15,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": True,
        },
    )


def shards() -> str:
    """Write the 6-shard training manifest (tmp, not a formal artifact)."""
    _assert_wsl_scratch()
    contract = build_contract()
    rows: list[str] = []
    for arm_id in contract["multiplier_floor_test"]["arms"]:
        for seed in contract["multiplier_floor_test"]["seeds"]:
            rows.append(f"train|{arm_id}|{seed}")
    if len(rows) != 6:
        raise RuntimeError(f"unexpected shard count: {len(rows)}")
    out_path = ROOT / "tmp/andes/r435_train_shards.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(out_path)


def train_shard(shard_id: str) -> None:
    """Parse ``train|<arm>|<seed>`` shard ids for the shared driver."""
    phase, _, rest = shard_id.partition("|")
    if phase != "train":
        raise SystemExit(f"R435 supports train shards only: {shard_id}")
    arm_id, _, seed_text = rest.partition("|")
    seed = int(seed_text)
    safe_emit("R435 training manifest: " + r432.train_arm_seed(arm_id, seed))


def _read_diagnostics(arm_id: str, seed: int, root: Path) -> dict[str, Any]:
    path = root / "train" / arm_id / f"seed{seed}" / "diagnostics_summary.json"
    return _read_hashed_json(path)


def _quarter_mean(rows: list[list[float]], window: slice) -> float:
    costs = [float(row[1]) for row in rows]
    return float(np.mean(costs[window]))


def classify() -> str:
    """Aggregate the 6 diagnostics summaries and apply the pre-registered
    judgement (never offline)."""
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    arms = list(contract["multiplier_floor_test"]["arms"])
    seeds = list(contract["multiplier_floor_test"]["seeds"])
    pairs: dict[str, dict[str, Any]] = {}
    mechanical_ok = True
    for arm_id in arms:
        for seed in seeds:
            summary = _read_diagnostics(arm_id, int(seed), OUT)
            rows = summary["episode_rows"]
            final_mean = _quarter_mean(rows, _EVAL_QUARTER)
            initial_mean = _quarter_mean(rows, _INITIAL_QUARTER)
            lagrange_final = float(summary["lagrange_final"])
            mechanical_ok = mechanical_ok and lagrange_final >= LAGRANGE_FLOOR - 1e-9
            control = _read_diagnostics(arm_id, int(seed), R432_OUT)
            control_final_mean = _quarter_mean(control["episode_rows"], _EVAL_QUARTER)
            pairs[f"{arm_id}|{seed}"] = {
                "final_quarter_mean": final_mean,
                "initial_quarter_mean": initial_mean,
                "within_ratio": final_mean / initial_mean if initial_mean > 0 else None,
                "paired_ratio_vs_r432": (
                    final_mean / control_final_mean if control_final_mean > 0 else None
                ),
                "r432_final_quarter_mean": control_final_mean,
                "lagrange_final": lagrange_final,
                "critic_q4_q1": (
                    float(summary["critic_loss_q4"]) / float(summary["critic_loss_q1"])
                    if summary["critic_loss_q1"] > 0
                    else None
                ),
                "episodes_above_budget": sum(
                    1 for row in rows if float(row[1]) > 3.0
                ),
                "r432_episodes_above_budget": sum(
                    1 for row in control["episode_rows"] if float(row[1]) > 3.0
                ),
            }
    primary_hits = sum(
        1
        for row in pairs.values()
        if row["paired_ratio_vs_r432"] is not None
        and row["paired_ratio_vs_r432"] < PAIRED_RATIO
    )
    within_hits = sum(
        1
        for row in pairs.values()
        if row["within_ratio"] is not None and row["within_ratio"] < WITHIN_RATIO
    )
    if not mechanical_ok:
        verdict = "CANARY-INVALID"
    elif primary_hits >= PAIRED_MAJORITY:
        verdict = "SUPPORTED"
    else:
        verdict = "REFUTED"
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": str(contract["manuscript_line"]),
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "hypothesis": contract["multiplier_floor_test"]["hypothesis"],
        "single_factor": contract["multiplier_floor_test"]["single_factor"],
        "mechanical_ok": mechanical_ok,
        "primary_pairs_hit": primary_hits,
        "primary_threshold": PAIRED_MAJORITY,
        "within_run_hits": within_hits,
        "within_threshold": WITHIN_MAJORITY,
        "verdict": verdict,
        "per_arm_seed": pairs,
        "control_source": "R432 paired diagnostics (same bundle/seeds, no floor)",
    }
    analysis_path = OUT / "formal_analysis.json"
    digest = _write_new_json(analysis_path, analysis)
    manifest_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_sha256": digest,
        "input_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "checkpoint_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("train/*/*/final.pt"))
        ],
        "verdict": verdict,
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def _patch_parent() -> None:
    values = {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "REHEARSAL": REHEARSAL,
        "CAPACITY": CAPACITY,
        "SEAL": SEAL,
        "OUT": OUT,
    }
    for module in (r432, base):
        for name, value in values.items():
            setattr(module, name, value)
    for module in (r432, base):
        module.build_contract = build_contract
        module._source_manifest = source_manifest
        module._parent_manifest = parent_manifest
        module._authority_checks = authority_checks
        module._write_new_json = write_new_json
    # The declared seam: the R432 training loop (verbatim, incl. B3
    # telemetry) builds agents through its module-global _agent_for;
    # rebinding it to the floored factory applies the single factor
    # everywhere.
    r432._agent_for = _floored_agent_for
    base._agent_for = _floored_agent_for
    base.OTHER_RESERVED_PROCESSES = 0


_patch_parent()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "reuse-capacity",
            "rehearse",
            "prepare",
            "shards",
            "shard",
            "classify",
        ],
    )
    parser.add_argument("shard_id", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "reuse-capacity":
        safe_emit(f"R435 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R435 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R435 formal seal: {prepare()}")
    elif args.command == "shards":
        safe_emit(f"R435 train shards: {shards()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        train_shard(args.shard_id)
    else:
        safe_emit(f"R435 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
