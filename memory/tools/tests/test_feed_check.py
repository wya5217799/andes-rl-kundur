from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from feed_check import check_feed  # noqa: E402

VALID_FEED = """\
# FEED

## Identity
R001 / CLM-0001; evidence `docs/evidence.json`.

## Frozen setup
One bounded comparison.

## Observations
- O1 effect is 12.3%. [CLM-0001; `docs/evidence.json` field `metric`]

## Conclusions (bounded)
- C1 bounded.

## Limits (scope)
- One topology.

## Publication gate
- **Evidence audit**: PASS — `docs/evidence.json` and CLM-0001 agree.
- **Domain audit**: QUALIFIED — physical claim is limited to this model.
- **External context**: CURRENT — verified survey covers this axis.
- **Claim disposition**: QUALIFY — enter with the stated scope.
- **Allowed claim**: The effect holds on the sealed bank.
- **Stay-out**: No deployment or topology-general claim.

## Manuscript mapping
- O1 -> Results.
"""


def _write_support(root: Path) -> None:
    evidence = root / "docs" / "evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"metric": 12.3}\n', encoding="utf-8")
    claim = root / "memory" / "claims" / "CLM-0001.md"
    claim.parent.mkdir(parents=True)
    claim.write_text("# Claim\nfeed.md\n", encoding="utf-8")
    (root / "memory" / "rounds" / "R001").mkdir(parents=True)


def test_publication_ready_feed_passes(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(VALID_FEED, encoding="utf-8")

    assert check_feed(feed, repo_root=tmp_path) == ()


def test_missing_publication_gate_fails_but_legacy_passes(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.split("## Publication gate", maxsplit=1)[0]
        + "## Manuscript mapping\n- O1 -> Results.\n",
        encoding="utf-8",
    )

    assert any(
        item.code == "PUBLICATION_GATE_MISSING"
        for item in check_feed(feed, repo_root=tmp_path)
    )
    assert check_feed(feed, legacy=True, repo_root=tmp_path) == ()


def test_open_deep_research_blocks_readiness(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.replace(
            "CURRENT — verified survey covers this axis.",
            "DEEP-RESEARCH-REQUIRED — nearest work is not verified.",
        ),
        encoding="utf-8",
    )

    assert any(
        item.code == "EXTERNAL_RESEARCH_OPEN"
        for item in check_feed(feed, repo_root=tmp_path)
    )


def test_inline_number_without_claim_id_fails(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.replace(
            "12.3%. [CLM-0001; `docs/evidence.json` field `metric`]",
            "12.3%. [`docs/evidence.json` field `metric`]",
        ),
        encoding="utf-8",
    )

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "OBSERVATION_CLAIM_MISSING" for item in findings)


def test_unmapped_observation_fails(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.replace("- O1 -> Results.", "- Stay-out: unrelated detail."),
        encoding="utf-8",
    )

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "OBSERVATION_UNMAPPED" for item in findings)


def test_missing_identity_pointer_fails(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.replace("`docs/evidence.json`", "`docs/missing.json`", 1),
        encoding="utf-8",
    )

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "POINTER_MISSING" for item in findings)


def test_claim_must_point_back_to_feed(tmp_path: Path) -> None:
    _write_support(tmp_path)
    claim = tmp_path / "memory" / "claims" / "CLM-0001.md"
    claim.write_text("# Claim\n", encoding="utf-8")
    feed = tmp_path / "feed.md"
    feed.write_text(VALID_FEED, encoding="utf-8")

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "CLAIM_FEED_UNBOUND" for item in findings)


def test_feed_era_machine_json_requires_sidecar(tmp_path: Path) -> None:
    _write_support(tmp_path)
    round_dir = tmp_path / "memory" / "rounds" / "R286"
    round_dir.mkdir()
    result_dir = tmp_path / "results" / "r286_demo"
    result_dir.mkdir(parents=True)
    (result_dir / "decision.json").write_text(
        '{"classification": "PASS"}\n',
        encoding="utf-8",
    )
    feed = result_dir / "FEED.md"
    feed.write_text(
        VALID_FEED.replace(
            "R001 / CLM-0001; evidence `docs/evidence.json`.",
            "R286 / CLM-0001; evidence "
            "`results/r286_demo/decision.json`.",
        ),
        encoding="utf-8",
    )
    claim = tmp_path / "memory" / "claims" / "CLM-0001.md"
    claim.write_text(
        "# Claim\nresults/r286_demo/FEED.md\n",
        encoding="utf-8",
    )

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "SIDECAR_MISSING" for item in findings)


def _write_future_result_feed(tmp_path: Path, *, sidecar: str) -> Path:
    import hashlib

    _write_support(tmp_path)
    (tmp_path / "memory" / "rounds" / "R291").mkdir()
    result_dir = tmp_path / "results" / "r291_demo"
    result_dir.mkdir(parents=True)
    decision = result_dir / "decision.json"
    decision.write_text('{"classification": "PASS"}\n', encoding="utf-8")
    digest = (
        hashlib.sha256(decision.read_bytes()).hexdigest()
        if sidecar == "VALID"
        else sidecar
    )
    Path(f"{decision}.sha256").write_text(digest, encoding="ascii")
    feed = result_dir / "FEED.md"
    feed.write_text(
        VALID_FEED.replace(
            "R001 / CLM-0001; evidence `docs/evidence.json`.",
            "R291 / CLM-0001; evidence "
            "`results/r291_demo/decision.json`.",
        ),
        encoding="utf-8",
    )
    claim = tmp_path / "memory" / "claims" / "CLM-0001.md"
    claim.write_text(
        "# Claim\nround: R291\nresults/r291_demo/FEED.md\n",
        encoding="utf-8",
    )
    return feed


def test_malformed_sidecar_is_a_finding_not_an_exception(tmp_path: Path) -> None:
    feed = _write_future_result_feed(tmp_path, sidecar="")

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "SIDECAR_INVALID" for item in findings)


def test_future_result_round_requires_pointer_manifest_entry(tmp_path: Path) -> None:
    feed = _write_future_result_feed(tmp_path, sidecar="VALID")

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "RESULT_MANIFEST_MISSING" for item in findings)


def test_placeholder_gate_field_fails(tmp_path: Path) -> None:
    _write_support(tmp_path)
    feed = tmp_path / "feed.md"
    feed.write_text(
        VALID_FEED.replace(
            "The effect holds on the sealed bank.",
            "TODO",
        ),
        encoding="utf-8",
    )

    findings = check_feed(feed, repo_root=tmp_path)

    assert any(item.code == "PUBLICATION_FIELD_PLACEHOLDER" for item in findings)
