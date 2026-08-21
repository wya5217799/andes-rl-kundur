from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r390_regf2_equilibrium_eig_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r390_runner_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_configures_create_only_r390_lifecycle() -> None:
    module = _load_runner()

    assert module.ROUND_ID == "R390"
    assert module.QUESTION_ID == "Q-0108"
    assert module.base.ROUND_ID == "R390"
    assert module.base.QUESTION_ID == "Q-0108"
    assert module.base.DEFAULT_OUT == module.DEFAULT_OUT
    assert module.DEFAULT_OUT.name == "r390_regf2_equilibrium_eig_gate"


def test_source_manifest_binds_parent_runtime_and_public_tests() -> None:
    module = _load_runner()

    manifest = module.source_manifest()

    assert {
        "runner",
        "parent_runner",
        "lifecycle_base",
        "builder",
        "parent_classifier",
        "classifier",
        "classifier_tests",
        "runner_tests",
        "plan",
        "question",
        "programme",
        "line",
        "route_contract",
        "artifact_manifest",
    } <= set(manifest)
    assert all(not row["path"].startswith("tmp/") for row in manifest.values())


def test_installed_runtime_must_match_every_frozen_model_and_solver_source() -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_contract()
    parent = contract["object_contract"]
    runtime = {
        "andes_version": parent["andes_version"],
        "xlsx_case_sha256": parent["xlsx_case_sha256"],
        "json_case_sha256": parent["json_case_sha256"],
        "derived_case_sha256": parent["derived_case_sha256"],
        "regf1_model_sha256": parent["regf1_source_sha256"],
        "regf2_model_sha256": parent["regf2_source_sha256"],
        "eig_source_sha256": contract["eig_source_sha256"],
        "pll2_source_sha256": contract["pll2_source_sha256"],
        "numpy_version": contract["numpy_version"],
        "scipy_version": contract["scipy_version"],
        "system_source_sha256": contract["system_source_sha256"],
        "tds_source_sha256": contract["tds_source_sha256"],
        "dae_source_sha256": contract["dae_source_sha256"],
    }

    assert module.installed_runtime_matches_contract(runtime, contract) is True
    for key in tuple(runtime):
        drifted = dict(runtime)
        drifted[key] = "drift"
        assert module.installed_runtime_matches_contract(drifted, contract) is False


def test_r389_parent_chain_is_verified_against_frozen_digests() -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_contract()

    assert module.validate_r389_parent_chain(contract) is True
    forged = {**contract, "r389_parent_sha256": dict(contract["r389_parent_sha256"])}
    forged["r389_parent_sha256"]["formal_execution"] = "0" * 64
    assert module.validate_r389_parent_chain(forged) is False


def test_setup_only_canary_never_runs_pflow_init_eig_or_trajectory(monkeypatch) -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_contract()
    calls = []

    class Forbidden:
        def __call__(self, *args, **kwargs):
            raise AssertionError("setup-only rehearsal crossed the scientific seam")

    regf2 = SimpleNamespace(n=4)
    pll2 = SimpleNamespace(n=4)
    for variable in contract["registered_state_variables"]["REGF2"]:
        setattr(regf2, variable, SimpleNamespace())
    for variable in contract["registered_state_variables"]["PLL2"]:
        setattr(pll2, variable, SimpleNamespace())
    system = SimpleNamespace(
        is_setup=False,
        REGF2=regf2,
        PLL2=pll2,
        PFlow=SimpleNamespace(run=Forbidden(), converged=False),
        TDS=SimpleNamespace(
            init=Forbidden(),
            run=Forbidden(),
            fg_update=Forbidden(),
            config=SimpleNamespace(tol=1.0e-4),
        ),
        EIG=SimpleNamespace(
            run=Forbidden(),
            calc_As=Forbidden(),
            As=None,
            mu=None,
            x_name=[],
            zstate_idx=[],
            dead_algeb_idx=[],
        ),
        dae=SimpleNamespace(
            x=[], y=[], z=[], f=[], g=[], fx=[], fy=[], gx=[], gy=[], Tf=[],
                x_name=[], y_name=[], z_name=[],
        ),
        j_update=Forbidden(),
    )

    def setup():
        calls.append("setup")
        system.is_setup = True

    system.setup = setup
    built = SimpleNamespace(
        system=system,
        derived_case_sha256=contract["object_contract"]["derived_case_sha256"],
        bindings=(),
    )
    monkeypatch.setattr(
        module.base,
        "load_verified_static_case",
        lambda **_: SimpleNamespace(full_case={}),
    )
    monkeypatch.setattr(
        module.parent, "build_regf2_static_kundur_object", lambda **_: built
    )
    monkeypatch.setattr(
        module.parent,
        "_full_inventory",
        lambda *_: {
            "forbidden_model_counts": {
                name: 0
                for name in contract["object_contract"]["forbidden_models"]
            },
            "forbidden_dae_names": [],
            "regf2": [
                {
                    "idx": f"REGF2_{index}",
                    "input_parameter_card": contract["object_contract"][
                        "parameter_card"
                    ],
                    "runtime_parameter_card": contract["object_contract"][
                        "runtime_parameter_card"
                    ],
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
    assert result["setup_completed"] is True
    assert result["eig_api_present"] is True
    assert result["registered_state_api_present"] is True
    assert result["runtime_api_present"] is True
    assert result["physical_trajectory_executed"] is False


def test_state_binding_resolves_exact_reduced_name_not_raw_dae_address() -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_contract()
    dae_names: list[str] = []
    models = {}
    address = 0
    for model_name, variables in contract["registered_state_variables"].items():
        model = SimpleNamespace(
            idx=SimpleNamespace(
                v=[f"{model_name}_{device}" for device in range(1, 5)]
            )
        )
        for variable_name in variables:
            addresses = []
            for device in range(1, 5):
                addresses.append(address)
                dae_names.append(
                    f"{variable_name} {model_name} {model_name}_{device}"
                )
                address += 1
            setattr(model, variable_name, SimpleNamespace(a=np.asarray(addresses)))
        models[model_name] = model
    reduced_names = list(reversed(dae_names))
    system = SimpleNamespace(
        **models,
        dae=SimpleNamespace(x_name=dae_names),
        EIG=SimpleNamespace(x_name=reduced_names, zstate_idx=[]),
    )

    bindings, zero_names = module.capture_state_bindings(system, contract)

    assert zero_names == []
    assert len(bindings) == len(dae_names)
    assert bindings[0]["reduced_index"] == len(dae_names) - 1
    assert bindings[0]["original_address"] == 0
    assert bindings[0]["dae_name"] == dae_names[0]

    system.EIG.x_name = [*reduced_names, reduced_names[0]]
    with pytest.raises(RuntimeError, match="reduced matches"):
        module.capture_state_bindings(system, contract)


def test_pflow_status_uses_authoritative_converged_flag_not_run_return() -> None:
    module = _load_runner()

    class PFlow:
        converged = True

        def run(self):
            return False

    assert module.run_pflow_and_read_converged(SimpleNamespace(PFlow=PFlow())) is True

    class FailedPFlow:
        converged = False

        def run(self):
            return True

    assert (
        module.run_pflow_and_read_converged(SimpleNamespace(PFlow=FailedPFlow()))
        is False
    )


def test_formal_record_runs_exact_two_ordered_no_trajectory_arms(monkeypatch) -> None:
    module = _load_runner()
    contract = module.build_regf2_equilibrium_eig_contract()
    observed = []

    def fake_run_arm(arm_spec, passed_contract, runtime):
        observed.append((arm_spec, passed_contract, runtime))
        return {"name": arm_spec["name"], "trajectory_count": 0}

    monkeypatch.setattr(module, "_run_arm", fake_run_arm)

    record = module.run_formal_record(contract, {"runtime": "sealed"})

    assert [row[0]["name"] for row in observed] == [
        "r389_reference_tol_1e-4",
        "sensitivity_tol_1e-6",
    ]
    assert all(row[1] is contract for row in observed)
    assert record["trajectory_count"] == 0
    assert record["post_init_action_executed"] is False
    assert record["training_executed"] is False
    assert [arm["name"] for arm in record["arms"]] == [
        "r389_reference_tol_1e-4",
        "sensitivity_tol_1e-6",
    ]


def test_run_arm_never_calls_tds_run_and_reads_actual_tolerance(monkeypatch) -> None:
    module = _load_runner()
    contract = deepcopy(module.build_regf2_equilibrium_eig_contract())
    contract["registered_state_variables"] = {}

    class PFlow:
        converged = False

        def run(self):
            self.converged = True
            return False

    class TDS:
        test_ok = True

        def __init__(self):
            self.config = SimpleNamespace(tol=9.0)

        def init(self):
            return True

        def fg_update(self, **_):
            return None

        def run(self):
            raise AssertionError("R390 must not run a trajectory")

    class EIG:
        As = np.asarray([[-1.0]])
        mu = np.asarray([-1.0 + 0.0j])
        x_name = ["x Other OTHER_1"]
        zstate_idx = []
        dead_algeb_idx = []

        def run(self):
            return True

    dae = SimpleNamespace(
        t=0.0,
        x=np.asarray([0.0]),
        y=np.asarray([1.0]),
        z=np.asarray([1.0]),
        f=np.asarray([0.0]),
        g=np.asarray([0.0]),
        fx=np.asarray([[0.0]]),
        fy=np.asarray([[0.0]]),
        gx=np.asarray([[0.0]]),
        gy=np.asarray([[1.0]]),
        Tf=np.asarray([1.0]),
            x_name=["x Other OTHER_1"],
            y_name=["y Other OTHER_1"],
            z_name=["z Other OTHER_1"],
        )
    system = SimpleNamespace(
        is_setup=False,
        exit_code=0,
        PFlow=PFlow(),
        TDS=TDS(),
        EIG=EIG(),
        dae=dae,
        exist=SimpleNamespace(pflow_tds={}),
    )

    def setup():
        system.is_setup = True
        system.TDS.config.tol = float(contract["arms"][0]["tds_tolerance"])

    system.setup = setup
    system.j_update = lambda **_: None
    built = SimpleNamespace(
        system=system,
        derived_case_sha256=contract["object_contract"]["derived_case_sha256"],
    )
    audit = SimpleNamespace(
        full_case={},
        xlsx_json_static_equal=True,
        xlsx_sha256=contract["object_contract"]["xlsx_case_sha256"],
        json_sha256=contract["object_contract"]["json_case_sha256"],
    )
    runtime = {
        "xlsx_case_path": "case.xlsx",
        "json_case_path": "case.json",
        "derived_case_sha256": built.derived_case_sha256,
        "andes_version": "2.0.0",
        "regf1_model_sha256": contract["object_contract"]["regf1_source_sha256"],
        "regf2_model_sha256": contract["object_contract"]["regf2_source_sha256"],
        **{
            key: contract[key]
            for key in (
                "eig_source_sha256",
                "pll2_source_sha256",
                "numpy_version",
                "scipy_version",
                "system_source_sha256",
                "tds_source_sha256",
                "dae_source_sha256",
            )
        },
    }
    monkeypatch.setattr(module.base, "load_verified_static_case", lambda **_: audit)
    monkeypatch.setattr(
        module.parent, "build_regf2_static_kundur_object", lambda **_: built
    )
    monkeypatch.setattr(module.parent, "_full_inventory", lambda *_: {})
    monkeypatch.setattr(module.parent, "_source_snapshot", lambda *_: [])
    monkeypatch.setattr(module.parent, "post_init_references", lambda *_: {})
    monkeypatch.setattr(
        module.parent,
        "capture_initialization_diagnostics",
        lambda *_args, **_kwargs: {"captured": True},
    )
    monkeypatch.setattr(module.parent, "finite_guards", lambda *_: (True, True))

    arm = module._run_arm(contract["arms"][0], contract, runtime)

    assert arm["execution_error"] is None
    assert arm["solver"]["pflow_converged"] is True
    assert arm["solver"]["actual_tds_tolerance"] == 1.0e-4
    assert arm["solver"]["eig_return"] is True
    assert arm["trajectory_attempted"] is False
    assert arm["physical_trajectory_executed"] is False


def test_thread_seal_precedes_numerics_and_no_trajectory_command_exists() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert source.index('os.environ[_thread_variable] = "1"') < source.index(
        "import numpy as np"
    )
    assert source.index('os.environ[_thread_variable] = "1"') < source.index(
        "PARENT_RUNNER ="
    )
    assert "system.TDS.run(" not in source
    parser = _load_runner().build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert set(choices) == {"rehearse", "prepare", "execute"}


def test_prepare_remeasures_zero_competing_processes_into_seal(
    monkeypatch, tmp_path
) -> None:
    module = _load_runner()
    sources = {"runner": {"path": "runner.py", "sha256": "a" * 64}}
    parents = {"r389": {"path": "parent.json", "sha256": "b" * 64}}
    runtime = {"runtime": "sealed"}
    rehearsal = tmp_path / "rehearsal.json"
    capacity_path = tmp_path / "capacity.json"
    seal = tmp_path / "formal_seal.json"
    output = tmp_path / "formal-output"
    observed = {}

    monkeypatch.setattr(module, "REHEARSAL", rehearsal)
    monkeypatch.setattr(module, "CAPACITY", capacity_path)
    monkeypatch.setattr(module, "SEAL", seal)
    monkeypatch.setattr(module, "DEFAULT_OUT", output)
    monkeypatch.setattr(module, "source_manifest", lambda: sources)
    monkeypatch.setattr(module, "parent_manifest", lambda: parents)
    monkeypatch.setattr(module, "installed_runtime", lambda: runtime)
    monkeypatch.setattr(
        module, "installed_runtime_matches_contract", lambda *_: True
    )
    monkeypatch.setattr(module, "validate_r389_parent_chain", lambda *_: True)
    monkeypatch.setattr(module.base, "assert_posix_runtime", lambda: None)
    monkeypatch.setattr(module.base, "rehearsal_checks", lambda _: True)
    monkeypatch.setattr(module.base, "other_research_python_processes", lambda: [])
    monkeypatch.setattr(module.base, "sha256_file", lambda _: "c" * 64)

    def fake_read(path):
        if path == rehearsal:
            return {
                "sources": sources,
                "parents": parents,
                "installed_runtime": runtime,
            }
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
    assert observed["payload"]["launch"] == {
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
    }
