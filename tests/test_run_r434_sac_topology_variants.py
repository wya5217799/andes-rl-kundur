"""R434 runner tests: contract shape, variant seam discipline, parser.

The variant-env probes and the real evaluation steps run in the WSL
rehearsal (``rehearse``); the static tests here pin (a) the seam
discipline — every ``R434-SEAM`` line lives inside the copied execution
functions and every non-seam body line of the copies is a verbatim line
of the frozen R433/R428 source functions — and (b) the frozen variant
list, the shard manifest shape, and the authority lifecycle awareness.
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
    runner = _load_runner("r434", "scripts/run_r434_sac_topology_variants.py")
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403, 404, 405]
    assert contract["engineering_successor"]["successor_of"] == "R433"
    assert contract["engineering_successor"]["evaluation_only"] is True
    assert contract["engineering_successor"]["training_authorized"] is False
    tve = contract["topology_variant_evaluation"]
    assert len(tve["variant_ids"]) == 10
    assert tve["variant_ids"][0] == "nominal"
    assert "out_Line_7_12" not in tve["variant_ids"]
    assert "out_Line_9_15" not in tve["variant_ids"]
    assert set(tve["evaluation_arms"]) == {
        "cd_matd3_message",
        "cd_matd3_no_message",
    }


def test_variant_list_frozen() -> None:
    runner = _load_runner("r434", "scripts/run_r434_sac_topology_variants.py")
    assert runner.EIG_SOUND_VARIANTS == (
        "nominal",
        "out_Line_4",
        "out_Line_5",
        "out_Line_7",
        "out_Line_8",
        "x0p5_Line_4",
        "x1p5_Line_4",
        "x0p5_Line_7",
        "x1p5_Line_7",
        "x1p5_Line_7_12",
    )
    assert len(runner.EVAL_ARMS) == 2


def test_authority_checks_pass() -> None:
    plan_path = ROOT / "memory/rounds/R434/plan.md"
    if not plan_path.is_file():
        pytest.skip("R434 plan not reserved yet; authority checks need the plan")
    runner = _load_runner("r434", "scripts/run_r434_sac_topology_variants.py")
    checks = runner.authority_checks()
    plan_text = plan_path.read_text(encoding="utf-8")
    plan_active = "state: active" in plan_text and "R434" in plan_text
    assert checks["active_plan"] == plan_active
    assert checks["active_line"] is True
    assert checks["contract_closed"] is True
    assert "output_absence" in checks
    assert checks["output_absence"] == (not runner.OUT.exists())


def test_parser_commands() -> None:
    runner = _load_runner("r434", "scripts/run_r434_sac_topology_variants.py")
    parser = runner._parser()
    args = parser.parse_args(["rehearse"])
    assert args.command == "rehearse"
    args = parser.parse_args(["shard", "eval|cd_matd3_message|401|out_Line_4"])
    assert args.command == "shard"
    phase, arm_id, seed, variant_id = runner._parse_shard(args.shard_id)
    assert (phase, arm_id, seed, variant_id) == (
        "eval",
        "cd_matd3_message",
        401,
        "out_Line_4",
    )
    phase, arm_id, seed, variant_id = runner._parse_shard(
        "eval|local_neighbour_md_km2_kd2|none|x1p5_Line_7_12"
    )
    assert seed is None
    assert variant_id == "x1p5_Line_7_12"
    with pytest.raises(ValueError):
        runner._parse_shard("eval|cd_matd3_message|401|out_Line_7_12")  # unsound
    with pytest.raises(ValueError):
        runner._parse_shard("eval|cd_matd3_message|401")  # 3-part id


def test_shards_manifest_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    runner = _load_runner("r434", "scripts/run_r434_sac_topology_variants.py")
    monkeypatch.setattr(runner, "_assert_wsl_scratch", lambda: None)
    path = Path(runner.shards())
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        assert len(rows) == 110
        assert rows[0] == "eval|cd_matd3_message|401|nominal"
        assert rows[-1] == "eval|local_neighbour_md_km2_kd2|none|x1p5_Line_7_12"
        for variant_id in runner.EIG_SOUND_VARIANTS:
            eval_rows = [row for row in rows if row.endswith(f"|{variant_id}")]
            assert len(eval_rows) == 11  # 2 arms x 5 seeds + reference
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("copy_name", "frozen_path", "frozen_name", "frozen_marker"),
    [
        (
            "_evaluate_arm_seed_variant",
            ROOT / "scripts/run_r433_sac_stress_penalty.py",
            "_evaluate_arm_seed_projected",
            "R433-SEAM",
        ),
        (
            "_build_env_variant",
            ROOT / "scripts/run_r428_c1_sac.py",
            "_build_env",
            "R434-SEAM",
        ),
    ],
)
def test_copy_seam_discipline(
    copy_name: str,
    frozen_path: Path,
    frozen_name: str,
    frozen_marker: str,
) -> None:
    """Every non-seam leaf statement of the copy must be a verbatim leaf
    statement of the frozen source (wrapping-insensitive); declared
    rewrites are excluded on both sides; fully seam-marked additions are
    excluded on the copy side."""
    from collections import Counter

    runner_path = ROOT / "scripts/run_r434_sac_topology_variants.py"
    copy_stmts = _leaf_statements(runner_path, copy_name)
    frozen_stmts = [
        dump
        for dump, node in _leaf_statements(frozen_path, frozen_name)
        if _not_fully_seam_marked(frozen_path, node, frozen_marker)
    ]

    seam_marker = "R434-SEAM"
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
    text = (ROOT / "scripts/run_r434_sac_topology_variants.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(text)
    copy_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_evaluate_arm_seed_variant",
            "_build_env_variant",
        }:
            copy_ranges.append((node.lineno, node.end_lineno))
    string_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_ranges.append((node.lineno, node.end_lineno))
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if "R434-SEAM" not in line:
            continue
        in_string = any(start <= index <= end for start, end in string_ranges)
        if in_string:
            continue
        assert any(start <= index <= end for start, end in copy_ranges), (
            f"R434-SEAM marker outside the copied functions at line {index}"
        )
