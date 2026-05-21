"""ANDES Kundur 4-VSG environment, V4 paper-faithful baseline.

V4 consolidates all the fixes found between R10 and R16 forensic audits.
This module is the only env in active use; V1/V2/V3 ancestors are kept
in ``_legacy/env/andes/`` for historical reference.

Topology (Yang et al., IEEE TPWRS 2023, Fig. 3 extended):
- Kundur two-area system with 4 GENROU (G1..G4) — all four retain inertia.
- 4 VSG storage units (GENCLS) added on new buses Bus12, Bus14, Bus15, Bus16,
  connected to existing buses via tie lines.
- 100 MW wind-farm proxy on Bus 8 (low-inertia GENCLS, M=0.1).
- IEEEG1 governor + EXST1 AVR on every GENROU, added BEFORE ``ss.setup()``
  so they participate in the DAE (R10 forensic fix — R03/R04 added them
  after ``setup()`` and they were silently DAE-inactive).

V4 specifics:
- VSG_M0 = 200 (H₀ = 100 s), middle of paper Eq.12 box [10, 300].
- VSG_D0 = 100 across all four agents (paper Eq.12 same box).
- Action ranges paper-faithful: ΔM ∈ [-200, 600], ΔD ∈ [-200, 600] (Sec.IV-B).
- φ_h, φ_d rescaled to 0.0056 — paper Eq.14 nominal is 1.0 but the
  paper's implicit narrow ΔH/ΔD ranges (V2 baseline) hide a 178× quadratic
  scaling factor. Without rescale, r_d/r_f ≈ 36000:1 at SAC explore and
  training diverges (R18 verdict).
- M_MIN/D_MIN physical clamps = paper Eq.12 lower bounds (20 / 10).
- ZERO_G4_INERTIA = True (silent V2 inheritance; see attribute comment).
  Pre-2026-05-16 V4 docstrings claimed G4 was preserved, but the inheritance
  chain made this False/True flip invisible. The actual paper numbers
  (R21 0.444 etc.) were computed with G4 zeroed.

V1/V2 actor checkpoints are NOT compatible with V4 (M0 changes by 6.7×,
action range expands 17×). Fresh training required for any V4 SAC run.

For deeper forensic context:
- memory/rounds/R10/verdict.md (governor wiring forensic)
- memory/rounds/R15/verdict.md (G4 inertia restoration)
- memory/rounds/R18/verdict.md (PHI rescale rationale)
- scenarios/kundur/NOTES_ANDES.md (current engineering notes)
"""
from __future__ import annotations

import os
import warnings
from collections import deque

import andes
import numpy as np

from andes_rl_kundur.env.andes.base_env import AndesBaseEnv
from andes_rl_kundur.env.andes.v4_config import V4Config
from andes_rl_kundur.scenarios.contract import KUNDUR as _CONTRACT

warnings.filterwarnings("ignore")


class AndesMultiVSGEnvV4(AndesBaseEnv):
    """ANDES Kundur 4-VSG environment, paper-faithful baseline.

    Self-contained: does not inherit from V1/V2/V3. All class attributes
    and overridden methods are visible in this file alone.
    """

    # ─── Topology ─────────────────────────────────────────────────────
    N_AGENTS = _CONTRACT.n_agents

    # G4 inertia toggle. The pre-2026-05-16 inheritance chain silently
    # inherited V2's ``ZERO_G4_INERTIA = True`` (V2 modeled G4 as a wind
    # farm) into V4, contradicting V4's own docstring claim that "G4
    # inertia is preserved." All paper results (R21 0.444, HAWE 0.439,
    # no-control 0.104) were computed with G4 zeroed. We pin True here
    # to preserve bit-identical reproducibility of those numbers.
    #
    # R37 (2026-05-16) records this discrepancy as CLM-0040. Future
    # research that wants the paper-faithful Kundur 4 SG baseline
    # (R15 forensic finding: G4 preservation drops max_df 26%) should
    # explicitly flip this to False in a subclass and re-train.
    ZERO_G4_INERTIA: bool = True

    # VSG attachment buses (Fig.3 extended topology)
    VSG_BUSES: list[int] = [12, 16, 14, 15]

    # New bus → parent bus for tie lines
    NEW_BUS_CONNECTIONS: dict[int, int] = {
        12: 7,   # ES1: Bus12 → Bus7
        16: 8,   # ES2: Bus16 → Bus8
        14: 10,  # ES3: Bus14 → Bus10
        15: 9,   # ES4: Bus15 → Bus9
    }

    # 100 MW wind-farm proxy on Bus 8 (low-inertia GENCLS)
    WF2_BUS: int = 8
    WF2_SN: float = 100.0   # MVA
    WF2_P0: float = 1.0     # p.u. on WF2_SN base

    NEW_BUS_VN: float = 230.0   # kV (matches Kundur base)

    # Disturbance load points (steady-state loads injected at Bus14 / Bus15
    # before any test perturbation).
    NEW_LOADS: dict[int, dict[str, float]] = {
        14: {"p0": 2.48, "q0": 0.0},
        15: {"p0": 0.0,  "q0": 0.0},
    }

    # 4-node ring communication topology
    COMM_ADJ: dict[int, list[int]] = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}

    # Disturbance magnitude (p.u. on 100 MVA base) for random_disturbance=True
    DIST_MIN: float = 0.5
    DIST_MAX: float = 2.0

    # ─── Baseline VSG dynamics (paper Eq.12 box middle) ───────────────
    # 2H = M; H₀ = 100 s gives settled_df ≈ paper 0.13 (R14 30s trace).
    VSG_M0: float = 200.0
    VSG_D0: float = 100.0

    # Paper Eq.12 same box for D₀. Uniform across agents (V2's hetero
    # [20,16,4,8] was a paper-deviation sweep, not paper convention).
    D0_HETEROGENEOUS: np.ndarray = np.array([100.0, 100.0, 100.0, 100.0])

    # ─── Action range (paper Sec.IV-B) ────────────────────────────────
    # ΔH ∈ [-100, +300] → ΔM = 2 × ΔH ∈ [-200, +600]
    # ΔD ∈ [-200, +600]
    DM_MIN: float = -200.0
    DM_MAX: float = 600.0
    DD_MIN: float = -200.0
    DD_MAX: float = 600.0

    # Paper Eq.12 lower physical bounds (M ≥ 20, D ≥ 10)
    M_MIN_PHYSICAL: float = 20.0
    D_MIN_PHYSICAL: float = 10.0

    # ─── Network tie-line parameters (V2 sweep verdict) ───────────────
    # NEW_LINE_X = 0.20 is the V2 sweep sweet spot (0.10 / 0.20 / 0.30 / 0.40 /
    # 0.60 → 0.60 power flow diverges). R/B keep V2 calibration.
    NEW_LINE_R: float = 0.002
    NEW_LINE_X: float = 0.20
    NEW_LINE_B: float = 0.0175

    # ─── Reward weights (R18 paper-effective rescale) ─────────────────
    # PHI_F = 100 inherited from base_env (action-range-independent term).
    PHI_H: float = 0.0056   # paper Eq.14 nominal 1.0; rescale = 1/178
    PHI_D: float = 0.0056   # same rationale
    # PHI_ABS = 50 inherited from base_env (Kundur tight-coupling patch,
    # NOT in paper). PHI_MAX / PHI_SETTLE / LAMBDA_SMOOTH inherited 0.0.

    # ──────────────────────────────────────────────────────────────────

    def __init__(
        self,
        random_disturbance: bool = True,
        comm_fail_prob: float | None = None,
        *,
        config: V4Config | None = None,
        comm_delay_steps: int = 0,
        forced_link_failures=None,
    ):
        # The explicit V4Config replaces the historic class-attr monkey-
        # patch pattern (root cause of CLM-0040). Defaults equal the
        # paper-faithful baseline; class attributes still hold the same
        # values as fallback for any code that bypasses the constructor.
        cfg = config or V4Config.paper_faithful()
        self.config: V4Config = cfg

        super().__init__(
            random_disturbance=random_disturbance,
            comm_fail_prob=comm_fail_prob,
            comm_delay_steps=comm_delay_steps,
            forced_link_failures=forced_link_failures,
        )

        # Per-instance physics + reward weights, sourced from cfg.
        # base_env.__init__ already populated self.M0 / self.D0 from class
        # attrs; override below so the supplied config wins.
        self.VSG_M0 = cfg.vsg_m0
        self.VSG_D0 = cfg.vsg_d0
        self.M0 = np.full(self.N_AGENTS, cfg.vsg_m0)
        self.D0 = np.full(self.N_AGENTS, cfg.vsg_d0)
        self.D0_HETEROGENEOUS = np.array(cfg.d0_per_agent)
        self.DM_MIN = cfg.dm_min
        self.DM_MAX = cfg.dm_max
        self.DD_MIN = cfg.dd_min
        self.DD_MAX = cfg.dd_max
        self.M_MIN_PHYSICAL = cfg.m_min_physical
        self.D_MIN_PHYSICAL = cfg.d_min_physical
        self.PHI_F = cfg.phi_f
        self.PHI_H = cfg.phi_h
        self.PHI_D = cfg.phi_d
        self.PHI_ABS = cfg.phi_abs
        self.PHI_MAX = cfg.phi_max
        self.PHI_SETTLE = cfg.phi_settle
        self.ZERO_G4_INERTIA = cfg.zero_g4_inertia
        self.action_penalty_mode = cfg.action_penalty_mode
        # R58 audit-A escape hatches (paper-ambiguity resolution).
        # Defaults preserve R30–R57 behaviour bit-identically.
        self.r_f_freq_units = cfg.r_f_freq_units
        self.h_paper_interpretation = cfg.h_paper_interpretation
        self.r_avg_scope = cfg.r_avg_scope
        # R50 opt B: V4Config-driven anti-smoothness + own-action obs.
        # Only override if cfg explicitly non-default; otherwise keep
        # base_env's env-var-derived value (R55 preserves LAMBDA_SMOOTH=-N
        # env-var path so research probes work via env-var-only).
        if cfg.lambda_smooth != 0.0:
            self._lambda_smooth = cfg.lambda_smooth
        # R83: V4Config 是 single source of truth (R37 / CLM-0040 fix 精神).
        # Sync 内部 flag 跟 cfg, 然后 recompute OBS_DIM. 支持 own_action + time
        # 并存 (V4Config 互斥已解除 R83 step 1).
        if cfg.include_own_action_obs and not self._include_own_action_obs:
            self._include_own_action_obs = True
            self._last_action = np.zeros((self.N_AGENTS, 2), dtype=np.float32)
        elif not cfg.include_own_action_obs and self._include_own_action_obs:
            self._include_own_action_obs = False
        if cfg.include_time_obs and not self._include_time_obs:
            self._include_time_obs = True
        elif not cfg.include_time_obs and self._include_time_obs:
            self._include_time_obs = False
        # R83 W3 area-mean freq obs aug
        if cfg.include_area_mean_freq_obs and not self._include_area_mean_freq_obs:
            self._include_area_mean_freq_obs = True
        elif not cfg.include_area_mean_freq_obs and self._include_area_mean_freq_obs:
            self._include_area_mean_freq_obs = False
        # Recompute OBS_DIM from current flags
        new_obs_dim = self.__class__.OBS_DIM
        if self._include_own_action_obs:
            new_obs_dim += 2
        if self._include_time_obs:
            new_obs_dim += 1
        if self._include_area_mean_freq_obs:
            new_obs_dim += 2
        self.OBS_DIM = new_obs_dim
        # R55 probe: windowed-horizon smoothness late-enable from cfg.
        if cfg.smoothness_window > 1 and self._smoothness_window <= 1:
            self._smoothness_window = cfg.smoothness_window
            self._action_history_dM = deque(maxlen=self._smoothness_window)
            self._action_history_dD = deque(maxlen=self._smoothness_window)

        # R05 disturbance-scale env var (calibrate against paper cum_rf).
        scale = float(os.environ.get("DISTURB_SCALE", "1.0"))
        if scale != 1.0:
            self.DIST_MIN = type(self).DIST_MIN * scale
            self.DIST_MAX = type(self).DIST_MAX * scale
            print(
                f"[disturb] DISTURB_SCALE={scale} -> "
                f"DIST_MIN={self.DIST_MIN}, DIST_MAX={self.DIST_MAX}"
            )

        self.case_path = andes.get_case("kundur/kundur_full.xlsx")

    def reset(self, *args, **kwargs):
        obs = super().reset(*args, **kwargs)
        # base_env._init_baselines populates self.D0 from VSG_D0 scalar;
        # re-apply heterogeneous D₀ vector here.
        self.D0 = self.D0_HETEROGENEOUS.copy()
        return obs

    # ─── System build ─────────────────────────────────────────────────

    def _build_system(self):
        """Load Kundur, extend topology (Fig.3), attach VSGs and wind-farm proxy."""
        ss = andes.load(self.case_path, default_config=True, setup=False)

        # G4 GENROU index, used optionally below to zero its inertia
        self._g4_genrou_idx = 4

        # Add new VSG buses (Bus 8 already exists)
        for new_bus in self.VSG_BUSES:
            if new_bus not in list(ss.Bus.idx.v):
                ss.add("Bus", {
                    "idx":  new_bus,
                    "name": f"Bus{new_bus}",
                    "Vn":   self.NEW_BUS_VN,
                    "v0":   1.0,
                    "a0":   0.0,
                    "area": 1 if new_bus in (12, 16) else 2,
                })

        # Tie lines
        for new_bus, parent_bus in self.NEW_BUS_CONNECTIONS.items():
            ss.add("Line", {
                "idx":  f"Line_{parent_bus}_{new_bus}",
                "bus1": parent_bus,
                "bus2": new_bus,
                "Vn1":  self.NEW_BUS_VN,
                "Vn2":  self.NEW_BUS_VN,
                "r":    self.NEW_LINE_R,
                "x":    self.NEW_LINE_X,
                "b":    self.NEW_LINE_B,
            })

        # Disturbance loads (Bus14, Bus15)
        for load_bus, load_params in self.NEW_LOADS.items():
            ss.add("PQ", {
                "idx":  f"PQ_Bus{load_bus}",
                "bus":  load_bus,
                "Vn":   self.NEW_BUS_VN,
                "p0":   load_params["p0"],
                "q0":   load_params["q0"],
            })

        # 4 VSGs (GENCLS) on new buses
        self.vsg_idx = []
        for i, bus in enumerate(self.VSG_BUSES):
            vsg_id = f"VSG_{i+1}"
            gen_id = f"SG_VSG_{i+1}"
            ss.add("PV", {
                "idx":  gen_id,
                "name": f"VSG{i+1}",
                "bus":  bus,
                "Vn":   self.NEW_BUS_VN,
                "Sn":   self.VSG_SN,
                "p0":   0.5, "q0": 0.0,
                "pmax": 5.0, "pmin": 0.0,
                "qmax": 5.0, "qmin": -5.0,
                "v0":   1.0,
            })
            ss.add("GENCLS", {
                "idx":  vsg_id,
                "bus":  bus,
                "gen":  gen_id,
                "Vn":   self.NEW_BUS_VN,
                "Sn":   self.VSG_SN,
                "M":    self.M0[i],
                "D":    self.D0[i],
                "ra":   0.001,
                "xd1":  0.15,
            })
            self.vsg_idx.append(vsg_id)

        # 100 MW wind-farm proxy on Bus 8 (low-inertia GENCLS)
        ss.add("PV", {
            "idx":  "SG_WF2",
            "name": "WF2_Bus8",
            "bus":  self.WF2_BUS,
            "Vn":   self.NEW_BUS_VN,
            "Sn":   self.WF2_SN,
            "p0":   self.WF2_P0, "q0": 0.0,
            "pmax": 5.0, "pmin": 0.0,
            "qmax": 5.0, "qmin": -5.0,
            "v0":   1.0,
        })
        ss.add("GENCLS", {
            "idx":  "WF2",
            "bus":  self.WF2_BUS,
            "gen":  "SG_WF2",
            "Vn":   self.NEW_BUS_VN,
            "Sn":   self.WF2_SN,
            "M":    0.1,
            "D":    0.0,
            "ra":   0.001,
            "xd1":  0.15,
        })

        # Add IEEEG1 governor + EXST1 AVR BEFORE ss.setup()
        # (R10 forensic fix — post-setup add is silently DAE-inactive)
        self._pre_setup_addons(ss)

        ss.setup()

        # Apply heterogeneous D₀ to each VSG after setup
        for i, vsg_id in enumerate(self.vsg_idx):
            ss.GENCLS.set("D", vsg_id, self.D0_HETEROGENEOUS[i], attr="v")

        # Optionally zero G4 inertia (off in V4 paper baseline)
        if self.ZERO_G4_INERTIA and hasattr(self, "_g4_genrou_idx"):
            genrou_idx_list = list(ss.GENROU.idx.v)
            if self._g4_genrou_idx in genrou_idx_list:
                ss.GENROU.set("M", self._g4_genrou_idx, 0.1, attr="v")
                ss.GENROU.set("D", self._g4_genrou_idx, 0.0, attr="v")

        # R114/CLM-0194 — optionally disable the ANDES default Toggler that
        # trips Line_8 at t=2s. Off by default (preserves R57-R85 behaviour
        # + all parallel rounds' ckpts). Set env var DISABLE_TOGGLER=1 to
        # train/eval on the cleaner single-event paper-faithful scenario.
        if os.environ.get("DISABLE_TOGGLER", "0") == "1":
            if hasattr(ss, "Toggler") and ss.Toggler.n > 0:
                for tog_idx in list(ss.Toggler.idx.v):
                    ss.Toggler.set("u", tog_idx, 0.0, attr="v")

        return ss

    def _pre_setup_addons(self, ss) -> None:
        """Attach IEEEG1 governor + EXST1 AVR to every GENROU before ss.setup().

        ANDES does not support ``add()`` after ``setup()`` — late additions
        produce models with NumParam fields populated but zero Algeb/State
        in the DAE (R10 forensic). Adding here ensures governor and AVR
        actually participate in the time-domain simulation.

        ``ss.GENROU.idx.v`` is populated by ``andes.load(setup=False)``
        because GENROU rows come from the xlsx data table.
        """
        assert len(ss.GENROU.idx.v) > 0, (
            "GENROU idx not populated pre-setup; "
            "andes.load(setup=False) API likely changed."
        )
        for syn_idx in ss.GENROU.idx.v:
            ss.IEEEG1.add(idx=f"GOV_{syn_idx}", syn=syn_idx)
            ss.EXST1.add(idx=f"AVR_{syn_idx}", syn=syn_idx)

    # ─── Disturbance application ──────────────────────────────────────

    def _apply_disturbance(self, delta_u=None, **kwargs):
        """Apply a PQ-bus load step.

        Uses ``Ppf`` (constant-power mode) rather than ``p0`` so the load
        change is honored during TDS. ``custom_event = True`` flags ANDES
        to re-evaluate algebraic variables on the next step.
        """
        if delta_u is not None:
            for pq_idx, dp in delta_u.items():
                pq_pos = list(self.ss.PQ.idx.v).index(pq_idx)
                self.ss.PQ.Ppf.v[pq_pos] += dp
        elif self.random_disturbance:
            n_pq = self.ss.PQ.n
            if n_pq > 0:
                pq_pos = self.rng.integers(0, n_pq)
                magnitude = self.rng.uniform(self.DIST_MIN, self.DIST_MAX)
                sign = self.rng.choice([-1, 1])
                self.ss.PQ.Ppf.v[pq_pos] += sign * magnitude

        self.ss.TDS.custom_event = True

    # ─── Introspection ────────────────────────────────────────────────

    @classmethod
    def deviation_summary(cls) -> dict:
        """Return a dict describing how this env deviates from the paper.

        Useful for logging / sanity-checking which baseline is being run.
        """
        g4_state = (
            "zeroed (ZERO_G4_INERTIA=True; paper headline numbers, CLM-0040)"
            if cls.ZERO_G4_INERTIA
            else "preserved (Kundur 4 SG baseline; not paper-headline reproducible)"
        )
        return {
            "version": "v4",
            "vsg_m0": cls.VSG_M0,
            "vsg_d0": cls.VSG_D0,
            "d0_heterogeneous": cls.D0_HETEROGENEOUS.tolist(),
            "g4_inertia": g4_state,
            "governor": "IEEEG1 DAE-active (R10 fix)",
            "avr": "EXST1 DAE-active (R10 fix)",
            "action_range_dm": (cls.DM_MIN, cls.DM_MAX),
            "action_range_dd": (cls.DD_MIN, cls.DD_MAX),
            "phi_f": cls.PHI_F,
            "phi_h": cls.PHI_H,
            "phi_d": cls.PHI_D,
            "rationale": (
                "V4 consolidates R10-R16 forensic fixes: governor wiring (R10), "
                "G4 paper-restoration (R15, 26% Root #3 share), "
                "H₀=100s middle of paper Eq.12 box [10,300] (R14), "
                "action range paper-faithful per Sec.IV-B "
                "(ΔM=[-200,600], ΔD=[-200,600]), "
                "PHI rescale 0.0056 = 1/178 (R18)."
            ),
        }
