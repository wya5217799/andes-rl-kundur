"""Tests for the R78 final-eval contract (post-training auto-eval).

Pins two library functions:
  - ``pick_final_eval_suffix(save_dir, eval_tracked) -> str | None``
    The ckpt suffix-picker. Pure. Drives which ckpt the post-training
    dual-eval scores.
  - ``run_final_eval(save_dir, env_config, *, eval_tracked, score_seed_fn)``
    The orchestrator. Writes ``final_eval_summary.json`` on success or
    ``final_eval_error.txt`` on failure. **Must never re-raise** —
    training has already finished and the ckpt is on disk; an eval
    crash MUST NOT kill the process.

The orchestrator takes ``score_seed_fn`` as a dependency so tests can
inject stubs without ever loading ANDES / agents / TDS.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.final_eval import (  # noqa: E402
    pick_final_eval_suffix,
    run_final_eval,
)


def _touch_ckpt(save_dir: Path, suffix: str, n_agents: int = 4) -> None:
    """Create empty ``agent_<i>_<suffix>.pt`` files. Suffix existence
    is detected via ``agent_0_<suffix>.pt`` per train.py convention."""
    for i in range(n_agents):
        (save_dir / f"agent_{i}_{suffix}.pt").write_bytes(b"")


def test_pick_prefers_best_eval_when_eval_tracking_on(tmp_path: Path):
    """When eval-tracked training produced ``best_eval``, the picker
    chooses it over plain ``best`` — the eval-metric ckpt is the gold
    one (R61 Q-0007 design intent)."""
    _touch_ckpt(tmp_path, "best_eval")
    _touch_ckpt(tmp_path, "best")
    _touch_ckpt(tmp_path, "final")
    assert pick_final_eval_suffix(tmp_path, eval_tracked=True) == "best_eval"


def test_pick_ignores_best_eval_when_eval_tracking_off(tmp_path: Path):
    """``best_eval`` might exist as orphan from a prior run, but if the
    *current* training had ``--eval-every-n-eps=0``, the eval-tracked
    ckpt is meaningless for this run — fall through to ``best``."""
    _touch_ckpt(tmp_path, "best_eval")
    _touch_ckpt(tmp_path, "best")
    _touch_ckpt(tmp_path, "final")
    assert pick_final_eval_suffix(tmp_path, eval_tracked=False) == "best"


def test_pick_returns_best_when_only_best_exists(tmp_path: Path):
    """No ``best_eval`` on disk → ``best`` wins regardless of
    ``eval_tracked`` flag (typical case: ``--eval-every-n-eps=0``)."""
    _touch_ckpt(tmp_path, "best")
    _touch_ckpt(tmp_path, "final")
    assert pick_final_eval_suffix(tmp_path, eval_tracked=True) == "best"
    assert pick_final_eval_suffix(tmp_path, eval_tracked=False) == "best"


def test_pick_falls_back_to_final_when_only_final_exists(tmp_path: Path):
    """A short / interrupted training that never improved on the
    epoch-0 reward never wrote ``best.pt`` — fall back to ``final``
    (which `_save_checkpoint(actor_tag="final")` writes unconditionally
    after the loop)."""
    _touch_ckpt(tmp_path, "final")
    assert pick_final_eval_suffix(tmp_path, eval_tracked=False) == "final"


def test_pick_returns_none_when_no_ckpt(tmp_path: Path):
    """Empty save_dir → ``None`` (skip signal). This happens when
    training crashed before any ``_save_checkpoint`` call — final-eval
    must NOT raise FileNotFoundError. Caller skips the eval entirely."""
    assert pick_final_eval_suffix(tmp_path, eval_tracked=False) is None
    assert pick_final_eval_suffix(tmp_path, eval_tracked=True) is None


# ─── run_final_eval orchestrator ──────────────────────────────────────


_STUB_SUMMARY = {
    "LS1": 0.42, "LS2": 0.38, "geo": 0.40,
    "cum_rf": -0.99, "cum_rf_LS1": -0.50, "cum_rf_LS2": -0.49,
}


def test_run_final_eval_writes_summary_on_success(tmp_path: Path):
    """Happy path: ckpt present, score_seed succeeds → summary dict
    persisted to ``final_eval_summary.json``, function returns the same
    dict. score_seed receives the picked suffix."""
    _touch_ckpt(tmp_path, "best")

    captured_kwargs: dict = {}

    def stub_score_seed(ckpt_dir, **kwargs):
        captured_kwargs["ckpt_dir"] = ckpt_dir
        captured_kwargs.update(kwargs)
        return _STUB_SUMMARY

    result = run_final_eval(
        tmp_path, env_config=None,
        eval_tracked=False, score_seed_fn=stub_score_seed,
    )

    # 1. score_seed got called with the picked suffix and our save_dir
    assert captured_kwargs["ckpt_dir"] == tmp_path
    assert captured_kwargs["suffix"] == "best"

    # 2. summary dict is returned verbatim
    assert result == _STUB_SUMMARY

    # 3. final_eval_summary.json exists with the same payload
    summary_path = tmp_path / "final_eval_summary.json"
    assert summary_path.exists()
    import json
    assert json.loads(summary_path.read_text(encoding="utf-8")) == _STUB_SUMMARY

    # 4. no error file on success
    assert not (tmp_path / "final_eval_error.txt").exists()


def test_run_final_eval_swallows_failure_and_logs_to_error_txt(tmp_path: Path):
    """Load-bearing safety contract: an exception in ``score_seed`` must
    NOT propagate. Training has already finished and the ckpt is on disk;
    crashing the process here would obscure that the run actually
    succeeded. Failures are dumped to ``final_eval_error.txt`` so the
    user can re-run eval manually.
    """
    _touch_ckpt(tmp_path, "best")

    sentinel_msg = "ANDES TDS diverged at step 42"

    def stub_score_seed_that_explodes(ckpt_dir, **kwargs):
        raise RuntimeError(sentinel_msg)

    # MUST NOT raise. (Pytest fails the test if the call propagates.)
    result = run_final_eval(
        tmp_path, env_config=None,
        eval_tracked=False, score_seed_fn=stub_score_seed_that_explodes,
    )

    # 1. Returns None on failure (caller's skip / fallback signal).
    assert result is None

    # 2. No summary.json written.
    assert not (tmp_path / "final_eval_summary.json").exists()

    # 3. final_eval_error.txt exists and contains the failure message
    # + a stack trace (so the user has enough to triage).
    err_path = tmp_path / "final_eval_error.txt"
    assert err_path.exists()
    err_body = err_path.read_text(encoding="utf-8")
    assert sentinel_msg in err_body
    assert "Traceback" in err_body or "RuntimeError" in err_body


def test_run_final_eval_skips_when_no_ckpt(tmp_path: Path):
    """Empty save_dir → ``run_final_eval`` returns ``None`` WITHOUT
    calling score_seed and WITHOUT writing any sidecar file. This
    protects against weird states (training crashed pre-save) and keeps
    the failure surface narrow: ``no_ckpt`` is a distinct skip-condition,
    not a failure.
    """
    call_count = {"n": 0}

    def stub_score_seed_must_not_be_called(ckpt_dir, **kwargs):
        call_count["n"] += 1
        return _STUB_SUMMARY

    result = run_final_eval(
        tmp_path, env_config=None,
        eval_tracked=False, score_seed_fn=stub_score_seed_must_not_be_called,
    )

    # 1. Skip signal
    assert result is None

    # 2. score_seed was NOT invoked (the picker short-circuited).
    assert call_count["n"] == 0

    # 3. Neither sidecar exists. Skip ≠ failure.
    assert not (tmp_path / "final_eval_summary.json").exists()
    assert not (tmp_path / "final_eval_error.txt").exists()
