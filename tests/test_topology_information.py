from __future__ import annotations

from copy import deepcopy
import json

import pytest

from andes_rl_kundur.evaluation.topology_information import (
    allocation_contract,
    allocation_library,
    analyze_eig_matrix,
    ordered_allocation_items,
    select_parallel_circuit_variants,
    select_topology_variants,
)


ALLOCATION_NAMES = (
    "q0",
    "h1_pos",
    "h1_neg",
    "h2_pos",
    "h2_neg",
    "h3_pos",
    "h3_neg",
)


def test_allocation_library_is_the_frozen_r277_hadamard_basis() -> None:
    allocations = allocation_library()

    assert tuple(allocations) == ALLOCATION_NAMES
    assert allocations == {
        "q0": (350.0, 350.0, 350.0, 350.0),
        "h1_pos": (500.0, 500.0, 200.0, 200.0),
        "h1_neg": (200.0, 200.0, 500.0, 500.0),
        "h2_pos": (500.0, 200.0, 500.0, 200.0),
        "h2_neg": (200.0, 500.0, 200.0, 500.0),
        "h3_pos": (500.0, 200.0, 200.0, 500.0),
        "h3_neg": (200.0, 500.0, 500.0, 200.0),
    }
    assert all(sum(values) == pytest.approx(1400.0) for values in allocations.values())


def test_allocation_order_survives_canonical_json_key_sorting() -> None:
    serialized = json.dumps(allocation_contract(), sort_keys=True)
    restored = json.loads(serialized)

    assert [name for name, _ in ordered_allocation_items(restored)] == list(
        ALLOCATION_NAMES
    )
    assert restored["order"][0] == "q0"


def test_topology_selection_filters_illegal_edges_and_prefers_disjoint_edges() -> None:
    lines = [
        {"idx": "L1", "bus1": 1, "bus2": 2, "x": 0.60, "active": True},
        {"idx": "L2", "bus1": 2, "bus2": 3, "x": 0.10, "active": True},
        {"idx": "L3", "bus1": 3, "bus2": 4, "x": 0.50, "active": True},
        {"idx": "L4", "bus1": 4, "bus2": 5, "x": 0.10, "active": True},
        {"idx": "L5", "bus1": 5, "bus2": 6, "x": 0.40, "active": True},
        {"idx": "L6", "bus1": 6, "bus2": 1, "x": 0.10, "active": True},
        {"idx": "Line_4", "bus1": 1, "bus2": 4, "x": 0.90, "active": True},
        {"idx": "P1", "bus1": 1, "bus2": 3, "x": 0.80, "active": True},
        {"idx": "P2", "bus1": 3, "bus2": 1, "x": 0.70, "active": True},
        {"idx": "BRIDGE", "bus1": 6, "bus2": 7, "x": 1.00, "active": True},
        {"idx": "VSG_STUB", "bus1": 7, "bus2": 12, "x": 1.10, "active": True},
    ]
    pflow_pass = {line["idx"]: True for line in lines}

    result = select_topology_variants(
        lines,
        pflow_pass=pflow_pass,
        forbidden_line_ids={"Line_4", "Line_5", "Line_6", "Line_8"},
        vsg_buses={12, 14, 15, 16},
        count=3,
    )

    assert result["selected"] == ["L6", "L3", "L1"]
    by_id = {row["idx"]: row for row in result["inventory"]}
    assert "forbidden_line" in by_id["Line_4"]["exclusion_reasons"]
    assert "parallel_endpoint_group" in by_id["P1"]["exclusion_reasons"]
    assert "parallel_endpoint_group" in by_id["P2"]["exclusion_reasons"]
    assert "disconnects_active_graph" in by_id["BRIDGE"]["exclusion_reasons"]
    assert "vsg_endpoint" in by_id["VSG_STUB"]["exclusion_reasons"]
    assert all(by_id[idx]["selected"] for idx in ("L6", "L3", "L1"))
    assert {by_id["L6"]["bus1"], by_id["L6"]["bus2"]}.isdisjoint(
        {by_id["L3"]["bus1"], by_id["L3"]["bus2"]}
    )


def test_topology_selection_can_report_pre_seal_structural_infeasibility() -> None:
    lines = [
        {"idx": "B1", "bus1": 1, "bus2": 2, "x": 0.1, "active": True},
        {"idx": "B2", "bus1": 2, "bus2": 3, "x": 0.1, "active": True},
    ]

    result = select_topology_variants(
        lines,
        pflow_pass={},
        forbidden_line_ids=set(),
        vsg_buses=set(),
        count=3,
        require_count=False,
    )

    assert result["selected"] == []
    assert result["requested_count"] == 3
    assert result["selection_complete"] is False
    assert all(
        "disconnects_active_graph" in row["exclusion_reasons"]
        for row in result["inventory"]
    )


def test_parallel_circuit_selection_is_canonical_and_parameter_matched() -> None:
    lines = [
        {"idx": "Line_0", "bus1": 5, "bus2": 6, "r": 0.01, "x": 0.10, "b": 0.0},
        {"idx": "Line_1", "bus1": 6, "bus2": 5, "r": 0.01, "x": 0.10, "b": 0.0},
        {"idx": "Line_2", "bus1": 6, "bus2": 7, "r": 0.02, "x": 0.20, "b": 0.0},
        {"idx": "Line_3", "bus1": 6, "bus2": 7, "r": 0.02, "x": 0.20, "b": 0.0},
        {"idx": "Line_9", "bus1": 9, "bus2": 10, "r": 0.03, "x": 0.30, "b": 0.0},
        {"idx": "Line_10", "bus1": 9, "bus2": 10, "r": 0.03, "x": 0.30, "b": 0.0},
        {"idx": "Link", "bus1": 7, "bus2": 9, "r": 0.01, "x": 0.10, "b": 0.0},
        {"idx": "Loop", "bus1": 10, "bus2": 5, "r": 0.01, "x": 0.10, "b": 0.0},
    ]

    result = select_parallel_circuit_variants(
        lines,
        target_groups={
            "topology_1": (5, 6),
            "topology_2": (6, 7),
            "topology_3": (9, 10),
        },
    )

    assert result["selected"] == ["Line_0", "Line_2", "Line_9"]
    assert [row["name"] for row in result["topologies"]] == [
        "topology_1",
        "topology_2",
        "topology_3",
    ]
    assert all(row["connected_after_outage"] for row in result["topologies"])
    assert all(row["parameter_matched"] for row in result["topologies"])


def test_parallel_circuit_selection_records_but_does_not_select_on_mismatch() -> None:
    lines = [
        {"idx": "Line_0", "bus1": 5, "bus2": 6, "r": 0.01, "x": 0.10},
        {"idx": "Line_1", "bus1": 5, "bus2": 6, "r": 0.01, "x": 0.11},
    ]

    result = select_parallel_circuit_variants(
        lines,
        target_groups={"topology_1": (5, 6)},
    )

    assert result["selected"] == ["Line_0"]
    assert result["topologies"][0]["parameter_matched"] is False
    assert result["topologies"][0]["parameter_signatures"]["Line_0"][1] == 0.10
    assert result["topologies"][0]["parameter_signatures"]["Line_1"][1] == 0.11


def _matrix(damping: dict[str, dict[str, float]]) -> dict:
    cells = []
    for topology, values in damping.items():
        for allocation in ALLOCATION_NAMES:
            cells.append(
                {
                    "topology": topology,
                    "allocation": allocation,
                    "m_vector": list(allocation_library()[allocation]),
                    "guards": {
                        "pflow_converged": True,
                        "g4_zeroed": True,
                        "total_m_pass": True,
                        "opened_line_pass": True,
                        "bus_count_pass": True,
                        "vsg_count_pass": True,
                        "positive_real_stable": True,
                    },
                    "identified": {
                        "damping_ratio": values[allocation],
                        "freq_hz": 0.70,
                        "p_vector": [1.0, -1.0],
                    },
                }
            )
    return {
        "topologies": list(damping),
        "allocations": list(ALLOCATION_NAMES),
        "cells": cells,
    }


def test_analysis_detects_material_static_topology_value() -> None:
    damping = {
        "nominal": {
            "q0": 0.10,
            "h1_pos": 0.13,
            "h1_neg": 0.08,
            "h2_pos": 0.10,
            "h2_neg": 0.10,
            "h3_pos": 0.10,
            "h3_neg": 0.10,
        },
        "topology_1": {
            "q0": 0.10,
            "h1_pos": 0.09,
            "h1_neg": 0.10,
            "h2_pos": 0.13,
            "h2_neg": 0.08,
            "h3_pos": 0.10,
            "h3_neg": 0.10,
        },
        "topology_2": {
            "q0": 0.10,
            "h1_pos": 0.09,
            "h1_neg": 0.10,
            "h2_pos": 0.09,
            "h2_neg": 0.10,
            "h3_pos": 0.13,
            "h3_neg": 0.08,
        },
        "topology_3": {
            "q0": 0.10,
            "h1_pos": 0.09,
            "h1_neg": 0.10,
            "h2_pos": 0.09,
            "h2_neg": 0.10,
            "h3_pos": 0.09,
            "h3_neg": 0.13,
        },
    }

    analysis = analyze_eig_matrix(
        _matrix(damping),
        nominal_anchors={"q0": 0.10, "h1_pos": 0.13, "h1_neg": 0.08},
    )

    assert analysis["classification"] == "STATIC-TOPOLOGY-VALUE"
    assert analysis["robust_fixed"]["allocation"] == "q0"
    assert analysis["distinct_oracle_actions"] == 4
    assert analysis["mean_headroom_percent"] == pytest.approx(30.0)
    assert analysis["max_headroom_percent"] == pytest.approx(30.0)


def test_analysis_detects_a_valid_matrix_without_material_topology_value() -> None:
    damping = {
        topology: {
            "q0": 0.10,
            "h1_pos": 0.099,
            "h1_neg": 0.099,
            "h2_pos": 0.099,
            "h2_neg": 0.099,
            "h3_pos": 0.099,
            "h3_neg": 0.099,
        }
        for topology in ("nominal", "topology_1", "topology_2", "topology_3")
    }

    analysis = analyze_eig_matrix(
        _matrix(damping),
        nominal_anchors={"q0": 0.10, "h1_pos": 0.099, "h1_neg": 0.099},
    )

    assert analysis["classification"] == "NO-MATERIAL-TOPOLOGY-VALUE"
    assert analysis["robust_fixed"]["allocation"] == "q0"
    assert analysis["distinct_oracle_actions"] == 1
    assert analysis["max_headroom_percent"] == pytest.approx(0.0)


def test_analysis_separates_branch_failure_from_integrity_failure() -> None:
    damping = {
        topology: {allocation: 0.10 for allocation in ALLOCATION_NAMES}
        for topology in ("nominal", "topology_1", "topology_2", "topology_3")
    }
    branch_failure = _matrix(damping)
    branch_failure["cells"][8]["identified"]["p_vector"] = [1.0, 1.0]

    partial = analyze_eig_matrix(
        branch_failure,
        nominal_anchors={"q0": 0.10, "h1_pos": 0.10, "h1_neg": 0.10},
    )
    assert partial["classification"] == "PARTIAL-IDENTIFICATION"
    assert partial["branch_failures"]

    anchor_failure = deepcopy(branch_failure)
    anchor_failure["cells"][8]["identified"]["p_vector"] = [1.0, -1.0]
    invalid = analyze_eig_matrix(
        anchor_failure,
        nominal_anchors={"q0": 0.20, "h1_pos": 0.10, "h1_neg": 0.10},
    )
    assert invalid["classification"] == "INVALID"
    assert invalid["integrity_failures"]
