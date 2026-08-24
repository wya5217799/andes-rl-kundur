"""Build deterministic R477 reproducibility tables from sealed artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
R477 = ROOT / "results/research_loop/r477_u2_confirmatory"
R413 = ROOT / "results/research_loop/r413_topology_robustness"
SUPPLEMENT = Path(__file__).resolve().parent / "supplement"
MANUSCRIPT = Path(__file__).resolve().parent / "main.tex"
STAGES = ("half", "final")
METRICS = ("disturbance_differential_energy", "off_diagonal_response_energy")
TRANSFORM = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0), 0.0, 0.0],
        [0.0, 0.0, 1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0)],
    ],
    dtype=float,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty table: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    Path(f"{path}.sha256").write_text(
        f"{sha256(path)}  {path.name}\n", encoding="ascii"
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    Path(f"{path}.sha256").write_text(
        f"{sha256(path)}  {path.name}\n", encoding="ascii"
    )


def endpoints(records: list[dict[str, Any]]) -> dict[str, float]:
    pairs: dict[str, dict[str, Any]] = {}
    for kind in ("common", "differential", "localized"):
        positive = next(
            row for row in records if row["pair_kind"] == kind and row["sign"] == "positive"
        )
        negative = next(
            row for row in records if row["pair_kind"] == kind and row["sign"] == "negative"
        )
        if not positive["completed"] or positive["tds_failed"]:
            raise RuntimeError(f"invalid positive record: {positive['scenario_id']}")
        if not negative["completed"] or negative["tds_failed"]:
            raise RuntimeError(f"invalid negative record: {negative['scenario_id']}")
        pos = np.asarray(
            [step["freq_hz_physical"] for step in positive["steps"]], dtype=float
        ) - 60.0
        neg = np.asarray(
            [step["freq_hz_physical"] for step in negative["steps"]], dtype=float
        ) - 60.0
        odd = 0.5 * (pos - neg)
        pairs[kind] = {
            "common": np.mean(odd, axis=1),
            "differential": odd @ TRANSFORM.T,
            "magnitude": float(positive["magnitude"]),
        }
    dt = 0.2
    common = pairs["common"]
    differential = pairs["differential"]
    cross = (
        dt
        * float(np.sum(np.mean(common["differential"] ** 2, axis=1)))
        / common["magnitude"] ** 2
        + dt
        * float(np.sum(differential["common"] ** 2))
        / differential["magnitude"] ** 2
    )
    disturbance = sum(
        dt
        * float(np.sum(np.mean(pairs[kind]["differential"] ** 2, axis=1)))
        / pairs[kind]["magnitude"] ** 2
        for kind in pairs
    )
    return {
        "disturbance_differential_energy": disturbance,
        "off_diagonal_response_energy": cross,
    }


def build_endpoint_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        stage_root = R477 / "eval" / stage
        for arm_dir in sorted(path for path in stage_root.iterdir() if path.is_dir()):
            for seed_dir in sorted(path for path in arm_dir.iterdir() if path.is_dir()):
                seed = int(seed_dir.name.removeprefix("seed"))
                for profile_path in sorted(seed_dir.glob("canary_eval_?.json")):
                    payload = read_hashed_json(profile_path)
                    values = endpoints(payload["records"])
                    actor, critic, reward = arm_dir.name.split("_")
                    rows.append(
                        {
                            "stage": stage,
                            "arm": arm_dir.name,
                            "actor_source": actor[-1].upper(),
                            "critic_source": critic[-1].upper(),
                            "reward_access": reward[-1],
                            "seed": seed,
                            "profile": profile_path.stem,
                            **values,
                            "source_sha256": sha256(profile_path),
                        }
                    )
    if len(rows) != 384:
        raise RuntimeError(f"expected 384 stage-arm-seed-profile rows, got {len(rows)}")
    return rows


def build_arm_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for stage in STAGES:
        for arm in sorted({row["arm"] for row in rows}):
            selected = [row for row in rows if row["stage"] == stage and row["arm"] == arm]
            summary: dict[str, Any] = {"stage": stage, "arm": arm, "n_seed_profiles": len(selected)}
            for metric in METRICS:
                values = np.asarray([row[metric] for row in selected], dtype=float)
                summary[f"{metric}_arithmetic_mean"] = float(np.mean(values))
                summary[f"{metric}_geometric_mean"] = float(np.exp(np.mean(np.log(values))))
            output.append(summary)
    return output


def build_reward_conditioned(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    primary = "disturbance_differential_energy"
    index = {
        (row["stage"], row["arm"], row["seed"], row["profile"]): float(row[primary])
        for row in rows
    }
    seeds = sorted({int(row["seed"]) for row in rows})
    profiles = sorted({str(row["profile"]) for row in rows})
    for stage in STAGES:
        for reward in ("r0", "r1"):
            for factor in ("actor", "critic"):
                for seed in seeds:
                    contrasts: list[float] = []
                    for profile in profiles:
                        if factor == "actor":
                            pairs = [
                                (f"an_{critic}_{reward}", f"ap_{critic}_{reward}")
                                for critic in ("cn", "cp")
                            ]
                        else:
                            pairs = [
                                (f"{actor}_cn_{reward}", f"{actor}_cp_{reward}")
                                for actor in ("an", "ap")
                            ]
                        for authentic, placebo in pairs:
                            n_value = index[(stage, authentic, seed, profile)]
                            p_value = index[(stage, placebo, seed, profile)]
                            contrasts.append(math.log(p_value / n_value))
                    mean_log = float(np.mean(contrasts))
                    output.append(
                        {
                            "stage": stage,
                            "reward_access": reward[-1],
                            "factor": factor,
                            "seed": seed,
                            "matched_profile_contrasts": len(contrasts),
                            "mean_log_effect": mean_log,
                            "signed_geometric_effect": math.expm1(mean_log),
                        }
                    )
    return output


def build_conditioned_effects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose the interaction-sensitive contrasts hidden by marginal effects."""

    primary = "disturbance_differential_energy"
    index = {
        (row["stage"], row["arm"], row["seed"], row["profile"]): float(row[primary])
        for row in rows
    }
    seeds = sorted({int(row["seed"]) for row in rows})
    profiles = sorted({str(row["profile"]) for row in rows})
    output: list[dict[str, Any]] = []

    def append_contrast(
        *, stage: str, contrast: str, condition: str, seed: int, pairs: list[tuple[str, str]]
    ) -> None:
        values = [
            math.log(index[(stage, placebo, seed, profile)] / index[(stage, authentic, seed, profile)])
            for profile in profiles
            for authentic, placebo in pairs
        ]
        mean_log = float(np.mean(values))
        output.append(
            {
                "stage": stage,
                "contrast": contrast,
                "condition": condition,
                "seed": seed,
                "matched_profile_contrasts": len(values),
                "mean_log_effect": mean_log,
                "signed_geometric_effect": math.expm1(mean_log),
            }
        )

    for stage in STAGES:
        for seed in seeds:
            for critic in ("cn", "cp"):
                append_contrast(
                    stage=stage,
                    contrast="actor_source_P_over_N",
                    condition=f"critic_source={critic[-1].upper()}",
                    seed=seed,
                    pairs=[
                        (f"an_{critic}_{reward}", f"ap_{critic}_{reward}")
                        for reward in ("r0", "r1")
                    ],
                )
            for reward in ("r0", "r1"):
                append_contrast(
                    stage=stage,
                    contrast="critic_source_P_over_N",
                    condition=f"reward_access={reward[-1]}",
                    seed=seed,
                    pairs=[
                        (f"{actor}_cn_{reward}", f"{actor}_cp_{reward}")
                        for actor in ("an", "ap")
                    ],
                )

    for stage in STAGES:
        stage_rows = [row for row in output if row["stage"] == stage]
        for contrast in sorted({str(row["contrast"]) for row in stage_rows}):
            contrast_rows = [row for row in stage_rows if row["contrast"] == contrast]
            for condition in sorted({str(row["condition"]) for row in contrast_rows}):
                selected = [
                    float(row["mean_log_effect"])
                    for row in contrast_rows
                    if row["condition"] == condition
                ]
                mean_log = float(np.mean(selected))
                output.append(
                    {
                        "stage": stage,
                        "contrast": contrast,
                        "condition": condition,
                        "seed": "across_seed_mean",
                        "matched_profile_contrasts": 8,
                        "mean_log_effect": mean_log,
                        "signed_geometric_effect": math.expm1(mean_log),
                    }
                )
    return output


def build_carryovers() -> list[dict[str, Any]]:
    imported = read_hashed_json(R477 / "r476_shard_import.json")
    entries = imported["hardlink_entries"]
    rows: list[dict[str, Any]] = []
    for cell in imported["imported_training_shards"]:
        arm, seed_text = cell.split("|")
        seed = int(seed_text)
        prefix = f"results/research_loop/r477_u2_confirmatory/train/{arm}/seed{seed}/"
        hashes = {
            Path(entry["target"]).name: entry
            for entry in entries
            if entry["target"].startswith(prefix) and not entry["target"].endswith(".sha256")
        }
        manifest = read_hashed_json(R477 / "train" / arm / f"seed{seed}" / "manifest.json")
        rows.append(
            {
                "source_round": imported["source_round"],
                "arm": arm,
                "seed": seed,
                "interaction_steps": manifest["interaction_steps"],
                "valid": manifest["valid"],
                "actor_source": manifest["factors"]["actor_source"],
                "critic_source": manifest["factors"]["critic_source"],
                "reward_access": manifest["factors"]["reward_access"],
                "base_state_sha256": manifest["base_state_sha256"],
                "reward_function_sha256": manifest["reward_function_sha256"],
                "manifest_sha256": hashes["manifest.json"]["sha256"],
                "half_checkpoint_sha256": hashes["half.pt"]["sha256"],
                "final_checkpoint_sha256": hashes["final.pt"]["sha256"],
                "curves_sha256": hashes["full_curves.npz"]["sha256"],
                "same_inode": all(entry["same_inode"] for entry in hashes.values()),
                "source_manifest_path": hashes["manifest.json"]["source"],
                "target_manifest_path": hashes["manifest.json"]["target"],
            }
        )
    if len(rows) != 16:
        raise RuntimeError(f"expected 16 carryover rows, got {len(rows)}")
    return rows


def build_training_stability(carryovers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    carried = {(str(row["arm"]), int(row["seed"])) for row in carryovers}
    rows: list[dict[str, Any]] = []
    for arm_dir in sorted(path for path in (R477 / "train").iterdir() if path.is_dir()):
        for seed_dir in sorted(path for path in arm_dir.iterdir() if path.is_dir()):
            manifest = read_hashed_json(seed_dir / "manifest.json")
            row: dict[str, Any] = {
                "arm": arm_dir.name,
                "seed": int(manifest["training_seed"]),
                "artifact_round": manifest["round"],
                "origin": "carryover" if (arm_dir.name, int(manifest["training_seed"])) in carried else "fresh",
                "interaction_steps": int(manifest["interaction_steps"]),
            }
            for kind in ("actor_loss", "critic_loss"):
                stability = manifest["stability"][kind]
                row[f"{kind}_previous_decile_median_abs"] = stability[
                    "previous_decile_median"
                ]
                row[f"{kind}_final_decile_median_abs"] = stability[
                    "final_decile_median"
                ]
                row[f"{kind}_absolute_log_ratio"] = stability["absolute_log_ratio"]
                row[f"{kind}_stable"] = stability["stable"]
            rows.append(row)
    if len(rows) != 48:
        raise RuntimeError(f"expected 48 stability rows, got {len(rows)}")
    return rows


def build_profile_rows() -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT / "src"))
    from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: PLC0415
        build_contract as build_learner_contract,
    )
    from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: PLC0415
        build_contract as build_deterministic_contract,
    )

    rows: list[dict[str, Any]] = []
    for bank, contract in (
        ("deterministic_comparator", build_deterministic_contract()),
        ("learner_confirmatory", build_learner_contract()),
    ):
        for profile in contract["profiles"]:
            probe = float(profile["probe_magnitude"])
            localized = float(profile["localized_magnitude"])
            location = str(profile["localized_location"])
            rows.append(
                {
                    "bank": bank,
                    "profile_id": profile["profile_id"],
                    "split": profile["split"],
                    "baseline_m0_s": json.dumps(profile["baseline_m0"], separators=(",", ":")),
                    "baseline_d0_pu": json.dumps(profile["baseline_d0"], separators=(",", ":")),
                    "steady_loads_system_pu": json.dumps(
                        profile["steady_loads"], sort_keys=True, separators=(",", ":")
                    ),
                    "common_input_system_pu": json.dumps(
                        [probe / 4.0] * 4, separators=(",", ":")
                    ),
                    "differential_input_system_pu": json.dumps(
                        [probe / 4.0, probe / 4.0, -probe / 4.0, -probe / 4.0],
                        separators=(",", ":"),
                    ),
                    "localized_location": location,
                    "localized_input_system_pu": json.dumps(
                        {location: localized}, separators=(",", ":")
                    ),
                }
            )
    return rows


def build_topology_rows() -> list[dict[str, Any]]:
    payload = read_hashed_json(R413 / "formal_analysis.json")
    rows: list[dict[str, Any]] = []
    for variant_id, result in payload["variants"].items():
        variant = result["variant"]
        eig = result["eig_gate"]
        rows.append(
            {
                "variant_id": variant_id,
                "kind": variant["kind"],
                "line_id": variant.get("line_idx", ""),
                "reactance_factor": variant.get("factor", ""),
                "equilibrium_screen_pass": eig["passed"],
                "initialization_tolerance": eig.get("initialization_tolerance", ""),
                "positive_real_tolerance": eig.get("positive_real_tolerance", ""),
                "performance_scored": bool(result["summary"]["passed"]),
                "exclusion_reason": "" if eig["passed"] else eig.get("failure", "pre-performance equilibrium gate failed"),
            }
        )
    return rows


def build_reproducibility_contract() -> dict[str, Any]:
    sources = [
        ROOT / "pyproject.toml",
        ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        ROOT / "scripts/run_r475_u2_confirmatory.py",
        ROOT / "scripts/run_r476_u2_confirmatory.py",
        ROOT / "scripts/run_r477_u2_confirmatory.py",
    ]
    return {
        "scope": "frozen direct-M/D comparator and R477 confirmatory evaluation",
        "software": {
            "andes": "2.0.0",
            "python_torch_numpy_exact_versions": "not recorded in the sealed R477 artifacts",
            "dependency_floor_source": "pyproject.toml",
        },
        "deterministic_comparator": {
            "candidate_gain_grid": [0.5, 1.0, 2.0],
            "selected_inertia_gain": 2.0,
            "selected_damping_gain": 2.0,
            "inertia_target": "tanh(k_M*(|f_i|+|rocof_i|-mean_j(|f_j|+|rocof_j|)))",
            "damping_target": "tanh(k_D*(|f_i|+mean_j|f_i-f_j|+mean_j|rocof_i-rocof_j|))",
            "projector": "elementwise [-1,1] clip with per-update slew <=0.25",
        },
        "probe_vectors": {
            "common": "epsilon_c/4 * [1,1,1,1]",
            "differential": "epsilon_d/4 * [1,1,-1,-1]",
            "localized": "epsilon_l * e_j",
        },
        "endpoint_units": "Hz^2 s / pu^2; discrete L2 response energy, not joules or a Lyapunov/storage function",
        "source_files": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for path in sources
        ],
    }


def build_asymmetric_sensitivity() -> dict[str, Any]:
    """Exact seed sign sensitivity for a median, not the primary mean estimand."""

    analysis = read_hashed_json(R477 / "formal_analysis.json")
    threshold = float(
        analysis["primary_materiality_tests"]["actor"]["materiality_log"]
    )
    results: dict[str, Any] = {}
    for factor in ("actor", "critic"):
        effects = [
            float(value)
            for value in analysis["primary_materiality_tests"][factor][
                "paired_log_effects"
            ]
        ]
        count = sum(value > threshold for value in effects)
        p_value = sum(math.comb(len(effects), k) for k in range(count, len(effects) + 1)) / (
            2 ** len(effects)
        )
        results[factor] = {
            "seed_effects_above_log_1p10": count,
            "seed_count": len(effects),
            "one_sided_exact_binomial_p": p_value,
        }
    return {
        "estimand": "seed median source effect above log(1.10)",
        "null_boundary": "Pr(seed effect > log(1.10)) <= 0.5",
        "purpose": (
            "asymmetric-distribution sensitivity only; it does not replace the "
            "primary across-seed mean estimand"
        ),
        "results": results,
    }


def write_flow(endpoint_rows: list[dict[str, Any]], carryovers: list[dict[str, Any]]) -> None:
    analysis = read_hashed_json(R477 / "formal_analysis.json")
    carryover_actor_n = sum(row["actor_source"] == "N" for row in carryovers)
    carryover_actor_p = sum(row["actor_source"] == "P" for row in carryovers)
    half_actor = analysis["optimization"]["direction_flips"]["actor"]["half_mean"]
    final_actor = analysis["optimization"]["direction_flips"]["actor"]["final_mean"]
    half_critic = analysis["optimization"]["direction_flips"]["critic"]["half_mean"]
    final_critic = analysis["optimization"]["direction_flips"]["critic"]["final_mean"]
    text = f"""# R477 run flow and audit summary

- Registered training cells: 48 (8 arms x 6 seeds).
- Hash-verified carryovers: {len(carryovers)}.
- Freshly trained cells: {48 - len(carryovers)}.
- Completed valid training cells: 48.
- Invalid training cells: 0.
- Incomplete or missing training cells: {len(analysis['missing_shards'])}.
- Evaluation jobs: 16 (8 arms x half/final checkpoints).
- Complete stage-arm-seed-profile summaries: {len(endpoint_rows)}.
- Formal design/execution/integrity: {analysis['classification']['design']} / {analysis['classification']['execution']} / {analysis['classification']['integrity']}.
- Formal verdict: {analysis['classification']['verdict']}.
- Carryover allocation by actor source: N={carryover_actor_n}, P={carryover_actor_p}.
- Half/final marginal mean log effects: actor {half_actor:.9f} / {final_actor:.9f}; critic {half_critic:.9f} / {final_critic:.9f}.
- Curve-stability rule: for each actor/critic loss, compare median absolute values
  in the penultimate and final training deciles; require absolute log-ratio <=
  log(1.25). All 96 arm-seed-loss rows pass. This rule does not establish that
  the source-effect estimand itself plateaued.

The 16 carryovers all occupy actor-source N cells. Their hashes, factor identity,
43,200-step completeness, reward hash, base-state hash, and NTFS inode identity
pass the frozen reuse gate, but no same-round retraining comparison was performed.
Consequently, arithmetic replay is verified while a batch-by-actor-source effect
cannot be empirically excluded from this sealed dataset.

Generated only from SHA-256-verified R477 JSON artifacts. No training,
simulation, retuning, case exclusion, or endpoint change is performed here.
"""
    path = SUPPLEMENT / "r477_run_flow.md"
    path.write_text(text, encoding="utf-8")
    Path(f"{path}.sha256").write_text(f"{sha256(path)}  {path.name}\n", encoding="ascii")


def write_supplement_manifest() -> None:
    generated = sorted(
        path
        for path in SUPPLEMENT.iterdir()
        if path.is_file()
        and path.name not in {"supplement_manifest.json", "supplement_manifest.json.sha256"}
        and not path.name.endswith(".sha256")
    )
    upstream = [
        R477 / "formal_analysis.json",
        R477 / "formal_manifest.json",
        R477 / "r476_shard_import.json",
        R413 / "formal_analysis.json",
    ]
    write_json(
        SUPPLEMENT / "supplement_manifest.json",
        {
            "schema_version": 1,
            "path_base": "repository_root",
            "manuscript": {
                "path": MANUSCRIPT.relative_to(ROOT).as_posix(),
                "sha256": sha256(MANUSCRIPT),
            },
            "generator": {
                "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                "sha256": sha256(Path(__file__)),
            },
            "generated_files": [
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
                for path in generated
            ],
            "upstream_evidence": [
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
                for path in upstream
            ],
            "scientific_scope": (
                "The manifest binds the manuscript to deterministic exports of sealed "
                "R477/R413 evidence. It performs no training, simulation, retuning, "
                "case exclusion, or endpoint modification."
            ),
        },
    )


def main() -> None:
    SUPPLEMENT.mkdir(parents=True, exist_ok=True)
    endpoint_rows = build_endpoint_rows()
    carryovers = build_carryovers()
    write_csv(SUPPLEMENT / "r477_arm_seed_profile.csv", endpoint_rows)
    write_csv(SUPPLEMENT / "r477_arm_summary.csv", build_arm_summary(endpoint_rows))
    write_csv(
        SUPPLEMENT / "r477_reward_conditioned_effects.csv",
        build_reward_conditioned(endpoint_rows),
    )
    write_csv(
        SUPPLEMENT / "r477_conditioned_effects.csv",
        build_conditioned_effects(endpoint_rows),
    )
    write_csv(SUPPLEMENT / "r477_carryover_manifest.csv", carryovers)
    write_csv(
        SUPPLEMENT / "r477_training_stability.csv",
        build_training_stability(carryovers),
    )
    write_csv(SUPPLEMENT / "frozen_profile_bank.csv", build_profile_rows())
    write_csv(SUPPLEMENT / "r413_topology_variants.csv", build_topology_rows())
    write_json(
        SUPPLEMENT / "reproducibility_contract.json",
        build_reproducibility_contract(),
    )
    write_json(
        SUPPLEMENT / "r477_asymmetric_sensitivity.json",
        build_asymmetric_sensitivity(),
    )
    write_flow(endpoint_rows, carryovers)
    write_supplement_manifest()


if __name__ == "__main__":
    main()
