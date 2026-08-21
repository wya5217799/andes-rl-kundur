"""Forensic analysis of the R402 CANARY-FAIL bank (read-only, no ANDES).

One command that recomputes, from the sealed evaluation records, training
manifests, and checkpoints: per-block action patterns (saturation, slew-bound
hits, magnitude), the trained policies' own two-component cost decomposition,
the Lagrangian multiplier trajectory, message-vs-no-message action
correlation, and endpoint-vs-action-deviation from the deterministic
reference.  This is the tight feedback loop for failure-cause hypotheses;
it never reruns physics.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract
from andes_rl_kundur.agents.cd_matd3 import compute_rocof, physical_costs

OUT = ROOT / "results/research_loop/r402_cd_matd3_canary"
OUTPUT = ROOT / "tmp" / "r402_forensics.json"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _action_patterns(records):
    sat = 0
    slew_hits = 0
    steps = 0
    abs_sum = 0.0
    for record in records:
        actions = np.array([s["action_norm"] for s in record["steps"]])
        diffs = np.diff(
            np.concatenate([np.zeros((1, 4, 2)), actions], axis=0), axis=0
        )
        sat += int(np.sum(np.abs(actions) > 0.999))
        slew_hits += int(np.sum(np.abs(np.abs(diffs) - 0.25) < 1e-6))
        steps += actions.shape[0] * 4 * 2
        abs_sum += float(np.sum(np.abs(actions)))
    return {
        "steps": int(steps),
        "saturation_fraction": float(sat / steps) if steps else None,
        "slew_bound_hit_fraction": float(slew_hits / steps) if steps else None,
        "mean_abs_action": float(abs_sum / steps) if steps else None,
    }


def _costs_for(records, contract):
    differential = []
    common = []
    for record in records:
        freq = np.array([s["freq_hz_physical"] for s in record["steps"]])
        initial = np.array(record["initial_freq_hz_physical"])
        rocof = compute_rocof(initial, freq, dt=float(contract["dt_seconds"]))
        power = np.zeros((freq.shape[0], 4))
        cd, cc = physical_costs(freq, rocof, power, contract=contract)
        differential.append(float(np.sum(cd)))
        common.append(float(np.sum(cc)))
    return {
        "total_differential_cost": float(sum(differential)),
        "total_common_cost": float(sum(common)),
        "mean_per_record_differential": float(np.mean(differential)),
        "mean_per_record_common": float(np.mean(common)),
    }


def _lagrange_trajectory(arm_id, seed):
    """Extract the multiplier trajectory from the periodic checkpoints."""

    import torch

    values = []
    root = OUT / "train" / arm_id / f"seed{seed}"
    for path in sorted((root / "snapshots").glob("episode*.pt")):
        payload = torch.load(str(path), map_location="cpu")
        values.append((int(path.stem.replace("episode", "")), float(payload["lagrange"])))
    final = root / "final.pt"
    if final.is_file():
        payload = torch.load(str(final), map_location="cpu")
        values.append((43200, float(payload["lagrange"])))
    return values


def _correlation(records_a, records_b):
    flat_a = []
    flat_b = []
    for ra, rb in zip(records_a, records_b):
        a = np.array([s["action_norm"] for s in ra["steps"]]).reshape(-1)
        b = np.array([s["action_norm"] for s in rb["steps"]]).reshape(-1)
        flat_a.append(a)
        flat_b.append(b)
    flat_a = np.concatenate(flat_a)
    flat_b = np.concatenate(flat_b)
    if flat_a.std() == 0 or flat_b.std() == 0:
        return None
    return float(np.corrcoef(flat_a, flat_b)[0, 1])


def main() -> None:
    contract = build_contract()
    evaluation = [
        p for p in contract["profiles"] if p["split"] == "evaluation"
    ]
    profiles = [str(p["profile_id"]) for p in evaluation]
    det_arm = str(contract["deterministic_arm_id"])
    arms = [str(a) for a in contract["learning_arm_ids"]]
    seeds = [int(s) for s in contract["training_seeds"]]

    def records_of(arm_id, seed):
        records = []
        for profile_id in profiles:
            suffix = "deterministic" if seed is None else f"seed{seed}"
            path = OUT / "eval" / arm_id / suffix / f"{profile_id}.json"
            records.extend(_read_json(path)["records"])
        return records

    det_records = records_of(det_arm, None)
    det_patterns = _action_patterns(det_records)
    det_costs = _costs_for(det_records, contract)

    report = {
        "deterministic": {
            "action_patterns": det_patterns,
            "costs": det_costs,
        },
        "learning_arms": {},
        "lagrange": {},
        "message_vs_no_message_correlation": {},
        "endpoint_and_deviation": {},
    }
    for arm_id in arms:
        for seed in seeds:
            records = records_of(arm_id, seed)
            key = f"{arm_id}_s{seed}"
            report["learning_arms"][key] = {
                "action_patterns": _action_patterns(records),
                "costs": _costs_for(records, contract),
            }
        if arm_id in ("cd_matd3_message", "cd_matd3_no_message"):
            for seed in seeds:
                report["lagrange"][f"{arm_id}_s{seed}"] = _lagrange_trajectory(
                    arm_id, seed
                )
    for seed in seeds:
        msg = records_of("cd_matd3_message", seed)
        nom = records_of("cd_matd3_no_message", seed)
        report["message_vs_no_message_correlation"][
            f"s{seed}"
        ] = _correlation(msg, nom)

    det_actions = []
    for record in det_records:
        det_actions.append(
            np.array([s["action_norm"] for s in record["steps"]])
        )
    for arm_id in arms:
        for seed in seeds:
            records = records_of(arm_id, seed)
            distances = []
            for record, det_action in zip(records, det_actions):
                action = np.array(
                    [s["action_norm"] for s in record["steps"]]
                )
                distances.append(
                    float(np.mean(np.abs(action - det_action)))
                )
            report["endpoint_and_deviation"][
                f"{arm_id}_s{seed}"
            ] = {"mean_abs_action_distance_from_deterministic": float(np.mean(distances))}

    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"forensics written: {OUTPUT} sha256={digest}")


if __name__ == "__main__":
    main()
