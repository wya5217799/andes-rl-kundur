from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes" / "r304_topology_vector_gate.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("r304_topology_vector_gate", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _matrix(module, *, material: bool = True) -> dict:
    oracle_action = {
        "nominal": "e01_pos",
        "line_0_out": "e12_pos",
        "line_9_out": "e23_pos",
    }
    cells = []
    for topology in module.TOPOLOGY_ORDER:
        for action, m_vector in module.ACTION_LIBRARY.items():
            damping = 0.10
            if material:
                damping = 0.101
                if action == oracle_action[topology]:
                    damping = 0.13
            cells.append(
                {
                    "topology": topology,
                    "opened_line": module.OPENED_LINES[topology],
                    "action": action,
                    "m_vector": list(m_vector),
                    "guards": {
                        guard: True for guard in module.REQUIRED_CELL_GUARDS
                    },
                    "identified": {
                        "damping_ratio": damping,
                        "freq_hz": 0.63,
                        "p_vector": [0.4, 0.3, 0.2, 0.1],
                    },
                }
            )
    return {
        "topologies": list(module.TOPOLOGY_ORDER),
        "actions": list(module.ACTION_LIBRARY),
        "cells": cells,
    }


def test_r304_action_library_is_the_r292_single_edge_basis() -> None:
    module = _load_probe()

    assert tuple(module.ACTION_LIBRARY) == (
        "q0",
        "e01_pos",
        "e01_neg",
        "e12_pos",
        "e12_neg",
        "e23_pos",
        "e23_neg",
    )
    assert module.ACTION_LIBRARY["q0"] == (350.0, 350.0, 350.0, 350.0)
    assert module.ACTION_LIBRARY["e12_pos"] == (350.0, 275.0, 425.0, 350.0)
    assert all(sum(values) == pytest.approx(1400.0) for values in module.ACTION_LIBRARY.values())


def test_r304_modal_rule_merges_conjugates_and_selects_area_contrast() -> None:
    module = _load_probe()
    modes = module.merge_conjugate_pairs(
        [
            {
                "freq_hz": 0.63,
                "real": -0.1,
                "damping_ratio": 0.2,
                "p_machines": {"a1": 0.8, "a2": 0.1},
            },
            {
                "freq_hz": 0.63,
                "real": -0.1,
                "damping_ratio": 0.2,
                "p_machines": {"a1": 0.6, "a2": 0.1},
            },
            {
                "freq_hz": 0.9,
                "real": -0.2,
                "damping_ratio": 0.3,
                "p_machines": {"a1": 0.2, "a2": 0.2},
            },
        ]
    )

    identified = module.identify_interarea(
        modes,
        area1_keys=("a1",),
        area2_keys=("a2",),
    )

    assert len(modes) == 2
    assert identified["freq_hz"] == pytest.approx(0.63)
    assert identified["area_contrast"] == pytest.approx(0.6)


@pytest.mark.parametrize(
    ("eval_ready", "expected"),
    [
        (False, "STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY"),
        (True, "STATIC-TOPOLOGY-VALUE-EVAL-READY"),
    ],
)
def test_r304_static_value_requires_eval_readiness(
    eval_ready: bool,
    expected: str,
) -> None:
    module = _load_probe()

    result = module.analyze_topology_vector_gate(
        _matrix(module),
        eval_ready=eval_ready,
    )

    assert result["classification"] == expected
    assert result["distinct_oracle_actions"] == 3
    assert result["training_gate"] == {
        "authorized": False,
        "training_executed": False,
        "next_step": (
            "R305_MATCHED_CLASSICAL_INFORMATION_GATE"
            if eval_ready
            else "REPAIR_VECTOR_INERTIA_EVAL_ONLY"
        ),
    }
    assert result["title_alignment"]["supports_distributed_agent_comparison"] is False


def test_r304_no_material_static_value_stops_before_time_domain() -> None:
    module = _load_probe()

    result = module.analyze_topology_vector_gate(
        _matrix(module, material=False),
        eval_ready=True,
    )

    assert result["classification"] == "NO-STATIC-TOPOLOGY-VALUE"
    assert result["training_gate"]["next_step"] == "STOP"


@pytest.mark.parametrize("failure", ["missing_cell", "guard", "branch"])
def test_r304_classifier_fails_closed_on_integrity_or_mode_branch(
    failure: str,
) -> None:
    module = _load_probe()
    matrix = _matrix(module)
    if failure == "missing_cell":
        matrix["cells"].pop()
    elif failure == "guard":
        matrix["cells"][0]["guards"]["spectrum_pass"] = False
    else:
        matrix["cells"][1]["identified"]["p_vector"] = [0.1, -0.3, 0.2, 0.4]

    result = module.analyze_topology_vector_gate(matrix, eval_ready=True)

    assert result["classification"] == "INVALID-TOPOLOGY-GATE"
    assert result["training_gate"]["authorized"] is False
    assert result["integrity_failures"] or result["branch_failures"]
