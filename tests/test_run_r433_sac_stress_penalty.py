"""R433 runner tests: contract shape, penalty direction, seam discipline.

The bitcheck and the penalty gradient-direction probe run in the WSL
rehearsal (``rehearse``); the static tests here pin (a) the seam
discipline — every ``R433-SEAM`` line lives inside the copied execution
functions and every non-seam body line of the copies is a verbatim line
of the frozen R431 source functions — and (b) the penalty-term direction
(p = -mean_j(a^2) means descent toward smaller action magnitude).
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


def _not_fully_seam_marked(path: Path, node: ast.stmt, marker: str) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    source_lines = lines[node.lineno - 1 : node.end_lineno]
    return not (bool(source_lines) and all(marker in line for line in source_lines))


def test_contract_shape() -> None:
    runner = _load_runner("r433", "scripts/run_r433_sac_stress_penalty.py")
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403, 404, 405]
    assert runner.base.training_run_count(contract) == 15
    assert contract["engineering_successor"]["successor_of"] == "R431"
    asp = contract["engineering_successor"]["action_stress_penalty"]
    assert asp["form"].startswith("r_i' = r_i + lambda_p * p_i")
    assert asp["scope"] == "training-only"
    assert isinstance(asp["lambda_p"], float)


def test_penalty_direction() -> None:
    """p_i = -mean_j(a_ij^2): analytic and numeric gradient point along -a;
    with lambda_p > 0 the penalized reward is <= the plain reward."""
    import numpy as np

    runner = _load_runner("r433", "scripts/run_r433_sac_stress_penalty.py")
    runner.LAMBDA_P = 10.0
    joint = np.zeros((4, 7), dtype=np.float32)
    delta = np.zeros(4)
    a = np.array([[0.3, -0.4], [0.1, 0.2], [-0.5, 0.6], [0.2, 0.1]], dtype=np.float32)
    r_plain = runner._sac_step_rewards(joint, delta, delta, masked=False)
    r_pen = runner._sac_step_rewards_penalized(
        joint, delta, delta, masked=False, action=a
    )
    assert np.all(r_pen <= r_plain + 1e-9)
    assert np.all(r_plain - r_pen >= 0)  # penalty never increases reward
    assert np.all(r_plain - r_pen > 0)  # nonzero actions -> strict penalty
    # per-agent penalty equals -lambda * mean(a^2)
    expected = -10.0 * np.mean(a**2, axis=1)
    assert np.allclose(r_pen - r_plain, expected, atol=1e-6)
    # gradient direction on a single component pair
    lam = 10.0
    av = np.array([0.30, -0.40])
    grad_analytic = -lam * av
    eps = 1e-6
    grad_numeric = np.zeros(2)
    for j in range(2):
        step = np.zeros(2)
        step[j] = eps
        p_plus = -float(np.mean((av + step) ** 2))
        p_minus = -float(np.mean((av - step) ** 2))
        grad_numeric[j] = lam * (p_plus - p_minus) / (2.0 * eps)
    assert np.all(np.sign(grad_analytic) == np.sign(-av))
    assert np.all(np.sign(grad_numeric) == np.sign(-av))
    assert np.allclose(grad_numeric, grad_analytic, atol=1e-6)


def test_authority_checks_pass() -> None:
    runner = _load_runner("r433", "scripts/run_r433_sac_stress_penalty.py")
    checks = runner.authority_checks()
    plan_text = (ROOT / "memory/rounds/R433/plan.md").read_text(encoding="utf-8")
    plan_active = "state: active" in plan_text
    assert checks["active_plan"] == plan_active
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
    assert "output_absence" in checks
    assert checks["output_absence"] == (not runner.OUT.exists())


def test_parser_commands() -> None:
    runner = _load_runner("r433", "scripts/run_r433_sac_stress_penalty.py")
    parser = runner._parser()
    args = parser.parse_args(["dev-lambda"])
    assert args.command == "dev-lambda"
    args = parser.parse_args(["shard", "train|cd_matd3_message|401"])
    assert args.command == "shard"
    assert args.shard_id == "train|cd_matd3_message|401"


@pytest.mark.parametrize(
    ("copy_name", "frozen_path", "frozen_name", "marker"),
    [
        (
            "_train_sac_arm_seed_projected",
            ROOT / "scripts/run_r431_sac_slew.py",
            "_train_sac_arm_seed_projected",
            "R431-SEAM",
        ),
        (
            "_evaluate_arm_seed_projected",
            ROOT / "scripts/run_r431_sac_slew.py",
            "_evaluate_arm_seed_projected",
            "R431-SEAM",
        ),
    ],
)
def test_copy_seam_discipline(
    copy_name: str, frozen_path: Path, frozen_name: str, marker: str
) -> None:
    """Every non-seam leaf statement of the copy must be a verbatim leaf
    statement of the frozen R431 source (wrapping-insensitive); declared
    rewrites are excluded on both sides; fully seam-marked additions are
    excluded on the copy side."""
    from collections import Counter

    runner_path = ROOT / "scripts/run_r433_sac_stress_penalty.py"
    copy_stmts = _leaf_statements(runner_path, copy_name)
    frozen_stmts = [
        dump
        for dump, node in _leaf_statements(frozen_path, frozen_name)
        if _not_fully_seam_marked(frozen_path, node, marker)
    ]

    seam_marker = "R433-SEAM"
    kept = []
    for dump, node in copy_stmts:
        if not _not_fully_seam_marked(runner_path, node, seam_marker):
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
    text = (ROOT / "scripts/run_r433_sac_stress_penalty.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(text)
    copy_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_train_sac_arm_seed_projected",
            "_evaluate_arm_seed_projected",
            "_sac_step_rewards_penalized",
        }:
            copy_ranges.append((node.lineno, node.end_lineno))
    string_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_ranges.append((node.lineno, node.end_lineno))
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if "R433-SEAM" not in line:
            continue
        in_string = any(start <= index <= end for start, end in string_ranges)
        if in_string:
            continue
        assert any(start <= index <= end for start, end in copy_ranges), (
            f"R433-SEAM marker outside the copied functions at line {index}"
        )
