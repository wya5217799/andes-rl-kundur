"""R434 successor of R433: topology-variant evaluation of the trained SAC arms.

Owner-approved (2026-08-19, "尽量提高硬件利用率" + item-1 direction): the
R433-trained adapted-SAC arms (cd_matd3_message / cd_matd3_no_message,
seeds 401-405) are re-evaluated on the frozen R413 topology-variant bank
(12 variants; the 10 EIG-sound variants per R413/CLM-1225).  This closes
the review-risk blind spot that the constructive energy-port controller
(R413, Object B) got the N-1 variant table while the learning arms
(Object A, the paper protagonist) were only ever evaluated on the nominal
topology.  Pure evaluation: no training, no learner change, no reward
change, no tuning.

The evaluation loop is a verbatim copy of the frozen R433
``_evaluate_arm_seed_projected`` (projected deterministic actions, frozen
classifier/estimators, frozen local-neighbour deterministic reference)
with one declared seam (``R434-SEAM``): the per-profile environment is
built on the variant topology through the frozen R413 variant-env factory
(``TopologyVariantEnvV4.build_variant_env_class``; outages only through
``apply_line_outage()``, impedance only through ANDES ``Line.set``), the
eval records land under ``OUT/eval/<variant>/...``, and every record
carries its ``variant_id``.  A drift test strips the seam and asserts
byte-identity of every non-seam leaf with the frozen R433 source.

The nominal variant is the pre-registered harness-identity anchor: its
rows must reproduce the R433 eval rows exactly (same checkpoints, same
env seeds, same deterministic protocol).  The 10 evaluated variants are
frozen from the sealed R413 soundness classification (CLM-1225); the two
VSG-tie outage variants (out_Line_7_12 / out_Line_9_15) are excluded as
case-level unsound equilibria with a pointer, never re-run.

Pre-registered pause: if any SAC arm passes every guard on any variant
(0 failures in all 20 blocks), stop at the claim gate and ask the owner;
no universal-SAC or topology-generalization claim is registered without
review.  No retry is authorized by any outcome.

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py reuse-capacity
    python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py rehearse
    python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py prepare
    python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py shards
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r434_sac_topology_variants.py \
        --shards tmp/andes/r434_eval_shards.json --workers 15 --round R434
    python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py classify

Formal outputs are create-only and hashed under
``results/research_loop/r434_sac_topology_variants``.  No retry is
authorized.
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

from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)

_r433_spec = importlib.util.spec_from_file_location(
    "_r434_r433_parent", ROOT / "scripts/run_r433_sac_stress_penalty.py"
)
if _r433_spec is None or _r433_spec.loader is None:
    raise RuntimeError("cannot load the frozen R433 parent runner")
r433 = importlib.util.module_from_spec(_r433_spec)
sys.modules[_r433_spec.name] = r433
_r433_spec.loader.exec_module(r433)
base = r433.base  # the frozen R428 harness module

ROUND_ID = "R434"
PLAN = ROOT / "memory/rounds/R434/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R434/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R434/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R434/formal_seal.json"
OUT = ROOT / "results/research_loop/r434_sac_topology_variants"
R433_OUT = ROOT / "results/research_loop/r433_sac_stress_penalty"
R433_CAPACITY = ROOT / "memory/rounds/R433/capacity_evidence.json"
R413_ANALYSIS = ROOT / "results/research_loop/r413_topology_robustness/formal_analysis.json"

# Frozen from the sealed R413 soundness classification (CLM-1225,
# eig_passing_variants): the 10 EIG-sound variants of the 12-variant bank.
# The two VSG-tie outage variants are excluded as case-level unsound
# equilibria (divergent initialization, recorded gate failures) — never
# re-run, always cited.  The rehearsal's eig-soundness probe pins this
# list against the sealed R413 analysis.
EIG_SOUND_VARIANTS: tuple[str, ...] = (
    "nominal",
    "out_Line_4",
    "out_Line_5",
    "out_Line_7",
    "out_Line_8",
    "x0p5_Line_4",
    "x1p5_Line_4",
    "x0p5_Line_7",
    "x1p5_Line_7",
    "x1p5_Line_7_12",
)
EVAL_ARMS: tuple[str, ...] = ("cd_matd3_message", "cd_matd3_no_message")

_R433_BUILD_CONTRACT = r433.build_contract
_R433_SOURCE_MANIFEST = r433.source_manifest
_R433_PARENT_MANIFEST = r433.parent_manifest

# Names the verbatim copies need from the frozen chain (module globals).
for _name in (
    "PerVSGMDActionProjector",
    "SAC_MASKED_ARM",
    "_agent_for",
    "_joint_obs",
    "_deterministic_controller",
    "_read_hashed_json",
    "_write_new_json",
    "contract_sha256",
    "augment_joint_obs_np",
    "safe_emit",
    "_assert_wsl_scratch",
    "load_seal",
    "_installed_runtime",
    "_other_processes",
    "_memory_resources",
    "_relative",
    "_sha256_file",
    "random",
    "ACTION_HALF_RANGE_M",
    "ACTION_HALF_RANGE_D",
):
    globals()[_name] = getattr(r433, _name, None) or getattr(base, _name, None)


# ── frozen R413 variant machinery (lazy: Windows tests must not pull the
# ── R408/R372 energy-port chain) ───────────────────────────────────────

_r413_module: Any = None


def _variants_module() -> Any:
    """Load the frozen R413 runner once (read-only) for the variant bank."""
    global _r413_module
    if _r413_module is None:
        spec = importlib.util.spec_from_file_location(
            "_r434_r413_parent", ROOT / "scripts/run_r413_topology_robustness.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load the frozen R413 variant runner")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _r413_module = module
    return _r413_module


def variant_by_id(variant_id: str) -> dict[str, Any]:
    return _variants_module().variant_by_id(str(variant_id))


def build_variant_env_class(variant: dict[str, Any]) -> type:
    return _variants_module().TopologyVariantEnvV4.build_variant_env_class(variant)


# ── contract ────────────────────────────────────────────────────────────


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_R433_BUILD_CONTRACT())
    contract["engineering_successor"] = {
        "successor_of": "R433",
        "single_change": "topology-variant-evaluation-of-trained-sac-arms",
        "evaluation_only": True,
        "training_authorized": False,
        "eig_soundness_source": "R413/CLM-1225 (sealed case-level gate)",
        "checkpoint_source": "R433 trained arms (results/research_loop/r433_sac_stress_penalty)",
    }
    contract["topology_variant_evaluation"] = {
        "variant_ids": list(EIG_SOUND_VARIANTS),
        "evaluation_arms": list(EVAL_ARMS),
        "training_seeds": [int(seed) for seed in contract["training_seeds"]],
        "protocol": "R433-eval-verbatim (projected deterministic actions)",
        "nominal_anchor": (
            "R434-nominal rows must reproduce the R433 eval rows exactly "
            "(same checkpoints, env seeds, deterministic protocol)"
        ),
        "pause_condition": (
            "any SAC arm passes every guard on any variant -> stop, ask owner"
        ),
    }
    return contract


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R434" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and list(contract["training_seeds"]) == [401, 402, 403, 404, 405]
        and all(arm in contract["learning_arm_ids"] for arm in EVAL_ARMS)
        and len(contract["topology_variant_evaluation"]["variant_ids"]) == 10,
        "output_absence": not OUT.exists(),
    }


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _R433_SOURCE_MANIFEST()
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r434_sac_topology_variants.py",
        "parent_r433_runner": ROOT / "scripts/run_r433_sac_stress_penalty.py",
        "variant_bank_r413_runner": ROOT / "scripts/run_r413_topology_robustness.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": base._relative(path),
            "sha256": base._sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r433_plan": ROOT / "memory/rounds/R433/plan.md",
        "r433_seal": ROOT / "memory/rounds/R433/formal_seal.json",
        "r433_capacity": R433_CAPACITY,
        "r433_analysis": R433_OUT / "formal_analysis.json",
        "r413_analysis": R413_ANALYSIS,
        "r431_analysis": ROOT
        / "results/research_loop/r431_sac_slew/formal_analysis.json",
    }
    return {
        name: {"path": base._relative(path), "sha256": base._sha256_file(path)}
        for name, path in paths.items()
    }


# ── variant-aware environment builder (verbatim R428 copy + seam) ───────


def _build_env_variant(profile: dict[str, Any], variant: dict[str, Any]) -> Any:
    """R428 ``_build_env`` verbatim with the R434-SEAM env class swap: the
    environment is the frozen ``AndesMultiVSGEnvV4`` subclass that applies
    the variant mutation in ``_build_system`` (outage through
    ``apply_line_outage()``, impedance through ANDES ``Line.set``)."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # R434-SEAM
    from andes_rl_kundur.env.andes.v4_config import V4Config  # R434-SEAM

    env_class = build_variant_env_class(variant)  # R434-SEAM
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env = env_class(  # R434-SEAM
        random_disturbance=False,  # R434-SEAM
        comm_fail_prob=0.0,  # R434-SEAM
        config=V4Config(  # R434-SEAM
            vsg_m0=200.0,  # R434-SEAM
            d0_per_agent=tuple(float(value) for value in baseline_d),  # R434-SEAM
        ),  # R434-SEAM
        comm_delay_steps=0,  # R434-SEAM
    )  # R434-SEAM
    env.M0 = baseline_m.copy()
    env.D0_HETEROGENEOUS = baseline_d.copy()
    env.NEW_LOADS = {
        14: {"p0": float(profile["steady_loads"]["PQ_Bus14"]), "q0": 0.0},
        15: {"p0": float(profile["steady_loads"]["PQ_Bus15"]), "q0": 0.0},
    }
    env.seed(int(build_contract()["bank_seed"]))
    env.STEPS_PER_EPISODE = int(build_contract()["steps"])
    return env


# ── evaluation loop (verbatim R433 copy + seam) ─────────────────────────


def _evaluate_arm_seed_variant(
    arm_id: str,
    seed: int | None,
    variant_id: str,
    project: bool = True,
) -> None:
    """Eval loop — verbatim copy of the frozen R433 ``_evaluate_arm_seed_\
    projected`` (which is itself the R428 loop with the R431 projected-SAC
    seam) with the single declared R434-SEAM: the per-profile environments
    are built on the variant topology and the records land under
    ``OUT/eval/<variant_id>/...`` carrying their ``variant_id``.
    """
    contract = build_contract()
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    deterministic = seed is None
    checkpoint_sha = None
    agent = None
    if not deterministic:
        checkpoint_path = R433_OUT / "train" / arm_id / f"seed{seed}" / "final.pt"  # R434-SEAM
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"missing final checkpoint: {checkpoint_path}")
        checkpoint_sha = _sha256_file(checkpoint_path)
        agent = _agent_for(arm_id, "cpu")
        agent.load(checkpoint_path)
    controller = _deterministic_controller() if deterministic else None
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    variant = variant_by_id(variant_id)  # R434-SEAM
    envs = {  # R434-SEAM
        str(profile["profile_id"]): _build_env_variant(profile, variant)  # R434-SEAM
        for profile in evaluation  # R434-SEAM
    }  # R434-SEAM
    for profile in evaluation:
        records = []
        env = envs[str(profile["profile_id"])]
        for scenario in profile["scenarios"]:
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            projector.reset()
            previous_executed = np.zeros((4, 2), dtype=np.float32)
            if controller is not None:
                controller.reset()
            initial_frequency = (
                np.asarray(env._get_vsg_omega(), dtype=float)
                * float(contract["physical_nominal_frequency_hz"])
            ).tolist()
            identity = {
                "n_agents": int(env.N_AGENTS),
                "vsg_idx": [str(value) for value in env.vsg_idx],
                "vsg_buses": [
                    int(env.ss.GENCLS.bus.v[position])
                    for position in env._vsg_pos
                ],
                "obs_dim": int(env.OBS_DIM),
                "baseline_m0": [float(value) for value in profile["baseline_m0"]],
                "baseline_d0": [float(value) for value in profile["baseline_d0"]],
                "control_nominal_frequency_hz": float(env.FN),
                "physical_nominal_frequency_hz": float(
                    env.andes_nominal_frequency_hz
                ),
            }
            rows = []
            failure = None
            for step_index in range(int(contract["steps"])):
                if controller is not None:
                    action = controller.act(
                        adapt_v4_observations_to_physical(observation)
                    )
                else:
                    joint = _joint_obs(observation)
                    if arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
                        # R434-SEAM (inherited R433-SEAM): execution-layer
                        # slew projection on the SAC arms (R430 executed raw
                        # tanh; rows invalid).
                        if project:  # R434-SEAM
                            action = projector.project(  # R434-SEAM
                                agent.act(joint, deterministic=True)  # R434-SEAM
                            )  # R434-SEAM
                        else:  # R434-SEAM
                            action = agent.act(joint, deterministic=True)  # R434-SEAM
                    else:
                        augmented = augment_joint_obs_np(
                            joint, previous_executed
                        )
                        raw = agent.act(augmented, deterministic=True)
                        action = projector.project(raw)
                action_dict = {
                    actor: np.asarray(action[actor], dtype=np.float32)
                    for actor in range(4)
                }
                observation, _reward, done, info = env.step(action_dict)
                previous_executed = np.asarray(action, dtype=np.float32).copy()
                actual_m = np.asarray(
                    [env.ss.GENCLS.M.v[position] for position in env._vsg_pos],
                    dtype=float,
                )
                actual_d = np.asarray(
                    [env.ss.GENCLS.D.v[position] for position in env._vsg_pos],
                    dtype=float,
                )
                rows.append(
                    {
                        "step_index": step_index,
                        "time": float(info["time"]),
                        "action_norm": action.astype(float).tolist(),
                        "freq_hz_physical": np.asarray(
                            info["freq_hz_physical"], dtype=float
                        ).tolist(),
                        "M_es": actual_m.tolist(),
                        "D_es": actual_d.tolist(),
                        "delta_M": np.asarray(
                            info["delta_M"], dtype=float
                        ).tolist(),
                        "delta_D": np.asarray(
                            info["delta_D"], dtype=float
                        ).tolist(),
                        "tds_failed": bool(info["tds_failed"]),
                        "done": bool(done),
                    }
                )
                if info["tds_failed"]:
                    failure = "TDS failed"
                    break
            record = {
                "profile_id": str(profile["profile_id"]),
                "split": str(profile["split"]),
                "scenario_id": str(scenario["scenario_id"]),
                "pair_kind": str(scenario["pair_kind"]),
                "sign": str(scenario["sign"]),
                "magnitude": float(scenario["magnitude"]),
                "delta_u": dict(scenario["delta_u"]),
                "arm_id": arm_id,
                "training_seed": seed,
                "checkpoint_sha256": checkpoint_sha,
                "identity": identity,
                "initial_freq_hz_physical": initial_frequency,
                "steps": rows,
                "completed_steps": len(rows),
                "completed": failure is None
                and len(rows) == int(contract["steps"]),
                "tds_failed": failure is not None
                or any(bool(row["tds_failed"]) for row in rows),
                "failure": failure,
                "reward_used_for_gate": False,
                "training_executed": True,
            }
            record["variant_id"] = str(variant_id)  # R434-SEAM
            records.append(record)
        folder = OUT / "eval" / variant_id / arm_id / (  # R434-SEAM
            "deterministic" if deterministic else f"seed{seed}"  # R434-SEAM
        )  # R434-SEAM
        _write_new_json(
            folder / (str(profile["profile_id"]) + ".json"),
            {"records": records},
        )
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass


def adapt_v4_observations_to_physical(observation: Any) -> Any:
    return base.adapt_v4_observations_to_physical(observation)


def _evaluate_variant(variant_id: str) -> None:
    """Serial full-variant evaluation: 2 SAC arms x 5 seeds + reference."""
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    for arm_id in EVAL_ARMS:
        for seed in contract["training_seeds"]:
            _evaluate_arm_seed_variant(str(arm_id), int(seed), variant_id)
    _evaluate_arm_seed_variant(
        str(contract["deterministic_arm_id"]), None, variant_id
    )
    safe_emit(f"R434 variant evaluation complete: {variant_id}")


def evaluate_all() -> None:
    for variant_id in EIG_SOUND_VARIANTS:
        _evaluate_variant(variant_id)
    safe_emit("R434 serial evaluation complete")


def shards() -> str:
    """Write the 110-shard evaluation manifest (tmp, not a formal artifact)."""
    _assert_wsl_scratch()
    contract = build_contract()
    rows: list[str] = []
    for variant_id in EIG_SOUND_VARIANTS:
        for arm_id in EVAL_ARMS:
            for seed in contract["training_seeds"]:
                rows.append(f"eval|{arm_id}|{int(seed)}|{variant_id}")
        rows.append(
            f"eval|{contract['deterministic_arm_id']}|none|{variant_id}"
        )
    if len(rows) != 110:
        raise RuntimeError(f"unexpected shard count: {len(rows)}")
    out_path = ROOT / "tmp/andes/r434_eval_shards.json"
    out_path.write_text(
        json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return str(out_path)


# ── capacity (reuse the R433 ladder after a fresh host check) ───────────


def reuse_capacity() -> str:
    """Reuse the R433 capacity evidence (R431 rung-16 anchor chain) after a
    fresh no-other-process host check; R434 is evaluation-only so the
    budget is 16 WSL processes (15 workers + driver), reserved 0."""
    _assert_wsl_scratch()
    if CAPACITY.exists() or REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R434 pre-attempt artifact already exists")
    other = _other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    inherited = _read_hashed_json(R433_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) != 15:
        raise RuntimeError("R433 capacity evidence is not the registered 15-worker anchor")
    logical, physical_memory, wsl_available = _memory_resources()
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner approved R434 (topology-variant evaluation of the "
                "trained SAC arms, 2026-08-19 hardware-saturation order); "
                "R431/R433 rung-16 ladder reused after a fresh no-load host "
                "check; evaluation-only round, other_reserved_processes=0"
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
                "path": base._relative(R433_CAPACITY),
                "sha256": _sha256_file(R433_CAPACITY),
                "reuse_basis": (
                    "identical physical task and learner; evaluation shards "
                    "are the R433 eval protocol on variant topologies "
                    "(same per-shard RSS envelope)"
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


# ── rehearsal probes ─────────────────────────────────────────────────────


def _variant_env_probe() -> dict[str, Any]:
    """One real 30-step episode on an outage variant and an impedance
    variant through the R434 variant env, with the deterministic reference
    controller; verifies the mutation is actually applied (outaged line
    absent from ``ss.Line.idx.v``; impedance factor applied) and the TDS
    stays healthy."""
    contract = build_contract()
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    result: dict[str, Any] = {
        "passed": False,
        "outage_variant": None,
        "impedance_variant": None,
    }
    checks = {}
    nominal_env = _build_env_variant(profile, variant_by_id("nominal"))
    try:
        # Build the ANDES system (ss is lazily constructed on reset) before
        # reading the nominal line impedances.
        nominal_env.reset(
            delta_u=dict(profile["scenarios"][0]["delta_u"])
        )
        nominal_line_x = {
            str(line_idx): float(nominal_env.ss.Line.x.v[position])
            for position, line_idx in enumerate(nominal_env.ss.Line.idx.v)
        }
        for variant_id, kind in (("out_Line_4", "outage"), ("x0p5_Line_4", "impedance")):
            variant = variant_by_id(variant_id)
            env = _build_env_variant(profile, variant)
            entry: dict[str, Any] = {"kind": kind, "tds_ok": False, "applied": False}
            try:
                controller = _deterministic_controller()
                observation = env.reset(
                    delta_u=dict(profile["scenarios"][0]["delta_u"])
                )
                if controller is not None:
                    controller.reset()
                tds_failed = False
                for _ in range(30):
                    action = controller.act(
                        adapt_v4_observations_to_physical(observation)
                    )
                    action_dict = {
                        actor: np.asarray(action[actor], dtype=np.float32)
                        for actor in range(4)
                    }
                    observation, _reward, _done, info = env.step(action_dict)
                    if info["tds_failed"]:
                        tds_failed = True
                        break
                entry["tds_ok"] = not tds_failed
                line_ids = list(env.ss.Line.idx.v)
                position = line_ids.index(str(variant["line_idx"]))
                if kind == "outage":
                    # apply_line_outage() sets Line.u = 0 (never array
                    # mutation); the line stays in idx.v with status 0.
                    entry["applied"] = bool(float(env.ss.Line.u.v[position]) == 0.0)
                else:
                    entry["applied"] = bool(
                        abs(
                            float(env.ss.Line.x.v[position])
                            - float(variant["factor"]) * nominal_line_x[str(variant["line_idx"])]
                        )
                        < 1e-9
                    )
            except Exception as exc:  # noqa: BLE001
                entry["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                try:
                    env.close()
                except Exception:
                    pass
            checks[variant_id] = entry
    finally:
        try:
            nominal_env.close()
        except Exception:
            pass
    result["outage_variant"] = checks["out_Line_4"]
    result["impedance_variant"] = checks["x0p5_Line_4"]
    result["passed"] = bool(
        checks["out_Line_4"]["tds_ok"]
        and checks["out_Line_4"]["applied"]
        and checks["x0p5_Line_4"]["tds_ok"]
        and checks["x0p5_Line_4"]["applied"]
    )
    return result


def _eig_soundness_reference_probe() -> dict[str, Any]:
    """Pin EIG_SOUND_VARIANTS against the sealed R413 classification."""
    analysis = _read_hashed_json(R413_ANALYSIS)
    recorded = list(analysis.get("eig_passing_variants", []))
    expected = list(EIG_SOUND_VARIANTS)
    return {
        "passed": bool(recorded == expected),
        "expected": expected,
        "recorded_in_r413": recorded,
        "source": base._relative(R413_ANALYSIS),
    }


def _nominal_env_probe() -> dict[str, Any]:
    """The nominal variant env must be the frozen nominal construction: the
    R434 variant env on 'nominal' must expose the same identity as the
    frozen chain ``_build_env``."""
    contract = build_contract()
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    env_variant = _build_env_variant(profile, variant_by_id("nominal"))
    env_frozen = base._build_env(profile)
    result: dict[str, Any] = {"passed": False}
    try:
        # Build both ANDES systems (ss and _vsg_pos are lazily constructed
        # on reset) before reading the identities.
        env_variant.reset(delta_u=dict(profile["scenarios"][0]["delta_u"]))
        env_frozen.reset(delta_u=dict(profile["scenarios"][0]["delta_u"]))
        identity_variant = {
            "n_agents": int(env_variant.N_AGENTS),
            "vsg_idx": [str(value) for value in env_variant.vsg_idx],
            "vsg_buses": [
                int(env_variant.ss.GENCLS.bus.v[position])
                for position in env_variant._vsg_pos
            ],
            "obs_dim": int(env_variant.OBS_DIM),
        }
        identity_frozen = {
            "n_agents": int(env_frozen.N_AGENTS),
            "vsg_idx": [str(value) for value in env_frozen.vsg_idx],
            "vsg_buses": [
                int(env_frozen.ss.GENCLS.bus.v[position])
                for position in env_frozen._vsg_pos
            ],
            "obs_dim": int(env_frozen.OBS_DIM),
        }
        result["identity_variant"] = identity_variant
        result["identity_frozen"] = identity_frozen
        result["passed"] = bool(identity_variant == identity_frozen)
    finally:
        try:
            env_variant.close()
        except Exception:
            pass
        try:
            env_frozen.close()
        except Exception:
            pass
    return result


def _checkpoint_source_probe() -> dict[str, Any]:
    """The R433 trained checkpoints exist and their sidecars are consistent."""
    contract = build_contract()
    rows: dict[str, dict[str, Any]] = {}
    passed = True
    for arm_id in EVAL_ARMS:
        for seed in contract["training_seeds"]:
            path = R433_OUT / "train" / arm_id / f"seed{int(seed)}" / "final.pt"
            sidecar = Path(f"{path}.sha256")
            entry: dict[str, Any] = {"exists": path.is_file(), "sha256": None}
            if path.is_file():
                entry["sha256"] = _sha256_file(path)
                if sidecar.is_file():
                    recorded = sidecar.read_text(encoding="ascii").split()[0]
                    entry["sidecar_matches"] = bool(recorded == entry["sha256"])
                    passed = passed and entry["sidecar_matches"]
            else:
                passed = False
            rows[f"{arm_id}|{int(seed)}"] = entry
    return {
        "passed": bool(passed),
        "checkpoints": rows,
        "source": base._relative(R433_OUT / "train"),
    }


def rehearse() -> str:
    """Pre-attempt verification through the formal entry path (same
    source/parent/runtime/output guards plus the R434 probes); creates no
    formal artifact."""
    _assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R434 pre-attempt artifact exists: {candidate}")
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
        raise RuntimeError("R434 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = source_manifest()
    parents = parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    variant_probe = _variant_env_probe()
    eig_probe = _eig_soundness_reference_probe()
    nominal_probe = _nominal_env_probe()
    checkpoint_probe = _checkpoint_source_probe()
    for name, probe in (
        ("variant_env_probe", variant_probe),
        ("eig_soundness_reference_probe", eig_probe),
        ("nominal_env_probe", nominal_probe),
        ("checkpoint_source_probe", checkpoint_probe),
    ):
        checks[name] = bool(probe["passed"])
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "checks": checks,
        "variant_env_probe": variant_probe,
        "eig_soundness_reference_probe": eig_probe,
        "nominal_env_probe": nominal_probe,
        "checkpoint_source_probe": checkpoint_probe,
        "training_authorized": False,
        "evaluation_only": True,
    }
    return _write_new_json(REHEARSAL, payload)


# ── seal ─────────────────────────────────────────────────────────────────


def prepare() -> str:
    """Formal seal: evaluation-only contract, create-only artifacts, no
    retry; freezes the reused R433 capacity budget (16 WSL processes)."""
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
        raise RuntimeError("R434 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R434 capacity gate is not RUN-READY")
    if not base._plan_process_budget_matches(capacity):
        raise RuntimeError("R434 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != sources:
            raise RuntimeError("R434 source drift before seal")
        if payload["installed_runtime"] != runtime:
            raise RuntimeError("R434 runtime drift before seal")
    if rehearsal["parents"] != parents:
        raise RuntimeError("R434 parent drift before seal")
    if not all(
        rehearsal["checks"].get(name) is True
        for name in (
            "variant_env_probe",
            "eig_soundness_reference_probe",
            "nominal_env_probe",
            "checkpoint_source_probe",
        )
    ):
        raise RuntimeError("R434 rehearsal probes did not pass")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R434 formal artifact exists before sealing")
    contract = build_contract()
    r433_reference_stats = R433_OUT / "reference_action_stats.json"
    if not r433_reference_stats.is_file():
        raise FileExistsError("R433 reference_action_stats.json missing")
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
            "reference_action_stats_sha256": _sha256_file(r433_reference_stats),
            "launch": {
                "host_process_budget": 16,
                "wsl_python_processes": 16,
                "worker_processes": 15,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
            "evaluation_only_topology_variants": True,
        },
    )


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    mutable = copy.deepcopy(payload)
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "R433-verbatim evaluation protocol (projected deterministic "
            "actions, frozen classifier/estimators, frozen local-neighbour "
            "reference) applied to the trained R433 SAC arms on the 10 "
            "EIG-sound frozen topology variants of the R413 bank; nominal "
            "variant must reproduce the R433 eval rows exactly (anchor)"
        )
    if path.name == "formal_analysis.json" and path.parent.resolve() == OUT.resolve():
        mutable.setdefault("repair", {})["engineering_successor"] = {
            "successor_of": "R433",
            "evaluation_only": True,
            "topology_variant_evaluation": True,
        }
    return _write_new_json(path, mutable)


# ── classify: per-variant tables ────────────────────────────────────────


def _arm_seed_aggregate(
    summaries: list[dict[str, Any]], arm_id: str, seed: int | None
) -> dict[str, float]:
    rows = [
        row
        for row in summaries
        if row["arm_id"] == arm_id
        and (row["training_seed"] is None) == (seed is None)
        and (seed is None or int(row["training_seed"]) == seed)
    ]
    return {
        endpoint: float(sum(float(row[endpoint]) for row in rows))
        for endpoint in ("off_diagonal_response_energy", "disturbance_differential_energy")
    }


def _variant_table(
    variant_id: str,
    summaries: list[dict[str, Any]],
    contract: dict[str, Any],
    deterministic_arm: str,
) -> dict[str, Any]:
    thresholds = contract["thresholds"]
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    seeds = [int(seed) for seed in contract["training_seeds"]]
    by_key: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    for summary in summaries:
        key = (
            str(summary["profile_id"]),
            str(summary["arm_id"]),
            None if summary["training_seed"] is None else int(summary["training_seed"]),
        )
        by_key[key] = summary
    expected_keys = {
        (str(profile["profile_id"]), arm_id, seed)
        for profile in evaluation
        for arm_id in EVAL_ARMS
        for seed in seeds
    } | {
        (str(profile["profile_id"]), deterministic_arm, None)
        for profile in evaluation
    }
    complete = bool(set(by_key) == expected_keys)
    rows_valid = complete and all(
        bool(summary.get("valid")) is True
        and bool(summary.get("actuator_mapping_pass")) is True
        and bool(summary.get("action_bound_violation")) is False
        and bool(summary.get("action_slew_violation")) is False
        for summary in summaries
    )
    if not rows_valid:
        return {
            "variant_id": variant_id,
            "classification": "CANARY-INVALID",
            "complete_bank": complete,
            "all_rows_valid": rows_valid,
        }
    from andes_rl_kundur.evaluation.cd_matd3_canary import (
        _common_guard,
        _stress_guard,
    )

    maximum_common_harm = float(thresholds["maximum_common_harm"])
    maximum_stress_harm = float(thresholds["maximum_action_stress_harm"])
    maximum_saturation = float(thresholds["maximum_action_saturation_fraction"])
    variation_floor = float(thresholds["nonconstant_action_variation_floor"])
    dispersion_floor = float(thresholds["independent_action_dispersion_floor"])
    guard_failures: list[dict[str, Any]] = []
    per_block: dict[tuple[str, int, str], dict[str, bool]] = {}
    for profile in evaluation:
        reference = by_key[(str(profile["profile_id"]), deterministic_arm, None)]
        for arm_id in EVAL_ARMS:
            for seed in seeds:
                row = by_key[(str(profile["profile_id"]), arm_id, seed)]
                guard = {
                    **_common_guard(
                        row, reference, maximum_harm=maximum_common_harm
                    ),
                    **_stress_guard(
                        row, reference, maximum_harm=maximum_stress_harm
                    ),
                    "saturation_budget": float(row["action_saturation_fraction"])
                    <= maximum_saturation,
                    "nonconstant_action": float(
                        row["minimum_record_total_variation"]
                    )
                    > variation_floor,
                    "independent_per_vsg_action": float(
                        row["minimum_record_action_row_dispersion"]
                    )
                    > dispersion_floor,
                }
                per_block[(arm_id, seed, str(profile["profile_id"]))] = guard
                if not all(guard.values()):
                    guard_failures.append(
                        {
                            "profile_id": str(profile["profile_id"]),
                            "arm_id": arm_id,
                            "training_seed": seed,
                            "failed": [
                                name
                                for name, value in guard.items()
                                if not value
                            ],
                        }
                    )
    guard_names = list(next(iter(per_block.values())).keys())
    per_arm_blocks = {
        arm_id: {
            name: sum(
                1
                for (block_arm, _seed, _profile), guard in per_block.items()
                if block_arm == arm_id and not guard[name]
            )
            for name in guard_names
        }
        for arm_id in EVAL_ARMS
    }
    per_seed = {
        f"{arm_id}|{seed}": _arm_seed_aggregate(summaries, arm_id, seed)
        for arm_id in EVAL_ARMS
        for seed in seeds
    }
    deterministic = _arm_seed_aggregate(summaries, deterministic_arm, None)
    endpoints = ("off_diagonal_response_energy", "disturbance_differential_energy")
    medians = {
        arm_id: {
            endpoint: float(
                np.median([per_seed[f"{arm_id}|{seed}"][endpoint] for seed in seeds])
            )
            for endpoint in endpoints
        }
        for arm_id in EVAL_ARMS
    }
    versus_deterministic = {
        arm_id: {
            endpoint: float(medians[arm_id][endpoint] / deterministic[endpoint])
            if deterministic[endpoint] > 0.0
            else float("inf")
            for endpoint in endpoints
        }
        for arm_id in EVAL_ARMS
    }
    message_contrast = {
        endpoint: float(
            (medians["cd_matd3_no_message"][endpoint] - medians["cd_matd3_message"][endpoint])
            / medians["cd_matd3_no_message"][endpoint]
        )
        if medians["cd_matd3_no_message"][endpoint] > 0.0
        else float("inf")
        for endpoint in endpoints
    }
    any_arm_all_guards_pass = any(
        all(value == 0 for value in per_arm_blocks[arm_id].values())
        for arm_id in EVAL_ARMS
    )
    return {
        "variant_id": variant_id,
        "classification": "CANARY-PASS" if not guard_failures else "CANARY-FAIL",
        "complete_bank": True,
        "all_rows_valid": True,
        "guard_failures": guard_failures,
        "guard_block_failures_per_arm": per_arm_blocks,
        "medians": medians,
        "median_endpoint_ratio_vs_deterministic": versus_deterministic,
        "message_contrast_vs_no_message": message_contrast,
        "deterministic_endpoints": deterministic,
        "pause_condition_met": bool(any_arm_all_guards_pass),
    }


def _nominal_anchor_check(contract: dict[str, Any]) -> dict[str, Any]:
    """R434-nominal rows must reproduce the R433 eval rows exactly."""
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    deterministic_arm = str(contract["deterministic_arm_id"])
    arms = [*EVAL_ARMS, deterministic_arm]
    seeds = [int(seed) for seed in contract["training_seeds"]]
    detail: dict[str, dict[str, Any]] = {}
    passed = True
    for arm_id in arms:
        seed_tokens = [None] if arm_id == deterministic_arm else seeds
        for seed in seed_tokens:
            suffix = "deterministic" if seed is None else f"seed{seed}"
            for profile in evaluation:
                profile_id = str(profile["profile_id"])
                r433_path = R433_OUT / "eval" / arm_id / suffix / f"{profile_id}.json"
                r434_path = OUT / "eval" / "nominal" / arm_id / suffix / f"{profile_id}.json"
                key = f"{arm_id}|{suffix}|{profile_id}"
                if not r433_path.is_file() or not r434_path.is_file():
                    detail[key] = {"match": False, "reason": "missing file"}
                    passed = False
                    continue
                p433 = _read_hashed_json(r433_path)
                p434 = _read_hashed_json(r434_path)
                rec433 = p433["records"]
                rec434 = p434["records"]
                if len(rec433) != len(rec434):
                    detail[key] = {"match": False, "reason": "record count"}
                    passed = False
                    continue
                match = all(
                    a["steps"] == b["steps"] for a, b in zip(rec433, rec434)
                )
                detail[key] = {"match": bool(match)}
                passed = passed and match
    return {
        "passed": bool(passed),
        "compare_source": "R433 eval records (results/research_loop/r433_sac_stress_penalty/eval)",
        "per_arm_seed_profile": detail,
    }


def _checkpoint_consistency_check(contract: dict[str, Any]) -> dict[str, Any]:
    """Every variant's eval records for an (arm, seed) must reference the
    same checkpoint sha256, equal to the R433 final.pt sidecar."""
    deterministic_arm = str(contract["deterministic_arm_id"])
    seeds = [int(seed) for seed in contract["training_seeds"]]
    rows: dict[str, dict[str, Any]] = {}
    passed = True
    for arm_id in EVAL_ARMS:
        for seed in seeds:
            shas = set()
            for variant_id in EIG_SOUND_VARIANTS:
                folder = OUT / "eval" / variant_id / arm_id / f"seed{seed}"
                for profile_json in sorted(folder.glob("*.json")):
                    payload = _read_hashed_json(profile_json)
                    for record in payload["records"]:
                        if record.get("checkpoint_sha256") is not None:
                            shas.add(str(record["checkpoint_sha256"]))
            sidecar = (
                R433_OUT / "train" / arm_id / f"seed{seed}" / "final.pt.sha256"
            )
            expected = None
            if sidecar.is_file():
                expected = sidecar.read_text(encoding="ascii").split()[0]
            consistent = bool(len(shas) == 1 and shas == {expected})
            passed = passed and consistent
            rows[f"{arm_id}|{seed}"] = {
                "checkpoint_shas_in_records": sorted(shas),
                "r433_sidecar_sha": expected,
                "consistent": consistent,
            }
    return {"passed": bool(passed), "per_arm_seed": rows}


def classify() -> str:
    """Per-variant formal analysis: guard blocks, endpoints, message
    contrast per EIG-sound variant; the nominal anchor against R433; the
    cross-variant message-arm readout."""
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    deterministic_arm = str(contract["deterministic_arm_id"])
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    seeds = [int(seed) for seed in contract["training_seeds"]]
    variant_tables: dict[str, dict[str, Any]] = {}
    for variant_id in EIG_SOUND_VARIANTS:
        summaries: list[dict[str, Any]] = []
        for arm_id in EVAL_ARMS:
            for seed in seeds:
                for profile in evaluation:
                    path = (
                        OUT
                        / "eval"
                        / variant_id
                        / arm_id
                        / f"seed{seed}"
                        / (str(profile["profile_id"]) + ".json")
                    )
                    payload = _read_hashed_json(path)
                    summary = summarise_profile(payload["records"], contract=contract)
                    summary["arm_id"] = str(arm_id)
                    summary["training_seed"] = int(seed)
                    summaries.append(summary)
        for profile in evaluation:
            path = (
                OUT
                / "eval"
                / variant_id
                / deterministic_arm
                / "deterministic"
                / (str(profile["profile_id"]) + ".json")
            )
            payload = _read_hashed_json(path)
            summary = summarise_profile(payload["records"], contract=contract)
            summary["arm_id"] = str(deterministic_arm)
            summary["training_seed"] = None
            summaries.append(summary)
        variant_tables[variant_id] = _variant_table(
            variant_id, summaries, contract, deterministic_arm
        )
    nominal_anchor = _nominal_anchor_check(contract)
    checkpoint_consistency = _checkpoint_consistency_check(contract)
    guard_names = (
        "common_frequency_no_harm",
        "worst_peak_no_harm",
        "rocof_no_harm",
        "action_rms_no_harm",
        "action_variation_no_harm",
        "saturation_budget",
        "nonconstant_action",
        "independent_per_vsg_action",
    )
    cross_variant = {
        arm_id: {
            name: sum(
                1
                for table in variant_tables.values()
                if table.get("classification") == "CANARY-FAIL"
                and table.get("guard_block_failures_per_arm", {}).get(arm_id, {}).get(name, 0)
                == 0
            )
            for name in guard_names
        }
        for arm_id in EVAL_ARMS
    }
    pause_variants = [
        variant_id
        for variant_id, table in variant_tables.items()
        if table.get("pause_condition_met")
    ]
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": str(contract["manuscript_line"]),
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "bank": {
            "variant_count": len(EIG_SOUND_VARIANTS),
            "eig_soundness_source": "R413/CLM-1225 (sealed case-level gate; "
            "out_Line_7_12 / out_Line_9_15 excluded as unsound equilibria)",
            "checkpoint_source": "R433 trained arms",
            "arms": list(EVAL_ARMS),
            "seeds": seeds,
            "evaluation_profiles": [str(profile["profile_id"]) for profile in evaluation],
        },
        "variants": variant_tables,
        "cross_variant_block_failures": cross_variant,
        "pause_variants": pause_variants,
        "pause_condition_met": bool(pause_variants),
        "nominal_anchor_matches_r433": nominal_anchor,
        "checkpoint_sha_consistent_with_r433": checkpoint_consistency,
        "reward_used_for_gate": False,
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
            for path in sorted(R433_OUT.rglob("train/*/*/final.pt"))
        ],
        "evaluation_records": len(variant_tables)
        * (len(EVAL_ARMS) * len(seeds) + 1)
        * len(evaluation),
        "pause_condition_met": bool(pause_variants),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


# ── bindings and CLI ────────────────────────────────────────────────────


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
    for module in (r433, base):
        for name, value in values.items():
            setattr(module, name, value)
    for module in (r433, base):
        module.build_contract = build_contract
        module._source_manifest = source_manifest
        module._parent_manifest = parent_manifest
        module._authority_checks = authority_checks
        module._write_new_json = write_new_json
    base.OTHER_RESERVED_PROCESSES = 0


_patch_parent()


def _parse_shard(shard_id: str) -> tuple[str, str, int | None, str]:
    parts = shard_id.split("|")
    if len(parts) != 4 or parts[0] != "eval":
        raise ValueError(
            "shard id must be eval|<arm>|<seed|none>|<variant>"
        )
    _phase, arm_id, seed_token, variant_id = parts
    known_arms = set(EVAL_ARMS) | {str(build_contract()["deterministic_arm_id"])}
    if arm_id not in known_arms:
        raise ValueError(f"unknown shard arm: {arm_id}")
    if variant_id not in EIG_SOUND_VARIANTS:
        raise ValueError(f"unknown shard variant: {variant_id}")
    seed = None if seed_token == "none" else int(seed_token)
    return "eval", arm_id, seed, variant_id


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
            "evaluate",
            "classify",
        ],
    )
    parser.add_argument("shard_id", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "reuse-capacity":
        safe_emit(f"R434 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R434 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R434 formal seal: {prepare()}")
    elif args.command == "shards":
        safe_emit(f"R434 eval shards: {shards()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        _phase, arm_id, seed, variant_id = _parse_shard(args.shard_id)
        _evaluate_arm_seed_variant(arm_id, seed, variant_id, project=True)
        safe_emit(f"R434 evaluation shard complete: {args.shard_id}")
    elif args.command == "evaluate":
        evaluate_all()
    else:
        safe_emit(f"R434 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
