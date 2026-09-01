"""R485 bounded confirmation: does feedback TV amplification generalize?

Selection is fixed and non-random: all eight factorial arms, seeds 501/513/526,
and profile ``canary_eval_a``.  For each of 24 policies, replay the sealed raw
actor then replace time-varying previous-action slots by each scenario's mean.

The mechanism is supported if at least 90% of the 48 policy-channel ratios are
<= 0.50 and none is >= 0.90.  It is refuted if at least half are >= 0.90;
otherwise it is heterogeneous.  Every checkpoint/trace sidecar and actual raw
replay is verified.  Actor-source P uses the frozen rho(i)=(i+1) mod 4 routing.

Usage: ``python probe_feedback_generality.py [--self-check]``
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ARM_IDS = (
    "an_cn_r0",
    "an_cn_r1",
    "an_cp_r0",
    "an_cp_r1",
    "ap_cn_r0",
    "ap_cn_r1",
    "ap_cp_r0",
    "ap_cp_r1",
)
SEEDS = (501, 513, 526)
PROFILE_ID = "canary_eval_a"
SUPPORT_RATIO_MAX = 0.50
REFUTE_RATIO_MIN = 0.90
SUPPORT_PREVALENCE_MIN = 0.90
REFUTE_PREVALENCE_MIN = 0.50
REPLAY_TOLERANCE = 1.0e-6
EXPECTED_PROBE05_SHA256 = "aa92a8be81978369e2f72916215740e5fa8088c2cce4aae00aecac6e460f270f"


def find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "CLAUDE.md").is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repository root not found")


ROOT = find_root()
OUT_DIR = Path(__file__).resolve().parent
PROBE05_PATH = ROOT / "tmp/yang-md-decoupling-marl/r485_root_cause_probe_05/probe_previous_action_feedback.py"
ATTEMPT_ROOT = ROOT / "results/research_loop/r485_60hz_source_factorial/r485-formal-20260829-a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_probe05() -> Any:
    if sha256_file(PROBE05_PATH) != EXPECTED_PROBE05_SHA256:
        raise ValueError("probe-05 code hash mismatch")
    spec = importlib.util.spec_from_file_location("r485_probe05_general", PROBE05_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load probe-05 helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_rows(rows: np.ndarray, source: str) -> np.ndarray:
    current = np.asarray(rows, dtype=np.float32).reshape(4, 7)
    if source == "N":
        return current.copy()
    if source != "P":
        raise ValueError(f"unknown actor source: {source}")
    routed = current.copy()
    for actor in range(4):
        routed[actor, 3:7] = current[(actor + 1) % 4, 3:7]
    return routed


def synthetic_self_check() -> dict[str, Any]:
    rows = np.arange(28, dtype=np.float32).reshape(4, 7)
    authentic = source_rows(rows, "N")
    placebo = source_rows(rows, "P")
    if not np.array_equal(authentic, rows):
        raise AssertionError("authentic routing self-check failed")
    for actor in range(4):
        if not np.array_equal(placebo[actor, :3], rows[actor, :3]):
            raise AssertionError("placebo owner slots changed")
        if not np.array_equal(placebo[actor, 3:7], rows[(actor + 1) % 4, 3:7]):
            raise AssertionError("placebo neighbour routing failed")
    return {"routing": "PASS", "arms": len(ARM_IDS), "seeds": list(SEEDS)}


def actor_source(arm_id: str) -> str:
    prefix = arm_id.split("_")[0]
    if prefix == "an":
        return "N"
    if prefix == "ap":
        return "P"
    raise ValueError(f"unknown arm actor prefix: {arm_id}")


def load_policy(base: Any, arm_id: str, seed: int) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    checkpoint = ATTEMPT_ROOT / f"train/{arm_id}/seed{seed}/final.pt"
    checkpoint_input = base.verified_sidecar(checkpoint)
    payload = base.torch.load(str(checkpoint), map_location="cpu", weights_only=True)
    if (
        payload.get("kind") != "r485-source-factorial"
        or payload.get("arm_id") != arm_id
        or int(payload.get("seed", -1)) != seed
        or payload.get("stage") != "final"
    ):
        raise ValueError("checkpoint identity mismatch")
    members = payload.get("members")
    if not isinstance(members, list) or len(members) != 4:
        raise ValueError("checkpoint member count mismatch")
    actors = []
    for member in members:
        actor = base.GaussianActor(9, 2, [128, 128, 128, 128]).cpu().eval()
        actor.load_state_dict(member["actor"])
        actors.append(actor)
    return actors, payload, checkpoint_input


def load_trace(base: Any, arm_id: str, seed: int, checkpoint_sha: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    path = ATTEMPT_ROOT / f"eval/same/{arm_id}/seed{seed}/{PROFILE_ID}.json"
    input_row = base.verified_sidecar(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"expected 6 records: {path}")
    observations = np.zeros((6, 150, 4, 7), dtype=np.float32)
    previous = np.zeros((6, 150, 4, 2), dtype=np.float32)
    saved_raw = np.zeros((6, 150, 4, 2), dtype=np.float32)
    source = actor_source(arm_id)
    for record_index, record in enumerate(records):
        if record.get("checkpoint_sha256") != checkpoint_sha:
            raise ValueError("trace/checkpoint hash mismatch")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise ValueError(f"expected 150 steps: {path}")
        prior = np.zeros((4, 2), dtype=np.float32)
        for step_index, step in enumerate(steps):
            observations[record_index, step_index] = source_rows(
                np.asarray(step["canonical_observation"], dtype=np.float32), source
            )
            previous[record_index, step_index] = prior
            saved_raw[record_index, step_index] = np.asarray(
                step["raw_action_norm"], dtype=np.float32
            )
            prior = np.asarray(step["projected_action_norm"], dtype=np.float32)
    return observations, previous, saved_raw, input_row


def actor_outputs_production_style(
    base: Any, actors: list[Any], observations: np.ndarray, previous: np.ndarray
) -> np.ndarray:
    """Match production's one-state-at-a-time deterministic actor calls."""

    output = np.zeros((*observations.shape[:3], 2), dtype=np.float32)
    flat_obs = observations.reshape(-1, 4, 7)
    flat_previous = previous.reshape(-1, 4, 2)
    flat_output = output.reshape(-1, 4, 2)
    with base.torch.no_grad():
        for row_index in range(len(flat_obs)):
            for agent_index, actor in enumerate(actors):
                state = np.concatenate(
                    [flat_obs[row_index, agent_index], flat_previous[row_index, agent_index]]
                ).astype(np.float32)
                flat_output[row_index, agent_index] = (
                    actor.deterministic(base.torch.from_numpy(state).unsqueeze(0))
                    .cpu()
                    .numpy()
                    .squeeze(0)
                    .astype(np.float32)
                )
    return output


def summarize_policy(base: Any, arm_id: str, seed: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    actors, _payload, checkpoint_input = load_policy(base, arm_id, seed)
    observations, previous, saved_raw, trace_input = load_trace(
        base, arm_id, seed, checkpoint_input["sha256"]
    )
    replayed = actor_outputs_production_style(base, actors, observations, previous)
    replay_error = float(np.max(np.abs(replayed - saved_raw)))
    if replay_error > REPLAY_TOLERANCE:
        raise AssertionError(
            f"sealed raw replay mismatch for {arm_id}/seed{seed}: {replay_error}"
        )
    fixed_previous = np.repeat(previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1)
    fixed_raw = base.actor_outputs(actors, observations, fixed_previous)
    actual_tv = base.path_tv(saved_raw)
    fixed_tv = base.path_tv(fixed_raw)
    row = {
        "arm_id": arm_id,
        "seed": seed,
        "actor_source": actor_source(arm_id),
        "fixed_mean_to_actual_tv_ratio": {
            "M": float(fixed_tv[0] / actual_tv[0]),
            "D": float(fixed_tv[1] / actual_tv[1]),
        },
        "actual_raw_tv": {"M": float(actual_tv[0]), "D": float(actual_tv[1])},
        "fixed_mean_raw_tv": {"M": float(fixed_tv[0]), "D": float(fixed_tv[1])},
        "actual_raw_rms": float(np.sqrt(np.mean(np.square(saved_raw)))),
        "fixed_mean_raw_rms": float(np.sqrt(np.mean(np.square(fixed_raw)))),
        "sealed_raw_replay_max_abs_error": replay_error,
    }
    del actors, replayed, fixed_raw, observations, previous, saved_raw
    gc.collect()
    return row, [checkpoint_input, trace_input]


def decide(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = np.asarray(
        [
            row["fixed_mean_to_actual_tv_ratio"][channel]
            for row in rows
            for channel in ("M", "D")
        ],
        dtype=float,
    )
    support_prevalence = float(np.mean(ratios <= SUPPORT_RATIO_MAX))
    refute_prevalence = float(np.mean(ratios >= REFUTE_RATIO_MIN))
    supported = support_prevalence >= SUPPORT_PREVALENCE_MIN and refute_prevalence == 0.0
    refuted = refute_prevalence >= REFUTE_PREVALENCE_MIN
    verdict = (
        "FEEDBACK_AMPLIFICATION_GENERALITY_SUPPORTED"
        if supported
        else "FEEDBACK_AMPLIFICATION_GENERALITY_REFUTED"
        if refuted
        else "HETEROGENEOUS"
    )
    return {
        "verdict": verdict,
        "support_prevalence": support_prevalence,
        "refute_prevalence": refute_prevalence,
        "ratio_median": float(np.median(ratios)),
        "ratio_q95": float(np.quantile(ratios, 0.95)),
        "ratio_max": float(np.max(ratios)),
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
        "# R485 root-cause probe 08: feedback generality",
        "",
        "> Scratch post-hoc checkpoint confirmation; not registered R485 evidence.",
        "",
        f"**Decision:** `{result['decision']['verdict']}`",
        "",
        f"- Support prevalence: {result['decision']['support_prevalence']:.1%}",
        f"- Median / q95 / max ratio: {result['decision']['ratio_median']:.3f} / "
        f"{result['decision']['ratio_q95']:.3f} / {result['decision']['ratio_max']:.3f}",
        "",
        "| Arm | Seed | M ratio | D ratio | Replay error |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["policies"]:
        ratio = row["fixed_mean_to_actual_tv_ratio"]
        lines.append(
            f"| {row['arm_id']} | {row['seed']} | {ratio['M']:.3f} | {ratio['D']:.3f} | "
            f"{row['sealed_raw_replay_max_abs_error']:.2e} |"
        )
    lines.extend(
        [
            "",
            "The fixed grid establishes bounded recurrence across factors/seeds/profile A only.",
            "It is not a 208-policy population or closed-loop intervention result.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    hashed = [Path(__file__).resolve(), result_path, report_path]
    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in hashed),
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    self_check = synthetic_self_check()
    if args.self_check:
        print(json.dumps({"self_check": "PASS", "details": self_check}, indent=2))
        return 0

    base = load_probe05()
    base.torch.set_num_threads(1)
    policies: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        for seed in SEEDS:
            row, input_rows = summarize_policy(base, arm_id, seed)
            policies.append(row)
            inputs.extend(input_rows)
    result = {
        "schema_version": "r485_root_cause_probe_08_v1",
        "scope": "scratch_posthoc_checkpoint_confirmation",
        "formal_artifacts_modified": False,
        "question": "Does time-varying previous-action feedback amplification recur across factors and fixed seeds?",
        "selection": {"arms": list(ARM_IDS), "seeds": list(SEEDS), "profile_id": PROFILE_ID},
        "thresholds": {
            "support_ratio_max": SUPPORT_RATIO_MAX,
            "refute_ratio_min": REFUTE_RATIO_MIN,
            "support_prevalence_min": SUPPORT_PREVALENCE_MIN,
            "refute_prevalence_min": REFUTE_PREVALENCE_MIN,
            "replay_tolerance": REPLAY_TOLERANCE,
        },
        "lineage": {"probe05_code_sha256": EXPECTED_PROBE05_SHA256, "inputs": inputs},
        "self_check": self_check,
        "policies": policies,
    }
    result["decision"] = decide(policies)
    write_outputs(result)
    print(json.dumps({"decision": result["decision"], "policy_count": len(policies)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
