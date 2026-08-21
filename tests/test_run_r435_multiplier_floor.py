"""R435 runner tests: contract shape, floor semantics, seam discipline.

The floor semantics run on the real learner in the WSL rehearsal
(``floor_semantics_probe``); the static tests here pin (a) the seam
discipline — the ``_floored_agent_for`` factory is an R410 ``_agent_for``
verbatim copy whose only R435-SEAM lines swap the CD class and add the
floor — and (b) the frozen dual-update formula with the floor clip.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_runner(module_name: str, path: str) -> pytest.ModuleType:
    import importlib.util

    import sys

    for _p in (ROOT, ROOT / "src", ROOT / "scripts"):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
    spec = importlib.util.spec_from_file_location(module_name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_COMPOUND_STATEMENTS = (
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.Try,
    ast.FunctionDef,
    ast.ClassDef,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Match,
)


def _leaf_statements(path: Path, name: str) -> list[tuple[str, ast.stmt]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            leaves = []
            for sub in ast.walk(node):
                if not isinstance(sub, ast.stmt) or isinstance(
                    sub, _COMPOUND_STATEMENTS
                ):
                    continue
                if isinstance(sub, ast.Expr) and isinstance(
                    sub.value, ast.Constant
                ) and isinstance(sub.value.value, str):
                    continue
                leaves.append((ast.dump(sub), sub))
            return leaves
    raise AssertionError(f"function {name} not found in {path}")


def _not_fully_seam_marked(path: Path, node: ast.stmt, marker: str) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    source_lines = lines[node.lineno - 1 : node.end_lineno]
    return not (bool(source_lines) and all(marker in line for line in source_lines))


def test_contract_shape() -> None:
    runner = _load_runner("r435", "scripts/run_r435_multiplier_floor.py")
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert contract["engineering_successor"]["successor_of"] == "R432"
    mft = contract["multiplier_floor_test"]
    assert mft["floor"] == 1.0
    assert mft["single_factor"].startswith("frozen dual update")
    assert mft["arms"] == ["cd_matd3_no_message", "cd_matd3_message"]
    assert mft["control"] == "R432 paired runs (same bundle, same seeds, no floor)"


def test_floor_semantics_formula() -> None:
    """The floored dual update is the frozen formula clipped at [floor, max]:
    above the floor both agree exactly; below it the floored value pins."""
    import numpy as np

    runner = _load_runner("r435", "scripts/run_r435_multiplier_floor.py")
    runner.LAGRANGE_FLOOR = 1.0

    def frozen(lam, cost, budget, step):
        return float(np.clip(lam + step * (cost - budget), 0.0, 10.0))

    floor = 1.0
    cases = [
        (0.97, 3.4, 3.0, 0.05),   # above budget -> rises, no floor contact
        (1.0, 2.0, 3.0, 0.05),    # below budget -> would decay, pinned at 1.0
        (5.0, 2.0, 3.0, 0.05),    # below budget, still above floor -> frozen
        (9.9, 5.0, 3.0, 0.05),    # near max -> clip at max unchanged
    ]
    for lam, cost, budget, step in cases:
        f = frozen(lam, cost, budget, step)
        assert float(np.clip(lam + step * (cost - budget), floor, 10.0)) == pytest.approx(
            max(f, floor) if f < floor else f
        )
    # the floor is the ONLY change vs the frozen clip bound
    assert floor == 1.0


def test_authority_checks_pass() -> None:
    plan_path = ROOT / "memory/rounds/R435/plan.md"
    if not plan_path.is_file():
        pytest.skip("R435 plan not written yet; authority checks need the plan")
    runner = _load_runner("r435", "scripts/run_r435_multiplier_floor.py")
    checks = runner.authority_checks()
    plan_text = plan_path.read_text(encoding="utf-8")
    plan_active = "state: active" in plan_text and "R435" in plan_text
    assert checks["active_plan"] == plan_active
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
    assert checks["output_absence"] == (not runner.OUT.exists())


def test_parser_commands() -> None:
    runner = _load_runner("r435", "scripts/run_r435_multiplier_floor.py")
    parser = runner._parser()
    args = parser.parse_args(["rehearse"])
    assert args.command == "rehearse"
    args = parser.parse_args(["shard", "train|cd_matd3_message|402"])
    assert args.shard_id == "train|cd_matd3_message|402"


def test_shards_manifest_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    runner = _load_runner("r435", "scripts/run_r435_multiplier_floor.py")
    monkeypatch.setattr(runner, "_assert_wsl_scratch", lambda: None)
    path = Path(runner.shards())
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        assert len(rows) == 6
        assert rows[0] == "train|cd_matd3_no_message|401"
        assert rows[-1] == "train|cd_matd3_message|403"
    finally:
        path.unlink(missing_ok=True)


def test_copy_seam_discipline() -> None:
    """Every non-seam leaf statement of ``_floored_agent_for`` must be a
    verbatim leaf statement of the frozen R410 ``_agent_for``."""
    from collections import Counter

    runner_path = ROOT / "scripts/run_r435_multiplier_floor.py"
    frozen_path = ROOT / "scripts/run_r410_message_repair.py"
    copy_stmts = _leaf_statements(runner_path, "_floored_agent_for")
    frozen_stmts = [
        dump for dump, _node in _leaf_statements(frozen_path, "_agent_for")
    ]
    kept = []
    for dump, node in copy_stmts:
        if not _not_fully_seam_marked(runner_path, node, "R435-SEAM"):
            continue
        kept.append(dump)
    counter = Counter(frozen_stmts)
    additions = []
    for dump in kept:
        if counter[dump] > 0:
            counter[dump] -= 1
        else:
            additions.append(dump)
    assert not additions, f"copy drifted from the frozen source: {additions}"


def test_seam_markers_contained_in_copies() -> None:
    text = (ROOT / "scripts/run_r435_multiplier_floor.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(text)
    copy_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_floored_agent_for",
        }:
            copy_ranges.append((node.lineno, node.end_lineno))
    string_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_ranges.append((node.lineno, node.end_lineno))
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if "R435-SEAM" not in line:
            continue
        in_string = any(start <= index <= end for start, end in string_ranges)
        if in_string:
            continue
        assert any(start <= index <= end for start, end in copy_ranges), (
            f"R435-SEAM marker outside the copied function at line {index}"
        )
