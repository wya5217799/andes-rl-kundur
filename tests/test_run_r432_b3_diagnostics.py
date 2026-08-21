"""R432 B3 diagnostics runner tests: contract, authority, shard grammar,
seam discipline (log-only persistence, zero RNG consumption by construction).

The bitcheck (short-budget frozen-vs-copy byte-identical checkpoint) runs in
the WSL rehearsal because it needs the ANDES environment; the static tests
here pin that every non-log statement of the copy is a verbatim statement of
the frozen R410 ``train_arm_seed`` (wrapping-insensitive) and that the
declared log statements are fully marked ``R432-LOG`` with no RNG calls.
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
        "run_r432_b3_diagnostics", ROOT / "scripts/run_r432_b3_diagnostics.py"
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
    """Flatten the named function's body into leaf statements, skipping
    docstrings."""
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


def test_contract_and_authority() -> None:
    runner = _load_runner()
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    checks = runner.authority_checks()
    # Lifecycle-aware wiring checks: active_plan reflects the plan
    # frontmatter state (False once the round is closed), output_absence
    # reflects whether the formal results root exists (R403 precedent).
    plan_text = (ROOT / "memory/rounds/R432/plan.md").read_text(encoding="utf-8")
    plan_active = "state: active" in plan_text
    assert checks["active_plan"] == plan_active
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
    # output_absence is a pre-launch guard: True only before the formal
    # results root exists (R403 precedent keeps key presence; after the
    # formal wave the guard is expected False by design).
    assert "output_absence" in checks
    assert checks["output_absence"] == (not runner.OUT.exists())


def test_shard_grammar() -> None:
    runner = _load_runner()
    assert runner._parser().parse_args(
        ["shard", "train|cd_matd3_message|401"]
    ).shard_id == "train|cd_matd3_message|401"


def test_copy_seam_discipline() -> None:
    """Every non-log leaf statement of the copy is a verbatim leaf statement
    of the frozen R410 train_arm_seed; declared rewrites are excluded on
    both sides; fully R432-LOG-marked statements are excluded on the copy
    side."""
    from collections import Counter

    runner_path = ROOT / "scripts/run_r432_b3_diagnostics.py"
    frozen_path = ROOT / "scripts/run_r410_message_repair.py"
    copy_stmts = _leaf_statements(runner_path, "train_arm_seed")
    frozen_stmts = [
        dump
        for dump, _node in _leaf_statements(frozen_path, "train_arm_seed")
        if "total_interaction_steps" not in dump
    ]

    text = runner_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept = []
    for dump, node in copy_stmts:
        source_lines = lines[node.lineno - 1 : node.end_lineno]
        fully_marked = bool(source_lines) and all(
            "R432-LOG" in line for line in source_lines
        )
        declared_rewrite = "diagnostics_csv_sha256" in dump or "episode_log_rows" in dump
        if fully_marked or declared_rewrite:
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


def test_log_seam_consumes_no_rng() -> None:
    text = (ROOT / "scripts/run_r432_b3_diagnostics.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    rng_names = {
        "np.random",
        "np.random.random",
        "np.random.rand",
        "np.random.randn",
        "torch.rand",
        "torch.randn",
        "random.random",
        "random.randint",
        "random.uniform",
        "random.gauss",
        "random.seed",
        "np.random.seed",
        "torch.manual_seed",
        ".sample(",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "train_arm_seed":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    source = text.splitlines()[sub.lineno - 1]
                    if "R432-LOG" not in source:
                        continue
                    func = sub.value.func
                    name = (
                        ast.unparse(func)
                        if isinstance(func, ast.Attribute)
                        else func.id if isinstance(func, ast.Name) else ""
                    )
                    assert name not in rng_names, (
                        f"R432-LOG line consumes RNG: {source.strip()}"
                    )
