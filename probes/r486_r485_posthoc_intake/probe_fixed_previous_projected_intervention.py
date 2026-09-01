"""R485 scratch intervention replay: fixed actor feedback through projector.

The frozen question, selection, formulas, controls and thresholds live in
``PROBE_CARD.md`` and are hash-bound below.  This script uses sealed
observations/checkpoints only; it does not run ANDES or produce physical
endpoint evidence.

Usage:
  python probe_fixed_previous_projected_intervention.py --self-check
  python probe_fixed_previous_projected_intervention.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


PROFILE_IDS = ("canary_eval_a", "canary_eval_b", "canary_eval_c", "canary_eval_d")
SLEW_LIMIT = 0.25
REPLAY_TOLERANCE = 1.0e-6
TV_SUPPORT_MAX = 0.50
RMS_NO_INCREASE_MAX = 1.10
TV_REFUTE_MIN = 0.90
COMPARATOR_GUARD_MAX = 1.10
EXPECTED_CARD_SHA256 = "83574e6d293427a030651ee4a037488cdfa2cbb0a0c61070ac6861c9f8454a6e"
EXPECTED_PROBE05_SHA256 = "aa92a8be81978369e2f72916215740e5fa8088c2cce4aae00aecac6e460f270f"
EXPECTED_PROBE02_SHA256 = "8712d95b7762d9995724f728e984ff4feb374999ec96ae67951d3ba0b08691ae"
EXPECTED_METRIC_SOURCE_SHA256 = "bb5cb7aafe4b03b556dbeca24773cfecc4d31955e4e6eb7e94b379107a6bb87c"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
CARD_PATH = OUT_DIR / "PROBE_CARD.md"
PROBE05_PATH = ROOT / "tmp/yang-md-decoupling-marl/r485_root_cause_probe_05/probe_previous_action_feedback.py"
PROBE02_PATH = ROOT / "tmp/yang-md-decoupling-marl/r485_root_cause_probe_02/probe_projection_tv_attribution.py"
METRIC_SOURCE_PATH = ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path, expected_sha256: str) -> Any:
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"dependency hash mismatch: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def action_metrics(actions: np.ndarray) -> dict[str, Any]:
    """Exact R485 action RMS/TV aggregation plus channel decompositions."""

    values = np.asarray(actions, dtype=np.float64)
    if values.shape != (6, 150, 4, 2):
        raise ValueError(f"unexpected action shape: {values.shape}")
    previous = np.concatenate(
        [np.zeros((6, 1, 4, 2), dtype=np.float64), values[:, :-1]], axis=1
    )
    absolute_delta = np.abs(values - previous)
    return {
        "rms": float(np.sqrt(np.mean(np.square(values)))),
        "total_variation": float(np.sum(absolute_delta)),
        "per_channel": {
            "M": {
                "rms": float(np.sqrt(np.mean(np.square(values[..., 0])))),
                "total_variation": float(np.sum(absolute_delta[..., 0])),
            },
            "D": {
                "rms": float(np.sqrt(np.mean(np.square(values[..., 1])))),
                "total_variation": float(np.sum(absolute_delta[..., 1])),
            },
        },
    }


def metric_ratios(numerator: dict[str, Any], denominator: dict[str, Any]) -> dict[str, Any]:
    return {
        "rms": float(numerator["rms"] / denominator["rms"]),
        "total_variation": float(
            numerator["total_variation"] / denominator["total_variation"]
        ),
        "per_channel": {
            channel: {
                metric: float(
                    numerator["per_channel"][channel][metric]
                    / denominator["per_channel"][channel][metric]
                )
                for metric in ("rms", "total_variation")
            }
            for channel in ("M", "D")
        },
    }


def synthetic_self_check(projector: Any) -> dict[str, Any]:
    actions = np.asarray([[[[0.10, -0.20]], [[0.30, -0.10]]]], dtype=np.float64)
    # Expand to the production shape and hold the second step thereafter, so
    # padding does not create an artificial return-to-zero TV transition.
    padded = np.zeros((6, 150, 4, 2), dtype=np.float64)
    padded[0, 0, 0] = actions[0, 0, 0]
    padded[0, 1:, 0] = actions[0, 1, 0]
    metrics = action_metrics(padded)
    expected_square_sum = 0.10**2 + 0.20**2 + 149 * (0.30**2 + 0.10**2)
    expected_rms = float(np.sqrt(expected_square_sum / padded.size))
    if not np.isclose(metrics["rms"], expected_rms, rtol=0.0, atol=1.0e-15):
        raise AssertionError("RMS self-check failed")
    if not np.isclose(metrics["total_variation"], 0.60, rtol=0.0, atol=1.0e-15):
        raise AssertionError("zero-to-first TV self-check failed")
    previous = np.arange(3 * 4 * 2, dtype=np.float32).reshape(3, 4, 2)
    anchor = np.repeat(previous.mean(axis=0, keepdims=True), 3, axis=0)
    if not np.array_equal(anchor[0], anchor[-1]):
        raise AssertionError("fixed anchor self-check failed")
    first = projector.project_independent(
        np.zeros((4, 2), dtype=np.float32),
        np.full((4, 2), 0.80, dtype=np.float32),
        SLEW_LIMIT,
    )
    if not np.array_equal(first, np.full((4, 2), 0.25, dtype=np.float32)):
        raise AssertionError("slew projector self-check failed")
    decision_fixture = {
        "intervention_to_actual": {
            "rms": 1.0,
            "total_variation": 0.4,
            "per_channel": {
                "M": {"rms": 1.0, "total_variation": 0.4},
                "D": {"rms": 1.0, "total_variation": 0.4},
            },
        },
        "intervention_to_direct_md": {"rms": 1.0, "total_variation": 1.0},
    }
    if decide([decision_fixture] * 4)["verdict"] != (
        "RECORDED_PATH_INTERVENTION_SUFFICIENT_FOR_ACTION_GUARDS"
    ):
        raise AssertionError("decision-tree self-check failed")
    return {
        "joint_rms": metrics["rms"],
        "joint_tv": metrics["total_variation"],
        "fixed_anchor_time_invariant": True,
        "slew_first": float(first[0, 0]),
    }


def actor_step(base: Any, actors: list[Any], observations: np.ndarray, previous_input: np.ndarray) -> np.ndarray:
    output = np.zeros((4, 2), dtype=np.float32)
    with base.torch.no_grad():
        for agent_index, actor in enumerate(actors):
            state = np.concatenate(
                [observations[agent_index], previous_input[agent_index]]
            ).astype(np.float32)
            output[agent_index] = (
                actor.deterministic(base.torch.from_numpy(state).unsqueeze(0))
                .cpu()
                .numpy()
                .squeeze(0)
                .astype(np.float32)
            )
    return output


def recursive_replay(
    base: Any,
    projector: Any,
    actors: list[Any],
    observations: np.ndarray,
    recorded_previous: np.ndarray,
    *,
    fixed_actor_previous: bool,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.zeros((6, 150, 4, 2), dtype=np.float32)
    projected = np.zeros_like(raw)
    for record_index in range(6):
        anchor = recorded_previous[record_index].mean(axis=0).astype(np.float32)
        projector_previous = np.zeros((4, 2), dtype=np.float32)
        for step_index in range(150):
            actor_previous = anchor if fixed_actor_previous else projector_previous
            proposed = actor_step(
                base,
                actors,
                observations[record_index, step_index],
                actor_previous,
            )
            executed = projector.project_independent(
                projector_previous, proposed, SLEW_LIMIT
            )
            raw[record_index, step_index] = proposed
            projected[record_index, step_index] = executed
            projector_previous = executed
    return raw, projected


def load_projected_trace(
    base: Any, path: Path, *, checkpoint_sha256: str | None = None
) -> tuple[np.ndarray, dict[str, Any]]:
    input_row = base.verified_sidecar(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"expected six scenarios: {path}")
    actions = np.zeros((6, 150, 4, 2), dtype=np.float32)
    for record_index, record in enumerate(records):
        if checkpoint_sha256 is not None and record.get("checkpoint_sha256") != checkpoint_sha256:
            raise ValueError("trace/checkpoint lineage mismatch")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise ValueError(f"expected 150 steps: {path}")
        for step_index, step in enumerate(steps):
            actions[record_index, step_index] = np.asarray(
                step["projected_action_norm"], dtype=np.float32
            )
    return actions, input_row


def summarize_profile(
    profile_id: str,
    base: Any,
    projector: Any,
    actors: list[Any],
    checkpoint_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate_path = base.TRACE_ROOT / f"{profile_id}.json"
    observations, recorded_previous, saved_raw, _ = base.load_profile(
        candidate_path, checkpoint_sha256
    )
    saved_projected, candidate_input = load_projected_trace(
        base, candidate_path, checkpoint_sha256=checkpoint_sha256
    )
    control_raw, control_projected = recursive_replay(
        base,
        projector,
        actors,
        observations,
        recorded_previous,
        fixed_actor_previous=False,
    )
    raw_error = float(np.max(np.abs(control_raw - saved_raw)))
    projected_error = float(np.max(np.abs(control_projected - saved_projected)))
    if raw_error > REPLAY_TOLERANCE or projected_error > REPLAY_TOLERANCE:
        raise AssertionError(
            f"negative control mismatch for {profile_id}: raw={raw_error}, projected={projected_error}"
        )
    _intervention_raw, intervention_projected = recursive_replay(
        base,
        projector,
        actors,
        observations,
        recorded_previous,
        fixed_actor_previous=True,
    )
    direct_path = (
        projector.EVAL_ROOT
        / "local_neighbour_md_km2_kd2/deterministic"
        / f"{profile_id}.json"
    )
    direct_projected, direct_input = load_projected_trace(base, direct_path)
    actual = action_metrics(saved_projected)
    intervention = action_metrics(intervention_projected)
    direct = action_metrics(direct_projected)
    return {
        "profile_id": profile_id,
        "negative_control": {
            "raw_max_abs_error": raw_error,
            "projected_max_abs_error": projected_error,
        },
        "actual": actual,
        "intervention": intervention,
        "direct_md": direct,
        "intervention_to_actual": metric_ratios(intervention, actual),
        "intervention_to_direct_md": metric_ratios(intervention, direct),
    }, [candidate_input, direct_input]


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    material_tv = all(
        row["intervention_to_actual"]["per_channel"][channel]["total_variation"]
        <= TV_SUPPORT_MAX
        for row in rows
        for channel in ("M", "D")
    ) and all(
        row["intervention_to_actual"]["total_variation"] <= TV_SUPPORT_MAX
        for row in rows
    )
    rms_no_increase = all(
        row["intervention_to_actual"]["rms"] <= RMS_NO_INCREASE_MAX
        and all(
            row["intervention_to_actual"]["per_channel"][channel]["rms"]
            <= RMS_NO_INCREASE_MAX
            for channel in ("M", "D")
        )
        for row in rows
    )
    refuted = all(
        row["intervention_to_actual"]["total_variation"] >= TV_REFUTE_MIN
        and all(
            row["intervention_to_actual"]["per_channel"][channel]["total_variation"]
            >= TV_REFUTE_MIN
            for channel in ("M", "D")
        )
        for row in rows
    )
    comparator_sufficient = all(
        row["intervention_to_direct_md"]["rms"] <= COMPARATOR_GUARD_MAX
        and row["intervention_to_direct_md"]["total_variation"]
        <= COMPARATOR_GUARD_MAX
        for row in rows
    )
    material_supported = material_tv and rms_no_increase
    if material_supported and comparator_sufficient:
        verdict = "RECORDED_PATH_INTERVENTION_SUFFICIENT_FOR_ACTION_GUARDS"
    elif material_supported:
        verdict = "ACTIONABLE_TV_AMPLIFIER_BUT_INTERVENTION_ALONE_INSUFFICIENT"
    elif refuted:
        verdict = "FIXED_PREVIOUS_PROJECTED_INTERVENTION_REFUTED"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "verdict": verdict,
        "material_tv_reduction_all": material_tv,
        "rms_no_increase_all": rms_no_increase,
        "material_intervention_supported": material_supported,
        "material_intervention_refuted": refuted,
        "comparator_action_guard_sufficient_all_profiles": comparator_sufficient,
    }


def write_outputs(result: dict[str, Any]) -> None:
    result_path = OUT_DIR / "result.json"
    report_path = OUT_DIR / "REPORT.md"
    sums_path = OUT_DIR / "SHA256SUMS"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R485 probe 10 — projected fixed-previous intervention",
        "",
        "> Scratch post-hoc recorded-path replay; not registered R485 evidence and not an ANDES replay.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        "| Profile | TV cf/actual | RMS cf/actual | TV cf/direct | RMS cf/direct |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["profiles"]:
        actual = row["intervention_to_actual"]
        direct = row["intervention_to_direct_md"]
        lines.append(
            f"| {row['profile_id']} | {actual['total_variation']:.4f} | "
            f"{actual['rms']:.4f} | {direct['total_variation']:.3f} | "
            f"{direct['rms']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The replay propagates the counterfactual command through the exact amplitude/slew",
            "projector but holds plant observations on their sealed path. It can screen an",
            "intervention; it cannot establish endpoint, stability, or TDS preservation.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    hashed = [CARD_PATH, Path(__file__).resolve(), result_path, report_path]
    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in hashed),
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if sha256_file(CARD_PATH) != EXPECTED_CARD_SHA256:
        raise ValueError("frozen probe-card hash mismatch")
    if sha256_file(METRIC_SOURCE_PATH) != EXPECTED_METRIC_SOURCE_SHA256:
        raise ValueError("formal metric source hash mismatch")
    base = load_module("r485_probe05_intervention", PROBE05_PATH, EXPECTED_PROBE05_SHA256)
    projector = load_module(
        "r485_probe02_intervention", PROBE02_PATH, EXPECTED_PROBE02_SHA256
    )
    self_check = synthetic_self_check(projector)
    if args.self_check:
        print(json.dumps({"self_check": "PASS", "details": self_check}, indent=2))
        return 0

    base.torch.set_num_threads(1)
    actors, payload, checkpoint_input = base.load_actors()
    rows: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = [checkpoint_input]
    for profile_id in PROFILE_IDS:
        row, profile_inputs = summarize_profile(
            profile_id, base, projector, actors, checkpoint_input["sha256"]
        )
        rows.append(row)
        inputs.extend(profile_inputs)
    result = {
        "schema_version": "r485_root_cause_probe_10_v1",
        "scope": "scratch_posthoc_recorded_path_intervention",
        "formal_artifacts_modified": False,
        "question": "Does a fixed previous-action actor input remain effective after recursive projection, and is it sufficient for the action guards?",
        "selection": {
            "arm_id": payload["arm_id"],
            "seed": int(payload["seed"]),
            "stage": payload["stage"],
            "profiles": list(PROFILE_IDS),
            "scenario_count_per_profile": 6,
            "steps_per_scenario": 150,
        },
        "thresholds": {
            "tv_intervention_to_actual_support_max": TV_SUPPORT_MAX,
            "rms_intervention_to_actual_no_increase_max": RMS_NO_INCREASE_MAX,
            "tv_intervention_to_actual_refute_min": TV_REFUTE_MIN,
            "comparator_guard_ratio_max": COMPARATOR_GUARD_MAX,
            "negative_control_tolerance": REPLAY_TOLERANCE,
        },
        "lineage": {
            "probe_card_sha256": EXPECTED_CARD_SHA256,
            "probe05_code_sha256": EXPECTED_PROBE05_SHA256,
            "probe02_code_sha256": EXPECTED_PROBE02_SHA256,
            "formal_metric_source": METRIC_SOURCE_PATH.relative_to(ROOT).as_posix(),
            "formal_metric_source_sha256": EXPECTED_METRIC_SOURCE_SHA256,
            "inputs": inputs,
        },
        "self_check": self_check,
        "profiles": rows,
    }
    result["decision"] = decide(rows)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "profiles": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
