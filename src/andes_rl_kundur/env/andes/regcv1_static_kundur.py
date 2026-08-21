"""Build four REGCV1 devices from a structurally static Kundur case.

The public builder accepts the complete packaged JSON payload, projects the
six static model tables into deterministic bytes, loads that derived case
without setup, verifies that no legacy dynamic/event records exist, and adds
the frozen four-device REGCV1 card. It performs no power flow or TDS work.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from andes_rl_kundur.evaluation.regcv1_clean_init_gate import (
    FORBIDDEN_MODELS,
    STATIC_MODELS,
    build_clean_contract,
)


@dataclass(frozen=True)
class Regcv1StaticKundurObject:
    system: Any
    bindings: tuple[dict[str, Any], ...]
    static_payload: dict[str, Any]
    derived_case_path: str
    derived_case_sha256: str
    forbidden_model_counts: dict[str, int]
    network_inventory: dict[str, Any]


@dataclass(frozen=True)
class StaticSourceAudit:
    full_case: dict[str, Any]
    xlsx_sha256: str
    json_sha256: str
    xlsx_json_static_equal: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_static_case(
    *,
    xlsx_path: str | Path,
    json_path: str | Path,
) -> StaticSourceAudit:
    """Load packaged sources and require complete static-table equality."""

    from openpyxl import load_workbook

    resolved_xlsx = Path(xlsx_path).resolve()
    resolved_json = Path(json_path).resolve()
    full_case = json.loads(resolved_json.read_text(encoding="utf-8"))
    workbook = load_workbook(resolved_xlsx, read_only=True, data_only=True)
    xlsx_static: dict[str, list[dict[str, Any]]] = {}
    try:
        for model in STATIC_MODELS:
            if model not in workbook.sheetnames:
                raise ValueError(f"packaged XLSX is missing static model {model}")
            rows = list(workbook[model].iter_rows(values_only=True))
            headers = rows[0]
            xlsx_static[model] = [
                {
                    key: value
                    for key, value in zip(headers, row, strict=True)
                    if key != "uid"
                }
                for row in rows[1:]
            ]
    finally:
        workbook.close()

    json_static = {model: full_case.get(model) for model in STATIC_MODELS}
    if xlsx_static != json_static:
        mismatches = [
            model for model in STATIC_MODELS if xlsx_static[model] != json_static[model]
        ]
        raise ValueError(f"packaged static table mismatch: {mismatches}")
    return StaticSourceAudit(
        full_case=full_case,
        xlsx_sha256=_sha256_file(resolved_xlsx),
        json_sha256=_sha256_file(resolved_json),
        xlsx_json_static_equal=True,
    )


def render_static_case_bytes(full_case: Mapping[str, Any]) -> bytes:
    """Return canonical bytes containing exactly the registered static tables."""

    missing = [name for name in STATIC_MODELS if name not in full_case]
    if missing:
        raise ValueError(f"missing static Kundur models: {missing}")
    payload = {name: full_case[name] for name in STATIC_MODELS}
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_system(path: Path) -> Any:
    import andes

    return andes.load(str(path), setup=False, no_output=True)


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


def build_regcv1_static_kundur_object(
    *,
    full_case: Mapping[str, Any],
    work_dir: str | Path,
    system_loader: Callable[[Path], Any] | None = None,
) -> Regcv1StaticKundurObject:
    """Return the clean four-REGCV1 object before ANDES setup."""

    rendered = render_static_case_bytes(full_case)
    digest = hashlib.sha256(rendered).hexdigest()
    target_dir = Path(work_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    derived_path = target_dir / "kundur_static_r385.json"
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
        raise ValueError(f"legacy models are structurally present: {retained}")
    if hasattr(system, "REGCV1") and int(system.REGCV1.n) != 0:
        raise ValueError("REGCV1 devices already exist before R385 construction")

    contract = build_clean_contract()
    inventory = _network_inventory(system)
    if inventory != contract["network_inventory"]:
        raise ValueError(
            f"Kundur network inventory drift: {inventory!r} != "
            f"{contract['network_inventory']!r}"
        )

    static_indices = [row["gen"] for row in contract["expected_mapping"]]
    buses = system.StaticGen.get(src="bus", idx=static_indices, attr="v")
    ratings = system.StaticGen.get(src="Sn", idx=static_indices, attr="v")
    bindings: list[dict[str, Any]] = []
    for expected, bus, rating in zip(
        contract["expected_mapping"], buses, ratings, strict=True
    ):
        if int(bus) != int(expected["bus"]):
            raise ValueError(
                f"static-generator bus drift for gen={expected['gen']}: {bus}"
            )
        payload = {
            **expected,
            "Sn": float(rating),
            **contract["parameter_card"],
        }
        system.add("REGCV1", payload)
        bindings.append(dict(payload))

    return Regcv1StaticKundurObject(
        system=system,
        bindings=tuple(bindings),
        static_payload=json.loads(rendered),
        derived_case_path=str(derived_path),
        derived_case_sha256=digest,
        forbidden_model_counts=forbidden_counts,
        network_inventory=inventory,
    )


__all__ = [
    "STATIC_MODELS",
    "Regcv1StaticKundurObject",
    "StaticSourceAudit",
    "build_regcv1_static_kundur_object",
    "load_verified_static_case",
    "render_static_case_bytes",
]
