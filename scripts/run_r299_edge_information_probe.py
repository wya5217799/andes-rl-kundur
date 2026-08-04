#!/usr/bin/env python3
"""Run R299's sealed edge-local information-value sentinel.

The outcome oracle is diagnostic only.  It selects from a frozen finite
library after seeing each complete trajectory and therefore cannot be treated
as a deployable controller or efficacy result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_r294_fast_controller_development as development  # noqa: E402
import run_r296_relative_rocof_probe as residual  # noqa: E402
import run_r297_relative_rocof_amplitude as selection  # noqa: E402
from andes_rl_kundur.control.edge_relative_rocof_residual import (  # noqa: E402
    DecentralizedEdgeSelectiveRelativeRoCoFExecution,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R299"
QUESTION_ID = "Q-0056"
STAGE = "edge_local_information_value_sentinel"
SHARD_COUNT = 3
FULL_GAIN = selection.FULL_GAIN
FILTER_TAU_S = residual.FILTER_TAU_S
EDGES = ((0, 1), (1, 2), (2, 3), (0, 3))
BASELINE_ARM = "edge_gain__base_kv"
ALL_EDGE_ARM = "edge_gain__all_extra_kv"
PRIOR_SEAL = ROOT / "memory/rounds/R299/edge_information_seal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R299/edge_information_seal_v2.json"
DEFAULT_OUT = ROOT / "results/r299_edge_information_probe"
R298_SUMMARY = ROOT / "results/r298_relative_rocof_formal/formal_summary.json"
CONTROLLER_SOURCE = (
    ROOT / "src/andes_rl_kundur/control/edge_relative_rocof_residual.py"
)
COMMON_ENDPOINTS = development.COMMON_ENDPOINTS
DIFFERENTIAL_ENDPOINTS = development.DIFFERENTIAL_ENDPOINTS
THRESHOLDS = {
    "common_individual_ratio_max": 1.05,
    "adaptive_fast_ratio_max": 0.99,
    "adaptive_sync_ratio_max": 0.99,
    "fixed_fast_material_ratio_max": 0.99,
    "fixed_sync_no_harm_ratio_max": 1.0,
    "minimum_distinct_nonbaseline_oracle_arms": 2,
    "local_spearman_min": 0.5,
    "local_best_edge_match_min": 3,
    "residual_sum_abs_max_system_pu": 1e-12,
    "causal_feature_steps": 5,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact exists: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = sha256_file(path)
    if expected != observed:
        raise RuntimeError(f"hash mismatch for {path}: {expected} != {observed}")
    return observed


def _source_entry(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def scenario_bank() -> list[dict[str, Any]]:
    return [
        {"name": "k1.25__pq_0__neg", "tie_k": 1.25, "location": "PQ_0", "delta_u": -1.0},
        {"name": "k1.25__pq_1__pos", "tie_k": 1.25, "location": "PQ_1", "delta_u": 1.0},
        {"name": "k1.75__pq_bus15__neg", "tie_k": 1.75, "location": "PQ_Bus15", "delta_u": -1.0},
        {"name": "k1.75__pq_0__pos", "tie_k": 1.75, "location": "PQ_0", "delta_u": 1.0},
    ]


def formal_eval_bank() -> list[dict[str, Any]]:
    rows = []
    for tie_k in (1.375, 1.625):
        for location in ("PQ_0", "PQ_Bus14", "PQ_Bus15"):
            for delta_u in (-1.0, 1.0):
                rows.append(
                    {
                        "name": f"k{tie_k:g}__{location.lower()}__{'pos' if delta_u > 0 else 'neg'}",
                        "tie_k": tie_k,
                        "location": location,
                        "delta_u": delta_u,
                    }
                )
    return rows


def _edge_name(edge: tuple[int, int]) -> str:
    return f"edge_gain__e{edge[0]}{edge[1]}_extra_kv"


def arm_bank() -> list[dict[str, Any]]:
    common = {
        "architecture": "explicit_local_edge_residual",
        "execution": "four_local_dapi_agents_with_neighbour_edge_channels",
        "sync_gain": 1.0,
        "consensus_gain": 1.0,
        "relative_rocof_gain": FULL_GAIN,
    }
    return [
        {**common, "name": BASELINE_ARM, "extra_edges": []},
        {**common, "name": ALL_EDGE_ARM, "extra_edges": [list(edge) for edge in EDGES]},
        *[
            {**common, "name": _edge_name(edge), "extra_edges": [list(edge)]}
            for edge in EDGES
        ],
    ]


def job_bank() -> list[dict[str, Any]]:
    return [
        {
            "order": index,
            "name": f"{scenario['name']}__{arm['name']}",
            "scenario": scenario,
            "arm": arm,
        }
        for index, (scenario, arm) in enumerate(
            (pair for scenario in scenario_bank() for pair in ((scenario, arm) for arm in arm_bank()))
        )
    ]


def _seal_payload() -> dict[str, Any]:
    _verify_sidecar(R298_SUMMARY)
    _verify_sidecar(PRIOR_SEAL)
    summary = json.loads(R298_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("classification") != "VALID-RELATIVE-ROCOF-PASS":
        raise RuntimeError("CLM-0700 formal baseline is not valid")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "outcome_oracle_non_deployable": True,
        "execution_amendment": {
            "supersedes_seal": _source_entry(PRIOR_SEAL),
            "reason": (
                "pre-trace smoke exposed missing explicit sync/consensus arm "
                "metadata required by the reused execution adapter; controller, "
                "matrix, estimand, thresholds, and future bank are unchanged"
            ),
            "retained_trace_count_before_amendment": 0,
        },
        "steps": development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "base_relative_rocof_gain_system_pu_s_per_hz": FULL_GAIN,
        "extra_edge_gain_system_pu_s_per_hz": FULL_GAIN,
        "edges": [list(edge) for edge in EDGES],
        "thresholds": THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "predeclared_disjoint_formal_eval_bank": formal_eval_bank(),
        "estimand": (
            "development-only optimistic edge-allocation headroom over the best "
            "fixed arm, plus association between causal edge-local features and "
            "counterfactual single-edge benefit"
        ),
        "comparison_identifiability": {
            "fixed_arms": "ALLOW; edge-gain placement is the sole treatment",
            "outcome_oracle": "QUALIFY; future-outcome upper bound only",
            "architecture_or_neural": "BLOCK",
        },
        "claim_boundary": (
            "fixed-topology development diagnosis only; no deployable efficacy, "
            "MARL, neural, pure-architecture, topology, stability, safety, "
            "robustness, EMT-HIL, or deployment claim"
        ),
        "prior_evidence": {"r298_formal_summary": _source_entry(R298_SUMMARY)},
        "sources": {
            "runner": _source_entry(Path(__file__).resolve()),
            "controller": _source_entry(CONTROLLER_SOURCE),
            "base_controller": _source_entry(residual.CONTROLLER_SOURCE),
            "execution_runner": _source_entry(Path(development.__file__).resolve()),
            "fast_endpoints": _source_entry(residual.FAST_ENDPOINT_SOURCE),
        },
    }


class RecordingEdgeController(DecentralizedEdgeSelectiveRelativeRoCoFExecution):
    """Edge controller with conclusion-bearing mechanism telemetry."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.mechanism_trace: list[dict[str, Any]] = []

    def act(self, **kwargs: Any) -> np.ndarray:
        request = super().act(**kwargs)
        total_residual = (
            self.last_residual_requests_system_pu
            + self.last_extra_requests_system_pu
        )
        count = math.sqrt(self.device_count)
        self.mechanism_trace.append(
            {
                "base_relative_residual_rms_system_pu": float(
                    np.linalg.norm(self.last_residual_requests_system_pu) / count
                ),
                "extra_edge_residual_rms_system_pu": float(
                    np.linalg.norm(self.last_extra_requests_system_pu) / count
                ),
                "total_residual_rms_system_pu": float(
                    np.linalg.norm(total_residual) / count
                ),
                "total_residual_sum_system_pu": float(np.sum(total_residual)),
                "extra_residual_sum_system_pu": float(
                    np.sum(self.last_extra_requests_system_pu)
                ),
                "filtered_rocof_hz_s": self.last_filtered_rocof_hz_s.tolist(),
                "extra_edge_flows_system_pu": {
                    f"{edge[0]}-{edge[1]}": float(value)
                    for edge, value in self.last_extra_edge_flows_system_pu.items()
                },
            }
        )
        return request


_LAST_CONTROLLER: RecordingEdgeController | None = None


def _controller(arm: dict[str, Any], *, device_count: int, nominal_hz: float):
    global _LAST_CONTROLLER
    extra = {
        tuple(int(value) for value in edge): FULL_GAIN
        for edge in arm["extra_edges"]
    }
    _LAST_CONTROLLER = RecordingEdgeController(
        adjacency=development.COMM_ADJ,
        device_count=device_count,
        nominal_frequency_hz=nominal_hz,
        kp_system_pu_per_hz_per_device=development.KP,
        ki_system_pu_per_hz_s_per_device=development.KI,
        sync_gain_system_pu_per_hz=1.0,
        consensus_gain_per_s=1.0,
        rocof_filter_time_constant_s=FILTER_TAU_S,
        relative_rocof_gain_system_pu_s_per_hz=FULL_GAIN,
        extra_edge_gains_system_pu_s_per_hz=extra,
    )
    return _LAST_CONTROLLER


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    global _LAST_CONTROLLER
    original = (
        development._controller,
        development.ROUND_ID,
        development.QUESTION_ID,
        development.STAGE,
    )
    _LAST_CONTROLLER = None
    try:
        development._controller = _controller
        development.ROUND_ID = ROUND_ID
        development.QUESTION_ID = QUESTION_ID
        development.STAGE = STAGE
        record = development._run_job(job, seal_hash)
        record["controller_config"] = {
            "architecture": DecentralizedEdgeSelectiveRelativeRoCoFExecution.architecture,
            "base_relative_rocof_gain_system_pu_s_per_hz": FULL_GAIN,
            "extra_edge_gain_system_pu_s_per_hz": FULL_GAIN,
            "extra_edges": job["arm"]["extra_edges"],
            "kp": development.KP,
            "ki": development.KI,
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "rocof_filter_time_constant_s": FILTER_TAU_S,
        }
        record["mechanism_trace"] = (
            list(_LAST_CONTROLLER.mechanism_trace)
            if _LAST_CONTROLLER is not None
            else []
        )
        return record
    finally:
        (
            development._controller,
            development.ROUND_ID,
            development.QUESTION_ID,
            development.STAGE,
        ) = original
        _LAST_CONTROLLER = None


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(
        f"scenarios={len(payload['scenarios'])} arms={len(payload['arms'])} "
        f"jobs={len(payload['jobs'])}"
    )


def _verify_seal(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(path.read_text(encoding="utf-8"))
    for group in ("sources", "prior_evidence"):
        for name, entry in seal[group].items():
            if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
                raise RuntimeError(f"sealed source drift for {group}.{name}")
    return seal


def smoke(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    job = next(item for item in seal["jobs"] if item["arm"]["name"] == _edge_name((0, 1)))
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    trace = record.get("mechanism_trace", [])
    zero_sum = max(abs(row["total_residual_sum_system_pu"]) for row in trace)
    if (
        record["guards"]["completed"] is not True
        or len(trace) != development.STEPS
        or zero_sum > THRESHOLDS["residual_sum_abs_max_system_pu"]
    ):
        raise RuntimeError(f"retained smoke failed: {path}")
    print(
        f"smoke_pass=True steps={record['n_steps']} "
        f"zero_sum_max={zero_sum:.3e} wall={record['runtime']['wall_clock_seconds']:.2f}s"
    )


def run_shard(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    if shard_count != int(seal["shard_count"]):
        raise RuntimeError("runtime shard count differs from seal")
    jobs = [job for job in seal["jobs"] if int(job["order"]) % shard_count == shard_index]
    for position, job in enumerate(jobs, start=1):
        path = out_dir / "records" / f"{job['name']}.json"
        if path.exists():
            _verify_sidecar(path)
            print(f"[{position}/{len(jobs)}] verified_existing={job['name']}", flush=True)
            continue
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
        print(
            f"[{position}/{len(jobs)}] job={job['name']} "
            f"completed={record['guards']['completed']} "
            f"wall={record['runtime']['wall_clock_seconds']:.2f}s",
            flush=True,
        )


def _safe_ratio(value: float, reference: float) -> float:
    if math.isclose(reference, 0.0, rel_tol=0.0, abs_tol=1e-15):
        return 1.0 if math.isclose(value, 0.0, abs_tol=1e-15) else float("inf")
    return value / reference


def _mean_ratio(
    candidate: dict[str, dict[str, float]],
    reference: dict[str, dict[str, float]],
    scenarios: list[str],
    endpoint: str,
) -> float:
    return _safe_ratio(
        float(np.mean([candidate[name][endpoint] for name in scenarios])),
        float(np.mean([reference[name][endpoint] for name in scenarios])),
    )


def _rankdata(values: list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(len(array), dtype=float)
    start = 0
    while start < len(array):
        end = start + 1
        while end < len(array) and array[order[end]] == array[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def spearman(values: list[float], targets: list[float]) -> float:
    if len(values) != len(targets) or len(values) < 2:
        raise ValueError("Spearman inputs must have equal length >= 2")
    left = _rankdata(values)
    right = _rankdata(targets)
    if np.std(left) == 0.0 or np.std(right) == 0.0:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _early_edge_features(record: dict[str, Any]) -> dict[str, float]:
    steps = int(THRESHOLDS["causal_feature_steps"])
    trace = record["mechanism_trace"][:steps]
    return {
        f"{source}-{target}": float(
            np.mean(
                [
                    abs(row["filtered_rocof_hz_s"][source] - row["filtered_rocof_hz_s"][target])
                    for row in trace
                ]
            )
        )
        for source, target in EDGES
    }


def classify_probe(
    *,
    valid: bool,
    adaptive_fast_ratio: float,
    adaptive_sync_ratio: float,
    distinct_nonbaseline_arms: int,
    local_spearman: float,
    best_edge_matches: int,
    best_fixed_is_nonbaseline: bool,
    fixed_fast_ratio: float,
    fixed_sync_ratio: float,
) -> str:
    if not valid:
        return "INVALID-EDGE-INFORMATION-PROBE"
    adaptive = bool(
        adaptive_fast_ratio <= THRESHOLDS["adaptive_fast_ratio_max"]
        and adaptive_sync_ratio <= THRESHOLDS["adaptive_sync_ratio_max"]
        and distinct_nonbaseline_arms
        >= THRESHOLDS["minimum_distinct_nonbaseline_oracle_arms"]
    )
    if adaptive:
        if (
            local_spearman >= THRESHOLDS["local_spearman_min"]
            and best_edge_matches >= THRESHOLDS["local_best_edge_match_min"]
        ):
            return "LOCALLY-SIGNALLED-EDGE-GAP"
        return "OUTCOME-ONLY-EDGE-GAP"
    if (
        best_fixed_is_nonbaseline
        and fixed_fast_ratio <= THRESHOLDS["fixed_fast_material_ratio_max"]
        and fixed_sync_ratio <= THRESHOLDS["fixed_sync_no_harm_ratio_max"]
    ):
        return "CLASSICAL-RETUNE"
    return "NO-ADAPTIVE-EDGE-VALUE"


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    by_arm: dict[str, dict[str, dict[str, float]]] = {}
    records: dict[str, dict[str, dict[str, Any]]] = {}
    invalid: list[str] = []
    zero_sum_max = 0.0
    for job in seal["jobs"]:
        path = out_dir / "records" / f"{job['name']}.json"
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        trace = record.get("mechanism_trace", [])
        observed_zero_sum = (
            max(abs(row["total_residual_sum_system_pu"]) for row in trace)
            if trace
            else float("inf")
        )
        zero_sum_max = max(zero_sum_max, observed_zero_sum)
        guards = record.get("guards", {})
        valid = bool(
            record.get("seal_sha256") == expected_sha256
            and guards.get("completed") is True
            and guards.get("finite_telemetry") is True
            and guards.get("tds_test_ok") is True
            and guards.get("system_exit_code") == 0
            and guards.get("action_contract_pass") is True
            and guards.get("storage_constraint_violation_count") == 0
            and len(trace) == development.STEPS
            and observed_zero_sum <= THRESHOLDS["residual_sum_abs_max_system_pu"]
        )
        if not valid:
            invalid.append(job["name"])
            continue
        metrics = summarise_fast_md_trace(
            record,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        arm = job["arm"]["name"]
        scenario = job["scenario"]["name"]
        by_arm.setdefault(arm, {})[scenario] = {
            endpoint: float(metrics[endpoint])
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        records.setdefault(arm, {})[scenario] = record

    scenarios = sorted(item["name"] for item in seal["scenarios"])
    arm_names = [item["name"] for item in seal["arms"]]
    complete = bool(
        not invalid
        and all(set(by_arm.get(arm, {})) == set(scenarios) for arm in arm_names)
    )
    analysis: dict[str, Any] = {}
    classification = "INVALID-EDGE-INFORMATION-PROBE"
    if complete:
        baseline = by_arm[BASELINE_ARM]
        ratios: dict[str, dict[str, dict[str, float]]] = {}
        feasible: dict[str, dict[str, bool]] = {}
        for arm in arm_names:
            ratios[arm] = {}
            feasible[arm] = {}
            for scenario in scenarios:
                ratios[arm][scenario] = {
                    endpoint: _safe_ratio(
                        by_arm[arm][scenario][endpoint], baseline[scenario][endpoint]
                    )
                    for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
                }
                feasible[arm][scenario] = all(
                    ratios[arm][scenario][endpoint]
                    <= THRESHOLDS["common_individual_ratio_max"]
                    for endpoint in COMMON_ENDPOINTS
                )

        fixed_scores: dict[str, float] = {}
        fixed_ratios: dict[str, dict[str, float]] = {}
        for arm in arm_names:
            if not all(feasible[arm].values()):
                continue
            fixed_ratios[arm] = {
                endpoint: _mean_ratio(by_arm[arm], baseline, scenarios, endpoint)
                for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
            }
            fixed_scores[arm] = max(
                fixed_ratios[arm][endpoint] for endpoint in DIFFERENTIAL_ENDPOINTS
            )
        best_fixed = min(
            fixed_scores,
            key=lambda arm: (fixed_scores[arm], arm_names.index(arm)),
        )

        oracle_selection: dict[str, str] = {}
        oracle_rows: dict[str, dict[str, float]] = {}
        for scenario in scenarios:
            candidates = [arm for arm in arm_names if feasible[arm][scenario]]
            selected = min(
                candidates,
                key=lambda arm: (
                    max(ratios[arm][scenario][endpoint] for endpoint in DIFFERENTIAL_ENDPOINTS),
                    np.mean([ratios[arm][scenario][endpoint] for endpoint in DIFFERENTIAL_ENDPOINTS]),
                    arm_names.index(arm),
                ),
            )
            oracle_selection[scenario] = selected
            oracle_rows[scenario] = by_arm[selected][scenario]

        oracle_over_baseline = {
            endpoint: _mean_ratio(oracle_rows, baseline, scenarios, endpoint)
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        oracle_over_best_fixed = {
            endpoint: _mean_ratio(
                oracle_rows, by_arm[best_fixed], scenarios, endpoint
            )
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        nonbaseline = {
            arm for arm in oracle_selection.values() if arm != BASELINE_ARM
        }

        features: list[float] = []
        benefits: list[float] = []
        per_scenario_signal: dict[str, Any] = {}
        best_edge_matches = 0
        single_edge_arms = {_edge_name(edge): edge for edge in EDGES}
        for scenario in scenarios:
            edge_features = _early_edge_features(records[BASELINE_ARM][scenario])
            edge_benefits = {
                arm: 1.0
                - max(
                    ratios[arm][scenario][endpoint]
                    for endpoint in DIFFERENTIAL_ENDPOINTS
                )
                for arm in single_edge_arms
            }
            best_feature_arm = max(
                single_edge_arms,
                key=lambda arm: (
                    edge_features[
                        f"{single_edge_arms[arm][0]}-{single_edge_arms[arm][1]}"
                    ],
                    -arm_names.index(arm),
                ),
            )
            best_benefit_arm = max(
                single_edge_arms,
                key=lambda arm: (edge_benefits[arm], -arm_names.index(arm)),
            )
            best_edge_matches += int(best_feature_arm == best_benefit_arm)
            per_scenario_signal[scenario] = {
                "early_edge_feature": edge_features,
                "single_edge_joint_benefit": edge_benefits,
                "largest_feature_arm": best_feature_arm,
                "best_benefit_arm": best_benefit_arm,
                "match": best_feature_arm == best_benefit_arm,
            }
            for arm, edge in single_edge_arms.items():
                features.append(edge_features[f"{edge[0]}-{edge[1]}"])
                benefits.append(edge_benefits[arm])
        local_spearman = spearman(features, benefits)

        classification = classify_probe(
            valid=True,
            adaptive_fast_ratio=oracle_over_best_fixed[
                "fast_inter_area_iae_hz_s"
            ],
            adaptive_sync_ratio=oracle_over_best_fixed[
                "normalized_sync_loss_hz2"
            ],
            distinct_nonbaseline_arms=len(nonbaseline),
            local_spearman=local_spearman,
            best_edge_matches=best_edge_matches,
            best_fixed_is_nonbaseline=best_fixed != BASELINE_ARM,
            fixed_fast_ratio=fixed_ratios[best_fixed]["fast_inter_area_iae_hz_s"],
            fixed_sync_ratio=fixed_ratios[best_fixed]["normalized_sync_loss_hz2"],
        )
        analysis = {
            "fixed_arm_ratios_over_baseline": fixed_ratios,
            "best_fixed_arm": best_fixed,
            "outcome_oracle_selection": oracle_selection,
            "distinct_nonbaseline_oracle_arms": sorted(nonbaseline),
            "oracle_over_baseline": oracle_over_baseline,
            "oracle_over_best_fixed": oracle_over_best_fixed,
            "local_information_signal": {
                "pooled_spearman": local_spearman,
                "best_edge_match_count": best_edge_matches,
                "case_count": len(scenarios),
                "per_scenario": per_scenario_signal,
            },
        }

    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "classification": classification,
        "guards": {
            "all_records_present_and_valid": complete,
            "record_count": sum(len(rows) for rows in by_arm.values()),
            "expected_record_count": len(seal["jobs"]),
            "invalid_jobs": invalid,
            "total_residual_sum_abs_max_system_pu": zero_sum_max,
        },
        "analysis": analysis,
        "thresholds": THRESHOLDS,
        "predeclared_disjoint_formal_eval_bank": seal[
            "predeclared_disjoint_formal_eval_bank"
        ],
        "claim_boundary": seal["claim_boundary"],
    }
    path = out_dir / "development_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    if analysis:
        print(f"best_fixed_arm={analysis['best_fixed_arm']}")
        print(
            "oracle_over_best_fixed="
            + json.dumps(analysis["oracle_over_best_fixed"], sort_keys=True)
        )
        print(
            "local_information_signal="
            + json.dumps(analysis["local_information_signal"], sort_keys=True)
        )
    print(f"summary_sha256={digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "smoke", "run", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-seal-sha256")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.seal, args.out)
        return
    if not args.expected_seal_sha256:
        parser.error("--expected-seal-sha256 is required after prepare")
    if args.command == "smoke":
        smoke(args.seal, args.expected_seal_sha256, args.out)
    elif args.command == "run":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out,
            args.shard_index,
            args.shard_count,
        )
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out)


if __name__ == "__main__":
    main()
