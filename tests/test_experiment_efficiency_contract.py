from pathlib import Path


REFERENCES = Path(__file__).resolve().parents[1] / "skills/kundur-round/references"


def test_plumbing_check_cannot_substitute_for_capacity_evidence() -> None:
    skill_text = (REFERENCES / "execution-readiness.md").read_text(encoding="utf-8")
    normalized = " ".join(skill_text.split())

    assert "### Plumbing check versus capacity evidence" in skill_text
    assert "A plumbing check is not capacity evidence" in normalized
    assert "unused resource headroom" in skill_text
    assert "return **MEASURE-FIRST**" in skill_text


def test_execution_card_exposes_capacity_contract() -> None:
    skill_text = (REFERENCES / "execution-readiness.md").read_text(encoding="utf-8")

    for field in (
        "Run state:",
        "Plumbing check:",
        "Capacity evidence and cap classification:",
        "Expected resource use and unused-capacity explanation:",
    ):
        assert field in skill_text
    assert "readiness status agrees with the capacity-evidence field" in skill_text


def test_active_frozen_attempt_is_monitor_only() -> None:
    formal_text = (
        REFERENCES / "formal-execution.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(formal_text.split())

    assert "Missing capacity evidence returns to **MEASURE-FIRST**" in normalized
    assert "Return **HOLD** for in-place reconfiguration" in formal_text
    assert "keep a healthy attempt running" in normalized
