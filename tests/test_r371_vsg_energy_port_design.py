from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from probes.r371_vsg_energy_port_design import build_design_analysis


def _passing_source_facts() -> dict[str, object]:
    return {
        "andes_version": "2.0.0",
        "source_files": {
            "group": {"path": "/andes/models/group.py", "sha256": "a" * 64},
            "genbase": {
                "path": "/andes/models/synchronous/genbase.py",
                "sha256": "b" * 64,
            },
        },
        "pref_priority_is_turbine_governor": True,
        "pref_fallback_is_tm0": True,
        "set_pref_uses_setpoint_resolver": True,
        "get_pref_uses_setpoint_resolver": True,
        "pref_documented_system_base_pu": True,
        "setpoint_write_targets_value_array": True,
        "omega_equation_uses_tm_minus_te_and_damping": True,
        "tm_equation_is_tm0_minus_tm": True,
    }


def test_design_analysis_passes_only_as_a_nonexecuting_object_contract() -> None:
    analysis = build_design_analysis(_passing_source_facts())

    assert analysis["classification"] == "ENERGY-PORT-DESIGN-PASS"
    assert all(analysis["checks"].values())
    assert analysis["actor_object_contract"] == {
        "actors": 4,
        "owned_objects": "four governor-free GENCLS VSGs",
        "ports": "one SynGen.pref/tm0 input per VSG",
        "mapping": "one-to-one actor-to-VSG-to-port",
        "excluded_objects": ["independent ESD1", "central scalar", "M/D action"],
    }
    assert analysis["power_torque_contract"]["sampled_write"] == (
        "pref = baseline_tm0 + commanded_power / sampled_omega"
    )
    assert analysis["power_torque_contract"]["energy_settlement"] == (
        "achieved_power = (readback_torque - baseline_tm0) * actual_omega"
    )
    assert analysis["physical_execution_authorized"] is False
    assert analysis["training_authorized"] is False
    assert analysis["next_gate"] == "physical_per_vsg_energy_port_object_gate"


def test_design_analysis_stops_if_tm0_is_treated_as_constant_power() -> None:
    facts = _passing_source_facts()
    facts["omega_equation_uses_tm_minus_te_and_damping"] = False

    analysis = build_design_analysis(facts)

    assert analysis["classification"] == "STOP-TORQUE-POWER-CONFLATION"
    assert analysis["checks"]["installed_swing_equation_supports_torque_semantics"] is False
    assert analysis["training_authorized"] is False


def test_probe_writes_create_only_analysis_from_injected_source_facts(
    tmp_path: Path,
) -> None:
    facts_path = tmp_path / "source-facts.json"
    facts_path.write_text(json.dumps(_passing_source_facts()), encoding="utf-8")
    output = tmp_path / "analysis.json"
    command = [
        sys.executable,
        "probes/r371_vsg_energy_port_design.py",
        "--source-facts",
        str(facts_path),
        "--output",
        str(output),
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    repeated = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert output.with_suffix(".json.sha256").is_file()
    assert repeated.returncode != 0
    assert "refusing to overwrite" in repeated.stderr
