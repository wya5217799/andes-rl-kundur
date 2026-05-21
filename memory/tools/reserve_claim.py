"""Atomically reserve the next CLM-NNNN under ``memory/claims/``.

Mirrors :mod:`reserve_round` but for claim IDs. The pre-CLM-0430
workflow was: scan ``memory/claims/`` by hand, mentally increment by
5, hope no parallel session picked the same number. This routinely
produces off-by-N errors when sessions are dense (this session created
~10 claims and required two manual ``ls`` rescans to avoid collision
with autonomous-loop output).

The fix is the same as ``reserve_round.py``: make the choice of N a
side-effect of creating the file. ``open(path, "x")`` is atomic — two
callers racing to claim the same N have exactly one winner; the loser
catches ``FileExistsError`` and retries with the new max.

Convention
----------
Claim IDs are zero-padded 4-digit integers, e.g. ``CLM-0435``. The
project has historically allocated in ``+5`` strides (CLM-0420,
CLM-0425, CLM-0430 …) to leave room for cross-references; this tool
preserves that stride by default. Override with ``--stride 1`` for
contiguous allocation.

Usage (CLI)
-----------
::

    $ python memory/tools/reserve_claim.py
    436                              # default stride=5 → next is 0440

    $ python memory/tools/reserve_claim.py --stride 1
    436                              # contiguous → next is 0436

    $ python memory/tools/reserve_claim.py --round R251 --type finding
    436                              # also writes CLM-0436.md stub with
                                     # round + type pre-filled in frontmatter

Usage (library)
---------------
::

    from memory.tools.reserve_claim import reserve_next_claim
    cid_str = reserve_next_claim(Path("memory/claims"))   # → "CLM-0440"
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_CLAIM_RE = re.compile(r"^CLM-(\d{3,4})\.md$")
_DEFAULT_STRIDE = 5


def _max_existing_clm(claims_dir: Path) -> int:
    """Highest CLM-NNNN integer under ``claims_dir``.

    Returns 0 when the directory is empty so that ``max + stride``
    yields the first allocation (``CLM-0005`` at default stride).
    """
    numbers: list[int] = []
    for entry in claims_dir.iterdir():
        if not entry.is_file():
            continue
        m = _CLAIM_RE.match(entry.name)
        if not m:
            continue
        numbers.append(int(m.group(1)))
    return max(numbers) if numbers else 0


def reserve_next_claim(
    claims_dir: Path,
    *,
    stride: int = _DEFAULT_STRIDE,
    round_id: str | None = None,
    claim_type: str = "finding",
) -> str:
    """Reserve and return the next CLM-NNNN identifier.

    Atomically creates ``claims_dir / CLM-NNNN.md`` with a minimal
    frontmatter stub and returns the canonical ``"CLM-NNNN"`` string.
    The stub is just frontmatter + a TODO body line; the author fills
    in ``statement`` and ``tags`` after the experiment lands.

    On concurrent races (two agents reserving simultaneously), the
    loser catches ``FileExistsError`` and retries against the updated
    max, guaranteeing a unique ID per call.

    Args:
        claims_dir: typically ``Path("memory/claims")``. Must exist.
        stride: increment per allocation. 5 = project convention
            (leave room for cross-references / hot-patches). 1 =
            contiguous.
        round_id: ``"RNNN"`` to pre-fill the frontmatter ``round``
            field; otherwise written as ``round: (TBD)`` and the
            author must edit before ``validate.py`` will pass.
        claim_type: ``finding`` / ``decision`` / ``correction``
            (validate.py enforces correction → trust=V, decision →
            trust=S). Defaults to ``finding`` (the most permissive).

    Returns:
        Canonical ``"CLM-NNNN"`` string. The file at
        ``claims_dir / f"{cid}.md"`` is now an unvalidated stub.
    """
    if not claims_dir.is_dir():
        raise FileNotFoundError(f"claims_dir does not exist: {claims_dir}")
    if stride < 1:
        raise ValueError(f"stride must be >= 1, got {stride}")
    if claim_type not in {"finding", "decision", "correction"}:
        raise ValueError(
            f"claim_type must be finding/decision/correction, got {claim_type!r}"
        )

    while True:
        next_n = _max_existing_clm(claims_dir) + stride
        # Snap to stride grid so allocations stay on the 5-step lattice
        # even after a contiguous (stride=1) reservation interrupted it.
        if stride > 1:
            next_n = ((next_n + stride - 1) // stride) * stride
        cid = f"CLM-{next_n:04d}"
        target = claims_dir / f"{cid}.md"
        try:
            # 'x' = exclusive create; raises FileExistsError if path exists
            with target.open("x", encoding="utf-8") as fh:
                fh.write(_stub_body(cid, round_id, claim_type))
            return cid
        except FileExistsError:
            # Race or stride collision — rescan and retry
            continue


def _stub_body(cid: str, round_id: str | None, claim_type: str) -> str:
    """Minimal frontmatter that ``validate.py`` will accept once the
    author fills in ``statement`` and (if cited) ``metric``.

    Kept deliberately small — the author should treat the stub as
    placeholder, not template. The full template lives at
    ``memory/claims/_TEMPLATE.md`` and should be used as the reference
    for what a finished claim looks like.
    """
    trust = "V" if claim_type == "correction" else (
        "S" if claim_type == "decision" else "V"
    )
    round_field = round_id if round_id else "TBD"
    return (
        "---\n"
        f"id: {cid}\n"
        f"type: {claim_type}\n"
        f"trust: {trust}\n"
        "status: current\n"
        "statement: |\n"
        "  (TODO — fill in)\n"
        f"round: {round_field}\n"
        "provenance:\n"
        "  - (TODO)\n"
        "tags: []\n"
        "---\n"
    )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--claims-dir", default="memory/claims",
        help="Path to the claims directory (default: memory/claims)",
    )
    parser.add_argument(
        "--stride", type=int, default=_DEFAULT_STRIDE,
        help=f"Allocation stride (default: {_DEFAULT_STRIDE})",
    )
    parser.add_argument(
        "--round", dest="round_id", default=None,
        help="Pre-fill the round field, e.g. R251",
    )
    parser.add_argument(
        "--type", dest="claim_type", default="finding",
        choices=["finding", "decision", "correction"],
        help="Pre-fill the type field (default: finding)",
    )
    args = parser.parse_args()
    cid = reserve_next_claim(
        Path(args.claims_dir),
        stride=args.stride,
        round_id=args.round_id,
        claim_type=args.claim_type,
    )
    print(cid)


if __name__ == "__main__":
    _main()
