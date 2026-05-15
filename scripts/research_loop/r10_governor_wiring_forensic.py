"""R10 Governor Wiring Forensic — 方向 1 MVV (no SAC training).

Goal: prove or refute "V3 env IEEEG1 vout 没接进 GENROU.Pm" hypothesis from
R08 finding (handoff `2026-05-07_andes_path_closure.md` Root #2).

Method (4 layer probe):
  L1  ss.IEEEG1.syn vs ss.GENROU.idx — does syn= field match?
  L2  IEEEG1 internal Pgv variable — does it move during LS1 disturbance?
  L3  GENROU.Pm trace — does it change with Pgv?
  L4  V2 (no gov) vs V3 (gov on) Pm trace diff — magnitude?

Verdict matrix:
  L1 fail              → wiring spec wrong (syn= field misuse)
  L1 ok, L2 fail       → IEEEG1 model not solving
  L1+L2 ok, L3 fail    → CONFIRM Root #2 hypothesis: Pgv → Pm not auto-linked
  L1+L2+L3 ok, L4 ~0   → Pm changes are tiny, governor effect masked
  All 4 layer pass     → wiring works, residual is platform-level (Root #3)

Run via WSL ANDES venv:
    /home/wya/andes_venv/bin/python scripts/research_loop/r10_governor_wiring_forensic.py

Output: results/research_loop/r10_governor_wiring_forensic.json + console.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from env.andes.andes_vsg_env_v2 import AndesMultiVSGEnvV2  # noqa: E402
from env.andes.andes_vsg_env_v3 import AndesMultiVSGEnvV3  # noqa: E402
from probes.andes_common import (  # noqa: E402
    introspect_model,
    safe_get as _safe_get,
    try_read_v,
)

LS1_DELTA_U = {"PQ_Bus14": -2.48}  # paper LS1 (per r08 reference)
PROBE_STEPS = 30  # ~3s at 100ms step
H_FORCED = 6.5    # Kundur Area1 H (paper anchor)


def inspect_static(env_cls, label: str) -> dict:
    """L1: static wiring inspection — no TDS run yet."""
    env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
    out: dict[str, Any] = {"label": label, "phase": "static"}
    try:
        ss = env._build_system()
        out["genrou_idx"] = list(ss.GENROU.idx.v) if _safe_get(ss, "GENROU") else []
        if _safe_get(ss, "IEEEG1"):
            ieeeg1 = ss.IEEEG1
            out["ieeeg1_idx"] = list(ieeeg1.idx.v) if _safe_get(ieeeg1, "idx") else []
            out["ieeeg1_n"] = ieeeg1.n if _safe_get(ieeeg1, "n") else 0
            syn = _safe_get(ieeeg1, "syn")
            if syn is not None:
                out["ieeeg1_syn"] = list(syn.v) if _safe_get(syn, "v") else None
            else:
                out["ieeeg1_syn"] = "NO_SYN_FIELD"
            # Probe IEEEG1 output candidate names
            for cand in ("pout", "Pgv", "Pmech", "tm", "PT", "Pout"):
                v = _safe_get(ieeeg1, cand)
                if v is not None:
                    out[f"ieeeg1_has_{cand}"] = True
        else:
            out["ieeeg1_n"] = 0
            out["note"] = "no IEEEG1 (V2 baseline)"
        # GENROU.Pm probe
        if _safe_get(ss, "GENROU"):
            pm = _safe_get(ss.GENROU, "Pm")
            out["genrou_has_Pm"] = pm is not None
            if pm is not None:
                # check dim, kind, source binding
                out["genrou_Pm_class"] = type(pm).__name__
                out["genrou_Pm_n"] = _safe_get(pm, "n")
        # ID match check
        if out.get("ieeeg1_syn") and out.get("genrou_idx"):
            syn_set = set(out["ieeeg1_syn"])
            gen_set = set(out["genrou_idx"])
            out["L1_pass"] = syn_set.issubset(gen_set) and len(syn_set) > 0
            out["syn_match"] = syn_set == gen_set
        else:
            out["L1_pass"] = False if env_cls is AndesMultiVSGEnvV3 else None
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
    finally:
        try:
            env.close()
        except Exception:
            pass
    return out


def trace_dynamic(env_cls, label: str) -> dict:
    """L2/L3/L4: dynamic Pgv + Pm trace under LS1 zero-action.

    Robust: tolerant to missing .v on some attrs; never crashes on empty arr.
    """
    out: dict[str, Any] = {"label": label, "phase": "dynamic"}
    PM_CAND = ("Pm", "tm", "Pe", "pm", "PMECH")
    GOV_CAND = ("pout", "Pgv", "Pmech", "tm", "PT", "pm")
    try:
        env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * H_FORCED)
        obs = env.reset(delta_u=LS1_DELTA_U)
        ss = env.ss

        # Introspect once for diagnostic
        out["genrou_introspect"] = introspect_model(ss, "GENROU")
        out["ieeeg1_introspect"] = introspect_model(ss, "IEEEG1")

        # DAE-active heuristic: count Algeb/State on IEEEG1.
        # 0 → model is parameter container, NOT in DAE (R10 finding for V3).
        DAE_KINDS = {"Algeb", "State", "ExtAlgeb", "ExtState"}
        ieeeg1_dae = sum(
            1 for v in out["ieeeg1_introspect"].get("readable_vars", [])
            if v.get("kind") in DAE_KINDS
        )
        genrou_dae = sum(
            1 for v in out["genrou_introspect"].get("readable_vars", [])
            if v.get("kind") in DAE_KINDS
        )
        out["ieeeg1_dae_count"] = ieeeg1_dae
        out["genrou_dae_count"] = genrou_dae
        out["ieeeg1_in_dae"] = bool(ieeeg1_dae > 0)

        # Try to read Pm and Pgv
        pm_attr, pm_t0 = try_read_v(_safe_get(ss, "GENROU"), PM_CAND)
        pgv_attr, pgv_t0 = try_read_v(_safe_get(ss, "IEEEG1"), GOV_CAND)
        out["pm_attr_used"] = pm_attr
        out["pgv_attr_used"] = pgv_attr
        out["pm_t0"] = pm_t0
        out["pgv_t0"] = pgv_t0

        pm_traj = []
        pgv_traj = []
        df_traj = []
        for step in range(PROBE_STEPS):
            actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
            try:
                obs, _, done, info = env.step(actions)
            except Exception as e:
                out["step_err"] = f"step {step}: {str(e)[:120]}"
                break
            if info.get("tds_failed"):
                out["tds_failed_step"] = step
                break
            if pm_attr is not None:
                v = getattr(getattr(ss, "GENROU"), pm_attr, None)
                if v is not None and _safe_get(v, "v") is not None:
                    pm_traj.append(list(np.asarray(v.v).copy()))
            if pgv_attr is not None:
                v = getattr(getattr(ss, "IEEEG1"), pgv_attr, None)
                if v is not None and _safe_get(v, "v") is not None:
                    pgv_traj.append(list(np.asarray(v.v).copy()))
            df_traj.append(float(np.max(np.abs(info["freq_hz"] - env.FN))))
            if done:
                break

        out["pm_traj_n"] = len(pm_traj)
        out["pgv_traj_n"] = len(pgv_traj)
        out["max_df_overall"] = float(max(df_traj)) if df_traj else None
        out["final_df"] = df_traj[-1] if df_traj else None

        if pm_traj and pm_t0:
            pm_arr = np.array(pm_traj)
            pm_t0_arr = np.array(pm_t0)
            if pm_arr.shape[1] == pm_t0_arr.size:
                pm_dev = np.abs(pm_arr - pm_t0_arr).max(axis=0)
                out["pm_max_dev_per_gen"] = pm_dev.tolist()
                out["pm_max_dev_overall"] = float(pm_dev.max())
                out["L3_pass"] = bool(pm_dev.max() > 1e-4)
        if pgv_traj and pgv_t0:
            pgv_arr = np.array(pgv_traj)
            pgv_t0_arr = np.array(pgv_t0)
            if pgv_arr.shape[1] == pgv_t0_arr.size:
                pgv_dev = np.abs(pgv_arr - pgv_t0_arr).max(axis=0)
                out["pgv_max_dev_per_gen"] = pgv_dev.tolist()
                out["pgv_max_dev_overall"] = float(pgv_dev.max())
                out["L2_pass"] = bool(pgv_dev.max() > 1e-4)
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
    finally:
        try:
            env.close()
        except Exception:
            pass
    return out


def main() -> int:
    results: dict[str, Any] = {
        "probe": "r10_governor_wiring_forensic",
        "ls": "LS1 PQ_Bus14 -2.48 sys_pu",
        "h_forced": H_FORCED,
        "steps": PROBE_STEPS,
    }

    print(f"=== R10 Governor Wiring Forensic (LS1, H={H_FORCED}, no SAC) ===\n")

    # L1 static
    print("[L1] Static wiring inspection ...")
    results["v2_static"] = inspect_static(AndesMultiVSGEnvV2, "V2_no_gov")
    results["v3_static"] = inspect_static(AndesMultiVSGEnvV3, "V3_gov_on")
    print(f"  V3 ieeeg1_n         = {results['v3_static'].get('ieeeg1_n')}")
    print(f"  V3 ieeeg1_syn       = {results['v3_static'].get('ieeeg1_syn')}")
    print(f"  V3 genrou_idx       = {results['v3_static'].get('genrou_idx')}")
    print(f"  V3 L1_pass          = {results['v3_static'].get('L1_pass')}")

    # L2/L3/L4 dynamic
    print("\n[L2/L3/L4] Dynamic Pgv + Pm trace under LS1 zero-action ...")
    results["v2_dyn"] = trace_dynamic(AndesMultiVSGEnvV2, "V2_no_gov")
    results["v3_dyn"] = trace_dynamic(AndesMultiVSGEnvV3, "V3_gov_on")

    v2 = results["v2_dyn"]
    v3 = results["v3_dyn"]
    print(f"  V2 max_df          = {v2.get('max_df_overall')}")
    print(f"  V3 max_df          = {v3.get('max_df_overall')}")
    print(f"  V2 pm_max_dev      = {v2.get('pm_max_dev_overall')}")
    print(f"  V3 pm_max_dev      = {v3.get('pm_max_dev_overall')}")
    print(f"  V3 pgv_max_dev     = {v3.get('pgv_max_dev_overall')} (attr={v3.get('pgv_attr_used')})")
    print(f"  V3 L2_pass (Pgv moves)   = {v3.get('L2_pass')}")
    print(f"  V3 L3_pass (Pm moves)    = {v3.get('L3_pass')}")

    if v2.get('pm_max_dev_overall') is not None and v3.get('pm_max_dev_overall') is not None:
        diff = abs(v3['pm_max_dev_overall'] - v2['pm_max_dev_overall'])
        results["L4_pm_dev_diff"] = float(diff)
        results["L4_pass"] = bool(diff > 1e-3)
        print(f"  L4_pass (V3 vs V2 Pm dev > 1e-3): {results['L4_pass']}  (diff={diff:.4e})")

    # Direct max_df comparison (the R08-style check, paper H=6.5)
    if v2.get("max_df_overall") and v3.get("max_df_overall"):
        gov_effect = abs(v3["max_df_overall"] - v2["max_df_overall"]) / v2["max_df_overall"]
        results["max_df_governor_effect_pct"] = float(gov_effect * 100)
        results["L0_max_df_pass"] = bool(gov_effect > 0.05)  # >5% diff = governor doing something
        print(f"  max_df governor effect: {gov_effect*100:.1f}% (V2 {v2['max_df_overall']:.3f} → V3 {v3['max_df_overall']:.3f})")

    # Final verdict
    L1 = results["v3_static"].get("L1_pass")
    L2 = v3.get("L2_pass")
    L3 = v3.get("L3_pass")
    L4 = results.get("L4_pass")
    L0 = results.get("L0_max_df_pass")

    # Promote DAE-active flag into verdict
    ieeeg1_in_dae = v3.get("ieeeg1_in_dae")
    ieeeg1_dae_count = v3.get("ieeeg1_dae_count")
    print(f"  ieeeg1 DAE-active (Algeb/State count > 0): {ieeeg1_in_dae} (count={ieeeg1_dae_count})")

    if L1 is False:
        verdict = "L1_FAIL — IEEEG1.syn does not match GENROU.idx"
    elif ieeeg1_in_dae is False and L0 is False:
        verdict = (
            f"DAE_INACTIVE — IEEEG1 added (n=4, syn matched) but 0 Algeb/State "
            f"in DAE. V3 max_df = V2 max_df ({v2.get('max_df_overall'):.13f}). "
            "ANDES did NOT integrate IEEEG1 into solver — confirm Root #2 升级."
        )
    elif L0 is False and L2 is None and L3 is None:
        verdict = "L0_FAIL — V3 max_df ≈ V2 max_df (governor invisible) AND Pgv/Pm fields not readable; Root #2 likely confirmed but introspection failed"
    elif L1 and L2 is False:
        verdict = "L2_FAIL — IEEEG1 internal Pgv frozen, governor model not solving"
    elif L1 and L2 and L3 is False:
        verdict = "L3_FAIL — Pgv moves but Pm frozen → CONFIRM Root #2: Pgv→Pm not auto-wired"
    elif L1 and L2 and L3 and (L4 is False):
        verdict = "L4_FAIL — Pm changes but tiny, governor effect ~0 (V3≈V2)"
    elif L1 and L2 and L3 and L4:
        verdict = "ALL_PASS — wiring works, residual is platform-level (Root #3)"
    elif L0 is True:
        verdict = "L0_GOVERNOR_VISIBLE — V3 max_df differs from V2 by " + f"{results.get('max_df_governor_effect_pct',0):.1f}%; ANDES governor does affect dynamics at H={H_FORCED}"
    else:
        verdict = "INCONCLUSIVE — see error/traceback fields"
    results["verdict"] = verdict
    print(f"\n=== Verdict: {verdict} ===")

    out_path = ROOT / "results" / "research_loop" / "r10_governor_wiring_forensic.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
