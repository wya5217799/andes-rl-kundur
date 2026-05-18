"""R80 Phase 0 probe — REGCA1/REECA1 wire check on Kundur 4-VSG topology.

RED expectation (this script declares the behavior contract V5 env must
satisfy *before* we write V5Config / V5 env scaffold):

    1.  ANDES 2.0.0 exposes REGCA1 + REECA1 models (model availability).
    2.  W2 wire (additive): adding a PV slot + REGCA1 + REECA1 to Bus 8
        produces a power-flow-converging system.
    3.  G4 wire (replacement): disabling the existing GENROU SG4 + adding
        REGCA1+REECA1 attached to G4's StaticGen slot @ Bus 11 still
        converges power flow.
    4.  Both together (additive + replacement on extended Kundur topology
        mirroring V4 `_build_system`) converges power flow.
    5.  TDS runs at least one step on the both-applied case.

GREEN means: every step above passes. Then we may write V5 scaffold.
RED on any step is recorded in JSON and gates Phase 1 OFF.

Output: probes/r80_regca1_wire_check.json
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import andes
from andes.utils.paths import get_case


PROBE_OUT = Path(__file__).resolve().parents[1] / "probes" / "r80_regca1_wire_check.json"

# V4 topology constants (mirrors andes_vsg_env_v4 hard-coded values; we
# do not import V4 to keep the probe self-contained — V4 is a hard-don't-
# touch asset).
VSG_BUSES = [12, 16, 14, 15]
NEW_BUS_CONNECTIONS = {12: 7, 16: 8, 14: 10, 15: 9}
NEW_LOADS = {14: {"p0": 2.48, "q0": 0.0}, 15: {"p0": 0.0, "q0": 0.0}}
NEW_BUS_VN = 230.0
VSG_SN = 200.0          # base_env default
VSG_M0 = 200.0
VSG_D0 = 100.0
WF2_BUS = 8
WF2_SN = 100.0
WF2_P0 = 1.0
# ANDES kundur_full.xlsx: G4 实际在 bus 4 (不是 paper 拓扑图的 bus 11)
# paper Fig.3 的 "Bus 11" 在 ANDES case 文件里编号是 4. V4 env 通过
# GENROU idx=4 直接操作 G4 inertia, 不绕 bus 编号. 探针修正一下.
G4_BUS = 4
G4_GENROU_IDX = 4       # ANDES kundur_full 里 G4 的 GENROU idx


def _build_extended_kundur():
    """Replay V4 topology mods (4 VSG + 2 disturbance loads, sans W2/G4)."""
    ss = andes.load(get_case("kundur/kundur_full.xlsx"), default_config=True, setup=False)

    for new_bus in VSG_BUSES:
        if new_bus not in list(ss.Bus.idx.v):
            ss.add("Bus", {
                "idx": new_bus, "name": f"Bus{new_bus}", "Vn": NEW_BUS_VN,
                "v0": 1.0, "a0": 0.0,
                "area": 1 if new_bus in (12, 16) else 2,
            })
    for new_bus, parent_bus in NEW_BUS_CONNECTIONS.items():
        ss.add("Line", {
            "idx": f"Line_{parent_bus}_{new_bus}", "bus1": parent_bus, "bus2": new_bus,
            "Vn1": NEW_BUS_VN, "Vn2": NEW_BUS_VN, "r": 0.002, "x": 0.20, "b": 0.0175,
        })
    for load_bus, lp in NEW_LOADS.items():
        ss.add("PQ", {
            "idx": f"PQ_Bus{load_bus}", "bus": load_bus,
            "Vn": NEW_BUS_VN, "p0": lp["p0"], "q0": lp["q0"],
        })
    # 4 VSG GENCLS (paper-faithful, unchanged in V5)
    for i, bus in enumerate(VSG_BUSES):
        vsg_id = f"VSG_{i+1}"
        gen_id = f"SG_VSG_{i+1}"
        ss.add("PV", {
            "idx": gen_id, "name": f"VSG{i+1}", "bus": bus,
            "Vn": NEW_BUS_VN, "Sn": VSG_SN, "p0": 0.5, "q0": 0.0,
            "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
        })
        ss.add("GENCLS", {
            "idx": vsg_id, "bus": bus, "gen": gen_id,
            "Vn": NEW_BUS_VN, "Sn": VSG_SN, "M": VSG_M0, "D": VSG_D0,
            "ra": 0.001, "xd1": 0.15,
        })
    return ss


def _add_w2_regca1(ss):
    """V5 W2 wire: REGCA1 (+REECA1) at Bus 8, replacing V4's GENCLS M=0.1."""
    ss.add("PV", {
        "idx": "SG_WF2", "name": "WF2_Bus8", "bus": WF2_BUS,
        "Vn": NEW_BUS_VN, "Sn": WF2_SN, "p0": WF2_P0, "q0": 0.0,
        "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
    })
    ss.add("REGCA1", {"idx": "WF2_R", "bus": WF2_BUS, "gen": "SG_WF2", "Sn": WF2_SN})
    ss.add("REECA1", {
        "idx": "WF2_E", "reg": "WF2_R",
        "PFFLAG": 0, "VFLAG": 0, "QFLAG": 0, "PFLAG": 0, "PQFLAG": 0,
    })


def _disable_g4_chain(ss):
    """V5 G4 wire (step 1): 把 G4 整条链 (GENROU + TGOV1 + EXDC2) 全 disable.

    R08 Finding 3 教训: 改一个模型不影响接它的链路, 不 disable governor 会
    TGOV1.LAG_y 卡 VMIN 限幅, init fail. 所以连同 syn=G4_GENROU_IDX 的
    TGOV1 / EXDC2 都 u=0.
    """
    disabled = {}
    if G4_GENROU_IDX in list(ss.GENROU.idx.v):
        ss.GENROU.set("u", G4_GENROU_IDX, 0, attr="v")
        disabled["GENROU"] = G4_GENROU_IDX
    # governor / AVR 链路: 任何 syn= G4_GENROU_IDX 的模型一起 disable
    for mname in ("TGOV1", "IEEEG1", "EXDC2", "EXST1", "IEEEX1", "SEXS"):
        if not hasattr(ss, mname):
            continue
        m = getattr(ss, mname)
        if m.n == 0 or not hasattr(m, "syn"):
            continue
        for i, syn_idx in enumerate(m.syn.v):
            if syn_idx == G4_GENROU_IDX:
                idx = m.idx.v[i]
                m.set("u", idx, 0, attr="v")
                disabled[mname] = idx
    return disabled


def _add_g4_regca1(ss):
    """V5 G4 wire (step 2): attach REGCA1+REECA1 to G4's StaticGen slot."""
    # Find the PV (or Slack) record at Bus 11 — this is G4's grid-side slot.
    g4_static_idx = None
    for i, b in enumerate(ss.PV.bus.v):
        if int(b) == G4_BUS:
            g4_static_idx = ss.PV.idx.v[i]
            break
    if g4_static_idx is None:
        for i, b in enumerate(ss.Slack.bus.v):
            if int(b) == G4_BUS:
                g4_static_idx = ss.Slack.idx.v[i]
                break
    if g4_static_idx is None:
        return None  # G4 has no static gen — caller decides
    # G4 nominal: 700 MW area-2 gen. Sn=900 in Kundur classic.
    ss.add("REGCA1", {"idx": "G4_R", "bus": G4_BUS, "gen": g4_static_idx, "Sn": 900.0})
    ss.add("REECA1", {
        "idx": "G4_E", "reg": "G4_R",
        "PFFLAG": 0, "VFLAG": 0, "QFLAG": 0, "PFLAG": 0, "PQFLAG": 0,
    })
    return g4_static_idx


def _try_pflow_and_tds(ss, label):
    """Setup + pflow + (if pflow OK) 1-step TDS. Return result dict."""
    rec = {"label": label, "setup": False, "pflow": False, "tds_1step": False,
           "n_buses": 0, "n_regca1": 0, "n_reeca1": 0, "n_genrou_active": 0,
           "n_gencls_active": 0, "max_freq_dev_pu": None, "error": None}
    try:
        ss.setup()
        rec["setup"] = True
        rec["n_buses"] = int(ss.Bus.n)
        rec["n_regca1"] = int(ss.REGCA1.n)
        rec["n_reeca1"] = int(ss.REECA1.n)
        rec["n_genrou_active"] = int(sum(int(u) for u in ss.GENROU.u.v))
        rec["n_gencls_active"] = int(sum(int(u) for u in ss.GENCLS.u.v))
        if hasattr(ss, "TGOV1") and ss.TGOV1.n > 0:
            rec["n_tgov1_active"] = int(sum(int(u) for u in ss.TGOV1.u.v))
        if hasattr(ss, "EXDC2") and ss.EXDC2.n > 0:
            rec["n_exdc2_active"] = int(sum(int(u) for u in ss.EXDC2.u.v))
        ok = ss.PFlow.run()
        rec["pflow"] = bool(ok)
        if ok:
            ss.TDS.config.tf = 0.05
            ok2 = ss.TDS.init()
            if ok2 is False:
                rec["error"] = "TDS.init returned False"
                return rec
            ss.TDS.run()
            rec["tds_1step"] = bool(ss.TDS.converged)
            # synchronous machine speeds (omega - 1) max abs
            omegas = []
            if ss.GENROU.n > 0:
                omegas.extend([float(o) for o in ss.GENROU.omega.v
                               if abs(o) > 1e-12])
            if ss.GENCLS.n > 0:
                omegas.extend([float(o) for o in ss.GENCLS.omega.v
                               if abs(o) > 1e-12])
            if omegas:
                rec["max_freq_dev_pu"] = max(abs(o - 1.0) for o in omegas)
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["traceback"] = traceback.format_exc().splitlines()[-6:]
    return rec


def main():
    PROBE_OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {"andes_version": andes.__version__, "experiments": []}

    # Exp 1 — model availability (via System instance, which is lazy-loaded)
    _ss = andes.System()
    avail = {
        "REGCA1_in_andes": hasattr(_ss, "REGCA1"),
        "REECA1_in_andes": hasattr(_ss, "REECA1"),
        "REPCA1_in_andes": hasattr(_ss, "REPCA1"),
    }
    out["model_availability"] = avail

    # Exp 2 — V4 baseline (extended Kundur + W2 GENCLS unchanged) — sanity
    ss0 = _build_extended_kundur()
    # add V4's GENCLS WF2 to make Exp2 actually a V4 plant baseline
    ss0.add("PV", {"idx": "SG_WF2", "name": "WF2_Bus8", "bus": WF2_BUS,
                   "Vn": NEW_BUS_VN, "Sn": WF2_SN, "p0": WF2_P0, "q0": 0.0,
                   "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0})
    ss0.add("GENCLS", {"idx": "WF2", "bus": WF2_BUS, "gen": "SG_WF2",
                       "Vn": NEW_BUS_VN, "Sn": WF2_SN, "M": 0.1, "D": 0.0,
                       "ra": 0.001, "xd1": 0.15})
    out["experiments"].append(_try_pflow_and_tds(ss0, "exp1_v4_baseline"))

    def _safe_exp(label, build_fn):
        try:
            ss, extra = build_fn()
            rec = _try_pflow_and_tds(ss, label)
            rec.update(extra)
        except Exception as e:
            rec = {"label": label, "setup": False, "pflow": False,
                   "tds_1step": False, "error": f"{type(e).__name__}: {e}",
                   "traceback": traceback.format_exc().splitlines()[-6:]}
        # Write JSON after each experiment so a crash doesn't wipe progress
        PROBE_OUT.write_text(json.dumps(out | {"experiments": out["experiments"] + [rec]},
                                        indent=2, default=str))
        out["experiments"].append(rec)
        return rec

    def _build_w2_only():
        ss = _build_extended_kundur()
        _add_w2_regca1(ss)
        return ss, {}

    def _build_g4_only():
        ss = _build_extended_kundur()
        ss.add("PV", {"idx": "SG_WF2", "name": "WF2_Bus8", "bus": WF2_BUS,
                      "Vn": NEW_BUS_VN, "Sn": WF2_SN, "p0": WF2_P0, "q0": 0.0,
                      "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0})
        ss.add("GENCLS", {"idx": "WF2", "bus": WF2_BUS, "gen": "SG_WF2",
                          "Vn": NEW_BUS_VN, "Sn": WF2_SN, "M": 0.1, "D": 0.0,
                          "ra": 0.001, "xd1": 0.15})
        g4_dis = _disable_g4_chain(ss)
        g4_static = _add_g4_regca1(ss)
        return ss, {"g4_genrou_disabled_idx": g4_dis,
                    "g4_static_slot_idx": g4_static}

    def _build_v5_target():
        ss = _build_extended_kundur()
        _add_w2_regca1(ss)
        g4_dis = _disable_g4_chain(ss)
        g4_static = _add_g4_regca1(ss)
        return ss, {"g4_genrou_disabled_idx": g4_dis,
                    "g4_static_slot_idx": g4_static}

    _safe_exp("exp2_w2_regca1_only", _build_w2_only)
    _safe_exp("exp3_g4_regca1_only", _build_g4_only)
    _safe_exp("exp4_v5_target_both", _build_v5_target)

    PROBE_OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    # Return-code: 0 if Exp5 (V5 target) tds_1step PASSES, else 1
    return 0 if out["experiments"][-1]["tds_1step"] else 1


if __name__ == "__main__":
    sys.exit(main())
