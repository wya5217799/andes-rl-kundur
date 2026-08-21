"""Build the prospective four-REGCV1 object on the packaged Kundur case.

The builder changes dynamic-device ownership only.  It verifies the frozen
network inventory before disabling the four synchronous-machine chains and
attaching one REGCV1 to each existing static generator.  It deliberately does
not call setup, power flow, or time-domain simulation; the sealed runner owns
those evidence-bearing stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from andes_rl_kundur.evaluation.regcv1_object_gate import build_contract


@dataclass(frozen=True)
class Regcv1KundurObject:
    """Inspectable pre-setup result of the dynamic-object replacement."""

    system: Any
    bindings: tuple[dict[str, Any], ...]
    disabled_dynamic_chain: tuple[dict[str, Any], ...]
    network_inventory: dict[str, Any]
    case_path: str | None


def _network_inventory(system: Any) -> dict[str, Any]:
    static_indices = [1, 2, 3, 4]
    buses = system.StaticGen.get(src="bus", idx=static_indices, attr="v")
    return {
        "bus_count": int(system.Bus.n),
        "line_count": int(system.Line.n),
        "pq_count": int(system.PQ.n),
        "static_gen_count": int(system.StaticGen.n),
        "static_generator_buses": [int(value) for value in buses],
    }


def _load_packaged_system(case_path: str | Path | None) -> tuple[Any, str]:
    import andes

    resolved = Path(
        andes.get_case("kundur/kundur_full.xlsx")
        if case_path is None
        else case_path
    ).resolve()
    system = andes.load(str(resolved), setup=False, no_output=True)
    return system, str(resolved)


def build_regcv1_kundur_object(
    *,
    system: Any | None = None,
    case_path: str | Path | None = None,
) -> Regcv1KundurObject:
    """Return the frozen four-device Kundur object before ANDES setup.

    ``system`` is an external-boundary injection seam for contract tests.  The
    formal runner leaves it unset and therefore loads the packaged ANDES case.
    """

    if system is not None and case_path is not None:
        raise ValueError("provide either system or case_path, not both")
    loaded_path: str | None = None
    if system is None:
        system, loaded_path = _load_packaged_system(case_path)

    contract = build_contract()
    inventory = _network_inventory(system)
    if inventory != contract["network_inventory"]:
        raise ValueError(
            "Kundur network inventory drift: "
            f"{inventory!r} != {contract['network_inventory']!r}"
        )
    if hasattr(system, "REGCV1") and int(system.REGCV1.n) != 0:
        raise ValueError("REGCV1 devices already exist before R384 construction")

    disabled: list[dict[str, Any]] = []
    for model_name in contract["disabled_chain_models"]:
        if not hasattr(system, model_name):
            raise ValueError(f"required Kundur dynamic model is missing: {model_name}")
        model = getattr(system, model_name)
        if int(model.n) != 4:
            raise ValueError(f"expected four {model_name} devices, got {model.n}")
        for position, idx in enumerate(model.idx.v):
            numeric_idx = int(idx)
            syn = numeric_idx if model_name == "GENROU" else int(model.syn.v[position])
            if numeric_idx not in range(1, 5) or syn not in range(1, 5):
                raise ValueError(f"unexpected {model_name} ownership at idx={idx!r}")
            model.set("u", idx, 0, attr="v")
            disabled.append(
                {
                    "model": model_name,
                    "idx": numeric_idx,
                    "syn": syn,
                    "u": int(model.u.v[position]),
                }
            )

    static_indices = [row["gen"] for row in contract["expected_mapping"]]
    buses = system.StaticGen.get(src="bus", idx=static_indices, attr="v")
    ratings = system.StaticGen.get(src="Sn", idx=static_indices, attr="v")
    bindings: list[dict[str, Any]] = []
    card = dict(contract["parameter_card"])
    for expected, bus, rating in zip(
        contract["expected_mapping"], buses, ratings, strict=True
    ):
        actual_bus = int(bus)
        if actual_bus != int(expected["bus"]):
            raise ValueError(
                f"static-generator bus drift for gen={expected['gen']}: {actual_bus}"
            )
        payload = {
            **expected,
            "Sn": float(rating),
            **card,
        }
        system.add("REGCV1", payload)
        bindings.append(dict(payload))

    return Regcv1KundurObject(
        system=system,
        bindings=tuple(bindings),
        disabled_dynamic_chain=tuple(disabled),
        network_inventory=inventory,
        case_path=loaded_path,
    )


__all__ = ["Regcv1KundurObject", "build_regcv1_kundur_object"]
