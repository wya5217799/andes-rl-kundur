"""Shared pytest bootstrap for the src-layout package."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


_CLOSED_ROUND_LIFECYCLE_TESTS = {
    (
        "test_r353_matched_residual_analysis.py",
        "test_rehearsal_and_prepare_are_create_only_and_bind_both_closures",
    ): ("r353", "R353", "Q-0094", False),
    (
        "test_r354_certificate_compatible_residual_headroom.py",
        "test_rehearsal_and_prepare_are_create_only_for_recovery",
    ): ("r354", "R354", "Q-0094", False),
    (
        "test_r355_rehearsal_binding_residual_headroom.py",
        "test_implicit_inherited_seal_load_uses_current_rehearsal",
    ): ("r355", "R355", "Q-0094", False),
    (
        "test_r355_rehearsal_binding_residual_headroom.py",
        "test_formal_rehearsal_command_exercises_implicit_loader_seam",
    ): ("r355", "R355", "Q-0094", False),
    (
        "test_r355_rehearsal_binding_residual_headroom.py",
        "test_rehearsal_prepare_and_loader_are_create_only",
    ): ("r355", "R355", "Q-0094", False),
    (
        "test_r358_physical_joint_endpoint_qp_analysis.py",
        "test_rehearsal_and_prepare_are_create_only_and_bind_closures",
    ): ("runner", "R358", "Q-0095", True),
}


@pytest.fixture(autouse=True)
def _isolate_closed_round_lifecycle(request, monkeypatch, tmp_path_factory) -> None:
    """Keep create-only tests independent of the repository lifecycle state."""

    key = (Path(str(request.node.path)).name, request.node.name)
    lifecycle = _CLOSED_ROUND_LIFECYCLE_TESTS.get(key)
    if lifecycle is None:
        return

    module_name, round_id, question_id, requires_question = lifecycle
    adapter = getattr(request.node.module, module_name)
    lifecycle_dir = tmp_path_factory.mktemp(f"{round_id.lower()}_lifecycle")
    plan = lifecycle_dir / "plan.md"
    plan.write_text(
        f"state: active\n{round_id}\n{question_id}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(adapter, "PLAN", plan)

    if requires_question:
        question = lifecycle_dir / "question.md"
        question.write_text(
            f"status: in-flight\n{round_id}:\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(adapter, "QUESTION", question)
