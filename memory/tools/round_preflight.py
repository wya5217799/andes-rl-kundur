"""Round-launch preflight checklist — read the plan, warn before running.

Codifies the three plan-time failures the 2026-05-20 session exposed:

1. **Unread prior CLM** — autonomous loop launched R244 SAC without
   reading CLM-0101 (which already says SAC default fails on this env).
   Wasted ~15 min compute + 1 verdict-writing cycle.
2. **Estimated baseline** — R246 verdict compared scalar+s50 against
   an extrapolated baseline (~0.327 inferred from hreg s50 × cross-algo
   ratio). R251 later measured true baseline = 0.266; the "-28% drop"
   framing was wrong and required CLM-0410 → CLM-0435 supersede chain.
3. **Single-metric plan** — six verdicts shipped citing only ``geo``
   without ``cum_rf``; CLM-0430 audit caught it after the fact and
   forced a session-wide qualification (~30 min of edits).

This tool runs each of these checks against a candidate ``plan.md``
**before** the training launches. Output is a go / no-go report with
actionable suggestions — it never edits the plan, just surfaces
issues.

Design philosophy
-----------------
- **Read-only**: never modifies the plan or any other file.
- **Composes existing tools**: ``query.py`` for tag lookup,
  ``baselines.py`` for measured-baseline check, ``validate.load_claims``
  for the supersede graph. New logic is the orchestration only.
- **Best-effort, not gatekeeper**: prints warnings + recommendations;
  CI / pre-commit can grep for ``BLOCK:`` lines to actually fail.
- **Conservative tag inference**: do not try to be clever about
  intent-from-natural-language. Pull obvious signals (cited CLM IDs,
  ``--algo X`` / ``--seed N`` / ``--phi-* V`` flags from the
  methodology block) and surface adjacent prior CLMs by tag.

Usage (CLI)
-----------
::

    # Check a specific round
    $ python memory/tools/round_preflight.py R252

    # Check newest reserved round (auto-discover)
    $ python memory/tools/round_preflight.py --latest

    # Machine-readable
    $ python memory/tools/round_preflight.py R252 --json

Exit codes
----------
- 0: all checks pass (or only INFO-level findings)
- 1: WARN-level issues found (run launches OK but author should review)
- 2: BLOCK-level issues (CI / pre-commit should refuse to launch)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_ROOT = _THIS_DIR.parents[1]
sys.path.insert(0, str(_THIS_DIR))

from validate import load_claims  # noqa: E402
from baselines import scan_baselines, find_matching_configs  # noqa: E402


@dataclass
class Finding:
    """One preflight finding — level + check + message + suggestion."""
    level: str        # "INFO" | "WARN" | "BLOCK"
    check: str        # short check name, e.g. "supersede-chain"
    message: str
    suggestion: str = ""

    def __str__(self) -> str:
        s = f"{self.level:5s} [{self.check}] {self.message}"
        if self.suggestion:
            s += f"\n      => {self.suggestion}"
        return s


@dataclass
class PreflightReport:
    round_id: str
    plan_path: Path
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, check: str, message: str,
            suggestion: str = "") -> None:
        self.findings.append(Finding(level, check, message, suggestion))

    @property
    def exit_code(self) -> int:
        if any(f.level == "BLOCK" for f in self.findings):
            return 2
        if any(f.level == "WARN" for f in self.findings):
            return 1
        return 0

    def counts(self) -> dict[str, int]:
        c = {"INFO": 0, "WARN": 0, "BLOCK": 0}
        for f in self.findings:
            c[f.level] = c.get(f.level, 0) + 1
        return c


# ── Plan parsing primitives ───────────────────────────────────────────

_CLM_CITE_RE = re.compile(r"\bCLM-(\d{3,4})\b")
_RUN_NAME_RE = re.compile(r"\br\d{1,3}_w\d+_[a-z0-9_]+_s\d{2}\b",
                          re.IGNORECASE)
_CLI_FLAG_RE = re.compile(
    r"--(algo|seed|phi-[a-z]+|episodes|tau|hidden-size|lstm-lr-warmup-eps|"
    r"normalize-actions|h-norm-reg|save-dir)(?:\s+(\S+))?"
)


def _cited_clm_ids(text: str) -> set[str]:
    return {f"CLM-{m.group(1).zfill(4)}" for m in _CLM_CITE_RE.finditer(text)}


def _cited_run_names(text: str) -> set[str]:
    return {m.group(0).lower() for m in _RUN_NAME_RE.finditer(text)}


def _extract_methodology_flags(text: str) -> dict[str, str]:
    """Pull --algo / --seed / --phi-* etc. from the methodology block.

    Returns first occurrence of each flag (later overrides not honored;
    methodology blocks usually have one canonical invocation). Bare
    flags (no value, e.g. ``--normalize-actions``) get value ``""``.
    """
    flags: dict[str, str] = {}
    for m in _CLI_FLAG_RE.finditer(text):
        name = m.group(1)
        if name not in flags:
            flags[name] = m.group(2) or ""
    return flags


# ── Check 1: supersede graph ──────────────────────────────────────────

def check_superseded_citations(report: PreflightReport, plan_text: str,
                               claims: dict[str, dict[str, Any]]) -> None:
    """For each CLM cited in plan.md, warn if its status is
    ``superseded`` — the author probably wants the successor."""
    cited = _cited_clm_ids(plan_text)
    for cid in sorted(cited):
        c = claims.get(cid)
        if c is None:
            report.add("WARN", "missing-clm",
                       f"plan cites {cid} but it doesn't exist in memory/claims/",
                       f"verify the ID; if you meant a sibling, fix the citation")
            continue
        if c.get("status") == "superseded":
            successors = c.get("superseded_by") or []
            succ_str = ", ".join(successors) if successors else "(unknown)"
            report.add("WARN", "supersede-chain",
                       f"plan cites SUPERSEDED claim {cid} (replaced by {succ_str})",
                       f"read {succ_str} and decide whether to cite it instead "
                       f"(or both, if {cid} carries unique historical context)")
        elif c.get("status") == "obsoleted":
            reason = c.get("obsoleted_reason", "unknown")
            report.add("WARN", "obsoleted-clm",
                       f"plan cites OBSOLETED claim {cid} (reason: {reason})",
                       "verify the cited number still applies under current ranker / config")


# ── Check 2: measured baselines ───────────────────────────────────────

def check_baselines_measured(report: PreflightReport, plan_text: str,
                             results_dir: Path,
                             *,
                             current_round_num: int | None = None) -> None:
    """If the plan cites a comparison baseline like ``r251_w1_scalar...``
    or mentions ``baseline 0.NNN``, check that ``baselines.py`` knows
    about the measured value. Suggest ``--match`` lookups.

    Skips run names matching the current round's number — those are
    typically the plan's own ``--save-dir`` (i.e. the OUTPUT of this
    round), not a baseline being compared against. Without this skip,
    every plan that names its own save-dir triggers a false-positive
    'missing-baseline' WARN (real failure mode caught by dogfooding
    on R253/R254 — 2026-05-20)."""
    cited_runs = _cited_run_names(plan_text)
    if current_round_num is not None:
        prefix = f"r{current_round_num}_"
        cited_runs = {r for r in cited_runs if not r.startswith(prefix)}
    if not cited_runs:
        report.add("INFO", "no-baseline-cited",
                   "plan doesn't cite any concrete run names; can't auto-verify baselines",
                   "if interpretation will compare to a measured baseline, "
                   "name the run (e.g. r251_w1_scalar_full_v4_s50) in plan rationale")
        return
    rows = scan_baselines(results_dir)
    available = {r.run.lower() for r in rows}
    for run in sorted(cited_runs):
        if run not in available:
            report.add("WARN", "missing-baseline",
                       f"plan cites run '{run}' but no final_eval_summary.json "
                       f"in results/{run}/",
                       f"either re-score the run "
                       f"(python scripts/score_run.py --ckpt-dirs results/{run}) "
                       f"or pick a measured baseline via "
                       f"`python memory/tools/baselines.py --filter <pattern>`")
        else:
            r = next(rr for rr in rows if rr.run.lower() == run)
            if not r.has_dual_metric:
                report.add("WARN", "single-metric-baseline",
                           f"baseline '{run}' has geo={r.geo} but cum_rf is "
                           f"missing (incomplete summary)",
                           f"re-score to get cum_rf for dual-metric comparison")

    # Heuristic: warn if plan says "estimated" / "extrapolated" anywhere
    if re.search(r"\b(estimated|extrapolated|inferred from)\b",
                 plan_text, re.IGNORECASE):
        report.add("BLOCK", "estimated-baseline",
                   "plan mentions 'estimated' / 'extrapolated' baseline",
                   "use baselines.py to get a MEASURED baseline; if none exists, "
                   "run that baseline FIRST before interpreting the ablation result. "
                   "See CLM-0410 → CLM-0435 for what happens otherwise (10 rounds "
                   "of wrong framing).")


# ── Check 3: dual-metric plan ─────────────────────────────────────────

# Tag fragments that mark a plan as paper-reward-ablation territory.
# Mirrors dual_metric_lint.py _DUAL_METRIC_TAGS but applied to plan body.
_DUAL_METRIC_KEYWORDS = (
    "paper Eq.14", "paper Eq. 14", "paper-eq14", "paper-strict",
    "gauge invariance", "gauge-invariance", "phi_abs", "phi-abs",
    "phi_h", "phi_d", "phi_f", "only-phi_abs", "only phi_abs",
    "reward reproducibility", "Yang2023",
)


def check_dual_metric_plan(report: PreflightReport, plan_text: str) -> None:
    """If the plan involves reward-ablation territory, remind the
    author the resulting verdict + claim MUST cite both geo and
    cum_rf. Also flag if plan's decision tree only mentions ``geo``."""
    text_low = plan_text.lower()
    if not any(kw.lower() in text_low for kw in _DUAL_METRIC_KEYWORDS):
        return  # not a reward-ablation plan; lint not applicable
    mentions_cum_rf = "cum_rf" in plan_text or "§iv-c" in text_low or "yang2023" in text_low
    mentions_geo = re.search(r"\bgeo\b", plan_text) is not None
    if mentions_geo and not mentions_cum_rf:
        report.add("BLOCK", "single-metric-plan",
                   "plan is paper-reward-ablation territory but only mentions "
                   "'geo' in decision tree / outcomes (no cum_rf)",
                   "add cum_rf thresholds to the pre-registered outcomes table. "
                   "Reward ablations consistently show -3 to -6% cum_rf even when "
                   "geo is vestigial (CLM-0430 audit). Single-metric framing "
                   "wastes a verdict cycle when the audit lands.")
    elif not mentions_cum_rf:
        report.add("WARN", "reward-ablation-no-cum-rf",
                   "plan is in reward-ablation territory but doesn't mention "
                   "cum_rf at all",
                   "even if the headline is geo, the verdict MUST report both "
                   "(CLM-0430 policy). Add a 'cum_rf threshold for follow-up' "
                   "to the decision tree.")


# ── Check 4: prior-art surfacing ──────────────────────────────────────

def check_prior_art(report: PreflightReport, plan_text: str,
                    claims: dict[str, dict[str, Any]], *,
                    top_k: int = 5) -> None:
    """Pull tag-like keywords from the plan and surface top-K most
    relevant existing claims by tag overlap. Helps catch
    'autonomous loop forgot CLM-0101' (R244 SAC) class of failure."""
    methodology = _extract_methodology_flags(plan_text)
    plan_keywords: set[str] = set()
    # From flags
    if "algo" in methodology:
        plan_keywords.add(methodology["algo"].lower())
    if "seed" in methodology:
        plan_keywords.add(f"s{methodology['seed']}")
    for k in ("phi-abs", "phi-h", "phi-d", "phi-f"):
        if k in methodology:
            v = methodology[k]
            plan_keywords.add(k.replace("-", "_"))
            if v == "0":
                plan_keywords.add("only-phi_abs" if k == "phi-abs"
                                  else f"{k.replace('-', '_')}-zero")
    # From freeform "compare to X" / "vs X" patterns
    plan_keywords.update(
        m.group(1).lower() for m in re.finditer(r"\b(\w+)-(?:rescue|inertness|"
                                                r"vestigial|collapse|baseline)\b",
                                                plan_text, re.IGNORECASE)
    )
    if not plan_keywords:
        return  # nothing to match against

    # Score each non-superseded claim by keyword overlap with its tags+statement
    cited_already = _cited_clm_ids(plan_text)
    scores: list[tuple[int, str, dict[str, Any]]] = []
    for cid, c in claims.items():
        if c.get("status") in {"superseded", "obsoleted"}:
            continue
        if cid in cited_already:
            continue
        tags = [str(t).lower() for t in (c.get("tags") or [])]
        stmt = str(c.get("statement", "")).lower()
        overlap = sum(1 for kw in plan_keywords
                      if any(kw in t for t in tags) or kw in stmt)
        if overlap > 0:
            scores.append((overlap, cid, c))
    scores.sort(key=lambda x: (-x[0], x[1]))
    top = scores[:top_k]
    if not top:
        return
    rel_str = ", ".join(f"{cid} ({n} kw)" for n, cid, _ in top)
    report.add("INFO", "prior-art",
               f"Possibly relevant prior claims (not cited in plan): {rel_str}",
               f"read these and add citations where relevant. This catches "
               f"the 'autonomous loop forgot CLM-0101' failure mode (R244 SAC).")


# ── Check 5: plan-quality structural ──────────────────────────────────

_REQUIRED_HEADINGS = ("TL;DR", "Methodology")
_RECOMMENDED_HEADINGS = ("Cross-references",)


def check_plan_structure(report: PreflightReport, plan_text: str) -> None:
    for heading in _REQUIRED_HEADINGS:
        if not re.search(rf"^##\s+{re.escape(heading)}\b", plan_text,
                         re.MULTILINE):
            report.add("WARN", "plan-structure",
                       f"plan is missing required section '## {heading}'",
                       f"add a '## {heading}' section")
    for heading in _RECOMMENDED_HEADINGS:
        if not re.search(rf"^##\s+{re.escape(heading)}\b", plan_text,
                         re.MULTILINE):
            report.add("INFO", "plan-structure",
                       f"plan is missing recommended section '## {heading}'",
                       "")
    # Pre-registered outcomes — look for a decision tree / outcomes table
    if not re.search(
            r"(?i)\b(outcomes?|decision tree|pre-?registered|predict)\b",
            plan_text):
        report.add("WARN", "no-preregistration",
                   "plan does not pre-register outcome thresholds / decision tree",
                   "add an 'Outcomes' subsection listing what each result "
                   "magnitude would mean (e.g. 'geo > 0.32 = rescue; "
                   "0.25-0.32 = partial; <0.10 = collapse'). Prevents "
                   "ad-hoc post-hoc interpretation.")


# ── Orchestration ─────────────────────────────────────────────────────

def preflight_check(plan_path: Path, *,
                    results_dir: Path | None = None,
                    claims_dir: Path | None = None,
                    ) -> PreflightReport:
    """Run all preflight checks against ``plan_path`` and return a report.

    All checks are best-effort — missing data produces INFO findings,
    not exceptions, so the tool works on minimal stub plans too.
    """
    if results_dir is None:
        results_dir = _ROOT / "results"
    if claims_dir is None:
        claims_dir = _ROOT / "memory" / "claims"

    text = plan_path.read_text(encoding="utf-8")
    claims = load_claims(claims_dir)

    round_id_match = re.search(r"^# (R\d+)\b", text, re.MULTILINE)
    round_id = round_id_match.group(1) if round_id_match else plan_path.parent.name
    report = PreflightReport(round_id=round_id, plan_path=plan_path)

    # Extract numeric round id for self-save-dir filtering
    round_num_match = re.match(r"^R(\d+)$", round_id)
    current_round_num = int(round_num_match.group(1)) if round_num_match else None

    check_plan_structure(report, text)
    check_superseded_citations(report, text, claims)
    check_baselines_measured(report, text, results_dir,
                             current_round_num=current_round_num)
    check_dual_metric_plan(report, text)
    check_prior_art(report, text, claims)
    return report


def _resolve_round_dir(round_arg: str | None, *,
                       memory_dir: Path) -> Path:
    rounds_dir = memory_dir / "rounds"
    if round_arg == "--latest" or round_arg is None:
        candidates: list[tuple[int, Path]] = []
        for entry in rounds_dir.iterdir():
            m = re.match(r"^R(\d+)$", entry.name)
            if m and (entry / "plan.md").exists():
                candidates.append((int(m.group(1)), entry))
        if not candidates:
            raise FileNotFoundError(
                f"no rounds with plan.md found under {rounds_dir}")
        candidates.sort()
        return candidates[-1][1]
    return rounds_dir / round_arg


def _print_human(report: PreflightReport) -> None:
    counts = report.counts()
    print(f"== Preflight for {report.round_id} ==")
    print(f"   plan: {report.plan_path}")
    if not report.findings:
        print("   OK: all checks pass")
        return
    for f in report.findings:
        print(f)
    print()
    print(f"-- Summary: BLOCK={counts['BLOCK']} WARN={counts['WARN']} "
          f"INFO={counts['INFO']}")
    if report.exit_code == 2:
        print("-- VERDICT: do NOT launch (resolve BLOCKs above)")
    elif report.exit_code == 1:
        print("-- VERDICT: review WARNs before launching")
    else:
        print("-- VERDICT: OK to launch")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_id", nargs="?", default=None,
                        help="Round to check, e.g. R252. Use --latest for newest.")
    parser.add_argument("--latest", action="store_true",
                        help="Check the newest round with a plan.md")
    parser.add_argument("--memory-dir", default=str(_ROOT / "memory"))
    parser.add_argument("--results-dir", default=str(_ROOT / "results"))
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON")
    args = parser.parse_args()

    arg = "--latest" if args.latest else args.round_id
    if arg is None:
        parser.error("provide a round_id (e.g. R252) or --latest")
    round_dir = _resolve_round_dir(arg, memory_dir=Path(args.memory_dir))
    plan_path = round_dir / "plan.md"
    if not plan_path.exists():
        print(f"# No plan.md at {plan_path}", file=sys.stderr)
        return 2

    report = preflight_check(
        plan_path,
        results_dir=Path(args.results_dir),
        claims_dir=Path(args.memory_dir) / "claims",
    )
    if args.json:
        json.dump({
            "round_id": report.round_id,
            "plan_path": str(report.plan_path),
            "findings": [
                {"level": f.level, "check": f.check,
                 "message": f.message, "suggestion": f.suggestion}
                for f in report.findings
            ],
            "exit_code": report.exit_code,
            "counts": report.counts(),
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_human(report)
    return report.exit_code


if __name__ == "__main__":
    sys.exit(_main())
