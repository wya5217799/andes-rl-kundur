"""Canonical post-run dual-eval helper (R78).

Given the per-scenario trace JSONs produced by ``paper_path.run_scenario``,
compute the canonical post-training summary:

  - **Paper test** (paper §IV-C global ``cum_rf``) via ``compute_global_cum_rf``
  - **6-axis test** (project 11-axis geo) via ``paper_grade_axes.evaluate_trace``
    + floored geo-mean across LS1+LS2

Used by every eval entry (``score_run.score_seed``, ``eval_ddic``,
``eval_ensemble``, ``eval_all_seeds``, and ``train.py --final-eval``) so
no caller forgets the canonical paper metric. Single source of truth for
"what does *evaluating a controller* mean for this project".

Inputs are trace JSON **files on disk** (not in-memory dicts) because
``paper_grade_axes.evaluate_trace`` reads the file path and also auto-
locates the sibling ``no_control_<scenario>.json`` reference for axis 8.
Eval scripts always write traces to disk anyway (for downstream plotting
+ re-scoring), so passing the path is the natural API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from andes_rl_kundur.evaluation.aggregation import floor_geo_mean
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf


def score_trace_files(
    trace_paths: dict[str, Path],
    *,
    label: str,
    is_ddic: bool = True,
) -> dict[str, float | None]:
    """Compute paper-metric + 6-axis summary from a set of trace JSON files.

    Args:
        trace_paths: ``{scenario_name: path_to_trace_json}``. Only scenarios
            with a benchmark in ``paper_grade_axes.PAPER`` are scored
            (currently ``load_step_1`` + ``load_step_2``). Extra entries
            are silently ignored.
        label: Controller label passed through to ``evaluate_trace`` for
            axis 8 (improvement-vs-no-ctrl) reference-trace lookup.
        is_ddic: ``True`` for DDIC controllers (full 11-axis). ``False``
            for no-control baseline (axes 6-11 collapse to 0 — see
            ``paper_grade_axes`` docstring).

    Returns:
        Dict with these keys (all ``None`` if no scenarios scored):
            - ``LS1``: 11-axis overall for ``load_step_1``
            - ``LS2``: 11-axis overall for ``load_step_2``
            - ``geo``: ``floor_geo_mean([LS1, LS2])`` — the headline 6-axis number
            - ``cum_rf``: ``compute_global_cum_rf`` summed across scenarios
              (matches the ``_r58_paper_strict_eval`` convention)
            - ``cum_rf_LS1``: per-scenario paper §IV-C cum_rf
            - ``cum_rf_LS2``: per-scenario paper §IV-C cum_rf

        Missing scenarios produce ``None`` in their slots; the ``geo`` /
        ``cum_rf`` aggregates skip them rather than crashing.

    Notes:
        ``evaluate_trace`` reads the trace file from disk. ``cum_rf`` is
        computed from the same JSON re-loaded here, so callers don't need
        to keep the in-memory trace dict.

        Failed or explicitly incomplete traces raise ``ValueError``.  A
        partial cumulative reward can look artificially good, so silently
        converting such a trajectory into a headline score is unsafe.
    """
    per_scen_geo: dict[str, float] = {}
    per_scen_cum_rf: dict[str, float] = {}

    for scen_name, trace_path in trace_paths.items():
        if scen_name not in PAPER:
            continue  # only score paper-anchor scenarios

        with open(trace_path, encoding="utf-8") as f:
            trace = json.load(f)
        if trace.get("tds_failed") is True:
            raise ValueError(
                f"Refusing to score {trace_path}: tds_failed=True"
            )
        if trace.get("completed") is False:
            raise ValueError(
                f"Refusing to score {trace_path}: completed=False"
            )
        traces = trace.get("traces")
        if not traces:
            raise ValueError(
                f"Refusing to score {trace_path}: trace is empty"
            )
        if "n_steps" in trace and int(trace["n_steps"]) != len(traces):
            raise ValueError(
                f"Refusing to score {trace_path}: n_steps={trace['n_steps']} "
                f"but len(traces)={len(traces)}"
            )

        ts = evaluate_trace(trace_path, PAPER[scen_name], is_ddic=is_ddic, label=label)
        per_scen_geo[scen_name] = ts.overall
        per_scen_cum_rf[scen_name] = compute_global_cum_rf(trace)

    geo = floor_geo_mean(per_scen_geo.values()) if per_scen_geo else None
    cum_rf_total = sum(per_scen_cum_rf.values()) if per_scen_cum_rf else None

    return {
        "LS1": per_scen_geo.get("load_step_1"),
        "LS2": per_scen_geo.get("load_step_2"),
        "geo": geo,
        "cum_rf": cum_rf_total,
        "cum_rf_LS1": per_scen_cum_rf.get("load_step_1"),
        "cum_rf_LS2": per_scen_cum_rf.get("load_step_2"),
    }


def format_headline(summary: dict[str, Any]) -> str:
    """Format a single-line summary headline for CLI output.

    Caller is responsible for the label prefix. Returns a string like
    ``geo=0.4099 cum_rf=-1.2345 (LS1=0.41/-0.62 LS2=0.41/-0.61)``.
    """
    def _fmt(v: float | None, prec: int = 4) -> str:
        return f"{v:.{prec}f}" if v is not None else "--"

    return (
        f"geo={_fmt(summary['geo'])} "
        f"cum_rf={_fmt(summary['cum_rf'])} "
        f"(LS1={_fmt(summary['LS1'])}/{_fmt(summary['cum_rf_LS1'])} "
        f"LS2={_fmt(summary['LS2'])}/{_fmt(summary['cum_rf_LS2'])})"
    )
