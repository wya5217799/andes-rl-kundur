"""Modal-decomposition probe over sealed evaluation records (GPT Pro A1/A2 check).

Motivation:
    The external A1/A2 theory answer (NOTE-0029; registered design aid)
    claims three algebraic facts about the frozen cost definitions:
    (1) the common cost ``c_c = mean_i (x_i/sigma_f)^2 + mean_i
    (rocof_i/sigma_rocof)^2`` is NOT a pure common-mode cost — under the
    frozen orthonormal frame (mean direction + differential rows T) it
    decomposes exactly as ``c^2/sigma_f^2 + ||T x||^2/(4 sigma_f^2)`` and
    the RoCoF analogue (answer eq. A.2); (2) the effort term is total
    executed-action energy with the exact modal split
    ``e = (1/4)||A_c||_F^2 + (1/4)||A_d||_F^2`` (answer eq. A.3); and
    (3) therefore the modal fraction of the executed actions,
    ``eta_d^a = sum_t ||T A_t||_F^2 / sum_t ||A_t||_F^2``, decides whether
    the penalty acts mostly on differential or common action energy.

    This probe verifies the identities numerically on the sealed
    evaluation trajectories (read-only) and reports per-arm modal
    fractions.  It never modifies sealed artifacts and never re-runs a
    trajectory; its output is a working-note JSON under tmp/.

Usage:
    python probes/md_decoupling_modal_decomposition.py <round-dir> <out.json>

    <round-dir> is repo-relative, e.g.
    results/research_loop/r419_slew_state_bundle.  Output is create-only
    (refuses to overwrite) with a sha256 sidecar.

Failure modes:
    Missing eval tree, hash mismatches, or a Parseval identity violation
    above 1e-9 (float32 trajectories) abort with a nonzero exit; a
    violation is a real finding, never silently dropped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

SIGMA_F = 0.15  # Hz, frozen in the CD reward contract
SIGMA_ROCOF = 1.0  # Hz/s, frozen
DT = 0.2  # s, frozen
NOMINAL_HZ = 60.0

# Frozen orthonormal differential frame (row 0 = inter-area).
_T = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0, 0.0],
        [0.0, 0.0, 1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)],
    ],
    dtype=float,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def modal_decompose_frequency(
    x: np.ndarray, rocof: np.ndarray | None = None
) -> dict[str, float]:
    """Exact decomposition of the frozen common cost (answer eq. A.2).

    ``x`` = frequency deviation (Hz) per unit, shape (n_units,);
    ``rocof`` optional, same shape.  Returns the two algebraic forms and
    the identity residual (must be ~0 at float precision).
    """
    c = float(np.mean(x))
    z = _T @ x
    mean_squares = float(np.mean(x**2))
    decomposed = float(c**2 + np.sum(z**2) / 4.0)
    out: dict[str, float] = {
        "frequency_mean_squares": mean_squares,
        "frequency_decomposed": decomposed,
        "frequency_identity_residual": abs(mean_squares - decomposed),
        "frequency_common_energy_share": (
            c**2 / mean_squares if mean_squares > 0.0 else 0.0
        ),
        "frequency_differential_energy_share": (
            np.sum(z**2) / 4.0 / mean_squares if mean_squares > 0.0 else 0.0
        ),
    }
    if rocof is not None:
        c_r = float(np.mean(rocof))
        z_r = _T @ rocof
        ms_r = float(np.mean(rocof**2))
        dec_r = float(c_r**2 + np.sum(z_r**2) / 4.0)
        out.update(
            {
                "rocof_mean_squares": ms_r,
                "rocof_decomposed": dec_r,
                "rocof_identity_residual": abs(ms_r - dec_r),
            }
        )
    return out


def action_modal_fraction(actions: np.ndarray) -> dict[str, float]:
    """Modal split of executed normalized actions (answer eq. A.3).

    ``actions`` shape (n_steps, 4, 2) of executed normalized actions.
    """
    flat = actions.reshape(-1, 4, 2)
    total = float(np.sum(flat**2)) / 4.0  # e_t = mean_i ||a_i||^2
    sum_a = np.sum(flat, axis=1)  # sum_i A_i
    common_energy = float(np.sum(sum_a**2)) / 16.0  # ||q0^T A||^2 / 4
    differential = np.einsum("ij,tjk->tik", _T, flat)
    differential_energy = float(np.sum(differential**2)) / 4.0
    return {
        "total_action_energy": total,
        "common_action_energy": common_energy,
        "differential_action_energy": differential_energy,
        "eta_d_action": (
            differential_energy / total if total > 0.0 else 0.0
        ),
        "eta_c_action": (
            common_energy / total if total > 0.0 else 0.0
        ),
        "identity_residual": abs(total - common_energy - differential_energy),
    }


def _rocof_from_frequencies(freq_hz: np.ndarray, dt: float) -> np.ndarray:
    """Backward-difference RoCoF (Hz/s) matching the frozen reward seam."""
    if freq_hz.shape[0] < 2:
        return np.zeros_like(freq_hz)
    return np.vstack(
        [freq_hz[0] - freq_hz[0], np.diff(freq_hz, axis=0) / dt]
    )


def process_record(record: Mapping[str, Any]) -> dict[str, Any]:
    rows = record["steps"]
    frequencies = np.asarray(
        [row["freq_hz_physical"] for row in rows], dtype=float
    )
    actions = np.asarray([row["action_norm"] for row in rows], dtype=float)
    x = frequencies - NOMINAL_HZ
    rocof = _rocof_from_frequencies(frequencies, DT)
    per_step_checks = []
    for step_index in range(x.shape[0]):
        check = modal_decompose_frequency(
            x[step_index], rocof[step_index]
        )
        check["step_index"] = step_index
        per_step_checks.append(check)
    action = action_modal_fraction(actions)
    # aggregate frequency modal share over the trajectory (energy-weighted)
    common_freq_energy = float(np.sum(np.mean(x, axis=1) ** 2))
    total_freq_energy = float(np.sum(x**2))
    return {
        "arm_id": str(record["arm_id"]),
        "training_seed": record.get("training_seed"),
        "profile_id": str(record["profile_id"]),
        "scenario_id": str(record["scenario_id"]),
        "steps": int(len(rows)),
        "frequency_identity_max_residual": float(
            max(row["frequency_identity_residual"] for row in per_step_checks)
        ),
        "rocof_identity_max_residual": float(
            max(row["rocof_identity_residual"] for row in per_step_checks)
        ),
        "frequency_differential_energy_share": (
            float(np.sum((_T @ x.T) ** 2) / 4.0 / total_freq_energy)
            if total_freq_energy > 0.0
            else 0.0
        ),
        "action_modal": action,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_dir")
    parser.add_argument("out_json")
    args = parser.parse_args()
    round_dir = (ROOT / args.round_dir).resolve()
    eval_dir = round_dir / "eval"
    if not eval_dir.is_dir():
        raise SystemExit(f"no eval tree: {eval_dir}")
    out_path = ROOT / args.out_json
    if out_path.exists() or Path(f"{out_path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only probe output: {out_path}")

    records = []
    identity_max = 0.0
    for payload_path in sorted(eval_dir.rglob("*.json")):
        payload = _read_hashed_json(payload_path)
        for record in payload["records"]:
            processed = process_record(record)
            identity_max = max(
                identity_max,
                processed["frequency_identity_max_residual"],
                processed["rocof_identity_max_residual"],
            )
            records.append(processed)

    # per-arm|seed aggregation over profiles
    aggregates: dict[str, dict[str, float]] = {}
    for processed in records:
        key = f"{processed['arm_id']}|{processed['training_seed']}"
        entry = aggregates.setdefault(
            key,
            {
                "total_action_energy": 0.0,
                "differential_action_energy": 0.0,
                "records": 0,
            },
        )
        entry["total_action_energy"] += processed["action_modal"][
            "total_action_energy"
        ]
        entry["differential_action_energy"] += processed["action_modal"][
            "differential_action_energy"
        ]
        entry["records"] += 1
    per_arm = {}
    for key, entry in aggregates.items():
        per_arm[key] = {
            "eta_d_action": (
                entry["differential_action_energy"]
                / entry["total_action_energy"]
                if entry["total_action_energy"] > 0.0
                else 0.0
            ),
            "total_action_energy": entry["total_action_energy"],
            "differential_action_energy": entry["differential_action_energy"],
            "records": entry["records"],
        }

    payload = {
        "schema_version": 1,
        "round_dir": str(args.round_dir),
        "identity_max_residual": identity_max,
        "identity_tolerance": 1e-9,
        "identity_verified": bool(identity_max <= 1e-9),
        "per_arm_seed": per_arm,
        "per_record": records,
        "role": "working-note-theory-verification-not-formal-evidence",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n",
        encoding="utf-8",
    )
    digest = _sha256_file(out_path)
    Path(f"{out_path}.sha256").write_text(
        f"{digest}  {out_path.name}\n", encoding="ascii"
    )
    print(f"identity_verified={payload['identity_verified']} "
          f"max_residual={identity_max:.3e} records={len(records)}")
    print(json.dumps(per_arm, indent=1))
    return 0 if payload["identity_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
