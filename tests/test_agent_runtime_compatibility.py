"""Cross-runtime bootstrap contract for Codex and DeepSeek Harness."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_is_runtime_neutral_and_routes_capability_failures() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert agents.startswith("# Research-agent bootstrap")
    assert "已注入其全文则算已读" in agents
    assert "docs/agents/runtime-compatibility.md" in agents
    assert "Codex 以外的 agent" in agents


def test_codex_uses_the_smallest_execution_lane() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "FAST" in agents
    assert "STANDARD" in agents
    assert "FORMAL" in agents
    assert "只有当当前 line/round 决定答案" in agents
    assert "精确文件 + focused tests" in agents
    assert "ANDES 执行" in agents


def test_runtime_adapter_is_operational_not_scientific_authority() -> None:
    text = (ROOT / "docs/agents/runtime-compatibility.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "只适配",
        "read-before-write",
        "lossless JSON",
        "Get-CimInstance",
        "scripts/launch_detached.py",
        "不在一个上下文里角色扮演两个 reviewer",
        "没有把运行时可用性误当成证据权威",
    ):
        assert required in text


def test_explicit_disjoint_scratch_does_not_mutate_active_evidence() -> None:
    workflow = (ROOT / "skills/kundur-round/SKILL.md").read_text(encoding="utf-8")
    resume = (
        ROOT / "skills/kundur-round/references/resume-contract.md"
    ).read_text(encoding="utf-8")

    assert "active evidence/write scope 不相交的 `scratch` 可插入" in workflow
    assert "不改 active round/seal/artifact" in workflow
    assert "owner-explicit `scratch` task disjoint" in resume
    assert "must not modify the active plan, seal, artifacts" in resume


def test_owner_language_keeps_field_terms_but_limits_internal_ids() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "保留学科通用专业词" in agents
    assert "仓库编号/文件名" in agents
    assert "`## 给 PI 的话` 仍按 kundur-round" in agents
