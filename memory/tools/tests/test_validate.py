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
    errors, _warnings = validate_rules(claims)
    assert errors == [], f"Unexpected errors: {errors}"


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
