"""R20 — reward paradox confirmatory probe (V4.1 trained ckpt settled-phase audit).

Question (from 2026-05-07 v4 session handoff Section 5 Hypothesis A + E):
  V4.1 strict paper Eq.14 (PHI_ABS=0) trains policies that are anti-paper
  (max|Δf| 20-30% WORSE than no_control). Hypothesis: paper reward formula
  has a *trivial optimum* on a 4-agent ring:

    r_f = -local_sync²  → 0 when 4 agents agree (any non-zero ω)
    r_h = -(mean ΔH)²   → 0 when 4 agents互抵 (signs cancel)
    r_d = -(mean ΔD)²   → 0 when 4 agents互抵
    PHI_ABS = 0         → no |Δω| absolute penalty

  → SAC should converge to: 4 agents sync to non-zero ω, ΔH/ΔD互抵,
    all reward terms ≈ 0. This is anti-paper by construction.

Probe protocol (uses ``probes/andes_common`` framework):
  1. Load V4.1 ckpt s44 best (handoff says cleanest 200-ep run).
  2. Run deterministic policy on LS1 + LS2 (paper Fig.6/8 scenarios).
  3. Settled phase = last 30 step (t > 4s) at STEPS=50.
  4. Verdict gate (3-clause AND for paradox confirmation):
       (a) settled max|Δω| ≥ 0.05 Hz                  ← agents NOT pulling to 50Hz
       (b) settled |r_f_total| < 0.5 (PHI_F=100 scale) ← sync achieved
       (c) settled |mean(ΔH)| < 5 AND std(ΔH) > 30    ← agents互抵 (signs cancel)

Output:
  results/research_loop/r20_reward_settled.json
  quality_reports/research_loop/round_20_verdict.md
"""
from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ─── Claude-safe stdout policy ──────────────────────────────────────────────
# Why: this probe runs 6 scenarios × 50 steps × 5 substeps = 1500 ANDES TDS
# calls. ANDES default logger emits ~10–50 lines per call via Python logging;
# the TDS routine also instantiates tqdm progress bars writing to sys.stdout.
# When invoked via PowerShell `2>&1` the captured tool result overflows
# Claude Code's tool-result buffer and crashes the host.
#
# Defence in depth (all three are needed; one is not enough):
#   (1) Lower andes Python loggers to CRITICAL — drops most messages at the
#       logger.filter() stage before they ever reach a handler.
#   (2) Wrap heavy loop in contextlib.redirect_stdout / redirect_stderr — this
#       captures `sys.stdout` reads that happen at runtime, including tqdm's
#       `file=sys.stdout` default. NOTE: this does NOT capture logging
#       StreamHandler output, because StreamHandler stores the stream by
#       reference at construction time.
#   (3) OS-level dup2() of fd 1 and fd 2 to a log file. This catches:
#         (a) the StreamHandler that survived (1)+(2) by holding the original
#             sys.stderr reference;
#         (b) any C-extension fprintf() to fd 1/2 (e.g., kvxopt solver chatter);
#         (c) anything else that bypasses sys.stdout/sys.stderr at the Python
#             level entirely.
#
# TQDM_DISABLE env var was removed: tqdm does not read it, and the progress
# bar's file=sys.stdout is already captured by (2).
#
# Final stdout to Claude is only the verdict summary (≈ 7 lines), printed
# AFTER the redirect+dup2 are torn down.
for _name in (
    "andes",
    "andes.system",
    "andes.routines",
    "andes.routines.tds",
    "andes.routines.pflow",
    "andes.utils",
    "andes.utils.misc",
    "andes.io",
):
    logging.getLogger(_name).setLevel(logging.CRITICAL)

from agents.sac import SACAgent  # noqa: E402
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from probes.andes_common import (  # noqa: E402
    LS1_DELTA_U,
    LS2_DELTA_U,
    run_trained_policy_trace,
    run_zero_action_trace,
)

# Re-assert silencing AFTER andes import. config_logger on a non-empty handler
# list only updates levels (it does NOT swap the handler stream — verified in
# andes/main.py), so this is purely a level-belt to complement the redirect.
try:
    import andes  # noqa: E402
    andes.config_logger(stream_level=logging.CRITICAL, file=False)
except Exception:
    pass


@contextlib.contextmanager
def _silence_fds_to(log_path: Path):
    """Single-OFD redirect of fd 1, fd 2, sys.stdout, sys.stderr to log_path.

    Why a single open-file-description matters:
        Naive layering (dup2 fd 1/2 + open(log,"a") + redirect_stdout) creates
        TWO open-file-descriptions writing to the same file with INDEPENDENT
        kernel offsets. On Windows, "a" mode only seeks to EOF at open time
        (no per-write O_APPEND atomicity), so the dup2-side fd writes from
        offset 0 silently OVERWRITE the redirect-side fd's earlier appends.
        This was confirmed by a self-test: MARKER_1/2 (Python print) went to
        offsets 0-46 via the "a"-mode handle; MARKER_3 (os.write) wrote at
        fd 1's offset 0 and clobbered them. (See selftest log.)
    Fix:
        Open ONE log fd. dup2 it onto fd 1 and fd 2. Then build new Python
        TextIOWrappers around those fds and replace sys.stdout / sys.stderr
        with them (closefd=False so leaving the context doesn't close fd 1/2
        prematurely; we restore the saved originals first).
    Catches:
        - Python print / sys.stdout.write          (via replaced sys.stdout)
        - logging.StreamHandler bound at import     (via dup2 fd 2)
        - os.write / C-extension fprintf to fd 1/2  (via dup2 fd 1/2)
        - tqdm with file=sys.stdout                 (via replaced sys.stdout)
    Restores everything on exit. Safe under exceptions.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()

    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    saved_sys_stdout = sys.stdout
    saved_sys_stderr = sys.stderr

    log_fd = os.open(
        str(log_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
    )
    try:
        os.dup2(log_fd, 1)
        os.dup2(log_fd, 2)
        os.close(log_fd)
        # Wrap fd 1 / fd 2 so Python-level writes share the SAME OFD as raw
        # os.write calls. closefd=False because we manage fd lifetime via the
        # dup2/restore pair.
        sys.stdout = os.fdopen(1, "w", buffering=1, encoding="utf-8",
                               errors="replace", closefd=False)
        sys.stderr = os.fdopen(2, "w", buffering=1, encoding="utf-8",
                               errors="replace", closefd=False)
        yield
    finally:
        # Flush our wrappers first (they hold buffered data).
        for _w in (sys.stdout, sys.stderr):
            try:
                _w.flush()
            except Exception:
                pass
        # Restore Python-level streams BEFORE restoring fds, so any code
        # caching sys.stdout doesn't see a half-restored state.
        sys.stdout = saved_sys_stdout
        sys.stderr = saved_sys_stderr
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)

OUT_DIR = ROOT / "results" / "research_loop"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "r20_reward_settled.json"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG = LOG_DIR / "r20_andes.log"

DEFAULT_CKPT = ROOT / "results" / "v4_1_paper_s44"
DEFAULT_SUFFIX = "best"
N_STEPS = 50
SETTLED_TAIL = 30
EVAL_SEED = 42

RECORD_KEYS = ("freq_hz", "delta_M", "delta_D", "r_f", "r_h", "r_d")


def load_actors(ckpt_dir: Path, suffix: str) -> list[SACAgent]:
    from config import HIDDEN_SIZES
    obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    actors = []
    for i in range(AndesMultiVSGEnvV4.N_AGENTS):
        a = SACAgent(
            obs_dim=obs_dim, action_dim=2,
            hidden_sizes=HIDDEN_SIZES, device="cpu",
        )
        path = ckpt_dir / f"agent_{i}_{suffix}.pt"
        if not path.exists():
            raise FileNotFoundError(f"missing ckpt: {path}")
        a.load(str(path))
        actors.append(a)
    return actors


def _patch_phi_abs(value: float):
    def patch(env):
        env.PHI_ABS = value
    return patch


def settled_metrics(out: dict[str, Any]) -> dict[str, Any]:
    """Compute settled-phase verdict gates from a trace dict.

    Accepts the schema from ``run_zero_action_trace`` /
    ``run_trained_policy_trace``: keys ``traj``, ``df_traj``, ``n_steps``.
    """
    n = out["n_steps"]
    if n == 0:
        return {"err": "no_steps"}
    traj = out["traj"]
    F_NOM = AndesMultiVSGEnvV4.FN

    freq = np.array(traj["freq_hz"])
    dM = np.array(traj["delta_M"])
    dD = np.array(traj["delta_D"])
    r_f = np.array(traj["r_f"]) if traj.get("r_f") else np.zeros(n)
    r_h = np.array(traj["r_h"]) if traj.get("r_h") else np.zeros(n)
    r_d = np.array(traj["r_d"]) if traj.get("r_d") else np.zeros(n)
    dH = dM / 2.0
    dω = freq - F_NOM

    tail = min(SETTLED_TAIL, n)
    s = slice(n - tail, n)

    settled_max_abs_dw = float(np.max(np.abs(dω[s])))
    settled_dH_per_agent = dH[s].mean(axis=0).tolist()
    settled_dD_per_agent = dD[s].mean(axis=0).tolist()
    settled_dH_global_mean = float(np.mean(dH[s]))
    settled_dH_per_agent_std = float(np.std(settled_dH_per_agent))

    settled_r_f = float(np.mean(r_f[-tail:]))
    settled_r_h = float(np.mean(r_h[-tail:]))
    settled_r_d = float(np.mean(r_d[-tail:]))

    gate_a = bool(settled_max_abs_dw >= 0.05)
    gate_b = bool(abs(settled_r_f) < 0.5)
    gate_c = bool(
        abs(settled_dH_global_mean) < 5.0
        and settled_dH_per_agent_std > 30.0
    )
    paradox = gate_a and gate_b and gate_c

    return {
        "tail_n": tail,
        "max_abs_dw_hz": settled_max_abs_dw,
        "mean_abs_dw_hz": float(np.mean(np.abs(dω[s]))),
        "dH_per_agent": settled_dH_per_agent,
        "dH_global_mean": settled_dH_global_mean,
        "dH_per_agent_std": settled_dH_per_agent_std,
        "dD_per_agent": settled_dD_per_agent,
        "dD_global_mean": float(np.mean(dD[s])),
        "r_f_mean": settled_r_f,
        "r_h_mean": settled_r_h,
        "r_d_mean": settled_r_d,
        "gates": {
            "A_settled_dw_ge_0p05": gate_a,
            "B_rf_settled_lt_0p5": gate_b,
            "C_dH_signs_cancel": gate_c,
        },
        "paradox_confirmed": paradox,
    }


def _run_all_scenarios(actors, args) -> dict[str, Any]:
    """Heavy work: 6 scenarios × 50 steps × 5 substeps = 1500 TDS calls.

    Caller MUST wrap this in redirect_stdout/redirect_stderr to keep ANDES
    chatter out of the parent stdout buffer (Claude-safe contract).
    """
    ckpt_dir = Path(args.ckpt_dir)
    results: dict[str, Any] = {
        "ckpt_dir": str(ckpt_dir),
        "ckpt_suffix": args.suffix,
        "n_steps": N_STEPS,
        "settled_tail": SETTLED_TAIL,
        "scenarios": {},
    }

    runs = [
        ("baseline_LS1",      LS1_DELTA_U, None,    0.0),
        ("baseline_LS2",      LS2_DELTA_U, None,    0.0),
        ("trained_phi0_LS1",  LS1_DELTA_U, actors,  0.0),
        ("trained_phi0_LS2",  LS2_DELTA_U, actors,  0.0),
        ("trained_phi50_LS1", LS1_DELTA_U, actors, 50.0),
        ("trained_phi50_LS2", LS2_DELTA_U, actors, 50.0),
    ]

    for name, scen, actors_or_none, phi_abs in runs:
        print(f"[R20] {name} (PHI_ABS={phi_abs}) ...")
        env_patch = _patch_phi_abs(phi_abs)
        if actors_or_none is None:
            out = run_zero_action_trace(
                env_cls=AndesMultiVSGEnvV4,
                scenario=scen,
                n_steps=N_STEPS,
                seed=EVAL_SEED,
                env_patch=env_patch,
                record_extras=RECORD_KEYS,
            )
        else:
            out = run_trained_policy_trace(
                env_cls=AndesMultiVSGEnvV4,
                scenario=scen,
                agents=actors_or_none,
                n_steps=N_STEPS,
                seed=EVAL_SEED,
                env_patch=env_patch,
                deterministic=True,
                record_extras=RECORD_KEYS,
            )
        out["settled"] = settled_metrics(out)
        out["phi_abs_recompute"] = phi_abs
        results["scenarios"][name] = out

    paradox_LS1 = results["scenarios"]["trained_phi0_LS1"]["settled"].get(
        "paradox_confirmed", False)
    paradox_LS2 = results["scenarios"]["trained_phi0_LS2"]["settled"].get(
        "paradox_confirmed", False)
    results["verdict"] = {
        "LS1_paradox_confirmed": paradox_LS1,
        "LS2_paradox_confirmed": paradox_LS2,
        "overall": ("PARADOX_CONFIRMED" if (paradox_LS1 or paradox_LS2)
                    else "PARADOX_NOT_CONFIRMED"),
    }
    return results


def _print_summary(results: dict[str, Any], out_path: Path, log_path: Path) -> None:
    """≤ 10 lines to real stdout; safe for Claude tool-result buffer.

    Guards every settled-metrics access against the {"err": "no_steps"} dict
    returned when a scenario crashes ANDES on step 1. This is the exact
    condition the paradox hypothesis predicts (PHI_ABS=0 destabilising the
    first TDS call), so silent KeyError here would mask the most diagnostic
    case.
    """
    print(f"[R20] wrote   {out_path}")
    print(f"[R20] log     {log_path}")
    print(f"[R20] verdict {results['verdict']['overall']}")
    for tag in ("trained_phi0_LS1", "trained_phi0_LS2"):
        d = results["scenarios"][tag]
        s = d["settled"]
        n_steps = d.get("n_steps", 0)
        tds_failed = d.get("tds_failed", False)
        if "err" in s or n_steps == 0:
            print(
                f"  {tag}: TDS_FAILED n_steps={n_steps} tds_failed={tds_failed} "
                f"err={s.get('err', 'n_steps==0')}"
            )
            continue
        max_df = d.get("max_df")
        max_df_str = f"{max_df:.3f}" if max_df is not None else "n/a"
        print(
            f"  {tag}: max_df={max_df_str} | settled max|dw|={s['max_abs_dw_hz']:.3f} | "
            f"mean(dH)={s['dH_global_mean']:.1f} | std(dH)={s['dH_per_agent_std']:.1f} | "
            f"r_f={s['r_f_mean']:.2f} | gates={s['gates']}"
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt-dir", default=str(DEFAULT_CKPT))
    p.add_argument("--suffix",   default=DEFAULT_SUFFIX)
    p.add_argument("--out",      default=str(OUT_PATH))
    p.add_argument("--log",      default=str(DEFAULT_LOG),
                   help="ANDES verbose output sink (Claude-safe stdout redirect target)")
    p.add_argument("--no-redirect", action="store_true",
                   help="Disable stdout/stderr redirect (for interactive debugging only)")
    args = p.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    ckpt_dir = Path(args.ckpt_dir)
    # Loading actors is quiet; do it before redirect so any ckpt errors are visible.
    print(f"[R20] loading 4 actors from {ckpt_dir} (suffix={args.suffix})")
    actors = load_actors(ckpt_dir, args.suffix)

    if args.no_redirect:
        results = _run_all_scenarios(actors, args)
    else:
        # _silence_fds_to handles all four escape paths via a single OFD:
        # dup2 of fd 1/2 + Python-level sys.stdout/stderr re-wrap. No need
        # for an additional contextlib.redirect_stdout layer (which would
        # create a second OFD and cause silent overwrites on Windows).
        with _silence_fds_to(log_path):
            results = _run_all_scenarios(actors, args)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    _print_summary(results, out_path, log_path)


if __name__ == "__main__":
    main()
