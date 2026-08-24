"""R478 adapter offline tests — rekey machinery, family table, launch gates.

No ANDES import: these tests verify the thin-adapter identity layer and
the seal/owner launch gates on any platform. Physical phases stay
WSL-only and are additionally blocked until owner approval.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

SPEC = importlib.util.spec_from_file_location(
    "_r478_runner_test",
    ROOT / "scripts" / "run_r478_md_revalidation.py",
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

from andes_rl_kundur.evaluation.r478_zero_action import (  # noqa: E402
    build_contract as zero_build_contract,
)


def _load_parent(name: str):
    spec = importlib.util.spec_from_file_location(
        f"_test_parent_{name}", ROOT / "scripts" / name
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_family_table_parents_exist_and_hashes_frozen() -> None:
    for family, cfg in RUNNER.FAMILIES.items():
        if cfg["parent"] is None:
            assert family == "zero"
            continue
        parent_name = str(cfg["parent"])
        parent_path = ROOT / "scripts" / parent_name
        assert parent_path.is_file(), f"missing parent runner: {parent_name}"
        assert RUNNER.PARENT_SHA256[parent_name] == RUNNER._sha256_normalized(
            parent_path
        ), f"parent hash drift: {parent_name}"
    out_names = [str(cfg["out"]) for cfg in RUNNER.FAMILIES.values()]
    assert len(out_names) == len(set(out_names)), "output roots must be distinct"


def test_rekey_patches_round_and_out_for_r416_parent() -> None:
    parent = _load_parent("run_r416_headroom_expansion.py")
    out_root = ROOT / "results" / "research_loop" / "r478_md_ninelaw"
    snapshot = RUNNER._rekey(parent, "ninelaw", out_root)
    assert parent.ROUND_ID == "R478"
    assert parent.OUT == out_root
    assert snapshot["before"]["ROUND_ID"] == "R416"
    assert snapshot["after"]["ROUND_ID"] == "R478"


def test_rekey_patches_shard_and_selection_paths_for_r458_parent() -> None:
    parent = _load_parent("run_r458_dev_select_eval_validate.py")
    out_root = ROOT / "results" / "research_loop" / "r478_md_schedule"
    snapshot = RUNNER._rekey(parent, "schedule", out_root)
    assert parent.ROUND_ID == "R478"
    assert parent.OUT == out_root
    assert parent.DEV_SHARDS == ROOT / "tmp/andes/r478_r478_md_schedule_dev_shards.json"
    assert parent.EVAL_SHARDS == ROOT / "tmp/andes/r478_r478_md_schedule_eval_shards.json"
    assert parent.SELECTION == out_root / "selection.json"
    assert parent.PLAN == ROOT / "memory/rounds/R478/plan.md"
    assert "DEV_SHARDS" in snapshot["before"]


def test_parent_source_drift_is_rejected(tmp_path: Path) -> None:
    fake = tmp_path / "run_r416_headroom_expansion.py"
    fake.write_text("# mutated copy\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="frozen parent source drift"):
        RUNNER._verify_parent_source("run_r416_headroom_expansion.py", fake)


def test_normalized_hashing_is_crlf_insensitive(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"hello\nworld\n")
    crlf.write_bytes(b"hello\r\nworld\r\n")
    assert RUNNER._sha256_normalized(lf) == RUNNER._sha256_normalized(crlf)


def test_launch_gate_blocks_physical_commands_without_owner_approval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(RUNNER, "SEAL_PATH", tmp_path / "formal_seal.json")
    monkeypatch.setattr(RUNNER, "APPROVAL_PATH", tmp_path / "OWNER_APPROVED.json")
    with pytest.raises(RuntimeError, match="seal missing"):
        RUNNER._require_launch_authority()
    (tmp_path / "formal_seal.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="owner approval missing"):
        RUNNER._require_launch_authority()
    (tmp_path / "OWNER_APPROVED.json").write_text("{}\n", encoding="utf-8")
    RUNNER._require_launch_authority()  # both present -> pass


def test_gated_commands_refuse_before_approval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(RUNNER, "SEAL_PATH", tmp_path / "formal_seal.json")
    monkeypatch.setattr(RUNNER, "APPROVAL_PATH", tmp_path / "OWNER_APPROVED.json")
    with pytest.raises(RuntimeError, match="seal missing"):
        RUNNER.main(["zero", "execute"])
    with pytest.raises(RuntimeError, match="seal missing"):
        RUNNER.main(["port_unseen", "rehearse"])


def test_rekey_sidecar_records_identity_and_is_idempotent(tmp_path: Path) -> None:
    common = dict(
        parent_name="run_r416_headroom_expansion.py",
        parent_hash=RUNNER.PARENT_SHA256["run_r416_headroom_expansion.py"],
        snapshot={"before": {"ROUND_ID": "R416"}, "after": {"ROUND_ID": "R478"}},
        sidecar_dir=tmp_path,
    )
    sidecar = RUNNER._write_rekey_sidecar(
        family="ninelaw", command="shards", command_args=(), **common
    )
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["adapter_round"] == "R478"
    assert payload["family"] == "ninelaw"
    assert payload["parent_sha256"].startswith("16869b41")
    again = RUNNER._write_rekey_sidecar(
        family="ninelaw", command="shards", command_args=(), **common
    )
    assert again == sidecar
    other = RUNNER._write_rekey_sidecar(
        family="ninelaw", command="shard",
        command_args=("local_neighbour_md_km1_kd1",), **common
    )
    assert other != sidecar
    with pytest.raises(FileExistsError, match="content mismatch"):
        RUNNER._write_rekey_sidecar(
            family="ninelaw",
            command="shards",
            command_args=(),
            parent_name="run_r416_headroom_expansion.py",
            parent_hash="x",
            snapshot={},
            sidecar_dir=tmp_path,
        )


def test_patched_authority_is_r478_keyed_and_scientific_checks_delegated() -> None:
    for family, parent_name, keys in (
        ("ninelaw", "run_r416_headroom_expansion.py",
         {"contract_shape", "candidates_frozen"}),
        ("schedule", "run_r458_dev_select_eval_validate.py",
         {"candidate_contract", "shard_contract"}),
        ("topology", "run_r413_topology_robustness.py",
         {"contract_shape", "variant_bank_frozen"}),
        ("port_extra_k35", "run_r415_energy_port_extra_banks.py",
         {"contract_shape", "banks_frozen"}),
    ):
        parent = _load_parent(parent_name)
        out_root = ROOT / "results" / "research_loop" / str(
            RUNNER.FAMILIES[family]["out"]
        )
        RUNNER._rekey(parent, family, out_root)
        checks = RUNNER._patched_authority(parent, family)
        assert checks["active_plan"] is True
        assert checks["active_line"] is True
        assert keys <= set(checks), f"{family} missing delegated checks"
        assert all(checks.values()), f"{family} authority not all green: {checks}"


def test_command_vocabulary_and_translation() -> None:
    assert RUNNER.COMMAND_TRANSLATION["port_unseen"]["rehearse"] == ["--rehearse"]
    assert RUNNER.COMMAND_TRANSLATION["port_unseen"]["execute"] == ["--execute"]
    assert "measure-capacity" in RUNNER.FAMILY_COMMANDS["ninelaw"]
    assert "select" in RUNNER.FAMILY_COMMANDS["schedule"]
    assert "inventory" in RUNNER.FAMILY_COMMANDS["topology"]
    assert "execute" in RUNNER.FAMILY_COMMANDS["zero"]
    assert "shard" in RUNNER.FAMILY_COMMANDS["topology"]
    assert RUNNER.OWNER_GATED_COMMANDS["zero"] == frozenset(
        {"rehearse", "execute"}
    )
    assert "prepare" not in RUNNER.OWNER_GATED_COMMANDS["ninelaw"]


def test_zero_contract_freezes_registered_scenarios() -> None:
    contract = zero_build_contract()
    assert contract["round"] == "R478"
    assert contract["seed"] == 42
    assert contract["n_steps"] == 30
    assert contract["record_extras"] == ["freq_hz", "M_es", "D_es"]
    assert [sc["id"] for sc in contract["scenarios"]] == ["ls1", "ls2"]
    assert contract["scenarios"][0]["delta_u"] == {"PQ_Bus14": -2.48}
    assert contract["scenarios"][1]["delta_u"] == {"PQ_Bus15": +1.88}
