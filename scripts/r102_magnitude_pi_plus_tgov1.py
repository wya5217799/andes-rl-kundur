"""R102 — Magnitude-PI variant (Q-0023) + TGOV1 ablation (Q-0021), bundled.

Two waves in one ANDES session (amortise ~30s init overhead, reuse R85
no_control cache):

  W1: Magnitude-PI controller (always-positive ΔM, ΔD on |Δω|), Kp grid
      sweep on V4 paper-faithful Kundur, comparison to R85 droop best
      0.197.

  W2: TGOV1 governor ablation: u=1 (default) vs u=0 (all 4 disabled)
      with zero-action policy. Tests whether TGOV1 in V4 is truly
      effective (R08 Finding 3 said V3 was not).

Reuses R85 `_no_control_cache` for axis-8 reference (no duplicate eval).

Run (WSL only — CLAUDE.md ANDES rule):
    /home/wya/andes_venv/bin/python scripts/r102_magnitude_pi_plus_tgov1.py
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.evaluation.summary import format_headline, score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
from andes_rl_kundur.scenarios.contract import KUNDUR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r102")

OUT_DIR = ROOT / "results" / "r102_magnitude_pi_plus_tgov1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Reuse R85 no_control cache (skip 2 redundant ANDES initialisations)
R85_NC_CACHE = ROOT / "results" / "r85_classical_baseline" / "_no_control_cache"

STEPS = 150
SEED = 42
DT = KUNDUR.dt


# ─── W1: Magnitude-PI controller ──────────────────────────────────────────

class MagnitudePIController:
    """Magnitude-symmetric PI on |Δω|. Always adds inertia/damping.

    err = obs[i][1]                # normalized Δω (signed)
    |err| = abs(err)
    integral[i] += |err| * DT      # always non-negative
    ΔM_norm[i] = clip(Kp_M*|err| + Ki_M*integral, 0, 1)
    ΔD_norm[i] = clip(Kp_D*|err| + Ki_D*integral, 0, 1)

    Reset on step==0. No anti-windup (10s episode keeps integral bounded
    for our gain magnitudes).
    """

    def __init__(self, kp_M: float, ki_M: float, kp_D: float, ki_D: float, n_agents: int):
        self.kp_M = kp_M
        self.ki_M = ki_M
        self.kp_D = kp_D
        self.ki_D = ki_D
        self.n_agents = n_agents
        self.integral = np.zeros(n_agents, dtype=np.float64)

    def reset(self) -> None:
        self.integral.fill(0.0)

    def __call__(self, step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
        if step == 0:
            self.reset()
        actions = {}
        for i in range(n_agents):
            abserr = abs(float(obs[i][1]))
            self.integral[i] += abserr * DT
            dM = self.kp_M * abserr + self.ki_M * self.integral[i]
            dD = self.kp_D * abserr + self.ki_D * self.integral[i]
            actions[i] = np.array([
                float(np.clip(dM, 0.0, 1.0)),
                float(np.clip(dD, 0.0, 1.0)),
            ], dtype=np.float32)
        return actions


# ─── Eval helper (mirrors R85 pattern, but uses cached R85 no_control) ────

def eval_controller(controller_factory, label: str, out_subdir: Path) -> dict:
    out_subdir.mkdir(parents=True, exist_ok=True)
    # copy cached no_control refs (axis 8 sibling)
    for scen in SCENARIOS:
        src = R85_NC_CACHE / f"no_control_{scen}.json"
        dst = out_subdir / f"no_control_{scen}.json"
        if not dst.exists():
            shutil.copy(src, dst)
    trace_paths = {}
    for scen, du in SCENARIOS.items():
        fn = controller_factory()
        rep = run_scenario(scen, du, action_fn=fn,
                           label=label, seed=SEED, steps=STEPS)
        p = out_subdir / f"{label}_{scen}.json"
        p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        trace_paths[scen] = p
        log.info(f"  {label}/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
    summary = score_trace_files(trace_paths, label=label, is_ddic=True)
    log.info(f"  → {format_headline(summary)}")
    return summary


def scan_magnitude_pi() -> tuple[dict, dict, list[dict]]:
    """W1: magnitude-PI Kp grid (P-only, 16 combo)."""
    log.info("\n=== W1: Magnitude-PI Kp grid ===")
    grid_kp_M = [0.5, 1.0, 2.0, 5.0]
    grid_kp_D = [0.5, 1.0, 2.0, 5.0]
    n_agents = KUNDUR.n_agents
    results = []
    best_geo = -1.0
    best_summary: dict = {}
    best_gains: dict = {}
    t0 = time.time()
    count = 0
    total = len(grid_kp_M) * len(grid_kp_D)
    for kp_M in grid_kp_M:
        for kp_D in grid_kp_D:
            count += 1
            log.info(f"\n[mag-PI {count}/{total}] kpM={kp_M} kpD={kp_D}")
            sub = OUT_DIR / "scan_mag_pi" / f"kpM{kp_M}_kpD{kp_D}"
            summary = eval_controller(
                lambda km=kp_M, kd=kp_D: MagnitudePIController(km, 0.0, kd, 0.0, n_agents),
                label="mag_pi",
                out_subdir=sub,
            )
            gains = {"kp_M": kp_M, "ki_M": 0.0, "kp_D": kp_D, "ki_D": 0.0}
            results.append({**gains, **summary})
            geo = summary.get("geo") or 0.0
            if geo > best_geo:
                best_geo = geo
                best_summary = dict(summary)
                best_gains = gains
            _flush({"w1_mag_pi_partial": results,
                    "w1_mag_pi_best_so_far": {**best_gains, **best_summary}})
    log.info(f"\n*** Magnitude-PI best: {best_gains} → geo={best_geo:.4f}  "
             f"(wall {time.time()-t0:.0f} s)")
    return best_gains, best_summary, results


# ─── W2: TGOV1 ablation ───────────────────────────────────────────────────

def _eval_tgov1_state(tgov1_active: bool, out_subdir: Path) -> dict:
    """Run zero-action eval on V4 with TGOV1.u set to tgov1_active (1/0).

    Uses a custom env wrapper that toggles TGOV1.u after setup().
    """
    out_subdir.mkdir(parents=True, exist_ok=True)
    # copy cached no_control (same controller logic but with TGOV1 toggle)
    for scen in SCENARIOS:
        src = R85_NC_CACHE / f"no_control_{scen}.json"
        dst = out_subdir / f"no_control_{scen}.json"
        if not dst.exists():
            shutil.copy(src, dst)

    trace_paths = {}
    label = f"tgov1_u{int(tgov1_active)}"
    for scen, du in SCENARIOS.items():
        env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
        try:
            env.seed(SEED)
            env.STEPS_PER_EPISODE = STEPS
            # Trigger initial build via reset (ANDES setup happens here)
            obs = env.reset(delta_u=du)
            # Toggle TGOV1.u after setup
            n_tgov1 = len(env.ss.TGOV1.idx.v)
            for g in env.ss.TGOV1.idx.v:
                env.ss.TGOV1.set("u", g, float(1.0 if tgov1_active else 0.0), attr="v")
            log.info(f"  [TGOV1 u={int(tgov1_active)}] {scen}: toggled {n_tgov1} governors")

            # Manually run scenario loop (mirrors run_scenario)
            from andes_rl_kundur.evaluation.paper_path import run_scenario as _ignored  # noqa
            traces = []
            cum_rf = 0.0
            max_df = 0.0
            osc_accum = 0.0
            n_agents = env.N_AGENTS
            f_nom = env.FN
            for step in range(STEPS):
                actions = {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}
                obs, _r, done, info = env.step(actions)
                if info.get("tds_failed"):
                    break
                freq_hz = info["freq_hz"].astype(float).tolist()
                delta_f = [(f - f_nom) for f in freq_hz]
                f_bar = float(np.mean(freq_hz))
                step_rf = float(np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f]))
                cum_rf -= step_rf
                max_df = max(max_df, float(np.max(np.abs(delta_f))))
                osc_accum += float(np.std(delta_f))
                traces.append({
                    "step": step, "t": float(info["time"]),
                    "freq_hz": freq_hz, "f_bar": f_bar, "step_rf": step_rf,
                    "delta_P_es": info["P_es"].astype(float).tolist(),
                    "delta_f_es": delta_f,
                    "M_es": info["M_es"].astype(float).tolist(),
                    "D_es": info["D_es"].astype(float).tolist(),
                    "delta_M": info["delta_M"].astype(float).tolist(),
                    "delta_D": info["delta_D"].astype(float).tolist(),
                })
                if done:
                    break
            rep = {
                "controller": label, "scenario": scen, "env_version": "v4",
                "cum_rf_total": cum_rf, "max_df": max_df, "osc": osc_accum,
                "n_steps": len(traces), "traces": traces,
                "tgov1_active": bool(tgov1_active),
            }
            p = out_subdir / f"{label}_{scen}.json"
            p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
            trace_paths[scen] = p
            log.info(f"    {scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
        finally:
            env.close()
    summary = score_trace_files(trace_paths, label=label, is_ddic=False)  # zero-action ≈ no_control
    log.info(f"  → {format_headline(summary)}")
    return summary


def ablation_tgov1() -> dict:
    """W2: TGOV1 ablation, zero-action × {u=1, u=0}."""
    log.info("\n=== W2: TGOV1 ablation ===")
    sum_u1 = _eval_tgov1_state(True, OUT_DIR / "w2_tgov1_u1")
    sum_u0 = _eval_tgov1_state(False, OUT_DIR / "w2_tgov1_u0")
    diff_geo = (sum_u0.get("geo") or 0.0) - (sum_u1.get("geo") or 0.0)
    cum_rf_u1 = sum_u1.get("cum_rf") or 0.0
    cum_rf_u0 = sum_u0.get("cum_rf") or 0.0
    diff_cum_rf = cum_rf_u0 - cum_rf_u1
    pct_diff_cum_rf = abs(diff_cum_rf) / (abs(cum_rf_u1) + 1e-9) * 100
    log.info(f"\n*** TGOV1 ablation: u=1 geo={sum_u1.get('geo'):.4f}  "
             f"u=0 geo={sum_u0.get('geo'):.4f}  Δgeo={diff_geo:+.4f}  "
             f"Δcum_rf={diff_cum_rf:+.4f} ({pct_diff_cum_rf:.1f}%)")
    return {
        "u1": sum_u1, "u0": sum_u0,
        "diff_geo": diff_geo,
        "diff_cum_rf": diff_cum_rf,
        "pct_diff_cum_rf": pct_diff_cum_rf,
        "verdict": (
            "TGOV1 silently DAE-inactive (R08 V3 extends V4)" if pct_diff_cum_rf < 1
            else "TGOV1 truly active (R08 V3 finding does NOT extend V4)" if pct_diff_cum_rf >= 5
            else "TGOV1 partial / borderline"
        ),
    }


# ─── Persistence ──────────────────────────────────────────────────────────

GRAND: dict = {
    "round": 102,
    "steps": STEPS, "seed": SEED, "dt": DT,
    "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "reference": {
        "r72_w4_sota_geo": 0.391,
        "no_control_geo": 0.104,
        "r85_best_droop_geo": 0.197,
        "r85_best_pi_naive_geo": 0.058,
    },
}


def _flush(updates: dict) -> None:
    GRAND.update(updates)
    (OUT_DIR / "r102_summary.json").write_text(
        json.dumps(GRAND, indent=2, default=str), encoding="utf-8"
    )


def main() -> None:
    log.info(f"R102 — magnitude-PI + TGOV1 ablation; output → {OUT_DIR}")
    log.info(f"  (reusing R85 no_control cache from {R85_NC_CACHE})")

    # Quick sanity: cache exists
    for scen in SCENARIOS:
        nc = R85_NC_CACHE / f"no_control_{scen}.json"
        assert nc.exists(), f"Missing R85 cache: {nc}"

    # W1: magnitude-PI
    best_gains, best_pi_summary, w1_results = scan_magnitude_pi()
    _flush({
        "w1_mag_pi_best": {**best_gains, **best_pi_summary},
        "w1_mag_pi_all": w1_results,
    })

    # W2: TGOV1 ablation
    w2 = ablation_tgov1()
    _flush({"w2_tgov1_ablation": w2})

    log.info("\n" + "=" * 60)
    log.info("R102 HEADLINE")
    log.info("=" * 60)
    pi_geo = best_pi_summary.get("geo") or 0.0
    log.info("  no_control      : geo = 0.104   (R30)")
    log.info("  best droop R85  : geo = 0.197   (CLM-0184)")
    log.info("  best naive PI   : geo = 0.058   (CLM-0185)")
    log.info(f"  best mag-PI R102: geo = {pi_geo:.4f}   ({best_gains})")
    log.info("  R72_w4 SOTA     : geo = 0.391   (CLM-0094)")
    log.info(f"  TGOV1 ablation  : u=1 vs u=0 Δcum_rf = {w2['pct_diff_cum_rf']:.1f}%")
    log.info(f"  TGOV1 verdict   : {w2['verdict']}")
    log.info("=" * 60)

    _flush({
        "headline": {
            "best_mag_pi_geo": pi_geo,
            "best_mag_pi_gains": best_gains,
            "tgov1_pct_diff_cum_rf": w2["pct_diff_cum_rf"],
            "tgov1_verdict": w2["verdict"],
            "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    })


if __name__ == "__main__":
    main()
