"""Audit: re-derive every plotted value from the sealed JSONs and verify it
against what the figure scripts assert. Also spot-check rendered PDF text.

This is a read-only verification; it never writes to the results JSONs.
"""

import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[4]
FIG = ROOT / "paper" / "decoupling_marl_model_first" / "figures"

fails = []


def check(name, cond, detail=""):
    status = "OK " if cond else "FAIL"
    print(f"  [{status}] {name} {detail}")
    if not cond:
        fails.append(name)


def load(p):
    with open(ROOT / p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def pdf_text(name):
    doc = fitz.open(FIG / name)
    return " ".join(page.get_text() for page in doc)


print("== fig3 (R312) ==")
r312 = load("results/r312_model_first_stage1/analysis.json")
pm = r312["pair_metrics"]
ratios = {p: pm[p]["cross_gain"] / pm[p]["self_gain"] * 100 for p in pm}
check("12 pairs", len(ratios) == 12)
check("min ratio 1.11%", abs(min(ratios.values()) - 1.1129) < 0.01)
check("max ratio 3.90%", abs(max(ratios.values()) - 3.8971) < 0.01)
check("max_all_nonlinearity_ratio",
      r312["max_all_nonlinearity_ratio"] == 0.0035181768548866567)
t3 = pdf_text("fig3_stage1_probes.pdf")
check("fig3 text has range", "1.11" in t3 and "3.90" in t3)

print("== fig4 (R344) ==")
exec_json = load("results/r344_deterministic_bridge/formal_execution.json")
analysis = load("results/r344_deterministic_bridge/formal_analysis.json")
recs = exec_json["records"]
by_scen = {}
for rec in recs:
    by_scen.setdefault(rec["scenario_id"], {})[rec["arm"]] = rec["metrics"]
check("32 records", len(recs) == 32)
check("16 scenarios", len(by_scen) == 16)
mz_c = sum(v["zero_control"]["common_coordinate_iae"] for v in by_scen.values()) / 16
mc_c = sum(v["frozen_controller"]["common_coordinate_iae"] for v in by_scen.values()) / 16
mz_d = sum(v["zero_control"]["differential_coordinate_energy"] for v in by_scen.values()) / 16
mc_d = sum(v["frozen_controller"]["differential_coordinate_energy"] for v in by_scen.values()) / 16
check("sealed common fraction", abs((mz_c - mc_c) / mz_c - analysis["paired_mean_improvement_fraction"]["common_coordinate_iae"]) < 1e-12)
check("sealed diff fraction", abs((mz_d - mc_d) / mz_d - analysis["paired_mean_improvement_fraction"]["differential_coordinate_energy"]) < 1e-12)
worst = max(v["frozen_controller"]["common_coordinate_iae"] / v["zero_control"]["common_coordinate_iae"] for v in by_scen.values())
check("no scenario worsens >5% (common)", worst <= 1.05)
worst_d = max(v["frozen_controller"]["differential_coordinate_energy"] / v["zero_control"]["differential_coordinate_energy"] for v in by_scen.values())
check("no scenario worsens >5% (diff)", worst_d <= 1.05)
check("guards pass", all(analysis["guards"].values()))
t4 = pdf_text("fig4_deterministic_bridge.pdf")
check("fig4 text has 5% no-harm", "5% no-harm" in t4)

print("== fig5 (R350, per-scenario oracle) ==")
r350 = load("results/r350_smooth_convex_residual/analysis.json")
o = r350["gates"]["oracle_nominal"]["endpoints"]
l = r350["gates"]["local_nominal"]["endpoints"]
oracle_recs = r350["oracle"]
check("16 oracle per-case records", len(oracle_recs) == 16)
frc = []
frd = []
for rec in oracle_recs:
    b = rec["base_endpoints"]
    n = rec["nominal_endpoints"]
    frc.append((b["common_coordinate_iae"] - n["common_coordinate_iae"]) / b["common_coordinate_iae"])
    frd.append((b["differential_coordinate_energy"] - n["differential_coordinate_energy"]) / b["differential_coordinate_energy"])
mean_c = sum(frc) / 16
mean_d = sum(frd) / 16
check("per-scenario mean-of-ratios common == sealed",
      abs(mean_c - o["common_coordinate_iae"]["mean_improvement_fraction"]) < 1e-12)
check("per-scenario mean-of-ratios diff == sealed",
      abs(mean_d - o["differential_coordinate_energy"]["mean_improvement_fraction"]) < 1e-12)
check("every scenario pins the 2% common bound",
      all(0.0199999 < v < 0.0200001 for v in frc))
shortfall = o["common_coordinate_iae"]["minimum_improvement_fraction"] - o["common_coordinate_iae"]["mean_improvement_fraction"]
check("shortfall ~1.7e-9", abs(shortfall - 1.736651072947737e-9) < 1e-18)
check("only PQ_Bus14 carries differential headroom",
      max(frd[i] for i in range(16) if "Bus14" in oracle_recs[i]["scenario_id"]) > 0.11
      and max(frd[i] for i in range(16) if "Bus14" not in oracle_recs[i]["scenario_id"]) < 0.021)
check("floor 2%", o["common_coordinate_iae"]["minimum_improvement_fraction"] == 0.02)
check("classification NO-TRAINING", r350["classification"] == "NO-TRAINING")
t5 = pdf_text("fig5_oracle_headroom.pdf")
check("fig5 text has 1.9999998", "1.9999998" in t5)
check("fig5 text has shortfall", "shortfall" in t5)

print("== fig6 (R359-R362; PDF retained but UNUSED - superseded by in-text Table II) ==")
def get_eps(run):
    d = load(run)
    dev = d["development"]
    if "family_gates" in dev:
        return {f: v["nominal"]["endpoints"] for f, v in dev["family_gates"].items()}
    return {"affine": dev["gates"]["nominal"]["endpoints"]}

exp = {
    ("R359", "affine"): (0.005031, 5.117733),
    ("R360", "knn"): (0.008859, 5.795724),
    ("R360", "quadratic_polynomial"): (0.011070, 36.925842),
    ("R360", "rbf_kernel_ridge"): (0.009217, 14.555536),
    ("R361", "affine"): (0.010582, 0.935514),
    ("R361", "knn"): (0.007934, 5.046776),
    ("R361", "quadratic_polynomial"): (-0.009523, 142.735105),
    ("R361", "rbf_kernel_ridge"): (0.010107, 19.804798),
    ("R362", "affine"): (0.006829, 3.778402),
    ("R362", "knn"): (0.012873, 4.849487),
    ("R362", "quadratic_polynomial"): (-0.000559, 672.933364),
    ("R362", "rbf_kernel_ridge"): (0.011476, 32.679510),
}
runs = {
    "R359": "results/r359_neighbour_causal_residual/analysis.json",
    "R360": "results/r360_flexible_neighbour_residual/analysis.json",
    "R361": "results/r361_neighbour_message_residual/analysis.json",
    "R362": "results/r362_shared_prediction_residual/analysis.json",
}
for (r, fam), (imp, worse) in exp.items():
    eps = get_eps(runs[r])
    pg_c = eps[fam]["common_coordinate_iae"]["paired_gate"]
    pg_d = eps[fam]["differential_coordinate_energy"]["paired_gate"]
    check(f"{r}/{fam} common imp", abs(pg_c["mean_improvement_fraction"] - imp) < 1e-4)
    check(f"{r}/{fam} diff worse", abs(pg_d["mean_signed_relative_change"] - worse) < 1e-3)
check("all gates fail", all(
    not eps[f]["common_coordinate_iae"]["paired_gate"]["pass"]
    for r in runs for eps in [get_eps(runs[r])] for f in eps))
t6 = pdf_text("fig6_family_gates.pdf")
check("fig6 text mentions missing R359 cells", "affine" in t6)

print("== fig7 (R356/R358/R363) ==")
r356 = load("results/r356_joint_endpoint_feasibility/analysis.json")
r358 = load("results/r358_physical_joint_endpoint_qp/analysis.json")
r363 = load("results/r363_common_channel_qp/analysis.json")
check("r356 10 optimal / 6 infeasible",
      r356["accepted_optimal_count"] == 10 and r356["accepted_primal_infeasible_count"] == 6)
check("r358 10 feasible", r358["accepted_physical_feasible_candidate_count"] == 10)
check("r358 6 inherited", r358["inherited_relaxed_infeasible_count"] == 6)
check("r363 16/16", r363["feasible_count"] == 16)
check("r363 baseline 10", r363["r358_baseline_feasible_count"] == 10)
check("r363 newly feasible 6", len(r363["newly_feasible_scenario_ids"]) == 6)
check("r363 headroom expanded", r363["headroom_expanded"] is True)
new6 = set(r363["newly_feasible_scenario_ids"])
check("newly == r358 inherited",
      new6 == set(r358["inherited_relaxed_infeasible_scenario_ids"]))
check("newly == r356 infeasible",
      new6 == {c["scenario_id"] for c in r356["development_results"]
               if c["status"] == "primal infeasible"})
t7 = pdf_text("fig7_common_channel.pdf")
check("fig7 text has 16/16", "16/16" in t7)

print()
if fails:
    print("FAILURES:", fails)
    sys.exit(1)
print("ALL AUDIT CHECKS PASSED")
