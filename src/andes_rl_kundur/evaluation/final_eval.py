"""Post-training auto-eval orchestration (R78 → library).

Two public functions:

- ``pick_final_eval_suffix(save_dir, eval_tracked)`` — pure ckpt
  suffix-picker. Preference: ``best_eval`` (R61 paper-metric tracked)
  > ``best`` (train-reward tracked) > ``final`` (last episode).
- ``run_final_eval(save_dir, env_config, *, eval_tracked, score_seed_fn)``
  — orchestrator. Calls ``score_seed_fn``, writes
  ``final_eval_summary.json`` on success or ``final_eval_error.txt``
  on failure, and **never re-raises**.

Originally lived as ``_pick_final_eval_suffix`` /  ``_run_final_eval``
in ``scripts/train.py``; promoted to library in R79 so the contract is
testable without a sys.path hack into ``scripts/``.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from andes_rl_kundur.env.andes.v4_config import V4Config


SummaryDict = dict[str, float | None]
ScoreSeedFn = Callable[..., SummaryDict]


def pick_final_eval_suffix(save_dir: Path, eval_tracked: bool) -> str | None:
    """Pick which ckpt suffix to evaluate at training end.

    Preference: ``best_eval`` (R61 Q-0007, paper-metric tracked) > ``best``
    (train-reward tracked) > ``final`` (last episode). The ``best_eval``
    branch is only consulted when ``eval_tracked=True`` because that ckpt
    only exists when the user opted into the in-training eval probe
    (``--eval-every-n-eps > 0``).

    Returns ``None`` when no ckpt is on disk — caller should skip eval.
    """
    if eval_tracked and (save_dir / "agent_0_best_eval.pt").exists():
        return "best_eval"
    if (save_dir / "agent_0_best.pt").exists():
        return "best"
    if (save_dir / "agent_0_final.pt").exists():
        return "final"
    return None


def _default_score_seed(*args: Any, **kwargs: Any) -> SummaryDict:
    """Lazy thunk to the real ``score_seed`` (delays the ANDES-pulling
    import to call time, keeps the library importable on Windows)."""
    from andes_rl_kundur.evaluation.score_seed import score_seed
    return score_seed(*args, **kwargs)


def run_final_eval(
    save_dir: Path,
    env_config: V4Config | None,
    *,
    eval_tracked: bool,
    score_seed_fn: ScoreSeedFn = _default_score_seed,
) -> SummaryDict | None:
    """Run post-training dual-eval and persist the summary.

    Resolves the ckpt suffix via :func:`pick_final_eval_suffix`, calls
    ``score_seed_fn``, and writes ``<save_dir>/final_eval_summary.json``
    on success. Returns the summary dict (same content as the file).

    Returns ``None`` and writes nothing when no ckpt is on disk.

    Never re-raises: any exception from ``score_seed_fn`` is captured
    into ``<save_dir>/final_eval_error.txt`` so a failed eval does NOT
    propagate to the training process (the ckpt is already saved).

    The ``score_seed_fn`` parameter is dependency injection for tests —
    real callers leave it default and the real ``score_seed`` is used.
    """
    suffix = pick_final_eval_suffix(save_dir, eval_tracked=eval_tracked)
    if suffix is None:
        return None

    label = f"final_eval_{save_dir.name}"
    try:
        summary = score_seed_fn(
            save_dir,
            label=label,
            out_dir=save_dir / "final_eval",
            suffix=suffix,
            seed=42,
            steps=150,
            config=env_config,
        )
    except Exception as exc:
        # Load-bearing safety: training already succeeded and the ckpt is
        # on disk. Do NOT propagate — dump enough triage info and bail.
        import traceback
        err_path = save_dir / "final_eval_error.txt"
        err_path.write_text(
            f"Final dual-eval failed:\n{exc}\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        return None

    summary_path = save_dir / "final_eval_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
