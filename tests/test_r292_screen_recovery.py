from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from andes_rl_kundur.evaluation.sealed_bank import sha256_file

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover_r292_fresh_bank.py"
ORIGINAL_SUMMARY = ROOT / "results/r292_fresh_bank/screen_summary.json"
ORIGINAL_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_seal.json"
ROUND_PLAN = ROOT / "memory/rounds/R292/plan.md"
V2_SEAL = ROOT / "memory/rounds/R292/fresh_bank_screen_v2_seal.json"
FORMAL_V2_TRACE_DIR = ROOT / "results/r292_formal_evaluation_v2/traces"


def _load_script():
    spec = importlib.util.spec_from_file_location("recover_r292_fresh_bank", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preserved_v2_seal_records_immutable_trace_reaudit() -> None:
    before = sha256_file(ORIGINAL_SUMMARY)
    payload = json.loads(V2_SEAL.read_text(encoding="utf-8"))
    assert payload["phase"] == "fresh-bank-q0-contract-reaudit-v2"
    assert payload["execution"]["andes_trajectory_count"] == 0
    assert payload["execution"]["reused_immutable_trace_count"] == 24
    assert payload["execution"]["performance_endpoints_inspected"] is False
    assert len(payload["frozen_trace_hashes"]) == 24
    assert payload["original_failed_attempt"]["summary_sha256"] == before
    assert sha256_file(ORIGINAL_SUMMARY) == before
    assert not FORMAL_V2_TRACE_DIR.exists() or not any(
        FORMAL_V2_TRACE_DIR.glob("*.json")
    )


def test_completed_plan_change_is_lifecycle_only() -> None:
    manifest = json.loads(ORIGINAL_SEAL.read_text(encoding="utf-8"))
    expected = manifest["sources"]["plan"]["sha256"]
    current = ROUND_PLAN.read_text(encoding="utf-8")
    active_snapshot = current.replace(
        "state: completed", "state: active", 1
    ).replace(
        "closed: '2026-08-01'", "closed: null", 1
    )
    assert hashlib.sha256(active_snapshot.encode("utf-8")).hexdigest() == expected
    assert hashlib.sha256(
        (active_snapshot + "\nUnauthorized contract body change.\n").encode("utf-8")
    ).hexdigest() != expected
