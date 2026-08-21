"""Build two PPVSM1 devices from a structurally static Kundur case.

The public builder projects the six static tables into deterministic bytes,
loads the derived case without setup, rejects any retained dynamic/event
object, registers the repo-local PPVSM1 model, and adds the frozen R393
cards at buses 1-2. StaticGen 3-4 remain static anchors. It performs no
PFlow or TDS work.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from andes_rl_kundur.env.andes.regcv1_static_kundur import render_static_case_bytes
from andes_rl_kundur.evaluation.ppvsm1_object_gate import (
    FORBIDDEN_MODELS,
    PPVSM1_PARAMETER_CARD,
    build_ppvsm1_object_contract,
)


@dataclass(frozen=True)
class Ppvsm1StaticKundurObject:
    system: Any
    bindings: tuple[dict[str, Any], ...]
    static_payload: dict[str, Any]
    derived_case_path: str
    derived_case_sha256: str
    forbidden_model_counts: dict[str, int]
    network_inventory: dict[str, Any]


def register_ppvsm1_model(system: Any) -> None:
    """Register the repo-local PPVSM1 model on a loaded ANDES system."""

    from andes_rl_kundur.env.andes.ppvsm1 import PPVSM1

    if "PPVSM1" in getattr(system, "models", {}):
        return
    instance = PPVSM1(system=system, config=system._config_object)
    system.__dict__["PPVSM1"] = instance
    system.models["PPVSM1"] = instance
    system.groups["RenGen"].add_model("PPVSM1", instance)


def _load_system(path: Path) -> Any:
    import andes

    system = andes.load(str(path), setup=False, no_output=True)
    register_ppvsm1_model(system)
    # Codegen for the repo-local model only; stock models keep their
    # pre-generated calls. Serial and single-threaded by contract.
    system.prepare(
        quick=True,
        incremental=False,
        models=["PPVSM1"],
        nomp=True,
        ncpu=1,
    )
    return system


def _network_inventory(system: Any) -> dict[str, Any]:
    static_indices = [1, 2, 3, 4]
    buses = system.StaticGen.get(src="bus", idx=static_indices, attr="v")
    return {
        "bus_count": int(system.Bus.n),
        "line_count": int(system.Line.n),
        "pq_count": int(system.PQ.n),
        "static_gen_count": int(system.StaticGen.n),
        "static_generator_buses": [int(value) for value in buses],
        "ppvsm1_buses": [1, 2],
        "static_anchor_buses": [3, 4],
    }


def build_ppvsm1_static_kundur_object(
    *,
    full_case: Mapping[str, Any],
    work_dir: str | Path,
    system_loader: Callable[[Path], Any] | None = None,
) -> Ppvsm1StaticKundurObject:
    """Return the exact two-PPVSM1 object before ANDES setup."""

    rendered = render_static_case_bytes(full_case)
    digest = hashlib.sha256(rendered).hexdigest()
    target_dir = Path(work_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    derived_path = target_dir / "kundur_static_r393.json"
    if derived_path.exists():
        if derived_path.read_bytes() != rendered:
            raise FileExistsError(f"derived case collision: {derived_path}")
    else:
        derived_path.write_bytes(rendered)

    loader = _load_system if system_loader is None else system_loader
    system = loader(derived_path)
    forbidden_counts = {
        name: int(getattr(system, name).n) if hasattr(system, name) else 0
        for name in FORBIDDEN_MODELS
    }
    retained = {name: count for name, count in forbidden_counts.items() if count}
    if retained:
        raise ValueError(f"dynamic models are structurally present: {retained}")
    if hasattr(system, "PPVSM1") and int(system.PPVSM1.n) != 0:
        raise ValueError("PPVSM1 devices already exist before R393 construction")

    contract = build_ppvsm1_object_contract()
    inventory = _network_inventory(system)
    if inventory != contract["network_inventory"]:
        raise ValueError(
            f"Kundur network inventory drift: {inventory!r} != "
            f"{contract['network_inventory']!r}"
        )

    bindings: list[dict[str, Any]] = []
    static_indices = [row["gen"] for row in contract["expected_mapping"]]
    buses = system.StaticGen.get(src="bus", idx=static_indices, attr="v")
    ratings = system.StaticGen.get(src="Sn", idx=static_indices, attr="v")
    for expected, bus, rating in zip(
        contract["expected_mapping"], buses, ratings, strict=True
    ):
        if int(bus) != int(expected["bus"]):
            raise ValueError(
                f"static-generator bus drift for gen={expected['gen']}: {bus}"
            )
        if float(rating) != float(contract["device_rating_mva"]):
            raise ValueError(
                f"static-generator rating drift for gen={expected['gen']}: {rating}"
            )
        payload = {
            **expected,
            "Sn": float(contract["device_rating_mva"]),
            **contract["parameter_card"],
        }
        bindings.append(dict(payload))
        system.add("PPVSM1", payload)

    return Ppvsm1StaticKundurObject(
        system=system,
        bindings=tuple(bindings),
        static_payload=json.loads(rendered),
        derived_case_path=str(derived_path),
        derived_case_sha256=digest,
        forbidden_model_counts=forbidden_counts,
        network_inventory=inventory,
    )
