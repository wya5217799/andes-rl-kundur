"""R421 B3 diagnostic readout probe (plan execution amendment, R419 precedent).

Applies the P3 pre-registered readout-to-failure-class mapping to the six
sealed ``diagnostics.csv`` files.  Read-only over the hashed manifests and
CSVs; writes one create-only hashed JSON into the R421 results root.

Pre-registered numeric proxies (frozen before the training curves were
complete; the qualitative rules live in memory/rounds/R421/plan.md):

For each run and field, Q1 = median of the first 25% of valid updates,
Q4 = median of the last 25%.  Failure-class flags:

- ``optimization_failure``: critic_loss Q4 > 3x Q1 (sustained growth).
- ``value_estimation_failure``: bellman_residual_mean Q4 > 1.25x Q1.
- ``policy_stagnation``: actor_grad_norm_mean Q4 < 0.5x Q1.
- ``exploration_collapse``: td_error_std Q4 < 0.5x Q1 OR
  sampled_state_variance_mean Q4 < 0.5x Q1.

The output records the ratios and flags, never an attribution.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "research_loop" / "r421_diagnostics"
READOUT = OUT / "diagnostic_readout.json"

ARMS = ("cd_matd3_no_message", "cd_matd3_message")
SEEDS = (401, 402, 403)

FIELDS = (
    "update_count",
    "critic_loss",
    "actor_loss_mean",
    "lagrange",
    "bellman_residual_mean",
    "bellman_residual_abs_max",
    "bellman_residual_std",
    "bellman_residual_q25",
    "bellman_residual_q50",
    "bellman_residual_q75",
    "critic_grad_norm_mean",
    "critic_grad_norm_max",
    "actor_grad_norm_mean",
    "actor_grad_norm_max",
    "td_error_std",
    "sampled_state_variance_mean",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_hashed(path: Path) -> dict:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed file: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new_json(path: Path, payload: dict) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _trend(values: np.ndarray) -> dict[str, float]:
    valid = values[np.isfinite(values)]
    if valid.size < 4:
        return {"q1": float("nan"), "q4": float("nan"), "n_valid": int(valid.size)}
    quarter = max(1, valid.size // 4)
    q1 = float(np.median(valid[:quarter]))
    q4 = float(np.median(valid[-quarter:]))
    return {"q1": q1, "q4": q4, "n_valid": int(valid.size)}


def _failure_flags(trends: dict[str, dict[str, float]]) -> dict[str, bool]:
    def ratio(name: str) -> float:
        t = trends[name]
        if t["n_valid"] < 4 or t["q1"] == 0.0 or not np.isfinite(t["q1"]) or not np.isfinite(t["q4"]):
            return float("nan")
        return t["q4"] / t["q1"]

    critic = ratio("critic_loss")
    residual = ratio("bellman_residual_mean")
    actor_grad = ratio("actor_grad_norm_mean")
    td_error = ratio("td_error_std")
    state_var = ratio("sampled_state_variance_mean")

    flags = {
        "optimization_failure": bool(np.isfinite(critic) and critic > 3.0),
        "value_estimation_failure": bool(np.isfinite(residual) and residual > 1.25),
        "policy_stagnation": bool(np.isfinite(actor_grad) and actor_grad < 0.5),
        "exploration_collapse": bool(
            (np.isfinite(td_error) and td_error < 0.5)
            or (np.isfinite(state_var) and state_var < 0.5)
        ),
    }
    flags["ratios"] = {
        "critic_loss_q4_over_q1": critic,
        "bellman_residual_mean_q4_over_q1": residual,
        "actor_grad_norm_mean_q4_over_q1": actor_grad,
        "td_error_std_q4_over_q1": td_error,
        "sampled_state_variance_mean_q4_over_q1": state_var,
    }
    return flags


def main() -> int:
    runs: dict[str, dict] = {}
    for arm_id in ARMS:
        for seed in SEEDS:
            key = f"{arm_id}|{seed}"
            run_dir = OUT / "train" / arm_id / f"seed{seed}"
            manifest = _read_hashed(run_dir / "manifest.json")
            csv_path = run_dir / "diagnostics.csv"
            csv_sha = _sha256_file(csv_path)
            if manifest.get("diagnostics_csv_sha256") != csv_sha:
                raise RuntimeError(f"csv drifted from manifest: {key}")
            raw = np.genfromtxt(csv_path, delimiter=",", names=True, encoding="utf-8")
            trends = {
                field: _trend(np.asarray(raw[field], dtype=float))
                for field in FIELDS
                if field in raw.dtype.names
            }
            flags = _failure_flags(trends)
            runs[key] = {
                "arm_id": arm_id,
                "training_seed": int(seed),
                "update_rows": int(raw.size),
                "csv_sha256": csv_sha,
                "manifest_sha256": _sha256_file(run_dir / "manifest.json"),
                "trends": trends,
                "failure_flags": flags,
            }
    anchor = _read_hashed(OUT / "formal_analysis.json")
    anchor_verdict = anchor.get("r410_anchor_verdict")
    payload = {
        "schema_version": 1,
        "round": "R421",
        "probe": "probes/r421_diagnostics_readout.py",
        "readout_rules": {
            "optimization_failure": "critic_loss Q4 > 3x Q1",
            "value_estimation_failure": "bellman_residual_mean Q4 > 1.25x Q1",
            "policy_stagnation": "actor_grad_norm_mean Q4 < 0.5x Q1",
            "exploration_collapse": (
                "td_error_std Q4 < 0.5x Q1 OR sampled_state_variance_mean Q4 < 0.5x Q1"
            ),
            "quartile_definition": "Q1/Q4 = median of first/last 25% of finite updates",
        },
        "runs": runs,
        "r410_anchor_verdict": anchor_verdict,
    }
    digest = _write_new_json(READOUT, payload)
    print("R421 diagnostic readout:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
