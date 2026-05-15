"""Explicit per-instance configuration for ``AndesMultiVSGEnvV4``.

Pre-2026-05-17 the env read its 12 tunable physics + reward parameters
from class attributes that scripts/train.py monkey-patched at runtime.
That pattern was the root cause of CLM-0040 (silent G4 inertia
inheritance from V2 into V4): class-attr overrides hide silently when
nobody looks. ``V4Config`` makes every tunable an explicit field;
the env reads from ``self.config`` only.

Defaults equal the paper-faithful baseline that produced the published
headlines (R21 0.444, HAWE 0.439, no-control 0.104).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class V4Config:
    """Per-instance V4 env configuration. Defaults are paper-faithful."""

    # ─── Physics (paper Eq.12 / Sec.IV-B) ────────────────────────────
    # H₀ = 100 s (middle of paper Eq.12 box [10, 300]) ⇒ M₀ = 2H₀ = 200
    vsg_m0: float = 200.0
    vsg_d0: float = 100.0
    # Per-agent D₀ vector — V4 uses uniform 100; V2 used hetero [20,16,4,8]
    d0_per_agent: tuple[float, ...] = (100.0, 100.0, 100.0, 100.0)
    # Action ranges (paper Sec.IV-B): ΔM=[-200,600], ΔD=[-200,600]
    dm_min: float = -200.0
    dm_max: float = 600.0
    dd_min: float = -200.0
    dd_max: float = 600.0
    # Eq.12 lower physical clamps
    m_min_physical: float = 20.0
    d_min_physical: float = 10.0

    # ─── Reward weights (paper Eq.14 + R18 effective rescale) ────────
    phi_f: float = 100.0    # paper Eq.14 nominal
    phi_h: float = 0.0056   # = 1/178 R18 rescale (paper nominal was 1.0)
    phi_d: float = 0.0056   # same rationale
    phi_abs: float = 50.0   # Kundur tight-coupling patch (not in paper Eq.14)
    phi_max: float = 0.0    # R31 shaping default OFF
    phi_settle: float = 0.0 # R33 shaping default OFF

    # ─── G4 inertia toggle ───────────────────────────────────────────
    # True preserves paper headline numbers (R37 / CLM-0040). Setting
    # False asks for the paper-faithful Kundur 4-SG baseline — that
    # requires re-running training to validate.
    zero_g4_inertia: bool = True

    # ─── Reward shape (R41 / CLM-0044 follow-up) ─────────────────────
    # "physical"  = r_h = -(mean(ΔM)/2)² × PHI_H, r_d = -(mean(ΔD))² × PHI_D
    #               (paper-faithful, bit-identical default; produces the
    #               action-cost dominance documented in CLM-0043)
    # "normalized" = r_h = -(mean(a_M))² × PHI_H, r_d = -(mean(a_D))² × PHI_D
    #               (a ∈ [-1, 1] is the normalized action passed to step();
    #               action-cost stays O(1) regardless of action range)
    action_penalty_mode: Literal["physical", "normalized"] = "physical"

    def __post_init__(self) -> None:
        if self.action_penalty_mode not in ("physical", "normalized"):
            raise ValueError(
                f"action_penalty_mode must be 'physical' or 'normalized', "
                f"got {self.action_penalty_mode!r}"
            )

    @classmethod
    def paper_faithful(cls) -> "V4Config":
        """Alias for the default config — explicit at the call site."""
        return cls()
