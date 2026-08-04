"""Pure contracts for the R288 topology-information value gate.

This module deliberately has no ANDES dependency.  It owns the frozen
allocation library, structural line-outage selection, branch continuity
checks, and the registered robust-fixed versus topology-oracle estimands.
ANDES-facing code is only an adapter that produces the matrix consumed here.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Mapping, Sequence
from math import isfinite, sqrt
import re
from typing import Any

ALLOCATION_LIBRARY: dict[str, tuple[float, float, float, float]] = {
    "q0": (350.0, 350.0, 350.0, 350.0),
    "h1_pos": (500.0, 500.0, 200.0, 200.0),
    "h1_neg": (200.0, 200.0, 500.0, 500.0),
    "h2_pos": (500.0, 200.0, 500.0, 200.0),
    "h2_neg": (200.0, 500.0, 200.0, 500.0),
    "h3_pos": (500.0, 200.0, 200.0, 500.0),
    "h3_neg": (200.0, 500.0, 500.0, 200.0),
}

REQUIRED_CELL_GUARDS = (
    "pflow_converged",
    "g4_zeroed",
    "total_m_pass",
    "opened_line_pass",
    "bus_count_pass",
    "vsg_count_pass",
    "positive_real_stable",
)

DEFAULT_THRESHOLDS: dict[str, float] = {
    "within_cosine_min": 0.90,
    "within_frequency_delta_max_hz": 0.05,
    "cross_topology_cosine_min": 0.80,
    "cross_topology_frequency_delta_max_hz": 0.10,
    "anchor_damping_tolerance": 1e-6,
    "headroom_max_min_percent": 5.0,
    "headroom_mean_min_percent": 2.0,
}


def allocation_library() -> dict[str, tuple[float, float, float, float]]:
    """Return a copy of the frozen q0 + R277 Hadamard action library."""

    return dict(ALLOCATION_LIBRARY)


def allocation_contract() -> dict[str, Any]:
    """Return an order-explicit, canonical-JSON-safe allocation contract."""

    return {
        "order": list(ALLOCATION_LIBRARY),
        "values": {
            name: list(values) for name, values in ALLOCATION_LIBRARY.items()
        },
    }


def ordered_allocation_items(
    contract: Mapping[str, Any],
) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Read allocation values only through the explicit frozen order list."""

    order = tuple(str(name) for name in contract.get("order", ()))
    values = contract.get("values")
    if order != tuple(ALLOCATION_LIBRARY):
        raise ValueError("allocation order does not match the frozen library")
    if not isinstance(values, Mapping) or set(values) != set(order):
        raise ValueError("allocation values do not match the explicit order")
    items: list[tuple[str, tuple[float, float, float, float]]] = []
    for name in order:
        vector = tuple(float(value) for value in values[name])
        if len(vector) != 4:
            raise ValueError(f"{name} must have four inertia values")
        items.append((name, vector))
    return items


def _node(value: Any) -> Hashable:
    if isinstance(value, Hashable):
        return value
    raise TypeError(f"bus identifier is not hashable: {value!r}")


def _edge_key(bus1: Hashable, bus2: Hashable) -> frozenset[Hashable]:
    return frozenset((_node(bus1), _node(bus2)))


def _active(line: Mapping[str, Any]) -> bool:
    return bool(line.get("active", True))


def _adjacency(
    lines: Sequence[Mapping[str, Any]],
    *,
    omit_idx: str | None = None,
) -> tuple[dict[Hashable, set[Hashable]], set[Hashable]]:
    nodes: set[Hashable] = set()
    adjacency: dict[Hashable, set[Hashable]] = {}
    for line in lines:
        if not _active(line):
            continue
        bus1 = _node(line["bus1"])
        bus2 = _node(line["bus2"])
        nodes.update((bus1, bus2))
        adjacency.setdefault(bus1, set())
        adjacency.setdefault(bus2, set())
        if str(line["idx"]) == omit_idx:
            continue
        adjacency[bus1].add(bus2)
        adjacency[bus2].add(bus1)
    return adjacency, nodes


def _distances(
    adjacency: Mapping[Hashable, set[Hashable]],
    source: Hashable,
) -> dict[Hashable, int]:
    distance = {source: 0}
    queue: deque[Hashable] = deque((source,))
    while queue:
        node = queue.popleft()
        for neighbour in adjacency.get(node, set()):
            if neighbour in distance:
                continue
            distance[neighbour] = distance[node] + 1
            queue.append(neighbour)
    return distance


def _all_pair_distances(
    adjacency: Mapping[Hashable, set[Hashable]],
    nodes: set[Hashable],
) -> dict[frozenset[Hashable], int]:
    distances: dict[frozenset[Hashable], int] = {}
    for source in nodes:
        from_source = _distances(adjacency, source)
        for target in nodes:
            if source == target:
                continue
            pair = _edge_key(source, target)
            if pair not in distances and target in from_source:
                distances[pair] = from_source[target]
    return distances


def rank_topology_candidates(
    lines: Sequence[Mapping[str, Any]],
    *,
    forbidden_line_ids: set[str],
    vsg_buses: set[Hashable],
) -> list[dict[str, Any]]:
    """Create the pre-PFlow structural inventory required by the R288 seal."""

    line_rows = [dict(line) for line in lines]
    adjacency, nodes = _adjacency(line_rows)
    if nodes and len(_distances(adjacency, next(iter(nodes)))) != len(nodes):
        raise ValueError("base active-bus graph must be connected")
    baseline_distances = _all_pair_distances(adjacency, nodes)
    parallel_counts: dict[frozenset[Hashable], int] = {}
    for line in line_rows:
        if _active(line):
            key = _edge_key(line["bus1"], line["bus2"])
            parallel_counts[key] = parallel_counts.get(key, 0) + 1

    inventory: list[dict[str, Any]] = []
    for line in line_rows:
        idx = str(line["idx"])
        bus1 = _node(line["bus1"])
        bus2 = _node(line["bus2"])
        reasons: list[str] = []
        if not _active(line):
            reasons.append("inactive_base_line")
        if idx in forbidden_line_ids:
            reasons.append("forbidden_line")
        if bus1 == bus2:
            reasons.append("self_loop")
        if bus1 in vsg_buses or bus2 in vsg_buses:
            reasons.append("vsg_endpoint")
        if parallel_counts.get(_edge_key(bus1, bus2), 0) > 1:
            reasons.append("parallel_endpoint_group")
        try:
            x_value = float(line["x"])
        except (KeyError, TypeError, ValueError):
            x_value = float("nan")
        if not isfinite(x_value) or x_value <= 0.0:
            reasons.append("nonpositive_or_nonfinite_x")

        distance_impact: int | None = None
        if _active(line):
            without, _ = _adjacency(line_rows, omit_idx=idx)
            connected = not nodes or len(_distances(without, next(iter(nodes)))) == len(nodes)
            if not connected:
                reasons.append("disconnects_active_graph")
            elif not reasons:
                changed = _all_pair_distances(without, nodes)
                distance_impact = sum(
                    changed[pair] > base_distance
                    for pair, base_distance in baseline_distances.items()
                )

        inventory.append(
            {
                **line,
                "idx": idx,
                "distance_impact": distance_impact,
                "structural_eligible": not reasons,
                "exclusion_reasons": reasons,
                "structural_rank": None,
                "pflow_pass": None,
                "eligible": False,
                "selected": False,
            }
        )

    ranked = sorted(
        (row for row in inventory if row["structural_eligible"]),
        key=lambda row: (
            -int(row["distance_impact"]),
            -abs(float(row["x"])),
            row["idx"],
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["structural_rank"] = rank
    return inventory


def select_topology_variants(
    lines: Sequence[Mapping[str, Any]],
    *,
    pflow_pass: Mapping[str, bool] | None,
    forbidden_line_ids: set[str],
    vsg_buses: set[Hashable],
    count: int,
    require_count: bool = True,
) -> dict[str, Any]:
    """Select PFlow-valid candidates, preferring endpoint-disjoint outages."""

    if count < 1:
        raise ValueError("count must be positive")
    inventory = rank_topology_candidates(
        lines,
        forbidden_line_ids=forbidden_line_ids,
        vsg_buses=vsg_buses,
    )
    for row in inventory:
        if not row["structural_eligible"]:
            continue
        if pflow_pass is None:
            row["eligible"] = True
            continue
        if row["idx"] not in pflow_pass:
            row["exclusion_reasons"].append("pflow_not_checked")
        elif not bool(pflow_pass[row["idx"]]):
            row["pflow_pass"] = False
            row["exclusion_reasons"].append("q0_pflow_failed")
        else:
            row["pflow_pass"] = True
            row["eligible"] = True

    eligible = sorted(
        (row for row in inventory if row["eligible"]),
        key=lambda row: int(row["structural_rank"]),
    )
    selected: list[dict[str, Any]] = []
    used_buses: set[Hashable] = set()
    for row in eligible:
        endpoints = {_node(row["bus1"]), _node(row["bus2"])}
        if used_buses.isdisjoint(endpoints):
            selected.append(row)
            used_buses.update(endpoints)
        if len(selected) == count:
            break
    if len(selected) < count:
        selected_ids = {row["idx"] for row in selected}
        for row in eligible:
            if row["idx"] in selected_ids:
                continue
            selected.append(row)
            if len(selected) == count:
                break
    if len(selected) != count and require_count:
        raise ValueError(f"only {len(selected)} eligible topology variants; need {count}")
    for row in selected:
        row["selected"] = True
    return {
        "selected": [row["idx"] for row in selected],
        "requested_count": count,
        "selection_complete": len(selected) == count,
        "inventory": inventory,
    }


def _line_number(idx: str) -> int:
    match = re.fullmatch(r"Line_(\d+)", idx)
    if match is None:
        raise ValueError(f"parallel-circuit candidate lacks numeric Line_ suffix: {idx}")
    return int(match.group(1))


def _parameter_signature(line: Mapping[str, Any]) -> tuple[float | None, ...]:
    signature: list[float | None] = []
    for field in ("r", "x", "b", "b1", "b2"):
        value = line.get(field)
        signature.append(None if value is None else float(value))
    return tuple(signature)


def select_parallel_circuit_variants(
    lines: Sequence[Mapping[str, Any]],
    *,
    target_groups: Mapping[str, tuple[Hashable, Hashable]],
) -> dict[str, Any]:
    """Freeze one canonical outage from each declared parallel corridor."""

    line_rows = [{**line, "idx": str(line["idx"])} for line in lines]
    adjacency, nodes = _adjacency(line_rows)
    if nodes and len(_distances(adjacency, next(iter(nodes)))) != len(nodes):
        raise ValueError("base active-bus graph must be connected")

    topologies: list[dict[str, Any]] = []
    selected: list[str] = []
    for topology_name, endpoints in target_groups.items():
        endpoint_key = _edge_key(*endpoints)
        group = [
            row
            for row in line_rows
            if _edge_key(row["bus1"], row["bus2"]) == endpoint_key
        ]
        if len(group) < 2:
            raise ValueError(
                f"{topology_name} endpoint group {tuple(endpoints)} is not parallel"
            )
        if not all(_active(row) for row in group):
            raise ValueError(f"{topology_name} parallel group is not fully active")
        signatures = {
            row["idx"]: _parameter_signature(row)
            for row in group
        }
        parameter_matched = len(set(signatures.values())) == 1
        x_values = [float(row["x"]) for row in group]
        if not all(isfinite(value) and value > 0.0 for value in x_values):
            raise ValueError(f"{topology_name} has nonpositive or nonfinite x")
        canonical = min(group, key=lambda row: _line_number(row["idx"]))
        without, _ = _adjacency(line_rows, omit_idx=canonical["idx"])
        connected = not nodes or len(_distances(without, next(iter(nodes)))) == len(nodes)
        if not connected:
            raise ValueError(f"{topology_name} canonical outage disconnects the graph")
        selected.append(canonical["idx"])
        topologies.append(
            {
                "name": topology_name,
                "endpoints": list(endpoints),
                "group_lines": sorted(
                    (row["idx"] for row in group),
                    key=_line_number,
                ),
                "selected_line": canonical["idx"],
                "parameter_matched": parameter_matched,
                "parameter_signatures": signatures,
                "connected_after_outage": True,
                "line": canonical,
            }
        )
    if len(set(selected)) != len(selected):
        raise ValueError("the same line was selected for multiple topology variants")
    return {"selected": selected, "topologies": topologies}


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(float(value) ** 2 for value in left))
    right_norm = sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return float("nan")
    return numerator / (left_norm * right_norm)


def _invalid_result(
    *,
    failures: list[str],
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    return {
        "classification": "INVALID",
        "integrity_failures": failures,
        "branch_failures": [],
        "thresholds": dict(thresholds),
    }


def analyze_eig_matrix(
    matrix: Mapping[str, Any],
    *,
    nominal_anchors: Mapping[str, float],
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Apply the sealed four-class R288 topology-information decision."""

    limits = {**DEFAULT_THRESHOLDS, **dict(thresholds or {})}
    expected_allocations = tuple(ALLOCATION_LIBRARY)
    topologies = tuple(str(value) for value in matrix.get("topologies", ()))
    allocations = tuple(str(value) for value in matrix.get("allocations", ()))
    cells = matrix.get("cells", ())
    failures: list[str] = []
    if len(topologies) != 4 or len(set(topologies)) != 4 or not topologies:
        failures.append("matrix must declare exactly four unique topologies")
    elif topologies[0] != "nominal":
        failures.append("the first topology must be nominal")
    if allocations != expected_allocations:
        failures.append("allocation order does not match the frozen library")
    if not isinstance(cells, Sequence) or isinstance(cells, (str, bytes)):
        failures.append("cells must be a sequence")
        return _invalid_result(failures=failures, thresholds=limits)

    by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in cells:
        if not isinstance(cell, Mapping):
            failures.append("every cell must be an object")
            continue
        key = (str(cell.get("topology")), str(cell.get("allocation")))
        if key in by_key:
            failures.append(f"duplicate cell {key[0]}/{key[1]}")
        by_key[key] = cell
    expected_keys = {
        (topology, allocation)
        for topology in topologies
        for allocation in expected_allocations
    }
    missing = sorted(expected_keys - set(by_key))
    extra = sorted(set(by_key) - expected_keys)
    if missing:
        failures.append(f"missing cells: {missing}")
    if extra:
        failures.append(f"unexpected cells: {extra}")

    for key in sorted(expected_keys & set(by_key)):
        cell = by_key[key]
        guards = cell.get("guards")
        if not isinstance(guards, Mapping):
            failures.append(f"{key[0]}/{key[1]} missing guards")
            continue
        for guard in REQUIRED_CELL_GUARDS:
            if guards.get(guard) is not True:
                failures.append(f"{key[0]}/{key[1]} guard failed: {guard}")
        actual_m = cell.get("m_vector")
        expected_m = ALLOCATION_LIBRARY[key[1]]
        try:
            m_matches = len(actual_m) == 4 and all(
                abs(float(actual) - expected) <= 1e-9
                for actual, expected in zip(actual_m, expected_m, strict=True)
            )
        except (TypeError, ValueError):
            m_matches = False
        if not m_matches:
            failures.append(f"{key[0]}/{key[1]} M vector drift")
        identified = cell.get("identified")
        if not isinstance(identified, Mapping):
            failures.append(f"{key[0]}/{key[1]} missing identified mode")
            continue
        try:
            damping = float(identified["damping_ratio"])
            frequency = float(identified["freq_hz"])
            vector = tuple(float(value) for value in identified["p_vector"])
        except (KeyError, TypeError, ValueError):
            failures.append(f"{key[0]}/{key[1]} malformed identified mode")
            continue
        if (
            not isfinite(damping)
            or damping <= 0.0
            or not isfinite(frequency)
            or not vector
            or not all(isfinite(value) for value in vector)
        ):
            failures.append(f"{key[0]}/{key[1]} nonfinite or nonpositive mode result")

    for allocation, expected in nominal_anchors.items():
        key = ("nominal", allocation)
        cell = by_key.get(key)
        if cell is None or not isinstance(cell.get("identified"), Mapping):
            failures.append(f"nominal anchor missing: {allocation}")
            continue
        actual = float(cell["identified"]["damping_ratio"])
        if abs(actual - float(expected)) >= limits["anchor_damping_tolerance"]:
            failures.append(
                f"nominal anchor drift: {allocation} actual={actual} expected={expected}"
            )
    if failures:
        return _invalid_result(failures=failures, thresholds=limits)

    branch_failures: list[str] = []
    nominal_q0 = by_key[("nominal", "q0")]["identified"]
    for topology in topologies:
        q0 = by_key[(topology, "q0")]["identified"]
        if topology != "nominal":
            cosine = cosine_similarity(nominal_q0["p_vector"], q0["p_vector"])
            frequency_delta = abs(
                float(nominal_q0["freq_hz"]) - float(q0["freq_hz"])
            )
            if (
                not isfinite(cosine)
                or cosine < limits["cross_topology_cosine_min"]
                or frequency_delta
                >= limits["cross_topology_frequency_delta_max_hz"]
            ):
                branch_failures.append(
                    f"{topology}/q0 cross-topology branch failed: "
                    f"cos={cosine}, df={frequency_delta}"
                )
        for allocation in expected_allocations:
            identified = by_key[(topology, allocation)]["identified"]
            cosine = cosine_similarity(q0["p_vector"], identified["p_vector"])
            frequency_delta = abs(float(q0["freq_hz"]) - float(identified["freq_hz"]))
            if (
                not isfinite(cosine)
                or cosine < limits["within_cosine_min"]
                or frequency_delta >= limits["within_frequency_delta_max_hz"]
            ):
                branch_failures.append(
                    f"{topology}/{allocation} within-topology branch failed: "
                    f"cos={cosine}, df={frequency_delta}"
                )

    damping = {
        topology: {
            allocation: float(
                by_key[(topology, allocation)]["identified"]["damping_ratio"]
            )
            for allocation in expected_allocations
        }
        for topology in topologies
    }
    ratios = {
        topology: {
            allocation: value / damping[topology]["q0"]
            for allocation, value in values.items()
        }
        for topology, values in damping.items()
    }
    oracle: dict[str, dict[str, float | str]] = {}
    for topology in topologies:
        allocation = max(
            expected_allocations,
            key=lambda name: (
                damping[topology][name],
                -expected_allocations.index(name),
            ),
        )
        oracle[topology] = {
            "allocation": allocation,
            "damping_ratio": damping[topology][allocation],
        }
    robust_allocation = max(
        expected_allocations,
        key=lambda name: (
            min(ratios[topology][name] for topology in topologies),
            -expected_allocations.index(name),
        ),
    )
    robust_fixed = {
        "allocation": robust_allocation,
        "worst_case_ratio": min(
            ratios[topology][robust_allocation] for topology in topologies
        ),
    }
    headroom = {
        topology: 100.0
        * (
            float(oracle[topology]["damping_ratio"])
            - damping[topology][robust_allocation]
        )
        / abs(damping[topology][robust_allocation])
        for topology in topologies
    }
    mean_headroom = sum(headroom.values()) / len(headroom)
    max_headroom = max(headroom.values())
    distinct_oracles = len({str(value["allocation"]) for value in oracle.values()})

    if branch_failures:
        classification = "PARTIAL-IDENTIFICATION"
    elif (
        distinct_oracles >= 2
        and max_headroom >= limits["headroom_max_min_percent"]
        and mean_headroom >= limits["headroom_mean_min_percent"]
    ):
        classification = "STATIC-TOPOLOGY-VALUE"
    else:
        classification = "NO-MATERIAL-TOPOLOGY-VALUE"

    return {
        "classification": classification,
        "integrity_failures": [],
        "branch_failures": branch_failures,
        "thresholds": limits,
        "damping_ratios": damping,
        "zeta_ratios": ratios,
        "oracle": oracle,
        "robust_fixed": robust_fixed,
        "headroom_percent": headroom,
        "mean_headroom_percent": mean_headroom,
        "max_headroom_percent": max_headroom,
        "distinct_oracle_actions": distinct_oracles,
    }
