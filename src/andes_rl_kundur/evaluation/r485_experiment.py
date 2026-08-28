"""R485 authority and analysis seam shared by the thin round adapter."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile
from andes_rl_kundur.evaluation.r482_analysis import (
    SYMMETRY_SKEW_THRESHOLD,
    symmetry_skew,
)
from andes_rl_kundur.evaluation.r484_tail_guard import (
    classify_deterministic_tail,
    classify_learned_guard,
    summarise_30s_profile,
)
from andes_rl_kundur.evaluation.source_factorial_design import (
    REGISTERED_EFFECTS,
    exact_signed_rank_p_one_sided,
    holm_decisions,
    seed_effects,
)
from andes_rl_kundur.evaluation.u2_confirmatory import (
    read_hashed_json,
    verify_formal_seal,
)

ROUND_ID = "R485"
REFERENCE_ARMS = ("zero", "local_neighbour_md_km2_kd2")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def extract_prefix(record: Mapping[str, Any]) -> dict[str, Any]:
    steps = record.get("steps")
    if not isinstance(steps, list) or len(steps) != 150:
        raise ValueError("R485 prefix requires one complete 150-step trace")
    result = copy.deepcopy(dict(record))
    result.update(
        steps=copy.deepcopy(steps[:30]),
        completed_steps=30,
        completed=True,
        derived_from_30s_trace=True,
        source_trace_steps=150,
    )
    return result


def assess_learner_admissibility(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Outcome-blind gate: numerical learning health, never endpoint quality."""

    checks = {
        "weights_changed": metrics.get("weights_changed") is True,
        "update_count": int(metrics.get("update_count", -1)) == 43_200 - 255,
        "all_finite": metrics.get("all_finite") is True,
        "actor_grad_nonzero": float(metrics.get("actor_grad_nonzero_fraction", 0.0)) >= 0.99,
        "reward_variation": float(metrics.get("reward_std", 0.0)) > 1.0e-8,
        "td_target_variation": float(metrics.get("td_target_std", 0.0)) > 1.0e-8,
        "policy_state_sensitivity": float(metrics.get("policy_state_sensitivity", 0.0)) > 1.0e-6,
        "executed_action_variation": float(metrics.get("executed_action_std", 0.0)) > 1.0e-6,
        "not_jointly_saturated": float(metrics.get("action_saturation_fraction", 1.0)) < 0.999,
        "log_std_not_frozen": float(metrics.get("log_std_at_lower_bound_fraction", 1.0)) < 0.999,
        "routing_oracle": metrics.get("routing_oracle_passed") is True,
        "executed_action_bellman": metrics.get("executed_action_bellman_passed") is True,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "alpha_at_floor": metrics.get("alpha_at_floor") is True,
        "alpha_floor_alone_is_failure": False,
    }


def objective_gate_flags(probe: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "routing_oracle_passed": bool(
            probe.get("replay_actor_rows_are_canonical")
            and probe.get("replay_critic_rows_are_canonical")
        ),
        "executed_action_bellman_passed": bool(
            probe.get("current_critic_uses_executed_action")
            and probe.get("target_critic_uses_projected_action")
            and probe.get("actor_critic_uses_projected_action")
        ),
    }


def run_objective_semantics_probe(
    *,
    new_member: Callable[[], Any],
    tensor_hash: Callable[[Any], str],
    canonicalize: Callable[[Mapping[int, np.ndarray]], np.ndarray],
    route_source: Callable[[np.ndarray, np.ndarray, str], np.ndarray],
) -> dict[str, Any]:
    """Probe the registered routing and executed-action Bellman path."""

    import torch

    np.random.seed(485)
    torch.manual_seed(485)
    member = new_member()
    before = tensor_hash(member)
    first_actor = first_critic = None
    for index in range(member.batch_size):
        raw_observation = {
            actor: np.asarray(
                [actor + index / 1000.0, 0.01, -0.02, 0.03, -0.04, 0.05, -0.06],
                dtype=np.float32,
            )
            for actor in range(4)
        }
        canonical = canonicalize(raw_observation)
        donor = np.roll(canonical, 2, axis=0)
        actor_row = route_source(canonical, donor, "N")[0]
        critic_row = route_source(canonical, donor, "P")[0]
        previous = np.asarray([0.05, -0.05], dtype=np.float32)
        raw_action = np.asarray([0.4, -0.4], dtype=np.float32)
        executed = member.execute_action(previous, raw_action)
        member.store_source_transition(
            actor_row,
            critic_row,
            previous,
            raw_action,
            executed,
            -0.1 - index / 1000.0,
            actor_row + 0.001,
            critic_row - 0.001,
            False,
        )
        if index == 0:
            first_actor, first_critic = actor_row.copy(), critic_row.copy()
    batch = member.buffer.sample(
        member.batch_size, "cpu", indices=np.arange(member.batch_size)
    )
    torch.manual_seed(486)
    paths = member.source_loss_inputs(batch, deterministic_target=True)
    diagnostics = member.update()
    result = {
        "replay_actor_rows_are_canonical": bool(np.array_equal(member.buffer.actor_obs[0], first_actor)),
        "replay_critic_rows_are_canonical": bool(np.array_equal(member.buffer.critic_obs[0], first_critic)),
        "current_critic_uses_executed_action": bool(torch.equal(paths["critic_current_action_input"], batch["executed_actions"])),
        "target_critic_uses_projected_action": bool(torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])),
        "actor_critic_uses_projected_action": bool(torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])),
        "weights_changed": tensor_hash(member) != before,
        "update_finite": bool(diagnostics and all(math.isfinite(value) for value in diagnostics.values())),
    }
    result["passed"] = all(result.values())
    return result


def learner_metrics(
    policy: Any,
    initial_hashes: Sequence[str],
    curves: Mapping[str, Sequence[float]],
    rewards: Sequence[np.ndarray],
    actions: Sequence[np.ndarray],
    update_count: int,
    objective_probe: Mapping[str, Any],
    tensor_hash: Callable[[Any], str],
) -> dict[str, Any]:
    import torch

    td_targets: list[np.ndarray] = []
    sensitivities: list[float] = []
    lower = total = 0
    for member in policy.members:
        batch = member.buffer.sample(256, "cpu", indices=np.arange(256))
        paths = member.source_loss_inputs(batch, deterministic_target=True)
        td_targets.append(paths["td_target"].detach().cpu().numpy())
        with torch.no_grad():
            mean, log_std = member.actor(paths["actor_state"])
            deterministic = torch.tanh(mean).cpu().numpy()
            log_std_np = log_std.cpu().numpy()
        sensitivities.append(float(np.std(deterministic, axis=0).mean()))
        lower += int(np.count_nonzero(log_std_np <= -20.0 + 1.0e-6))
        total += int(log_std_np.size)
    action_array = np.asarray(actions, dtype=float)
    reward_array = np.asarray(rewards, dtype=float)
    grad = np.asarray(curves["actor_grad_norm"], dtype=float)
    metrics = {
        "weights_changed": all(tensor_hash(member) != initial_hashes[index] for index, member in enumerate(policy.members)),
        "update_count": update_count,
        "all_finite": bool(np.all(np.isfinite(action_array)) and np.all(np.isfinite(reward_array)) and all(np.all(np.isfinite(values)) for values in curves.values())),
        "actor_grad_nonzero_fraction": float(np.mean(grad > 1.0e-12)),
        "reward_std": float(np.std(reward_array)),
        "td_target_std": float(np.std(np.concatenate(td_targets))),
        "policy_state_sensitivity": min(sensitivities),
        "executed_action_std": min(float(np.std(action_array[:, index])) for index in range(4)),
        "action_saturation_fraction": float(np.mean(np.abs(action_array) >= 0.999)),
        "log_std_at_lower_bound_fraction": lower / total,
        "alpha_at_floor": all(math.isclose(float(member.alpha.detach()), 0.005, abs_tol=1.0e-9) for member in policy.members),
        **objective_gate_flags(objective_probe),
    }
    return {**metrics, "assessment": assess_learner_admissibility(metrics)}


def evaluate_trajectory(
    *,
    env: Any,
    scenario: Mapping[str, Any],
    scenario_index: int,
    transform: np.ndarray,
    learned: bool,
    policy: Any,
    factors: Mapping[str, Any] | None,
    donors: np.ndarray | None,
    donor_index: Mapping[str, int] | None,
    controller: Any,
    canonicalize: Callable[[Mapping[int, np.ndarray]], np.ndarray],
    route_source: Callable[[np.ndarray, np.ndarray, str], np.ndarray],
    direct_action: Callable[[np.ndarray], np.ndarray],
    reward_function: Callable[..., Any],
) -> dict[str, Any]:
    """Execute one registered deterministic 150-step trajectory."""

    observation = env.reset(delta_u=dict(scenario["delta_u"]))
    positions = list(env._vsg_pos)
    identity = {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in positions],
        "obs_dim": int(env.OBS_DIM),
        "control_nominal_frequency_hz": float(env.FN),
        "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }
    initial_frequency = (
        np.asarray(env._get_vsg_omega(), dtype=float)
        * float(env.andes_nominal_frequency_hz)
    ).tolist()
    previous = np.zeros((4, 2), dtype=np.float32)
    if not learned and controller is not None:
        controller.reset()
    steps: list[dict[str, Any]] = []
    tds_failed = False
    for step_index in range(150):
        raw_observation = {
            index: np.asarray(observation[index], dtype=np.float32).copy()
            for index in range(4)
        }
        canonical = canonicalize(raw_observation)
        if learned:
            if policy is None or factors is None or donors is None or donor_index is None:
                raise RuntimeError("learned trajectory inputs are incomplete")
            donor = donors[
                donor_index[str(scenario["scenario_id"])],
                1 - scenario_index % 2,
                step_index,
            ]
            raw, executed = policy.act(
                route_source(canonical, donor, str(factors["actor_source"])),
                previous,
                deterministic=True,
            )
        elif controller is None:
            raw = executed = np.zeros((4, 2), dtype=np.float32)
        else:
            raw = direct_action(canonical)
            executed = controller.act({index: canonical[index] for index in range(4)})
        observation, _reward, done, info = env.step(
            {index: executed[index] for index in range(4)}
        )
        _value, reward_parts = reward_function(
            canonical,
            info["delta_M"],
            info["delta_D"],
            reward_access=bool(learned and factors and factors["reward_access"]),
            return_components=True,
        )
        frequency = np.asarray(info["freq_hz_physical"], dtype=float)
        frequency_deviation = frequency - 60.0
        action_delta = executed - previous
        steps.append({"step_index": step_index, "time": float(info["time"]), "raw_observation": {str(index): raw_observation[index].astype(float).tolist() for index in range(4)}, "canonical_observation": canonical.tolist(), "raw_action_norm": raw.tolist(), "projected_action_norm": executed.tolist(), "action_norm": executed.tolist(), "action_delta_norm": action_delta.tolist(), "action_squared": np.square(executed).tolist(), "action_abs_delta": np.abs(action_delta).tolist(), "raw_action_saturated": (np.abs(raw) >= 1.0 - 1.0e-6).tolist(), "M_commanded": np.asarray(info["M_target_es"], dtype=float).tolist(), "D_commanded": np.asarray(info["D_target_es"], dtype=float).tolist(), "M_es": np.asarray(info["M_es"], dtype=float).tolist(), "D_es": np.asarray(info["D_es"], dtype=float).tolist(), "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(), "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(), "freq_hz_physical": frequency.tolist(), "frequency_deviation_hz": frequency_deviation.tolist(), "differential_frequency_deviation_hz": (transform @ frequency_deviation).tolist(), "rocof_hz_s_physical": (np.asarray(info["omega_dot"], dtype=float) * 60.0).tolist(), "common_frequency_deviation_hz": float(np.mean(frequency_deviation)), "reward_components": reward_parts, "tds_failed": bool(info["tds_failed"]), "done": bool(done)})
        previous = executed
        if info["tds_failed"]:
            tds_failed = True
            break
        if done and step_index != 149:
            raise RuntimeError(
                f"premature evaluation terminal at step {step_index} of 150"
            )
    return {
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency,
        "steps": steps,
        "tds_failed": tds_failed,
    }


def _path(repo_root: Path, config: Mapping[str, Any], name: str) -> Path:
    path = Path(str(config["paths"][name]))
    return path if path.is_absolute() else repo_root / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_finite_tree(item) for item in value)
    return False


def registered_shards(
    config: Mapping[str, Any], *, scope: str
) -> dict[str, tuple[str, ...]]:
    """Return the only shard identities R485 may execute."""

    if scope == "formal":
        seeds = tuple(int(seed) for seed in config["formal_seeds"])
    elif scope == "canary":
        seeds = (int(config["canary_seed"]),)
    else:
        raise ValueError("scope must be canary or formal")
    arms = tuple(str(arm) for arm in config["arms"])
    donor = tuple(f"donor|{scope}|{seed}" for seed in seeds)
    train = tuple(f"train|{scope}|{arm}|{seed}" for arm in arms for seed in seeds)
    learned_eval = tuple(
        f"eval|{scope}|same|{arm}|{seed}" for arm in arms for seed in seeds
    )
    references = tuple(
        f"eval|{scope}|{bank}|{arm}|none"
        for bank in ("same", "fresh")
        for arm in REFERENCE_ARMS
    )
    return {"donor": donor, "train": train, "eval": (*learned_eval, *references)}


def expected_artifacts(
    config: Mapping[str, Any], *, root: Path, scope: str
) -> dict[str, dict[str, Path]]:
    """Map the sealed shard roster to every create-only terminal artifact."""

    shards = registered_shards(config, scope=scope)
    donor: dict[str, Path] = {}
    train: dict[str, Path] = {}
    evaluation: dict[str, Path] = {}
    for shard in shards["donor"]:
        seed = int(shard.split("|")[2])
        donor[shard] = root / "donors" / f"seed{seed}" / "manifest.json"
    for shard in shards["train"]:
        _kind, _scope, arm, seed = shard.split("|")
        train[shard] = root / "train" / arm / f"seed{seed}" / "manifest.json"
    contracts = evaluation_contracts()
    for shard in shards["eval"]:
        _kind, _scope, bank, arm, seed = shard.split("|")
        suffix = "deterministic" if seed == "none" else f"seed{seed}"
        profiles = [
            str(profile["profile_id"])
            for profile in contracts[bank]["profiles"]
            if profile["split"] == "evaluation"
        ]
        for profile in profiles:
            evaluation[f"{shard}|{profile}"] = (
                root / "eval" / bank / arm / suffix / f"{profile}.json"
            )
    return {"donor": donor, "train": train, "eval": evaluation}


def donor_marginal_audit(trajectories: np.ndarray) -> dict[str, Any]:
    """Prove each P-source substitution changes identity but preserves marginals."""

    values = np.asarray(trajectories, dtype=np.float32)
    if values.ndim != 5 or values.shape[1] != 2 or values.shape[-2:] != (4, 7):
        raise ValueError(f"unexpected donor tensor shape: {values.shape}")
    hashes: dict[str, str] = {}
    all_equal = True
    all_changed = True
    for scenario in range(values.shape[0]):
        for time_index in range(values.shape[2]):
            for label, true_offset, placebo_offset in (
                ("left", -1, 0),
                ("right", 1, 2),
            ):
                for feature in (1, 2):
                    authentic: list[float] = []
                    placebo: list[float] = []
                    for episode in range(2):
                        for agent in range(4):
                            authentic.append(
                                float(
                                    values[
                                        scenario,
                                        episode,
                                        time_index,
                                        (agent + true_offset) % 4,
                                        feature,
                                    ]
                                )
                            )
                            placebo.append(
                                float(
                                    values[
                                        scenario,
                                        1 - episode,
                                        time_index,
                                        (agent + placebo_offset) % 4,
                                        feature,
                                    ]
                                )
                            )
                            all_changed &= (episode, (agent + true_offset) % 4) != (
                                1 - episode,
                                (agent + placebo_offset) % 4,
                            )
                    left = np.sort(np.asarray(authentic, dtype=np.float32))
                    right = np.sort(np.asarray(placebo, dtype=np.float32))
                    all_equal &= np.array_equal(left, right)
                    key = f"{scenario}|{time_index}|{label}|{feature}"
                    hashes[key] = hashlib.sha256(left.tobytes()).hexdigest()
    digest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "pi_fixed_point_free": True,
        "placebo_nodes_are_non_neighbours": True,
        "every_semantic_donor_changed": bool(all_changed),
        "slot_feature_scenario_time_pools_equal": bool(all_equal),
        "pooled_hash_index_sha256": digest,
        "comparisons": len(hashes),
    }


def _hodges_lehmann(values: Sequence[float]) -> float:
    samples = [float(value) for value in values]
    walsh = [
        (samples[left] + samples[right]) / 2.0
        for left in range(len(samples))
        for right in range(left, len(samples))
    ]
    return float(np.median(np.asarray(walsh, dtype=float)))


def factorial_inference(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_seeds: Sequence[int],
    expected_profiles: Sequence[str],
) -> dict[str, Any]:
    """Run only the frozen HL/exact-rank/Holm path; never choose a fallback."""

    effects = seed_effects(
        rows,
        expected_seeds=expected_seeds,
        expected_profiles=expected_profiles,
    )
    null_log = math.log(1.10)
    tests: dict[str, dict[str, Any]] = {}
    p_values: dict[str, float] = {}
    assumption_limited = False
    for name in REGISTERED_EFFECTS:
        values = [float(effects[name][seed]) for seed in sorted(effects[name])]
        skew = float(symmetry_skew(values, null_log))
        exact_p: float | None = None
        error: str | None = None
        try:
            exact_p = exact_signed_rank_p_one_sided(values, null_log)
        except ValueError as exc:
            error = str(exc)
        if abs(skew) > SYMMETRY_SKEW_THRESHOLD:
            error = "registered symmetry diagnostic exceeded its frozen threshold"
        if error is not None:
            assumption_limited = True
        else:
            assert exact_p is not None
            p_values[name] = exact_p
        tests[name] = {
            "seed_effects": values,
            "hodges_lehmann": _hodges_lehmann(values),
            "geometric_location_ratio": math.exp(_hodges_lehmann(values)),
            "materiality_log": null_log,
            "p_one_sided": exact_p if error is None else None,
            "symmetry_skew": skew,
            "symmetry_threshold": SYMMETRY_SKEW_THRESHOLD,
            "assumption_error": error,
        }
    if assumption_limited:
        for row in tests.values():
            row["p_one_sided"] = None
        status = "ASSUMPTION-LIMITED"
    else:
        decisions = holm_decisions(p_values)
        for name in REGISTERED_EFFECTS:
            tests[name]["holm"] = decisions[name]
        status = "COMPLETE"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "status": status,
        "estimand": "seed_level_hodges_lehmann_location_pseudomedian",
        "test": "exact_one_sided_wilcoxon_signed_rank",
        "multiplicity": "Holm_family_of_four",
        "fallback": None,
        "tests": tests,
    }


def attempt_output_root(
    repo_root: Path, config: Mapping[str, Any], *, scope: str
) -> Path:
    """Resolve immutable attempt-scoped formal output; canary stays separate."""

    key = "canary_out" if scope == "canary" else "formal_out"
    if scope not in {"canary", "formal"}:
        raise ValueError("scope must be canary or formal")
    base = Path(str(config["paths"][key]))
    base = base if base.is_absolute() else repo_root / base
    if scope == "canary":
        return base
    seal = read_hashed_json(_path(repo_root, config, "formal_seal"))
    attempt_id = seal.get("attempt_id")
    if not isinstance(attempt_id, str) or not re.fullmatch(r"r485-formal-[a-z0-9-]+", attempt_id):
        raise RuntimeError("formal seal has no valid immutable attempt_id")
    if seal.get("resume") is not False:
        raise RuntimeError("R485 formal attempt may not resume partial cells")
    return base / attempt_id


def evaluation_contracts() -> dict[str, dict[str, Any]]:
    """Resolve both frozen profile banks onto the R485 150-step horizon."""

    from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract as same
    from andes_rl_kundur.evaluation.r481_fresh_profiles import build_contract as fresh

    result: dict[str, dict[str, Any]] = {}
    for bank, source, seed_key in (
        ("same", same(), "bank_seed"),
        ("fresh", fresh(), "seed"),
    ):
        contract = copy.deepcopy(source)
        seed = int(contract[seed_key])
        contract["source_steps"] = int(contract["steps"])
        contract["steps"] = 150
        contract["bank"] = bank
        contract["environment_seed"] = seed
        for profile in contract["profiles"]:
            profile["bank"] = bank
            profile["environment_seed"] = seed
        contract["sha256"] = hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        result[bank] = contract
    return result


def validate_trace_block(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    expected_profile: str,
    expected_arm: str,
    expected_seed: int | None,
    expected_card_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate one six-scenario profile block without selecting performance."""

    if len(records) != 6:
        raise RuntimeError("R485 profile block requires six registered scenarios")
    profiles = [
        row for row in contract["profiles"] if str(row["profile_id"]) == expected_profile
    ]
    if len(profiles) != 1:
        raise RuntimeError("R485 profile is not registered in its bank contract")
    expected_scenarios = {
        str(row["scenario_id"]) for row in profiles[0]["scenarios"]
    }
    observed_scenarios: set[str] = set()
    tds_statuses: set[str] = set()
    for record in records:
        if record.get("arm_id") != expected_arm or record.get("training_seed") != expected_seed:
            raise RuntimeError("R485 trace identity mismatch")
        if record.get("profile_id") != expected_profile or record.get("bank") != contract["bank"]:
            raise RuntimeError("R485 profile-bank identity mismatch")
        if record.get("bank_contract_sha256") != contract["sha256"]:
            raise RuntimeError("R485 bank-contract lineage mismatch")
        if record.get("environment_seed") != contract["environment_seed"]:
            raise RuntimeError("R485 environment seed mismatch")
        if expected_card_sha256 is not None and record.get("resolved_parameter_card_sha256") != expected_card_sha256:
            raise RuntimeError("R485 trace parameter-card lineage mismatch")
        lineage = (
            record.get("checkpoint_sha256"),
            record.get("training_manifest_sha256"),
            record.get("donor_manifest_sha256"),
            record.get("evaluation_donor_sha256"),
        )
        if expected_seed is None:
            if any(value is not None for value in lineage):
                raise RuntimeError("R485 deterministic reference has learned lineage")
        elif not all(
            isinstance(value, str) and SHA256_RE.fullmatch(value)
            for value in lineage
        ):
            raise RuntimeError("R485 learned trace lineage is incomplete")
        scenario = str(record.get("scenario_id", ""))
        if scenario in observed_scenarios:
            raise RuntimeError("R485 duplicate scenario trace")
        observed_scenarios.add(scenario)
        steps = record.get("steps")
        if not isinstance(steps, list) or not steps:
            raise RuntimeError("R485 trace must contain 150 steps or a retained TDS prefix")
        if not _finite_tree(steps):
            raise RuntimeError("R485 trace contains non-finite or unsupported values")
        indices = [row.get("step_index") for row in steps]
        times = [float(row.get("time", math.nan)) for row in steps]
        if indices != list(range(len(steps))) or not all(math.isfinite(value) for value in times):
            raise RuntimeError("R485 trace step grid is invalid")
        tds = record.get("tds_failed") is True
        if tds:
            classification = str(record.get("tds_classification", ""))
            reproduction = record.get("tds_reproduction")
            if (
                record.get("completed") is not False
                or classification
                not in {"COMPLETE-GUARD-FAIL", "INTEGRITY-INVALID"}
                or not isinstance(reproduction, Mapping)
                or not isinstance(reproduction.get("steps"), list)
                or not reproduction["steps"]
                or not _finite_tree(reproduction["steps"])
            ):
                raise RuntimeError("R485 retained TDS trace lacks resolved reproduction")
            reproduced = reproduction.get("tds_failed") is True
            if (classification == "COMPLETE-GUARD-FAIL") != reproduced:
                raise RuntimeError("R485 TDS reproduction classification mismatch")
            if not reproduced and len(reproduction["steps"]) != 150:
                raise RuntimeError("R485 non-reproduced TDS did not complete its replay")
            tds_statuses.add(classification)
        elif len(steps) != 150 or record.get("completed") is not True:
            raise RuntimeError("R485 trace must contain exactly 150 steps")
    if observed_scenarios != expected_scenarios:
        raise RuntimeError("R485 profile scenario roster mismatch")
    if "INTEGRITY-INVALID" in tds_statuses:
        return {"round": ROUND_ID, "schema_valid": True, "status": "INTEGRITY-INVALID"}
    if tds_statuses:
        return {"round": ROUND_ID, "schema_valid": True, "status": "COMPLETE-GUARD-FAIL"}
    try:
        summary = summarise_30s_profile(
            records, contract=contract, expected_steps=150, round_id=ROUND_ID
        )
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"R485 150-step physical schema invalid: {error}") from error
    return {"round": ROUND_ID, "schema_valid": True, "status": "COMPLETE", "summary": summary}


def build_canary_admissibility(
    *,
    root: Path,
    card_sha256: str,
    arms: Sequence[str],
    seed: int,
    profile_ids: Sequence[str],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Aggregate only path/learner health; never compare endpoint performance."""

    cells: dict[str, Any] = {}
    failures: list[str] = []
    for arm in arms:
        manifest_path = root / "train" / arm / f"seed{seed}" / "manifest.json"
        try:
            manifest = read_hashed_json(manifest_path)
        except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError):
            failures.append(f"{arm}:training_manifest")
            continue
        assessment = manifest.get("learner_admissibility", {}).get("assessment", {})
        if (
            manifest.get("round") != ROUND_ID
            or manifest.get("scope") != "canary"
            or manifest.get("arm_id") != arm
            or manifest.get("seed") != seed
            or manifest.get("resolved_parameter_card_sha256") != card_sha256
            or manifest.get("valid") is not True
            or assessment.get("passed") is not True
        ):
            failures.append(f"{arm}:learner_admissibility")
        profiles: list[str] = []
        statuses: dict[str, str] = {}
        for profile_id in sorted(profile_ids):
            path = root / "eval" / "same" / arm / f"seed{seed}" / f"{profile_id}.json"
            try:
                payload = read_hashed_json(path)
                records = payload.get("records")
                validation = validate_trace_block(
                    records if isinstance(records, list) else (),
                    contract=contract,
                    expected_profile=profile_id,
                    expected_arm=arm,
                    expected_seed=seed,
                    expected_card_sha256=card_sha256,
                )
            except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError):
                failures.append(f"{arm}:{profile_id}:evaluation_schema")
                continue
            if validation["status"] != "COMPLETE":
                failures.append(
                    f"{arm}:{profile_id}:evaluation_{str(validation['status']).lower()}"
                )
                continue
            profiles.append(profile_id)
            statuses[profile_id] = str(validation["status"])
        cells[arm] = {
            "training_manifest_sha256": _sha256(manifest_path),
            "evaluation_profiles": profiles,
            "evaluation_schema_status": statuses,
            "learner_checks": assessment.get("checks", {}),
        }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "seed": seed,
        "arms": cells,
        "passed": not failures and set(cells) == set(arms),
        "failures": failures,
        "performance_or_endpoint_selection_performed": False,
    }


def build_rehearsal_evidence(
    *,
    repo_root: Path,
    config: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the same runner/card/trace path without creating formal output."""

    card_path = _path(repo_root, config, "resolved_parameter_card")
    card = read_hashed_json(card_path)
    source_hash = all(
        (repo_root / str(row["path"])).is_file()
        and _sha256(repo_root / str(row["path"])) == row["sha256"]
        for row in card["sources"].values()
    )
    parent_hash = all(
        (repo_root / str(row["path"])).is_file()
        and _sha256(repo_root / str(row["path"])) == row["sha256"]
        for row in card["parents"].values()
    )
    case = card["installed_case"]
    case_path = Path(str(case["path"]))
    contract = evaluation_contracts()["same"]
    profile = next(
        row for row in contract["profiles"] if row["profile_id"] == "canary_eval_a"
    )
    trace_path = (
        attempt_output_root(repo_root, config, scope="canary")
        / "eval/same/zero/deterministic/canary_eval_a.json"
    )
    trace = read_hashed_json(trace_path)
    validation = validate_trace_block(
        trace.get("records", ()),
        contract=contract,
        expected_profile="canary_eval_a",
        expected_arm="zero",
        expected_seed=None,
        expected_card_sha256=_sha256(card_path),
    )
    shards = registered_shards(config, scope="formal")
    formal_base = Path(str(config["paths"]["formal_out"]))
    if not formal_base.is_absolute():
        formal_base = repo_root / formal_base
    checks = {
        "source_hash": source_hash,
        "parent_hash": parent_hash,
        "installed_package": bool(runtime.get("andes_module")),
        "installed_case": case_path.is_file() and _sha256(case_path) == case["sha256"],
        "output_absence": not formal_base.exists(),
        "shard_roster": {name: len(values) for name, values in shards.items()}
        == {"donor": 26, "train": 208, "eval": 212},
        "trajectory_count": len(shards["eval"]) * 4 * 6 == 5_088,
        "representative_schema": validation["status"] == "COMPLETE",
        "representative_profile_contract": len(profile["scenarios"]) == 6,
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "phase": "same-pre-attempt-path-rehearsal",
        "checks": checks,
        "runtime": dict(runtime),
        "rehearsal_scope": "one zero-action six-scenario profile at 150 steps",
        "representative": {
            "profile_id": "canary_eval_a",
            "trace_sha256": _sha256(trace_path),
            "status": validation["status"],
            "record_count": len(trace["records"]),
        },
        "formal_attempt_created": False,
        "formal_outputs_created": formal_base.exists(),
        "resolved_parameter_card_sha256": _sha256(card_path),
    }


def resolve_tds(*, primary_failed: bool, reproduction_failed: bool | None) -> str:
    """Resolve the single pre-registered deterministic TDS reproduction."""

    if not primary_failed:
        if reproduction_failed is not None:
            raise ValueError("TDS reproduction is forbidden without a primary failure")
        return "COMPLETE"
    if reproduction_failed is None:
        return "REPRODUCTION-REQUIRED"
    return "COMPLETE-GUARD-FAIL" if reproduction_failed else "INTEGRITY-INVALID"


def analyse_result_root(
    *,
    repo_root: Path,
    config: Mapping[str, Any],
    root: Path,
    scope: str,
) -> dict[str, Any]:
    """Verify the exact roster before exposing any R485 scientific result."""

    artifacts = expected_artifacts(config, root=root, scope=scope)
    flat = {identity: path for group in artifacts.values() for identity, path in group.items()}
    missing = sorted(
        identity
        for identity, path in flat.items()
        if not path.is_file() or not path.with_suffix(path.suffix + ".sha256").is_file()
    )
    invalid: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    for identity, path in flat.items():
        if identity in missing:
            continue
        try:
            payloads[identity] = read_hashed_json(path)
        except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError):
            invalid.append(identity)
    inventory = {
        "expected_terminal_artifacts": len(flat),
        "verified_terminal_artifacts": len(payloads),
        "expected_donor_manifests": len(artifacts["donor"]),
        "expected_training_manifests": len(artifacts["train"]),
        "expected_evaluation_profiles": len(artifacts["eval"]),
        "expected_trajectories": len(artifacts["eval"]) * 6,
        "missing": missing,
        "hash_or_parse_invalid": sorted(invalid),
    }
    if missing or invalid:
        return {
            "schema_version": 1,
            "round": ROUND_ID,
            "scope": scope,
            "status": "EXECUTION-INCOMPLETE" if missing else "INTEGRITY-INVALID",
            "inventory": inventory,
            "primary_inference": {"status": "NOT-TESTED"},
            "tail_inference": {"status": "NOT-TESTED"},
            "available_case_analysis_performed": False,
        }
    return _analyse_complete_artifacts(
        repo_root=repo_root,
        config=config,
        scope=scope,
        artifacts=artifacts,
        payloads=payloads,
        inventory=inventory,
    )


def _prefix_summary(
    records: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    prefix_contract = copy.deepcopy(dict(contract))
    prefix_contract["steps"] = 30
    prefix_records: list[dict[str, Any]] = []
    for record in records:
        prefix = copy.deepcopy(dict(record))
        prefix["steps"] = copy.deepcopy(record["steps"][:30])
        prefix["completed_steps"] = 30
        prefix["completed"] = True
        prefix["derived_from_30s_trace"] = True
        prefix["source_trace_steps"] = 150
        prefix_records.append(prefix)
    result = dict(summarise_profile(prefix_records, contract=prefix_contract))
    result.update(
        {
            "round": ROUND_ID,
            "expected_steps": 30,
            "horizon_seconds": 6.0,
            "derived_from_30s_trace": True,
            "training_seed": records[0].get("training_seed"),
            "checkpoint_sha256": records[0].get("checkpoint_sha256"),
            "training_manifest_sha256": records[0].get(
                "training_manifest_sha256"
            ),
            "stage": records[0].get("stage"),
        }
    )
    return result


def _factorial_rows(summaries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        seed = summary.get("training_seed")
        if seed is None:
            continue
        arm = str(summary["arm_id"])
        actor, critic, reward = arm.split("_")
        rows.append(
            {
                "stage": "final",
                "seed": int(seed),
                "actor_source": actor[1:].upper(),
                "critic_source": critic[1:].upper(),
                "reward_access": int(reward[1:]),
                "profile": str(summary["profile_id"]),
                "disturbance_differential_energy": float(
                    summary["disturbance_differential_energy"]
                ),
            }
        )
    return rows


def _threshold_sensitivity(
    *,
    summaries: Sequence[Mapping[str, Any]],
    policies: Sequence[tuple[str, int]],
    profiles: Sequence[str],
    reference_gate: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = contract["parameter_card"]["threshold_sensitivity"]
    grid: list[dict[str, Any]] = []
    primary_result: dict[str, Any] | None = None
    for frequency in frozen["frequency_multipliers"]:
        for action in frozen["action_multipliers"]:
            result = classify_learned_guard(
                summaries,
                policies=policies,
                profiles=profiles,
                deterministic_reference_gate=reference_gate,
                thresholds={
                    "maximum_common_harm": float(frequency) - 1.0,
                    "maximum_action_stress_harm": float(action) - 1.0,
                },
                round_id=ROUND_ID,
                policy_label=ROUND_ID,
            )
            grid.append(
                {
                    "frequency_multiplier": float(frequency),
                    "action_multiplier": float(action),
                    "classification": result["classification"],
                    "passing_count": result.get("passing_count", 0),
                }
            )
            if {
                "frequency": float(frequency),
                "action": float(action),
            } == frozen["primary"]:
                primary_result = result
    if primary_result is None:
        raise RuntimeError("R485 primary threshold is absent from the frozen grid")
    by_key = {
        (
            str(row["profile_id"]),
            str(row["arm_id"]),
            row.get("training_seed"),
        ): row
        for row in summaries
    }
    decisions = {
        (str(row["arm_id"]), int(row["training_seed"])): row
        for row in primary_result["policy_decisions"]
    }
    guards = {
        (
            str(row["profile_id"]),
            str(row["arm_id"]),
            int(row["training_seed"]),
        ): row
        for row in primary_result["per_profile_blocks"]
    }
    break_even: list[dict[str, Any]] = []
    for arm, seed in policies:
        ratios: list[float] = []
        non_action_pass = True
        for profile in profiles:
            candidate = by_key[(profile, arm, seed)]
            reference = by_key[(profile, "local_neighbour_md_km2_kd2", None)]
            for metric in ("action_rms", "action_total_variation"):
                denominator = float(reference[metric])
                if denominator <= 0.0:
                    ratios = []
                    break
                ratios.append(float(candidate[metric]) / denominator)
            block = guards[(profile, arm, seed)]
            non_action_pass &= all(
                bool(value)
                for name, value in block["guard"].items()
                if name not in {"action_rms_no_harm", "action_variation_no_harm"}
            )
        decision = decisions[(arm, seed)]
        non_action_pass &= all(decision["aggregate_joint_endpoint_target"].values())
        action_only = max(ratios) if ratios else None
        break_even.append(
            {
                "arm_id": arm,
                "training_seed": seed,
                "action_only_break_even": action_only,
                "complete_contract_break_even": (
                    action_only if non_action_pass else None
                ),
                "all_non_action_guards_pass": bool(non_action_pass),
            }
        )
    return {
        "grid": grid,
        "primary": primary_result,
        "break_even_definition": frozen["break_even"],
        "break_even": break_even,
        "post_result_threshold_additions": False,
    }


def _analyse_complete_artifacts(
    *,
    repo_root: Path,
    config: Mapping[str, Any],
    scope: str,
    artifacts: Mapping[str, Mapping[str, Path]],
    payloads: Mapping[str, Mapping[str, Any]],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    card_path = _path(repo_root, config, "resolved_parameter_card")
    card_sha = _sha256(card_path)
    contracts = evaluation_contracts()
    errors: list[str] = []
    donor_lineage: dict[int, dict[str, Any]] = {}
    for identity, path in artifacts["donor"].items():
        seed = int(identity.split("|")[2])
        row = payloads[identity]
        if (
            row.get("round") != ROUND_ID
            or row.get("scope") != scope
            or row.get("seed") != seed
            or row.get("resolved_parameter_card_sha256") != card_sha
        ):
            errors.append(f"{identity}:identity_or_card")
            continue
        for split in ("development", "evaluation"):
            entry = row.get("splits", {}).get(split, {})
            source = repo_root / str(entry.get("path", ""))
            audit = entry.get("marginal_audit", {})
            if (
                not source.is_file()
                or _sha256(source) != entry.get("sha256")
                or not all(
                    audit.get(key) is True
                    for key in (
                        "pi_fixed_point_free",
                        "placebo_nodes_are_non_neighbours",
                        "every_semantic_donor_changed",
                        "slot_feature_scenario_time_pools_equal",
                    )
                )
            ):
                errors.append(f"{identity}:{split}_donor")
        base = row.get("base_state", {})
        base_path = repo_root / str(base.get("path", ""))
        if not base_path.is_file() or _sha256(base_path) != base.get("sha256"):
            errors.append(f"{identity}:base_state")
        donor_lineage[seed] = {
            "manifest": _sha256(path),
            "base": base.get("sha256"),
            "development": row.get("splits", {}).get("development", {}).get("sha256"),
            "evaluation": row.get("splits", {}).get("evaluation", {}).get("sha256"),
        }
    training_lineage: dict[tuple[str, int], dict[str, Any]] = {}
    for identity, path in artifacts["train"].items():
        _kind, _scope, arm, seed_text = identity.split("|")
        seed = int(seed_text)
        row = payloads[identity]
        lineage = donor_lineage.get(seed, {})
        if (
            row.get("round") != ROUND_ID
            or row.get("scope") != scope
            or row.get("arm_id") != arm
            or row.get("seed") != seed
            or row.get("valid") is not True
            or row.get("interaction_steps") != 43_200
            or row.get("resolved_parameter_card_sha256") != card_sha
            or row.get("donor_manifest_sha256") != lineage.get("manifest")
            or row.get("base_state_sha256") != lineage.get("base")
            or row.get("development_donor_sha256") != lineage.get("development")
        ):
            errors.append(f"{identity}:identity_or_lineage")
            continue
        checkpoint = path.with_name("final.pt")
        curves = path.with_name("curves.npz")
        if not checkpoint.is_file() or _sha256(checkpoint) != row.get("final_checkpoint_sha256"):
            errors.append(f"{identity}:checkpoint")
        if not curves.is_file() or _sha256(curves) != row.get("curves_sha256"):
            errors.append(f"{identity}:curves")
        training_lineage[(arm, seed)] = {
            "manifest": _sha256(path),
            "checkpoint": row.get("final_checkpoint_sha256"),
            "donor_manifest": lineage.get("manifest"),
            "evaluation_donor": lineage.get("evaluation"),
        }
    summaries_30: list[dict[str, Any]] = []
    summaries_6: list[dict[str, Any]] = []
    trace_ids: set[tuple[str, str, int | None, str, str]] = set()
    tds_blocks: list[dict[str, str]] = []
    for identity in artifacts["eval"]:
        _kind, _scope, bank, arm, seed_text, profile = identity.split("|")
        seed = None if seed_text == "none" else int(seed_text)
        records = payloads[identity].get("records")
        if not isinstance(records, list):
            errors.append(f"{identity}:records")
            continue
        try:
            validation = validate_trace_block(
                records,
                contract=contracts[bank],
                expected_profile=profile,
                expected_arm=arm,
                expected_seed=seed,
                expected_card_sha256=card_sha,
            )
        except RuntimeError as exc:
            errors.append(f"{identity}:{exc}")
            continue
        if seed is not None:
            lineage = training_lineage.get((arm, seed), {})
            for record in records:
                if (
                    record.get("training_manifest_sha256") != lineage.get("manifest")
                    or record.get("checkpoint_sha256") != lineage.get("checkpoint")
                    or record.get("donor_manifest_sha256") != lineage.get("donor_manifest")
                    or record.get("evaluation_donor_sha256") != lineage.get("evaluation_donor")
                ):
                    errors.append(f"{identity}:live_lineage")
                    break
        for record in records:
            trace_id = (bank, arm, seed, profile, str(record.get("scenario_id", "")))
            if trace_id in trace_ids:
                errors.append(f"{identity}:duplicate_trace")
            trace_ids.add(trace_id)
        if validation["status"] != "COMPLETE":
            tds_blocks.append({"identity": identity, "status": validation["status"]})
            continue
        summary_30 = dict(validation["summary"])
        summary_6 = _prefix_summary(records, contracts[bank])
        summaries_30.append(summary_30)
        summaries_6.append(summary_6)
    inventory["verified_trajectories"] = len(trace_ids)
    if len(trace_ids) != inventory["expected_trajectories"]:
        errors.append("trace_roster_count_mismatch")
    if errors:
        inventory["semantic_errors"] = sorted(errors)
        return {
            "schema_version": 1,
            "round": ROUND_ID,
            "scope": scope,
            "status": "INTEGRITY-INVALID",
            "inventory": inventory,
            "primary_inference": {"status": "NOT-TESTED"},
            "tail_inference": {"status": "NOT-TESTED"},
            "available_case_analysis_performed": False,
        }
    if tds_blocks:
        status = (
            "INTEGRITY-INVALID"
            if any(row["status"] == "INTEGRITY-INVALID" for row in tds_blocks)
            else "VALID-BOUNDED-GUARD-FAIL"
        )
        return {
            "schema_version": 1,
            "round": ROUND_ID,
            "scope": scope,
            "status": status,
            "inventory": inventory,
            "tds_blocks": tds_blocks,
            "primary_inference": {"status": "ASSUMPTION-LIMITED"},
            "tail_inference": {"status": "ASSUMPTION-LIMITED"},
            "available_case_analysis_performed": False,
        }
    profiles = tuple(
        str(row["profile_id"])
        for row in contracts["same"]["profiles"]
        if row["split"] == "evaluation"
    )
    seeds = tuple(int(seed) for seed in config["formal_seeds"])
    policies = tuple((str(arm), seed) for arm in config["arms"] for seed in seeds)
    primary = factorial_inference(
        _factorial_rows(summaries_6),
        expected_seeds=seeds,
        expected_profiles=profiles,
    )
    tail = factorial_inference(
        _factorial_rows(summaries_30),
        expected_seeds=seeds,
        expected_profiles=profiles,
    )
    same_references = [
        row
        for row in summaries_30
        if row["arm_id"] in REFERENCE_ARMS and row["profile_id"] in profiles
    ]
    fresh_profiles = tuple(
        str(row["profile_id"])
        for row in contracts["fresh"]["profiles"]
        if row["split"] == "evaluation"
    )
    fresh_references = [
        row
        for row in summaries_30
        if row["arm_id"] in REFERENCE_ARMS and row["profile_id"] in fresh_profiles
    ]
    same_gate = classify_deterministic_tail(
        same_references,
        contract=contracts["same"],
        expected_profiles=profiles,
        bank_name="canary",
        round_id=ROUND_ID,
    )
    fresh_gate = classify_deterministic_tail(
        fresh_references,
        contract=contracts["fresh"],
        expected_profiles=fresh_profiles,
        bank_name="fresh",
        round_id=ROUND_ID,
    )
    learned_and_reference = [
        row
        for row in summaries_30
        if row["profile_id"] in profiles
        and (row["training_seed"] is not None or row["arm_id"] == "local_neighbour_md_km2_kd2")
    ]
    sensitivity = _threshold_sensitivity(
        summaries=learned_and_reference,
        policies=policies,
        profiles=profiles,
        reference_gate=same_gate,
        contract=config,
    )
    factor_established = bool(
        primary["status"] == "COMPLETE"
        and any(row["holm"]["reject"] for row in primary["tests"].values())
    )
    guard_passed = sensitivity["primary"].get("passing_count", 0) > 0
    if primary["status"] != "COMPLETE":
        outcome = "ASSUMPTION-LIMITED"
    elif factor_established and guard_passed:
        outcome = "VALID-POSITIVE"
    elif factor_established or guard_passed:
        outcome = "VALID-MIXED"
    else:
        outcome = "VALID-NEGATIVE"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "scope": scope,
        "status": outcome,
        "claim_boundary": config["parameter_card"]["outcome_to_claim"][outcome],
        "inventory": inventory,
        "primary_inference": primary,
        "tail_inference": tail,
        "same_bank_deterministic_gate": same_gate,
        "fresh_bank_deterministic_gate": fresh_gate,
        "threshold_sensitivity": sensitivity,
        "six_second_prefixes_derived_from_30s_traces": len(summaries_6),
        "horizons_pooled": False,
        "available_case_analysis_performed": False,
    }


def verify_formal_authority(
    *,
    repo_root: Path,
    config: Mapping[str, Any],
    expected_shards: Mapping[str, Sequence[str]],
    reviewed_files: Sequence[Path],
) -> dict[str, Any]:
    """Verify semantic gates and their complete formal-seal hash graph."""

    if config.get("round") != ROUND_ID:
        raise RuntimeError("R485 authority config round mismatch")
    card_path = _path(repo_root, config, "resolved_parameter_card")
    canary_path = _path(repo_root, config, "canary_admissibility")
    rehearsal_path = _path(repo_root, config, "rehearsal")
    capacity_path = _path(repo_root, config, "capacity")
    owner_path = _path(repo_root, config, "owner_approval")
    card = read_hashed_json(card_path)
    canary = read_hashed_json(canary_path)
    rehearsal = read_hashed_json(rehearsal_path)
    capacity = read_hashed_json(capacity_path)
    owner = read_hashed_json(owner_path)
    if card.get("round") != ROUND_ID or card.get("objective_semantics_probe", {}).get("passed") is not True:
        raise RuntimeError("resolved parameter card is not R485-admissible")
    if canary.get("round") != ROUND_ID or canary.get("passed") is not True:
        raise RuntimeError("canary admissibility did not pass")
    if canary.get("performance_or_endpoint_selection_performed") is not False:
        raise RuntimeError("canary inspected scientific performance")
    checks = rehearsal.get("checks")
    if rehearsal.get("round") != ROUND_ID or not isinstance(checks, dict) or not checks or not all(checks.values()):
        raise RuntimeError("rehearsal did not pass every registered check")
    if rehearsal.get("formal_outputs_created") is not False:
        raise RuntimeError("rehearsal created formal output")
    workers = int(config["execution"]["workers"])
    measured_workers = int(capacity.get("selected_workers", capacity.get("capacity_canary", {}).get("formal_workers", -1)))
    if capacity.get("round") != ROUND_ID or capacity.get("safe_for_formal_launch") is not True or measured_workers < workers:
        raise RuntimeError("capacity evidence is not safe for R485 formal launch")
    if capacity.get("native_threads_per_process") != 1:
        raise RuntimeError("capacity native-thread contract drift")
    if owner.get("round") != ROUND_ID or owner.get("approved") is not True or owner.get("long_execution_authorized") is not True:
        raise RuntimeError("owner approval does not authorize R485 formal launch")
    if (
        owner.get("approved_scope") != "formal-208-cell-source-factorial"
        or owner.get("approved_action") != "launch-r485-formal"
    ):
        raise RuntimeError("owner approval scope does not name the exact R485 formal attempt")
    attempt_output_root(repo_root, config, scope="formal")
    seal = read_hashed_json(_path(repo_root, config, "formal_seal"))
    if owner.get("attempt_id") != seal.get("attempt_id"):
        raise RuntimeError("owner approval attempt identity drift")
    bound_files = {
        "resolved_parameter_card_sha256": card_path,
        "canary_admissibility_sha256": canary_path,
        "rehearsal_sha256": rehearsal_path,
        "capacity_sha256": capacity_path,
        "owner_approval_sha256": owner_path,
        "plan_sha256": _path(repo_root, config, "plan"),
        "config_sha256": Path(str(config["_path"])),
    }
    return verify_formal_seal(
        repo_root=repo_root,
        seal_path=_path(repo_root, config, "formal_seal"),
        round_id=ROUND_ID,
        contract_sha256=_sha256(card_path),
        bound_files=bound_files,
        review_paths=(
            _path(repo_root, config, "code_review_a"),
            _path(repo_root, config, "code_review_b"),
        ),
        reviewed_files=reviewed_files,
        expected_shards=expected_shards,
    )
