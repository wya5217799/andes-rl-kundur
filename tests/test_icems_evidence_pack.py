from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/export_icems_evidence_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "export_icems_evidence_pack",
        MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evidence_pack_preserves_registered_decisions() -> None:
    module = _load_module()
    pack = module.build_evidence_pack()

    assert pack["paper_title"] == (
        "Decoupling-Oriented Coordination of Paralleled VSGs With "
        "Multi-Agent Reinforcement Learning"
    )
    assert pack["stages"]["R274"]["decision"]["classification"] == (
        "AUTHORITY-POSITIVE"
    )
    assert pack["stages"]["R275"]["decision"]["classification"] == (
        "FAST-LAYER-POSITIVE"
    )
    assert pack["stages"]["R276"]["decision"]["classification"] == "ADDITIVE-ONLY"
    assert pack["stages"]["R277"]["decision"]["classification"] == (
        "LEARNING-GAP-PRESENT"
    )

    r278 = pack["stages"]["R278"]
    assert r278["original_decision"]["classification"] == "INVALID"
    assert r278["repaired_decision"]["classification"] == "PILOT-NO-GO"
    assert not r278["repaired_decision"]["guards"]["both_primary_endpoints_clear"]
    assert r278["training"]["seed"] == 49
    assert r278["training"]["episodes_completed"] == 300
    assert r278["training"]["total_steps"] == 4500
    assert r278["training"]["algorithm"]["name"] == "shared_area_td3"
    assert r278["training"]["action_and_reward"]["executed_residual"] == (
        "q*[1,1,-1,-1]"
    )


def test_evidence_pack_does_not_promote_partial_marl_result() -> None:
    module = _load_module()
    pack = module.build_evidence_pack()
    manuscript = pack["manuscript_decision"]
    primary = pack["stages"]["R278"]["repaired_decision"]["primary_endpoints"]

    assert manuscript["readiness"] == "CONDITIONAL_HONEST_EVALUATION_ONLY"
    assert manuscript["marl_incremental_value"] == "NO-ADAPTIVE-MARL-VALUE"
    assert not manuscript["positive_marl_superiority_supported"]
    assert not manuscript["three_seed_continuation_authorized"]
    assert not manuscript["fresh_formal_bank_authorized"]
    assert not manuscript["hawe_contribution_authorized"]
    assert primary["normalized_sync_loss_hz2"]["material_improvement"]
    assert not primary["fast_inter_area_iae_hz_s"]["material_improvement"]
    assert primary["fast_inter_area_iae_hz_s"]["ci_upper_percent"] > 0.0


def test_evidence_pack_write_and_check_are_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    output = tmp_path / "evidence.json"

    written_digest = module.write_evidence_pack(output)
    checked_digest = module.check_evidence_pack(output)

    assert written_digest == checked_digest
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert output.with_name(output.name + ".sha256").is_file()


def test_verified_json_accepts_only_git_crlf_materialization(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    path = tmp_path / "evidence.json"
    canonical = b'{\n  "classification": "VALID"\n}\n'
    path.write_bytes(canonical.replace(b"\n", b"\r\n"))
    digest = hashlib.sha256(canonical).hexdigest()
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    payload, verified_digest = module._verified_json(path)

    assert payload == {"classification": "VALID"}
    assert verified_digest == digest


def test_verified_json_rejects_non_eol_content_change(tmp_path: Path) -> None:
    module = _load_module()
    module.ROOT = tmp_path
    path = tmp_path / "evidence.json"
    canonical = b'{\n  "classification": "VALID"\n}\n'
    path.write_bytes(canonical.replace(b"VALID", b"INVALID"))
    digest = hashlib.sha256(canonical).hexdigest()
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        module._verified_json(path)
