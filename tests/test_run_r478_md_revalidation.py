"""R478 adapter offline tests — rekey machinery, family table, zero contract.

No ANDES import: these tests verify the thin-adapter identity layer on
any platform. Physical phases stay WSL-only.
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
        assert RUNNER.PARENT_SHA256[parent_name] == RUNNER._sha256_source_file(
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
    assert parent.DEV_SHARDS == (
        ROOT / "tmp/andes/r478_repair5_r478_md_schedule_dev_shards.json"
    )
    assert parent.EVAL_SHARDS == (
        ROOT / "tmp/andes/r478_repair5_r478_md_schedule_eval_shards.json"
    )
    assert parent.SELECTION == out_root / "selection.json"
    assert parent.PLAN == ROOT / "memory/rounds/R478/plan.md"
    assert "DEV_SHARDS" in snapshot["before"]


def test_parent_source_drift_is_rejected(tmp_path: Path) -> None:
    fake = tmp_path / "run_r416_headroom_expansion.py"
    fake.write_text("# mutated copy\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="frozen parent source drift"):
        RUNNER._verify_parent_source("run_r416_headroom_expansion.py", fake)


def test_parent_source_hash_is_checkout_line_ending_independent(
    tmp_path: Path,
) -> None:
    lf = tmp_path / "lf.py"
    crlf = tmp_path / "crlf.py"
    lf.write_bytes(b"x = 1\ny = 2\n")
    crlf.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert RUNNER._sha256_source_file(lf) == RUNNER._sha256_source_file(crlf)


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
    # Byte-identical re-dispatch (resume re-entry) is a no-op.
    again = RUNNER._write_rekey_sidecar(
        family="ninelaw", command="shards", command_args=(), **common
    )
    assert again == sidecar
    # Different command gets its own sidecar; content mismatch is refused.
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
    assert RUNNER.COMMAND_TRANSLATION["port_unseen"]["execute"] == ["--execute"]
    assert "measure-capacity" in RUNNER.FAMILY_COMMANDS["port_unseen"]
    assert "prepare" in RUNNER.FAMILY_COMMANDS["port_unseen"]
    assert "measure-capacity" in RUNNER.FAMILY_COMMANDS["ninelaw"]
    assert "select" in RUNNER.FAMILY_COMMANDS["schedule"]
    assert "inventory" in RUNNER.FAMILY_COMMANDS["topology"]
    assert "execute" in RUNNER.FAMILY_COMMANDS["zero"]
    assert RUNNER.EXECUTION_COMMANDS["zero"] == {"execute"}
    assert "execute" in RUNNER.EXECUTION_COMMANDS["port_unseen"]
    assert "shard" in RUNNER.EXECUTION_COMMANDS["schedule"]
    assert "shard" in RUNNER.FAMILY_COMMANDS["topology"]


def test_zero_contract_freezes_registered_scenarios() -> None:
    contract = RUNNER._zero_contract()
    assert contract["round"] == "R478"
    assert contract["seed"] == 42
    assert contract["n_steps"] == 30
    assert contract["record_extras"] == ["freq_hz", "M_es", "D_es"]
    assert [sc["id"] for sc in contract["scenarios"]] == ["ls1", "ls2"]
    assert contract["scenarios"][0]["delta_u"] == {"PQ_Bus14": -2.48}
    assert contract["scenarios"][1]["delta_u"] == {"PQ_Bus15": +1.88}


def test_zero_prepare_writes_create_only_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    digest = RUNNER._zero_prepare(contract_path)
    assert contract_path.is_file()
    assert (tmp_path / "contract.json.sha256").is_file()
    assert digest == RUNNER._sha256_file(contract_path)
    with pytest.raises(FileExistsError):
        RUNNER._zero_prepare(contract_path)


def test_capacity_ladder_uses_32_jobs_and_confirms_borderline_gain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    throughputs = {
        1: [1.0, 1.0],
        2: [1.04, 1.06],
        4: [1.20],
        8: [1.40],
        12: [1.60],
        16: [1.80],
    }
    calls: list[int] = []

    def fake_measure(_task, workers: int) -> dict[str, object]:
        calls.append(workers)
        throughput = throughputs[workers].pop(0)
        return {
            "workers": workers,
            "job_count": RUNNER.CAPACITY_TASKS_PER_RUNG,
            "all_records_valid": True,
            "maximum_worker_rss_bytes": 100,
            "throughput_jobs_per_second": throughput,
        }

    assert RUNNER.CAPACITY_RUNGS == (16,)
    assert RUNNER.CAPACITY_TASKS_PER_RUNG == 8
    monkeypatch.setattr(RUNNER, "_measure_capacity_rung", fake_measure)
    # The full-ladder algorithm is still exercised with the historical rung
    # set; the production constants are the owner-ordered fast ladder.
    monkeypatch.setattr(RUNNER, "CAPACITY_RUNGS", (1, 2, 4, 8, 12, 16))
    monkeypatch.setattr(RUNNER, "CAPACITY_TASKS_PER_RUNG", 32)
    payload = RUNNER._capacity_ladder(
        task=lambda _index: {"ok": True},
        family="zero",
        memory_total_bytes=10_000,
    )
    assert all(row["job_count"] == 32 for row in payload["rungs"])
    assert payload["confirmation_pairs"] == [
        {"low_workers": 1, "high_workers": 2}
    ]
    assert calls.count(1) == 2
    assert calls.count(2) == 2
    assert payload["final_throughput_jobs_per_second"][1] == pytest.approx(1.0)
    assert payload["final_throughput_jobs_per_second"][2] == pytest.approx(1.05)
    assert RUNNER.ADAPTER_CAPACITY_COMMANDS == {
        "schedule": "capacity",
        "port_extra_k35": "measure-capacity",
        "port_extra_k4": "measure-capacity",
    }


def test_pre_attempt_snapshot_checks_runtime_case_sources_and_real_output_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_path = tmp_path / "kundur_full.xlsx"
    case_path.write_bytes(b"case")
    monkeypatch.setattr(
        RUNNER,
        "_installed_runtime",
        lambda: {
            "python": "test-python",
            "andes_version": "test-andes",
            "andes_distribution_version": "test-andes",
            "andes_module_path": str(case_path),
            "andes_module_sha256": RUNNER._sha256_file(case_path),
            "case_path": str(case_path),
            "case_sha256": RUNNER._sha256_file(case_path),
        },
    )
    out_root = tmp_path / "formal-output"
    snapshot = RUNNER._adapter_pre_attempt_snapshot(
        family="zero", out_root=out_root, parent_name=None
    )
    assert snapshot["checks"] == {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
    }
    assert snapshot["installed_runtime"]["case_sha256"] == (
        RUNNER._sha256_file(case_path)
    )

    out_root.mkdir()
    blocked = RUNNER._adapter_pre_attempt_snapshot(
        family="zero", out_root=out_root, parent_name=None
    )
    assert blocked["checks"]["output_absence"] is False


def test_transitive_source_manifest_is_complete_and_detects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zero_paths = {
        entry["path"] for entry in RUNNER._adapter_sources("zero", None).values()
    }
    assert "src/andes_rl_kundur/env/andes/base_env.py" in zero_paths
    assert "src/andes_rl_kundur/env/andes/md_convention.py" in zero_paths
    assert "src/andes_rl_kundur/probes/andes_common/tracers.py" in zero_paths

    dependency = tmp_path / "src/andes_rl_kundur/dependency.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("VALUE = 1\n", encoding="utf-8")
    manifest = {
        "dependency": {
            "path": "src/andes_rl_kundur/dependency.py",
            "sha256": RUNNER._sha256_source_file(dependency),
        }
    }
    monkeypatch.setattr(RUNNER, "ROOT", tmp_path)
    assert RUNNER._source_manifest_valid(manifest) is True
    dependency.write_text("VALUE = 2\n", encoding="utf-8")
    assert RUNNER._source_manifest_valid(manifest) is False


def test_parent_seal_overlay_binds_rehearsal_sources_and_rejects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dependency = tmp_path / "src/andes_rl_kundur/dependency.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("VALUE = 1\n", encoding="utf-8")
    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"

    class FakeParent:
        REHEARSAL = rehearsal_path
        SEAL = seal_path

        @staticmethod
        def _write_new_json(path, payload):
            return RUNNER._write_new_json(path, dict(payload))

    monkeypatch.setattr(RUNNER, "ROOT", tmp_path)
    RUNNER._write_new_json(
        rehearsal_path,
        {
            "r478_pre_attempt": {
                "checks": {
                    "source_hash": True,
                    "parent_hash": True,
                    "installed_package": True,
                    "installed_case": True,
                    "output_absence": True,
                },
                "sources": {
                    "dependency": {
                        "path": "src/andes_rl_kundur/dependency.py",
                        "sha256": RUNNER._sha256_source_file(dependency),
                    }
                },
                "installed_runtime": {"identity": "runtime"},
            }
        },
    )
    parent = FakeParent()
    RUNNER._install_parent_seal_overlay(parent)
    parent._write_new_json(seal_path, {"sources": {}})
    seal, _digest = RUNNER._read_hashed_json(seal_path)
    assert "r478:dependency" in seal["sources"]
    assert seal["r478_installed_runtime"] == {"identity": "runtime"}

    dependency.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="parent sealed source drift"):
        RUNNER._verify_parent_overlay_seal(parent)


def test_physical_preformal_authorization_is_hashed_and_source_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization = tmp_path / "physical_authorization.json"
    monkeypatch.setattr(RUNNER, "PHYSICAL_EXECUTION_AUTHORIZATION", authorization)
    with pytest.raises(FileNotFoundError, match="missing artifact"):
        RUNNER._require_physical_authorization("zero", "measure-capacity")

    RUNNER._write_new_json(
        authorization,
        {
            "round": "R478",
            "authority_generation": "repair5",
            "physical_execution_authorized": True,
            "approved_commands": {
                "zero": ["measure-capacity", "rehearse"],
            },
            "sources": RUNNER._physical_authority_sources(),
        },
    )
    RUNNER._require_physical_authorization("zero", "measure-capacity")
    with pytest.raises(RuntimeError, match="does not approve"):
        RUNNER._require_physical_authorization("port_unseen", "rehearse")


def test_rehearsal_requires_green_hashed_capacity(tmp_path: Path) -> None:
    capacity_path = tmp_path / "capacity.json"
    with pytest.raises(FileNotFoundError, match="missing artifact"):
        RUNNER._require_capacity_before_rehearsal(capacity_path)
    RUNNER._write_new_json(capacity_path, {"all_ok": False})
    with pytest.raises(RuntimeError, match="capacity is not RUN-READY"):
        RUNNER._require_capacity_before_rehearsal(capacity_path)


def test_rehearsal_accepts_complete_parent_capacity_ladder(tmp_path: Path) -> None:
    capacity_path = tmp_path / "capacity.json"
    identity = {
        "sources": {"runner": {"sha256": "stable"}},
        "installed_runtime": {"case_sha256": "stable"},
    }
    RUNNER._write_new_json(
        capacity_path,
        {
            "readiness": "RUN-READY",
            "rungs": [
                {
                    "workers": workers,
                    "jobs": RUNNER.CAPACITY_TASKS_PER_RUNG,
                    "all_ok": True,
                }
                for workers in RUNNER.CAPACITY_RUNGS
            ],
            "confirmation_pass_2": [
                {
                    "workers": 2,
                    "job_count": RUNNER.CAPACITY_TASKS_PER_RUNG,
                    "all_records_valid": True,
                }
            ],
            "pre_attempt": identity,
            "post_attempt": identity,
            "identity_stable": True,
        },
    )
    capacity = RUNNER._require_capacity_before_rehearsal(
        capacity_path,
        current_snapshot=identity,
    )
    assert capacity["readiness"] == "RUN-READY"


def test_rehearsal_rejects_capacity_identity_drift(tmp_path: Path) -> None:
    capacity_path = tmp_path / "capacity.json"
    before = {
        "sources": {"runner": {"sha256": "before"}},
        "installed_runtime": {"case_sha256": "stable"},
    }
    after = {
        "sources": {"runner": {"sha256": "after"}},
        "installed_runtime": {"case_sha256": "stable"},
    }
    RUNNER._write_new_json(
        capacity_path,
        {
            "readiness": "RUN-READY",
            "rungs": [
                {
                    "workers": workers,
                    "jobs": RUNNER.CAPACITY_TASKS_PER_RUNG,
                    "all_ok": True,
                }
                for workers in RUNNER.CAPACITY_RUNGS
            ],
            "confirmation_pass_2": [],
            "pre_attempt": before,
            "post_attempt": after,
            "identity_stable": True,
        },
    )

    with pytest.raises(RuntimeError, match="capacity is not RUN-READY"):
        RUNNER._require_capacity_before_rehearsal(capacity_path)


def test_rehearsal_rejects_incomplete_parent_capacity_ladder(
    tmp_path: Path,
) -> None:
    capacity_path = tmp_path / "capacity.json"
    RUNNER._write_new_json(
        capacity_path,
        {
            "readiness": "RUN-READY",
            "rungs": [
                {
                    "workers": workers,
                    "job_count": RUNNER.CAPACITY_TASKS_PER_RUNG,
                    "all_records_valid": True,
                }
                for workers in RUNNER.CAPACITY_RUNGS[:-1]
            ],
        },
    )
    with pytest.raises(RuntimeError, match="capacity is not RUN-READY"):
        RUNNER._require_capacity_before_rehearsal(capacity_path)


def test_schedule_gate_requires_all_registered_evaluation_profiles() -> None:
    parent = _load_parent("run_r458_dev_select_eval_validate.py")
    evaluation = {
        profile: {"guards": {"joint_guard_feasible": profile == "eval_a"}}
        for profile in parent.EVAL_PROFILE_IDS
    }
    payload = {
        "integrity": {"valid": True, "errors": []},
        "selection": {"priority_branch": 1},
        "evaluation": evaluation,
        "classification": {
            "profiles_with_guard_clean_transfer": ["eval_a"],
            "transfer_count": 1,
            "verdict": "GUARD-CLEAN-TRANSFER",
        },
    }
    corrected = RUNNER._strict_schedule_analysis_payload(payload, parent)
    assert corrected["classification"]["verdict"] == (
        "NO-GUARD-CLEAN-TRANSFER"
    )
    assert corrected["classification"]["all_registered_profiles_guard_clean"] is False

    for row in evaluation.values():
        row["guards"]["joint_guard_feasible"] = True
    passed = RUNNER._strict_schedule_analysis_payload(payload, parent)
    assert passed["classification"]["verdict"] == "GUARD-CLEAN-TRANSFER"
    assert passed["classification"]["all_registered_profiles_guard_clean"] is True


def test_formal_execution_requires_owner_approval_bound_to_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seal_path = tmp_path / "formal_seal.json"
    seal_sha = RUNNER._write_new_json(
        seal_path,
        {"round": "R478", "family": "zero", "formal_authority": True},
    )
    missing = tmp_path / "missing_approval.json"
    monkeypatch.setattr(RUNNER, "OWNER_APPROVAL", missing)
    with pytest.raises(FileNotFoundError, match="missing artifact"):
        RUNNER._require_owner_approval("zero", seal_path)

    approval_path = tmp_path / "approval.json"
    RUNNER._write_new_json(
        approval_path,
        {
            "round": "R478",
            "owner_approved": True,
            "approved_seals": {"zero": seal_sha},
        },
    )
    monkeypatch.setattr(RUNNER, "OWNER_APPROVAL", approval_path)
    RUNNER._require_owner_approval("zero", seal_path)
