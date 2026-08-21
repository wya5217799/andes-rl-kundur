"""Signed-probe odd-response order analysis for R444 (geometric amplitude ladder).

Motivation
----------
The draft §3.4 refuses any order claim for the signed-pair odd response of
the implemented deterministic law ("quadratic or cubic") until a geometric
amplitude scaling test exists.  This probe implements that test exactly as
the theory audit C.7 prescribes: a geometric amplitude ladder
eps_k = eps_0 * 2^-k, the controller-to-controller response difference
delta(eps) = Y_law(eps) - Y_zero(eps), its antisymmetric part
delta_odd = (delta_+ - delta_-)/2 with a fixed dt-weighted L2 norm, a
log-log slope estimate p_hat, compensated quantities ||delta_odd||/eps^p,
mode-signature consistency, and a noise-floor rejection rule.

Pure functions only (Windows-safe): the WSL runner calls these from its
``classify`` command after reading the sealed records.

Usage (Windows or WSL)
----------------------
    python probes/r444_signed_probe_order.py <results-root> [--json]

Failure modes
-------------
Missing/incomplete records raise ValueError; noise-floor and mode-inconsistent
blocks are classified INCONCLUSIVE rather than raising, so a partially usable
ladder still yields an honest verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

SCALE_COUNT = 6          # k = 0..5
GEOMETRIC_BASE = 2.0
MIN_USABLE_SCALES = 5
NOISE_FLOOR_RELATIVE = 1.0e-3     # floor = max(smallest_norm * 1e-3, 1e-12)
NOISE_DROP_RATIO_MAX = 9.0        # per-halving drop beyond cubic (2^3=8) + slack
PLATEAU_SPREAD_MAX = 0.20         # compensated plateau relative spread bound
QUADRATIC_BAND = (1.5, 2.5)
CUBIC_BAND = (2.5, 3.5)
R2_MIN = 0.9

CONTROLLER_LAW = "law"
CONTROLLER_ZERO = "zero"
PAIR_KINDS = ("common", "differential", "localized")


def load_records(block_path: Path) -> dict[str, Any]:
    """Read one hashed profile JSON and index its six scenario records."""
    payload = json.loads(block_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError(f"profile block must contain six records: {block_path}")
    by_scenario: dict[str, Mapping[str, Any]] = {}
    for record in records:
        scenario_id = str(record.get("scenario_id", ""))
        if scenario_id in by_scenario:
            raise ValueError(f"duplicate scenario record: {scenario_id}")
        by_scenario[scenario_id] = record
    return by_scenario


def trajectory(record: Mapping[str, Any]) -> np.ndarray:
    """4 x T frequency-deviation trajectory (Hz), validating completeness."""
    steps = record.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("record has no steps")
    if record.get("completed") is not True or record.get("tds_failed") is not False:
        raise ValueError("record is incomplete or TDS-failed")
    rows = []
    for step in steps:
        frequencies = step.get("freq_hz_physical")
        if not isinstance(frequencies, list) or len(frequencies) != 4:
            raise ValueError("step frequency row must have four units")
        rows.append([float(value) for value in frequencies])
    return np.asarray(rows, dtype=float).T  # (4, T)


def pair_odd_norm(
    law_positive: Mapping[str, Any],
    law_negative: Mapping[str, Any],
    zero_positive: Mapping[str, Any],
    zero_negative: Mapping[str, Any],
    *,
    dt: float,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """C.7 delta decomposition with the fixed dt-weighted L2 norm.

    delta_+(eps) = Y_law(+eps) - Y_zero(+eps)
    delta_-(eps) = Y_law(-eps) - Y_zero(-eps)
    delta_odd    = (delta_+ - delta_-)/2     (antisymmetric part)
    delta_even   = (delta_+ + delta_-)/2     (symmetric part)

    Returns (odd_norm, even_norm, odd_array, even_array).  The norm is the
    same dt-weighted L2 across every amplitude; no epsilon normalization is
    applied here (compensated quantities are computed downstream).
    """
    y_lp = trajectory(law_positive)
    y_ln = trajectory(law_negative)
    y_zp = trajectory(zero_positive)
    y_zn = trajectory(zero_negative)
    if y_lp.shape != y_ln.shape or y_lp.shape != y_zp.shape or y_lp.shape != y_zn.shape:
        raise ValueError("paired trajectories must share shape")
    delta_plus = y_lp - y_zp
    delta_minus = y_ln - y_zn
    odd = 0.5 * (delta_plus - delta_minus)
    even = 0.5 * (delta_plus + delta_minus)
    norm = float(np.sqrt(float(np.sum(odd**2)) * dt))
    even_norm = float(np.sqrt(float(np.sum(even**2)) * dt))
    return norm, even_norm, odd, even


def mode_signature(record: Mapping[str, Any]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Per-step saturation / limiter signature derived from recorded rows.

    saturation flag: |action_norm| >= 1 - 1e-9 on either M or D channel
    limiter flag:    executed M or D at the decoder lower clamp
                     (m_lower_clamp=20 / d_lower_clamp=10 with 1e-6 tolerance)
    """
    saturation: list[int] = []
    limiter: list[int] = []
    for step in record.get("steps", []):
        action = step.get("action_norm")
        sat = 0
        if isinstance(action, list):
            for unit in action:
                if isinstance(unit, list) and len(unit) == 2:
                    if abs(float(unit[0])) >= 1.0 - 1e-9 or abs(float(unit[1])) >= 1.0 - 1e-9:
                        sat = 1
        saturation.append(sat)
        m_es = step.get("M_es")
        d_es = step.get("D_es")
        lim = 0
        if isinstance(m_es, list) and m_es:
            if min(float(value) for value in m_es) <= 20.0 + 1e-6:
                lim = 1
        if isinstance(d_es, list) and d_es:
            if min(float(value) for value in d_es) <= 10.0 + 1e-6:
                lim = 1
        limiter.append(lim)
    return tuple(saturation), tuple(limiter)


def noise_floor(norms: Sequence[float]) -> float:
    """Fixed noise-floor threshold across the whole ladder (per block)."""
    nonzero = [float(value) for value in norms if float(value) > 0.0]
    if not nonzero:
        return 1.0e-12
    return max(min(nonzero) * NOISE_FLOOR_RELATIVE, 1.0e-12)


def usable_mask(
    norms: Sequence[float],
    magnitudes: Sequence[float],
) -> tuple[list[bool], list[str]]:
    """Mark scales unusable from TDS/incompleteness, noise floor, or anomaly."""
    floor = noise_floor(norms)
    flags: list[bool] = []
    reasons: list[str] = []
    for index, norm in enumerate(norms):
        if norm <= floor:
            flags.append(False)
            reasons.append("noise-floor")
            continue
        flags.append(True)
        reasons.append("")
    # Anomalous drop: norm falls more than 9x per halving between two adjacent
    # usable scales (steeper than cubic) => mark the smaller one unusable.
    usable_index = [i for i, ok in enumerate(flags) if ok]
    for left, right in zip(usable_index, usable_index[1:]):
        if magnitudes[left] <= 0.0 or magnitudes[right] <= 0.0:
            continue
        ratio = norms[left] / max(norms[right], 1e-300)
        halvings = np.log2(float(magnitudes[left]) / float(magnitudes[right]))
        if halvings <= 0.0:
            continue
        per_halving = ratio ** (1.0 / halvings)
        if per_halving > NOISE_DROP_RATIO_MAX:
            flags[right] = False
            reasons[right] = "anomalous-drop"
    return flags, reasons


def loglog_fit(
    magnitudes: Sequence[float],
    norms: Sequence[float],
    usable: Sequence[bool],
) -> dict[str, Any]:
    """Ordinary least squares of ln norm on ln eps over usable scales."""
    xs: list[float] = []
    ys: list[float] = []
    for magnitude, norm, ok in zip(magnitudes, norms, usable):
        if not ok or magnitude <= 0.0 or norm <= 0.0:
            continue
        xs.append(float(np.log(magnitude)))
        ys.append(float(np.log(norm)))
    if len(xs) < 2:
        return {"p_hat": None, "r2": None, "n_points": len(xs)}
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    denom = float(np.sum((x - x_mean) ** 2))
    if denom <= 0.0:
        return {"p_hat": None, "r2": None, "n_points": len(xs)}
    slope = float(np.sum((x - x_mean) * (y - y_mean)) / denom)
    intercept = y_mean - slope * x_mean
    residuals = y - (slope * x + intercept)
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else float("nan")
    return {
        "p_hat": slope,
        "intercept": intercept,
        "r2": r2,
        "n_points": len(xs),
    }


def local_slopes(
    magnitudes: Sequence[float],
    norms: Sequence[float],
    usable: Sequence[bool],
) -> list[dict[str, Any]]:
    """Per-consecutive-scale order estimates (C.7 p_hat_k definition)."""
    slopes: list[dict[str, Any]] = []
    indices = [i for i, ok in enumerate(usable) if ok]
    for left, right in zip(indices, indices[1:]):
        log_eps = float(np.log(magnitudes[left]) - np.log(magnitudes[right]))
        log_norm = float(np.log(norms[left]) - np.log(norms[right]))
        slopes.append(
            {
                "from_scale": left,
                "to_scale": right,
                "p_hat_local": log_norm / log_eps if log_eps != 0.0 else None,
            }
        )
    return slopes


def compensated(
    magnitudes: Sequence[float],
    norms: Sequence[float],
    usable: Sequence[bool],
) -> dict[str, Any]:
    """||delta_odd|| / eps^p for p in {1,2,3} with plateau spread per p."""
    rows: dict[str, list[float]] = {"p1": [], "p2": [], "p3": []}
    for magnitude, norm, ok in zip(magnitudes, norms, usable):
        if not ok or magnitude <= 0.0:
            continue
        rows["p1"].append(norm / magnitude)
        rows["p2"].append(norm / magnitude**2)
        rows["p3"].append(norm / magnitude**3)
    plateaus: dict[str, Any] = {}
    for key, values in rows.items():
        if not values:
            plateaus[key] = {"plateau": False, "relative_spread": None}
            continue
        median = float(np.median(values))
        if median <= 0.0:
            plateaus[key] = {"plateau": False, "relative_spread": float("inf")}
            continue
        spread = (max(values) - min(values)) / median
        plateaus[key] = {
            "plateau": spread <= PLATEAU_SPREAD_MAX,
            "relative_spread": spread,
            "values": values,
        }
    return plateaus


def classify_block(
    law_by_scale: Sequence[Mapping[str, Mapping[str, Any]]],
    zero_by_scale: Sequence[Mapping[str, Mapping[str, Any]]],
    *,
    profile_id: str,
    pair_kind: str,
    magnitudes: Sequence[float],
    dt: float,
) -> dict[str, Any]:
    """Full C.7 analysis for one (profile, pair_kind) block.

    ``law_by_scale`` / ``zero_by_scale`` are sequences of length
    SCALE_COUNT; element k maps scenario_id -> record for scale k.
    """
    if len(law_by_scale) != SCALE_COUNT or len(zero_by_scale) != SCALE_COUNT:
        raise ValueError("per-scale record maps must have SCALE_COUNT entries")
    odd_norms: list[float] = []
    even_norms: list[float] = []
    odd_arrays: list[np.ndarray] = []
    even_arrays: list[np.ndarray] = []
    for k in range(SCALE_COUNT):
        positive_id = f"{profile_id}_{pair_kind}_positive"
        negative_id = f"{profile_id}_{pair_kind}_negative"
        try:
            odd_norm, even_norm, odd, even = pair_odd_norm(
                law_by_scale[k][positive_id],
                law_by_scale[k][negative_id],
                zero_by_scale[k][positive_id],
                zero_by_scale[k][negative_id],
                dt=dt,
            )
        except KeyError as exc:
            raise ValueError(
                f"missing scenario record for {profile_id}/{pair_kind}/k{k}"
            ) from exc
        odd_norms.append(odd_norm)
        even_norms.append(even_norm)
        odd_arrays.append(odd)
        even_arrays.append(even)
    usable, reasons = usable_mask(odd_norms, magnitudes)
    fit = loglog_fit(magnitudes, odd_norms, usable)
    slopes = local_slopes(magnitudes, odd_norms, usable)
    comp = compensated(magnitudes, odd_norms, usable)

    usable_count = int(sum(usable))
    p_hat = fit.get("p_hat")
    r2 = fit.get("r2")
    classification: str
    reject_reason: str | None = None
    if usable_count < MIN_USABLE_SCALES:
        classification = "INCONCLUSIVE"
        reject_reason = f"usable-scales={usable_count}<{MIN_USABLE_SCALES}"
    elif p_hat is None or r2 is None or r2 < R2_MIN:
        classification = "INCONCLUSIVE"
        reject_reason = f"fit-unreliable r2={r2}"
    elif QUADRATIC_BAND[0] <= p_hat <= QUADRATIC_BAND[1]:
        classification = "QUADRATIC"
    elif CUBIC_BAND[0] <= p_hat <= CUBIC_BAND[1]:
        classification = "CUBIC"
    else:
        classification = "INCONCLUSIVE"
        reject_reason = f"p_hat={p_hat:.3f} outside both bands"

    # mode-signature consistency across the usable ladder
    law_sigs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    zero_sigs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for k in range(SCALE_COUNT):
        if not usable[k]:
            continue
        positive_id = f"{profile_id}_{pair_kind}_positive"
        negative_id = f"{profile_id}_{pair_kind}_negative"
        law_sigs.append(mode_signature(law_by_scale[k][positive_id]))
        law_sigs.append(mode_signature(law_by_scale[k][negative_id]))
        zero_sigs.append(mode_signature(zero_by_scale[k][positive_id]))
        zero_sigs.append(mode_signature(zero_by_scale[k][negative_id]))
    law_consistent = len(set(law_sigs)) == 1 if law_sigs else True
    zero_consistent = len(set(zero_sigs)) == 1 if zero_sigs else True
    mode_ok = law_consistent and zero_consistent
    if classification != "INCONCLUSIVE" and not mode_ok:
        classification = "INCONCLUSIVE"
        reject_reason = "mode-signature-inconsistent"

    return {
        "profile_id": profile_id,
        "pair_kind": pair_kind,
        "magnitudes": [float(value) for value in magnitudes],
        "delta_odd_norms": odd_norms,
        "delta_even_norms": even_norms,
        "usable": usable,
        "reasons": reasons,
        "usable_count": usable_count,
        "loglog": fit,
        "local_slopes": slopes,
        "compensated": comp,
        "mode_consistency": {
            "law": law_consistent,
            "zero": zero_consistent,
            "overall": mode_ok,
        },
        "classification": classification,
        "reject_reason": reject_reason,
    }


def summarize(blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate block classifications into the pre-registered manuscript branch."""
    counts: dict[str, int] = {}
    for block in blocks:
        classification = str(block.get("classification", "INCONCLUSIVE"))
        counts[classification] = counts.get(classification, 0) + 1
    total = len(blocks)
    quadratic = counts.get("QUADRATIC", 0)
    cubic = counts.get("CUBIC", 0)
    inconclusive = counts.get("INCONCLUSIVE", 0)
    if total and quadratic == total:
        manuscript_branch = "QUADRATIC-CONSISTENT"
    elif total and cubic == total:
        manuscript_branch = "CUBIC-CONSISTENT"
    elif quadratic + cubic > inconclusive and quadratic >= cubic:
        manuscript_branch = "QUADRATIC-MAJORITY"
    elif quadratic + cubic > inconclusive and cubic > quadratic:
        manuscript_branch = "CUBIC-MAJORITY"
    else:
        manuscript_branch = "INCONCLUSIVE-DOMINANT"
    return {
        "counts": counts,
        "total_blocks": total,
        "manuscript_branch": manuscript_branch,
    }


def run_analysis(results_root: Path, *, dt: float) -> dict[str, Any]:
    """Analyse the sealed R444 record tree into the formal order table."""
    blocks: list[dict[str, Any]] = []
    eval_root = results_root / "eval"
    for controller in (CONTROLLER_LAW, CONTROLLER_ZERO):
        for k in range(SCALE_COUNT):
            key = f"k{k}"
            folder = eval_root / controller / key
            if not folder.is_dir():
                raise ValueError(f"missing controller scale folder: {folder}")
    profiles = sorted(
        {
            path.stem
            for path in (eval_root / CONTROLLER_LAW / "k0").glob("*.json")
            if path.name != "*.sha256"
        }
    )
    for profile_id in profiles:
        for pair_kind in PAIR_KINDS:
            law_by_scale: list[dict[str, Mapping[str, Any]]] = []
            zero_by_scale: list[dict[str, Mapping[str, Any]]] = []
            magnitudes: list[float] = []
            for k in range(SCALE_COUNT):
                key = f"k{k}"
                law_block = eval_root / CONTROLLER_LAW / key / f"{profile_id}.json"
                zero_block = eval_root / CONTROLLER_ZERO / key / f"{profile_id}.json"
                law_by_scale.append(load_records(law_block))
                zero_by_scale.append(load_records(zero_block))
                positive_id = f"{profile_id}_{pair_kind}_positive"
                magnitudes.append(float(law_by_scale[k][positive_id]["magnitude"]))
            blocks.append(
                classify_block(
                    law_by_scale,
                    zero_by_scale,
                    profile_id=profile_id,
                    pair_kind=pair_kind,
                    magnitudes=magnitudes,
                    dt=dt,
                )
            )
    blocks.sort(key=lambda block: (block["profile_id"], block["pair_kind"]))
    summary = summarize(blocks)
    return {
        "schema_version": 1,
        "block_count": len(blocks),
        "blocks": blocks,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    analysis = run_analysis(args.results_root, dt=args.dt)
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        summary = analysis["summary"]
        print(f"blocks={analysis['block_count']} {summary}")
        for block in analysis["blocks"]:
            fit = block["loglog"]
            print(
                f"  {block['profile_id']}/{block['pair_kind']}: "
                f"{block['classification']} "
                f"usable={block['usable_count']} p_hat={fit.get('p_hat')} "
                f"r2={fit.get('r2')} reason={block.get('reject_reason')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
