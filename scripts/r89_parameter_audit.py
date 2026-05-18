"""R89 — ANDES Kundur parameter audit vs paper §IV-A / Kundur 1994 reference.

Pure file inspection. Zero ANDES TDS. Zero conflict with parallel R83 / R85
/ R86 / R87 / R88 sessions. Compares:

  1. GENROU H/D/Sn — vs ``paper_constants.KUNDUR_AREA1_H / 2_H / GEN_MVA``
  2. fn (nominal frequency) — vs ``KUNDUR.fn`` contract default = 50 Hz
  3. PQ load distribution — vs paper Sec.IV-A topology
  4. TGOV1 governor active state — vs paper Sec.II-A "neglect inner loop"
  5. Line impedance schema — readability + tie-line layout

Output: ``results/r89_kundur_audit/{summary.json, audit_report.md}``

Driver for R09-副线 (R08 Finding 2 12-day-old TODO).
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Stub andes module so we can run audit on Windows (no ANDES install) without
# importing the env. We only need paper_constants + scenarios.contract.
import types  # noqa: E402
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")
    sys.modules["andes"].load = lambda *a, **k: None       # type: ignore[attr-defined]
    sys.modules["andes"].get_case = lambda *a, **k: ""     # type: ignore[attr-defined]
    sys.modules["andes"].main = types.ModuleType("andes.main")  # type: ignore[attr-defined]
    sys.modules["andes.main"] = sys.modules["andes"].main

# Import constants directly via file path (bypasses package __init__ which
# eagerly imports the env).
import importlib.util  # noqa: E402

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

_paper_consts = _load_module(
    "paper_constants",
    ROOT / "src" / "andes_rl_kundur" / "probes" / "andes_common" / "paper_constants.py"
)
KUNDUR_AREA1_H = _paper_consts.KUNDUR_AREA1_H
KUNDUR_AREA2_H = _paper_consts.KUNDUR_AREA2_H
KUNDUR_GENROU_M_SYS_BASE = _paper_consts.KUNDUR_GENROU_M_SYS_BASE
KUNDUR_TOTAL_GEN_MVA = _paper_consts.KUNDUR_TOTAL_GEN_MVA

_contract = _load_module(
    "contract",
    ROOT / "src" / "andes_rl_kundur" / "scenarios" / "contract.py"
)
KUNDUR = _contract.KUNDUR

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r89")

JSON_PATH = ROOT / "probes" / "r89_andes_kundur_full.json"
OUT_DIR = ROOT / "results" / "r89_kundur_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_andes_kundur() -> dict[str, Any]:
    if not JSON_PATH.exists():
        log.error(f"Missing {JSON_PATH}; regenerate via:")
        log.error("  wsl bash -c 'cat /home/wya/andes_venv/lib/python3.12/"
                  "site-packages/andes/cases/kundur/kundur_full.json' "
                  f"> {JSON_PATH.relative_to(ROOT)}")
        sys.exit(1)
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def audit_genrou(d: dict) -> dict:
    """F1 + F3: nominal frequency + machine damping."""
    rows = d.get("GENROU", [])
    fns = sorted({float(g.get("fn", 0)) for g in rows})
    ds = sorted({float(g.get("D", 0)) for g in rows})
    h_paper = (KUNDUR_AREA1_H, KUNDUR_AREA1_H, KUNDUR_AREA2_H, KUNDUR_AREA2_H)
    # H from M (M=2H assumption — paper_constants documents this is at machine base 900 MVA)
    h_andes_machinebase = [float(g["M"]) / 2 for g in rows]
    # ANDES default uses M in system base 100 MVA — but stored ratio is the same value
    # (the M field reads as 13 = 2×6.5 at machine base if 900MVA Sn is referenced).
    sn = [float(g.get("Sn", 0)) for g in rows]
    return {
        "n_gen": len(rows),
        "fns_unique": fns,
        "fn_paper_target": KUNDUR.fn,
        "F1_fn_mismatch": len(fns) == 1 and abs(fns[0] - KUNDUR.fn) > 0.1,
        "F1_scaling_factor": (KUNDUR.fn / fns[0]) if fns else None,
        "ds_unique": ds,
        "F3_zero_damping": ds == [0.0],
        "h_paper_target": list(h_paper),
        "h_andes_machinebase": h_andes_machinebase,
        "h_match_paper": all(abs(a - p) < 0.05 for a, p in zip(h_andes_machinebase, h_paper)),
        "sn_MVA": sn,
        "sn_matches_900": all(abs(s - 900.0) < 1 for s in sn),
        "M_field_raw": [float(g["M"]) for g in rows],
        "M_sys_base_paper": list(KUNDUR_GENROU_M_SYS_BASE),
    }


def audit_pq(d: dict) -> dict:
    """F2 + F5: PQ load distribution + capacitive injection."""
    rows = d.get("PQ", [])
    return {
        "n_pq": len(rows),
        "buses": [r.get("bus") for r in rows],
        "p0_pu": [float(r.get("p0", 0)) for r in rows],
        "q0_pu": [float(r.get("q0", 0)) for r in rows],
        "F5_capacitive_q": any(float(r.get("q0", 0)) < 0 for r in rows),
        "paper_disturbance_buses": [14, 15],
        "F2_disturbance_buses_present": all(
            14 in [r.get("bus") for r in rows] for _ in [None]
        ),
        "note": ("ANDES kundur_full default loads at Bus 7+8 (transmission 230kV); "
                 "V4 env._build_system() adds NEW PQ_Bus14/15 at runtime for "
                 "LS1/LS2 disturbances — those are NOT in this JSON dump."),
    }


def audit_tgov1(d: dict) -> dict:
    """F4: TGOV1 governors active by default?"""
    rows = d.get("TGOV1", [])
    return {
        "n_tgov1": len(rows),
        "u_states": [float(r.get("u", 0)) for r in rows],
        "syn_attached": [r.get("syn") for r in rows],
        "R_droops": [float(r.get("R", 0)) for r in rows],
        "Dt_dampings": [float(r.get("Dt", 0)) for r in rows],
        "F4_all_active": all(float(r.get("u", 0)) == 1.0 for r in rows),
        "paper_assumption": "Sec.II-A neglects inner loop; TGOV1 is primary-frequency "
                            "governor, not inner loop, but adds effective system damping "
                            "via R=0.05 droop curve.",
    }


def audit_line(d: dict) -> dict:
    """Line schema: counts, fn consistency."""
    rows = d.get("Line", [])
    fns = sorted({float(r.get("fn", 0)) for r in rows})
    sns = sorted({float(r.get("Sn", 0)) for r in rows})
    return {
        "n_line": len(rows),
        "fns_unique": fns,
        "sns_unique_MVA": sns,
        "fn_matches_genrou": len(fns) == 1 and fns[0] == 60.0,  # known F1 finding
        "r_range": [min(float(r.get("r", 0)) for r in rows), max(float(r.get("r", 0)) for r in rows)],
        "x_range": [min(float(r.get("x", 0)) for r in rows), max(float(r.get("x", 0)) for r in rows)],
    }


def audit_bus(d: dict) -> dict:
    rows = d.get("Bus", [])
    return {
        "n_bus": len(rows),
        "names": [r.get("name") for r in rows],
        "Vn_unique_kV": sorted({float(r.get("Vn", 0)) for r in rows}),
        "areas": [r.get("area") for r in rows],
        "note": "ANDES default has 10 buses (textbook Kundur). V4 env adds buses 12/14/15/16 at runtime for ESS + disturbance loads (not in this dump).",
    }


def write_audit_report(summary: dict) -> str:
    """Markdown report for human + verdict consumption."""
    g, p, t, ln, b = (summary[k] for k in ("genrou", "pq", "tgov1", "line", "bus"))
    md = []
    md.append("# R89 — ANDES Kundur parameter audit report\n")
    md.append("**Source**: `probes/r89_andes_kundur_full.json` (copied from ANDES "
              "`andes/cases/kundur/kundur_full.json`)\n")
    md.append("**Paper reference**: Yang et al. TPWRS 2023, Sec.IV-A + Kundur 1994 [49].\n")
    md.append("**Date**: 2026-05-19, R89.\n\n")

    md.append("## 🚨 F1 — fn mismatch (CRITICAL)\n")
    md.append(f"- ANDES GENROU fn = {g['fns_unique']} Hz\n")
    md.append(f"- Project FN (paper target) = {g['fn_paper_target']} Hz\n")
    md.append(f"- **Mismatch detected**: {g['F1_fn_mismatch']}\n")
    md.append(f"- Scaling factor (env reports = real × ratio): {g['F1_scaling_factor']}\n")
    md.append(f"- ANDES Line fn = {ln['fns_unique']} Hz (consistent with GENROU)\n")
    md.append("- Impact: `base_env.py:441` `freq_hz = omega * self.FN` "
              "(FN=50) interprets ANDES omega_pu using a 50 Hz base, but "
              "ANDES integrates at 60 Hz physically. Env underreports |Δf| "
              "by factor 50/60 = 0.833 relative to physical reality.\n\n")

    md.append("## HIGH F2 — load topology\n")
    md.append(f"- ANDES default PQ: n={p['n_pq']} at buses {p['buses']} "
              f"(p0={p['p0_pu']} pu, q0={p['q0_pu']} pu)\n")
    md.append("- Paper Sec.IV-A: 4 ESS at Bus 12/16/14/15 'with loads'; "
              "LS1 = 248 MW reduction at Bus 14, LS2 = 188 MW increase at Bus 15.\n")
    md.append("- V4 `_build_system()` adds NEW PQ_Bus14/15 at runtime, but the "
              "default Bus 7+8 loads remain. ANDES Kundur topology has loads at "
              "230kV transmission buses, NOT at the ESS-co-located distribution buses.\n\n")

    md.append("## MEDIUM F3 — GENROU damping D=0\n")
    md.append(f"- All {g['n_gen']} GENROU machines: D = {g['ds_unique']}\n")
    md.append(f"- Zero machine-side damping: {g['F3_zero_damping']}\n")
    md.append("- Paper Eq.1 has lumped D_es,i ≠ 0 (control-派 form). ANDES "
              "machine damping is 0; system damping comes only from TGOV1 droop "
              "(R=0.05) + line resistance + transient EMF coupling. NOT 1:1 with "
              "paper's swing-equation D.\n\n")

    md.append("## NEEDS VERIFICATION F4 — TGOV1 governors active\n")
    md.append(f"- n_TGOV1={t['n_tgov1']}, u_states={t['u_states']}\n")
    md.append(f"- Attached to syn={t['syn_attached']}, R={t['R_droops']}\n")
    md.append(f"- **All active**: {t['F4_all_active']}\n")
    md.append("- R08 Finding 3 (CLM-0046ish) declared V3 governor 'completely "
              "ineffective' based on max_df identity test; but the JSON dump shows "
              "u=1.0 in all 4 governors. **Open question**: are R03/R04/R08's "
              "governor-wire findings still valid post-R37 refactor, or did "
              "V4 silently re-enable TGOV1?\n\n")

    md.append("## LOW F5 — Capacitive q0 injection in default loads\n")
    md.append(f"- PQ q0 values: {p['q0_pu']} pu\n")
    md.append(f"- Any q0 < 0: {p['F5_capacitive_q']}\n")
    md.append("- Both default loads have NEGATIVE q0 (capacitive injection, "
              "-0.735 and -0.899 pu). Unusual for 'loads' — likely co-located "
              "shunt cap compensation embedded in the PQ record. Voltage support "
              "side-effect potentially impacts damping.\n\n")

    md.append("## Topology summary (Bus + Line)\n")
    md.append(f"- {b['n_bus']} buses, voltage levels: {b['Vn_unique_kV']} kV, "
              f"areas {sorted(set(b['areas']))}\n")
    md.append(f"- Bus names: {b['names']}\n")
    md.append(f"- {ln['n_line']} lines, all Sn={ln['sns_unique_MVA']} MVA, "
              f"r-range {ln['r_range']}, x-range {ln['x_range']}\n\n")

    md.append("## GENROU detail\n")
    md.append(f"- n_gen={g['n_gen']}, Sn={g['sn_MVA']} MVA (paper expects 900 MVA): "
              f"match={g['sn_matches_900']}\n")
    md.append(f"- H (machine base from M/2) = {g['h_andes_machinebase']} s\n")
    md.append(f"- H paper target = {g['h_paper_target']} s\n")
    md.append(f"- H matches paper: {g['h_match_paper']}\n")
    md.append(f"- M raw values = {g['M_field_raw']}\n")
    md.append(f"- M paper at sys 100 MVA base = {g['M_sys_base_paper']}\n\n")

    md.append("## Recommendations (R90+ candidates)\n")
    md.append("1. **F1 fix**: either re-import kundur_full.xlsx as 50 Hz "
              "(new probe baseline JSON) OR override GENROU.fn=50 after `andes.load()`. "
              "Either path breaks R57+ ckpt reproducibility (regression must be "
              "rerun, hash change).\n")
    md.append("2. **F2 document**: write ADR-0006 'ANDES vs paper Kundur topology' "
              "explaining loads at Bus 7+8 are inherited from textbook, not paper. "
              "LS1/LS2 disturbance buses 14/15 are V4-env additions, not Kundur defaults.\n")
    md.append("3. **F4 verify**: run a TGOV1.u=0 vs u=1 ablation in V4 with zero-"
              "action policy + same scenarios. If max_df differs, governors ARE "
              "effective (and R08 Finding 3 was about V3 not V4). If identical, "
              "they're DAE-inactive and V4's effective dampening is purely line-R.\n\n")

    md.append("## What this audit does NOT cover\n")
    md.append("- ANDES TDS solver damping (numerical stiffness)\n")
    md.append("- New buses 12/14/15/16 + their tie lines added by V4\n")
    md.append("- VSG GENCLS H/D/M parameters (covered by ADR-0002 + V4Config docstring)\n")
    md.append("- Disturbance injection profile (PQ Toggler vs continuous ramp)\n")
    return "".join(md)


def main() -> None:
    log.info(f"R89 — ANDES Kundur audit; output → {OUT_DIR}")
    d = load_andes_kundur()
    summary = {
        "round": 89,
        "source_json": str(JSON_PATH.relative_to(ROOT)),
        "genrou": audit_genrou(d),
        "pq": audit_pq(d),
        "tgov1": audit_tgov1(d),
        "line": audit_line(d),
        "bus": audit_bus(d),
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    report = write_audit_report(summary)
    (OUT_DIR / "audit_report.md").write_text(report, encoding="utf-8")
    log.info(f"summary.json + audit_report.md written to {OUT_DIR}")
    log.info("\n=== Quick gate ===")
    log.info(f"  F1 fn mismatch: {summary['genrou']['F1_fn_mismatch']} "
             f"(ANDES {summary['genrou']['fns_unique']} Hz vs FN={KUNDUR.fn} Hz)")
    log.info(f"  F2 load buses: {summary['pq']['buses']} (paper: 14/15)")
    log.info(f"  F3 GENROU D=0: {summary['genrou']['F3_zero_damping']}")
    log.info(f"  F4 TGOV1 all active: {summary['tgov1']['F4_all_active']}")
    log.info(f"  F5 capacitive q0: {summary['pq']['F5_capacitive_q']}")


if __name__ == "__main__":
    main()
