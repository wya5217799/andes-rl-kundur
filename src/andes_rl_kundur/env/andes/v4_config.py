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

    # ─── Action smoothing / anti-smoothing (R01 / R50 follow-up) ─────
    # r_smooth = -lambda_smooth × Σ((Δa - Δa_prev)/range)² added per step.
    #   0.0          : disabled (paper-faithful default)
    #   > 0.0        : PENALIZE action change (R01 smoothness probe)
    #   < 0.0        : REWARD action change (R50 anti-flatness, addresses
    #                  CLM-0057 temporal-flatness bottleneck)
    # The env-var ``LAMBDA_SMOOTH`` is the legacy entry point (still
    # honoured by ``base_env`` for back-compat); pinning via V4Config
    # is the recommended modern path.
    lambda_smooth: float = 0.0

    # ─── Windowed-horizon smoothness (R55 / CLM-0061 follow-up) ──────
    # The R50 anti-smoothness reward (lambda_smooth < 0) at window=1
    # was hijacked by exploration noise: per-step action change
    # variance was dominated by Gaussian exploration noise (sigma~0.1),
    # not by policy-driven systematic variation. Window > 1 switches
    # from per-step diff `(a[t] - a[t-1])²` to telescoping diff
    # `(a[t] - a[t-W])²`, which preserves policy drift signal across
    # W steps while leaving noise variance still bounded at 2σ².
    # Default 1 (per-step, original R01/R50 behaviour).
    smoothness_window: int = 1

    # ─── Observation augmentation (R03 / R49 probe) ──────────────────
    # When True, OBS_DIM += 2 and each agent's obs is appended with its
    # previous action ``(delta_M_prev, delta_D_prev)``. R49-α found this
    # NEGATIVE for V4 (-21% 6-axis vs baseline) — see CLM-0057. Field
    # exists for reproducibility / future ablations; default OFF.
    include_own_action_obs: bool = False

    # ─── Observation augmentation — time-in-obs (R52 probe) ──────────
    # When True, OBS_DIM += 1 and each agent's obs is appended with
    # normalized episode progress ``step_count / STEPS_PER_EPISODE``
    # in [0, 1]. Gives the deterministic-mode policy explicit phase
    # info so it can output time-varying action even at eval.
    # Addresses the structural temporal-flatness finding (CLM-0057/
    # CLM-0058/CLM-0059): deterministic policies on V4 converge to
    # static setpoint independent of algorithm/obs/reward shaping
    # because they lack trajectory-phase information.
    # Default OFF (paper-faithful). Mutually exclusive with
    # ``include_own_action_obs`` for the R52 minimal-diff slot layout.
    include_time_obs: bool = False

    # ─── R83 obs aug — area-mean freq (CLM-0057 follow-up alt) ────────
    # 当 True, OBS_DIM += 2, 每 agent obs 末加 (area1_mean_d_omega,
    # area2_mean_d_omega). paper Fig.3 area assignment: agent 0/1 (bus
    # 12/16) → area 1, agent 2/3 (bus 14/15) → area 2. 给 decentralized
    # agent 加 area-level coordination signal, 直接针对 CLM-0057
    # temporal-flatness + obs-blindness bottleneck. R52 时间维 / R49-α
    # own_action 维都试过但单独退化, area-mean freq 是第三个 obs aug
    # 候选. 跟 include_own_action_obs / include_time_obs 可并存
    # (R83 slot-layout refactor 后).
    include_area_mean_freq_obs: bool = False

    # ─── R58 audit-A escape hatches (paper-ambiguity resolution) ─────
    # Three paper-implementation choices that the paper text doesn't
    # nail down. Defaults preserve R30–R57 behaviour bit-identically.
    # Documented as paper-§13 ambiguities Q-A / Q-B + R58 audit A3:

    # A3: paper Eq.15-16 use "Δω" which physics convention reads as
    # rad/s. Paper Sec.IV-C eval explicitly uses Hz. Project default is
    # "hz" (matches eval + R30–R57). "rad_per_s" multiplies the internal
    # r^f scale by (2π·FN)² ≈ 39.5× — i.e., effective PHI_F is ~40×
    # stronger. Used by `paper_strict_pure_radsec()` classmethod to
    # test whether the R18 verdict's "PHI=1 diverges" conclusion holds
    # under paper-faithful radians interpretation.
    r_f_freq_units: Literal["hz", "rad_per_s"] = "hz"

    # A2: paper §1.1 / §13 Q-A leaves H_es,i dimensions unspecified.
    # "mechanical_H" (default) interprets paper H = M/2 (Eq.1 form
    # H·Δω̇ + D·Δω = Δu - ΔP, M = 2H mechanical convention).
    # "andes_M" interprets paper H = ANDES M directly (no /2 in r^h).
    # Effect: changes r^h magnitude by 4× (since (ΔM/2)² vs (ΔM)²).
    h_paper_interpretation: Literal["mechanical_H", "andes_M"] = "mechanical_H"

    # A5: paper §13 Q-B leaves "ΔH_avg / ΔD_avg" scope unspecified.
    # "global" (default) = mean over all N=4 ESS agents (consistent
    # with paper §0.5 "system total inertia ... basically unchanged").
    # "neighbor" = each agent uses its own + neighbors' mean.
    r_avg_scope: Literal["global", "neighbor"] = "global"

    def __post_init__(self) -> None:
        if self.action_penalty_mode not in ("physical", "normalized"):
            raise ValueError(
                f"action_penalty_mode must be 'physical' or 'normalized', "
                f"got {self.action_penalty_mode!r}"
            )
        # R83: 互斥已解除. base_env._build_obs + V4 env __init__ 改成绝对 slot
        # 索引 (own_action 占 7:9, time 占下一个), 支持 own_action + time 并存.
        # OBS_DIM 计算: base 7 + (own_action ? 2 : 0) + (time ? 1 : 0).
        pass
        if self.r_f_freq_units not in ("hz", "rad_per_s"):
            raise ValueError(
                f"r_f_freq_units must be 'hz' or 'rad_per_s', "
                f"got {self.r_f_freq_units!r}"
            )
        if self.h_paper_interpretation not in ("mechanical_H", "andes_M"):
            raise ValueError(
                f"h_paper_interpretation must be 'mechanical_H' or 'andes_M', "
                f"got {self.h_paper_interpretation!r}"
            )
        if self.r_avg_scope not in ("global", "neighbor"):
            raise ValueError(
                f"r_avg_scope must be 'global' or 'neighbor', "
                f"got {self.r_avg_scope!r}"
            )

    @classmethod
    def paper_faithful(cls) -> "V4Config":
        """Alias for the default config — explicit at the call site.

        NOTE (R58 / ADR-0002): "paper_faithful" is a historical name. The
        config it returns matches the paper on **topology, observation
        space, action space, and algorithm scaffolding** but adds a non-
        paper ``phi_abs=50`` reward term and rescales ``phi_h=phi_d=0.0056``
        (1/178 of paper Eq.14 nominal 1.0) for ANDES numerical stability.
        For exact paper Eq.14 weights, use :meth:`paper_strict_pure` or
        :meth:`paper_strict_rescaled`.
        """
        return cls()

    @classmethod
    def paper_strict_pure(cls) -> "V4Config":
        """R58 — paper Eq.14 nominal weights, no project deviations.

        Returns a config matching Yang et al., IEEE TPWRS 2023, Eq.14
        exactly on the reward weights: ``phi_f=100, phi_h=1, phi_d=1``
        and no ``phi_abs`` term. All other fields (physics, action
        range, smoothness, obs augmentation) match :meth:`paper_faithful`.

        Expected behaviour: R18 verdict mechanism predicts this config
        will diverge during training (``r_h/r_f ≈ 36000:1`` at standard
        SAC explore magnitude). R58 verifies this empirically.

        Used to answer: does the algorithm ranking under V4 depend on
        the R18 PHI rescale? See R58 verdict / ADR-0002.
        """
        return cls(phi_abs=0.0, phi_h=1.0, phi_d=1.0)

    @classmethod
    def paper_strict_rescaled(cls) -> "V4Config":
        """R58 — paper Eq.14 form (no ``phi_abs``) but keep R18 PHI rescale.

        Returns a config with ``phi_abs=0`` (removes the non-paper term)
        but retains ``phi_h=phi_d=0.0056`` (R18 1/178 rescale).

        Used to isolate the question: does the algorithm ranking under
        V4 depend on the non-paper ``phi_abs=50`` term, or on the
        R18 PHI rescale? Comparing this against :meth:`paper_strict_pure`
        (rescale removed) and :meth:`paper_faithful` (both deviations
        in play) discriminates the two effects.
        """
        return cls(phi_abs=0.0)

    @classmethod
    def paper_strict_pure_radsec(cls) -> "V4Config":
        """R58 audit-A3 — paper Eq.14 nominal + rad/s frequency units.

        Same as :meth:`paper_strict_pure` (PHI_ABS=0, PHI_H=PHI_D=1.0)
        but additionally interprets paper Eq.15-16 frequency deviation
        as rad/s rather than Hz. The (2π·FN)² ≈ 39.5× internal scaling
        on r^f is the "true paper-faithful" interpretation; the Hz
        choice is a project convention inherited from the eval formula.

        Why R58 audits this: R18 verdict measured r_h/r_f ≈ 3600:1 with
        PHI_H=1 + Hz r^f → concluded "PHI=1 diverges." Under rad/s r^f
        the ratio drops to ~91:1 → may be trainable. This config tests
        the hypothesis empirically.
        """
        return cls(phi_abs=0.0, phi_h=1.0, phi_d=1.0,
                   r_f_freq_units="rad_per_s")
