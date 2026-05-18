"""End-to-end single-ckpt scoring (R78 library promotion).

Was previously ``scripts/score_run.score_seed`` (introduced R50). Moved
into the library so ``scripts/train.py`` can call it after training
without a cross-script import. The CLI wrapper in ``scripts/score_run.py``
now re-exports this function.

Pipeline: load actors → run LS1+LS2 scenarios → write trace JSONs →
delegate to ``summary.score_trace_files`` for the canonical paper-metric
+ 11-axis dual-eval.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from andes_rl_kundur.env.andes.v4_config import V4Config


def score_seed(
    ckpt_dir: Path,
    *,
    label: str,
    out_dir: Path,
    suffix: str = "best",
    seed: int = 42,
    steps: int = 150,
    config: "V4Config | None" = None,
) -> dict[str, float | None]:
    """Run one ckpt's actors across the paper scenarios and return the
    canonical dual-eval summary (paper §IV-C cum_rf + 11-axis geo).

    Heavy: imports ANDES via the env, runs TDS for each scenario.
    Returns the ``score_trace_files`` dict — see that function for the
    full key list. Trace JSONs are written under ``out_dir`` with the
    standard ``<label>_<scenario>.json`` naming so paper_grade_axes can
    re-score later.

    Args:
        ckpt_dir: Directory holding ``agent_{0..3}_<suffix>.pt``.
        label: Controller label used in trace filenames + axis-8 lookup.
        out_dir: Where to write the per-scenario trace JSONs.
        suffix: ``best`` / ``best_eval`` / ``final`` / ``ep<N>``.
        seed: Env seed (default 42, matches paper).
        steps: Episode length per scenario (default 150 = 30s @ DT=0.2).
        config: Optional V4Config override; defaults to paper-faithful.
    """
    # Library-level imports kept inside the function so importing this
    # module does NOT pull ANDES on Windows-side (where `andes` is not
    # installed by design — see docs/eng-notes/NOTES_ANDES.md).
    from andes_rl_kundur.agents.checkpoint_loader import load_agents
    from andes_rl_kundur.evaluation.paper_path import (
        deterministic_actor_action_fn, run_scenario,
    )
    from andes_rl_kundur.evaluation.summary import score_trace_files
    from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS

    out_dir.mkdir(parents=True, exist_ok=True)
    agents = load_agents(ckpt_dir, suffix=suffix)
    action_fn = deterministic_actor_action_fn(agents)

    trace_paths: dict[str, Path] = {}
    for scen_name, delta_u in SCENARIOS.items():
        rec = run_scenario(
            scen_name, delta_u,
            action_fn=action_fn,
            label=label, seed=seed, steps=steps,
            config=config,
        )
        out_path = out_dir / f"{label}_{scen_name}.json"
        out_path.write_text(json.dumps(rec), encoding="utf-8")
        trace_paths[scen_name] = out_path

    return score_trace_files(trace_paths, label=label, is_ddic=True)
