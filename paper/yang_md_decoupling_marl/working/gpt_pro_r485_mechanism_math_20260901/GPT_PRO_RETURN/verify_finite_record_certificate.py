#!/usr/bin/env python3
"""Deterministic CPU-only verifier for the R485 finite-record math audit.

Usage
-----
python verify_finite_record_certificate.py \
    --package-root /path/to/gpt_pro_r485_mechanism_math_20260901

To reconstruct the machine-readable result:
python verify_finite_record_certificate.py --package-root ... \
    --write-result math_result.json

The script performs no training, simulation, network access, or stochastic
sampling.  It interprets the exported float32 actor parameters as the supplied
ReLU--tanh policy and uses the exact production-style float32 projector replay.
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
import torch
import torch.nn as nn

PROFILE_FILES = {
    "a": "canary_eval_a.json",
    "b": "canary_eval_b.json",
    "c": "canary_eval_c.json",
    "d": "canary_eval_d.json",
}
PROFILE_IDS = {k: f"canary_eval_{k}" for k in PROFILE_FILES}
SLEW_LIMIT = 0.25
ACTOR_REPLAY_ATOL = 1.0e-6
METRIC_ATOL = 2.0e-5
PROJECTOR_ATOL = 1.0e-7
RESULT_ATOL = 2.0e-6


class GaussianActor(nn.Module):
    """Minimal exact reconstruction of the supplied deterministic actor."""

    def __init__(self) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        width = 128
        previous = 9
        for _ in range(4):
            layers.append(nn.Linear(previous, width))
            layers.append(nn.ReLU())
            previous = width
        self.net = nn.Sequential(*layers)
        self.mean_head = nn.Linear(width, 2)
        self.log_std_head = nn.Linear(width, 2)

    def deterministic(self, state: torch.Tensor) -> torch.Tensor:
        hidden = self.net(state)
        return torch.tanh(self.mean_head(hidden))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"


def locate_package_root(explicit: str | None, script_dir: Path) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend(
        [
            script_dir.parent / "gpt_pro_r485_mechanism_math_20260901",
            script_dir / "gpt_pro_r485_mechanism_math_20260901",
            Path.cwd() / "gpt_pro_r485_mechanism_math_20260901",
            Path.cwd(),
        ]
    )
    for candidate in candidates:
        if (candidate / "PACKAGE_MANIFEST.json").is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "package root not found; pass --package-root pointing to the extracted input archive"
    )


def verify_manifest(root: Path) -> dict[str, str]:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes: dict[str, str] = {"PACKAGE_MANIFEST.json": sha256_file(manifest_path)}
    for row in manifest["entries"]:
        relative = row["entry"]
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"manifest entry missing: {relative}")
        actual = sha256_file(path)
        if actual != row["sha256"]:
            raise AssertionError(
                f"manifest SHA-256 mismatch for {relative}: {actual} != {row['sha256']}"
            )
        if path.stat().st_size != int(row["bytes"]):
            raise AssertionError(f"manifest byte-size mismatch for {relative}")
        hashes[relative] = actual
    return hashes


def load_checkpoint(root: Path) -> tuple[list[GaussianActor], dict[str, Any]]:
    checkpoint_path = root / "checkpoint/an_cn_r0_seed501_final.pt"
    try:
        checkpoint = torch.load(
            checkpoint_path, map_location="cpu", weights_only=True
        )
    except TypeError:  # pragma: no cover - compatibility for older PyTorch
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
    identity = {
        "kind": checkpoint.get("kind"),
        "round": checkpoint.get("round"),
        "scope": checkpoint.get("scope"),
        "arm_id": checkpoint.get("arm_id"),
        "seed": checkpoint.get("seed"),
        "stage": checkpoint.get("stage"),
    }
    expected = {
        "kind": "r485-source-factorial",
        "round": "R485",
        "scope": "formal",
        "arm_id": "an_cn_r0",
        "seed": 501,
        "stage": "final",
    }
    if identity != expected:
        raise AssertionError(f"checkpoint identity mismatch: {identity}")
    members = checkpoint.get("members")
    if not isinstance(members, list) or len(members) != 4:
        raise AssertionError("checkpoint must contain four actor members")
    actors: list[GaussianActor] = []
    for member in members:
        actor = GaussianActor().cpu().eval()
        actor.load_state_dict(member["actor"])
        actors.append(actor)
    return actors, checkpoint


def load_trace(root: Path, profile: str) -> dict[str, Any]:
    payload = json.loads(
        (root / "traces" / PROFILE_FILES[profile]).read_text(encoding="utf-8")
    )
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise AssertionError(f"profile {profile}: expected six records")
    observations = np.zeros((6, 150, 4, 7), dtype=np.float32)
    previous = np.zeros((6, 150, 4, 2), dtype=np.float32)
    raw = np.zeros((6, 150, 4, 2), dtype=np.float32)
    projected = np.zeros((6, 150, 4, 2), dtype=np.float32)
    saved_delta = np.zeros((6, 150, 4, 2), dtype=np.float32)
    for record_index, record in enumerate(records):
        if record.get("checkpoint_sha256") != (
            "c5fec5e301cae22fbc71818523aca119d85bcb304b42f4dc87043618b072aaaa"
        ):
            raise AssertionError("trace/checkpoint lineage mismatch")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != 150:
            raise AssertionError(f"profile {profile}: expected 150 steps per record")
        prior = np.zeros((4, 2), dtype=np.float32)
        for step_index, step in enumerate(steps):
            observations[record_index, step_index] = np.asarray(
                step["canonical_observation"], dtype=np.float32
            )
            previous[record_index, step_index] = prior
            raw[record_index, step_index] = np.asarray(
                step["raw_action_norm"], dtype=np.float32
            )
            projected[record_index, step_index] = np.asarray(
                step["projected_action_norm"], dtype=np.float32
            )
            saved_delta[record_index, step_index] = np.asarray(
                step["action_delta_norm"], dtype=np.float32
            )
            prior = projected[record_index, step_index]
    return {
        "observations": observations,
        "previous": previous,
        "raw": raw,
        "projected": projected,
        "saved_delta": saved_delta,
    }


def actor_outputs(
    actors: list[GaussianActor], observations: np.ndarray, previous: np.ndarray
) -> np.ndarray:
    output = np.zeros((*observations.shape[:3], 2), dtype=np.float32)
    flat_observations = observations.reshape(-1, 4, 7)
    flat_previous = previous.reshape(-1, 4, 2)
    flat_output = output.reshape(-1, 4, 2)
    with torch.no_grad():
        for agent, actor in enumerate(actors):
            state = np.concatenate(
                [flat_observations[:, agent], flat_previous[:, agent]], axis=1
            ).astype(np.float32)
            flat_output[:, agent] = (
                actor.deterministic(torch.from_numpy(state))
                .cpu()
                .numpy()
                .astype(np.float32)
            )
    return output


def project_action_numpy(previous: np.ndarray, raw: np.ndarray) -> np.ndarray:
    previous32 = np.asarray(previous, dtype=np.float32)
    raw32 = np.asarray(raw, dtype=np.float32)
    amplitude = np.clip(raw32, -1.0, 1.0).astype(np.float32)
    previous64 = previous32.astype(np.float64)
    delta64 = np.clip(
        amplitude.astype(np.float64) - previous64, -SLEW_LIMIT, SLEW_LIMIT
    )
    executed = np.clip(previous64 + delta64, -1.0, 1.0).astype(np.float32)
    overshoot = executed.astype(np.float64) - previous64 > SLEW_LIMIT
    undershoot = executed.astype(np.float64) - previous64 < -SLEW_LIMIT
    if np.any(overshoot):
        executed[overshoot] = np.nextafter(
            executed[overshoot], np.float32(-np.inf)
        )
    if np.any(undershoot):
        executed[undershoot] = np.nextafter(
            executed[undershoot], np.float32(np.inf)
        )
    return np.clip(executed, -1.0, 1.0).astype(np.float32)


def recursive_project(raw: np.ndarray) -> np.ndarray:
    output = np.zeros_like(raw, dtype=np.float32)
    for record in range(raw.shape[0]):
        previous = np.zeros((4, 2), dtype=np.float32)
        for step in range(raw.shape[1]):
            previous = project_action_numpy(previous, raw[record, step])
            output[record, step] = previous
    return output


def previous_array(values: np.ndarray) -> np.ndarray:
    return np.concatenate([np.zeros_like(values[:, :1]), values[:, :-1]], axis=1)


def channel_tv(values: np.ndarray) -> np.ndarray:
    rows = values.astype(np.float64)
    return np.abs(rows - previous_array(rows)).sum(axis=(0, 1, 2))


def channel_rms(values: np.ndarray) -> np.ndarray:
    rows = values.astype(np.float64)
    return np.sqrt(np.mean(np.square(rows), axis=(0, 1, 2)))


def joint_metrics(values: np.ndarray) -> dict[str, Any]:
    rows = values.astype(np.float64)
    delta = np.abs(rows - previous_array(rows))
    return {
        "rms": float(np.sqrt(np.mean(np.square(rows)))),
        "total_variation": float(delta.sum()),
        "per_channel": {
            "M": {
                "rms": float(np.sqrt(np.mean(np.square(rows[..., 0])))),
                "total_variation": float(delta[..., 0].sum()),
            },
            "D": {
                "rms": float(np.sqrt(np.mean(np.square(rows[..., 1])))),
                "total_variation": float(delta[..., 1].sum()),
            },
        },
    }


def qsummary(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.quantile(values, 0.0, method="linear")),
        "q01": float(np.quantile(values, 0.01, method="linear")),
        "q05": float(np.quantile(values, 0.05, method="linear")),
        "median": float(np.quantile(values, 0.5, method="linear")),
        "q95": float(np.quantile(values, 0.95, method="linear")),
        "q99": float(np.quantile(values, 0.99, method="linear")),
        "max": float(np.quantile(values, 1.0, method="linear")),
    }


def local_jacobian_certificate(
    actor: GaussianActor, states: np.ndarray
) -> dict[str, np.ndarray | int | float]:
    """Exact active-set Jacobians and largest same-region L-infinity radii.

    For a differentiable saved input, every hidden preactivation is affine in
    the two previous-action coordinates while the active set is fixed.  The
    minimum |z|/||grad_p z||_1 is the radius of the largest L-infinity ball in
    those two coordinates that remains inside that activation region.
    """

    x = torch.from_numpy(states.astype(np.float32))
    linear_layers = [actor.net[0], actor.net[2], actor.net[4], actor.net[6]]
    hidden = x
    first_weight = linear_layers[0].weight[:, 7:9]
    gradient = first_weight.unsqueeze(0).expand(x.shape[0], -1, -1).clone()
    radii: list[torch.Tensor] = []
    preactivations: list[torch.Tensor] = []

    for layer_index, layer in enumerate(linear_layers):
        if layer_index > 0:
            gradient = torch.einsum("ij,bjk->bik", layer.weight, gradient)
        z = layer(hidden)
        preactivations.append(z)
        denominator = gradient.abs().sum(dim=-1)
        radius = torch.where(
            denominator > 0,
            z.abs() / denominator,
            torch.full_like(denominator, float("inf")),
        )
        radii.append(radius)
        mask = (z > 0).to(z.dtype)
        hidden = torch.relu(z)
        gradient = mask.unsqueeze(-1) * gradient

    mu = actor.mean_head(hidden)
    pre_tanh_jacobian = torch.einsum(
        "ij,bjk->bik", actor.mean_head.weight, gradient
    )
    action = torch.tanh(mu)
    jacobian = (1.0 - action.square()).unsqueeze(-1) * pre_tanh_jacobian
    local_linf = jacobian.abs().sum(dim=-1).max(dim=-1).values
    stacked_z = torch.cat(preactivations, dim=1)
    active_radius = torch.cat(radii, dim=1).min(dim=1).values
    return {
        "action": action.detach().cpu().numpy().astype(np.float32),
        "local_linf": local_linf.detach().cpu().numpy().astype(np.float64),
        "active_radius": active_radius.detach().cpu().numpy().astype(np.float64),
        "minimum_abs_preactivation": float(stacked_z.abs().min().item()),
        "exact_zero_preactivations": int((stacked_z == 0).sum().item()),
        "preactivation_count": int(stacked_z.numel()),
    }


def compare_numeric(actual: Any, expected: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise AssertionError(f"result structure mismatch at {path}")
        for key in expected:
            compare_numeric(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError(f"result list mismatch at {path}")
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            compare_numeric(left, right, f"{path}[{index}]")
        return
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not math.isclose(
            float(actual), expected, rel_tol=RESULT_ATOL, abs_tol=RESULT_ATOL
        ):
            raise AssertionError(
                f"numeric mismatch at {path}: recomputed={actual}, expected={expected}"
            )
        return
    if actual != expected:
        raise AssertionError(f"value mismatch at {path}: {actual!r} != {expected!r}")


def compute_result(root: Path) -> dict[str, Any]:
    torch.set_num_threads(1)
    np.seterr(all="raise")
    hashes = verify_manifest(root)
    actors, _checkpoint = load_checkpoint(root)

    projection_json = json.loads(
        (root / "posthoc/projection_tv_result.json").read_text(encoding="utf-8")
    )
    feedback_json = json.loads(
        (root / "posthoc/feedback_grid_result.json").read_text(encoding="utf-8")
    )
    quasi_grid_json = json.loads(
        (root / "posthoc/quasistatic_rms_grid_result.json").read_text(
            encoding="utf-8"
        )
    )
    recursive_json = json.loads(
        (root / "posthoc/recursive_intervention_result.json").read_text(
            encoding="utf-8"
        )
    )

    actor_replay_error = 0.0
    projector_replay_error = 0.0
    saved_delta_error = 0.0
    between_violations = 0
    slew_violations = 0
    projection_rows: list[dict[str, Any]] = []
    decomposition_rows: list[dict[str, Any]] = []
    quasi_rows: list[dict[str, Any]] = []
    local_linf_values: list[np.ndarray] = []
    active_radius_values: list[np.ndarray] = []
    secant_gain_values: list[np.ndarray] = []
    all_anchor_delta_values: list[np.ndarray] = []
    all_temporal_delta_values: list[np.ndarray] = []
    total_preactivations = 0
    exact_zero_preactivations = 0
    minimum_abs_preactivation = float("inf")
    anchor_inside_active_region = 0
    temporal_inside_active_region = 0
    temporal_nonzero_inside_active_region = 0
    temporal_nonzero_count = 0
    total_actor_evaluations = 0
    ordered_rms_negative_contrasts = 0
    representative_intervention_rows: list[dict[str, Any]] = []

    projection_reference = {
        row["profile_id"]: row for row in projection_json["candidate"]["profiles"]
    }
    recursive_reference = {
        row["profile_id"]: row for row in recursive_json["profiles"]
    }
    if len(feedback_json.get("policies", [])) != 24:
        raise AssertionError("feedback grid must contain exactly 24 policies")
    if len(quasi_grid_json.get("rows", [])) != 96:
        raise AssertionError("quasi-static grid must contain exactly 96 policy-profile rows")
    if set(recursive_reference) != set(PROFILE_IDS.values()):
        raise AssertionError("recursive result must contain exactly the four profiles")
    quasi_reference = {
        (row["profile_id"], row["arm_id"], int(row["seed"])): row
        for row in quasi_grid_json["rows"]
    }

    for profile in PROFILE_FILES:
        trace = load_trace(root, profile)
        observations = trace["observations"]
        previous = trace["previous"]
        saved_raw = trace["raw"]
        saved_projected = trace["projected"]
        saved_delta = trace["saved_delta"]

        replayed_raw = actor_outputs(actors, observations, previous)
        profile_actor_error = float(np.max(np.abs(replayed_raw - saved_raw)))
        actor_replay_error = max(actor_replay_error, profile_actor_error)
        if profile_actor_error > ACTOR_REPLAY_ATOL:
            raise AssertionError(
                f"actor replay mismatch for profile {profile}: {profile_actor_error}"
            )

        replayed_projected = recursive_project(saved_raw)
        profile_projector_error = float(
            np.max(np.abs(replayed_projected - saved_projected))
        )
        projector_replay_error = max(projector_replay_error, profile_projector_error)
        if profile_projector_error > PROJECTOR_ATOL:
            raise AssertionError(
                f"projector replay mismatch for profile {profile}: {profile_projector_error}"
            )
        previous_projected = previous_array(saved_projected)
        profile_delta_error = float(
            np.max(np.abs((saved_projected - previous_projected) - saved_delta))
        )
        saved_delta_error = max(saved_delta_error, profile_delta_error)
        if profile_delta_error > PROJECTOR_ATOL:
            raise AssertionError("saved action_delta_norm mismatch")

        lower = np.minimum(previous_projected, saved_raw) - PROJECTOR_ATOL
        upper = np.maximum(previous_projected, saved_raw) + PROJECTOR_ATOL
        between_violations += int(
            np.count_nonzero((saved_projected < lower) | (saved_projected > upper))
        )
        slew_violations += int(
            np.count_nonzero(
                np.abs(saved_projected - previous_projected)
                > SLEW_LIMIT + PROJECTOR_ATOL
            )
        )

        raw_tv = channel_tv(saved_raw)
        projected_tv = channel_tv(saved_projected)
        terminal_residual = np.abs(
            saved_raw[:, -1].astype(np.float64)
            - saved_projected[:, -1].astype(np.float64)
        ).sum(axis=(0, 1))
        tvd_slack = raw_tv - projected_tv - terminal_residual
        if np.any(tvd_slack < -METRIC_ATOL):
            raise AssertionError("finite-record TV-diminishing inequality failed")
        if np.any(projected_tv > 6 * 150 * 4 * SLEW_LIMIT + METRIC_ATOL):
            raise AssertionError("slew-cap TV bound failed")

        reference = projection_reference[PROFILE_IDS[profile]]
        for channel_index, channel in enumerate(("M", "D")):
            if not math.isclose(
                float(raw_tv[channel_index]),
                float(reference["raw_tv"][channel]),
                abs_tol=METRIC_ATOL,
                rel_tol=0.0,
            ):
                raise AssertionError("raw TV differs from promoted probe result")
            if not math.isclose(
                float(projected_tv[channel_index]),
                float(reference["projected_tv"][channel]),
                abs_tol=METRIC_ATOL,
                rel_tol=0.0,
            ):
                raise AssertionError("projected TV differs from promoted probe result")

        projection_rows.append(
            {
                "profile": profile,
                "raw_tv": {"M": float(raw_tv[0]), "D": float(raw_tv[1])},
                "projected_tv": {
                    "M": float(projected_tv[0]),
                    "D": float(projected_tv[1]),
                },
                "terminal_tracking_residual_l1": {
                    "M": float(terminal_residual[0]),
                    "D": float(terminal_residual[1]),
                },
                "tvd_certificate_slack": {
                    "M": float(tvd_slack[0]),
                    "D": float(tvd_slack[1]),
                },
                "projected_tv_to_slew_cap": {
                    "M": float(projected_tv[0] / 900.0),
                    "D": float(projected_tv[1] / 900.0),
                },
            }
        )

        fixed_previous = np.repeat(
            previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1
        )
        fixed_observations = np.repeat(
            observations.mean(axis=1, keepdims=True), observations.shape[1], axis=1
        )
        fixed_raw = actor_outputs(actors, observations, fixed_previous)
        constant_raw = actor_outputs(actors, fixed_observations, fixed_previous)

        qref = quasi_reference[(PROFILE_IDS[profile], "an_cn_r0", 501)]
        actual_rms = channel_rms(saved_raw)
        fixed_rms = channel_rms(fixed_raw)
        constant_rms = channel_rms(constant_raw)
        for index, channel in enumerate(("M", "D")):
            for actual_value, expected_value, label in (
                (actual_rms[index], qref["actual_raw_rms"][channel], "actual"),
                (fixed_rms[index], qref["fixed_prev_raw_rms"][channel], "fixed"),
                (
                    constant_rms[index],
                    qref["constant_anchor_raw_rms"][channel],
                    "constant",
                ),
            ):
                if not math.isclose(
                    float(actual_value),
                    float(expected_value),
                    abs_tol=METRIC_ATOL,
                    rel_tol=0.0,
                ):
                    raise AssertionError(
                        f"{label} RMS differs from grid result for profile {profile}"
                    )

        actual_tv = channel_tv(saved_raw)
        fixed_tv = channel_tv(fixed_raw)
        constant_tv = channel_tv(constant_raw)
        previous_path_tv = channel_tv(saved_raw - fixed_raw)
        observation_path_tv = channel_tv(fixed_raw - constant_raw)
        previous_path_rms = channel_rms(saved_raw - fixed_raw)
        observation_path_rms = channel_rms(fixed_raw - constant_raw)

        for index, channel in enumerate(("M", "D")):
            tv_upper = (
                constant_tv[index]
                + observation_path_tv[index]
                + previous_path_tv[index]
            )
            tv_lower = max(
                0.0,
                constant_tv[index]
                - observation_path_tv[index]
                - previous_path_tv[index],
                observation_path_tv[index]
                - constant_tv[index]
                - previous_path_tv[index],
                previous_path_tv[index]
                - constant_tv[index]
                - observation_path_tv[index],
            )
            rms_upper = (
                constant_rms[index]
                + observation_path_rms[index]
                + previous_path_rms[index]
            )
            rms_lower = max(
                0.0,
                constant_rms[index]
                - observation_path_rms[index]
                - previous_path_rms[index],
                observation_path_rms[index]
                - constant_rms[index]
                - previous_path_rms[index],
                previous_path_rms[index]
                - constant_rms[index]
                - observation_path_rms[index],
            )
            if not (tv_lower - METRIC_ATOL <= actual_tv[index] <= tv_upper + METRIC_ATOL):
                raise AssertionError("TV polygon bound failed")
            if not (
                rms_lower - METRIC_ATOL
                <= actual_rms[index]
                <= rms_upper + METRIC_ATOL
            ):
                raise AssertionError("RMS polygon bound failed")
            ordered_previous_rms = actual_rms[index] - fixed_rms[index]
            ordered_observation_rms = fixed_rms[index] - constant_rms[index]
            ordered_rms_negative_contrasts += int(ordered_previous_rms < 0)
            ordered_rms_negative_contrasts += int(ordered_observation_rms < 0)
            decomposition_rows.append(
                {
                    "profile": profile,
                    "channel": channel,
                    "tv": {
                        "actual": float(actual_tv[index]),
                        "fixed_previous": float(fixed_tv[index]),
                        "constant_anchor": float(constant_tv[index]),
                        "path_norm_previous_input": float(previous_path_tv[index]),
                        "path_norm_observation": float(observation_path_tv[index]),
                        "ordered_previous_contrast": float(
                            actual_tv[index] - fixed_tv[index]
                        ),
                        "ordered_observation_contrast": float(
                            fixed_tv[index] - constant_tv[index]
                        ),
                        "sharp_norm_only_lower_bound": float(tv_lower),
                        "sharp_norm_only_upper_bound": float(tv_upper),
                        "triangle_cancellation_slack": float(tv_upper - actual_tv[index]),
                    },
                    "rms": {
                        "actual": float(actual_rms[index]),
                        "fixed_previous": float(fixed_rms[index]),
                        "constant_anchor": float(constant_rms[index]),
                        "path_norm_previous_input": float(previous_path_rms[index]),
                        "path_norm_observation": float(observation_path_rms[index]),
                        "ordered_previous_contrast": float(ordered_previous_rms),
                        "ordered_observation_contrast": float(ordered_observation_rms),
                        "sharp_norm_only_lower_bound": float(rms_lower),
                        "sharp_norm_only_upper_bound": float(rms_upper),
                        "triangle_cancellation_slack": float(
                            rms_upper - actual_rms[index]
                        ),
                    },
                }
            )

        temporal_mean = saved_raw.mean(axis=1, keepdims=True, dtype=np.float64)
        temporal_mean_repeated = np.repeat(temporal_mean, 150, axis=1)
        for index, channel in enumerate(("M", "D")):
            actual_channel = saved_raw[..., index].astype(np.float64)
            constant_channel = constant_raw[..., index].astype(np.float64)
            mean_channel = temporal_mean_repeated[..., index]
            actual_norm = float(np.sqrt(np.mean(np.square(actual_channel))))
            constant_norm = float(np.sqrt(np.mean(np.square(constant_channel))))
            mean_norm = float(np.sqrt(np.mean(np.square(mean_channel))))
            residual_norm = float(
                np.sqrt(np.mean(np.square(actual_channel - mean_channel)))
            )
            normalized_error = float(
                np.sqrt(np.mean(np.square(actual_channel - constant_channel)))
                / actual_norm
            )
            denominator = float(
                np.linalg.norm(actual_channel.ravel())
                * np.linalg.norm(constant_channel.ravel())
            )
            cosine = float(
                np.dot(actual_channel.ravel(), constant_channel.ravel()) / denominator
            )
            mean_share = float((mean_norm / actual_norm) ** 2)
            variance_share = float((residual_norm / actual_norm) ** 2)
            if not math.isclose(
                mean_share + variance_share,
                1.0,
                abs_tol=2.0e-7,
                rel_tol=0.0,
            ):
                raise AssertionError("temporal mean/variance RMS identity failed")
            quasi_rows.append(
                {
                    "profile": profile,
                    "channel": channel,
                    "constant_anchor_to_actual_rms": float(
                        constant_norm / actual_norm
                    ),
                    "temporal_mean_squared_rms_share": mean_share,
                    "within_record_temporal_variance_share": variance_share,
                    "constant_anchor_normalized_l2_error": normalized_error,
                    "constant_anchor_cosine_alignment": cosine,
                }
            )

        # The supplied package contains the recursive-intervention aggregate
        # result, but not its stepwise raw/projected intervention arrays.  A
        # fresh recursive actor replay is backend-sensitive: sub-ulp differences
        # in one actor call can alter later actor inputs and accumulate.  We
        # therefore verify (i) the actual projected path independently, (ii)
        # the promoted file hash through PACKAGE_MANIFEST.json, and (iii) every
        # reported intervention/actual ratio arithmetically.  We deliberately
        # do not substitute a newly generated recursive path for the missing
        # sealed intervention path.
        actual_metrics = joint_metrics(saved_projected)
        rref = recursive_reference[PROFILE_IDS[profile]]
        expected_actual = rref["actual"]
        for key in ("rms", "total_variation"):
            if not math.isclose(
                actual_metrics[key],
                expected_actual[key],
                abs_tol=METRIC_ATOL,
                rel_tol=0.0,
            ):
                raise AssertionError(
                    f"recursive actual metric mismatch: {profile}.{key}"
                )
        for channel in ("M", "D"):
            for key in ("rms", "total_variation"):
                if not math.isclose(
                    actual_metrics["per_channel"][channel][key],
                    expected_actual["per_channel"][channel][key],
                    abs_tol=METRIC_ATOL,
                    rel_tol=0.0,
                ):
                    raise AssertionError(
                        f"recursive actual channel metric mismatch: {profile}.{channel}.{key}"
                    )

        negative_control = rref["negative_control"]
        if (
            float(negative_control["raw_max_abs_error"]) != 0.0
            or float(negative_control["projected_max_abs_error"]) != 0.0
        ):
            raise AssertionError("promoted recursive negative control is not exact")

        intervention_metrics = rref["intervention"]
        reported_ratio = rref["intervention_to_actual"]
        for key in ("rms", "total_variation"):
            recomputed_ratio = float(
                intervention_metrics[key] / expected_actual[key]
            )
            if not math.isclose(
                recomputed_ratio,
                float(reported_ratio[key]),
                abs_tol=1.0e-12,
                rel_tol=1.0e-12,
            ):
                raise AssertionError(
                    f"recursive ratio arithmetic mismatch: {profile}.{key}"
                )
        for channel in ("M", "D"):
            for key in ("rms", "total_variation"):
                recomputed_ratio = float(
                    intervention_metrics["per_channel"][channel][key]
                    / expected_actual["per_channel"][channel][key]
                )
                if not math.isclose(
                    recomputed_ratio,
                    float(reported_ratio["per_channel"][channel][key]),
                    abs_tol=1.0e-12,
                    rel_tol=1.0e-12,
                ):
                    raise AssertionError(
                        f"recursive channel-ratio arithmetic mismatch: {profile}.{channel}.{key}"
                    )

        representative_intervention_rows.append(
            {
                "profile": profile,
                "intervention_to_actual_joint_tv": float(
                    reported_ratio["total_variation"]
                ),
                "intervention_to_actual_joint_rms": float(reported_ratio["rms"]),
                "intervention_to_actual_M_tv": float(
                    reported_ratio["per_channel"]["M"]["total_variation"]
                ),
                "intervention_to_actual_D_tv": float(
                    reported_ratio["per_channel"]["D"]["total_variation"]
                ),
                "verification_mode": (
                    "actual path independently replayed; promoted intervention "
                    "artifact hash and ratio arithmetic verified"
                ),
            }
        )

        flat_observations = observations.reshape(-1, 4, 7)
        flat_previous = previous.reshape(-1, 4, 2)
        flat_fixed_previous = fixed_previous.reshape(-1, 4, 2)
        flat_saved_raw = saved_raw.reshape(-1, 4, 2)
        flat_replayed_raw = replayed_raw.reshape(-1, 4, 2)
        flat_fixed_raw = fixed_raw.reshape(-1, 4, 2)
        previous_previous = previous_array(previous).reshape(-1, 4, 2)

        for agent, actor in enumerate(actors):
            states = np.concatenate(
                [flat_observations[:, agent], flat_previous[:, agent]], axis=1
            ).astype(np.float32)
            local = local_jacobian_certificate(actor, states)
            local_action = np.asarray(local["action"], dtype=np.float32)
            local_error = float(
                np.max(np.abs(local_action - flat_saved_raw[:, agent]))
            )
            if local_error > ACTOR_REPLAY_ATOL:
                raise AssertionError("analytic Jacobian forward replay mismatch")
            local_linf = np.asarray(local["local_linf"], dtype=np.float64)
            active_radius = np.asarray(local["active_radius"], dtype=np.float64)
            local_linf_values.append(local_linf)
            active_radius_values.append(active_radius)
            minimum_abs_preactivation = min(
                minimum_abs_preactivation,
                float(local["minimum_abs_preactivation"]),
            )
            exact_zero_preactivations += int(local["exact_zero_preactivations"])
            total_preactivations += int(local["preactivation_count"])

            anchor_delta = np.max(
                np.abs(flat_fixed_previous[:, agent] - flat_previous[:, agent]),
                axis=1,
            ).astype(np.float64)
            output_delta = np.max(
                np.abs(flat_fixed_raw[:, agent] - flat_replayed_raw[:, agent]), axis=1
            ).astype(np.float64)
            if np.any(anchor_delta <= 0):
                raise AssertionError("unexpected zero fixed-anchor perturbation")
            secant_gain = output_delta / anchor_delta
            secant_gain_values.append(secant_gain)
            all_anchor_delta_values.append(anchor_delta)
            anchor_inside_active_region += int(
                np.count_nonzero(anchor_delta < active_radius)
            )

            temporal_delta = np.max(
                np.abs(flat_previous[:, agent] - previous_previous[:, agent]),
                axis=1,
            ).astype(np.float64)
            all_temporal_delta_values.append(temporal_delta)
            temporal_inside_active_region += int(
                np.count_nonzero(temporal_delta < active_radius)
            )
            nonzero = temporal_delta > 0
            temporal_nonzero_count += int(np.count_nonzero(nonzero))
            temporal_nonzero_inside_active_region += int(
                np.count_nonzero(nonzero & (temporal_delta < active_radius))
            )
            total_actor_evaluations += states.shape[0]

    if between_violations or slew_violations:
        raise AssertionError("projector monotonicity/slew property violated")

    local_linf_all = np.concatenate(local_linf_values)
    active_radius_all = np.concatenate(active_radius_values)
    secant_gain_all = np.concatenate(secant_gain_values)
    anchor_delta_all = np.concatenate(all_anchor_delta_values)
    temporal_delta_all = np.concatenate(all_temporal_delta_values)

    feedback_ratios = np.asarray(
        [
            policy["fixed_mean_to_actual_tv_ratio"][channel]
            for policy in feedback_json["policies"]
            for channel in ("M", "D")
        ],
        dtype=np.float64,
    )
    quasi_ratios_by_channel = {
        channel: np.asarray(
            [
                row["constant_anchor_to_actual_rms_ratio"][channel]
                for row in quasi_grid_json["rows"]
            ],
            dtype=np.float64,
        )
        for channel in ("M", "D")
    }
    quasi_ratios_all = np.concatenate(
        [quasi_ratios_by_channel["M"], quasi_ratios_by_channel["D"]]
    )

    quasi_variance_values = np.asarray(
        [row["within_record_temporal_variance_share"] for row in quasi_rows],
        dtype=np.float64,
    )
    quasi_mean_values = np.asarray(
        [row["temporal_mean_squared_rms_share"] for row in quasi_rows],
        dtype=np.float64,
    )
    quasi_error_values = np.asarray(
        [row["constant_anchor_normalized_l2_error"] for row in quasi_rows],
        dtype=np.float64,
    )

    result: dict[str, Any] = {
        "schema_version": "r485_finite_record_math_certificate_v1",
        "overall_disposition": "CERTIFIED-BOUNDED-MECHANISM",
        "claim_ceiling": (
            "Exact projector and representative actor-path statements plus fixed-grid "
            "descriptions only; no training causality, unique root cause, closed-loop "
            "counterfactual, endpoint preservation, stability, safety, wear, topology "
            "generalisation, convergence, optimality, or retraining benefit."
        ),
        "subgoals": {
            "S1": {
                "disposition": "CERTIFIED",
                "result": (
                    "The scalar projector moves between previous and raw action, is "
                    "one-step non-expansive, and its recursive common-reset path is "
                    "total-variation diminishing with a terminal-residual strengthening."
                ),
            },
            "S2": {
                "disposition": "NONIDENTIFIED-UNIQUE-DECOMPOSITION",
                "result": (
                    "Only path-vector identities, sharp norm-only polygon bounds, and "
                    "declared order-specific signed contrasts are identified. Metric "
                    "differences are not causal shares."
                ),
            },
            "S3": {
                "disposition": "CERTIFIED-REPRESENTATIVE-DATA-UNDECIDABLE-FULL-GRID",
                "result": (
                    "Exact active-set Jacobians, same-region radii, and nonsmooth-safe "
                    "finite endpoint secant sensitivities are replayable for the one "
                    "included checkpoint and four traces. The other 23 checkpoint-level "
                    "certificates cannot be reconstructed from summaries."
                ),
            },
            "S4": {
                "disposition": "QUALIFIED-DESCRIPTIVE-ONLY",
                "result": (
                    "A near-one constant-anchor/actual RMS ratio establishes comparable "
                    "aggregate norm only. It does not establish closeness, temporal-mean "
                    "dominance, or a causal RMS source."
                ),
            },
            "S5": {
                "disposition": "FINITE-GRID-DESCRIPTIVE-ONLY",
                "result": (
                    "The fixed grids admit exact prevalence statements without sampling "
                    "uncertainty; no superpopulation inference is identified."
                ),
            },
            "S6": {
                "disposition": "MANUSCRIPT-PATCH-PROVIDED",
                "result": (
                    "Use the projector inequality plus explicit frozen-path/fixed-grid "
                    "language; replace both unqualified mechanism phrases."
                ),
            },
        },
        "language_audit": {
            "previous_action_feedback_amplifies_tv": {
                "disposition": "CURRENT-LANGUAGE-FAILS-AS-WRITTEN",
                "replacement": (
                    "On the frozen observation paths, replacing the time-varying "
                    "previous-executed-action actor input by its within-record mean "
                    "reduced raw TV on the tested fixed grid."
                ),
            },
            "quasi_static_setpoint_retains_rms": {
                "disposition": "QUALIFY",
                "replacement": (
                    "Constant-anchor raw RMS was at least 0.90 times actual raw RMS "
                    "in 141 of 192 tested channel-block ratios, with stronger prevalence "
                    "for D than M; this is a threshold count, not source dominance."
                ),
            },
        },
        "assumptions": [
            {
                "id": "A1",
                "text": (
                    "The mathematical actor is the real-valued ReLU--tanh map whose "
                    "parameters are the exported float32 tensors; replay differences up "
                    "to ACTOR_REPLAY_ATOL are numerical implementation tolerance."
                ),
            },
            {
                "id": "A2",
                "text": (
                    "Every record uses p[-1]=r[-1]=0 for the TV comparison; changing the "
                    "raw reference initial value changes the TV-diminishing statement."
                ),
            },
            {
                "id": "A3",
                "text": (
                    "All actor interventions freeze the supplied canonical observations; "
                    "they are not endogenous plant counterfactuals."
                ),
            },
            {
                "id": "A4",
                "text": (
                    "Exact-zero ReLU tests use the replayed float32 preactivations. Near-"
                    "zero nonzero values remain differentiable points but provide small "
                    "same-active-set radii."
                ),
            },
            {
                "id": "A5",
                "text": (
                    "The promoted recursive fixed-previous intervention is treated as a "
                    "hash-bound actor-path result. Its aggregate ratios are checked, but "
                    "independent backend-invariant path replay requires the absent stepwise "
                    "intervention action arrays or a bitwise-locked runtime."
                ),
            },
        ],
        "tolerances": {
            "actor_replay_atol": ACTOR_REPLAY_ATOL,
            "metric_atol": METRIC_ATOL,
            "projector_atol": PROJECTOR_ATOL,
            "result_comparison_atol": RESULT_ATOL,
        },
        "input_hashes": hashes,
        "certificate": {
            "projector": {
                "actor_replay_max_abs_error": actor_replay_error,
                "projector_replay_max_abs_error": projector_replay_error,
                "saved_action_delta_max_abs_error": saved_delta_error,
                "between_previous_and_raw_violations": between_violations,
                "slew_limit_violations": slew_violations,
                "per_channel_per_profile_slew_tv_cap": 900.0,
                "rows": projection_rows,
            },
            "identifiable_decomposition": {
                "ordered_path": "constant_anchor -> fixed_previous -> actual_raw",
                "rows": decomposition_rows,
                "negative_ordered_rms_contrast_count": ordered_rms_negative_contrasts,
                "missing_cross_cell": "pi(mean_observation, recorded_previous)",
                "full_grid_shapley_status": "DATA-UNDECIDABLE",
                "minimal_missing_for_full_grid_shapley": [
                    "the other 23 actor checkpoints",
                    "their per-profile canonical observations and recorded previous actions",
                    "or precomputed full action paths for the missing cross cell",
                ],
            },
            "actor_sensitivity": {
                "scope": "an_cn_r0 seed501, four profiles, six records, 150 steps, four agents",
                "actor_evaluations": total_actor_evaluations,
                "hidden_preactivations": total_preactivations,
                "exact_zero_hidden_preactivations": exact_zero_preactivations,
                "minimum_abs_hidden_preactivation": minimum_abs_preactivation,
                "local_previous_slot_jacobian_linf": qsummary(local_linf_all),
                "same_active_set_linf_radius": qsummary(active_radius_all),
                "fixed_mean_anchor_delta_linf": qsummary(anchor_delta_all),
                "fixed_mean_endpoint_secant_gain_linf": qsummary(secant_gain_all),
                "fixed_mean_segments_certified_inside_local_linf_ball": anchor_inside_active_region,
                "fixed_mean_segment_count": int(anchor_delta_all.size),
                "successive_previous_action_segments_certified_inside_local_linf_ball": temporal_inside_active_region,
                "successive_previous_action_segment_count": int(temporal_delta_all.size),
                "nonzero_successive_segments_certified_inside_local_linf_ball": temporal_nonzero_inside_active_region,
                "nonzero_successive_segment_count": temporal_nonzero_count,
                "interpretation": (
                    "The endpoint secant is exact and kink-safe for each supplied pair, "
                    "but it is not a uniform Lipschitz upper bound. The local Jacobian is "
                    "exact only inside its certified active-set radius."
                ),
                "full_24_checkpoint_status": "DATA-UNDECIDABLE",
                "minimal_missing_for_full_24": [
                    "the other 23 actor state_dict exports",
                    "their actor input paths or active-set/Jacobian exports",
                ],
            },
            "quasi_static_rms": {
                "fixed_grid": {
                    "ratio_count": int(quasi_ratios_all.size),
                    "at_least_0_90_count": int(np.count_nonzero(quasi_ratios_all >= 0.90)),
                    "at_most_0_50_count": int(np.count_nonzero(quasi_ratios_all <= 0.50)),
                    "greater_than_1_count": int(np.count_nonzero(quasi_ratios_all > 1.0)),
                    "at_least_1_10_count": int(np.count_nonzero(quasi_ratios_all >= 1.10)),
                    "M_at_least_0_90_count": int(
                        np.count_nonzero(quasi_ratios_by_channel["M"] >= 0.90)
                    ),
                    "D_at_least_0_90_count": int(
                        np.count_nonzero(quasi_ratios_by_channel["D"] >= 0.90)
                    ),
                    "all_ratio_summary": qsummary(quasi_ratios_all),
                    "M_ratio_summary": qsummary(quasi_ratios_by_channel["M"]),
                    "D_ratio_summary": qsummary(quasi_ratios_by_channel["D"]),
                },
                "representative_orthogonal_audit": {
                    "rows": quasi_rows,
                    "temporal_mean_squared_rms_share_range": {
                        "min": float(quasi_mean_values.min()),
                        "max": float(quasi_mean_values.max()),
                    },
                    "within_record_temporal_variance_share_range": {
                        "min": float(quasi_variance_values.min()),
                        "max": float(quasi_variance_values.max()),
                    },
                    "constant_anchor_normalized_l2_error_range": {
                        "min": float(quasi_error_values.min()),
                        "max": float(quasi_error_values.max()),
                    },
                    "full_grid_mean_variance_status": "DATA-UNDECIDABLE",
                    "minimal_missing_sufficient_statistics": [
                        "per record-agent-channel temporal sums of actual raw action",
                        "per record-agent-channel sums of squared actual raw action",
                        "actual/constant-anchor inner products for alignment",
                    ],
                },
            },
            "fixed_grid_descriptives": {
                "previous_action_grid": {
                    "policies": len(feedback_json["policies"]),
                    "channel_ratios": int(feedback_ratios.size),
                    "at_most_0_50_count": int(
                        np.count_nonzero(feedback_ratios <= 0.50)
                    ),
                    "at_most_0_205_count": int(
                        np.count_nonzero(feedback_ratios <= 0.205)
                    ),
                    "ratio_summary": qsummary(feedback_ratios),
                    "inference_class": "finite-grid descriptive",
                },
                "quasi_static_grid_inference_class": "finite-grid descriptive",
                "sampling_uncertainty_status": "NOT-IDENTIFIED-NO-SAMPLING-DESIGN",
            },
            "recursive_fixed_previous_intervention": {
                "rows": representative_intervention_rows,
                "inference_class": "actor-path intervention with frozen observations",
                "reported_result_integrity": (
                    "manifest SHA-256, actual-path metrics, and all reported ratios verified"
                ),
                "independent_intervention_path_replay_status": "DATA-UNDECIDABLE",
                "reason": (
                    "the stepwise recursive intervention raw/projected actions are absent; "
                    "a fresh stateful replay is not a backend-invariant substitute"
                ),
                "minimal_missing_for_backend_invariant_replay": [
                    "the 6x150x4x2 recursive intervention raw-action array",
                    "the 6x150x4x2 recursive intervention projected-action array",
                    "or a bitwise-locked runtime/container plus arithmetic determinism record",
                ],
            },
        },
        "conclusion_classes": {
            "exact_replay": [
                "representative actor output replay within tolerance",
                "production projector replay and TV-diminishing checks",
                "representative local Jacobians, active-set radii, endpoint secants",
                "representative temporal mean/variance RMS identity",
            ],
            "finite_grid_descriptive": [
                "24-policy one-profile fixed-previous raw-TV ratios",
                "24-policy four-profile constant-anchor raw-RMS ratios",
            ],
            "actor_path_intervention": [
                "fixed-previous raw replay",
                "constant-anchor raw replay",
                "recursive fixed-previous projected result (hash/arithmetic verified; path replay data absent)",
            ],
            "unidentified": [
                "training-causal mechanism",
                "unique or additive root-cause shares",
                "modified-controller plant observation path",
                "closed-loop endpoint preservation or action-guard passage",
                "benefit from retraining",
            ],
        },
        "source_locators": {
            "projector_code": "source/executed_action_sac.py:29-83",
            "actor_code": "source/networks.py:28-80",
            "projection_result": "posthoc/projection_tv_result.json#/candidate/profiles",
            "feedback_grid": "posthoc/feedback_grid_result.json#/policies",
            "quasi_grid": "posthoc/quasistatic_rms_grid_result.json#/rows",
            "recursive_intervention": "posthoc/recursive_intervention_result.json#/profiles",
            "representative_checkpoint": "checkpoint/an_cn_r0_seed501_final.pt#/members/*/actor",
            "representative_traces": "traces/canary_eval_[a-d].json#/records/*/steps",
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", default=None)
    parser.add_argument(
        "--write-result",
        default=None,
        help="write the reconstructed result JSON instead of checking the sibling file",
    )
    parser.add_argument(
        "--expected-result",
        default=None,
        help="override the math_result.json path used in verification mode",
    )
    args = parser.parse_args()
    script_dir = Path(__file__).resolve().parent
    root = locate_package_root(args.package_root, script_dir)
    computed = compute_result(root)

    if args.write_result:
        output = Path(args.write_result)
        if not output.is_absolute():
            output = Path.cwd() / output
        output.write_text(canonical_json(computed), encoding="utf-8")
        print(f"WROTE {output}")
        return 0

    expected_path = (
        Path(args.expected_result)
        if args.expected_result
        else script_dir / "math_result.json"
    )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    compare_numeric(computed, expected)
    sensitivity = computed["certificate"]["actor_sensitivity"]
    quasi = computed["certificate"]["quasi_static_rms"]["fixed_grid"]
    print(
        canonical_json(
            {
                "status": "PASS",
                "package_root": str(root),
                "overall_disposition": computed["overall_disposition"],
                "actor_evaluations": sensitivity["actor_evaluations"],
                "exact_zero_hidden_preactivations": sensitivity[
                    "exact_zero_hidden_preactivations"
                ],
                "quasi_static_at_least_0_90": f"{quasi['at_least_0_90_count']}/{quasi['ratio_count']}",
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
