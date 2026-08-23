import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_kundur_round_routes_work_before_reserving_a_round() -> None:
    text = (REPO_ROOT / "skills/kundur-round/SKILL.md").read_text(encoding="utf-8")

    assert "## 2. 工作量分流" in text
    assert "`scratch`" in text
    assert "`manuscript`" in text
    assert "`evidence`" in text
    assert "scratch 不领 round/claim" in text
    assert "新 ANDES、训练或其他物理执行" in text
    assert "标题、摘要、claim 或 question" in text


def test_bootstrap_and_navigation_point_to_the_lane_gate() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "skills/kundur-round/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "classify the work as `scratch`, `manuscript`, or `evidence`" in agents
    assert "先分流、再领 round" in claude
    # Lane details live in the SKILL.md canonical (CLAUDE.md slimmed 2026-08-23
    # to progressive disclosure; CLAUDE.md keeps only the lane pointer).
    assert "scratch 每个 red-green slice 只跑定向测试" in workflow


def test_global_workflow_recommendation_cannot_expand_project_write_scope() -> None:
    adapter = (
        REPO_ROOT / "skills/kundur-round/references/research-skill-adapter.md"
    ).read_text(encoding="utf-8")
    external = (
        REPO_ROOT / "docs/repo-hygiene/external-skills.md"
    ).read_text(encoding="utf-8")
    scope = json.loads(
        (REPO_ROOT / "docs/repo-hygiene/research-skills.scope.json").read_text(
            encoding="utf-8"
        )
    )
    supervisor = next(
        item
        for item in scope["global_skills"]
        if item["name"] == "ask-research-supervisor"
    )

    assert "A global workflow-load recommendation does not authorize project writes" in adapter
    assert "workflow-load recommendation" in external
    assert supervisor["project_write_authority"] == []


def test_future_pi_report_is_plain_language_layer_before_technical_evidence() -> None:
    template = (
        REPO_ROOT / "memory/rounds/_TEMPLATE_VERDICT.md"
    ).read_text(encoding="utf-8")
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workflow = (
        REPO_ROOT / "skills/kundur-round/SKILL.md"
    ).read_text(encoding="utf-8")

    for label in ("**发生了什么**", "**这说明什么**", "**下一步做什么**"):
        assert label in template
    assert "**这周干了啥**" not in template
    assert template.index("Feed:") < template.index("## 给 PI 的话")
    assert "From R317 onward" in agents
    assert "禁英文、缩写、仓库编号、文件名、代码名和明显专业词" in workflow


def test_project_skill_owners_are_disjoint_and_ask_matt_stays_peer_only() -> None:
    adapter = (
        REPO_ROOT / "skills/kundur-round/references/research-skill-adapter.md"
    ).read_text(encoding="utf-8")
    external = (
        REPO_ROOT / "docs/repo-hygiene/external-skills.md"
    ).read_text(encoding="utf-8")
    external_normalized = " ".join(external.split())

    assert "## Ownership and handoffs" in adapter
    assert "Project state owner" in adapter
    assert "Academic route owner" in adapter
    assert "Engineering route owner" in adapter
    assert "Audit owner" in adapter
    assert "Ask Matt remains a peer engineering router" in external
    assert "must not be added to the academic scope manifest" in external_normalized


def test_publication_review_uses_the_canonical_feed_as_its_first_input() -> None:
    adapter = (
        REPO_ROOT / "skills/kundur-round/references/research-skill-adapter.md"
    ).read_text(encoding="utf-8")
    gate = (
        REPO_ROOT / "skills/kundur-round/references/publication-gate.md"
    ).read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "skills/kundur-round/SKILL.md").read_text(
        encoding="utf-8"
    )
    gate_normalized = " ".join(gate.casefold().split())

    assert "## Feed-first publication handoff" in adapter
    assert "Draft the canonical feed first" in adapter
    assert "Audit that same feed" in adapter
    assert "Do not audit a temporary substitute" in adapter
    assert "Use the feed as the pre-draft claim sheet" in gate
    assert "finalize the same-round claim card" in gate_normalized
    assert workflow.index("b. feed + publication gate") < workflow.index(
        "c. claim registration card"
    ) < workflow.index("d. `feed_check.py`")


def test_formal_execution_rules_require_launch_rehearsal_and_count_children() -> None:
    workflow = (REPO_ROOT / "skills/kundur-round/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    workflow_normalized = " ".join(workflow.split())
    claude_normalized = " ".join(claude.split())

    assert "Formal launch contract" in workflow
    assert "same pre-attempt verification path" in workflow_normalized
    assert "a scientific canary does not satisfy this rehearsal" in workflow_normalized
    # Process-budget counting lives in the SKILL.md canonical after the
    # 2026-08-23 CLAUDE.md slim-down; CLAUDE.md keeps the pointer only.
    assert "child 与 process-pool worker" in workflow_normalized
    assert "native numerical-library threads fixed to one" in claude_normalized
