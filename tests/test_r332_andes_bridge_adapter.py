from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r332_andes_bridge_reconciliation.py"


def _module():
    spec = importlib.util.spec_from_file_location("r332_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R332 adapter")
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
            "tds": {
                "path": "/official/andes/routines/tds.py",
                "sha256": "224ff43d78de8e6808efa0a6b858d8dbe2ca511128a90a8260009c8146d6e8ba",
            },
            "discrete": {
                "path": "/official/andes/core/discrete.py",
                "sha256": "93bc2c82379fef80f157e5916b20437d82afb2381bba5b5730c2d4a1877c73fc",
            },
            "group": {
                "path": "/official/andes/models/group.py",
                "sha256": "139e172b31e96fa7e92ee8909feca704253702a3e9b5ea6c3df12b54d46b9697",
            },
        },
        "semantic_facts": {
            "esd1_lower_bound_is_minus_pmx": True,
            "ipul_has_no_lower_saturation_term": True,
            "achieved_power_is_voltage_times_ipout": True,
            "tds_store_precedes_switch": True,
            "limiter_lower_flag_excludes_inside_flag": True,
            "set_paux_writes_pext0_absolute_system_base": True,
        },
    }


def test_r332_reconciliation_exposes_exact_blocker_and_qualifications() -> None:
    module = _module()
    payload = module.build_reconciliation(_installed_identity())
    rows = {row["id"]: row for row in payload["mapping_rows"]}
    result = module.evaluate_bridge_reconciliation(payload)

    assert result["classification"] == "BLOCK"
    assert result["blocking_mapping_ids"] == ["disturbance_and_initialization"]
    assert set(result["qualification_ids"]) == {
        "action_mapping",
        "feasibility_limits",
        "platform_scope",
        "sample_timing",
        "storage_dynamics",
    }
    assert any(
        locator.endswith("model_first_env.py:200")
        for locator in rows["device_identity"]["implementation_locators"]
    )
    assert any(
        locator.endswith("model_first_constrained_qp.py:310")
        for locator in rows["action_mapping"]["implementation_locators"]
    )
    assert "Psum > -pmx + epsilon" in rows["feasibility_limits"]["sign"]
    assert (
        "v * Ipout_y, not Pext0, Psum, or Ipcmd"
        in rows["delivered_outputs"]["reduced_model_meaning"]
    )
    assert "stored pre-switch exact-event row" in rows["sample_timing"]["claim_ceiling_consequence"]
    assert module.OFFICIAL_TDS_SOURCE in rows["sample_timing"]["official_locators"]
    assert module.OFFICIAL_DISCRETE_SOURCE in rows["feasibility_limits"]["official_locators"]
    assert module.OFFICIAL_GROUP_SOURCE in rows["action_mapping"]["official_locators"]


def test_r332_static_semantics_are_bound_to_current_sources() -> None:
    guards = _module()._static_repo_semantics()
    assert all(guards.values()), guards


def test_r332_detector_catches_hidden_md_write(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    original = module._read

    def mutated(path: str) -> str:
        source = original(path)
        if path.endswith("model_first_env.py"):
            return source.replace(
                "self.ss.DG.set_paux(self.ss, bess_idx, float(command))",
                "self.ss.GENCLS.set('M', bess_idx, float(command), attr='v')",
            )
        return source

    monkeypatch.setattr(module, "_read", mutated)
    assert module._static_repo_semantics()["no_hidden_md_write"] is False


def test_r332_detector_catches_requested_as_achieved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    original = module._read

    def mutated(path: str) -> str:
        source = original(path)
        if path.endswith("model_first_env.py"):
            return source.replace(
                '"bess_actual_power_system_pu": actual_power.copy()',
                '"bess_actual_power_system_pu": requested.copy()',
            )
        return source

    monkeypatch.setattr(module, "_read", mutated)
    guard = "requested_projected_internal_achieved_distinguished"
    assert module._static_repo_semantics()[guard] is False


def test_r332_detector_catches_reversed_incidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    original = module.active_power_incidence
    monkeypatch.setattr(module, "active_power_incidence", lambda: -original())
    assert module._static_repo_semantics()["active_power_incidence_sign_correct"] is False


def test_r332_detector_catches_over_ceiling_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    original = module._read

    def mutated(path: str) -> str:
        source = original(path)
        if path.endswith("R332/plan.md"):
            return source.replace("No performance, EMT, hardware", "Performance, EMT, hardware")
        return source

    monkeypatch.setattr(module, "_read", mutated)
    assert module._static_repo_semantics()["platform_claim_ceiling_respected"] is False


@pytest.mark.parametrize("source", ("esd1", "tds", "discrete", "group"))
def test_r332_rejects_each_unpinned_source_family(source: str) -> None:
    module = _module()
    installed = _installed_identity()
    installed["sources"][source]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="source identity or semantics"):
        module.build_reconciliation(installed)


@pytest.mark.parametrize(
    "fact",
    (
        "ipul_has_no_lower_saturation_term",
        "tds_store_precedes_switch",
        "limiter_lower_flag_excludes_inside_flag",
        "set_paux_writes_pext0_absolute_system_base",
    ),
)
def test_r332_rejects_each_pinned_semantic_family(fact: str) -> None:
    module = _module()
    installed = _installed_identity()
    installed["semantic_facts"][fact] = False
    with pytest.raises(RuntimeError, match="source identity or semantics"):
        module.build_reconciliation(installed)


def test_r332_prepare_analyse_create_only_and_two_pass_reproducible(
    tmp_path: Path,
) -> None:
    module = _module()
    installed = _installed_identity()
    roots = [tmp_path / "pass_a", tmp_path / "pass_b"]
    created_utc = "2026-08-04T00:00:00+00:00"

    for root in roots:
        seal = root / "seal.json"
        out = root / "out"
        seal_digest = module.prepare(
            seal,
            installed_identity=installed,
            created_utc=created_utc,
        )
        module.analyse(
            seal,
            seal_digest,
            out,
            installed_identity=installed,
            created_utc=created_utc,
        )
        with pytest.raises(FileExistsError):
            module.prepare(seal, installed_identity=installed)
        with pytest.raises(FileExistsError):
            module.analyse(
                seal,
                seal_digest,
                out,
                installed_identity=installed,
                created_utc=created_utc,
            )

    for relative in (
        "seal.json",
        "out/analysis.json",
        "out/provenance.json",
        "out/run_manifest.json",
    ):
        assert (roots[0] / relative).read_bytes() == (roots[1] / relative).read_bytes()
    assert (
        json.loads((roots[0] / "seal.json").read_text(encoding="utf-8"))[
            "reconciliation_payload_sha256"
        ]
        == json.loads((roots[1] / "seal.json").read_text(encoding="utf-8"))[
            "reconciliation_payload_sha256"
        ]
    )


def test_r332_cli_has_prepare_and_analyse_only() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")
    assert set(action.choices) == {"prepare", "analyse"}
