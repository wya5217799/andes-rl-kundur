"""Map external-theory observables to what a round's sealed data can supply.

Motivation (R422/R424/R432, external-theory intake rule 2026-08-19): the
GPT Pro A1/A2 answer demanded a 12-column per-arm/seed/profile diagnostic
table (lambda_eff, lambda clip, sum c_c, sum effort, eta_d^a, eta_d^phys,
chi_a, K_E/K_G, slew-active, saturation) to separate the four explanation
axes (physical modal routing / effective regularization / dual feasibility
/ value failure).  Those observables were never registered into any sealed
protocol, so they were re-tested late or by accident.  This probe turns
the theory's demanded observables into a per-round *gap table*: for each
observable it reports COMPUTED (derivable from the sealed summary),
NOT-APPLICABLE (no such mechanism in this bundle, e.g. no constraint
multiplier), or MISSING (the trace that would supply it was never saved,
with the required source named).  The MISSING rows are the machine form of
the ``## Theory intake`` observable list a future round must register.

This probe only reads sealed artifacts; it never writes results and never
edits the ledger.  Its output is advisory working notes for the next
round's plan (route to ``tmp/<line>/`` per the generated-document rules).

Usage::

    python probes/theory_observable_gap.py --results results/research_loop/r431_sac_slew
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The GPT Pro A1/A2 §3.2.3 / §5.3 observables, with the sealed-data field
# that would supply each one.  ``source_field`` names the summary location;
# ``trace_hint`` names a per-run trace file whose presence makes the
# observable computable when the summary field is absent.
OBSERVABLES = [
    {
        "name": "lambda_eff",
        "definition": "median/mean multiplier at actor updates",
        "summary_field": ("guard_multiplier_readout",),
        "trace_hint": ("multiplier_trace.json",),
    },
    {
        "name": "lambda_clip_fraction",
        "definition": "fraction of updates clipped at 0 / ceiling",
        "summary_field": ("guard_multiplier_readout",),
        "trace_hint": ("multiplier_trace.json",),
    },
    {
        "name": "sum_c_c",
        "definition": "episode common-cost sum (Σ_t c_c)",
        "summary_field": (),
        "trace_hint": ("cost_trace.json", "episode_cost_trace.json"),
    },
    {
        "name": "sum_effort",
        "definition": "episode executed-action energy sum (Σ_t mean_j a_ij^2)",
        "summary_field": (),
        "trace_hint": ("cost_trace.json", "action_energy_trace.json"),
    },
    {
        "name": "eta_d_a",
        "definition": "differential modal fraction of executed actions",
        "summary_field": (),
        "trace_hint": ("action_trace.json", "executed_action_trace.json"),
    },
    {
        "name": "eta_d_phys",
        "definition": "differential fraction of equivalent physical forcing",
        "summary_field": (),
        "trace_hint": ("state_action_trace.json", "physical_trace.json"),
    },
    {
        "name": "chi_a",
        "definition": "coefficient-to-action response proxy",
        "summary_field": (),
        "trace_hint": ("multiplier_trace.json", "action_trace.json"),
    },
    {
        "name": "K_E_K_G",
        "definition": "plant sensitivity of endpoints / no-harm guards",
        "summary_field": (),
        "trace_hint": ("jacobian.json", "small_signal.json"),
    },
    {
        "name": "slew_active",
        "definition": "fraction of steps the slew projector binds",
        "summary_field": ("b1_table", "slew_diagnostics"),
        "trace_hint": (),
    },
    {
        "name": "saturation",
        "definition": "action/decoded saturation fraction",
        "summary_field": ("b1_table", "slew_diagnostics"),
        "trace_hint": (),
    },
]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _nested_nonempty(doc: dict, keys: tuple[str, ...]) -> bool:
    """True when the key path exists AND holds a non-empty container.

    An empty key path or an empty dict/list is NOT "data present": the
    summary field may exist but carry nothing (e.g. an empty
    ``guard_multiplier_readout`` means the bundle has no constraint
    multiplier), which must not read as COMPUTED.
    """
    if not keys:
        return False
    cur = doc
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return False
        cur = cur[k]
    return isinstance(cur, (dict, list)) and bool(cur)


def _multiplier_populated(analysis: dict | None) -> bool:
    """True when guard_multiplier_readout has at least one non-empty arm."""
    readout = (analysis or {}).get("guard_multiplier_readout", {})
    if not isinstance(readout, dict):
        return False
    return any(isinstance(v, dict) and bool(v) for v in readout.values())


def _trace_files(manifest: dict | None) -> set[str]:
    """Collect the basenames of every training-run trace in the manifest."""
    names: set[str] = set()
    if not manifest:
        return names
    for group in ("checkpoint_artifacts", "input_artifacts"):
        for item in manifest.get(group, []) or []:
            p = item.get("path", "")
            if isinstance(p, str):
                names.add(Path(p).name)
    return names


# Observables whose only supplier is the constraint multiplier.  When the
# bundle's guard_multiplier_readout is present but empty, they are
# NOT-APPLICABLE (no constraint term) rather than MISSING.
_MULTIPLIER_OBSERVABLES = {"lambda_eff", "lambda_clip_fraction", "chi_a"}


def gap_table(results_dir: Path) -> dict:
    analysis = _read_json(results_dir / "formal_analysis.json")
    manifest = _read_json(results_dir / "formal_manifest.json")
    traces = _trace_files(manifest)

    rows = []
    for obs in OBSERVABLES:
        status = "MISSING"
        supplied: list[str] = []
        if obs["name"] in _MULTIPLIER_OBSERVABLES:
            # Multiplier observables read only the constraint multiplier;
            # a present-but-empty readout means no constraint term.
            if _multiplier_populated(analysis):
                status = "COMPUTED"
                supplied = ["guard_multiplier_readout"]
            elif analysis is not None and "guard_multiplier_readout" in analysis:
                status = "NOT-APPLICABLE"
        elif (
            obs["summary_field"]
            and analysis is not None
            and _nested_nonempty(analysis, obs["summary_field"])
        ):
            status = "COMPUTED"
            supplied = list(obs["summary_field"])
        elif any(h in traces for h in obs["trace_hint"]):
            status = "COMPUTED"
            supplied = [h for h in obs["trace_hint"] if h in traces]
        rows.append(
            {
                "observable": obs["name"],
                "status": status,
                "definition": obs["definition"],
                "supplied_by": supplied,
            }
        )
    return {
        "round": analysis.get("round") if analysis else None,
        "observables": rows,
        "summary": {
            "computed": sum(r["status"] == "COMPUTED" for r in rows),
            "not_applicable": sum(r["status"] == "NOT-APPLICABLE" for r in rows),
            "missing": sum(r["status"] == "MISSING" for r in rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--results", required=True,
        help="path to a round's results dir (e.g. results/research_loop/r431_sac_slew)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="emit JSON instead of a readable table",
    )
    args = parser.parse_args()

    results_dir = Path(args.results)
    if not (results_dir / "formal_analysis.json").exists():
        print(f"NO-RESULTS: {results_dir / 'formal_analysis.json'} missing")
        return 1

    table = gap_table(results_dir)
    if args.as_json:
        print(json.dumps(table, indent=2, ensure_ascii=False))
        return 0

    print(f"# Theory observable gap table — {table['round']}")
    for r in table["observables"]:
        src = ", ".join(r["supplied_by"]) or "-"
        print(
            f"{r['status']:<14} {r['observable']:<22} "
            f"[{src}] {r['definition']}"
        )
    s = table["summary"]
    print(
        f"\nsummary: {s['computed']} computed, "
        f"{s['not_applicable']} not-applicable, {s['missing']} missing"
    )
    if s["missing"]:
        print(
            "missing rows name the trace a future round must register as a "
            "frozen observable (## Theory intake)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
