"""R437 spectral diagnosis of the a4_md_relaxed failure block (offline only).

Motivation: R415/CLM-1230 records a4_md_relaxed (inertia x0.85, damping
x1.15) failing the frozen r_d <= 0.95 endpoint (0.9712) while all guards
pass, with no mechanism explanation.  This probe reads the sealed R415
records read-only and tests the pre-registered hypothesis that the frozen
0.4 Hz ring-edge bandpass channel is detuned from the block's dominant
differential mode (channel-mode mismatch), against the passing blocks
a4_md_stiff and a4_conditions_b.

Usage (no ANDES, no WSL):

    python probes/r437_relaxed_spectral.py [--out results/research_loop/r437_relaxed_spectral]

Failure modes: missing sealed inputs (hard error), all-NaN traces (record
marked invalid, never crashes), Welch resolution limits (reported in the
payload's resolution_notes, not fatal).

Output: hashed JSON + .sha256 sidecar under the result root; never writes
into any sealed R415 artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEALED_ROOT = ROOT / "results/research_loop/r415_energy_port_extra_banks"
BLOCKS = ("a4_md_relaxed", "a4_md_stiff", "a4_conditions_b")
BANDS = {
    "window_0p3_0p5": (0.30, 0.50),
    "passband_0p2_0p6": (0.20, 0.60),
    "out_of_window": (0.10, 2.50),
}
FREQ_LIMITS = (0.10, 2.50)
FS_HZ = 5.0  # dt = 0.2 s
DIFFERENTIAL_ROWS = np.asarray(
    [
        [1.0, 1.0, -1.0, -1.0],  # inter-area
        [1.0, -1.0, 0.0, 0.0],  # local area 1
        [0.0, 0.0, 1.0, -1.0],  # local area 2
    ],
    dtype=float,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_block(block_id: str) -> list[dict]:
    path = SEALED_ROOT / block_id / "records.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload["records"]
    if payload.get("block_id") != block_id:
        raise ValueError(f"sealed block id mismatch: {block_id}")
    return records


def _band_energy(psd: np.ndarray, freqs: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    return float(np.sum(psd[mask]))


def _trajectory_psd(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Detrended periodogram (full-length FFT with zero padding to 256)."""
    series = np.asarray(values, dtype=float)
    series = series - np.mean(series)
    n = max(len(series), 1)
    nfft = 256
    spectrum = np.abs(np.fft.rfft(series, n=nfft)) ** 2.0
    freqs = np.fft.rfftfreq(nfft, d=1.0 / FS_HZ)
    return spectrum, freqs


def analyze_record(record: dict) -> dict:
    """One record: differential PSD, peak frequency, band energy fractions."""
    steps = record["steps"]
    freq_matrix = np.asarray(
        [[float(step["freq_hz_physical"][agent]) for agent in range(4)] for step in steps],
        dtype=float,
    )
    if freq_matrix.shape[0] < 16:
        return {
            "record_too_short": True,
            "completed_steps": int(freq_matrix.shape[0]),
        }
    differential = freq_matrix @ DIFFERENTIAL_ROWS.T  # (T, 3)
    total_psd = np.zeros(129, dtype=float)
    per_coord_psd = []
    for column in range(differential.shape[1]):
        psd, freqs = _trajectory_psd(differential[:, column])
        total_psd += psd
        per_coord_psd.append(psd.tolist())
    band_mask = (freqs >= FREQ_LIMITS[0]) & (freqs <= FREQ_LIMITS[1])
    band_total = float(np.sum(total_psd[band_mask]))
    total_energy = float(np.sum(total_psd))
    in_band = np.argmax(total_psd[band_mask])
    peak_freq = float(freqs[band_mask][in_band])
    peak_psd = float(total_psd[band_mask][in_band])
    band_fractions = {
        name: (
            _band_energy(total_psd, freqs, band) / band_total
            if band_total > 1e-12
            else float("nan")
        )
        for name, band in BANDS.items()
    }
    return {
        "record_too_short": False,
        "completed_steps": int(freq_matrix.shape[0]),
        "peak_freq_hz": peak_freq,
        "peak_psd": peak_psd,
        "window_fraction_0p3_0p5": band_fractions["window_0p3_0p5"],
        "passband_fraction_0p2_0p6": band_fractions["passband_0p2_0p6"],
        "out_of_window_fraction": band_fractions["out_of_window"],
        "differential_energy_total": total_energy,
        "differential_energy_in_band": band_total,
        "per_coord_psd": per_coord_psd,
    }


def summarize(records: list[dict]) -> dict:
    per_arm: dict[str, list[dict]] = {}
    for record in records:
        arm = str(record["arm_id"])
        per_arm.setdefault(arm, []).append(record)
    summary: dict[str, dict] = {}
    for arm, arm_records in sorted(per_arm.items()):
        analyses = [analyze_record(record) for record in arm_records]
        valid = [a for a in analyses if not a.get("record_too_short")]
        if not valid:
            summary[arm] = {"valid_records": 0, "records": len(arm_records)}
            continue
        summary[arm] = {
            "valid_records": len(valid),
            "records": len(arm_records),
            "median_peak_freq_hz": float(np.median([a["peak_freq_hz"] for a in valid])),
            "median_window_fraction": float(
                np.median([a["window_fraction_0p3_0p5"] for a in valid])
            ),
            "median_passband_fraction": float(
                np.median([a["passband_fraction_0p2_0p6"] for a in valid])
            ),
            "median_out_of_window_fraction": float(
                np.median([a["out_of_window_fraction"] for a in valid])
            ),
            "median_peak_psd": float(np.median([a["peak_psd"] for a in valid])),
        }
    return summary


def classify(summaries: dict[str, dict]) -> dict:
    def _arm(block: str, arm: str) -> dict:
        return summaries.get(block, {}).get(arm, {})

    relaxed_band = _arm("a4_md_relaxed", "bandpass_k3p5")
    stiff_band = _arm("a4_md_stiff", "bandpass_k3p5")
    condb_band = _arm("a4_conditions_b", "bandpass_k3p5")
    relaxed_local = _arm("a4_md_relaxed", "local_feasibility_native")
    check = {
        "relaxed_band_valid": bool(relaxed_band.get("valid_records", 0) > 0),
        "stiff_band_valid": bool(stiff_band.get("valid_records", 0) > 0),
        "condb_band_valid": bool(condb_band.get("valid_records", 0) > 0),
        "relaxed_local_valid": bool(relaxed_local.get("valid_records", 0) > 0),
    }
    if not all(check.values()):
        return {
            "verdict": "UNDECIDABLE",
            "reason": "missing valid records for a required arm",
            "checks": check,
        }
    relaxed_peak = float(relaxed_band.get("median_peak_freq_hz", np.nan))
    relaxed_window = float(relaxed_band.get("median_window_fraction", np.nan))
    passing_peaks = [
        float(stiff_band.get("median_peak_freq_hz", np.nan)),
        float(condb_band.get("median_peak_freq_hz", np.nan)),
    ]
    passing_windows = [
        float(stiff_band.get("median_window_fraction", np.nan)),
        float(condb_band.get("median_window_fraction", np.nan)),
    ]
    mismatched = bool(
        (relaxed_peak < 0.25 or relaxed_peak > 0.55)
        and (relaxed_window < 0.5)
    )
    passing_in_window = [w >= 0.5 for w in passing_windows if np.isfinite(w)]
    if mismatched and any(passing_in_window):
        verdict = "SUPPORTED"
        reason = (
            "relaxed block peak outside 0.25-0.55 Hz with <50% window energy "
            "while >=1 passing block peaks inside the window"
        )
    elif not mismatched and all(passing_in_window):
        verdict = "REFUTED"
        reason = (
            "relaxed block spectrum stays inside the 0.4 Hz window like the "
            "passing blocks; no channel-mode mismatch detected"
        )
    else:
        verdict = "UNDECIDABLE"
        reason = "spectral patterns do not separate the blocks as pre-registered"
    return {
        "verdict": verdict,
        "reason": reason,
        "relaxed_peak_freq_hz": relaxed_peak,
        "relaxed_window_fraction": relaxed_window,
        "passing_peaks_hz": passing_peaks,
        "passing_window_fractions": passing_windows,
        "checks": check,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results/research_loop/r437_relaxed_spectral",
    )
    args = parser.parse_args()
    out_root = args.out
    if out_root.exists() or Path(f"{out_root}.sha256").exists():
        raise FileExistsError(f"result root already exists: {out_root}")

    per_block: dict[str, dict] = {}
    for block in BLOCKS:
        records = _load_block(block)
        per_block[block] = summarize(records)
    decision = classify(per_block)
    payload = {
        "schema_version": 1,
        "round": "R437",
        "inputs": {
            block: str((SEALED_ROOT / block / "records.json").resolve())
            for block in BLOCKS
        },
        "input_shas": {
            block: sha256_file(SEALED_ROOT / block / "records.json") for block in BLOCKS
        },
        "fs_hz": FS_HZ,
        "differential_rows": DIFFERENTIAL_ROWS.tolist(),
        "resolution_notes": [
            "periodogram on detrended 50-step traces, zero-padded FFT to 256 "
            "bins at fs=5 Hz -> ~0.02 Hz bins; effective resolution ~0.1 Hz",
        ],
        "per_block": per_block,
        "classification": decision,
    }
    out_root.mkdir(parents=True, exist_ok=False)
    target = out_root / "formal_analysis.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(target)
    Path(f"{target}.sha256").write_text(f"{digest}\n", encoding="utf-8")
    print(json.dumps(decision, indent=2, sort_keys=True))
    print(f"payload sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
