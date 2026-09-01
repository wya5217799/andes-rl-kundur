#!/usr/bin/env python3
"""Deterministic CPU checker for the R485 finite-record mechanism certificate.

The checker validates the exact source package, replays the representative
checkpoint/traces, recomputes finite-grid summaries from the supplied JSON
rows, proves the numerical instances of the projector TV-residual inequality,
and constructs a kink-aware straight-path sensitivity certificate for the two
previous-action actor inputs.

Evidence scope: finite stored records/checkpoints only.  No plant, training, or
closed-loop counterfactual is simulated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
import torch.nn as nn

PACKAGE_ID = "gpt_pro_r485_mechanism_math_20260901"
EXPECTED_OUTER_SHA256 = (
    "530ed9942169f620c88ee14138d263a9271516b8366e1296006002378fe41410"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "c5fec5e301cae22fbc71818523aca119d85bcb304b42f4dc87043618b072aaaa"
)
PROFILE_IDS = (
    "canary_eval_a",
    "canary_eval_b",
    "canary_eval_c",
    "canary_eval_d",
)
CHANNELS = ("M", "D")
RECORDS = 6
STEPS = 150
AGENTS = 4
OBS_DIM = 7
PREV_DIM = 2
ACTION_DIM = 2
SLEW_LIMIT = 0.25
ROOT_TOLERANCE = 1.0e-13
REPLAY_TOLERANCE = 1.0e-6
NUMERIC_ATOL = 2.0e-9
NUMERIC_RTOL = 2.0e-9


class CertificateFailure(RuntimeError):
    """Raised when an identity, replay, or numerical certificate check fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CertificateFailure(message)


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def qsummary(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float64)
    require(array.size > 0, "cannot summarize an empty numerical array")
    require(bool(np.all(np.isfinite(array))), "non-finite value in numerical summary")
    return {
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "q95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
    }


def validate_source_package(root: Path, archive: Path | None) -> dict[str, Any]:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    require(manifest_path.is_file(), f"missing package manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    require(manifest.get("package_id") == PACKAGE_ID, "package_id mismatch")
    entries = manifest.get("entries")
    require(isinstance(entries, list) and len(entries) == 30, "expected 30 manifest entries")

    validated: list[dict[str, Any]] = []
    expected_members = {"PACKAGE_MANIFEST.json"}
    for row in entries:
        relative = row.get("entry")
        require(isinstance(relative, str) and relative, "invalid manifest entry path")
        expected_members.add(relative)
        path = root / relative
        require(path.is_file(), f"missing manifest payload: {relative}")
        size = path.stat().st_size
        digest = sha256_file(path)
        require(size == int(row.get("bytes")), f"byte-size mismatch: {relative}")
        require(digest == row.get("sha256"), f"SHA-256 mismatch: {relative}")
        validated.append({"entry": relative, "bytes": size, "sha256": digest})

    checkpoint_hash = sha256_file(root / "checkpoint/an_cn_r0_seed501_final.pt")
    require(checkpoint_hash == EXPECTED_CHECKPOINT_SHA256, "checkpoint identity mismatch")

    archive_receipt: dict[str, Any] = {
        "provided": archive is not None,
        "sha256": None,
        "member_count": None,
        "members_match_manifest": None,
    }
    if archive is not None:
        require(archive.is_file(), f"archive not found: {archive}")
        outer_hash = sha256_file(archive)
        require(outer_hash == EXPECTED_OUTER_SHA256, "outer archive SHA-256 mismatch")
        with zipfile.ZipFile(archive, "r") as bundle:
            names = bundle.namelist()
            require(len(names) == len(set(names)), "duplicate archive member name")
            require(not any(Path(name).is_absolute() or ".." in Path(name).parts for name in names),
                    "unsafe archive member path")
            require(set(names) == expected_members, "archive member set does not match manifest")
        archive_receipt = {
            "provided": True,
            "sha256": outer_hash,
            "member_count": len(names),
            "members_match_manifest": True,
        }

    return {
        "package_id": PACKAGE_ID,
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_entry_count": len(validated),
        "all_manifest_entries_validated": True,
        "checkpoint_sha256": checkpoint_hash,
        "archive": archive_receipt,
    }


class GaussianActor(nn.Module):
    """Exact deterministic architecture used by the supplied source/checkpoint."""

    def __init__(self) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        previous = OBS_DIM + PREV_DIM
        for width in (128, 128, 128, 128):
            layers.extend((nn.Linear(previous, width), nn.ReLU()))
            previous = width
        self.net = nn.Sequential(*layers)
        self.mean_head = nn.Linear(previous, ACTION_DIM)
        self.log_std_head = nn.Linear(previous, ACTION_DIM)

    def deterministic(self, state: torch.Tensor) -> torch.Tensor:
        hidden = self.net(state)
        return torch.tanh(self.mean_head(hidden))


RealNetwork = tuple[list[tuple[np.ndarray, np.ndarray]], tuple[np.ndarray, np.ndarray]]


def load_actors(root: Path) -> tuple[list[GaussianActor], list[RealNetwork], dict[str, Any]]:
    checkpoint = root / "checkpoint/an_cn_r0_seed501_final.pt"
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    require(isinstance(payload, Mapping), "checkpoint payload is not a mapping")
    require(payload.get("kind") == "r485-source-factorial", "checkpoint kind mismatch")
    require(payload.get("arm_id") == "an_cn_r0", "checkpoint arm mismatch")
    require(int(payload.get("seed")) == 501, "checkpoint seed mismatch")
    require(payload.get("stage") == "final", "checkpoint stage mismatch")
    members = payload.get("members")
    require(isinstance(members, list) and len(members) == AGENTS, "expected four actor members")

    actors: list[GaussianActor] = []
    real_networks: list[RealNetwork] = []
    for member in members:
        state = member.get("actor")
        require(isinstance(state, Mapping), "member actor state missing")
        actor = GaussianActor().cpu().eval()
        actor.load_state_dict(state, strict=True)
        actors.append(actor)

        hidden: list[tuple[np.ndarray, np.ndarray]] = []
        for index in (0, 2, 4, 6):
            hidden.append(
                (
                    state[f"net.{index}.weight"].detach().cpu().numpy().astype(np.float64),
                    state[f"net.{index}.bias"].detach().cpu().numpy().astype(np.float64),
                )
            )
        output = (
            state["mean_head.weight"].detach().cpu().numpy().astype(np.float64),
            state["mean_head.bias"].detach().cpu().numpy().astype(np.float64),
        )
        real_networks.append((hidden, output))

    identity = {
        "kind": payload["kind"],
        "arm_id": payload["arm_id"],
        "seed": int(payload["seed"]),
        "stage": payload["stage"],
        "members": len(members),
    }
    return actors, real_networks, identity


def load_profile(root: Path, profile_id: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    payload = read_json(root / "traces" / f"{profile_id}.json")
    records = payload.get("records")
    require(isinstance(records, list) and len(records) == RECORDS,
            f"{profile_id}: expected six records")
    observations = np.zeros((RECORDS, STEPS, AGENTS, OBS_DIM), dtype=np.float32)
    previous = np.zeros((RECORDS, STEPS, AGENTS, PREV_DIM), dtype=np.float32)
    raw = np.zeros((RECORDS, STEPS, AGENTS, ACTION_DIM), dtype=np.float32)
    projected = np.zeros_like(raw)

    for record_index, record in enumerate(records):
        require(record.get("checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA256,
                f"{profile_id}: trace/checkpoint identity mismatch")
        steps = record.get("steps")
        require(isinstance(steps, list) and len(steps) == STEPS,
                f"{profile_id}: expected 150 steps")
        prior = np.zeros((AGENTS, ACTION_DIM), dtype=np.float32)
        for step_index, step in enumerate(steps):
            obs = np.asarray(step["canonical_observation"], dtype=np.float32)
            raw_row = np.asarray(step["raw_action_norm"], dtype=np.float32)
            projected_row = np.asarray(step["projected_action_norm"], dtype=np.float32)
            require(obs.shape == (AGENTS, OBS_DIM), "observation shape mismatch")
            require(raw_row.shape == (AGENTS, ACTION_DIM), "raw action shape mismatch")
            require(projected_row.shape == (AGENTS, ACTION_DIM), "projected action shape mismatch")
            require(bool(np.all(np.isfinite(obs))), "non-finite observation")
            require(bool(np.all(np.isfinite(raw_row))), "non-finite raw action")
            require(bool(np.all(np.isfinite(projected_row))), "non-finite projected action")
            observations[record_index, step_index] = obs
            previous[record_index, step_index] = prior
            raw[record_index, step_index] = raw_row
            projected[record_index, step_index] = projected_row
            prior = projected_row
    return observations, previous, raw, projected


def actor_outputs_production(
    actors: Sequence[GaussianActor], observations: np.ndarray, previous: np.ndarray
) -> np.ndarray:
    """Use the production-style one-state-at-a-time float32 actor call."""
    output = np.zeros((*observations.shape[:3], ACTION_DIM), dtype=np.float32)
    flat_obs = observations.reshape(-1, AGENTS, OBS_DIM)
    flat_previous = previous.reshape(-1, AGENTS, PREV_DIM)
    flat_output = output.reshape(-1, AGENTS, ACTION_DIM)
    with torch.inference_mode():
        for row_index in range(len(flat_obs)):
            for agent_index, actor in enumerate(actors):
                state = np.concatenate(
                    (flat_obs[row_index, agent_index], flat_previous[row_index, agent_index])
                ).astype(np.float32)
                flat_output[row_index, agent_index] = (
                    actor.deterministic(torch.from_numpy(state).unsqueeze(0))
                    .cpu()
                    .numpy()[0]
                    .astype(np.float32)
                )
    return output


def project_action(previous: np.ndarray, raw: np.ndarray) -> np.ndarray:
    """Exact NumPy implementation copied semantically from supplied source."""
    previous32 = np.asarray(previous, dtype=np.float32)
    raw32 = np.asarray(raw, dtype=np.float32)
    require(previous32.shape == raw32.shape, "projector shape mismatch")
    amplitude = np.clip(raw32, -1.0, 1.0).astype(np.float32)
    previous64 = previous32.astype(np.float64)
    delta64 = np.clip(
        amplitude.astype(np.float64) - previous64, -SLEW_LIMIT, SLEW_LIMIT
    )
    executed = np.clip(previous64 + delta64, -1.0, 1.0).astype(np.float32)
    overshoot = executed.astype(np.float64) - previous64 > SLEW_LIMIT
    undershoot = executed.astype(np.float64) - previous64 < -SLEW_LIMIT
    if np.any(overshoot):
        executed[overshoot] = np.nextafter(executed[overshoot], np.float32(-np.inf))
    if np.any(undershoot):
        executed[undershoot] = np.nextafter(executed[undershoot], np.float32(np.inf))
    return np.clip(executed, -1.0, 1.0).astype(np.float32)


def project_sequence(raw: np.ndarray) -> np.ndarray:
    output = np.zeros_like(raw, dtype=np.float32)
    for record_index in range(raw.shape[0]):
        previous = np.zeros((AGENTS, ACTION_DIM), dtype=np.float32)
        for step_index in range(raw.shape[1]):
            previous = project_action(previous, raw[record_index, step_index])
            output[record_index, step_index] = previous
    return output


def channel_tv(values: np.ndarray) -> np.ndarray:
    values64 = values.astype(np.float64)
    prior = np.concatenate(
        (np.zeros((values.shape[0], 1, values.shape[2], values.shape[3])), values64[:, :-1]),
        axis=1,
    )
    return np.abs(values64 - prior).sum(axis=(0, 1, 2))


def channel_rms(values: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean(np.square(values.astype(np.float64)), axis=(0, 1, 2)))


def metrics(values: np.ndarray) -> dict[str, np.ndarray]:
    return {"rms": channel_rms(values), "tv": channel_tv(values)}


def real_forward_and_previous_jacobian(
    state: np.ndarray, network: RealNetwork
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    hidden_layers, (output_weight, output_bias) = network
    hidden = state.astype(np.float64)
    derivative = np.zeros((OBS_DIM + PREV_DIM, PREV_DIM), dtype=np.float64)
    derivative[OBS_DIM:, :] = np.eye(PREV_DIM, dtype=np.float64)
    preactivations: list[np.ndarray] = []
    for weight, bias in hidden_layers:
        preactivation = weight @ hidden + bias
        preactivations.append(preactivation)
        propagated = weight @ derivative
        active = (preactivation > 0.0).astype(np.float64)
        hidden = np.maximum(preactivation, 0.0)
        derivative = active[:, None] * propagated
    mean = output_weight @ hidden + output_bias
    mean_derivative = output_weight @ derivative
    action = np.tanh(mean)
    jacobian = (1.0 - np.square(action))[:, None] * mean_derivative
    return action, jacobian, preactivations


def torch_double_previous_jacobian(state: np.ndarray, network: RealNetwork) -> tuple[np.ndarray, np.ndarray]:
    hidden_layers, (output_weight, output_bias) = network
    x = torch.tensor(state, dtype=torch.float64, requires_grad=True)
    hidden = x
    for weight, bias in hidden_layers:
        hidden = torch.relu(
            torch.from_numpy(weight) @ hidden + torch.from_numpy(bias)
        )
    output = torch.tanh(
        torch.from_numpy(output_weight) @ hidden + torch.from_numpy(output_bias)
    )
    rows: list[np.ndarray] = []
    for channel in range(ACTION_DIM):
        gradient = torch.autograd.grad(output[channel], x, retain_graph=True)[0]
        rows.append(gradient.detach().cpu().numpy()[OBS_DIM:])
    return output.detach().cpu().numpy(), np.stack(rows)


def line_pieces(
    state0: np.ndarray, state1: np.ndarray, hidden_layers: Sequence[tuple[np.ndarray, np.ndarray]]
) -> list[tuple[float, float, np.ndarray, np.ndarray]]:
    """Partition [0,1] so each hidden activation pattern is fixed per open piece.

    Each tuple encodes h(s) = slope*s + intercept on [left,right].  Breakpoints
    are retained explicitly, so the certificate never differentiates through a
    ReLU kink.
    """
    pieces: list[tuple[float, float, np.ndarray, np.ndarray]] = [
        (0.0, 1.0, (state1 - state0).astype(np.float64), state0.astype(np.float64))
    ]
    for weight, bias in hidden_layers:
        next_pieces: list[tuple[float, float, np.ndarray, np.ndarray]] = []
        for left, right, slope, intercept in pieces:
            pre_slope = weight @ slope
            pre_intercept = weight @ intercept + bias
            nonzero = np.abs(pre_slope) > ROOT_TOLERANCE
            roots = -pre_intercept[nonzero] / pre_slope[nonzero] if np.any(nonzero) else np.empty(0)
            roots = roots[
                np.isfinite(roots)
                & (roots > left + ROOT_TOLERANCE)
                & (roots < right - ROOT_TOLERANCE)
            ]
            unique_roots: list[float] = []
            for root in np.sort(roots):
                value = float(root)
                if not unique_roots or abs(value - unique_roots[-1]) > ROOT_TOLERANCE * max(1.0, abs(value)):
                    unique_roots.append(value)
            points = [left, *unique_roots, right]
            for sub_left, sub_right in zip(points[:-1], points[1:]):
                midpoint = 0.5 * (sub_left + sub_right)
                active = (pre_slope * midpoint + pre_intercept) > 0.0
                next_pieces.append(
                    (
                        sub_left,
                        sub_right,
                        pre_slope * active,
                        pre_intercept * active,
                    )
                )
        pieces = next_pieces
    return pieces


def path_certificate(state0: np.ndarray, state1: np.ndarray, network: RealNetwork) -> dict[str, Any]:
    hidden_layers, (output_weight, output_bias) = network
    pieces = line_pieces(state0, state1, hidden_layers)
    variation = np.zeros(ACTION_DIM, dtype=np.float64)
    telescoped = np.zeros(ACTION_DIM, dtype=np.float64)
    minimum_width = 1.0
    for left, right, slope, intercept in pieces:
        minimum_width = min(minimum_width, right - left)
        mean_slope = output_weight @ slope
        mean_intercept = output_weight @ intercept + output_bias
        value_left = np.tanh(mean_slope * left + mean_intercept)
        value_right = np.tanh(mean_slope * right + mean_intercept)
        change = value_right - value_left
        telescoped += change
        variation += np.abs(change)
    output0, _, _ = real_forward_and_previous_jacobian(state0, network)
    output1, _, _ = real_forward_and_previous_jacobian(state1, network)
    endpoint_abs = np.abs(output1 - output0)
    return {
        "pieces": len(pieces),
        "variation": variation,
        "endpoint_abs": endpoint_abs,
        "telescoping_error": float(np.max(np.abs(telescoped - (output1 - output0)))),
        "endpoint_bound_violation": float(np.max(endpoint_abs - variation)),
        "minimum_piece_width": float(minimum_width),
        "output0": output0,
        "output1": output1,
    }


def shapley_two_factor(v00: float, v10: float, v01: float, v11: float) -> dict[str, float]:
    first = 0.5 * ((v10 - v00) + (v11 - v01))
    second = 0.5 * ((v01 - v00) + (v11 - v10))
    return {"first": float(first), "second": float(second), "total": float(v11 - v00)}


def summarize_grid_jsons(root: Path) -> dict[str, Any]:
    feedback = read_json(root / "posthoc/feedback_grid_result.json")
    feedback_rows = feedback["policies"]
    feedback_ratios = np.asarray(
        [row["fixed_mean_to_actual_tv_ratio"][channel] for row in feedback_rows for channel in CHANNELS],
        dtype=np.float64,
    )
    replay_errors = np.asarray(
        [row["sealed_raw_replay_max_abs_error"] for row in feedback_rows], dtype=np.float64
    )
    feedback_summary = {
        "policies": len(feedback_rows),
        "channel_policy_cells": int(feedback_ratios.size),
        "ratio": qsummary(feedback_ratios),
        "count_ratio_le_0_50": int(np.count_nonzero(feedback_ratios <= 0.50)),
        "prevalence_ratio_le_0_50": float(np.mean(feedback_ratios <= 0.50)),
        "maximum_replay_error": float(np.max(replay_errors)),
    }
    require(feedback_summary["policies"] == 24, "feedback grid policy count mismatch")
    require(feedback_summary["channel_policy_cells"] == 48, "feedback grid cell count mismatch")
    require(feedback_summary["count_ratio_le_0_50"] == 48, "feedback grid threshold count mismatch")
    require(feedback_summary["maximum_replay_error"] <= REPLAY_TOLERANCE, "feedback replay failed")
    for key in ("median", "q95", "max"):
        require(math.isclose(feedback_summary["ratio"][key], feedback["decision"][f"ratio_{key}"],
                             rel_tol=1e-12, abs_tol=1e-12), f"feedback {key} summary mismatch")

    quasistatic = read_json(root / "posthoc/quasistatic_rms_grid_result.json")
    qrows = quasistatic["rows"]
    ratios_all = np.asarray(
        [row["constant_anchor_to_actual_rms_ratio"][channel] for row in qrows for channel in CHANNELS],
        dtype=np.float64,
    )
    by_channel: dict[str, Any] = {}
    for channel in CHANNELS:
        values = np.asarray(
            [row["constant_anchor_to_actual_rms_ratio"][channel] for row in qrows], dtype=np.float64
        )
        by_channel[channel] = {
            "ratio": qsummary(values),
            "count_ge_0_90": int(np.count_nonzero(values >= 0.90)),
            "prevalence_ge_0_90": float(np.mean(values >= 0.90)),
        }
    by_profile: dict[str, Any] = {}
    for profile_id in PROFILE_IDS:
        values = np.asarray(
            [
                row["constant_anchor_to_actual_rms_ratio"][channel]
                for row in qrows
                if row["profile_id"] == profile_id
                for channel in CHANNELS
            ],
            dtype=np.float64,
        )
        by_profile[profile_id] = {
            "cells": int(values.size),
            "count_ge_0_90": int(np.count_nonzero(values >= 0.90)),
            "prevalence_ge_0_90": float(np.mean(values >= 0.90)),
        }
    quasistatic_summary = {
        "policies": len({(row["arm_id"], int(row["seed"])) for row in qrows}),
        "policy_profile_blocks": len(qrows),
        "channel_policy_profile_cells": int(ratios_all.size),
        "ratio": qsummary(ratios_all),
        "count_ge_0_90": int(np.count_nonzero(ratios_all >= 0.90)),
        "prevalence_ge_0_90": float(np.mean(ratios_all >= 0.90)),
        "count_le_0_50": int(np.count_nonzero(ratios_all <= 0.50)),
        "prevalence_le_0_50": float(np.mean(ratios_all <= 0.50)),
        "by_channel": by_channel,
        "by_profile": by_profile,
        "maximum_replay_error": float(
            max(row["sealed_raw_replay_max_abs_error"] for row in qrows)
        ),
    }
    require(quasistatic_summary["policies"] == 24, "quasi-static policy count mismatch")
    require(quasistatic_summary["policy_profile_blocks"] == 96, "quasi-static block count mismatch")
    require(quasistatic_summary["channel_policy_profile_cells"] == 192,
            "quasi-static channel-cell count mismatch")
    require(quasistatic_summary["count_ge_0_90"] == 141, "quasi-static >=0.90 count mismatch")
    require(by_channel["M"]["count_ge_0_90"] == 54, "M >=0.90 count mismatch")
    require(by_channel["D"]["count_ge_0_90"] == 87, "D >=0.90 count mismatch")
    require(quasistatic_summary["count_le_0_50"] == 0, "unexpected <=0.50 quasi-static cell")
    require(quasistatic_summary["maximum_replay_error"] <= REPLAY_TOLERANCE,
            "quasi-static grid replay failed")
    for key in ("min", "median", "max"):
        require(math.isclose(quasistatic_summary["ratio"][key], quasistatic["decision"][key],
                             rel_tol=1e-12, abs_tol=1e-12), f"quasi-static {key} mismatch")

    projection = read_json(root / "posthoc/projection_tv_result.json")
    projection_rows = projection["candidate"]["profiles"]
    projection_ratios = np.asarray(
        [row["projected_to_raw_tv_ratio"][channel] for row in projection_rows for channel in CHANNELS],
        dtype=np.float64,
    )
    projection_summary = {
        "profiles": len(projection_rows),
        "channel_profile_cells": int(projection_ratios.size),
        "ratio": qsummary(projection_ratios),
        "all_ratios_le_1": bool(np.all(projection_ratios <= 1.0)),
        "projector_replay_max_abs_error": float(
            projection["candidate"]["checks"]["projector_replay_max_abs_error"]
        ),
        "saved_action_delta_max_abs_error": float(
            projection["candidate"]["checks"]["saved_action_delta_max_abs_error"]
        ),
    }
    require(projection_summary["profiles"] == 4, "projection profile count mismatch")
    require(projection_summary["all_ratios_le_1"], "projection ratio exceeds one")
    require(projection_summary["projector_replay_max_abs_error"] <= REPLAY_TOLERANCE,
            "projection replay failed")

    recursive = read_json(root / "posthoc/recursive_intervention_result.json")
    recursive_rows = recursive["profiles"]
    recursive_summary = {
        "profiles": len(recursive_rows),
        "joint_tv_intervention_to_actual": {
            row["profile_id"]: float(row["intervention_to_actual"]["total_variation"])
            for row in recursive_rows
        },
        "joint_rms_intervention_to_actual": {
            row["profile_id"]: float(row["intervention_to_actual"]["rms"])
            for row in recursive_rows
        },
        "joint_tv_intervention_to_direct": {
            row["profile_id"]: float(row["intervention_to_direct_md"]["total_variation"])
            for row in recursive_rows
        },
        "joint_rms_intervention_to_direct": {
            row["profile_id"]: float(row["intervention_to_direct_md"]["rms"])
            for row in recursive_rows
        },
        "maximum_negative_control_raw_error": float(
            max(row["negative_control"]["raw_max_abs_error"] for row in recursive_rows)
        ),
        "maximum_negative_control_projected_error": float(
            max(row["negative_control"]["projected_max_abs_error"] for row in recursive_rows)
        ),
        "m_channel_rms_increase_all_profiles": bool(
            all(
                row["intervention_to_actual"]["per_channel"]["M"]["rms"] > 1.0
                for row in recursive_rows
            )
        ),
    }
    require(recursive_summary["profiles"] == 4, "recursive intervention profile count mismatch")
    require(recursive_summary["maximum_negative_control_raw_error"] <= REPLAY_TOLERANCE,
            "recursive raw negative control failed")
    require(recursive_summary["maximum_negative_control_projected_error"] <= REPLAY_TOLERANCE,
            "recursive projected negative control failed")
    require(recursive_summary["m_channel_rms_increase_all_profiles"],
            "reported M-channel RMS direction mismatch")

    reward = read_json(root / "posthoc/reward_tv_blindness_result.json")
    reward_rows = reward["profiles"]
    tv_order_ratios = np.asarray(
        [row["high_to_low_combined_tv_ratio"] for row in reward_rows], dtype=np.float64
    )
    reward_summary = {
        "profiles": len(reward_rows),
        "high_to_low_combined_tv_ratio": qsummary(tv_order_ratios),
        "maximum_action_cost_abs_difference": float(
            max(row["max_action_cost_abs_difference"] for row in reward_rows)
        ),
    }
    require(reward_summary["profiles"] == 4, "reward diagnostic profile count mismatch")
    require(reward_summary["maximum_action_cost_abs_difference"] <= 1e-12,
            "reward cost changed under row-multiset reordering")

    formal = read_json(root / "formal/r485_formal_analysis.json")
    qualification = formal["learner_qualification"]
    blocks = formal["threshold_sensitivity"]["primary"]["per_profile_blocks"]
    formal_summary = {
        "endpoint_qualified_count": int(qualification["endpoint_qualified_count"]),
        "complete_contract_passing_count": int(qualification["complete_contract_passing_count"]),
        "policy_profile_blocks": len(blocks),
        "blocks_failing_action_rms": int(
            sum(not row["guard"]["action_rms_no_harm"] for row in blocks)
        ),
        "blocks_failing_action_tv": int(
            sum(not row["guard"]["action_variation_no_harm"] for row in blocks)
        ),
    }
    require(formal_summary == {
        "endpoint_qualified_count": 121,
        "complete_contract_passing_count": 0,
        "policy_profile_blocks": 832,
        "blocks_failing_action_rms": 832,
        "blocks_failing_action_tv": 832,
    }, "formal headline/count identity mismatch")

    return {
        "formal_headline": formal_summary,
        "feedback_grid": feedback_summary,
        "quasistatic_rms_grid": quasistatic_summary,
        "projection_grid": projection_summary,
        "recursive_intervention": recursive_summary,
        "reward_temporal_order": reward_summary,
    }


def representative_certificate(
    root: Path, actors: Sequence[GaussianActor], real_networks: Sequence[RealNetwork]
) -> tuple[dict[str, Any], dict[str, Any]]:
    profiles: dict[str, Any] = {}
    local_operator_norms: list[float] = []
    piece_counts: list[int] = []
    piece_widths: list[float] = []
    path_gains: list[list[float]] = [[], []]
    secant_gains: list[list[float]] = [[], []]
    endpoint_path_ratios: list[list[float]] = [[], []]
    exact_zero_preactivations = 0
    near_zero_preactivations = 0
    minimum_abs_preactivation = math.inf
    kink_segments = 0
    zero_displacements = 0
    max_telescoping_error = 0.0
    max_endpoint_bound_violation = -math.inf
    max_float64_actual_error = 0.0
    max_float64_anchor_error = 0.0
    max_production_bound_violation = -math.inf
    autograd_jacobian_error = 0.0
    autograd_output_error = 0.0
    sampled_autograd_states = 0
    state_index = 0

    global_product_bounds: dict[str, float] = {}
    for agent_index, network in enumerate(real_networks):
        hidden, (output_weight, _) = network
        bound = np.linalg.norm(output_weight, 2)
        bound *= np.linalg.norm(hidden[3][0], 2)
        bound *= np.linalg.norm(hidden[2][0], 2)
        bound *= np.linalg.norm(hidden[1][0], 2)
        bound *= np.linalg.norm(hidden[0][0][:, OBS_DIM:], 2)
        global_product_bounds[f"agent_{agent_index}"] = float(bound)

    for profile_id in PROFILE_IDS:
        observations, previous, raw, projected = load_profile(root, profile_id)
        replay = actor_outputs_production(actors, observations, previous)
        fixed_previous = np.repeat(
            previous.mean(axis=1, keepdims=True), previous.shape[1], axis=1
        )
        fixed_observations = np.repeat(
            observations.mean(axis=1, keepdims=True), observations.shape[1], axis=1
        )
        fixed_prev_raw = actor_outputs_production(actors, observations, fixed_previous)
        constant_anchor_raw = actor_outputs_production(
            actors, fixed_observations, fixed_previous
        )
        missing_factorial_cell_raw = actor_outputs_production(
            actors, fixed_observations, previous
        )
        projected_replay = project_sequence(replay)
        fixed_prev_projected = project_sequence(fixed_prev_raw)

        raw_replay_error = float(np.max(np.abs(replay - raw)))
        projector_replay_error = float(np.max(np.abs(projected_replay - projected)))
        require(raw_replay_error <= REPLAY_TOLERANCE,
                f"{profile_id}: representative raw replay failed")
        require(projector_replay_error <= REPLAY_TOLERANCE,
                f"{profile_id}: representative projector replay failed")

        arrays = {
            "A_actual_raw": raw,
            "F_fixed_prev_raw": fixed_prev_raw,
            "C_constant_anchor_raw": constant_anchor_raw,
            "B_fixed_obs_actual_prev_raw": missing_factorial_cell_raw,
            "E_actual_projected": projected,
            "I_fixed_prev_projected": fixed_prev_projected,
        }
        metric_values = {name: metrics(values) for name, values in arrays.items()}
        channel_cells: dict[str, Any] = {}
        for channel_index, channel in enumerate(CHANNELS):
            cells = {
                name: {
                    "rms": float(value["rms"][channel_index]),
                    "tv": float(value["tv"][channel_index]),
                }
                for name, value in metric_values.items()
            }
            obs_prev_tv = shapley_two_factor(
                cells["C_constant_anchor_raw"]["tv"],
                cells["F_fixed_prev_raw"]["tv"],
                cells["B_fixed_obs_actual_prev_raw"]["tv"],
                cells["A_actual_raw"]["tv"],
            )
            obs_prev_rms = shapley_two_factor(
                cells["C_constant_anchor_raw"]["rms"],
                cells["F_fixed_prev_raw"]["rms"],
                cells["B_fixed_obs_actual_prev_raw"]["rms"],
                cells["A_actual_raw"]["rms"],
            )
            prev_projection_tv = shapley_two_factor(
                cells["F_fixed_prev_raw"]["tv"],
                cells["A_actual_raw"]["tv"],
                cells["I_fixed_prev_projected"]["tv"],
                cells["E_actual_projected"]["tv"],
            )
            prev_projection_rms = shapley_two_factor(
                cells["F_fixed_prev_raw"]["rms"],
                cells["A_actual_raw"]["rms"],
                cells["I_fixed_prev_projected"]["rms"],
                cells["E_actual_projected"]["rms"],
            )
            difference = raw[..., channel_index].astype(np.float64) - fixed_prev_raw[..., channel_index].astype(np.float64)
            scalar_difference = difference[..., None]
            contrast_bounds = {
                "absolute_rms_metric_contrast": abs(
                    cells["A_actual_raw"]["rms"] - cells["F_fixed_prev_raw"]["rms"]
                ),
                "rms_of_pointwise_difference": float(np.sqrt(np.mean(np.square(difference)))),
                "absolute_tv_metric_contrast": abs(
                    cells["A_actual_raw"]["tv"] - cells["F_fixed_prev_raw"]["tv"]
                ),
                "tv_of_pointwise_difference": float(channel_tv(scalar_difference)[0]),
            }
            require(
                contrast_bounds["absolute_rms_metric_contrast"]
                <= contrast_bounds["rms_of_pointwise_difference"] + 1e-12,
                "RMS reverse-triangle inequality failed",
            )
            require(
                contrast_bounds["absolute_tv_metric_contrast"]
                <= contrast_bounds["tv_of_pointwise_difference"] + 1e-9,
                "TV reverse-triangle inequality failed",
            )
            channel_cells[channel] = {
                "cells": cells,
                "declared_shapley_obs_prev": {
                    "observation_factor": obs_prev_tv["first"],
                    "previous_action_factor": obs_prev_tv["second"],
                    "total_tv_contrast": obs_prev_tv["total"],
                    "rms_observation_factor": obs_prev_rms["first"],
                    "rms_previous_action_factor": obs_prev_rms["second"],
                    "total_rms_contrast": obs_prev_rms["total"],
                },
                "declared_shapley_prev_projection": {
                    "previous_action_factor_tv": prev_projection_tv["first"],
                    "projector_factor_tv": prev_projection_tv["second"],
                    "total_tv_contrast": prev_projection_tv["total"],
                    "previous_action_factor_rms": prev_projection_rms["first"],
                    "projector_factor_rms": prev_projection_rms["second"],
                    "total_rms_contrast": prev_projection_rms["total"],
                },
                "metric_contrast_bounds": contrast_bounds,
            }

        raw_tv = channel_tv(raw)
        projected_tv = channel_tv(projected)
        final_tracking = np.abs(
            raw[:, -1].astype(np.float64) - projected[:, -1].astype(np.float64)
        ).sum(axis=(0, 1))
        residual = {
            channel: {
                "raw_tv": float(raw_tv[index]),
                "projected_tv": float(projected_tv[index]),
                "final_tracking_l1": float(final_tracking[index]),
                "slack": float(raw_tv[index] - projected_tv[index] - final_tracking[index]),
            }
            for index, channel in enumerate(CHANNELS)
        }
        require(all(row["slack"] >= -1e-9 for row in residual.values()),
                f"{profile_id}: TV-residual inequality failed")

        quasi_decomposition: dict[str, Any] = {}
        for channel_index, channel in enumerate(CHANNELS):
            actual = raw[..., channel_index].astype(np.float64)
            temporal_mean = np.mean(actual, axis=1)
            temporal_variance = float(
                np.mean(np.square(actual - temporal_mean[:, None, :]))
            )
            temporal_mean_energy = float(np.mean(np.square(temporal_mean)))
            anchor = constant_anchor_raw[:, 0, :, channel_index].astype(np.float64)
            anchor_energy = float(np.mean(np.square(anchor)))
            mean_anchor_mismatch = float(np.mean(np.square(temporal_mean - anchor)))
            actual_energy = float(np.mean(np.square(actual)))
            actual_anchor_error = float(
                np.mean(np.square(actual - constant_anchor_raw[..., channel_index].astype(np.float64)))
            )
            pythagorean_error = abs(
                actual_anchor_error - (temporal_variance + mean_anchor_mismatch)
            )
            require(pythagorean_error <= 1e-12, "quasi-static RMS identity failed")
            quasi_decomposition[channel] = {
                "actual_rms": float(math.sqrt(actual_energy)),
                "anchor_rms": float(math.sqrt(anchor_energy)),
                "anchor_to_actual_rms_ratio": float(math.sqrt(anchor_energy / actual_energy)),
                "temporal_mean_energy_fraction": float(temporal_mean_energy / actual_energy),
                "temporal_variance_fraction": float(temporal_variance / actual_energy),
                "anchor_mean_mismatch_rms": float(math.sqrt(mean_anchor_mismatch)),
                "actual_anchor_error_rms": float(math.sqrt(actual_anchor_error)),
                "pythagorean_error": float(pythagorean_error),
            }

        profiles[profile_id] = {
            "raw_replay_max_abs_error": raw_replay_error,
            "projector_replay_max_abs_error": projector_replay_error,
            "tv_residual_inequality": residual,
            "quasistatic_rms_decomposition": quasi_decomposition,
            "factorial_cells_and_declared_allocations": channel_cells,
        }

        for record_index in range(RECORDS):
            anchor = previous[record_index].mean(axis=0).astype(np.float64)
            for step_index in range(STEPS):
                for agent_index in range(AGENTS):
                    state0 = np.concatenate(
                        (observations[record_index, step_index, agent_index],
                         previous[record_index, step_index, agent_index])
                    ).astype(np.float64)
                    state1 = np.concatenate(
                        (observations[record_index, step_index, agent_index], anchor[agent_index])
                    ).astype(np.float64)
                    output0, jacobian, preactivations = real_forward_and_previous_jacobian(
                        state0, real_networks[agent_index]
                    )
                    local_operator_norms.append(float(np.linalg.svd(jacobian, compute_uv=False)[0]))
                    for preactivation in preactivations:
                        exact_zero_preactivations += int(np.count_nonzero(preactivation == 0.0))
                        near_zero_preactivations += int(
                            np.count_nonzero(np.abs(preactivation) <= 1e-7)
                        )
                        minimum_abs_preactivation = min(
                            minimum_abs_preactivation,
                            float(np.min(np.abs(preactivation))),
                        )

                    certificate = path_certificate(state0, state1, real_networks[agent_index])
                    piece_counts.append(int(certificate["pieces"]))
                    piece_widths.append(float(certificate["minimum_piece_width"]))
                    if certificate["pieces"] > 1:
                        kink_segments += 1
                    max_telescoping_error = max(
                        max_telescoping_error, float(certificate["telescoping_error"])
                    )
                    max_endpoint_bound_violation = max(
                        max_endpoint_bound_violation,
                        float(certificate["endpoint_bound_violation"]),
                    )

                    production0 = raw[record_index, step_index, agent_index].astype(np.float64)
                    production1 = fixed_prev_raw[record_index, step_index, agent_index].astype(np.float64)
                    error0 = np.abs(output0 - production0)
                    error1 = np.abs(certificate["output1"] - production1)
                    max_float64_actual_error = max(max_float64_actual_error, float(np.max(error0)))
                    max_float64_anchor_error = max(max_float64_anchor_error, float(np.max(error1)))
                    production_endpoint = np.abs(production1 - production0)
                    production_bound = certificate["variation"] + error0 + error1
                    max_production_bound_violation = max(
                        max_production_bound_violation,
                        float(np.max(production_endpoint - production_bound)),
                    )

                    displacement = float(np.linalg.norm(state1[-PREV_DIM:] - state0[-PREV_DIM:]))
                    if displacement == 0.0:
                        zero_displacements += 1
                    else:
                        for channel_index in range(ACTION_DIM):
                            path_gains[channel_index].append(
                                float(certificate["variation"][channel_index] / displacement)
                            )
                            secant_gains[channel_index].append(
                                float(certificate["endpoint_abs"][channel_index] / displacement)
                            )
                            if certificate["variation"][channel_index] > 0.0:
                                endpoint_path_ratios[channel_index].append(
                                    float(
                                        certificate["endpoint_abs"][channel_index]
                                        / certificate["variation"][channel_index]
                                    )
                                )

                    if state_index % 227 == 0:
                        torch_output, torch_jacobian = torch_double_previous_jacobian(
                            state0, real_networks[agent_index]
                        )
                        autograd_output_error = max(
                            autograd_output_error,
                            float(np.max(np.abs(torch_output - output0))),
                        )
                        autograd_jacobian_error = max(
                            autograd_jacobian_error,
                            float(np.max(np.abs(torch_jacobian - jacobian))),
                        )
                        sampled_autograd_states += 1
                    state_index += 1

    require(max_telescoping_error <= 1e-10, "path telescoping check failed")
    require(max_endpoint_bound_violation <= 1e-12, "path endpoint bound failed")
    require(max_production_bound_violation <= 1e-12, "production endpoint bound failed")
    require(max_float64_actual_error <= REPLAY_TOLERANCE, "float64/production actual endpoint mismatch")
    require(max_float64_anchor_error <= REPLAY_TOLERANCE, "float64/production anchor endpoint mismatch")
    require(autograd_jacobian_error <= 1e-12, "manual/autograd Jacobian mismatch")
    require(autograd_output_error <= 1e-12, "manual/autograd output mismatch")

    sensitivity = {
        "state_segments": state_index,
        "hidden_preactivations": state_index * 4 * 128,
        "exact_zero_preactivations": exact_zero_preactivations,
        "near_zero_preactivations_abs_le_1e_7": near_zero_preactivations,
        "minimum_abs_preactivation": float(minimum_abs_preactivation),
        "zero_previous_input_displacements": zero_displacements,
        "segments_crossing_at_least_one_hidden_kink": kink_segments,
        "line_piece_count": qsummary(piece_counts),
        "minimum_line_piece_width": float(np.min(np.asarray(piece_widths))),
        "local_previous_jacobian_spectral_norm": qsummary(local_operator_norms),
        "global_product_spectral_bound_by_agent": global_product_bounds,
        "path_variation_gain": {
            "M": qsummary(path_gains[0]),
            "D": qsummary(path_gains[1]),
        },
        "secant_gain": {
            "M": qsummary(secant_gains[0]),
            "D": qsummary(secant_gains[1]),
        },
        "endpoint_to_path_variation_ratio": {
            "M": qsummary(endpoint_path_ratios[0]),
            "D": qsummary(endpoint_path_ratios[1]),
        },
        "root_partition_tolerance": ROOT_TOLERANCE,
        "max_path_telescoping_error": max_telescoping_error,
        "max_float64_endpoint_bound_violation": max_endpoint_bound_violation,
        "max_float64_vs_production_error_actual_endpoint": max_float64_actual_error,
        "max_float64_vs_production_error_anchor_endpoint": max_float64_anchor_error,
        "max_production_endpoint_bound_violation_after_roundoff_allowance": max_production_bound_violation,
        "autograd_cross_check": {
            "sampled_states": sampled_autograd_states,
            "max_output_error": autograd_output_error,
            "max_jacobian_error": autograd_jacobian_error,
        },
    }
    return profiles, sensitivity


def compare_expected(expected: Any, actual: Any, path: str, atol: float, rtol: float) -> None:
    """Recursively compare every expected leaf; extra actual keys are allowed."""
    if isinstance(expected, Mapping):
        require(isinstance(actual, Mapping), f"expected mapping at {path}")
        for key, value in expected.items():
            require(key in actual, f"missing expected key: {path}/{key}")
            compare_expected(value, actual[key], f"{path}/{key}", atol, rtol)
        return
    if isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected),
                f"list shape mismatch at {path}")
        for index, value in enumerate(expected):
            compare_expected(value, actual[index], f"{path}/{index}", atol, rtol)
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        require(actual == expected, f"value mismatch at {path}: expected {expected!r}, got {actual!r}")
        return
    if isinstance(expected, int):
        require(int(actual) == expected, f"integer mismatch at {path}: expected {expected}, got {actual}")
        return
    if isinstance(expected, float):
        require(math.isfinite(float(actual)), f"non-finite actual at {path}")
        require(math.isclose(float(actual), expected, rel_tol=rtol, abs_tol=atol),
                f"float mismatch at {path}: expected {expected:.17g}, got {float(actual):.17g}")
        return
    require(actual == expected, f"unsupported/mismatched expected value at {path}")


def build_certificate(root: Path, archive: Path | None) -> dict[str, Any]:
    source_identity = validate_source_package(root, archive)
    grid = summarize_grid_jsons(root)
    actors, real_networks, checkpoint_identity = load_actors(root)
    representative, sensitivity = representative_certificate(root, actors, real_networks)
    raw_tv_upper = RECORDS * AGENTS * (1 + (STEPS - 1) * 2)
    projected_tv_upper = RECORDS * AGENTS * STEPS * SLEW_LIMIT
    require(raw_tv_upper == 7176, "raw-TV range calculation mismatch")
    require(projected_tv_upper == 900.0, "projected-TV range calculation mismatch")

    return {
        "schema_version": "r485_finite_record_certificate_v1",
        "source_identity": source_identity,
        "checkpoint_identity": checkpoint_identity,
        "finite_grid": grid,
        "theoretical_metric_ranges": {
            "raw_component_rms": {"lower": 0.0, "upper": 1.0},
            "raw_channel_tv": {"lower": 0.0, "upper": float(raw_tv_upper)},
            "projected_channel_tv": {"lower": 0.0, "upper": float(projected_tv_upper)},
            "dimensions": {"records": RECORDS, "steps": STEPS, "agents": AGENTS},
        },
        "representative_profiles": representative,
        "previous_action_path_sensitivity": sensitivity,
        "checks": {
            "status": "PASS",
            "scope": "finite stored package, representative checkpoint/traces, and supplied full-grid rows",
            "plant_counterfactual_run": False,
            "training_run": False,
            "random_sampling_assumption": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True, help="extracted source package root")
    parser.add_argument("--archive", type=Path, help="exact source ZIP; validates outer hash/member set")
    parser.add_argument("--expected", type=Path, help="math_result.json or raw expected certificate")
    parser.add_argument("--output", type=Path, help="write full certificate JSON here")
    parser.add_argument("--atol", type=float, default=NUMERIC_ATOL)
    parser.add_argument("--rtol", type=float, default=NUMERIC_RTOL)
    args = parser.parse_args()

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    np.seterr(all="raise")

    try:
        certificate = build_certificate(args.input_root.resolve(), args.archive.resolve() if args.archive else None)
        expected_status = "NOT_REQUESTED"
        if args.expected is not None:
            expected_document = read_json(args.expected)
            expected = expected_document.get("numerical_certificate", expected_document)
            compare_expected(expected, certificate, "numerical_certificate", args.atol, args.rtol)
            expected_status = "PASS"
        document = {
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "torch": torch.__version__,
                "device": "cpu",
                "threads": 1,
                "deterministic_algorithms": True,
            },
            "expected_comparison": expected_status,
            "certificate": certificate,
        }
        text = json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output is not None:
            args.output.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
        return 0
    except (CertificateFailure, KeyError, ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        sys.stderr.write(f"CERTIFICATE FAILURE: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
