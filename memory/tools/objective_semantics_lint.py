"""Objective-semantics lint: verify rounds that modify the training objective.

Motivation (R424 sign-defect lesson, 2026-08-18): the R424 guard-aligned
constraint terms entered the actor loss inside the negated mean, turning
the intended penalties into rewards for action stress.  The defect passed
every mechanical gate (directed tests checked existence/finiteness/wiring,
the rehearsal checked hashes/absence/finiteness, the seal hashed bytes) —
none of them asked whether the new mechanism pushes in the direction the
plan intends.  The codified gate (skills/kundur-round/SKILL.md section 2,
target semantics gate) requires objective-modifying rounds to (a) declare
the marker in the plan's Formal launch contract rehearsal_checks, (b) run
a semantics probe on the real learner during rehearsal, and (c) keep the
probe values in the rehearsal JSON.

Two probe forms are recognised (additive; a round declares exactly one):

- ``penalty_direction_probe`` (R425 form): the constraint terms must
  DESCEND on the executed-action statistics (rms/tv dots > 0, the
  defect-form contrast < 0).
- ``normalization_semantics_probe`` (R427 form): a critic/normalization
  change must be an exact positive rescale with the untouched channel
  verbatim: output-correction identity ok, common target bitwise
  untouched, differential gradient dot > 0 with the decomposition ok,
  and the stats EMA convergence ok.

Usage::

    python memory/tools/objective_semantics_lint.py R<N>

Exit codes: 0 = pass (or not applicable); 1 = violation.  Failure modes:
the round's plan or rehearsal is missing (reports pending), the marker is
declared but the rehearsal carries no valid probe record, or the probe
values contradict the declared semantics.  The tool only reads; it never
edits the ledger.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MARKER = "penalty_direction_probe"
NORMALIZATION_MARKER = "normalization_semantics_probe"
SAC_MARKER = "sac_semantics_probe"
OBJECTIVE_HINT = re.compile(
    r"loss|objective|reward|penalty|constraint|惩罚|奖励|约束项", re.IGNORECASE
)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _lint_normalization_probe(round_id: str, probe: dict) -> int:
    identity = probe.get("output_correction_identity")
    common = probe.get("common_target_untouched")
    stats = probe.get("stats_convergence")
    dot = float(probe.get("differential_gradient_dot", float("nan")))
    decomposition = bool(
        probe.get("differential_gradient_decomposition_ok", False)
    )
    identity_ok = isinstance(identity, dict) and bool(identity.get("ok"))
    common_ok = isinstance(common, dict) and bool(common.get("ok"))
    stats_ok = isinstance(stats, dict) and bool(stats.get("ok"))
    if identity_ok and common_ok and stats_ok and dot > 0.0 and decomposition:
        print(
            f"[{round_id}] OK: normalization probe valid "
            f"(identity_ok={identity_ok}, common_ok={common_ok}, "
            f"grad_dot={dot:.3e}, decomposition_ok={decomposition}, "
            f"stats_ok={stats_ok})"
        )
        return 0
    print(
        f"[{round_id}] VIOLATION: normalization probe invalid "
        f"(identity_ok={identity_ok}, common_ok={common_ok}, "
        f"grad_dot={dot:.3e}, decomposition_ok={decomposition}, "
        f"stats_ok={stats_ok}); expected identity/common/stats ok, "
        f"gradient dot > 0 (positive rescale, no sign flip), and the "
        f"decomposition exact"
    )
    return 1


def _lint_sac_probe(round_id: str, probe: dict) -> int:
    required = {
        "critic_target_identity_ok",
        "actor_loss_form_ok",
        "alpha_loss_form_ok",
        "reward_nonpositive_ok",
        "reward_obs_consistent_ok",
    }
    missing = [k for k in sorted(required) if not bool(probe.get(k, False))]
    if not missing:
        print(
            f"[{round_id}] OK: SAC probe valid (critic-target, actor-form, "
            f"alpha-form, reward non-positive/obs-consistent all ok)"
        )
        return 0
    print(
        f"[{round_id}] VIOLATION: SAC probe invalid — missing/False: "
        f"{', '.join(missing)}; expected all five semantics checks true "
        f"(Eq.21 target identity, Eq.22 actor form, Eq.23 alpha form, "
        f"non-positive Eq.14-18 reward rebuilt from the obs row)"
    )
    return 1


def lint(round_id: str) -> int:
    plan_path = ROOT / "memory" / "rounds" / round_id / "plan.md"
    rehearsal_path = ROOT / "memory" / "rounds" / round_id / "rehearsal.json"
    plan_text = _read_text(plan_path)
    if plan_text is None:
        print(f"[{round_id}] NO-PLAN: {plan_path} unreadable or missing")
        return 1
    declares_penalty = MARKER in plan_text
    declares_normalization = NORMALIZATION_MARKER in plan_text
    declares_sac = SAC_MARKER in plan_text
    declares_gate = declares_penalty or declares_normalization or declares_sac
    if not declares_gate:
        if OBJECTIVE_HINT.search(plan_text):
            print(
                f"[{round_id}] HINT: plan mentions objective/loss/constraint "
                f"terms but declares no `{MARKER}` / "
                f"`{NORMALIZATION_MARKER}` / `{SAC_MARKER}` rehearsal "
                f"check; if this round adds objective terms, the semantics "
                f"gate applies (SKILL.md section 2)"
            )
        else:
            print(f"[{round_id}] OK: no objective-modification marker; "
                  f"semantics gate not applicable")
        return 0
    rehearsal = _read_json(rehearsal_path)
    if rehearsal is None:
        print(
            f"[{round_id}] PENDING: plan declares a semantics marker but "
            f"{rehearsal_path} does not exist yet — run the rehearsal "
            f"before close-out"
        )
        return 1
    probe = rehearsal.get("objective_semantics_probe")
    if not isinstance(probe, dict):
        print(
            f"[{round_id}] VIOLATION: plan declares a semantics marker but "
            f"the rehearsal carries no objective_semantics_probe record"
        )
        return 1
    if declares_sac:
        return _lint_sac_probe(round_id, probe)
    if declares_normalization:
        return _lint_normalization_probe(round_id, probe)
    rms_dot = float(probe.get("rms_penalty_dot", float("nan")))
    tv_dot = float(probe.get("tv_penalty_dot", float("nan")))
    defect_dot = float(probe.get("defect_form_dot", float("nan")))
    # R433 adaptation (gate-calibration log 2026-08-19): a mean-square
    # penalty form has no total-variation term by construction; when the
    # probe declares `tv_not_penalized: true`, the TV check is replaced by
    # the explicit declaration (the guard consequence is recorded in the
    # round feed), while the RMS and defect-form directions stay mandatory.
    tv_declared = bool(probe.get("tv_not_penalized")) and tv_dot == 0.0
    valid = (
        rms_dot > 0.0
        and (tv_dot > 0.0 or tv_declared)
        and defect_dot < 0.0
    )
    if valid:
        print(
            f"[{round_id}] OK: penalty-direction probe valid "
            f"(rms_dot={rms_dot:.3e}, tv_dot={tv_dot:.3e}, "
            f"defect_form_dot={defect_dot:.3e})"
        )
        return 0
    print(
        f"[{round_id}] VIOLATION: penalty-direction probe signs wrong "
        f"(rms_dot={rms_dot:.3e}, tv_dot={tv_dot:.3e}, "
        f"defect_form_dot={defect_dot:.3e}); expected rms/tv > 0 "
        f"(descent on the statistic) and defect_form < 0"
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_id", help="round id, e.g. R425")
    args = parser.parse_args()
    return lint(args.round_id)


if __name__ == "__main__":
    sys.exit(main())
