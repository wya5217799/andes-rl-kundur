from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r391_regf2_equilibrium_eig_correction_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r391_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SparseLike:
    def __array__(self, *args, **kwargs):
        raise TypeError("installed sparse type has no direct NumPy conversion")


def test_dense_adapter_accepts_direct_and_sparse_fallback() -> None:
    module = _load_runner()

    direct = module.dense_andes_matrix(np.asarray([[1.0, 2.0]]))
    fallback = module.dense_andes_matrix(
        SparseLike(), sparse_converter=lambda _: [[3.0]]
    )

    assert direct.tolist() == [[1.0, 2.0]]
    assert fallback.tolist() == [[3.0]]


@pytest.mark.parametrize("value", ([1.0], [[float("nan")]]))
def test_dense_adapter_rejects_nonmatrix_or_nonfinite(value) -> None:
    module = _load_runner()

    with pytest.raises(ValueError):
        module.dense_andes_matrix(value)


def test_finite_status_uses_corrected_sparse_adapter(monkeypatch) -> None:
    module = _load_runner()
    monkeypatch.setattr(
        module.parent_runner.parent,
        "finite_guards",
        lambda _: (True, True),
    )
    system = SimpleNamespace(
        dae=SimpleNamespace(
            fx=SparseLike(),
            fy=SparseLike(),
            gx=SparseLike(),
            gy=SparseLike(),
        )
    )
    monkeypatch.setattr(
        module,
        "dense_andes_matrix",
        lambda _: np.asarray([[1.0]]),
    )

    status = module._finite_status(system, state_matrix_finite=True)

    assert status == {
        "checked": True,
        "dae_finite": True,
        "jacobian_finite": True,
        "state_matrix_finite": True,
    }


def test_parent_chain_and_lifecycle_route_to_r391() -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_correction_contract()

    assert module.validate_r390_parent_chain(contract) is True
    assert module.parent_runner.ROUND_ID == "R391"
    assert module.base.ROUND_ID == "R391"
    assert module.base.DEFAULT_OUT == module.DEFAULT_OUT
    assert module.DEFAULT_OUT.name == "r391_regf2_equilibrium_eig_correction_gate"


def test_source_manifest_binds_static_renderer_dependency() -> None:
    module = _load_runner()

    manifest = module.source_manifest()
    row = manifest["builder_base"]

    assert row["path"].endswith(
        "src/andes_rl_kundur/env/andes/regcv1_static_kundur.py"
    )
    assert len(row["sha256"]) == 64
    assert manifest["parent_object_runner"]["path"].endswith(
        "scripts/run_r389_regf2_object_init_gate.py"
    )
    assert manifest["lifecycle_base"]["path"].endswith(
        "scripts/run_r385_regcv1_clean_init_gate.py"
    )


@pytest.mark.parametrize(
    ("artifact", "field"),
    (
        ("formal_attempt.json", "seal_sha256"),
        ("formal_seal.json", "round"),
        ("formal_attempt.json", "round"),
        ("formal_execution.json", "round"),
        ("formal_analysis.json", "round"),
    ),
)
def test_parent_chain_rejects_internal_identity_corruption(
    monkeypatch, artifact: str, field: str
) -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_correction_contract()
    original = module.base.read_hashed_json

    def corrupted(path):
        value = deepcopy(original(path))
        if Path(path).name == artifact:
            value[field] = "forged"
        return value

    monkeypatch.setattr(module.base, "read_hashed_json", corrupted)

    assert module.validate_r390_parent_chain(contract) is False


def test_sparse_runtime_identity_is_frozen_and_fail_closed(monkeypatch) -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_correction_contract()
    runtime = dict(contract["sparse_adapter_runtime"])
    monkeypatch.setattr(
        module,
        "_parent_installed_runtime_matches_contract",
        lambda _runtime, _contract: True,
    )

    assert module.installed_runtime_matches_contract(runtime, contract) is True
    for key in tuple(runtime):
        forged = dict(runtime)
        forged[key] = "forged"
        assert (
            module.installed_runtime_matches_contract(forged, contract) is False
        )


def test_formal_record_uses_exact_two_parent_arms(monkeypatch) -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_correction_contract()
    calls = []

    def fake_run_arm(arm_spec, received_contract, runtime):
        calls.append((arm_spec["name"], received_contract is contract, runtime))
        return {"name": arm_spec["name"]}

    monkeypatch.setattr(module.parent_runner, "_run_arm", fake_run_arm)
    record = module.run_formal_record(contract, {"runtime": "sealed"})

    assert record["schema_version"] == 2
    assert record["round"] == "R391"
    assert record["trajectory_count"] == 0
    assert [row["name"] for row in record["arms"]] == [
        row["name"] for row in contract["arms"]
    ]
    assert all(same_contract for _, same_contract, _ in calls)


def test_runner_source_has_no_tds_run_call() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r391_regf2_equilibrium_eig_correction_gate.py"
    )
    source = path.read_text(encoding="utf-8")

    assert ".TDS.run(" not in source
    assert "training" in source
