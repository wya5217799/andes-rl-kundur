"""Query helpers for the claim ledger.

R50 optimization L — once the claim ledger crossed ~50 entries, scanning
``memory/claims/CLM-*.md`` by hand became expensive. ``query.py`` gives
two minimal lookups that came up most often during R43-R49:

  --tag <name>           : claims tagged <name>, status=current (default).
  --best <metric_name>   : top-K claims with metric.name=<metric_name>,
                           sorted by metric.value descending.

The library API mirrors the CLI:

  from memory.tools.query import query_by_tag, query_best
  from memory.tools.validate import load_claims

  td3_current = query_by_tag(load_claims(Path("memory/claims")), "td3")
  best_6axis  = query_best(load_claims(Path("memory/claims")),
                            metric_name="6_axis", top=5)

CLI:

  $ python memory/tools/query.py --tag td3
  CLM-0049  R43  ...
  CLM-0055  R48  ...

  $ python memory/tools/query.py --best 6_axis --top 5
  CLM-...   0.365  ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def query_by_tag(
    claims: dict[str, dict[str, Any]],
    tag: str,
    *,
    include_superseded: bool = False,
) -> list[dict[str, Any]]:
    """Return claims whose ``tags`` list contains ``tag``.

    Hides ``status='superseded'`` claims by default — overrideable via
    ``include_superseded=True``. Order is stable by id (claims sort
    naturally as CLM-NNNN).
    """
    out: list[dict[str, Any]] = []
    for cid in sorted(claims):
        c = claims[cid]
        tags = c.get("tags", []) or []
        if tag not in tags:
            continue
        if not include_superseded and c.get("status") == "superseded":
            continue
        out.append(c)
    return out


def query_best(
    claims: dict[str, dict[str, Any]],
    *,
    metric_name: str,
    top: int = 10,
) -> list[dict[str, Any]]:
    """Return up to ``top`` claims whose ``metric.name == metric_name``,
    sorted by ``metric.value`` descending.

    Claims without a metric block, or whose metric.name differs, or whose
    metric.value isn't numeric are skipped.
    """
    if top <= 0:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for c in claims.values():
        m = c.get("metric")
        if not isinstance(m, dict):
            continue
        if m.get("name") != metric_name:
            continue
        v = m.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        scored.append((float(v), c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _v, c in scored[:top]]


def _format_tag_row(c: dict[str, Any]) -> str:
    cid = c.get("id", "?")
    round_label = c.get("round", "?")
    status = c.get("status", "?")
    # Statement first line, truncated.
    stmt = (c.get("statement") or "").strip().splitlines()
    first = stmt[0].strip() if stmt else ""
    if len(first) > 80:
        first = first[:77] + "..."
    return f"{cid}  {round_label:>4}  {status:>11}  {first}"


def _format_best_row(c: dict[str, Any]) -> str:
    cid = c.get("id", "?")
    round_label = c.get("round", "?")
    m = c.get("metric") or {}
    value = m.get("value", float("nan"))
    name = m.get("name", "?")
    return f"{cid}  {round_label:>4}  {name} = {value:.4f}"


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    base = Path(__file__).parent.parent
    parser.add_argument(
        "--claims-dir", type=Path, default=base / "claims",
        help="Path to memory/claims/ (default: <repo>/memory/claims)",
    )
    parser.add_argument("--tag", type=str, help="Filter by tag (e.g. td3, h64)")
    parser.add_argument(
        "--include-superseded", action="store_true",
        help="Include status='superseded' claims (off by default)",
    )
    parser.add_argument(
        "--best", type=str, default=None, metavar="METRIC_NAME",
        help="List top-K claims for the named metric (e.g. 6_axis)",
    )
    parser.add_argument("--top", type=int, default=10, help="K for --best (default 10)")
    args = parser.parse_args()

    # Late import so module-level CLI parsing doesn't pull in YAML on
    # ``--help``.
    from validate import load_claims

    claims = load_claims(args.claims_dir)

    if args.best:
        rows = query_best(claims, metric_name=args.best, top=args.top)
        for c in rows:
            print(_format_best_row(c))
        return 0

    if args.tag:
        rows = query_by_tag(
            claims, args.tag, include_superseded=args.include_superseded
        )
        for c in rows:
            print(_format_tag_row(c))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_main())
