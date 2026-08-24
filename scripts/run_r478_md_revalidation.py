"""R478 corrected M/D revalidation — thin adapter over the frozen
deterministic bank runners.

Authority: revalidation plan
``paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md``
(Phase 1A / 1B / 1C) and the frozen composition map
``tmp/yang_md_decoupling_marl/r478_adapter_map/bank_composition_map.md``.

Adapter rule (non-negotiable): the parent sealed runners and every frozen
scientific function stay byte-identical. This adapter only

- re-keys the round id and output roots of the loaded parent module,
- records an adapter sidecar (parent source hash + patched globals),
- delegates each phase to the parent's own entry point,
- runs the registered zero-action trace bank directly (Phase 1A/1C).

Family table (family -> parent runner -> corrected output root):

    zero            (none; tracers.run_zero_action_trace)  r478_zero_action
    ninelaw         run_r416_headroom_expansion            r478_md_ninelaw
    schedule        run_r458_dev_select_eval_validate      r478_md_schedule
    port_unseen     run_r409_heldout_gate                  r478_port_unseen
    port_extra_k35  run_r415_energy_port_extra_banks       r478_port_extra_k35
    port_extra_k4   run_r417_energy_port_banks_k4          r478_port_extra_k4
    topology        run_r413_topology_robustness           r478_topology_variants

Physical phases are WSL-only and must run through the scratch launcher:

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r478_md_revalidation.py <family> <command> [args...]

Every formal artifact is create-only with a ``.sha256`` sidecar. Parent
lineage keys inside inherited contracts (e.g. ``contract["r415"]``) are
true provenance and stay unchanged; the adapter identity is recorded in
the rekey sidecar instead of rewriting lineage.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# ─── Frozen parent source hashes (freeze-in 2026-08-24; fail-closed) ───

PARENT_SHA256 = {
    "run_r416_headroom_expansion.py":
        "16869b415df14e1942bd20ba0ff8d68558494846bc15c1dd3924a5685dd56a29",
    "run_r458_dev_select_eval_validate.py":
        "5be961a71defa2238cacf9685bf8875a1f9202d54d5134fce4b7f9d79ec883c8",
    "run_r409_heldout_gate.py":
        "14f012278c7f725566c7c6540b8bc5e81240be1f7cc70f31b1d022ea2da2f000",
    "run_r415_energy_port_extra_banks.py":
        "ac729240304cb1eb504e473673bd99d6a7d8d42fe2bc9d6c53d36a21ebba6fa3",
    "run_r417_energy_port_banks_k4.py":
        "1f30b781219660d191b2964eae222b6f02eb42998faec297ad0be42d15e6e7cf",
    "run_r413_topology_robustness.py":
        "60ed77ff0bccaa0ee1437ae0abe15e5f86d06ce5902e4ef846312ba523b7cd36",
}

FAMILIES: dict[str, dict[str, str | None]] = {
    "zero": {"parent": None, "out": "r478_zero_action"},
    "ninelaw": {"parent": "run_r416_headroom_expansion.py",
                "out": "r478_md_ninelaw"},
    "schedule": {"parent": "run_r458_dev_select_eval_validate.py",
                 "out": "r478_md_schedule"},
    "port_unseen": {"parent": "run_r409_heldout_gate.py",
                    "out": "r478_port_unseen"},
    "port_extra_k35": {"parent": "run_r415_energy_port_extra_banks.py",
                       "out": "r478_port_extra_k35"},
    "port_extra_k4": {"parent": "run_r417_energy_port_banks_k4.py",
                      "out": "r478_port_extra_k4"},
    "topology": {"parent": "run_r413_topology_robustness.py",
                 "out": "r478_topology_variants"},
}

ROUND_ID = "R478"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_json(path: Path, payload: dict[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_parent_source(name: str, path: Path) -> None:
    expected = PARENT_SHA256[name]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(
            f"frozen parent source drift: {name} "
            f"(expected {expected[:16]}..., got {actual[:16]}...)"
        )


def _rekey(parent: Any, family: str, out_root: Path) -> dict[str, Any]:
    """Patch parent module globals to the R478 identity; return the snapshot."""
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if hasattr(parent, "ROUND_ID"):
        before["ROUND_ID"] = parent.ROUND_ID
        parent.ROUND_ID = ROUND_ID
        after["ROUND_ID"] = parent.ROUND_ID
    for attr, rel in (
        ("OUT", f"results/research_loop/{out_root.name}"),
        ("LINE", "paper/yang_md_decoupling_marl/LINE.md"),
        ("PLAN", "memory/rounds/R478/plan.md"),
        ("REHEARSAL", "memory/rounds/R478/rehearsal.json"),
        ("CAPACITY", "memory/rounds/R478/capacity_evidence.json"),
        ("SEAL", "memory/rounds/R478/formal_seal.json"),
        ("DEV_SHARDS", "tmp/andes/r478_dev_shards.json"),
        ("EVAL_SHARDS", "tmp/andes/r478_eval_shards.json"),
    ):
        if hasattr(parent, attr):
            before[attr] = str(getattr(parent, attr))
            setattr(parent, attr, ROOT / rel)
            after[attr] = str(getattr(parent, attr))
    if hasattr(parent, "SELECTION"):
        before["SELECTION"] = str(parent.SELECTION)
        parent.SELECTION = parent.OUT / "selection.json"
        after["SELECTION"] = str(parent.SELECTION)
    return {"before": before, "after": after}


def _write_rekey_sidecar(
    *,
    family: str,
    command: str,
    command_args: tuple[str, ...],
    parent_name: str | None,
    parent_hash: str | None,
    snapshot: dict[str, Any],
    sidecar_dir: Path,
) -> Path:
    """Create-only per (family, command, args) identity sidecar.

    Re-dispatch with identical content is a no-op (needed for ``--resume``
    re-entry); a content mismatch is refused (fail-closed, no silent rekey).
    """
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    slug = "_".join(
        ["".join(ch if ch.isalnum() else "_" for ch in part) or "noargs"
         for part in (command, *command_args)]
    )
    path = sidecar_dir / f"{family}_{slug}.json"
    payload = {
        "adapter_round": ROUND_ID,
        "family": family,
        "command": command,
        "command_args": list(command_args),
        "parent_runner": parent_name,
        "parent_sha256": parent_hash,
        "adapter_sha256": _sha256_file(Path(__file__).resolve()),
        "rekey_snapshot": snapshot,
        "written_utc": datetime.now(UTC).isoformat(),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        # Drop the timestamp, which is the only field allowed to differ on a
        # byte-identical re-dispatch.
        existing_payload = json.loads(existing)
        existing_payload.pop("written_utc", None)
        payload.pop("written_utc", None)
        if existing_payload != payload:
            raise FileExistsError(f"rekey sidecar content mismatch: {path}")
        return path
    path.write_text(text, encoding="utf-8")
    return path


def _assert_wsl_scratch() -> None:
    """Physical phases are WSL-only and must run through the scratch launcher
    (ANDES writes kundur_full_out.* to cwd; the repo root must stay clean)."""
    if os.name != "posix":
        raise RuntimeError("physical phases are WSL/POSIX-only (ANDES runtime)")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("must run through scripts/andes_scratch.py")


# ─── Family: zero (registered zero-action trace bank, Phase 1A/1C) ───

def _zero_contract() -> dict[str, Any]:
    from andes_rl_kundur.probes.andes_common.paper_constants import (
        DEFAULT_PROBE_SEED,
        DEFAULT_PROBE_STEPS_SHORT,
        LS1_DELTA_U,
        LS2_DELTA_U,
    )
    return {
        "round": ROUND_ID,
        "family": "zero",
        "env": "andes_vsg_env_v4 corrected base convention (md_convention)",
        "scenarios": [
            {"id": "ls1", "delta_u": LS1_DELTA_U},
            {"id": "ls2", "delta_u": LS2_DELTA_U},
        ],
        "seed": DEFAULT_PROBE_SEED,
        "n_steps": DEFAULT_PROBE_STEPS_SHORT,
        "record_extras": ["freq_hz", "M_es", "D_es"],
        "runtime_readback_note": (
            "M_es/D_es are device-base telemetry; the runtime system-base "
            "values follow the declared exact conversion "
            "x_sys = x_dev * S_n / S_b (md_convention, S_n=200, S_b=100)."
        ),
    }


def _zero_prepare(out_root: Path) -> str:
    out_root.mkdir(parents=True, exist_ok=True)
    return _write_new_json(out_root / "contract.json", _zero_contract())


def _zero_rehearse(out_root: Path) -> str:
    """Walk the zero family's same-pre-attempt path without writing records.

    Runs both registered zero-action traces on the corrected env, asserts
    the zero-action invariant (device telemetry M_es/D_es constant across
    steps, no TDS failure), and returns a rehearsal digest. No formal
    artifact is created (create-only discipline: records.json only at
    execute).
    """
    _assert_wsl_scratch()
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.andes_common.paper_constants import (
        DEFAULT_PROBE_SEED,
        DEFAULT_PROBE_STEPS_SHORT,
        LS1_DELTA_U,
        LS2_DELTA_U,
    )
    from andes_rl_kundur.probes.andes_common.tracers import (
        run_zero_action_trace,
    )

    results = {}
    for scenario_id, delta_u in (("ls1", LS1_DELTA_U), ("ls2", LS2_DELTA_U)):
        result = run_zero_action_trace(
            AndesMultiVSGEnvV4,
            delta_u,
            h_forced=None,
            n_steps=DEFAULT_PROBE_STEPS_SHORT,
            seed=DEFAULT_PROBE_SEED,
            env_patch=None,
            record_extras=("freq_hz", "M_es", "D_es"),
        )
        if result["tds_failed"]:
            raise RuntimeError(f"zero rehearsal TDS failure: {scenario_id}")
        traj = result["traj"]  # dict[str, list[list[float]]] per record_extras
        m_values = traj.get("M_es") or []
        d_values = traj.get("D_es") or []
        if not m_values or not d_values:
            raise RuntimeError(f"zero rehearsal missing M/D extras: {scenario_id}")
        m0 = np.asarray(m_values[0], dtype=float)
        d0 = np.asarray(d_values[0], dtype=float)
        if not all(
            np.allclose(np.asarray(v, dtype=float), m0) for v in m_values
        ) or not all(
            np.allclose(np.asarray(v, dtype=float), d0) for v in d_values
        ):
            raise RuntimeError(
                f"zero rehearsal invariant failure: M_es/D_es drift: {scenario_id}"
            )
        results[scenario_id] = {
            "n_steps": int(result["n_steps"]),
            "max_df": float(result["max_df"]),
            "final_df": float(result["final_df"]),
            "M_es_first": m0.tolist(),
            "D_es_first": d0.tolist(),
        }
    rehearsal_dir = ROOT / "memory" / "rounds" / "R478"
    return _write_new_json(
        rehearsal_dir / "rehearsal_zero.json",
        {"round": ROUND_ID, "family": "zero", "checks": [
            "same-pre-attempt-path", "zero-action-preserves-M_es-D_es",
            "tds-ok"], "results": results},
    )


def _zero_execute(out_root: Path) -> str:
    _assert_wsl_scratch()
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.probes.andes_common.paper_constants import (
        DEFAULT_PROBE_SEED,
        DEFAULT_PROBE_STEPS_SHORT,
        LS1_DELTA_U,
        LS2_DELTA_U,
    )
    from andes_rl_kundur.probes.andes_common.tracers import (
        run_zero_action_trace,
    )

    records: dict[str, Any] = {}
    for scenario_id, delta_u in (("ls1", LS1_DELTA_U), ("ls2", LS2_DELTA_U)):
        result = run_zero_action_trace(
            AndesMultiVSGEnvV4,
            delta_u,
            h_forced=None,
            n_steps=DEFAULT_PROBE_STEPS_SHORT,
            seed=DEFAULT_PROBE_SEED,
            env_patch=None,
            record_extras=("freq_hz", "M_es", "D_es"),
        )
        if result["tds_failed"]:
            raise RuntimeError(f"zero execute TDS failure: {scenario_id}")
        records[scenario_id] = {
            "max_df": float(result["max_df"]),
            "final_df": float(result["final_df"]),
            "n_steps": int(result["n_steps"]),
            "tds_failed": bool(result["tds_failed"]),
            "delta_u": result["delta_u"],
            "traj": result["traj"],
            "df_traj": result["df_traj"],
        }
    out_root.mkdir(parents=True, exist_ok=True)
    return _write_new_json(out_root / "records.json", {"round": ROUND_ID,
                                                       "records": records})


# ─── Dispatcher ───

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=sorted(FAMILIES))
    parser.add_argument("command")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    family_cfg = FAMILIES[args.family]
    out_root = ROOT / "results" / "research_loop" / str(family_cfg["out"])
    sidecar_dir = ROOT / "memory" / "rounds" / "R478" / "adapter_rekey"

    if args.family == "zero":
        if args.command == "prepare":
            print(f"R478 zero contract: {_zero_prepare(out_root)}")
            return 0
        if args.command == "rehearse":
            print(f"R478 zero rehearsal: {_zero_rehearse(out_root)}")
            return 0
        if args.command == "execute":
            print(f"R478 zero records: {_zero_execute(out_root)}")
            return 0
        raise SystemExit("zero family commands: prepare | rehearse | execute")

    parent_name = str(family_cfg["parent"])
    parent_path = ROOT / "scripts" / parent_name
    _verify_parent_source(parent_name, parent_path)
    parent = _load_module(f"_r478_{args.family}_parent", parent_path)
    snapshot = _rekey(parent, args.family, out_root)
    sidecar = _write_rekey_sidecar(
        family=args.family,
        command=args.command,
        command_args=tuple(args.args),
        parent_name=parent_name,
        parent_hash=PARENT_SHA256[parent_name],
        snapshot=snapshot,
        sidecar_dir=sidecar_dir,
    )
    print(f"R478 rekey sidecar: {sidecar}")

    saved_argv = sys.argv
    try:
        sys.argv = [str(parent_path), args.command, *args.args]
        return int(parent.main())
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    raise SystemExit(main())
