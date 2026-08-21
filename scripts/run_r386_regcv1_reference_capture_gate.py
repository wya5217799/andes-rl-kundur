"""Run the sealed R386 pre-init static-reference capture correction.

Motivation:
    R386 reuses the reviewed R385 lifecycle and scientific gate. Its only
    scientific-code change is to freeze linked StaticGen p/q immediately after
    a successful power flow and before TDS initialization.

Usage:
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r386_regcv1_reference_capture_gate.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r386_regcv1_reference_capture_gate.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r386_regcv1_reference_capture_gate.py execute \
        --expected-seal-sha256 <sha256>

Failure modes:
    Provenance, capture timing/schema, diagnostics, source-to-comparison
    identity, runtime, or create-only collision failures are ANALYSIS-INVALID.
    A complete formal record that fails a native solver or scientific guard is
    STOP. R386 has no retry, controller, training, or overwrite command.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.regcv1_reference_gate import (  # noqa: E402
    build_reference_contract,
    classify_regcv1_reference_record,
)

BASE_RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"
_base_spec = importlib.util.spec_from_file_location("r386_r385_lifecycle", BASE_RUNNER)
if _base_spec is None or _base_spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load lifecycle base: {BASE_RUNNER}")
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)

ROUND_ID = "R386"
QUESTION_ID = "Q-0105"
LINE_ID = "converter-vsg-pq-decoupling"
PLAN = ROOT / "memory/rounds/R386/plan.md"
QUESTION = ROOT / "memory/questions/Q-0105.md"
REHEARSAL = ROOT / "memory/rounds/R386/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R386/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R386/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r386_regcv1_reference_capture_gate"


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "lifecycle_base": BASE_RUNNER,
        "builder": ROOT / "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_reference_gate.py",
        "base_classifier": ROOT
        / "src/andes_rl_kundur/evaluation/regcv1_clean_init_gate.py",
        "builder_tests": ROOT / "tests/test_regcv1_static_kundur.py",
        "classifier_tests": ROOT / "tests/test_regcv1_reference_gate.py",
        "runner_tests": ROOT
        / "tests/test_r386_regcv1_reference_capture_gate.py",
        "base_classifier_tests": ROOT / "tests/test_regcv1_clean_init_gate.py",
        "base_runner_tests": ROOT / "tests/test_r385_regcv1_clean_init_gate.py",
        "plan": PLAN,
        "question": QUESTION,
        "line": ROOT / "paper/converter_vsg_pq_decoupling/LINE.md",
        "route_contract": ROOT
        / "paper/converter_vsg_pq_decoupling/working/route_contract.md",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r385_claim": ROOT / "memory/claims/CLM-1070.md",
        "r385_feed": ROOT / "paper/converter_vsg_pq_decoupling/reports/R385.md",
        "r385_verdict": ROOT / "memory/rounds/R385/verdict.md",
        "successor_adr": ROOT
        / "docs/adr/0017-structural-absence-regcv1-successor.md",
        "line_adr": ROOT / "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md",
    }
    return {
        name: {"path": base.relative(path), "sha256": base.sha256_file(path)}
        for name, path in parents.items()
    }


def capture_reference_source(
    system: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    expected = contract["expected_mapping"]
    idxes = [row["gen"] for row in expected]
    static_p = system.StaticGen.get(src="p", idx=idxes, attr="v")
    static_q = system.StaticGen.get(src="q", idx=idxes, attr="v")
    rows = [
        {
            "idx": str(expected[position]["idx"]),
            "static_p": float(static_p[position]),
            "static_q": float(static_q[position]),
        }
        for position in range(4)
    ]
    return {
        "captured": True,
        "phase": "post_pflow_pre_tds_init",
        "pflow_converged_at_capture": True,
        "tds_initialized_at_capture": False,
        "rows": rows,
    }


def post_init_references(
    system: Any,
    reference_source: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    tol = float(contract["reference_abs_tolerance"])
    rows: list[dict[str, Any]] = []
    for position, source in enumerate(reference_source["rows"]):
        pref = float(system.REGCV1.Pref.v[position])
        qref = float(system.REGCV1.Qref.v[position])
        p_value = float(source["static_p"])
        q_value = float(source["static_q"])
        rows.append(
            {
                "idx": str(source["idx"]),
                "static_p": p_value,
                "static_q": q_value,
                "pref": pref,
                "qref": qref,
                "pref_match": math.isclose(pref, p_value, rel_tol=0.0, abs_tol=tol),
                "qref_match": math.isclose(qref, q_value, rel_tol=0.0, abs_tol=tol),
            }
        )
    return {"checked": True, "absolute_tolerance": tol, "rows": rows}


def run_formal_record(
    contract: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    record = base.empty_record(base.payload_sha256(contract))
    record["reference_source"] = {
        "captured": False,
        "phase": None,
        "pflow_converged_at_capture": False,
        "tds_initialized_at_capture": False,
        "rows": [],
    }
    system: Any | None = None
    initial: dict[str, Any] | None = None
    trajectory_start_time: float | None = None
    try:
        audit = base.load_verified_static_case(
            xlsx_path=runtime["xlsx_case_path"],
            json_path=runtime["json_case_path"],
        )
        built = base.build_regcv1_static_kundur_object(
            full_case=audit.full_case,
            work_dir=Path.cwd(),
        )
        system = built.system
        record["source"] = {
            "xlsx_json_static_equal": audit.xlsx_json_static_equal,
            "xlsx_case_sha256": audit.xlsx_sha256,
            "json_case_sha256": audit.json_sha256,
            "derived_case_sha256": built.derived_case_sha256,
            "derived_case_deterministic": built.derived_case_sha256
            == runtime["derived_case_sha256"],
        }
        record["inventory"] = {
            "network": built.network_inventory,
            "forbidden_model_counts": built.forbidden_model_counts,
            "forbidden_dae_names": [],
            "regcv1": base.regcv1_inventory(system),
        }
        record["solver"]["tds_tolerance"] = float(system.TDS.config.tol)
        system.setup()
        record["solver"]["setup_completed"] = True
        record["inventory"]["regcv1"] = base.regcv1_inventory(system)
        record["inventory"]["forbidden_model_counts"] = base.forbidden_model_counts(
            system, contract["forbidden_models"]
        )

        pflow_return = system.PFlow.run()
        record["solver"]["pflow_converged"] = bool(pflow_return)
        if not pflow_return:
            record["scientific_error"] = "PFlow.run returned a non-success value"
            diagnostics = base.capture_initialization_diagnostics(system)
            record["initialization_diagnostics"] = diagnostics
            if diagnostics["captured"] is not True:
                raise RuntimeError(
                    "initialization diagnostic capture failed after PFlow failure: "
                    f"{diagnostics.get('capture_error', 'unknown error')}"
                )
            return record

        reference_source = capture_reference_source(system, contract)
        record["reference_source"] = reference_source
        system.TDS.config.tf = float(contract["tds_tf_seconds"])
        init_return = system.TDS.init()
        record["solver"]["tds_initialized"] = init_return is not False
        record["solver"]["tds_test_ok"] = system.TDS.test_ok is True
        record["inventory"]["forbidden_dae_names"] = base.forbidden_dae_names(
            system, contract["forbidden_models"]
        )
        diagnostics = base.capture_initialization_diagnostics(system)
        record["initialization_diagnostics"] = diagnostics
        if diagnostics["captured"] is not True:
            raise RuntimeError(
                "initialization diagnostic capture failed: "
                f"{diagnostics.get('capture_error', 'unknown error')}"
            )
        record["references"] = post_init_references(system, reference_source, contract)
        if not (
            record["solver"]["tds_initialized"]
            and record["solver"]["tds_test_ok"]
        ):
            record["scientific_error"] = "native TDS initialization guard failed"
            return record

        initial = base.signal_snapshot(system, contract["drift_signals"])
        trajectory_start_time = float(system.dae.t)
        record["trajectory_attempted"] = True
        system.TDS.run()
        terminal_time = float(system.dae.t)
        record["solver"]["terminal_time_seconds"] = terminal_time
        if terminal_time > trajectory_start_time:
            record["physical_trajectory_executed"] = True
            record["trajectory_count"] = 1
        record["solver"]["tds_converged"] = bool(system.TDS.converged)
        terminal = base.signal_snapshot(system, contract["drift_signals"])
        dae_finite, model_finite = base.finite_guards(system)
        record["finite_guard"] = {
            "checked": True,
            "dae_finite": dae_finite,
            "regcv1_finite": model_finite,
        }
        record["drift"] = {
            "checked": True,
            "max_abs_by_signal": {
                name: float(base.np.max(base.np.abs(terminal[name] - initial[name])))
                for name in contract["drift_signals"]
            },
        }
    except Exception as exc:
        record["execution_error"] = f"{type(exc).__name__}: {exc}"
        if system is not None:
            record["initialization_diagnostics"] = (
                base.capture_initialization_diagnostics(system)
            )
            try:
                record["inventory"]["forbidden_dae_names"] = base.forbidden_dae_names(
                    system, contract["forbidden_models"]
                )
                terminal_time = float(system.dae.t)
                record["solver"]["terminal_time_seconds"] = terminal_time
                if (
                    record["trajectory_attempted"] is True
                    and trajectory_start_time is not None
                    and terminal_time > trajectory_start_time
                ):
                    record["physical_trajectory_executed"] = True
                    record["trajectory_count"] = 1
                dae_finite, model_finite = base.finite_guards(system)
                record["finite_guard"] = {
                    "checked": True,
                    "dae_finite": dae_finite,
                    "regcv1_finite": model_finite,
                }
                if initial is not None:
                    terminal = base.signal_snapshot(system, contract["drift_signals"])
                    record["drift"] = {
                        "checked": True,
                        "max_abs_by_signal": {
                            name: float(
                                base.np.max(base.np.abs(terminal[name] - initial[name]))
                            )
                            for name in contract["drift_signals"]
                        },
                    }
            except Exception:
                pass
    return record


def _configure_lifecycle() -> None:
    base.ROUND_ID = ROUND_ID
    base.QUESTION_ID = QUESTION_ID
    base.LINE_ID = LINE_ID
    base.PLAN = PLAN
    base.QUESTION = QUESTION
    base.REHEARSAL = REHEARSAL
    base.CAPACITY = CAPACITY
    base.SEAL = SEAL
    base.DEFAULT_OUT = DEFAULT_OUT
    base.build_clean_contract = build_reference_contract
    base.classify_regcv1_clean_init_record = classify_regcv1_reference_record
    base.source_manifest = source_manifest
    base.parent_manifest = parent_manifest
    base.run_formal_record = run_formal_record


_configure_lifecycle()


def execute(*, expected_sha256: str) -> str:
    """Execute through the reused lifecycle with the R386 output root explicit."""

    return base.execute(
        expected_sha256=expected_sha256,
        out_dir=DEFAULT_OUT,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        print(f"rehearsal_sha256={base.rehearse()}")
    elif args.command == "prepare":
        print(f"seal_sha256={base.prepare()}")
    elif args.command == "execute":
        print(
            "analysis_sha256="
            f"{execute(expected_sha256=args.expected_seal_sha256)}"
        )
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
