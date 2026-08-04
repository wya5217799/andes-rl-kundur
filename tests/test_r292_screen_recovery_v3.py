from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from andes_rl_kundur.evaluation.sealed_bank import sha256_file

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/recover_r292_fresh_bank_v3.py"
ORIGINAL_SUMMARY = ROOT / "results/r292_fresh_bank/screen_summary.json"
V2_EVIDENCE = ROOT / "results/r292_fresh_bank_v2/screen_evidence.json"
V3_SUMMARY = ROOT / "results/r292_fresh_bank_v3/screen_summary.json"
FORMAL_TRACES = ROOT / "results/r292_formal_evaluation_v3/traces"


def _load_script():
    spec = importlib.util.spec_from_file_location("recover_r292_fresh_bank_v3", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v3_reaudits_real_immutable_rows_and_passes_bank_guards(
    tmp_path: Path,
) -> None:
    module = _load_script()
    original_before = sha256_file(ORIGINAL_SUMMARY)
    v2_before = sha256_file(V2_EVIDENCE)
    seal = tmp_path / "fresh_bank_screen_v3_seal.json"
    out_dir = tmp_path / "r292_fresh_bank_v3"

    if FORMAL_TRACES.exists() and any(FORMAL_TRACES.glob("*.json")):
        manifest = json.loads(module.DEFAULT_SEAL.read_text(encoding="utf-8"))
        summary = json.loads(V3_SUMMARY.read_text(encoding="utf-8"))
    else:
        module.prepare(seal, out_dir)
        module.analyse(seal, sha256_file(seal), out_dir)
        manifest = json.loads(seal.read_text(encoding="utf-8"))
        summary = json.loads(
            (out_dir / "screen_summary.json").read_text(encoding="utf-8")
        )
    assert manifest["phase"] == "fresh-bank-q0-contract-reaudit-v3"
    assert manifest["execution"]["andes_trajectory_count"] == 0
    assert manifest["execution"]["reused_immutable_trace_count"] == 24
    assert summary["decision"]["classification"] == "PASS"
    assert summary["included_nontriviality"]["scenario_count"] == 24
    assert summary["controller_performance_endpoints_inspected"] is False
    assert sha256_file(ORIGINAL_SUMMARY) == original_before
    assert sha256_file(V2_EVIDENCE) == v2_before
