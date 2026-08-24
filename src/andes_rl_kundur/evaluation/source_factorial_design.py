"""Freeze and audit the prospective fresh-source factorial statistics.

Motivation: the confirmatory analysis must not infer its seed/profile roster or
Holm family from whatever result rows happen to exist.  ``build_power_plan``
uses the sealed historical bank for variance planning only; ``seed_effects``
and ``holm_decisions`` fail closed on incomplete registered inputs.

Usage: run this module to print the reproducible planning JSON, or import the
pure helpers from the formal aggregator.  Missing/duplicate/invalid cells,
unexpected roster members, tied exact ranks, and incomplete hypothesis
families raise ``ValueError``; no available-case or asymptotic fallback exists.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

MATERIALITY_RATIO = 1.10
FAMILYWISE_ALPHA = 0.05
HOLM_TESTS = 4
HOLM_WORST_THRESHOLD = FAMILYWISE_ALPHA / HOLM_TESTS
PRIMARY_METRIC = "disturbance_differential_energy"
PRIMARY_STAGE = "final"
POWER_TARGET = 0.80
POWER_SIMULATIONS = 200_000
POWER_RNG_SEED = 20260824

ALTERNATIVE_RATIOS = {
    "actor_main": 1.20,
    "critic_main": 1.20,
    "actor_x_critic": 1.30,
    "critic_x_reward": 1.25,
}
REGISTERED_EFFECTS = tuple(ALTERNATIVE_RATIOS)
PLANNING_SOURCE_SEEDS = tuple(range(401, 407))
FRESH_SEEDS = tuple(range(501, 527))
REGISTERED_PROFILES = (
    "canary_eval_a",
    "canary_eval_b",
    "canary_eval_c",
    "canary_eval_d",
)


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("cannot average an empty contrast")
    return float(sum(materialized) / len(materialized))


def seed_effects(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_seeds: Iterable[int],
    expected_profiles: Iterable[str],
    stage: str = PRIMARY_STAGE,
    metric: str = PRIMARY_METRIC,
) -> dict[str, dict[int, float]]:
    """Build the four registered equal-weight within-seed log contrasts.

    Every seed must contain every actor x critic x reward x profile cell.
    Missing, duplicate, nonfinite, or nonpositive outcomes invalidate the seed
    rather than being averaged on an available-case basis.
    """
    index: dict[tuple[int, str, str, int, str], float] = {}
    seeds = tuple(int(seed) for seed in expected_seeds)
    profiles = tuple(str(profile) for profile in expected_profiles)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("expected seed roster must be non-empty and unique")
    if not profiles or len(set(profiles)) != len(profiles):
        raise ValueError("expected profile roster must be non-empty and unique")
    for row in rows:
        if str(row["stage"]) != stage:
            continue
        key = (
            int(row["seed"]),
            str(row["actor_source"]),
            str(row["critic_source"]),
            int(row["reward_access"]),
            str(row["profile"]),
        )
        if key in index:
            raise ValueError(f"duplicate factorial cell: {key}")
        value = float(row[metric])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"invalid positive-loss endpoint for {key}: {value}")
        index[key] = value
    if not index:
        raise ValueError(f"no rows for stage={stage!r}")

    expected = {
        (seed, actor, critic, reward, profile)
        for seed in seeds
        for actor in ("N", "P")
        for critic in ("N", "P")
        for reward in (0, 1)
        for profile in profiles
    }
    missing = sorted(expected - set(index))
    if missing:
        raise ValueError(f"missing factorial cells; first={missing[0]}")
    unexpected = sorted(set(index) - expected)
    if unexpected:
        raise ValueError(f"unexpected factorial cells; first={unexpected[0]}")

    effects = {
        "actor_main": {},
        "critic_main": {},
        "actor_x_critic": {},
        "critic_x_reward": {},
    }
    for seed in sorted(seeds):
        def loss(actor: str, critic: str, reward: int, profile: str) -> float:
            return index[(seed, actor, critic, reward, profile)]

        effects["actor_main"][seed] = _mean(
            math.log(loss("P", critic, reward, profile) /
                     loss("N", critic, reward, profile))
            for critic in ("N", "P")
            for reward in (0, 1)
            for profile in sorted(profiles)
        )
        effects["critic_main"][seed] = _mean(
            math.log(loss(actor, "P", reward, profile) /
                     loss(actor, "N", reward, profile))
            for actor in ("N", "P")
            for reward in (0, 1)
            for profile in sorted(profiles)
        )
        effects["actor_x_critic"][seed] = _mean(
            math.log(loss("P", "N", reward, profile) /
                     loss("N", "N", reward, profile))
            - math.log(loss("P", "P", reward, profile) /
                       loss("N", "P", reward, profile))
            for reward in (0, 1)
            for profile in sorted(profiles)
        )
        effects["critic_x_reward"][seed] = _mean(
            math.log(loss(actor, "P", 1, profile) /
                     loss(actor, "N", 1, profile))
            - math.log(loss(actor, "P", 0, profile) /
                       loss(actor, "N", 0, profile))
            for actor in ("N", "P")
            for profile in sorted(profiles)
        )
    return effects


def _signed_rank_counts(n: int) -> list[int]:
    if n < 1:
        raise ValueError("n must be positive")
    counts = [1]
    for rank in range(1, n + 1):
        updated = [0] * (len(counts) + rank)
        for total, count in enumerate(counts):
            updated[total] += count
            updated[total + rank] += count
        counts = updated
    return counts


def exact_signed_rank_critical(n: int, alpha: float) -> int:
    """Smallest W+ whose exact one-sided null tail is at most alpha."""
    counts = _signed_rank_counts(n)
    tails = [0] * len(counts)
    running = 0
    for total in range(len(counts) - 1, -1, -1):
        running += counts[total]
        tails[total] = running
    denominator = 2**n
    for statistic, tail_count in enumerate(tails):
        if tail_count / denominator <= alpha:
            return statistic
    return n * (n + 1) // 2 + 1


def exact_signed_rank_p_one_sided(values: Iterable[float], null: float) -> float:
    """Exact upper-tail signed-rank p-value at a materiality boundary."""
    centered = np.asarray(list(values), dtype=float) - float(null)
    if centered.ndim != 1 or centered.size == 0 or not np.all(np.isfinite(centered)):
        raise ValueError("seed effects must be a non-empty finite vector")
    absolute = np.abs(centered)
    if np.any(absolute == 0.0) or len(np.unique(absolute)) != len(absolute):
        raise ValueError("zero differences or tied absolute ranks invalidate exact inference")
    order = np.argsort(absolute)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(centered) + 1)
    statistic = int(np.sum(ranks[centered > 0.0]))
    counts = _signed_rank_counts(len(centered))
    return float(sum(counts[statistic:]) / (2 ** len(centered)))


def holm_decisions(
    p_values: Mapping[str, float], *, alpha: float = FAMILYWISE_ALPHA
) -> dict[str, dict[str, float | bool]]:
    """Return raw/adjusted p-values and step-down Holm decisions."""
    if set(p_values) != set(REGISTERED_EFFECTS):
        raise ValueError(
            "Holm input must contain exactly the registered four hypotheses"
        )
    for name, value in p_values.items():
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"invalid p-value for {name}: {value}")
    ordered = sorted(p_values, key=lambda name: (p_values[name], name))
    result: dict[str, dict[str, float | bool]] = {}
    running_adjusted = 0.0
    prior_rejected = True
    total = len(ordered)
    for rank, name in enumerate(ordered):
        multiplier = total - rank
        threshold = alpha / multiplier
        running_adjusted = max(running_adjusted, multiplier * p_values[name])
        rejected = prior_rejected and p_values[name] <= threshold
        prior_rejected = rejected
        result[name] = {
            "raw_p": float(p_values[name]),
            "adjusted_p": min(1.0, float(running_adjusted)),
            "holm_threshold": float(threshold),
            "reject": bool(rejected),
        }
    return result


def _wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    estimate = successes / trials
    denominator = 1.0 + z * z / trials
    center = estimate + z * z / (2.0 * trials)
    spread = z * math.sqrt(
        estimate * (1.0 - estimate) / trials + z * z / (4.0 * trials * trials)
    )
    return float((center - spread) / denominator)


def simulate_signed_rank_power(
    *,
    n: int,
    alternative_log: float,
    null_log: float,
    sd: float,
    simulations: int,
    rng_seed: int,
) -> dict[str, float | int]:
    """Simulate power of the exact one-sided signed-rank boundary test."""
    if not math.isfinite(sd) or sd <= 0.0:
        raise ValueError("sd must be positive and finite")
    critical = exact_signed_rank_critical(n, HOLM_WORST_THRESHOLD)
    rng = np.random.default_rng(rng_seed)
    successes = 0
    standardized_shift = (alternative_log - null_log) / sd
    batch_size = 5_000
    rank_values = np.arange(1, n + 1)
    for start in range(0, simulations, batch_size):
        batch = min(batch_size, simulations - start)
        samples = rng.normal(
            loc=standardized_shift,
            scale=1.0,
            size=(batch, n),
        )
        order = np.argsort(np.abs(samples), axis=1)
        ranks = np.empty_like(order)
        np.put_along_axis(ranks, order, rank_values, axis=1)
        statistic = np.sum(ranks * (samples > 0.0), axis=1)
        successes += int(np.count_nonzero(statistic >= critical))
    return {
        "n": n,
        "critical_w_plus": critical,
        "power": successes / simulations,
        "power_wilson95_lower": _wilson_lower(successes, simulations),
        "simulations": simulations,
        "rng_seed": rng_seed,
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    return str(path.resolve().relative_to(root)).replace("\\", "/")


def build_power_plan(source_csv: Path) -> dict[str, Any]:
    """Build the prospective four-contrast sample-size artifact."""
    with source_csv.open("r", encoding="utf-8", newline="") as handle:
        effects = seed_effects(
            csv.DictReader(handle),
            expected_seeds=PLANNING_SOURCE_SEEDS,
            expected_profiles=REGISTERED_PROFILES,
        )
    old_summary = {
        name: {
            "seed_effects": [values[seed] for seed in sorted(values)],
            "mean": statistics.fmean(values.values()),
            "sample_sd": statistics.stdev(values.values()),
        }
        for name, values in effects.items()
    }
    main_sd_bound = max(
        old_summary[name]["sample_sd"]
        for name in ("actor_main", "critic_main")
    )
    interaction_sd_bound = max(
        old_summary[name]["sample_sd"]
        for name in ("actor_x_critic", "critic_x_reward")
    )
    sd_bounds = {
        "actor_main": main_sd_bound,
        "critic_main": main_sd_bound,
        "actor_x_critic": interaction_sd_bound,
        "critic_x_reward": interaction_sd_bound,
    }
    null_log = math.log(MATERIALITY_RATIO)
    requirements: dict[str, dict[str, Any]] = {}
    for effect_index, (name, ratio) in enumerate(ALTERNATIVE_RATIOS.items()):
        for n in range(7, 129):
            result = simulate_signed_rank_power(
                n=n,
                alternative_log=math.log(ratio),
                null_log=null_log,
                sd=sd_bounds[name],
                simulations=POWER_SIMULATIONS,
                rng_seed=POWER_RNG_SEED + effect_index * 1_000 + n,
            )
            if result["power_wilson95_lower"] >= POWER_TARGET:
                requirements[name] = {
                    "alternative_ratio": ratio,
                    "alternative_log": math.log(ratio),
                    "sd_bound": sd_bounds[name],
                    "required_n": n,
                    "power_at_required_n": result,
                }
                break
        else:
            raise RuntimeError(f"power target not reached for {name}")
    n_star = max(row["required_n"] for row in requirements.values())
    power_at_n_star = {
        name: simulate_signed_rank_power(
            n=n_star,
            alternative_log=row["alternative_log"],
            null_log=null_log,
            sd=row["sd_bound"],
            simulations=POWER_SIMULATIONS,
            rng_seed=POWER_RNG_SEED + 10_000 + index,
        )
        for index, (name, row) in enumerate(requirements.items())
    }
    return {
        "schema_version": 1,
        "round": "R478",
        "prospective_only": True,
        "constructed_new_training_outcomes": False,
        "source": {
            "path": _repo_relative(source_csv),
            "sha256": _sha256_file(source_csv),
            "use": "variance and direction planning only; never pooled",
            "stage": PRIMARY_STAGE,
            "metric": PRIMARY_METRIC,
        },
        "planner": {
            "path": _repo_relative(Path(__file__)),
            "sha256": _sha256_file(Path(__file__)),
        },
        "estimand": {
            "unit": "training seed",
            "fresh_seed_roster": list(FRESH_SEEDS),
            "profile_roster": list(REGISTERED_PROFILES),
            "registered_hypotheses": list(REGISTERED_EFFECTS),
            "profile_weights": "equal within seed",
            "nuisance_factor_weights": "equal within seed",
            "missing_rule": "any missing/invalid matched cell invalidates the whole seed",
            "available_case_analysis": False,
        },
        "inference": {
            "test": "exact one-sided Wilcoxon signed-rank at the materiality boundary",
            "familywise_alpha": FAMILYWISE_ALPHA,
            "holm_tests": HOLM_TESTS,
            "power_planning_threshold": HOLM_WORST_THRESHOLD,
            "materiality_ratio": MATERIALITY_RATIO,
            "materiality_log": null_log,
            "assumptions": [
                "independent training seeds",
                "continuous symmetric location-shift distribution of boundary-centered seed effects",
                "no zero differences or tied absolute ranks; otherwise inferential verdict is invalid",
            ],
            "non_rejection": "not equivalence and not evidence of zero effect",
        },
        "power_model": (
            "independent normal location shifts on the boundary-centred "
            "seed effects; exact signed-rank rejection region"
        ),
        "old_descriptive_effects": old_summary,
        "variance_rule": {
            "main_effects": "maximum old sample SD across actor and critic main effects",
            "interactions": "maximum old sample SD across both interactions",
        },
        "alternatives": {
            "actor_main": "true 20% ratio; prove above the 10% bar",
            "critic_main": "true 20% ratio; prove above the 10% bar",
            "actor_x_critic": "positive 30% ratio-of-ratios, rounded below the old descriptive mean",
            "critic_x_reward": "positive 25% ratio-of-ratios, rounded below the old descriptive mean",
        },
        "requirements": requirements,
        "n_star": n_star,
        "power_at_n_star": power_at_n_star,
        "workload": {
            "fresh_training_cells": 8 * n_star,
            "arm_stage_evaluation_jobs": 16,
            "total_factorial_jobs": 8 * n_star + 16,
        },
        "execution_queue_status": "DEFERRED-UNTIL-UPSTREAM-CONCLUSIONS-SURVIVE",
        "formal_execution_ready": False,
        "remaining_gates": [
            "corrected physical regression baseline",
            "all offline and real-ANDES invariants green",
            "measured capacity/runtime/memory/disk budget on final sources",
            "frozen source map and dual review",
            "formal seal and explicit owner approval",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    source = (
        root
        / "paper/yang_md_decoupling_marl/manuscript/supplement/"
        "r477_arm_seed_profile.csv"
    )
    text = json.dumps(build_power_plan(source), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
        return 0
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    output.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if sidecar.exists():
        raise FileExistsError(f"refusing to overwrite: {sidecar}")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
