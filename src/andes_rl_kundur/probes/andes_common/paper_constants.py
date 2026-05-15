"""Paper-spec constants for ANDES Kundur 4-VSG probes.

Single source of truth for paper Yang et al. TPWRS 2023 numbers used across
R10-R17 forensic probes. Whenever a probe needs paper LS1/LS2 magnitudes or
Fig.6/8 benchmark numbers, import from here, do NOT redefine.

References:
- LS1/LS2 magnitudes:    paper Sec.IV-C "load step 1 ... 248 MW at bus 14"
                         "load step 2 ... 188 MW at bus 15"
- Fig.6/8 benchmarks:    paper Fig.6 (no-ctrl LS1) / Fig.8 (no-ctrl LS2)
- Eq.12 action box:      paper Sec.IV-B "ΔH ∈ [-100, +300], ΔD ∈ [-200, +600]"
- Kundur sync gen H:     Kundur "Power System Stability and Control" 1994
                         Area 1: H₁=H₂=6.5 s @ 900 MVA machine base
                         Area 2: H₃=H₄=6.175 s @ 900 MVA machine base

Per scenarios/kundur/NOTES_ANDES.md:
  Probe 量化前必从此 import. 否则数字漂移 → cross-probe verdict 不可比.
"""
from __future__ import annotations

from dataclasses import dataclass


# ─── Disturbance protocols ───────────────────────────────────────────────

LS1_DELTA_U = {"PQ_Bus14": -2.48}   # 248 MW load reduction at Bus 14
LS2_DELTA_U = {"PQ_Bus15": +1.88}   # 188 MW load increase at Bus 15

LS1_NAME = "load_step_1"
LS2_NAME = "load_step_2"

SCENARIOS = {
    LS1_NAME: LS1_DELTA_U,
    LS2_NAME: LS2_DELTA_U,
}


# ─── Paper Fig.6/8 benchmarks (no-control baseline, 6s window) ───────────

@dataclass(frozen=True)
class PaperBenchmark:
    """Paper Fig.6/8 ground truth for one LS scenario, no-control baseline.

    All Δf values are |Δf| magnitudes (sign-agnostic per paper convention).
    """
    scenario: str
    max_abs_df_Hz: float          # peak |Δf| during 6s window
    final_abs_df_Hz: float        # |Δf| at t=6s (settled with droop)
    settling_to_residual_s: float # time to enter ±0.02 Hz of final


PAPER_FIG6 = PaperBenchmark(
    scenario=LS1_NAME,
    max_abs_df_Hz=0.13,
    final_abs_df_Hz=0.08,
    settling_to_residual_s=3.0,
)

PAPER_FIG8 = PaperBenchmark(
    scenario=LS2_NAME,
    max_abs_df_Hz=0.10,
    final_abs_df_Hz=0.05,
    settling_to_residual_s=2.5,
)

PAPER_BENCHMARKS = {
    LS1_NAME: PAPER_FIG6,
    LS2_NAME: PAPER_FIG8,
}


# ─── Paper Eq.12 action constraints (Sec.IV-B) ───────────────────────────

EQ12_DH_RANGE = (-100.0, +300.0)   # ΔH per-step action bounds
EQ12_DD_RANGE = (-200.0, +600.0)   # ΔD per-step action bounds


# ─── Paper Kundur sync gen baseline (machine base 900 MVA each) ──────────

KUNDUR_AREA1_H = 6.5      # G1, G2 (s, machine base)
KUNDUR_AREA2_H = 6.175    # G3, G4 (s, machine base)
KUNDUR_GENROU_M_SYS_BASE = (117.0, 117.0, 111.15, 111.15)  # ANDES 100MVA base
KUNDUR_TOTAL_GEN_MVA = 3600.0


# ─── Probe defaults (R10-R17 conventions) ────────────────────────────────

DEFAULT_PROBE_STEPS_SHORT = 30   # 6s @ DT=0.2 (paper Fig.6 window)
DEFAULT_PROBE_STEPS_LONG = 150   # 30s for settling-axis verification
DEFAULT_PROBE_SEED = 42
PAPER_DT = 0.2                   # paper Sec.IV-A "control 0.2s / episode 10s"
PAPER_T_EPISODE = 10.0


# ─── Common H_FORCED test points ─────────────────────────────────────────

H_TEST_POINTS = (6.175, 6.5, 30.0, 100.0, 300.0)
H_PAPER_AREA1 = 6.5
H_PAPER_AREA2 = 6.175
H_EQ12_BOX_MIDDLE = 100.0   # Eq.12 [10, 300] middle, V4 default H₀
H_EQ12_BOX_UPPER = 300.0    # Eq.12 upper bound


__all__ = [
    "LS1_DELTA_U", "LS2_DELTA_U", "LS1_NAME", "LS2_NAME", "SCENARIOS",
    "PaperBenchmark", "PAPER_FIG6", "PAPER_FIG8", "PAPER_BENCHMARKS",
    "EQ12_DH_RANGE", "EQ12_DD_RANGE",
    "KUNDUR_AREA1_H", "KUNDUR_AREA2_H", "KUNDUR_GENROU_M_SYS_BASE",
    "KUNDUR_TOTAL_GEN_MVA",
    "DEFAULT_PROBE_STEPS_SHORT", "DEFAULT_PROBE_STEPS_LONG",
    "DEFAULT_PROBE_SEED", "PAPER_DT", "PAPER_T_EPISODE",
    "H_TEST_POINTS", "H_PAPER_AREA1", "H_PAPER_AREA2",
    "H_EQ12_BOX_MIDDLE", "H_EQ12_BOX_UPPER",
]
