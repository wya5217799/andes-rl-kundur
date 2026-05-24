"""Multi-layer classification ladder resolver for ANDES forensic probes.

Pattern emerged across R10/R14/R15/R16: each probe has a classification matrix
where multiple gate flags (L0/L1/L2/L3/L4) collapse to ONE classification tag
("L1_FAIL — ...", "ROOT3_REAL — ...", "ALL_PASS").

Module name was previously ``verdict.py`` (R45 C4 rename, 2026-05-16) — the
name collided with the round ledger's ``memory/rounds/RNN/verdict.md`` first-
class entity. ``probe_classifier`` keeps the concept local to probes/.

Without this helper each probe re-implements the same chain of ``if elif elif``.
With it, define a classification ladder declaratively::

    from andes_rl_kundur.probes.andes_common.probe_classifier import (
        resolve_probe_ladder, ClassificationRule,
    )

    rules = [
        ClassificationRule("L1_FAIL", lambda r: r.get("L1_pass") is False,
                           "IEEEG1.syn does not match GENROU.idx"),
        ClassificationRule("DAE_INACTIVE",
                           lambda r: r.get("ieeeg1_in_dae") is False
                                     and r.get("L0_max_df_pass") is False,
                           "IEEEG1 added but 0 Algeb/State in DAE"),
        ClassificationRule("ALL_PASS", lambda r: True,
                           "wiring works, residual is platform-level"),
    ]
    classification = resolve_probe_ladder(probe_results, rules)

First matching rule wins. Final rule is typically a catch-all "ALL_PASS" or
"INCONCLUSIVE".
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProbeClassification:
    """One classification result with optional explanation + extras."""
    classification: str        # short tag, e.g. "ALL_PASS", "L1_FAIL", "ROOT3_REAL"
    explanation: str = ""      # human-readable reason
    extras: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.explanation:
            return f"{self.classification} — {self.explanation}"
        return self.classification


@dataclass(frozen=True)
class ClassificationRule:
    """One rung of the classification ladder.

    classification: tag to emit if predicate passes.
    predicate:      fn(probe_results: dict) -> bool. First True wins.
    explanation:    human reason. Can be a string or fn(results) -> string for
                    dynamic content (e.g. "max_df={x:.3f}").
    """
    classification: str
    predicate: Callable[[dict[str, Any]], bool]
    explanation: str | Callable[[dict[str, Any]], str] = ""


def resolve_probe_ladder(
    probe_results: dict[str, Any],
    rules: list[ClassificationRule],
    on_predicate_error: str = "warn",
) -> ProbeClassification:
    """Walk rules in order. First predicate that returns True wins.

    Args:
        on_predicate_error: ``"warn"`` (default) emits ``RuntimeWarning`` when
            a predicate raises (typo in `r.get("max_dff")` etc.) so it doesn't
            silently fall through to a catch-all rule. ``"raise"`` re-raises
            for strict CI use. ``"ignore"`` keeps R10-R17 historical behavior.

    Always pass a final catch-all rule (``predicate=lambda r: True``) so the
    resolver never returns INCONCLUSIVE silently. If no rule matches, returns
    ``ProbeClassification("INCONCLUSIVE", ...)``.
    """
    import warnings
    for rule in rules:
        try:
            ok = bool(rule.predicate(probe_results))
        except Exception as e:
            if on_predicate_error == "raise":
                raise
            if on_predicate_error == "warn":
                warnings.warn(
                    f"ClassificationRule predicate {rule.classification!r} raised "
                    f"{type(e).__name__}: {e}; treating as non-match. "
                    f"Fix the predicate.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            ok = False
        if not ok:
            continue
        if callable(rule.explanation):
            try:
                expl = rule.explanation(probe_results)
            except Exception:
                expl = ""
        else:
            expl = rule.explanation
        return ProbeClassification(rule.classification, expl)
    return ProbeClassification(
        "INCONCLUSIVE",
        "no classification rule matched; check probe outputs / add catch-all rule",
    )


# ─── Common classification ladder factories ─────────────────────────────────────


def governor_wiring_ladder() -> list[ClassificationRule]:
    """R10-style ladder for "is governor in DAE + does it affect dynamics".

    Expects probe_results with keys:
      L1_pass, ieeeg1_in_dae, L2_pass, L3_pass, L0_max_df_pass, L4_pass
    """
    return [
        ClassificationRule(
            "L1_FAIL",
            lambda r: r.get("L1_pass") is False,
            "IEEEG1.syn does not match GENROU.idx",
        ),
        ClassificationRule(
            "DAE_INACTIVE",
            lambda r: (r.get("ieeeg1_in_dae") is False
                       and r.get("L0_max_df_pass") is False),
            "IEEEG1 added but 0 Algeb/State in DAE — silent ss.setup() failure",
        ),
        ClassificationRule(
            "L2_FAIL",
            lambda r: r.get("L1_pass") and r.get("L2_pass") is False,
            "IEEEG1 internal Pgv frozen, governor model not solving",
        ),
        ClassificationRule(
            "L3_FAIL",
            lambda r: r.get("L2_pass") and r.get("L3_pass") is False,
            "Pgv moves but Pm frozen — Pgv→Pm not auto-wired",
        ),
        ClassificationRule(
            "L4_WEAK",
            lambda r: r.get("L3_pass") and r.get("L4_pass") is False,
            "Pm changes but tiny, governor effect ~0",
        ),
        ClassificationRule(
            "ALL_PASS",
            lambda r: r.get("L1_pass") and r.get("L4_pass") is True,
            "wiring works, residual (if any) is platform-level",
        ),
        ClassificationRule(
            "INCONCLUSIVE",
            lambda r: True,
            "see error/traceback fields",
        ),
    ]


def root3_residual_ladder(paper_max_df: float, max_df_key: str = "max_df") -> list[ClassificationRule]:
    """R14/R15/R16-style ladder for "is platform residual to paper level".

    Returns ROOT3_FAKE / ROOT3_PARTIAL / ROOT3_REAL based on best-variant ratio.

    Expects probe_results with key max_df_key (default "max_df").
    """
    def _ratio(r: dict) -> float:
        v = r.get(max_df_key)
        return (v / paper_max_df) if v else 999.0

    return [
        ClassificationRule(
            "ROOT3_FAKE",
            lambda r: _ratio(r) <= 1.3,
            lambda r: f"max_df {r.get(max_df_key, 0):.3f} ≈ paper {paper_max_df} ({_ratio(r):.2f}×)",
        ),
        ClassificationRule(
            "ROOT3_PARTIAL",
            lambda r: _ratio(r) <= 2.0,
            lambda r: f"max_df {r.get(max_df_key, 0):.3f}, {_ratio(r):.2f}× paper, partial fix",
        ),
        ClassificationRule(
            "ROOT3_REAL",
            lambda r: _ratio(r) <= 99.0,
            lambda r: f"max_df {r.get(max_df_key, 0):.3f}, {_ratio(r):.2f}× paper, real residual",
        ),
        ClassificationRule(
            "INCONCLUSIVE",
            lambda r: True,
            "max_df not measured",
        ),
    ]


__all__ = [
    "ProbeClassification",
    "ClassificationRule",
    "resolve_probe_ladder",
    "governor_wiring_ladder",
    "root3_residual_ladder",
]
