"""Baseline registry — scan ``results/`` for ``final_eval_summary.json``
and emit a dual-metric table.

Motivation (CLM-0410 / CLM-0435 audit, 2026-05-20)
--------------------------------------------------
This session's R246 verdict compared scalar-s50-only-phi_abs against an
**estimated** baseline (~0.327 inferred from hreg-s50 × s54
scalar/hreg ratio), then framed the result as "-28%". When R251
finally measured the true scalar-s50 full-V4 baseline it was 0.266 —
the estimate was 19% too high and the framing collapsed to -11.9%.

Root cause: there was no canonical "look up the measured baseline for
config X" tool. Each new round had to grep ``results/`` by hand and
sometimes resorted to cross-algorithm extrapolation. This tool
removes the temptation by making the registry a one-line query.

What this tool does NOT try to do
---------------------------------
- It does NOT parse the dir naming convention into structured
  ``(algo, seed, reward_config)`` tuples. The naming is informal and
  evolves; parsing it would be brittle. Callers can ``--filter`` by
  regex or use the ``--match`` flag to find runs whose ``env_config``
  matches a reference run's.
- It does NOT compute differences between runs — that's the verdict
  author's interpretive work. The tool just surfaces the raw measured
  numbers.

Usage (CLI)
-----------
::

    # Default: print all runs as a table sorted by mtime
    $ python memory/tools/baselines.py

    # Filter by name pattern
    $ python memory/tools/baselines.py --filter '_s50$'

    # Sort by geo (best first)
    $ python memory/tools/baselines.py --sort geo

    # Find runs whose env_config matches a reference run
    $ python memory/tools/baselines.py --match r251_w1_scalar_full_v4_s50

Usage (library)
---------------
::

    from memory.tools.baselines import scan_baselines, find_matching_configs

    rows = scan_baselines(Path("results"))
    # rows: list[BaselineRow]; each row has run, geo, cum_rf, env_config, ...

    matches = find_matching_configs(rows, reference="r251_w1_scalar_full_v4_s50")
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class BaselineRow:
    """One measured run from ``results/<run>/final_eval_summary.json``."""

    run: str
    geo: float | None
    cum_rf: float | None
    ls1: float | None
    ls2: float | None
    env_config: dict[str, Any] = field(default_factory=dict)
    summary_path: Path | None = None
    mtime: float = 0.0

    @property
    def has_dual_metric(self) -> bool:
        return self.geo is not None and self.cum_rf is not None


def _load_summary(summary_path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _summary_to_floats(j: dict[str, Any]) -> tuple[float | None, float | None,
                                                    float | None, float | None]:
    """Extract ``geo, cum_rf, LS1, LS2`` from either the flat
    ``final_eval_summary.json`` (single-seed) or the aggregated
    ``score_run.py`` output (``per_seed`` envelope)."""
    if "per_seed" in j and isinstance(j["per_seed"], dict):
        # score_run aggregate envelope — use first seed's record
        first = next(iter(j["per_seed"].values()))
        if not isinstance(first, dict):
            return None, None, None, None
        return (
            first.get("geo"),
            first.get("cum_rf"),
            first.get("LS1"),
            first.get("LS2"),
        )
    return j.get("geo"), j.get("cum_rf"), j.get("LS1"), j.get("LS2")


def _load_env_config(run_dir: Path) -> dict[str, Any]:
    """Best-effort pull of ``env_config`` + ``hparam_effective`` from
    ``training_log.json`` for fingerprinting. Returns ``{}`` on failure
    so a missing log does not crash a registry scan."""
    log = run_dir / "training_log.json"
    if not log.exists():
        return {}
    try:
        j = json.loads(log.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, Any] = {}
    env = j.get("env_config")
    if isinstance(env, dict):
        out.update(env)
    hparam = j.get("hparam_effective")
    if isinstance(hparam, dict):
        # Don't shadow env_config keys — env wins where they overlap
        for k, v in hparam.items():
            out.setdefault(k, v)
    return out


def scan_baselines(results_dir: Path) -> list[BaselineRow]:
    """Walk ``results_dir`` and return one ``BaselineRow`` per run with a
    ``final_eval_summary.json`` (or a ``score_run.py``-produced
    ``*_summary.json`` if no canonical name exists).

    Rows are returned sorted by run-directory name (lexical) for stable
    output; sort-by-metric is the CLI's job, not the scanner's.
    """
    if not results_dir.is_dir():
        return []
    rows: list[BaselineRow] = []
    for run_dir in sorted(results_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        # Prefer canonical name; fall back to first matching *_summary.json
        summary_path = run_dir / "final_eval_summary.json"
        if not summary_path.exists():
            candidates = sorted(run_dir.glob("*_summary.json"))
            if not candidates:
                continue
            summary_path = candidates[0]
        j = _load_summary(summary_path)
        if j is None:
            continue
        geo, cum_rf, ls1, ls2 = _summary_to_floats(j)
        rows.append(BaselineRow(
            run=run_dir.name,
            geo=geo, cum_rf=cum_rf, ls1=ls1, ls2=ls2,
            env_config=_load_env_config(run_dir),
            summary_path=summary_path,
            mtime=summary_path.stat().st_mtime,
        ))
    return rows


# ── env_config fingerprint comparison ────────────────────────────────

# Subset of env_config keys that define the "reward config" identity.
# Two runs with identical values on these keys are considered to share
# a reward configuration regardless of other env tweaks.
_REWARD_CONFIG_KEYS = (
    "phi_f", "phi_h", "phi_d", "phi_abs", "phi_max", "phi_settle",
    "vsg_m0", "vsg_d0", "zero_g4_inertia",
    "action_penalty_mode", "lambda_smooth", "smoothness_window",
    "r_f_freq_units", "h_paper_interpretation", "r_avg_scope",
    "include_own_action_obs", "include_time_obs",
    "include_area_mean_freq_obs",
)


def _config_fingerprint(env_config: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Hashable view over the reward-config-defining keys; missing keys
    are coerced to ``None`` so two configs with the same explicit values
    fingerprint the same even when one omits an irrelevant default."""
    return tuple(
        (k, env_config.get(k)) for k in _REWARD_CONFIG_KEYS
    )


def find_matching_configs(rows: list[BaselineRow], reference: str,
                          ) -> list[BaselineRow]:
    """Return rows whose ``env_config`` fingerprint matches ``reference``'s
    on the reward-config keys (see ``_REWARD_CONFIG_KEYS``).

    The reference row is included in the result so the caller sees the
    full match set. Empty list = no match (often because the reference
    run does not exist or has no ``training_log.json``).
    """
    ref = next((r for r in rows if r.run == reference), None)
    if ref is None:
        return []
    ref_fp = _config_fingerprint(ref.env_config)
    return [r for r in rows if _config_fingerprint(r.env_config) == ref_fp]


# ── CLI ──────────────────────────────────────────────────────────────

def _fmt_float(x: float | None, width: int = 7, sign: bool = False) -> str:
    if x is None:
        return f"{'n/a':>{width}}"
    fmt = f"{{:>{width}.4f}}" if not sign else f"{{:>+{width}.4f}}"
    return fmt.format(x)


def _print_table(rows: list[BaselineRow]) -> None:
    if not rows:
        print("(no rows)")
        return
    # ASCII-only output so Windows GBK terminals don't UnicodeEncodeError
    print(f"  {'run':40s}  {'geo':>7s}  {'cum_rf':>8s}  "
          f"{'LS1':>7s}  {'LS2':>7s}  {'dual?':>5s}")
    for r in rows:
        dual = "yes" if r.has_dual_metric else "no"
        print(f"  {r.run:40s}  "
              f"{_fmt_float(r.geo)}  {_fmt_float(r.cum_rf, sign=True, width=8)}  "
              f"{_fmt_float(r.ls1)}  {_fmt_float(r.ls2)}  {dual:>5s}")


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--results-dir", default=str(_ROOT / "results"),
        help="Path to results directory (default: <repo>/results)",
    )
    parser.add_argument(
        "--filter", default=None,
        help="Regex filter on run name (case-insensitive)",
    )
    parser.add_argument(
        "--sort", default="mtime",
        choices=["mtime", "name", "geo", "cum_rf"],
        help="Sort key (default: mtime, newest first)",
    )
    parser.add_argument(
        "--match", default=None,
        help="Reference run name; show only runs with matching env_config",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Max rows to print (default: 50)",
    )
    args = parser.parse_args()

    rows = scan_baselines(Path(args.results_dir))
    if args.match:
        rows = find_matching_configs(rows, reference=args.match)
        if not rows:
            print(f"# No rows match env_config of '{args.match}' "
                  f"(reference run not found or has no training_log.json)")
            sys.exit(1)
    if args.filter:
        pat = re.compile(args.filter, re.IGNORECASE)
        rows = [r for r in rows if pat.search(r.run)]
    if args.sort == "mtime":
        rows.sort(key=lambda r: r.mtime, reverse=True)
    elif args.sort == "name":
        rows.sort(key=lambda r: r.run)
    elif args.sort == "geo":
        rows.sort(key=lambda r: (r.geo is None, -(r.geo or 0.0)))
    elif args.sort == "cum_rf":
        # higher (less negative) cum_rf first
        rows.sort(key=lambda r: (r.cum_rf is None, -(r.cum_rf or -1e9)))
    rows = rows[:args.limit]
    _print_table(rows)


if __name__ == "__main__":
    _main()
