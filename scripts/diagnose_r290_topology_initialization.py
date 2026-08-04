#!/usr/bin/env python3
"""Minimal R290 q0 topology/EIG feedback loop.

``reproduce`` is intentionally read-only: it writes no repository artifact
and exits nonzero when the exact R289 symptom is present.  Formal diagnostic
subcommands are added only after the red loop is established.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT / "src", ROOT / "probes"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from andes_rl_kundur.evaluation.topology_information import (  # noqa: E402
    allocation_contract,
    allocation_library,
    ordered_allocation_items,
)

ROUND_ID = "R290"
QUESTION_ID = "Q-0047"
TARGET_LINE = "Line_2"
POSITIVE_REAL_TOLERANCE = 1e-7
METHODS = (
    "post_setup_direct",
    "post_setup_set",
    "post_setup_set_connectivity",
    "pre_setup_set",
)
R288_INVENTORY = (
    ROOT / "results" / "r288_topology_information" / "topology_inventory.json"
)
PLAN = ROOT / "memory" / "rounds" / ROUND_ID / "plan.md"
DEFAULT_SEAL = ROOT / "memory" / "rounds" / ROUND_ID / "diagnostic_seal.json"
DEFAULT_OUT = ROOT / "results" / "r290_topology_initialization"
PURE_MODULE = (
    ROOT / "src" / "andes_rl_kundur" / "evaluation" / "topology_information.py"
)
COMMON_MODULE = ROOT / "probes" / "eig_alloc_common.py"
ENV_SOURCE = (
    ROOT
    / "src"
    / "andes_rl_kundur"
    / "env"
    / "andes"
    / "andes_vsg_env_v4.py"
)
R289_SEAL = ROOT / "memory" / "rounds" / "R289" / "topology_information_seal.json"
R289_ANALYSIS = ROOT / "results" / "r289_topology_information" / "analysis.json"
HYPOTHESES = (
    "post-setup direct Line.u mutation leaves setup-derived topology state stale",
    "the public Line.set API with optional connectivity refresh fixes initialization",
    "EIG continues after TDS.test_ok=False and can expose an invalid-state spectrum",
    "a positive pair persisting after valid pre/post-setup application is physical in this model",
)


def _load_common():
    import eig_alloc_common

    return eig_alloc_common


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_json(path: Path, payload: object) -> str:
    sidecar = path.with_name(f"{path.name}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"formal diagnostic artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_verified_json(path: Path, expected: str | None = None) -> tuple[dict, str]:
    sidecar = path.with_name(f"{path.name}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"artifact or sidecar missing: {path}")
    digest = sha256_file(path)
    recorded = sidecar.read_text(encoding="utf-8").split()[0].lower()
    if digest != recorded:
        raise RuntimeError(f"sidecar mismatch for {path}")
    if expected is not None and digest != expected.lower():
        raise RuntimeError(f"unexpected SHA-256 for {path}: {digest}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload, digest


def _source_entry(path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        "plan": _source_entry(PLAN),
        "diagnostic_script": _source_entry(Path(__file__).resolve()),
        "pure_decision_module": _source_entry(PURE_MODULE),
        "eig_common": _source_entry(COMMON_MODULE),
        "environment": _source_entry(ENV_SOURCE),
        "r288_structural_input": _source_entry(R288_INVENTORY),
        "r289_seal": _source_entry(R289_SEAL),
        "r289_analysis": _source_entry(R289_ANALYSIS),
    }


def _verify_sources(seal: dict[str, Any]) -> None:
    for name, entry in seal["sources"].items():
        observed = sha256_file(ROOT / entry["path"])
        if observed != entry["sha256"]:
            raise RuntimeError(
                f"sealed source drift for {name}: {entry['sha256']} != {observed}"
            )


def _simple_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, np.generic):
        return value.item()
    return None


def _initialization_flags(ss: Any) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    for owner_name, owner in (("system", ss), ("tds", ss.TDS), ("eig", ss.EIG)):
        for attribute in (
            "initialized",
            "converged",
            "exit_code",
            "success",
            "test_ok",
        ):
            if not hasattr(owner, attribute):
                continue
            value = getattr(owner, attribute)
            if callable(value):
                continue
            simple = _simple_value(value)
            if simple is not None:
                flags[f"{owner_name}.{attribute}"] = simple
    return flags


def _max_abs(values: Any) -> float | None:
    array = np.asarray(values)
    if array.size == 0:
        return None
    finite = np.abs(array[np.isfinite(array)])
    return None if finite.size == 0 else float(np.max(finite))


def _base_line_statuses() -> dict[str, float]:
    payload = json.loads(R288_INVENTORY.read_text(encoding="utf-8"))
    return {str(row["idx"]): float(row["u"]) for row in payload["lines"]}


def _build_plant(common: Any, line_idx: str | None, method: str):
    if line_idx is None or method != "pre_setup_set":
        return common.build_frozen_plant()

    from andes.system import System

    original_setup = System.setup

    def setup_with_line_status(system):
        system.Line.set("u", line_idx, 0.0, attr="v")
        return original_setup(system)

    System.setup = setup_with_line_status
    try:
        return common.build_frozen_plant()
    finally:
        System.setup = original_setup


def reproduce(
    line_idx: str | None,
    *,
    method: str = "post_setup_direct",
) -> tuple[dict[str, Any], bool]:
    if method not in METHODS:
        raise ValueError(f"unknown method: {method}")
    common = _load_common()
    _, ss, vsg_pos = _build_plant(common, line_idx, method)
    q0 = allocation_library()["q0"]
    for position, machine_position in enumerate(vsg_pos):
        ss.GENCLS.M.v[machine_position] = q0[position]

    indices = [str(value) for value in ss.Line.idx.v]
    if line_idx is not None and method == "post_setup_direct":
        ss.Line.u.v[indices.index(line_idx)] = 0.0
    elif line_idx is not None and method in {
        "post_setup_set",
        "post_setup_set_connectivity",
    }:
        ss.Line.set("u", line_idx, 0.0, attr="v")
        if method == "post_setup_set_connectivity":
            ss.connectivity(info=False)
    after = [float(value) for value in ss.Line.u.v]
    base_status = _base_line_statuses()
    changed = [
        idx
        for idx, new in zip(indices, after, strict=True)
        if abs(base_status[idx] - new) > 1e-12
    ]

    pflow_return = ss.PFlow.run()
    eig_return = ss.EIG.run() if bool(pflow_return) else False
    eigenvalues = np.asarray(ss.EIG.mu) if bool(pflow_return) else np.asarray([])
    real = np.real(eigenvalues)
    finite = bool(
        eigenvalues.size
        and np.all(np.isfinite(real))
        and np.all(np.isfinite(np.imag(eigenvalues)))
    )
    positive_count = int(np.count_nonzero(real > POSITIVE_REAL_TOLERANCE))
    max_real = None if real.size == 0 else float(np.max(real))
    expected_changed = [] if line_idx is None else [line_idx]
    init_tol = float(ss.TDS.config.tol)
    max_f = _max_abs(ss.dae.f)
    max_g = _max_abs(ss.dae.g)
    residual_pass = bool(
        max_f is not None
        and max_g is not None
        and max(max_f, max_g) < init_tol
    )
    passed = bool(
        pflow_return
        and eig_return is not False
        and changed == expected_changed
        and ss.TDS.test_ok is True
        and ss.exit_code == 0
        and residual_pass
        and finite
        and positive_count == 0
    )
    result = {
        "line": line_idx,
        "method": method,
        "m_vector": list(q0),
        "changed_lines": changed,
        "pflow_return": _simple_value(pflow_return),
        "eig_return": _simple_value(eig_return),
        "initialization_flags": _initialization_flags(ss),
        "dae_max_abs_f": max_f,
        "dae_max_abs_g": max_g,
        "initialization_tolerance": init_tol,
        "residual_pass": residual_pass,
        "eigenvalue_finite": finite,
        "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
        "positive_real_count": positive_count,
        "max_real": max_real,
        "passed": passed,
    }
    return result, passed


def classify_diagnostic(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required = {"nominal", *METHODS}
    failures: list[str] = []
    if set(results) != required:
        failures.append(
            f"diagnostic result keys mismatch: {sorted(results)} != {sorted(required)}"
        )
    nominal = results.get("nominal", {})
    if nominal.get("passed") is not True or nominal.get("changed_lines") != []:
        failures.append("nominal q0 control did not pass")
    for method in METHODS:
        row = results.get(method, {})
        if row.get("pflow_return") is not True:
            failures.append(f"{method} PFlow failed")
        if row.get("changed_lines") != [TARGET_LINE]:
            failures.append(f"{method} did not change exactly {TARGET_LINE}")
        if row.get("eigenvalue_finite") is not True:
            failures.append(f"{method} eigenvalues are not finite")

    eligible = [
        method for method in METHODS if results.get(method, {}).get("passed") is True
    ]
    direct = results.get("post_setup_direct", {})
    public_set = results.get("post_setup_set", {})
    refreshed = results.get("post_setup_set_connectivity", {})
    pre_setup = results.get("pre_setup_set", {})
    direct_init_bug = bool(
        direct.get("initialization_flags", {}).get("tds.test_ok") is False
        and public_set.get("initialization_flags", {}).get("tds.test_ok") is True
        and public_set.get("residual_pass") is True
    )
    valid_init_rows = (public_set, refreshed, pre_setup)
    positive_persists = bool(
        all(
            row.get("initialization_flags", {}).get("tds.test_ok") is True
            and row.get("residual_pass") is True
            and int(row.get("positive_real_count", 0)) > 0
            for row in valid_init_rows
        )
        and max(float(row["max_real"]) for row in valid_init_rows)
        - min(float(row["max_real"]) for row in valid_init_rows)
        <= 1e-12
    )
    if failures:
        classification = "INVALID-DIAGNOSTIC"
    elif eligible:
        classification = "ROOT-CAUSE-AND-PATH-VALIDATED"
    elif direct_init_bug and positive_persists:
        classification = "ROOT-CAUSE-BOUNDED-NO-VALID-PATH"
    else:
        classification = "ROOT-CAUSE-BOUNDED-NO-VALID-PATH"
    return {
        "classification": classification,
        "integrity_failures": failures,
        "eligible_methods": eligible,
        "direct_mutation_initialization_bug": direct_init_bug,
        "positive_mode_persists_after_valid_initialization": positive_persists,
    }


def prepare(seal_path: Path) -> None:
    seal_path = seal_path.resolve()
    explicit_allocations = allocation_contract()
    ordered_allocation_items(explicit_allocations)
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "target": {
            "nominal_control": True,
            "line": TARGET_LINE,
            "m_vector": list(allocation_library()["q0"]),
        },
        "methods": list(METHODS),
        "hypotheses": list(HYPOTHESES),
        "thresholds": {
            "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
            "initialization_residual": "strictly below installed TDS.config.tol",
            "method_spectrum_match_tolerance": 1e-12,
        },
        "allocation_contract": explicit_allocations,
        "sources": _sources(),
        "asset_protection": {
            "r288_r289_read_only": True,
            "q0_only": True,
            "no_time_integration": True,
            "no_value_matrix": True,
            "no_training": True,
            "no_manuscript_write": True,
            "formal_artifacts_create_only": True,
        },
    }
    digest = _write_new_json(seal_path, seal)
    print(f"diagnostic_seal_sha256={digest}", flush=True)


def _load_seal(seal_path: Path, expected: str) -> tuple[dict, str]:
    seal, digest = _read_verified_json(seal_path.resolve(), expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("diagnostic seal identity mismatch")
    if tuple(seal.get("methods", ())) != METHODS:
        raise RuntimeError("diagnostic method order drift")
    if seal.get("target", {}).get("line") != TARGET_LINE:
        raise RuntimeError("diagnostic target drift")
    ordered_allocation_items(seal["allocation_contract"])
    _verify_sources(seal)
    return seal, digest


def formal_run(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    out_dir = out_dir.resolve()
    diagnostic_path = out_dir / "diagnostic.json"
    provenance_path = out_dir / "provenance.json"
    if diagnostic_path.exists() or provenance_path.exists():
        raise FileExistsError("R290 formal diagnostic artifacts already exist")

    results: dict[str, dict[str, Any]] = {}
    results["nominal"], _ = reproduce(None, method="post_setup_direct")
    for method in METHODS:
        results[method], _ = reproduce(TARGET_LINE, method=method)
        print(
            f"{method}: test_ok="
            f"{results[method]['initialization_flags'].get('tds.test_ok')} "
            f"positive={results[method]['positive_real_count']} "
            f"max_real={results[method]['max_real']}",
            flush=True,
        )
    analysis = classify_diagnostic(results)
    diagnostic = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "hypotheses": seal["hypotheses"],
        "results": results,
        "analysis": analysis,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    diagnostic_digest = _write_new_json(diagnostic_path, diagnostic)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {
            "path": seal_path.resolve().relative_to(ROOT).as_posix(),
            "sha256": seal_digest,
        },
        "diagnostic": {
            "path": diagnostic_path.relative_to(ROOT).as_posix(),
            "sha256": diagnostic_digest,
        },
        "sources_verified": seal["sources"],
        "allocation_order": seal["allocation_contract"]["order"],
    }
    provenance_digest = _write_new_json(provenance_path, provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"diagnostic_sha256={diagnostic_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    reproduce_parser = commands.add_parser("reproduce")
    reproduce_parser.add_argument("--line", default="Line_2")
    reproduce_parser.add_argument(
        "--method",
        choices=METHODS,
        default="post_setup_direct",
    )
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-seal-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "reproduce":
        line_idx = None if args.line.lower() == "nominal" else args.line
        result, passed = reproduce(line_idx, method=args.method)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if passed else 1
    if args.command == "prepare":
        prepare(args.seal)
    else:
        formal_run(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
