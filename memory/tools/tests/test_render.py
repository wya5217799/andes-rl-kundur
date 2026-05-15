from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from render import render_state  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_render_state_includes_current_headlines_and_decisions(tmp_path):
    out = tmp_path / "STATE.md"
    render_state(
        claims_dir=FIXTURES / "claims",
        rounds_dir=FIXTURES / "rounds",
        handoffs_dir=FIXTURES / "handoffs",
        out_path=out,
    )
    text = out.read_text(encoding="utf-8")
    # Current headline finding (CLM-0001) appears
    assert "CLM-0001" in text
    # Current correction (CLM-0003) appears
    assert "CLM-0003" in text
    # Current decision (CLM-0004) appears in decisions section
    assert "CLM-0004" in text
    # Superseded claim (CLM-0002) does NOT appear under current
    # (allowed in stats/drift but not in current headlines)
    headlines_section = text.split("## Current Headlines")[1].split("##")[0]
    # CLM-0002 is superseded — it must not appear as a line item under current
    assert "- CLM-0002 " not in headlines_section
    # Latest round (R02) referenced
    assert "R02" in text
    # Latest handoff referenced
    assert "2026-01-01-init" in text
    # Stats line includes counts
    assert "4 claims" in text
