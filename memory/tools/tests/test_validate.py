from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from validate import load_claims  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "claims"


def test_load_claims_returns_dict_of_id_to_frontmatter():
    claims = load_claims(FIXTURES)
    assert set(claims.keys()) == {"CLM-0001", "CLM-0002", "CLM-0003", "CLM-0004"}
    assert claims["CLM-0001"]["type"] == "finding"
    assert claims["CLM-0001"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == ["CLM-0003"]


from validate import validate_rules  # noqa: E402


def test_rule1_duplicate_id_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": []},
        "CLM-0001b": {"id": "CLM-0001", "status": "current",
                      "supersedes": [], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("duplicate id" in e.lower() for e in errors)


def test_rule2_supersedes_nonexistent_target_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": ["CLM-9999"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("CLM-9999" in e and "does not exist" in e for e in errors)


def test_rule3_current_with_nonempty_superseded_by_fails():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "status": "current",
                     "supersedes": [], "superseded_by": ["CLM-0002"]},
        "CLM-0002": {"id": "CLM-0002", "status": "current",
                     "supersedes": ["CLM-0001"], "superseded_by": []},
    }
    errors, _warnings = validate_rules(claims)
    assert any("status: current" in e and "superseded_by" in e for e in errors)


def test_clean_fixtures_have_no_errors():
    claims = load_claims(FIXTURES)
    errors, warnings = validate_rules(claims)
    assert errors == [], f"Unexpected errors: {errors}"
    assert warnings == [], f"Unexpected warnings: {warnings}"


def test_rule4_decision_with_trust_V_fails():
    """A `type: decision` claim must be `trust: S` (Stated, not Verified).
    Decisions are choices, not measurable facts."""
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "decision", "trust": "V",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert any("CLM-0001" in e and "decision" in e and "trust" in e for e in errors), \
        f"expected rule4 error, got: {errors}"


def test_rule4_decision_with_trust_S_passes():
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "decision", "trust": "S",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert not any("CLM-0001" in e and "decision" in e and "trust" in e for e in errors), \
        f"unexpected rule4 error: {errors}"


def test_rule4_correction_with_trust_S_fails():
    """A `type: correction` claim must be `trust: V` (it replaces a verified
    prior number — the replacement itself must be verified)."""
    claims = {
        "CLM-0001": {"id": "CLM-0001", "type": "correction", "trust": "S",
                     "status": "current", "supersedes": [], "superseded_by": []},
    }
    errors, _ = validate_rules(claims)
    assert any("CLM-0001" in e and "correction" in e and "trust" in e for e in errors), \
        f"expected rule4 error, got: {errors}"


def test_rule4_finding_trust_V_or_S_both_pass():
    """Findings can be V, S, or T — different levels of evidence."""
    for trust in ("V", "S", "T"):
        claims = {
            "CLM-0001": {"id": "CLM-0001", "type": "finding", "trust": trust,
                         "status": "current", "supersedes": [], "superseded_by": []},
        }
        errors, _ = validate_rules(claims)
        assert not any("CLM-0001" in e and "finding" in e and "trust" in e for e in errors), \
            f"unexpected rule4 error for trust={trust}: {errors}"


def test_load_claims_raises_on_duplicate_id_on_disk(tmp_path):
    """Two files with the same id should error at load time."""
    (tmp_path / "CLM-0001.md").write_text(
        "---\nid: CLM-0001\ntype: finding\ntrust: V\n"
        "status: current\nstatement: foo\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "CLM-0001b.md").write_text(
        "---\nid: CLM-0001\ntype: finding\ntrust: V\n"
        "status: current\nstatement: bar\n---\n",
        encoding="utf-8",
    )
    import pytest
    with pytest.raises(ValueError, match="duplicate id CLM-0001"):
        load_claims(tmp_path)


import shutil
from validate import fix_back_edges  # noqa: E402


def test_fix_back_edges_writes_superseded_by_and_flips_status(tmp_path):
    src = FIXTURES
    dst = tmp_path / "claims"
    shutil.copytree(src, dst)

    # Wipe back edge + status from CLM-0002 to simulate forgotten metadata
    target = dst / "CLM-0002.md"
    content = target.read_text(encoding="utf-8")
    content = content.replace("status: superseded", "status: current")
    content = content.replace("superseded_by: [CLM-0003]", "superseded_by: []")
    target.write_text(content, encoding="utf-8")

    claims = load_claims(dst)
    assert claims["CLM-0002"]["status"] == "current"
    assert claims["CLM-0002"]["superseded_by"] == []

    fix_back_edges(claims, write=True)

    fixed = load_claims(dst)
    assert fixed["CLM-0002"]["status"] == "superseded"
    assert fixed["CLM-0002"]["superseded_by"] == ["CLM-0003"]
