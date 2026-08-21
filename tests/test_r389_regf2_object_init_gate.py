from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r389_regf2_object_init_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r389_runner_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_configures_reused_lifecycle_for_r389_only() -> None:
    module = _load_runner()

    assert module.ROUND_ID == "R389"
    assert module.QUESTION_ID == "Q-0107"
    assert module.base.ROUND_ID == "R389"
    assert module.base.QUESTION_ID == "Q-0107"
    assert module.base.DEFAULT_OUT == module.DEFAULT_OUT
    assert module.DEFAULT_OUT.name == "r389_regf2_object_init_gate"


def test_inventory_serializes_exact_card_and_pll_linkage() -> None:
    module = _load_runner()
    card = module.build_regf2_object_init_contract()["parameter_card"]
    model = SimpleNamespace(
        idx=SimpleNamespace(v=["REGF2_1", "REGF2_2", "REGF2_3", "REGF2_4"]),
        bus=SimpleNamespace(v=[1, 2, 3, 4]),
        gen=SimpleNamespace(v=[1, 2, 3, 4]),
        Sn=SimpleNamespace(v=[900.0] * 4),
        u=SimpleNamespace(v=[1] * 4),
        pll=SimpleNamespace(v=["PLL2_1", "PLL2_2", "PLL2_3", "PLL2_4"]),
        **{key: SimpleNamespace(v=[value] * 4) for key, value in card.items() if key != "pll"},
    )
    system = SimpleNamespace(
        REGF2=model,
        PLL2=SimpleNamespace(
            idx=SimpleNamespace(v=["PLL2_1", "PLL2_2", "PLL2_3", "PLL2_4"]),
            bus=SimpleNamespace(v=[1, 2, 3, 4]),
            u=SimpleNamespace(v=[1] * 4),
        ),
    )

    runtime_card = {
        **card,
        "xf": 0.2 * 100.0 / 900.0,
        "Pmax": 9.0,
        "Pmin": -9.0,
        "Qmax": 9.0,
        "Qmin": -9.0,
    }
    for key, value in runtime_card.items():
        if key != "pll":
            getattr(model, key).v = [value] * 4
    bindings = [
        {
            "idx": f"REGF2_{index}",
            "bus": index,
            "gen": index,
            "Sn": 900.0,
            **card,
        }
        for index in range(1, 5)
    ]

    inventory = module.regf2_and_pll_inventory(system, bindings=bindings)

    assert [row["input_parameter_card"] for row in inventory["regf2"]] == [card] * 4
    assert [row["runtime_parameter_card"] for row in inventory["regf2"]] == [
        runtime_card
    ] * 4
    assert [row["pll"] for row in inventory["regf2"]] == [
        "PLL2_1",
        "PLL2_2",
        "PLL2_3",
        "PLL2_4",
    ]
    assert [row["bus"] for row in inventory["pll2"]] == [1, 2, 3, 4]


def test_execute_routes_to_create_only_r389_output(monkeypatch) -> None:
    module = _load_runner()
    observed = {}

    def fake_execute(*, expected_sha256, out_dir):
        observed.update(expected_sha256=expected_sha256, out_dir=out_dir)
        return "a" * 64

    monkeypatch.setattr(module.base, "execute", fake_execute)

    assert module.execute(expected_sha256="b" * 64) == "a" * 64
    assert observed == {
        "expected_sha256": "b" * 64,
        "out_dir": module.DEFAULT_OUT,
    }


def test_native_thread_seal_precedes_numpy_and_only_three_commands_exist() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert source.index('os.environ[_thread_variable] = "1"') < source.index(
        "import numpy as np"
    )
    parser = _load_runner().build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert set(choices) == {"rehearse", "prepare", "execute"}


def test_setup_only_canary_does_not_run_pflow_or_tds(monkeypatch) -> None:
    module = _load_runner()
    calls = []

    class ForbiddenRoutine:
        def run(self):
            raise AssertionError("rehearsal must not run PFlow or TDS")

    system = SimpleNamespace(
        is_setup=False,
        PFlow=ForbiddenRoutine(),
        TDS=ForbiddenRoutine(),
        REGF2=SimpleNamespace(n=4),
        PLL2=SimpleNamespace(n=4),
    )

    def setup():
        calls.append("setup")
        system.is_setup = True

    system.setup = setup
    built = SimpleNamespace(
        system=system,
        derived_case_sha256="d" * 64,
        bindings=(),
    )
    monkeypatch.setattr(
        module.base,
        "load_verified_static_case",
        lambda **_: SimpleNamespace(full_case={}),
    )
    monkeypatch.setattr(module, "build_regf2_static_kundur_object", lambda **_: built)
    monkeypatch.setattr(
        module,
        "_full_inventory",
        lambda *_: {
            "forbidden_model_counts": {name: 0 for name in module.build_regf2_object_init_contract()["forbidden_models"]},
            "forbidden_dae_names": [],
            "regf2": [
                {
                    "idx": f"REGF2_{index}",
                    "input_parameter_card": module.build_regf2_object_init_contract()["parameter_card"],
                    "runtime_parameter_card": module.build_regf2_object_init_contract()["runtime_parameter_card"],
                }
                for index in range(1, 5)
            ],
            "pll2": [{"bus": index} for index in range(1, 5)],
        },
    )

    result = module.setup_only_canary(
        {"xlsx_case_path": "case.xlsx", "json_case_path": "case.json"}
    )

    assert calls == ["setup"]
    assert result["physical_trajectory_executed"] is False
    assert result["setup_only_wall_seconds"] >= 0.0


def test_diagnostic_capture_uses_registered_residual_threshold() -> None:
    module = _load_runner()
    owner = SimpleNamespace(class_name="REGF2", idx=SimpleNamespace(v=["REGF2_1"]))
    variable = SimpleNamespace(
        owner=owner,
        a=np.asarray([0]),
        e_str="residual equation",
    )
    system = SimpleNamespace(
        dae=SimpleNamespace(
            fg=np.asarray([5.0e-6]),
            n=1,
            x_map={0: (None, variable)},
            y_map={},
            xy_name=["x REGF2 REGF2_1"],
        ),
        TDS=SimpleNamespace(config=SimpleNamespace(tol=1.0e-4)),
        exist=SimpleNamespace(pflow_tds={}),
    )

    diagnostics = module.capture_initialization_diagnostics(
        system,
        residual_threshold=1.0e-6,
    )

    assert diagnostics["captured"] is True
    assert diagnostics["bad_combined_indices"] == [0]
    assert diagnostics["residual_count"] == 1


def test_source_manifest_binds_durable_authority_and_implementation() -> None:
    module = _load_runner()
    manifest = module.source_manifest()

    assert {
        "runner",
        "lifecycle_base",
        "builder",
        "classifier",
        "builder_tests",
        "classifier_tests",
        "runner_tests",
        "plan",
        "question",
        "programme",
        "line",
        "route_contract",
        "artifact_manifest",
        "route_audit",
    } <= set(manifest)
    assert all(not row["path"].startswith("tmp/") for row in manifest.values())


def test_installed_case_hashes_must_match_frozen_contract() -> None:
    module = _load_runner()
    contract = module.build_regf2_object_init_contract()
    runtime = {
        "xlsx_case_sha256": contract["xlsx_case_sha256"],
        "json_case_sha256": contract["json_case_sha256"],
        "derived_case_sha256": contract["derived_case_sha256"],
    }

    assert module.installed_case_hashes_match(runtime, contract) is True
    for key in tuple(runtime):
        drifted = dict(runtime)
        drifted[key] = "0" * 64
        assert module.installed_case_hashes_match(drifted, contract) is False


def test_prepare_remeasures_zero_competing_processes_into_seal(
    monkeypatch,
    tmp_path,
) -> None:
    module = _load_runner()
    sources = {"runner": {"path": "runner.py", "sha256": "a" * 64}}
    parents = {"parent": {"path": "parent.json", "sha256": "b" * 64}}
    runtime = {"andes_version": "2.0.0"}
    rehearsal = tmp_path / "rehearsal.json"
    capacity_path = tmp_path / "capacity.json"
    seal = tmp_path / "formal_seal.json"
    out = tmp_path / "formal-output"
    observed = {}

    monkeypatch.setattr(module, "REHEARSAL", rehearsal)
    monkeypatch.setattr(module, "CAPACITY", capacity_path)
    monkeypatch.setattr(module, "SEAL", seal)
    monkeypatch.setattr(module, "DEFAULT_OUT", out)
    monkeypatch.setattr(module, "source_manifest", lambda: sources)
    monkeypatch.setattr(module, "parent_manifest", lambda: parents)
    monkeypatch.setattr(module, "installed_runtime", lambda: runtime)
    monkeypatch.setattr(module.base, "assert_posix_runtime", lambda: None)
    monkeypatch.setattr(module.base, "rehearsal_checks", lambda _: True)
    monkeypatch.setattr(module.base, "other_research_python_processes", lambda: [])
    monkeypatch.setattr(module.base, "sha256_file", lambda _: "c" * 64)

    def fake_read(path):
        if path == rehearsal:
            return {"sources": sources, "parents": parents, "installed_runtime": runtime}
        assert path == capacity_path
        return {
            "readiness": "RUN-READY",
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
        }

    def fake_write(path, payload):
        observed.update(path=path, payload=payload)
        return "d" * 64

    monkeypatch.setattr(module.base, "read_hashed_json", fake_read)
    monkeypatch.setattr(module.base, "write_new_json", fake_write)

    assert module.prepare() == "d" * 64
    assert observed["path"] == seal
    assert observed["payload"]["preseal_process_check"]["passed"] is True
    assert observed["payload"]["preseal_process_check"]["other_reserved_processes"] == 0
