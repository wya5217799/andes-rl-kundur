"""R85 — Classical PI / Droop baseline (paper-mandatory comparison).

Implements two classical controllers in the same action space as the RL
agent (per-ESS distributed, ΔM_norm + ΔD_norm ∈ [-1, 1]^2) and evaluates
them on the same LS1 + LS2 scenarios as the R72_w4 SOTA cross-eval (R80).

Goal: produce 11-axis geo number to compare with R72_w4 (0.391) +
no_control (0.104). R57-R82 共 91 round 全部跳过 classical baseline ―
R85 closes that gap.

Output: ``results/r85_classical_baseline/{droop,pi}_<scen>.json``
       + ``r85_classical_baseline_summary.json`` at the top.

Run (WSL only — CLAUDE.md ANDES rule):
    /home/wya/andes_venv/bin/python scripts/r85_classical_baseline.py
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import zero_action_fn  # noqa: E402
from andes_rl_kundur.evaluation.summary import format_headline, score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
from andes_rl_kundur.scenarios.contract import KUNDUR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r85")

OUT_DIR = ROOT / "results" / "r85_classical_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS = 150          # 30s @ DT=0.2 (paper-cited; R80 cross-eval same)
SEED = 42            # paper seed; R80 cross-eval same
DT = KUNDUR.dt  # 0.2 s — RL control timestep, PI integration step


# ─── Controllers ──────────────────────────────────────────────────────────

@dataclass
class DroopController:
    """Pure frequency droop on damping coefficient. Memoryless.

    ``ΔD_norm[i] = clip(K_droop * |obs[i][1]|, 0, 1)`` ; ``ΔM_norm[i] = 0``.

    obs[i][1] is the V4 base_env normalized Δω = (omega[i] - 1.0) * omega_scale / 3.0
    (rad/s offset, divided by 3.0 for normalization — see base_env._build_obs L536).
    Taking ``|·|`` because damping should be added regardless of overshoot
    or undershoot direction.
    """
    k_droop: float

    def __call__(self, step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
        actions = {}
        for i in range(n_agents):
            dD = float(np.clip(self.k_droop * abs(float(obs[i][1])), 0.0, 1.0))
            actions[i] = np.array([0.0, dD], dtype=np.float32)
        return actions


class PIController:
    """Distributed PI on (ΔM, ΔD), one instance shared across all agents.

    State: per-agent integral of normalized Δω. Reset on ``step == 0``.

    ``err_i = obs[i][1]``  (normalized Δω, see DroopController docstring)
    ``integral[i] += err_i * DT``
    ``ΔM_norm[i] = clip(-Kp_M * err_i - Ki_M * integral[i], -1, 1)``
    ``ΔD_norm[i] = clip(-Kp_D * err_i - Ki_D * integral[i], -1, 1)``

    Sign convention: frequency drop (Δω < 0) ⇒ err < 0 ⇒ -Kp*err > 0 ⇒
    ΔM, ΔD > 0 (add inertia + damping). Matches Kundur intuition.

    No anti-windup. Episode = 50 step × DT=0.2 = 10 s, integral stays bounded
    for the gain magnitudes we scan (verified empirically by clip ratio).
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
            err = float(obs[i][1])
            self.integral[i] += err * DT
            dM = -self.kp_M * err - self.ki_M * self.integral[i]
            dD = -self.kp_D * err - self.ki_D * self.integral[i]
            actions[i] = np.clip([dM, dD], -1.0, 1.0).astype(np.float32)
        return actions


# ─── Eval helper ──────────────────────────────────────────────────────────

ActionFnFactory = Callable[[], Callable]


# Shared no_control reference dir — generated once, copied into every controller
# subdir to satisfy axis 8 sibling-file requirement. Avoids ~25 redundant ANDES
# init across the gain sweep.
NC_CACHE_DIR = OUT_DIR / "_no_control_cache"


def ensure_no_control_cache() -> None:
    """Run no_control on LS1+LS2 once, cache JSON in NC_CACHE_DIR."""
    NC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for scen, du in SCENARIOS.items():
        nc_path = NC_CACHE_DIR / f"no_control_{scen}.json"
        if nc_path.exists():
            continue
        log.info(f"\n[no_control cache] {scen}")
        rep = run_scenario(scen, du, action_fn=zero_action_fn,
                           label="no_control", seed=SEED, steps=STEPS)
        nc_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        log.info(f"  no_ctrl/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")


def eval_controller(
    controller_factory: ActionFnFactory,
    label: str,
    out_subdir: Path,
) -> dict[str, float | None]:
    """Run controller on LS1 + LS2, save traces, copy cached no_control refs
    (axis 8 sibling-file dependency), then score via score_trace_files.

    Returns the summary dict with ``geo`` headline.
    """
    out_subdir.mkdir(parents=True, exist_ok=True)
    trace_paths: dict[str, Path] = {}

    # 1. no_control reference (copy from cache — axis 8 sibling requirement)
    for scen in SCENARIOS:
        src = NC_CACHE_DIR / f"no_control_{scen}.json"
        dst = out_subdir / f"no_control_{scen}.json"
        if not dst.exists():
            shutil.copy(src, dst)

    # 2. controller traces
    for scen, du in SCENARIOS.items():
        fn = controller_factory()
        rep = run_scenario(scen, du, action_fn=fn,
                           label=label, seed=SEED, steps=STEPS)
        p = out_subdir / f"{label}_{scen}.json"
        p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        trace_paths[scen] = p
        log.info(f"  {label}/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")

    # 3. score
    summary = score_trace_files(trace_paths, label=label, is_ddic=True)
    log.info(f"  → {format_headline(summary)}")
    return summary


# ─── Grid scans ───────────────────────────────────────────────────────────

def scan_droop() -> tuple[float, dict, list[dict]]:
    """Sweep K_droop ∈ {0.5, 1, 2, 5, 10, 20, 50}."""
    log.info("\n=== Droop grid scan ===")
    grid = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    results = []
    best_geo = -1.0
    best_summary: dict = {}
    best_k = 0.0
    for k in grid:
        sub = OUT_DIR / "scan_droop" / f"k{k:.1f}"
        log.info(f"\n[droop k={k:.1f}]")
        summary = eval_controller(
            lambda kk=k: DroopController(k_droop=kk),
            label="droop",
            out_subdir=sub,
        )
        results.append({"k_droop": k, **summary})
        geo = summary.get("geo") or 0.0
        if geo > best_geo:
            best_geo = geo
            best_summary = dict(summary)
            best_k = k
    log.info(f"\n*** Droop best: K={best_k:.1f} → geo={best_geo:.4f}")
    return best_k, best_summary, results


def _eval_pi(kp_M: float, ki_M: float, kp_D: float, ki_D: float, n_agents: int,
             label_suffix: str) -> dict:
    """One PI eval, returns gains + summary merged."""
    sub = OUT_DIR / label_suffix / f"kpM{kp_M}_kiM{ki_M}_kpD{kp_D}_kiD{ki_D}"
    summary = eval_controller(
        lambda km=kp_M, im=ki_M, kd=kp_D, id_=ki_D:
            PIController(km, im, kd, id_, n_agents),
        label="pi",
        out_subdir=sub,
    )
    return {"kp_M": kp_M, "ki_M": ki_M, "kp_D": kp_D, "ki_D": ki_D, **summary}


def scan_pi() -> tuple[dict, dict, list[dict]]:
    """Ladder PI scan: P-only coarse, then Ki around best. Total ~13 PI combos.

    Phase 1: Ki=0, sweep Kp_M × Kp_D over 3x3 = 9.
    Phase 2: lock best Kp's, sweep Ki_M × Ki_D over 2x2 = 4.
    """
    log.info("\n=== PI Phase 1: P-only (Ki=0) ===")
    grid_kp_M = [2.0, 10.0, 40.0]
    grid_kp_D = [2.0, 10.0, 40.0]
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
            log.info(f"\n[pi P-only {count}/{total}] kpM={kp_M} kpD={kp_D}")
            r = _eval_pi(kp_M, 0.0, kp_D, 0.0, n_agents, "scan_pi_phase1")
            results.append(r)
            geo = r.get("geo") or 0.0
            if geo > best_geo:
                best_geo = geo
                best_summary = {k: r[k] for k in ("LS1", "LS2", "geo", "cum_rf",
                                                   "cum_rf_LS1", "cum_rf_LS2")}
                best_gains = {k: r[k] for k in ("kp_M", "ki_M", "kp_D", "ki_D")}
            _flush({"pi_phase1_partial": results,
                    "pi_phase1_best_so_far": {**best_gains, **best_summary}})

    log.info(f"\n*** Phase 1 best: {best_gains} → geo={best_geo:.4f}  "
             f"(wall {time.time()-t0:.0f} s)")

    # Phase 2: Ki sweep around best Kp
    log.info("\n=== PI Phase 2: Ki sweep around best Kp ===")
    grid_ki_M = [2.0, 10.0]
    grid_ki_D = [2.0, 10.0]
    p1_best_kp_M = best_gains["kp_M"]
    p1_best_kp_D = best_gains["kp_D"]
    count = 0
    total = len(grid_ki_M) * len(grid_ki_D)
    for ki_M in grid_ki_M:
        for ki_D in grid_ki_D:
            count += 1
            log.info(f"\n[pi Ki {count}/{total}] kpM={p1_best_kp_M} kiM={ki_M} "
                     f"kpD={p1_best_kp_D} kiD={ki_D}")
            r = _eval_pi(p1_best_kp_M, ki_M, p1_best_kp_D, ki_D, n_agents,
                         "scan_pi_phase2")
            results.append(r)
            geo = r.get("geo") or 0.0
            if geo > best_geo:
                best_geo = geo
                best_summary = {k: r[k] for k in ("LS1", "LS2", "geo", "cum_rf",
                                                   "cum_rf_LS1", "cum_rf_LS2")}
                best_gains = {k: r[k] for k in ("kp_M", "ki_M", "kp_D", "ki_D")}
            _flush({"pi_phase2_partial": results,
                    "pi_phase2_best_so_far": {**best_gains, **best_summary}})

    log.info(f"\n*** PI overall best: {best_gains} → geo={best_geo:.4f}  "
             f"(total wall {time.time()-t0:.0f} s)")
    return best_gains, best_summary, results


# ─── Persistence ──────────────────────────────────────────────────────────

GRAND: dict = {
    "round": 85,
    "steps": STEPS, "seed": SEED, "dt": DT,
    "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "reference": {
        "r72_w4_sota_geo": 0.391,       # CLM-0094 + R80 cross-eval
        "no_control_geo": 0.104,        # R30 baseline
    },
}


def _flush(updates: dict) -> None:
    GRAND.update(updates)
    (OUT_DIR / "r85_classical_baseline_summary.json").write_text(
        json.dumps(GRAND, indent=2, default=str), encoding="utf-8"
    )


def main() -> None:
    log.info(f"R85 — classical baseline; output → {OUT_DIR}")

    # Phase 0: cache no_control once (avoids ~25 redundant ANDES init)
    ensure_no_control_cache()

    # Scan 1: droop
    best_k, droop_summary, droop_results = scan_droop()
    _flush({
        "droop_best_k": best_k,
        "droop_best_summary": droop_summary,
        "droop_all": droop_results,
    })

    # Scan 2: PI coarse
    best_pi_gains, pi_summary, pi_results = scan_pi()
    _flush({
        "pi_coarse_best": {**best_pi_gains, **pi_summary},
        "pi_coarse_all": pi_results,
    })

    # Headline comparison
    droop_geo = droop_summary.get("geo") or 0.0
    pi_geo = pi_summary.get("geo") or 0.0
    log.info("\n" + "=" * 60)
    log.info("R85 HEADLINE")
    log.info("=" * 60)
    log.info(f"  no_control      : geo = 0.104   (R30, ref)")
    log.info(f"  best droop      : geo = {droop_geo:.4f}   (K={best_k:.1f})")
    log.info(f"  best PI (coarse): geo = {pi_geo:.4f}   ({best_pi_gains})")
    log.info(f"  R72_w4 SOTA     : geo = 0.391   (CLM-0094)")
    log.info("=" * 60)

    headline = {
        "no_control_geo": 0.104,
        "best_droop_geo": droop_geo,
        "best_pi_coarse_geo": pi_geo,
        "r72_w4_sota_geo": 0.391,
        "rl_advantage_over_droop": 0.391 - droop_geo,
        "rl_advantage_over_pi": 0.391 - pi_geo,
        "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _flush({"headline": headline})

    log.info(f"\nSummary written to {OUT_DIR/'r85_classical_baseline_summary.json'}")


if __name__ == "__main__":
    main()
