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
- dispatches the zero-action bank to the R478-owned module
  ``andes_rl_kundur.evaluation.r478_zero_action`` (Phase 1A/1C).

Family table (family -> parent runner -> corrected output root):

    zero            (none; r478_zero_action module)     r478_zero_action
    ninelaw         run_r416_headroom_expansion         r478_md_ninelaw
    schedule        run_r458_dev_select_eval_validate   r478_md_schedule
    port_unseen     run_r409_heldout_gate               r478_port_unseen
    port_extra_k35  run_r415_energy_port_extra_banks    r478_port_extra_k35
    port_extra_k4   run_r417_energy_port_banks_k4       r478_port_extra_k4
    topology        run_r413_topology_robustness        r478_topology_variants

Launch authority (Codex review P0, 2026-08-24): every physical command
(rehearse / execute / shard / capacity measurements) is BLOCKED until the
R478 seal exists (``<family> ... seal`` writes the frozen manifest) AND the
owner approval marker ``memory/rounds/R478/OWNER_APPROVED.json`` exists.
Seal-before-trace is enforced in code, not by convention.

Physical phases are WSL-only and must run through the scratch launcher:

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \\
        scripts/run_r478_md_revalidation.py <family> <command> [args...]

Every formal artifact is create-only with a ``.sha256`` sidecar. Parent
lineage keys inside inherited contracts (e.g. ``contract["r415"]``) are
true provenance and stay unchanged; the adapter identity is recorded in
the rekey sidecar instead of rewriting lineage. Parent source hashes are
computed on LF-normalized bytes so CRLF checkouts verify identically.
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

ROUND_ID = "R478"
SEAL_PATH = ROOT / "memory" / "rounds" / "R478" / "formal_seal.json"
APPROVAL_PATH = ROOT / "memory" / "rounds" / "R478" / "OWNER_APPROVED.json"

# ─── Frozen parent source hashes (LF-normalized; freeze-in 2026-08-24) ───

PARENT_SHA256 = {
    "run_r416_headroom_expansion.py":
        "16869b415df14e1942bd20ba0ff8d68558494846bc15c1dd3924a5685dd56a29",
    "run_r458_dev_select_eval_validate.py":
        "5be961a71defa2238cacf9685bf8875a1f9202d54d5134fce4b7f9d79ec883c8",
    "run_r409_heldout_gate.py":
        "14f012278c7f725566c7c6540b8bc5e81240be1f7cc70f31b1d022ea2da2f000",
    "run_r415_energy_port_extra_banks.py":
        "df84af97ef1bb0f94c42a4653ca05641ebd1ec414edae6d4dcc8bd17599f2dac",
    "run_r417_energy_port_banks_k4.py":
        "261046f49dda728982fa0015db9ffe1e3340b9944f5fded9cabbbb2c6ef7b7c5",
    "run_r413_topology_robustness.py":
        "2e1482d5250db64817654661cac18c6126b440eb6d84642ba93406d6fb6125f0",
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

# Parent CLI shapes differ: positional commands (R416/R458/R413/R415/R417)
# vs flags (R409). The adapter translates the uniform command vocabulary.
COMMAND_TRANSLATION: dict[str, dict[str, list[str]]] = {
    "port_unseen": {
        "measure-capacity": ["--measure-capacity"],
        "rehearse": ["--rehearse"],
        "execute": ["--execute"],
    },
}

FAMILY_COMMANDS: dict[str, frozenset[str]] = {
    "zero": frozenset({"prepare", "rehearse", "execute"}),
    "ninelaw": frozenset({"measure-capacity", "rehearse", "prepare",
                          "shards", "shard", "classify"}),
    "schedule": frozenset({"capacity", "rehearse", "prepare", "shard",
                           "select", "aggregate", "classify"}),
    # R409's measure-capacity writes its artifact to a hardcoded R409 path
    # (would clobber historical evidence); its rehearse does not require it.
    "port_unseen": frozenset({"rehearse", "execute"}),
    "port_extra_k35": frozenset({"measure-capacity", "rehearse", "prepare",
                                 "execute", "classify"}),
    "port_extra_k4": frozenset({"measure-capacity", "rehearse", "prepare",
                                "execute", "classify"}),
    "topology": frozenset({"inventory", "measure-capacity", "rehearse",
                           "prepare", "shards", "shard", "classify"}),
}

# Physical / formal-attempt commands blocked until seal + owner approval.
OWNER_GATED_COMMANDS: dict[str, frozenset[str]] = {
    "zero": frozenset({"rehearse", "execute"}),
    "ninelaw": frozenset({"measure-capacity", "rehearse", "shard"}),
    "schedule": frozenset({"capacity", "rehearse", "shard"}),
    "port_unseen": frozenset({"rehearse", "execute"}),
    "port_extra_k35": frozenset({"measure-capacity", "rehearse", "execute"}),
    "port_extra_k4": frozenset({"measure-capacity", "rehearse", "execute"}),
    "topology": frozenset({"measure-capacity", "rehearse", "shard"}),
}

SEALED_SOURCES: dict[str, str] = {
    "md_convention": "src/andes_rl_kundur/env/andes/md_convention.py",
    "base_env": "src/andes_rl_kundur/env/andes/base_env.py",
    "v4_environment": "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    "v5_environment": "src/andes_rl_kundur/env/andes/andes_vsg_env_v5.py",
    "distributed_residual_env":
        "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
    "zero_action_module":
        "src/andes_rl_kundur/evaluation/r478_zero_action.py",
    "parameter_card":
        "paper/yang_md_decoupling_marl/working/md_parameter_card_20260824.json",
    "plan": "memory/rounds/R478/plan.md",
    "invariant_tests": "tests/test_v4_md_convention_invariants.py",
    "extras_tests": "tests/test_v4_md_convention_extras.py",
    "regression_tests": "tests/test_v4_env_regression.py",
    "adapter_tests": "tests/test_run_r478_md_revalidation.py",
}


def _sha256_normalized(path: Path) -> str:
    """LF-normalized sha256: identical on CRLF and LF checkouts."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


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
    # Register the module so ProcessPoolExecutor workers can re-import (pickle)
    # functions defined inside the parent runner (capacity ladders fork pools).
    sys.modules[name] = module
    return module


def _verify_parent_source(name: str, path: Path) -> None:
    expected = PARENT_SHA256[name]
    actual = _sha256_normalized(path)
    if actual != expected:
        raise RuntimeError(
            f"frozen parent source drift: {name} "
            f"(expected {expected[:16]}..., got {actual[:16]}...)"
        )


def _rekey(parent: Any, family: str, out_root: Path) -> dict[str, Any]:
    """Patch parent module globals to the R478 identity; return the snapshot."""
    stem = out_root.name  # unique per family -> no cross-family path collisions
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if hasattr(parent, "ROUND_ID"):
        before["ROUND_ID"] = parent.ROUND_ID
        parent.ROUND_ID = ROUND_ID
        after["ROUND_ID"] = parent.ROUND_ID
    for attr, rel in (
        ("OUT", f"results/research_loop/{stem}"),
        ("LINE", "paper/yang_md_decoupling_marl/LINE.md"),
        ("PLAN", "memory/rounds/R478/plan.md"),
        ("REHEARSAL", f"memory/rounds/R478/rehearsal_{stem}.json"),
        ("CAPACITY", f"memory/rounds/R478/capacity_{stem}.json"),
        ("SEAL", f"memory/rounds/R478/formal_seal_{stem}.json"),
        ("DEV_SHARDS", f"tmp/andes/r478_{stem}_dev_shards.json"),
        ("EVAL_SHARDS", f"tmp/andes/r478_{stem}_eval_shards.json"),
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


def _patched_authority(parent: Any, family: str) -> dict[str, bool]:
    """R478-keyed equivalent of the parent's authority gate.

    Identity re-key only: every scientific check delegates to the parent's
    own primitives; the round-id string is the R478 plan. Parent source
    files stay byte-identical (the override is recorded in the rekey sidecar).
    """
    plan_text = (ROOT / "memory/rounds/R478/plan.md").read_text(encoding="utf-8")
    line_text = (
        ROOT / "paper/yang_md_decoupling_marl/LINE.md"
    ).read_text(encoding="utf-8")
    checks = {
        "active_plan": (
            "state: active" in plan_text
            and "manuscript_line: yang-md-decoupling-marl" in plan_text
            and "R478" in plan_text
        ),
        "active_line": (
            "line_id: yang-md-decoupling-marl" in line_text
            and "status: active" in line_text
        ),
        "output_absence": not parent.OUT.exists(),
    }
    if family == "ninelaw":
        contract = parent._r399_contract()
        checks.update({
            "contract_shape": (
                len(contract["profiles"]) == 6 and int(contract["steps"]) == 30
            ),
            "candidates_frozen": (
                len(parent.extended_candidate_ids()) == 21
                and set(parent.original_nine_ids()).issubset(
                    set(parent.extended_candidate_ids())
                )
            ),
        })
    elif family == "schedule":
        checks.update({
            "candidate_contract": (
                len(parent.candidates()) == 350
                and parent.R452.candidate_sequence_sha256()
                == parent.R452.EXPECTED_CANDIDATE_SHA256
            ),
            "shard_contract": (
                len(parent.expected_dev_shard_ids()) == 34
                and len(parent.expected_eval_shard_ids()) == 8
            ),
        })
    elif family in ("port_extra_k35", "port_extra_k4", "topology"):
        contract = parent._base_contract()
        checks.update({
            "contract_shape": (
                len(contract["mode_ids"]) == 4
                and int(contract["device_count"]) == 4
                and int(contract["steps"]) == 50
            ),
        })
        if family == "topology":
            checks["variant_bank_frozen"] = (
                len(parent.TOPOLOGY_VARIANTS) == 12
                and parent.variant_ids()[0] == "nominal"
            )
        else:
            checks["banks_frozen"] = (
                len(parent.BLOCKS) == 3
                and parent.block_ids()[0] == "a4_conditions_b"
            )
    return checks


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
        existing_payload = json.loads(existing)
        existing_payload.pop("written_utc", None)
        payload.pop("written_utc", None)
        if existing_payload != payload:
            raise FileExistsError(f"rekey sidecar content mismatch: {path}")
        return path
    path.write_text(text, encoding="utf-8")
    return path


def _seal_payload() -> dict[str, Any]:
    sources: dict[str, dict[str, str]] = {}
    for name, rel in (("adapter", "scripts/run_r478_md_revalidation.py"),):
        sources[name] = {"path": rel, "sha256": _sha256_normalized(ROOT / rel)}
    for name, digest in PARENT_SHA256.items():
        sources[name] = {"path": f"scripts/{name}", "sha256": digest}
    for name, rel in SEALED_SOURCES.items():
        sources[name] = {"path": rel, "sha256": _sha256_normalized(ROOT / rel)}
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "sources": sources,
        "authority": (
            "Frozen pre-launch program. Physical execution is blocked until "
            "OWNER_APPROVED.json exists (owner review gate, Codex review P0)."
        ),
    }


def cmd_seal() -> str:
    return _write_new_json(SEAL_PATH, _seal_payload())


def _require_launch_authority() -> None:
    """Fail closed until the frozen program is sealed AND owner-approved."""
    if not SEAL_PATH.is_file():
        raise RuntimeError(
            "R478 seal missing: the frozen program must be sealed first "
            "(run the 'seal' command) and physical execution is blocked "
            "until the owner approves it"
        )
    if not APPROVAL_PATH.is_file():
        raise RuntimeError(
            "owner approval missing: physical execution is blocked until "
            "the owner approves the frozen program "
            "(memory/rounds/R478/OWNER_APPROVED.json)"
        )


# ─── Dispatcher ───

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=sorted(FAMILIES) + ["seal"])
    parser.add_argument("command", nargs="?")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.family == "seal":
        print(f"R478 formal seal: {cmd_seal()}")
        return 0

    family_cfg = FAMILIES[args.family]
    allowed = FAMILY_COMMANDS[args.family]
    if args.command not in allowed:
        raise SystemExit(
            f"{args.family} commands: {' | '.join(sorted(allowed))}"
        )
    out_root = ROOT / "results" / "research_loop" / str(family_cfg["out"])
    sidecar_dir = ROOT / "memory" / "rounds" / "R478" / "adapter_rekey"

    if args.family == "zero":
        from andes_rl_kundur.evaluation.r478_zero_action import (
            build_contract,
            execute_payload,
            rehearsal_payload,
        )
        if args.command in OWNER_GATED_COMMANDS["zero"]:
            _require_launch_authority()
        if args.command == "prepare":
            out_root.mkdir(parents=True, exist_ok=True)
            digest = _write_new_json(out_root / "contract.json", build_contract())
            print(f"R478 zero contract: {digest}")
            return 0
        if args.command == "rehearse":
            digest = _write_new_json(
                ROOT / "memory/rounds/R478/rehearsal_zero.json",
                rehearsal_payload(),
            )
            print(f"R478 zero rehearsal: {digest}")
            return 0
        digest = _write_new_json(
            out_root / "records.json", execute_payload()
        )
        print(f"R478 zero records: {digest}")
        return 0

    parent_name = str(family_cfg["parent"])
    parent_path = ROOT / "scripts" / parent_name
    _verify_parent_source(parent_name, parent_path)
    if args.command in OWNER_GATED_COMMANDS[args.family]:
        _require_launch_authority()
    parent = _load_module(f"_r478_{args.family}_parent", parent_path)
    snapshot = _rekey(parent, args.family, out_root)
    for _auth_name in ("authority_checks", "_authority_checks"):
        if hasattr(parent, _auth_name):
            family_name = args.family
            setattr(
                parent,
                _auth_name,
                lambda: _patched_authority(parent, family_name),
            )
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
        translated = COMMAND_TRANSLATION.get(
            args.family, {}
        ).get(args.command, [args.command])
        sys.argv = [str(parent_path), *translated, *args.args]
        return int(parent.main())
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    raise SystemExit(main())
