"""Sealed WSL runner for R405: linearization + candidate-A disclosed gate.

Loads the frozen R405 contract, snapshots and folds the ANDES DAE Jacobians
at the eight canary profile operating points, evaluates the zero-action,
km2_kd2 reference, and candidate-A homogenization arms on all 48 disclosed
scenarios, aggregates through the frozen estimator and decision tree, and
writes create-only formal artifacts with sha256 sidecars under
results/research_loop/r405_homogenization_gate/.

--rehearse exercises the same pre-attempt verification path as --execute
(source hashes, installed runtime, output absence, contract closure) on one
representative profile and one scenario, and creates no formal artifact.
--measure-capacity runs the R339+ worker ladder and writes the capacity
evidence payload to memory/rounds/R405/capacity_evidence.json.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
try:
    import resource  # POSIX-only; used only by the WSL capacity ladder
except ImportError:  # pragma: no cover - Windows host
    resource = None
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    LocalNeighbourMDExecution,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)
from andes_rl_kundur.evaluation.r405_homogenization_gate import (  # noqa: E402
    CANDIDATE_ARM,
    REFERENCE_ARM,
    build_contract,
    classify_r405,
    compute_gate_payload,
    contract_sha256,
)
from andes_rl_kundur.evaluation.r405_linearization import (  # noqa: E402
    load_input_columns,
    snapshot_profile_jacobians,
    try_extract_reduced_l,
)
from probes.homogenization_linearization import (  # noqa: E402
    homogenization_targets,
    homogenized_action_schedule,
    leading_cross_moments,
)

ROUND_ID = "R405"
PLAN = ROOT / "memory/rounds/R405/plan.md"
SEAL = ROOT / "memory/rounds/R401/formal_seal.json"
OUT = ROOT / "results/research_loop/r405_homogenization_gate"
CAPACITY_OUT = ROOT / "memory/rounds/R405/capacity_evidence.json"

LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
EPS_STEPS = (1.0e-4, 1.0e-5)
REHEARSE_PROFILE = "canary_dev_a"
REHEARSE_SCENARIO = "canary_dev_a_common_positive"


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"formal artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}\n", encoding="utf-8")
    return digest


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _source_manifest() -> dict[str, dict[str, str]]:
    paths = [
        ROOT / "probes/homogenization_linearization.py",
        ROOT / "src/andes_rl_kundur/evaluation/r405_homogenization_gate.py",
        ROOT / "src/andes_rl_kundur/evaluation/r405_linearization.py",
        ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
    ]
    manifest: dict[str, dict[str, str]] = {}
    for path in paths:
        manifest[_relative(path)] = {"sha256": _sha256_file(path)}
    return manifest


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _pre_attempt_checks(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_closed": bool(contract["round"] == ROUND_ID),
        "contract_sha256": contract_sha256(contract),
        "parent_seal_sha256": _sha256_file(SEAL),
        "source_manifest": _source_manifest(),
        "installed_runtime": _installed_runtime(),
        "output_absence": not OUT.exists(),
    }


def _profile_by_id(contract: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    for profile in contract["profiles"]:
        if str(profile["profile_id"]) == profile_id:
            return profile
    raise ValueError(f"unknown profile: {profile_id}")


def _build_env(profile: Mapping[str, Any]) -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=V4Config(
            vsg_m0=200.0,
            d0_per_agent=tuple(float(value) for value in baseline_d),
        ),
        comm_delay_steps=0,
    )
    env.M0 = baseline_m.copy()
    env.D0_HETEROGENEOUS = baseline_d.copy()
    env.NEW_LOADS = {
        14: {"p0": float(profile["steady_loads"]["PQ_Bus14"]), "q0": 0.0},
        15: {"p0": float(profile["steady_loads"]["PQ_Bus15"]), "q0": 0.0},
    }
    env.seed(int(_load_json(SEAL)["contract"]["bank_seed"]))
    env.STEPS_PER_EPISODE = int(build_contract()["steps"])
    return env


def _deterministic_controller() -> LocalNeighbourMDExecution:
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    return LocalNeighbourMDExecution(contracts[REFERENCE_ARM])


def _candidate_a_schedule(profile: Mapping[str, Any], steps: int) -> np.ndarray:
    targets = homogenization_targets(
        [float(v) for v in profile["baseline_m0"]],
        [float(v) for v in profile["baseline_d0"]],
    )
    if not targets.reachable:
        raise ValueError(f"homogenization infeasible for {profile['profile_id']}")
    return homogenized_action_schedule(targets.normalized_targets, steps=steps)


def _record(
    *,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    arm_id: str,
    identity: Mapping[str, Any],
    rows: list[dict[str, Any]],
    completed: bool,
    tds_failed: bool,
    initial_frequency: list[float],
) -> dict[str, Any]:
    return {
        "profile_id": str(profile["profile_id"]),
        "arm_id": arm_id,
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "completed": completed,
        "tds_failed": tds_failed,
        "initial_freq_hz_physical": initial_frequency,
        "identity": identity,
        "steps": rows,
    }


def _run_scenario(
    env: Any,
    *,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    arm_id: str,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    observation = env.reset(delta_u=dict(scenario["delta_u"]))
    controller = _deterministic_controller() if arm_id == REFERENCE_ARM else None
    schedule = (
        _candidate_a_schedule(profile, int(contract["steps"]))
        if arm_id == CANDIDATE_ARM
        else None
    )
    initial_frequency = (
        np.asarray(env._get_vsg_omega(), dtype=float)
        * float(contract["physical_nominal_frequency_hz"])
    ).tolist()
    identity = {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[pos]) for pos in env._vsg_pos],
        "obs_dim": int(env.OBS_DIM),
        "baseline_m0": [float(value) for value in profile["baseline_m0"]],
        "baseline_d0": [float(value) for value in profile["baseline_d0"]],
        "control_nominal_frequency_hz": float(env.FN),
        "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }
    rows: list[dict[str, Any]] = []
    tds_failed = False
    for step_index in range(int(contract["steps"])):
        if arm_id == REFERENCE_ARM:
            action = controller.act(adapt_v4_observations_to_physical(observation))
        elif arm_id == CANDIDATE_ARM:
            # The offline schedule is slew-safe and inside the box by
            # construction, so it is behaviorally equivalent to passing each
            # target through LocalMDActionProjector; the estimator's mapping
            # check validates the executed decode either way.
            action = schedule[step_index]
        else:
            action = np.zeros((4, 2), dtype=np.float32)
        action_dict = {actor: np.asarray(action[actor], dtype=np.float32) for actor in range(4)}
        observation, _reward, done, info = env.step(action_dict)
        actual_m = np.asarray(
            [env.ss.GENCLS.M.v[pos] for pos in env._vsg_pos], dtype=float
        )
        actual_d = np.asarray(
            [env.ss.GENCLS.D.v[pos] for pos in env._vsg_pos], dtype=float
        )
        tds_failed = tds_failed or bool(info["tds_failed"])
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
                "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
                "tds_failed": bool(info["tds_failed"]),
                "done": bool(done),
            }
        )
    return _record(
        profile=profile,
        scenario=scenario,
        arm_id=arm_id,
        identity=identity,
        rows=rows,
        completed=True,
        tds_failed=tds_failed,
        initial_frequency=initial_frequency,
    )


def _linearize_all(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    payloads = []
    for profile in contract["profiles"]:
        env = _build_env(profile)
        env.reset()
        snapshot = snapshot_profile_jacobians(env, str(profile["profile_id"]))
        input_columns = load_input_columns(
            env,
            perturbed_env_factory=lambda p=profile: _build_env(p),
            load_ids=LOAD_IDS,
            eps_steps=EPS_STEPS,
        )
        l_attempt = try_extract_reduced_l(env)
        targets = homogenization_targets(
            [float(v) for v in profile["baseline_m0"]],
            [float(v) for v in profile["baseline_d0"]],
        )
        moments = {
            "baseline": leading_cross_moments(
                [float(v) for v in profile["baseline_m0"]],
                [float(v) for v in profile["baseline_d0"]],
            ),
            "homogenized": (
                leading_cross_moments([targets.m_star] * 4, [targets.d_star] * 4)
                if targets.reachable
                else None
            ),
        }
        payloads.append(
            {
                "profile_id": str(profile["profile_id"]),
                "snapshot": snapshot,
                "input_columns": input_columns,
                "reduced_l": l_attempt,
                "cross_moments": moments,
            }
        )
    return payloads


def _evaluate_all(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for profile in contract["profiles"]:
        for arm_id in contract["arms"]:
            env = _build_env(profile)
            for scenario in profile["scenarios"]:
                records.append(
                    _run_scenario(
                        env, profile=profile, scenario=scenario, arm_id=arm_id,
                        contract=contract,
                    )
                )
    return records


def _summaries_from_records(
    records: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, dict[str, dict[str, Any]]]:
    summaries: dict[str, dict[str, dict[str, Any]]] = {}
    for profile in contract["profiles"]:
        pid = str(profile["profile_id"])
        for arm_id in contract["arms"]:
            block = [
                r for r in records
                if str(r["profile_id"]) == pid and str(r["arm_id"]) == arm_id
            ]
            summary = summarise_profile(block, contract=contract)
            summaries.setdefault(arm_id, {})[pid] = summary
    return summaries




def archive_matrices() -> str:
    """Supplement: archive the per-profile linearization matrices (A-3)."""
    from andes_rl_kundur.evaluation.r405_linearization import dense_matrix

    contract = build_contract()
    if not OUT.exists():
        raise FileExistsError("execute must run before --archive-matrices")
    matrix_path = OUT / "linearization_matrices.json"
    payload: dict[str, Any] = {"round": ROUND_ID, "profiles": {}}
    for profile in contract["profiles"]:
        env = _build_env(profile)
        env.reset()
        system = env.ss
        models = system.exist.pflow_tds
        system.TDS.fg_update(models=models)
        system.j_update(models=models, info="R405 matrix archive")
        fx = dense_matrix(system.dae.fx)
        fy = dense_matrix(system.dae.fy)
        gx = dense_matrix(system.dae.gx)
        gy = dense_matrix(system.dae.gy)
        payload["profiles"][str(profile["profile_id"])] = {
            "f_x": fx.tolist(),
            "f_y": fy.tolist(),
            "g_x": gx.tolist(),
            "g_y": gy.tolist(),
            "x0": np.asarray(system.dae.x, dtype=float).tolist(),
            "y0": np.asarray(system.dae.y, dtype=float).tolist(),
            "baseline_m0": [float(v) for v in profile["baseline_m0"]],
            "baseline_d0": [float(v) for v in profile["baseline_d0"]],
        }
    digest = _write_new_json(matrix_path, payload)
    return json.dumps(
        {"round": ROUND_ID, "matrix_archive_sha256": digest, "path": _relative(matrix_path)},
        indent=2,
        sort_keys=True,
    )


def rehearse() -> str:
    contract = build_contract()
    checks = _pre_attempt_checks(contract)
    profile = _profile_by_id(contract, REHEARSE_PROFILE)
    scenario = next(
        s for s in profile["scenarios"] if s["scenario_id"] == REHEARSE_SCENARIO
    )
    env = _build_env(profile)
    env.reset()
    snapshot = snapshot_profile_jacobians(env, REHEARSE_PROFILE)
    input_columns = load_input_columns(
        env,
        perturbed_env_factory=lambda: _build_env(profile),
        load_ids=(LOAD_IDS[0],),
        eps_steps=(1e-4,),
    )
    l_attempt = try_extract_reduced_l(env)
    record = _run_scenario(
        env, profile=profile, scenario=scenario, arm_id=CANDIDATE_ARM,
        contract=contract,
    )
    payload = {
        "rehearsal": True,
        "pre_attempt": {
            "contract_closed": checks["contract_closed"],
            "output_absence": checks["output_absence"],
            "parent_seal_sha256": checks["parent_seal_sha256"],
            "source_files": len(checks["source_manifest"]),
        },
        "snapshot": snapshot,
        "input_columns_rehearsed": {
            "load_id": LOAD_IDS[0],
            "final_column_finite": input_columns[LOAD_IDS[0]]["final_column_finite"],
        },
        "reduced_l": l_attempt,
        "scenario": {
            "completed": record["completed"],
            "tds_failed": record["tds_failed"],
            "rows": len(record["steps"]),
            "final_M_es": record["steps"][-1]["M_es"],
            "final_D_es": record["steps"][-1]["D_es"],
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _capacity_job(job_id: int) -> dict[str, Any]:
    contract = build_contract()
    profile = contract["profiles"][job_id % len(contract["profiles"])]
    env = _build_env(profile)
    env.reset()
    snapshot_profile_jacobians(env, str(profile["profile_id"]))
    scenario = profile["scenarios"][0]
    _run_scenario(
        env, profile=profile, scenario=scenario, arm_id=CANDIDATE_ARM,
        contract=contract,
    )
    return {"job_id": job_id, "ok": True}


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in (1, 2, 4):
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers)))
        wall = time.monotonic() - start
        rss_kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(len(results) / max(wall, 1e-9), 4),
                "children_max_rss_kb": int(rss_kb),
            }
        )
    payload["measured_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return json.dumps(payload, indent=2, sort_keys=True)


def execute() -> str:
    contract = build_contract()
    checks = _pre_attempt_checks(contract)
    if not checks["output_absence"]:
        raise FileExistsError("formal output root already exists")
    if not checks["contract_closed"]:
        raise ValueError("contract not closed")

    attempt_payload = {
        "round": ROUND_ID,
        "pre_attempt": {
            "contract_sha256": checks["contract_sha256"],
            "parent_seal_sha256": checks["parent_seal_sha256"],
            "source_manifest": checks["source_manifest"],
            "installed_runtime": checks["installed_runtime"],
        },
        "contract": contract,
    }
    attempt_digest = _write_new_json(OUT / "formal_attempt.json", attempt_payload)

    linearizations = _linearize_all(contract)
    records = _evaluate_all(contract)
    summaries = _summaries_from_records(records, contract)
    payload = compute_gate_payload(summaries, contract=contract)
    decision = classify_r405(payload)

    execution_payload = {
        "round": ROUND_ID,
        "record_count": len(records),
        "linearization_count": len(linearizations),
        "linearizations": linearizations,
        "records": records,
    }
    execution_digest = _write_new_json(OUT / "formal_execution.json", execution_payload)

    analysis_payload = {
        "round": ROUND_ID,
        "attempt_sha256": attempt_digest,
        "execution_sha256": execution_digest,
        "payload": payload,
        "classification": decision["classification"],
        "reasons": decision["reasons"],
        "summaries": summaries,
        "training_authorized": False,
    }
    analysis_digest = _write_new_json(OUT / "formal_analysis.json", analysis_payload)

    manifest_payload = {
        "round": ROUND_ID,
        "entries": [
            {"path": _relative(OUT / "formal_attempt.json"), "sha256": attempt_digest},
            {"path": _relative(OUT / "formal_execution.json"), "sha256": execution_digest},
            {"path": _relative(OUT / "formal_analysis.json"), "sha256": analysis_digest},
        ],
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return json.dumps(
        {
            "classification": decision["classification"],
            "reasons": decision["reasons"],
            "endpoints": payload["endpoints"],
            "guard_ratios": payload["guard_ratios"],
            "record_count": len(records),
            "linearization_count": len(linearizations),
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rehearse", action="store_true", help="same pre-attempt path, no formal outputs")
    group.add_argument("--measure-capacity", action="store_true", help="R339+ worker ladder")
    group.add_argument("--execute", action="store_true", help="create the formal attempt")
    group.add_argument("--archive-matrices", action="store_true", help="A-3 supplement: archive linearization matrices")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.rehearse:
        safe_emit(rehearse())
        return 0
    if args.archive_matrices:
        safe_emit(archive_matrices())
        return 0
    if args.measure_capacity:
        payload = json.loads(measure_capacity())
        CAPACITY_OUT.parent.mkdir(parents=True, exist_ok=True)
        with CAPACITY_OUT.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    safe_emit(execute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())