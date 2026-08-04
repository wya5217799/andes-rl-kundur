from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r331_andes_bridge_reconciliation.py"


def _module():
    spec = importlib.util.spec_from_file_location("r331_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R331 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _installed_identity() -> dict[str, object]:
    return {
        "version": "2.0.0",
        "sources": {
            "gencls": {
                "path": "/official/andes/models/synchronous/gencls.py",
                "sha256": "b9b84d57434b989e7923a2eba197d5ce7122fd7b51c30e4d6ff547ed33797168",
            },
            "esd1": {
                "path": "/official/andes/models/distributed/esd1.py",
                "sha256": "8049088d711d47c3799826c8977fb86e6b0af822b579bc04625d26b584e419cb",
            },
            "pvd1": {
                "path": "/official/andes/models/distributed/pvd1.py",
                "sha256": "56fb6012016b821104df0f38efed0ca2a048635e95872439efadf39534600c95",
            },
        },
        "semantic_facts": {
            "esd1_lower_bound_is_minus_pmx": True,
            "ipul_has_no_lower_saturation_term": True,
            "achieved_power_is_voltage_times_ipout": True,
        },
    }


def test_r331_reconciliation_exposes_the_load_disturbance_blocker() -> None:
    module = _module()
    payload = module.build_reconciliation(_installed_identity())
    rows = {row["id"]: row for row in payload["mapping_rows"]}
    result = module.evaluate_bridge_reconciliation(payload)

    assert result["classification"] == "BLOCK"
    assert rows["disturbance_and_initialization"]["disposition"] == "unsupported"
    assert result["blocking_mapping_ids"] == ["disturbance_and_initialization"]
    assert rows["platform_scope"]["disposition"] == "declared-omission"
    assert rows["action_mapping"]["disposition"] == "declared-assumption"
    assert "externally projected command" in rows["action_mapping"]["reduced_model_meaning"]
    assert rows["sample_timing"]["disposition"] == "declared-assumption"
    assert (
        "strict charging-boundary margin" in rows["feasibility_limits"]["claim_ceiling_consequence"]
    )
    assert payload["scope_guards"] == {
        "physical_execution_performed": False,
        "controller_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }


def test_r331_static_repo_semantics_are_bound_to_current_sources() -> None:
    module = _module()
    guards = module._static_repo_semantics()

    assert all(guards.values()), guards
    assert set(guards) == {
        "no_hidden_md_write",
        "requested_projected_internal_achieved_distinguished",
        "active_power_incidence_sign_correct",
        "physical_frequency_base_60_hz",
        "sample_order_and_delay_explicit",
        "disturbance_and_initialization_explicit",
        "all_feasibility_limits_explicit",
        "reduced_latent_state_not_claimed_as_physical_readback",
        "platform_claim_ceiling_respected",
    }


def test_r331_rejects_unpinned_installed_source_identity() -> None:
    module = _module()
    installed = _installed_identity()
    installed["sources"]["esd1"]["sha256"] = "0" * 64

    with pytest.raises(RuntimeError, match="source identity or semantics"):
        module.build_reconciliation(installed)


def test_r331_prepare_and_analyse_are_create_only(tmp_path: Path) -> None:
    module = _module()
    seal = tmp_path / "seal.json"
    out = tmp_path / "out"
    installed = _installed_identity()

    seal_digest = module.prepare(seal, installed_identity=installed)
    analysis_digest = module.analyse(
        seal,
        seal_digest,
        out,
        installed_identity=installed,
    )

    assert len(seal_digest) == len(analysis_digest) == 64
    analysis, _ = module.read_verified_json(out / "analysis.json")
    manifest, _ = module.read_verified_json(out / "run_manifest.json")
    assert analysis["classification"] == "BLOCK"
    assert analysis["deterministic_replay"] is True
    assert manifest["physical_execution_performed"] is False
    assert manifest["training_executed"] is False
    with pytest.raises(FileExistsError):
        module.prepare(seal, installed_identity=installed)


def test_r331_cli_has_prepare_and_analyse_only() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")
    assert set(action.choices) == {"prepare", "analyse"}
