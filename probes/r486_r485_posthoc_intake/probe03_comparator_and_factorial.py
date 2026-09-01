"""PROTOTYPE: audit comparator object equality and factorial inference.

No project analysis function is imported.  The script checks reset/plant/action
path parity against the R485 direct-M/D traces and independently rebuilds the
6 s and 30 s seed-level contrasts, exact signed-rank tests, and Holm family.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ROUND_DIR = ROOT / "memory" / "rounds" / "R485"
ATTEMPT = ROOT / "results" / "research_loop" / "r485_60hz_source_factorial" / "r485-formal-20260829-a"
DIRECT = "local_neighbour_md_km2_kd2"
EFFECTS = ("actor_main", "critic_main", "actor_x_critic", "critic_x_reward")


def close(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1.0e-12, abs_tol=1.0e-10)


def project(previous: np.ndarray, raw: np.ndarray, limit: float = 0.25) -> np.ndarray:
    amplitude = np.clip(np.asarray(raw, dtype=np.float32), -1.0, 1.0).astype(np.float32)
    previous = np.asarray(previous, dtype=np.float32)
    previous64 = previous.astype(np.float64)
    delta64 = np.clip(amplitude.astype(np.float64) - previous64, -limit, limit)
    executed = np.clip(previous64 + delta64, -1.0, 1.0).astype(np.float32)
    overshoot = executed.astype(np.float64) - previous64 > limit
    undershoot = executed.astype(np.float64) - previous64 < -limit
    if np.any(overshoot):
        executed[overshoot] = np.nextafter(executed[overshoot], np.float32(-np.inf))
    if np.any(undershoot):
        executed[undershoot] = np.nextafter(executed[undershoot], np.float32(np.inf))
    return np.clip(executed, -1.0, 1.0).astype(np.float32)


def direct_raw(canonical: np.ndarray) -> np.ndarray:
    rows = np.asarray(canonical, dtype=np.float32).reshape(4, 7)
    result = np.zeros((4, 2), dtype=np.float32)
    for actor, row in enumerate(rows):
        own_f, own_r = float(row[1]), float(row[2])
        neighbour_f = row[3:5].astype(np.float64)
        neighbour_r = row[5:7].astype(np.float64)
        own_severity = abs(own_f) + abs(own_r)
        neighbour_severity = float(np.mean(np.abs(neighbour_f) + np.abs(neighbour_r)))
        damping = abs(own_f) + float(np.mean(np.abs(own_f - neighbour_f))) + float(np.mean(np.abs(own_r - neighbour_r)))
        result[actor] = np.tanh([2.0 * (own_severity - neighbour_severity), 2.0 * damping])
    return result


def check_projection(record: dict[str, Any], *, deterministic_direct: bool) -> tuple[float, float, int]:
    previous = np.zeros((4, 2), dtype=np.float32)
    max_projection_error = 0.0
    max_raw_law_error = 0.0
    mismatches = 0
    for step in record["steps"]:
        raw = np.asarray(step["raw_action_norm"], dtype=np.float32)
        executed = np.asarray(step["action_norm"], dtype=np.float32)
        projected_saved = np.asarray(step["projected_action_norm"], dtype=np.float32)
        expected = project(previous, raw)
        max_projection_error = max(max_projection_error, float(np.max(np.abs(expected - executed))))
        if not np.array_equal(executed, projected_saved) or not np.array_equal(executed, expected):
            mismatches += 1
        if deterministic_direct:
            expected_raw = direct_raw(np.asarray(step["canonical_observation"], dtype=np.float32))
            max_raw_law_error = max(max_raw_law_error, float(np.max(np.abs(expected_raw - raw))))
            if not np.allclose(expected_raw, raw, rtol=0.0, atol=1.0e-7):
                mismatches += 1
        previous = executed
    return max_projection_error, max_raw_law_error, mismatches


def differential_energy(records: list[dict[str, Any]], contract: dict[str, Any], steps: int) -> float:
    profile_id = records[0]["profile_id"]
    profile = next(row for row in contract["profiles"] if row["profile_id"] == profile_id)
    registered = {row["scenario_id"]: row for row in profile["scenarios"]}
    by_id = {row["scenario_id"]: row for row in records}
    transform = np.asarray(contract["differential_transform"], dtype=float)
    nominal = float(contract["physical_nominal_frequency_hz"])
    dt = float(contract["dt_seconds"])
    total = 0.0
    for kind in ("common", "differential", "localized"):
        positive = np.asarray([row["freq_hz_physical"] for row in by_id[f"{profile_id}_{kind}_positive"]["steps"][:steps]], dtype=float) - nominal
        negative = np.asarray([row["freq_hz_physical"] for row in by_id[f"{profile_id}_{kind}_negative"]["steps"][:steps]], dtype=float) - nominal
        odd = 0.5 * (positive - negative)
        differential = odd @ transform.T
        magnitude = float(registered[f"{profile_id}_{kind}_positive"]["magnitude"])
        total += float(np.sum(np.mean(differential**2, axis=1))) * dt / magnitude**2
    return total


def seed_effects(rows: list[dict[str, Any]], metric: str, seeds: tuple[int, ...], profiles: tuple[str, ...]) -> dict[str, list[float]]:
    index: dict[tuple[int, str, str, int, str], float] = {}
    for row in rows:
        key = (row["seed"], row["actor"], row["critic"], row["reward"], row["profile"])
        if key in index:
            raise ValueError(f"duplicate factorial cell: {key}")
        index[key] = float(row[metric])
    expected = {(seed, actor, critic, reward, profile) for seed in seeds for actor in ("N", "P") for critic in ("N", "P") for reward in (0, 1) for profile in profiles}
    if set(index) != expected:
        raise ValueError("factorial roster mismatch")
    result = {name: [] for name in EFFECTS}
    for seed in seeds:
        loss = lambda a, c, r, p: index[(seed, a, c, r, p)]
        result["actor_main"].append(statistics.fmean(math.log(loss("P", c, r, p) / loss("N", c, r, p)) for c in ("N", "P") for r in (0, 1) for p in profiles))
        result["critic_main"].append(statistics.fmean(math.log(loss(a, "P", r, p) / loss(a, "N", r, p)) for a in ("N", "P") for r in (0, 1) for p in profiles))
        result["actor_x_critic"].append(statistics.fmean(math.log(loss("P", "N", r, p) / loss("N", "N", r, p)) - math.log(loss("P", "P", r, p) / loss("N", "P", r, p)) for r in (0, 1) for p in profiles))
        result["critic_x_reward"].append(statistics.fmean(math.log(loss(a, "P", 1, p) / loss(a, "N", 1, p)) - math.log(loss(a, "P", 0, p) / loss(a, "N", 0, p)) for a in ("N", "P") for p in profiles))
    return result


def hodges_lehmann(values: list[float]) -> float:
    return float(np.median([(values[i] + values[j]) / 2.0 for i in range(len(values)) for j in range(i, len(values))]))


def symmetry_skew(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    deviations = array - float(np.mean(array))
    second = float(np.mean(deviations**2))
    return 0.0 if second == 0.0 else float(np.mean(deviations**3)) / second**1.5


def signed_rank_p(values: list[float], null: float) -> float:
    centered = np.asarray(values, dtype=float) - null
    absolute = np.abs(centered)
    if np.any(absolute == 0.0) or len(np.unique(absolute)) != len(absolute):
        raise ValueError("zero or tied ranks")
    order = np.argsort(absolute)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(centered) + 1)
    statistic = int(np.sum(ranks[centered > 0.0]))
    counts = [1]
    for rank in range(1, len(centered) + 1):
        updated = [0] * (len(counts) + rank)
        for total, count in enumerate(counts):
            updated[total] += count
            updated[total + rank] += count
        counts = updated
    return float(sum(counts[statistic:]) / 2 ** len(centered))


def holm(p_values: dict[str, float]) -> dict[str, dict[str, float | bool]]:
    ordered = sorted(p_values, key=lambda name: (p_values[name], name))
    result: dict[str, dict[str, float | bool]] = {}
    running = 0.0
    prior = True
    for rank, name in enumerate(ordered):
        multiplier = len(ordered) - rank
        threshold = 0.05 / multiplier
        running = max(running, multiplier * p_values[name])
        rejected = prior and p_values[name] <= threshold
        prior = rejected
        result[name] = {"raw_p": p_values[name], "adjusted_p": min(1.0, running), "holm_threshold": threshold, "reject": rejected}
    return result


def compare_inference(effects: dict[str, list[float]], formal: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    null = math.log(1.10)
    p_values = {name: signed_rank_p(values, null) for name, values in effects.items()}
    decisions = holm(p_values)
    for name, values in effects.items():
        row = formal["tests"][name]
        checks = [
            all(close(a, b) for a, b in zip(values, row["seed_effects"], strict=True)),
            close(hodges_lehmann(values), row["hodges_lehmann"]),
            close(math.exp(hodges_lehmann(values)), row["geometric_location_ratio"]),
            close(p_values[name], row["p_one_sided"]),
            close(symmetry_skew(values), row["symmetry_skew"]),
            all(close(decisions[name][key], row["holm"][key]) if key != "reject" else decisions[name][key] == row["holm"][key] for key in decisions[name]),
        ]
        if not all(checks):
            errors.append(name)
    return errors


def run() -> dict[str, Any]:
    started = time.time()
    card = json.loads((ROUND_DIR / "resolved_parameter_card.json").read_text(encoding="utf-8"))
    config = json.loads((ROUND_DIR / "config.json").read_text(encoding="utf-8"))
    formal = json.loads((ATTEMPT / "formal_analysis.json").read_text(encoding="utf-8"))
    contract = card["evaluation_contracts"]["same"]
    profiles = tuple(row["profile_id"] for row in contract["profiles"] if row["split"] == "evaluation")
    seeds = tuple(config["formal_seeds"])
    direct_records: dict[tuple[str, str], dict[str, Any]] = {}
    projection_mismatches = 0
    max_projection_error = 0.0
    max_direct_raw_law_error = 0.0
    for path in sorted((ATTEMPT / "eval" / "same" / DIRECT / "deterministic").glob("*.json")):
        for record in json.loads(path.read_bytes())["records"]:
            direct_records[(record["profile_id"], record["scenario_id"])] = record
            p_error, raw_error, mismatches = check_projection(record, deterministic_direct=True)
            max_projection_error = max(max_projection_error, p_error)
            max_direct_raw_law_error = max(max_direct_raw_law_error, raw_error)
            projection_mismatches += mismatches

    identity_mismatches = 0
    reset_frequency_mismatches = 0
    rows: list[dict[str, Any]] = []
    learned_trajectories = 0
    for path in sorted((ATTEMPT / "eval" / "same").glob("*/seed*/*.json")):
        records = json.loads(path.read_bytes())["records"]
        arm = records[0]["arm_id"]
        seed = int(records[0]["training_seed"])
        actor, critic, reward = arm.split("_")
        for record in records:
            learned_trajectories += 1
            reference = direct_records[(record["profile_id"], record["scenario_id"])]
            fields = ("bank", "bank_contract_sha256", "environment_seed", "profile_id", "scenario_id", "pair_kind", "sign", "magnitude", "delta_u", "identity")
            if any(record[field] != reference[field] for field in fields):
                identity_mismatches += 1
            if not np.array_equal(np.asarray(record["initial_freq_hz_physical"]), np.asarray(reference["initial_freq_hz_physical"])):
                reset_frequency_mismatches += 1
            p_error, _, mismatches = check_projection(record, deterministic_direct=False)
            max_projection_error = max(max_projection_error, p_error)
            projection_mismatches += mismatches
        rows.append({
            "seed": seed,
            "actor": actor[1:].upper(),
            "critic": critic[1:].upper(),
            "reward": int(reward[1:]),
            "profile": records[0]["profile_id"],
            "energy_6s": differential_energy(records, contract, 30),
            "energy_30s": differential_energy(records, contract, 150),
        })

    effects_6 = seed_effects(rows, "energy_6s", seeds, profiles)
    effects_30 = seed_effects(rows, "energy_30s", seeds, profiles)
    primary_errors = compare_inference(effects_6, formal["primary_inference"])
    tail_errors = compare_inference(effects_30, formal["tail_inference"])

    r481 = json.loads((ROOT / "results" / "research_loop" / "r481_direct_md" / "formal_analysis.json").read_text(encoding="utf-8"))
    r481_profiles = {row["profile_id"] for row in r481["summaries"]}
    reversed_actor = [-value for value in effects_6["actor_main"]]
    negative_control = {
        "registered_inference_units": len(seeds),
        "incorrect_profile_as_independent_units": len(seeds) * len(profiles),
        "actor_direction_reversal_negates_effects": max(abs(a + b) for a, b in zip(effects_6["actor_main"], reversed_actor, strict=True)) == 0.0,
        "r481_historical_profile_overlap_with_r485_same_bank": len(r481_profiles & set(profiles)),
        "historical_denominator_reuse_rejected": not bool(r481_profiles & set(profiles)),
    }
    errors = []
    if identity_mismatches or reset_frequency_mismatches or projection_mismatches:
        errors.append("comparator_object_or_projection_mismatch")
    if max_direct_raw_law_error > 1.0e-7:
        errors.append("direct_law_mismatch")
    if primary_errors:
        errors.append(f"primary_inference:{primary_errors}")
    if tail_errors:
        errors.append(f"tail_inference:{tail_errors}")
    return {
        "schema_version": 1,
        "probe": "R485 pre-paper audit probe 03: comparator and factorial",
        "question": "Are the comparator object and seed-level source inference correctly matched?",
        "negative_control": negative_control,
        "comparator": {
            "direct_reference_trajectories": len(direct_records),
            "learned_trajectories_compared": learned_trajectories,
            "identity_mismatches": identity_mismatches,
            "reset_frequency_mismatches": reset_frequency_mismatches,
            "projection_mismatches": projection_mismatches,
            "max_projection_error": max_projection_error,
            "max_direct_raw_law_error": max_direct_raw_law_error,
            "same_action_shape_decoder_and_slew": not bool(projection_mismatches),
        },
        "factorial": {
            "rows": len(rows),
            "inference_unit": "training_seed",
            "seed_count": len(seeds),
            "profile_count_within_seed": len(profiles),
            "primary_6s_comparison_errors": primary_errors,
            "tail_30s_comparison_errors": tail_errors,
            "primary_holm_rejections": [name for name, row in formal["primary_inference"]["tests"].items() if row["holm"]["reject"]],
            "tail_holm_rejections": [name for name, row in formal["tail_inference"]["tests"].items() if row["holm"]["reject"]],
        },
        "errors": errors,
        "decision": "PASS_PROCEED_TO_MECHANISM_AND_AUTHORITY_AUDIT" if not errors else "P0_STOP",
        "elapsed_seconds": round(time.time() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["decision"] != "P0_STOP" else 2


if __name__ == "__main__":
    raise SystemExit(main())
