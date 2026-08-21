"""R431 runner tests: contract shape, authority, root probe, seam discipline.

The bitcheck (short-budget frozen-vs-copy byte-identical checkpoint) runs in
the WSL rehearsal (``rehearse``) because it needs the ANDES environment; the
static tests here pin the seam discipline: every ``R431-SEAM`` line lives
inside the two copied execution functions, and every non-seam body line of
the copies is a verbatim line of the frozen R428 source functions.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_runner() -> pytest.ModuleType:
    import importlib.util

    import sys

    for _p in (ROOT, ROOT / "src", ROOT / "scripts"):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
    spec = importlib.util.spec_from_file_location(
        "run_r431_sac_slew", ROOT / "scripts/run_r431_sac_slew.py"
    )
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
    """Flatten the named function's body into leaf statements (Assign,
    Expr, AugAssign, Break, Pass, Return, ...), skipping docstrings."""
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
                    continue  # docstring / standalone string
                leaves.append((ast.dump(sub), sub))
            return leaves
    raise AssertionError(f"function {name} not found in {path}")


def test_contract_shape() -> None:
    runner = _load_runner()
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403, 404, 405]
    assert runner.base.training_run_count(contract) == 15
    # 4 evaluation profiles x 2 scenarios x (3 arms x 5 seeds + 1
    # deterministic) = 8 x 16 records.
    assert runner.base.evaluation_record_count(contract) == 384
    assert contract["engineering_successor"]["sac_slew_projection"] is True


def test_authority_checks_pass() -> None:
    runner = _load_runner()
    checks = runner.authority_checks()
    # Lifecycle-aware wiring checks: active_plan reflects the plan
    # frontmatter state (False once the round is closed), output_absence
    # reflects whether the formal results root exists (R403 precedent).
    plan_text = (ROOT / "memory/rounds/R431/plan.md").read_text(encoding="utf-8")
    plan_active = "state: active" in plan_text
    assert checks["active_plan"] == plan_active
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
    assert "output_absence" in checks
    assert checks["output_absence"] == (not runner.OUT.exists())


def test_output_root_probe_passes() -> None:
    runner = _load_runner()
    probe = runner.output_root_probe()
    assert probe["passed"] is True
    resolved = set(probe["resolved"].values())
    assert len(resolved) == 1
    assert probe["expected"] in resolved


def test_parser_commands() -> None:
    runner = _load_runner()
    parser = runner._parser()
    commands = parser.parse_args(["shard", "train|cd_matd3_message|401"])
    assert commands.command == "shard"
    assert commands.shard_id == "train|cd_matd3_message|401"


@pytest.mark.parametrize(
    ("copy_name", "frozen_name", "frozen_path", "drop_frozen", "drop_copy"),
    [
        (
            "_train_sac_arm_seed_projected",
            "_train_sac_arm_seed",
            ROOT / "scripts/run_r428_c1_sac.py",
            lambda dump: dump.startswith(
                "Assign(targets=[Name(id='action_dict', ctx=Store())]"
            ),
            lambda dump: False,
        ),
        (
            "_evaluate_arm_seed_projected",
            "_evaluate_arm_seed",
            ROOT / "scripts/run_r428_c1_sac.py",
            lambda dump: dump.startswith(
                "Assign(targets=[Name(id='action', ctx=Store())]"
            )
            and "value=Call(func=Attribute(value=Name(id='agent', ctx=Load()), attr='act'"
            in dump,
            lambda dump: False,
        ),
    ],
)
def test_copy_seam_discipline(
    copy_name: str,
    frozen_name: str,
    frozen_path: Path,
    drop_frozen: object,
    drop_copy: object,
) -> None:
    """Every non-seam leaf statement of the copy must be a verbatim leaf
    statement of the frozen source (wrapping-insensitive); declared rewrites
    are excluded on both sides; fully seam-marked additions are excluded on
    the copy side."""
    from collections import Counter

    runner_path = ROOT / "scripts/run_r431_sac_slew.py"
    copy_stmts = _leaf_statements(runner_path, copy_name)
    frozen_stmts = [
        dump
        for dump, _node in _leaf_statements(frozen_path, frozen_name)
        if not drop_frozen(dump)  # type: ignore[operator]
    ]

    seam_marker = "R431-SEAM"
    text = runner_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept = []
    for dump, node in copy_stmts:
        source_lines = lines[node.lineno - 1 : node.end_lineno]
        fully_marked = bool(source_lines) and all(
            seam_marker in line for line in source_lines
        )
        if fully_marked or drop_copy(dump):  # type: ignore[operator]
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
    text = (ROOT / "scripts/run_r431_sac_slew.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    copy_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_train_sac_arm_seed_projected",
            "_evaluate_arm_seed_projected",
        }:
            copy_ranges.append((node.lineno, node.end_lineno))
    # Lines inside string literals (docstrings/comments) are excluded.
    string_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_ranges.append((node.lineno, node.end_lineno))
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if "R431-SEAM" not in line:
            continue
        in_string = any(start <= index <= end for start, end in string_ranges)
        if in_string:
            continue
        assert any(start <= index <= end for start, end in copy_ranges), (
            f"R431-SEAM marker outside the copied functions at line {index}"
        )
