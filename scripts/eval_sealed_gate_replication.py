"""Prepare, seal, execute, and analyse a prospective controller replication.

This is the thin real-ANDES driver for the reusable sealing/statistics
primitives in :mod:`andes_rl_kundur.evaluation.sealed_bank`.  Two frozen
profiles are supported:

* ``q0028-gate`` keeps the original four-controller R265 replication;
* ``q0029-slew`` compares static alpha=0.25, the raw mode-ratio gate, and the
  single prospectively fixed alpha-slew mechanism on a new no-anchor bank.

Usage
-----
Prepare the bank before any controller trajectory (Windows or WSL):

```
python scripts/eval_sealed_gate_replication.py --profile q0029-slew \
  prepare-bank --bank memory/rounds/R267/scenario_bank.json
```

After recording the printed bank hash in the prospective plan, prepare a seal
before any controller trajectory:

```
python scripts/eval_sealed_gate_replication.py --profile q0029-slew \
  prepare-seal --bank memory/rounds/R267/scenario_bank.json \
  --expected-bank-sha256 <digest> --plan memory/rounds/R267/plan.md \
  --ckpt-dir results/r201_w1_hreg_tau005_s54 \
  --manifest memory/rounds/R267/scenario_bank.manifest.json
```

Then run real ANDES in WSL:

```
/home/wya/andes_venv/bin/python scripts/eval_sealed_gate_replication.py \
  --profile q0029-slew evaluate \
  --bank memory/rounds/R267/scenario_bank.json \
  --expected-bank-sha256 <digest> \
  --seal-manifest memory/rounds/R267/scenario_bank.manifest.json \
  --expected-manifest-sha256 <digest> \
  --ckpt-dir results/r201_w1_hreg_tau005_s54 \
  --out-dir results/r267_q0029_slew_replication
```

Use ``--resume`` after interruption.  Existing artifacts are only reused when
their sealed-bank, scenario, controller, run-order, and checkpoint provenance
match exactly.  There is deliberately no overwrite option.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.hybrid import (  # noqa: E402
    convex_blend_action_fn,
    mode_ratio_gated_blend_action_fn,
    proportional_damping_action_fn,
    slew_limited_mode_ratio_gated_blend_action_fn,
)
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.evaluation.paper_strict_eval import (  # noqa: E402
    compute_global_cum_rf,
)
from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    binomial_rate_summary,
    build_scenario_bank,
    classify_gate_replication,
    classify_smoothing_replication,
    empirical_upper_tail,
    load_scenario_bank,
    paired_binary_outcome_table,
    paired_bootstrap_contrasts,
    sha256_file,
    write_scenario_bank,
)

BANK_N = 20
BANK_SEED = 20260724
ENV_SEED = 42
STEPS = 150
DROOP_K = 10.0
STATIC_ALPHA = 0.25
GATE_ALPHA_CAP = 0.25
GATE_RATIO_FULL_SCALE = 0.05
BOOTSTRAP_SEED = 2026072401
BOOTSTRAP_RESAMPLES = 10_000
EXPERIMENT_PROFILE = "q0028-gate"
EXPERIMENT_KEY = "q0028_sealed_gate_replication"
RAW_GATE_CONTROLLER: str | None = None

CONTROLLER_ORDER = (
    "r201",
    "droop_k10",
    "static_a0p25",
    "mode_gate_c0p25",
)
STATIC_CONTROLLER = "static_a0p25"
GATE_CONTROLLER = "mode_gate_c0p25"
CONTROLLER_SPECS: dict[str, dict[str, Any]] = {
    "r201": {
        "kind": "legacy_deterministic_actor",
        "checkpoint_suffix": "best",
    },
    "droop_k10": {
        "kind": "proportional_damping",
        "droop_k": DROOP_K,
    },
    "static_a0p25": {
        "kind": "convex_learned_droop_blend",
        "droop_k": DROOP_K,
        "alpha": STATIC_ALPHA,
    },
    "mode_gate_c0p25": {
        "kind": "common_differential_mode_ratio_gated_residual",
        "droop_k": DROOP_K,
        "alpha_cap": GATE_ALPHA_CAP,
        "ratio_full_scale": GATE_RATIO_FULL_SCALE,
    },
}
CONTRASTS = (
    ("gate_minus_static", GATE_CONTROLLER, STATIC_CONTROLLER),
    ("gate_minus_r201", GATE_CONTROLLER, "r201"),
    ("gate_minus_droop", GATE_CONTROLLER, "droop_k10"),
    ("static_minus_r201", STATIC_CONTROLLER, "r201"),
    ("static_minus_droop", STATIC_CONTROLLER, "droop_k10"),
)
CONTINUOUS_ENDPOINTS = (
    "worst_bus_peak_abs_hz",
    "vsg_mean_peak_abs_hz",
    "vsg_mean_iae_hz_s",
    "dispersion_rms_hz",
    "dispersion_ise_hz2_s",
    "normalized_sync_loss_hz2",
    "max_abs_rocof_hz_s",
    "terminal_worst_bus_abs_hz",
    "action_l1_agent_s",
    "action_total_variation",
    "action_saturation_fraction",
    "legacy_normalized_sync_loss_hz2",
)


def _activate_profile(profile: str) -> None:
    """Activate one pre-registered controller/bank profile.

    The original Q-0028 profile remains the default so its read-only analysis
    contract is unchanged.  Q-0029 reuses the same sealing, trace, endpoint,
    bootstrap, failure, and tail machinery with a different frozen controller
    set and bank seed.
    """
    global BANK_SEED
    global BOOTSTRAP_SEED
    global EXPERIMENT_PROFILE
    global EXPERIMENT_KEY
    global CONTROLLER_ORDER
    global STATIC_CONTROLLER
    global GATE_CONTROLLER
    global RAW_GATE_CONTROLLER
    global CONTROLLER_SPECS
    global CONTRASTS

    if profile == "q0028-gate":
        BANK_SEED = 20260724
        BOOTSTRAP_SEED = 2026072401
        EXPERIMENT_PROFILE = profile
        EXPERIMENT_KEY = "q0028_sealed_gate_replication"
        CONTROLLER_ORDER = (
            "r201",
            "droop_k10",
            "static_a0p25",
            "mode_gate_c0p25",
        )
        STATIC_CONTROLLER = "static_a0p25"
        GATE_CONTROLLER = "mode_gate_c0p25"
        RAW_GATE_CONTROLLER = None
        CONTROLLER_SPECS = {
            "r201": {
                "kind": "legacy_deterministic_actor",
                "checkpoint_suffix": "best",
            },
            "droop_k10": {
                "kind": "proportional_damping",
                "droop_k": DROOP_K,
            },
            "static_a0p25": {
                "kind": "convex_learned_droop_blend",
                "droop_k": DROOP_K,
                "alpha": STATIC_ALPHA,
            },
            "mode_gate_c0p25": {
                "kind": "common_differential_mode_ratio_gated_residual",
                "droop_k": DROOP_K,
                "alpha_cap": GATE_ALPHA_CAP,
                "ratio_full_scale": GATE_RATIO_FULL_SCALE,
            },
        }
        CONTRASTS = (
            ("gate_minus_static", GATE_CONTROLLER, STATIC_CONTROLLER),
            ("gate_minus_r201", GATE_CONTROLLER, "r201"),
            ("gate_minus_droop", GATE_CONTROLLER, "droop_k10"),
            ("static_minus_r201", STATIC_CONTROLLER, "r201"),
            ("static_minus_droop", STATIC_CONTROLLER, "droop_k10"),
        )
        return

    if profile == "q0029-slew":
        smooth = "slew_mode_gate_c0p25_da0p02895"
        raw = "raw_mode_gate_c0p25"
        BANK_SEED = 20260725
        BOOTSTRAP_SEED = 2026072501
        EXPERIMENT_PROFILE = profile
        EXPERIMENT_KEY = "q0029_alpha_slew_replication"
        CONTROLLER_ORDER = (
            "static_a0p25",
            raw,
            smooth,
        )
        STATIC_CONTROLLER = "static_a0p25"
        GATE_CONTROLLER = smooth
        RAW_GATE_CONTROLLER = raw
        CONTROLLER_SPECS = {
            "static_a0p25": {
                "kind": "convex_learned_droop_blend",
                "droop_k": DROOP_K,
                "alpha": STATIC_ALPHA,
            },
            raw: {
                "kind": "common_differential_mode_ratio_gated_residual",
                "droop_k": DROOP_K,
                "alpha_cap": GATE_ALPHA_CAP,
                "ratio_full_scale": GATE_RATIO_FULL_SCALE,
            },
            smooth: {
                "kind": "alpha_slew_limited_mode_ratio_gated_residual",
                "droop_k": DROOP_K,
                "alpha_cap": GATE_ALPHA_CAP,
                "ratio_full_scale": GATE_RATIO_FULL_SCALE,
                "delta_alpha_max": 0.02895,
                "rate_source": "Kundur inter-area mode 0.579 Hz; one-period full travel",
            },
        }
        CONTRASTS = (
            ("gate_minus_static", smooth, STATIC_CONTROLLER),
            ("slew_minus_raw", smooth, raw),
            ("raw_minus_static", raw, STATIC_CONTROLLER),
        )
        return

    raise ValueError(f"unknown experiment profile: {profile}")


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json_atomic(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{path}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary artifact exists: {temporary}")
    text = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    temporary.write_text(text + "\n", encoding="utf-8")
    temporary.replace(path)


def _checkpoint_hashes(ckpt_dir: Path, suffix: str = "best") -> dict[str, str]:
    paths = [ckpt_dir / f"agent_{index}_{suffix}.pt" for index in range(4)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen actor checkpoints: {missing}")
    return {path.name: sha256_file(path) for path in paths}


def _runtime_versions() -> dict[str, str]:
    packages = {}
    for package in ("andes", "numpy", "torch"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "not-installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        **packages,
    }


def _evaluation_source_hashes() -> dict[str, str]:
    relative_paths = (
        "scripts/eval_sealed_gate_replication.py",
        "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "src/andes_rl_kundur/evaluation/hybrid.py",
        "src/andes_rl_kundur/evaluation/paper_path.py",
        "src/andes_rl_kundur/evaluation/physical_endpoints.py",
    )
    return {
        relative_path: sha256_file(ROOT / relative_path)
        for relative_path in relative_paths
    }


def _prepare_bank(path: Path) -> None:
    generator_source = (
        ROOT
        / "src"
        / "andes_rl_kundur"
        / "evaluation"
        / "paper_strict_eval.py"
    )
    payload = build_scenario_bank(
        n=BANK_N,
        seed=BANK_SEED,
        repository_head=_git_head(),
        generator_source_sha256=sha256_file(generator_source),
    )
    if EXPERIMENT_PROFILE == "q0029-slew":
        development_bank_path = ROOT / "memory" / "rounds" / "R265" / "scenario_bank.json"
        development_bank, _ = load_scenario_bank(development_bank_path)
        development_signatures = {
            (row["name"], json.dumps(row["delta_u"], sort_keys=True))
            for row in development_bank["scenarios"]
        }
        new_signatures = {
            (row["name"], json.dumps(row["delta_u"], sort_keys=True))
            for row in payload["scenarios"]
        }
        overlap = development_signatures & new_signatures
        if overlap:
            raise ValueError(f"Q-0029 bank overlaps R265 development bank: {overlap}")
    digest = write_scenario_bank(path, payload)
    print(f"[sealed bank] path={path}")
    print(f"[sealed bank] profile={EXPERIMENT_PROFILE}")
    print(f"[sealed bank] scenarios={BANK_N} seed={BANK_SEED} anchors=False")
    print(f"[sealed bank] sha256={digest}")


def _prepare_seal(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    plan_path: Path,
    ckpt_dir: Path,
    manifest_path: Path,
) -> None:
    """Freeze the bank, plan, checkpoints, controllers, and source hashes."""
    bank, bank_sha256 = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    arguments = bank["generator_arguments"]
    expected_arguments = {
        "n": BANK_N,
        "seed": BANK_SEED,
        "include_anchors": False,
    }
    if arguments != expected_arguments:
        raise ValueError(
            f"{EXPERIMENT_PROFILE} bank parameters drifted: "
            f"expected {expected_arguments}, got {arguments}"
        )
    if not plan_path.is_file():
        raise FileNotFoundError(f"round plan is missing: {plan_path}")

    payload = {
        "schema_version": 2,
        "sealed_at_local": dt.datetime.now().astimezone().isoformat(),
        "prospective_evidence": {
            "first_controller_trajectory_started": False,
            "round_plan": str(plan_path),
            "round_plan_sha256": sha256_file(plan_path),
            "limitation": (
                "Local timestamp and hashes establish repository-local ordering; "
                "they are not an independent third-party timestamp."
            ),
        },
        "bank": {
            "path": str(bank_path),
            "byte_count": bank_path.stat().st_size,
            "sha256": bank_sha256,
            "scenario_count": len(bank["scenarios"]),
            "ordered_scenarios_are_measurement_of_record": True,
        },
        "generation": {
            "function": (
                "andes_rl_kundur.evaluation.paper_strict_eval."
                "generate_test_scenarios"
            ),
            "arguments": arguments,
            "repository_head": bank["repository_head"],
            "generator_source_sha256": bank["generator_source_sha256"],
        },
        "evaluation": {
            "profile": EXPERIMENT_PROFILE,
            "environment": "andes_vsg_env_v4 paper_faithful default",
            "environment_seed": ENV_SEED,
            "steps": STEPS,
            "controllers": CONTROLLER_SPECS,
            "checkpoint_sha256": _checkpoint_hashes(ckpt_dir),
            "evaluation_source_sha256": _evaluation_source_hashes(),
            "primary_contrast": "gate_minus_static",
            "co_primary_lower_is_better": [
                "vsg_mean_iae_hz_s",
                "normalized_sync_loss_hz2",
            ],
            "bootstrap": {
                "method": "paired percentile bootstrap with shared scenario rows",
                "resamples": BOOTSTRAP_RESAMPLES,
                "seed": BOOTSTRAP_SEED,
                "confidence": 0.95,
            },
        },
    }
    _write_json_atomic(manifest_path, payload)
    print(f"[seal] manifest={manifest_path}")
    print(f"[seal] sha256={sha256_file(manifest_path)}")


def _verify_manifest_evaluation(
    manifest: dict[str, Any],
    *,
    checkpoint_hashes: dict[str, str],
    evaluation_source_hashes: dict[str, str],
) -> None:
    """Reject any drift from a prospective evaluation seal."""
    frozen = manifest.get("evaluation", {})
    if frozen.get("checkpoint_sha256") != checkpoint_hashes:
        raise ValueError("checkpoint SHA-256 differs from prospective seal manifest")
    frozen_profile = frozen.get("profile")
    if frozen_profile is not None and frozen_profile != EXPERIMENT_PROFILE:
        raise ValueError(
            f"seal profile drifted: expected {EXPERIMENT_PROFILE}, got {frozen_profile}"
        )
    frozen_controllers = frozen.get("controllers")
    if frozen_profile is not None and frozen_controllers != CONTROLLER_SPECS:
        raise ValueError("controller specs differ from prospective seal manifest")
    frozen_sources = frozen.get("evaluation_source_sha256")
    if frozen_sources is not None and frozen_sources != evaluation_source_hashes:
        raise ValueError("evaluation source SHA-256 differs from seal manifest")


def _rotated_controller_order(scenario_index: int) -> tuple[str, ...]:
    shift = scenario_index % len(CONTROLLER_ORDER)
    return CONTROLLER_ORDER[shift:] + CONTROLLER_ORDER[:shift]


def _trace_path(out_dir: Path, scenario_name: str, controller: str) -> Path:
    return out_dir / "traces" / scenario_name / f"{controller}.json"


def _expected_trace_metadata(
    *,
    bank_sha256: str,
    scenario_index: int,
    scenario: dict[str, Any],
    controller: str,
    run_order: tuple[str, ...],
    checkpoint_hashes: dict[str, str],
    evaluation_source_hashes: dict[str, str],
    seal_manifest_sha256: str,
) -> dict[str, Any]:
    return {
        "sealed_bank_sha256": bank_sha256,
        "scenario_index": scenario_index,
        "scenario_definition": scenario,
        "controller_key": controller,
        "controller_spec": CONTROLLER_SPECS[controller],
        "controller_run_order": list(run_order),
        "checkpoint_sha256": checkpoint_hashes,
        "evaluation_source_sha256": evaluation_source_hashes,
        "seal_manifest_sha256": seal_manifest_sha256,
        "env_seed": ENV_SEED,
        "requested_steps": STEPS,
    }


def _load_resumable_trace(
    path: Path,
    *,
    expected_metadata: dict[str, Any],
) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot resume malformed trace {path}") from exc
    for key, expected in expected_metadata.items():
        if record.get(key) != expected:
            raise ValueError(
                f"cannot resume {path}: metadata {key!r} drifted "
                f"(expected {expected!r}, got {record.get(key)!r})"
            )
    terminal = (
        record.get("evaluation_error") is not None
        or record.get("tds_failed") is True
        or record.get("completed") is True
    )
    if not terminal:
        raise ValueError(f"cannot resume non-terminal trace: {path}")
    return record


def _build_action_functions(
    ckpt_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    agents = load_agents(ckpt_dir, suffix="best")
    learned = deterministic_actor_action_fn(agents)
    droop = proportional_damping_action_fn(DROOP_K)
    raw_gate = mode_ratio_gated_blend_action_fn(
        learned,
        droop,
        alpha_cap=GATE_ALPHA_CAP,
        ratio_full_scale=GATE_RATIO_FULL_SCALE,
    )
    static = convex_blend_action_fn(
        learned,
        droop,
        alpha=STATIC_ALPHA,
    )

    if EXPERIMENT_PROFILE == "q0028-gate":
        return {
            "r201": learned,
            "droop_k10": droop,
            "static_a0p25": static,
            "mode_gate_c0p25": raw_gate,
        }, {"mode_gate_c0p25": raw_gate}

    smooth_gate = slew_limited_mode_ratio_gated_blend_action_fn(
        learned,
        droop,
        alpha_cap=GATE_ALPHA_CAP,
        ratio_full_scale=GATE_RATIO_FULL_SCALE,
        delta_alpha_max=0.02895,
    )
    assert RAW_GATE_CONTROLLER is not None
    return {
        STATIC_CONTROLLER: static,
        RAW_GATE_CONTROLLER: raw_gate,
        GATE_CONTROLLER: smooth_gate,
    }, {
        RAW_GATE_CONTROLLER: raw_gate,
        GATE_CONTROLLER: smooth_gate,
    }


def _run_evaluation(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    seal_manifest_path: Path,
    expected_manifest_sha256: str,
    ckpt_dir: Path,
    out_dir: Path,
    resume: bool,
) -> None:
    bank, bank_sha256 = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    arguments = bank["generator_arguments"]
    if arguments != {
        "n": BANK_N,
        "seed": BANK_SEED,
        "include_anchors": False,
    }:
        raise ValueError(f"{EXPERIMENT_PROFILE} bank parameters drifted: {arguments}")
    checkpoint_hashes = _checkpoint_hashes(ckpt_dir)
    evaluation_source_hashes = _evaluation_source_hashes()
    seal_manifest_sha256 = sha256_file(seal_manifest_path)
    if seal_manifest_sha256 != expected_manifest_sha256.lower():
        raise ValueError(
            "seal manifest SHA-256 mismatch: "
            f"expected {expected_manifest_sha256}, got {seal_manifest_sha256}"
        )
    seal_manifest = json.loads(seal_manifest_path.read_text(encoding="utf-8"))
    if seal_manifest.get("bank", {}).get("sha256") != bank_sha256:
        raise ValueError("seal manifest does not bind the evaluated bank SHA-256")
    _verify_manifest_evaluation(
        seal_manifest,
        checkpoint_hashes=checkpoint_hashes,
        evaluation_source_hashes=evaluation_source_hashes,
    )
    action_functions, telemetry_objects = _build_action_functions(ckpt_dir)

    provenance = {
        "sealed_bank_path": str(bank_path),
        "sealed_bank_sha256": bank_sha256,
        "seal_manifest_path": str(seal_manifest_path),
        "seal_manifest_sha256": seal_manifest_sha256,
        "bank_generator_source_sha256": bank["generator_source_sha256"],
        "bank_repository_head": bank["repository_head"],
        "current_repository_head": _git_head(),
        "checkpoint_dir": str(ckpt_dir),
        "checkpoint_sha256": checkpoint_hashes,
        "evaluation_source_sha256": evaluation_source_hashes,
        "controller_specs": CONTROLLER_SPECS,
        "controller_base_order": list(CONTROLLER_ORDER),
        "run_order": "cyclic rotation by zero-based scenario index",
        "env_version": "andes_vsg_env_v4 paper_faithful default",
        "env_seed": ENV_SEED,
        "steps": STEPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "runtime": _runtime_versions(),
    }
    provenance_path = out_dir / "provenance.json"
    if provenance_path.exists():
        if not resume:
            raise FileExistsError(f"use --resume for existing evaluation: {provenance_path}")
        existing = json.loads(provenance_path.read_text(encoding="utf-8"))
        if existing != provenance:
            raise ValueError("resume provenance differs from frozen evaluation contract")
    else:
        _write_json_atomic(provenance_path, provenance)

    started = time.monotonic()
    for scenario_index, scenario in enumerate(bank["scenarios"]):
        scenario_name = scenario["name"]
        run_order = _rotated_controller_order(scenario_index)
        print(
            f"[scenario {scenario_index + 1:02d}/{BANK_N}] "
            f"{scenario_name} {scenario['delta_u']} order={','.join(run_order)}"
        )
        for order_index, controller in enumerate(run_order):
            trace_path = _trace_path(out_dir, scenario_name, controller)
            metadata = _expected_trace_metadata(
                bank_sha256=bank_sha256,
                scenario_index=scenario_index,
                scenario=scenario,
                controller=controller,
                run_order=run_order,
                checkpoint_hashes=checkpoint_hashes,
                evaluation_source_hashes=evaluation_source_hashes,
                seal_manifest_sha256=seal_manifest_sha256,
            )
            if trace_path.exists():
                if not resume:
                    raise FileExistsError(f"refusing to overwrite trace: {trace_path}")
                record = _load_resumable_trace(
                    trace_path,
                    expected_metadata=metadata,
                )
                status = (
                    "error"
                    if record.get("evaluation_error")
                    else "failed"
                    if record.get("tds_failed") or not record.get("completed")
                    else "complete"
                )
                print(
                    f"  [resume {order_index + 1}/{len(run_order)}] "
                    f"{controller}: {status}"
                )
                continue

            print(
                f"  [run {order_index + 1}/{len(run_order)}] {controller}",
                flush=True,
            )
            try:
                record = run_scenario(
                    scenario_name,
                    scenario["delta_u"],
                    action_fn=action_functions[controller],
                    label=controller,
                    seed=ENV_SEED,
                    steps=STEPS,
                    extra_keys=metadata,
                )
                if record.get("completed") is True and record.get("tds_failed") is not True:
                    record["physical_endpoints"] = summarise_physical_trace(record)
                else:
                    record["physical_endpoints"] = None
                if controller in telemetry_objects:
                    record["gate_telemetry"] = telemetry_objects[controller].telemetry()
            except Exception as exc:
                record = {
                    **metadata,
                    "controller": controller,
                    "scenario": scenario_name,
                    "env_version": "v4",
                    "tds_failed": False,
                    "completed": False,
                    "n_steps": 0,
                    "traces": [],
                    "physical_endpoints": None,
                    "evaluation_error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                }
            _write_json_atomic(trace_path, record)
            if record.get("evaluation_error"):
                print(f"    -> ERROR {record['evaluation_error']}", flush=True)
            else:
                print(
                    f"    -> completed={record.get('completed')} "
                    f"n={record.get('n_steps')} "
                    f"peak={record.get('max_df_physical_hz')}",
                    flush=True,
                )

    summary = _analyse(
        bank=bank,
        bank_sha256=bank_sha256,
        out_dir=out_dir,
        checkpoint_hashes=checkpoint_hashes,
        evaluation_source_hashes=evaluation_source_hashes,
        seal_manifest_sha256=seal_manifest_sha256,
    )
    summary["wall_seconds"] = time.monotonic() - started
    summary_path = out_dir / "sealed_gate_replication_summary.json"
    _write_json_atomic(summary_path, summary)
    markdown_path = out_dir / "sealed_gate_replication_summary.md"
    _write_markdown_summary(markdown_path, summary)
    print(
        f"[sealed replication] classification="
        f"{summary['replication_gate']['classification']}"
    )
    print(f"[sealed replication] wrote {summary_path}")
    print(f"[sealed replication] wrote {markdown_path}")


def _analyse_existing(
    *,
    bank_path: Path,
    expected_bank_sha256: str,
    seal_manifest_path: Path,
    expected_manifest_sha256: str,
    ckpt_dir: Path,
    out_dir: Path,
) -> None:
    """Read-only analysis after trace production, preserving producer hashes."""
    bank, bank_sha256 = load_scenario_bank(
        bank_path,
        expected_sha256=expected_bank_sha256,
    )
    manifest_sha256 = sha256_file(seal_manifest_path)
    if manifest_sha256 != expected_manifest_sha256.lower():
        raise ValueError("seal manifest SHA-256 mismatch during read-only analysis")
    checkpoint_hashes = _checkpoint_hashes(ckpt_dir)
    seal_manifest = json.loads(seal_manifest_path.read_text(encoding="utf-8"))
    if seal_manifest.get("bank", {}).get("sha256") != bank_sha256:
        raise ValueError("seal manifest does not bind the analysed bank")
    if (
        seal_manifest.get("evaluation", {}).get("checkpoint_sha256")
        != checkpoint_hashes
    ):
        raise ValueError("checkpoint SHA-256 differs from prospective seal manifest")

    provenance_path = out_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("sealed_bank_sha256") != bank_sha256:
        raise ValueError("producer provenance bank hash mismatch")
    if provenance.get("seal_manifest_sha256") != manifest_sha256:
        raise ValueError("producer provenance manifest hash mismatch")
    if provenance.get("checkpoint_sha256") != checkpoint_hashes:
        raise ValueError("producer provenance checkpoint hash mismatch")
    producer_source_hashes = provenance.get("evaluation_source_sha256")
    if not isinstance(producer_source_hashes, dict):
        raise ValueError("producer provenance lacks evaluation source hashes")
    _verify_manifest_evaluation(
        seal_manifest,
        checkpoint_hashes=checkpoint_hashes,
        evaluation_source_hashes=producer_source_hashes,
    )

    summary = _analyse(
        bank=bank,
        bank_sha256=bank_sha256,
        out_dir=out_dir,
        checkpoint_hashes=checkpoint_hashes,
        evaluation_source_hashes=producer_source_hashes,
        seal_manifest_sha256=manifest_sha256,
    )
    summary["producer_source_sha256"] = producer_source_hashes
    summary["analysis_source_sha256"] = _evaluation_source_hashes()
    summary["analysis_repair"] = (
        "Read-only post-run representation fix: zero reference means retain "
        "absolute paired effects and mark relative percentages unavailable."
    )
    summary["wall_seconds"] = None
    summary_path = out_dir / "sealed_gate_replication_summary.json"
    _write_json_atomic(summary_path, summary)
    markdown_path = out_dir / "sealed_gate_replication_summary.md"
    _write_markdown_summary(markdown_path, summary)
    print(
        f"[sealed replication] classification="
        f"{summary['replication_gate']['classification']}"
    )
    print(f"[sealed replication] wrote {summary_path}")
    print(f"[sealed replication] wrote {markdown_path}")


def _record_endpoint_values(record: dict[str, Any]) -> dict[str, float]:
    endpoints = record.get("physical_endpoints")
    if not isinstance(endpoints, dict):
        endpoints = summarise_physical_trace(record)
    values: dict[str, float] = {}
    for endpoint in CONTINUOUS_ENDPOINTS:
        if endpoint == "legacy_normalized_sync_loss_hz2":
            steps = record["traces"]
            n_agents = len(steps[0]["freq_hz"])
            value = -compute_global_cum_rf(record) / (len(steps) * n_agents)
        else:
            value = endpoints.get(endpoint)
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"{record.get('scenario')}/{record.get('controller')}: "
                f"missing endpoint {endpoint}"
            )
        values[endpoint] = float(value)
    return values


def _analyse(
    *,
    bank: dict[str, Any],
    bank_sha256: str,
    out_dir: Path,
    checkpoint_hashes: dict[str, str],
    evaluation_source_hashes: dict[str, str],
    seal_manifest_sha256: str,
) -> dict[str, Any]:
    scenario_names = [scenario["name"] for scenario in bank["scenarios"]]
    records: dict[str, dict[str, dict[str, Any]]] = {
        controller: {} for controller in CONTROLLER_ORDER
    }
    invalid_reasons: list[str] = []
    for scenario_index, scenario in enumerate(bank["scenarios"]):
        run_order = _rotated_controller_order(scenario_index)
        for controller in CONTROLLER_ORDER:
            path = _trace_path(out_dir, scenario["name"], controller)
            if not path.is_file():
                invalid_reasons.append(f"missing trace: {path}")
                continue
            expected = _expected_trace_metadata(
                bank_sha256=bank_sha256,
                scenario_index=scenario_index,
                scenario=scenario,
                controller=controller,
                run_order=run_order,
                checkpoint_hashes=checkpoint_hashes,
                evaluation_source_hashes=evaluation_source_hashes,
                seal_manifest_sha256=seal_manifest_sha256,
            )
            try:
                record = _load_resumable_trace(path, expected_metadata=expected)
            except ValueError as exc:
                invalid_reasons.append(str(exc))
                continue
            if record.get("evaluation_error"):
                invalid_reasons.append(
                    f"{scenario['name']}/{controller}: "
                    f"{record['evaluation_error']}"
                )
            records[controller][scenario["name"]] = record

    controller_summaries: dict[str, Any] = {}
    ordered_values: dict[str, dict[str, list[float]]] = {}
    complete_controllers: set[str] = set()
    for controller in CONTROLLER_ORDER:
        controller_records = records[controller]
        failed_names: list[str] = []
        endpoint_maps: dict[str, dict[str, float]] = {
            endpoint: {} for endpoint in CONTINUOUS_ENDPOINTS
        }
        settling_names: list[str] = []
        for scenario_name in scenario_names:
            record = controller_records.get(scenario_name)
            if record is None or record.get("evaluation_error"):
                failed_names.append(scenario_name)
                continue
            complete = (
                record.get("completed") is True
                and record.get("tds_failed") is not True
                and record.get("n_steps") == STEPS
            )
            if not complete:
                failed_names.append(scenario_name)
                continue
            try:
                values = _record_endpoint_values(record)
            except ValueError as exc:
                invalid_reasons.append(str(exc))
                failed_names.append(scenario_name)
                continue
            for endpoint, value in values.items():
                endpoint_maps[endpoint][scenario_name] = value
            if record["physical_endpoints"]["settling_time_s"] is not None:
                settling_names.append(scenario_name)

        complete_count = len(scenario_names) - len(failed_names)
        endpoint_summaries: dict[str, Any] = {}
        if complete_count:
            for endpoint, values in endpoint_maps.items():
                if len(values) != complete_count:
                    invalid_reasons.append(
                        f"{controller}/{endpoint}: {len(values)} values "
                        f"for {complete_count} completed traces"
                    )
                    continue
                endpoint_summaries[endpoint] = empirical_upper_tail(values)
        controller_summaries[controller] = {
            "spec": CONTROLLER_SPECS[controller],
            "complete_count": complete_count,
            "failed_or_incomplete_scenarios": failed_names,
            "failures": binomial_rate_summary(len(failed_names), len(scenario_names)),
            "settling": {
                **binomial_rate_summary(len(settling_names), len(scenario_names)),
                "settled_scenarios": settling_names,
            },
            "endpoints": endpoint_summaries,
        }
        if complete_count == len(scenario_names):
            complete_controllers.add(controller)
            ordered_values[controller] = {
                endpoint: [
                    endpoint_maps[endpoint][scenario_name]
                    for scenario_name in scenario_names
                ]
                for endpoint in CONTINUOUS_ENDPOINTS
            }

    eligible_contrasts = [
        contrast
        for contrast in CONTRASTS
        if contrast[1] in complete_controllers and contrast[2] in complete_controllers
    ]
    if eligible_contrasts:
        bootstrap = paired_bootstrap_contrasts(
            {
                controller: ordered_values[controller]
                for controller in sorted(complete_controllers)
            },
            contrasts=eligible_contrasts,
            seed=BOOTSTRAP_SEED,
            n_resamples=BOOTSTRAP_RESAMPLES,
        )
    else:
        bootstrap = {
            "seed": BOOTSTRAP_SEED,
            "n_resamples": BOOTSTRAP_RESAMPLES,
            "confidence": 0.95,
            "shared_index_resampling": True,
            "contrasts": {},
        }
    for contrast_name, left, right in CONTRASTS:
        if contrast_name not in bootstrap["contrasts"]:
            bootstrap["contrasts"][contrast_name] = {
                "left": left,
                "right": right,
                "available": False,
                "reason": "one or both controllers had failed/incomplete scenarios; none dropped",
            }

    def is_complete(controller: str, scenario_name: str) -> bool:
        record = records[controller].get(scenario_name)
        return bool(
            record is not None
            and not record.get("evaluation_error")
            and record.get("completed") is True
            and record.get("tds_failed") is not True
            and record.get("n_steps") == STEPS
        )

    paired_completion = paired_binary_outcome_table(
        [is_complete(GATE_CONTROLLER, name) for name in scenario_names],
        [is_complete(STATIC_CONTROLLER, name) for name in scenario_names],
    )

    primary = bootstrap["contrasts"].get("gate_minus_static")
    if primary is not None and primary.get("available") is False:
        primary = None
    if invalid_reasons:
        replication_gate = {
            "classification": "INVALID",
            "reason": "evaluation/provenance errors require infrastructure repair",
            "invalid_reasons": invalid_reasons,
        }
    else:
        if EXPERIMENT_PROFILE == "q0029-slew":
            mechanism = bootstrap["contrasts"].get("slew_minus_raw")
            if mechanism is not None and mechanism.get("available") is False:
                mechanism = None
            replication_gate = classify_smoothing_replication(
                controller_summaries=controller_summaries,
                primary_contrast=primary,
                mechanism_contrast=mechanism,
                smooth_name=GATE_CONTROLLER,
                static_name=STATIC_CONTROLLER,
                total_scenarios=len(scenario_names),
            )
        else:
            replication_gate = classify_gate_replication(
                controller_summaries=controller_summaries,
                primary_contrast=primary,
                gate_name=GATE_CONTROLLER,
                static_name=STATIC_CONTROLLER,
                total_scenarios=len(scenario_names),
            )

    return {
        "experiment": EXPERIMENT_KEY,
        "profile": EXPERIMENT_PROFILE,
        "bank_sha256": bank_sha256,
        "scenario_count": len(scenario_names),
        "scenario_names": scenario_names,
        "controller_specs": CONTROLLER_SPECS,
        "checkpoint_sha256": checkpoint_hashes,
        "evaluation_source_sha256": evaluation_source_hashes,
        "seal_manifest_sha256": seal_manifest_sha256,
        "endpoint_direction": "lower_is_better",
        "tail_note": (
            "With n=20, empirical CVaR90 is the mean of only the worst two "
            "scenarios and is a descriptive guard, not strong inference."
        ),
        "controllers": controller_summaries,
        "paired_bootstrap": bootstrap,
        "gate_static_paired_completion": {
            "left": GATE_CONTROLLER,
            "right": STATIC_CONTROLLER,
            **paired_completion,
        },
        "replication_gate": replication_gate,
    }


def _write_markdown_summary(path: Path, summary: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    gate = summary["replication_gate"]
    lines = [
        f"# {summary['profile']} sealed controller summary",
        "",
        f"- Classification: **{gate['classification']}**",
        f"- Reason: {gate['reason']}",
        f"- Scenario bank SHA-256: `{summary['bank_sha256']}`",
        f"- Scenarios: {summary['scenario_count']}",
        "",
        "## Controller completion",
        "",
        "| Controller | Complete | Fail/incomplete | Settled |",
        "|---|---:|---:|---:|",
    ]
    for controller in CONTROLLER_ORDER:
        row = summary["controllers"][controller]
        lines.append(
            f"| {controller} | {row['complete_count']} | "
            f"{row['failures']['count']} | {row['settling']['count']} |"
        )
    primary = summary["paired_bootstrap"]["contrasts"]["gate_minus_static"]
    if primary.get("available") is False:
        lines.extend(["", "Primary paired bootstrap unavailable because a trace failed."])
    else:
        lines.extend(
            [
                "",
                "## Primary controller minus static alpha=0.25",
                "",
                "| Endpoint | Mean effect % | 95% paired bootstrap | P(improve) |",
                "|---|---:|---:|---:|",
            ]
        )
        for endpoint in (
            "vsg_mean_iae_hz_s",
            "normalized_sync_loss_hz2",
            "worst_bus_peak_abs_hz",
            "max_abs_rocof_hz_s",
            "action_total_variation",
        ):
            effect = primary["endpoints"][endpoint]
            relative = effect["ratio_of_means_percent"]
            interval = relative["percentile_95_interval"]
            lines.append(
                f"| {endpoint} | {relative['point']:.4f} | "
                f"[{interval[0]:.4f}, {interval[1]:.4f}] | "
                f"{effect['bootstrap_probability_left_improves']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Tail interpretation",
            "",
            summary["tail_note"],
            "",
        ]
    )
    temporary = Path(f"{path}.tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("q0028-gate", "q0029-slew"),
        default="q0028-gate",
        help="select the prospectively frozen experiment profile",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-bank")
    prepare.add_argument("--bank", type=Path, required=True)

    seal = subparsers.add_parser("prepare-seal")
    seal.add_argument("--bank", type=Path, required=True)
    seal.add_argument("--expected-bank-sha256", required=True)
    seal.add_argument("--plan", type=Path, required=True)
    seal.add_argument("--ckpt-dir", type=Path, required=True)
    seal.add_argument("--manifest", type=Path, required=True)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--bank", type=Path, required=True)
    evaluate.add_argument("--expected-bank-sha256", required=True)
    evaluate.add_argument("--seal-manifest", type=Path, required=True)
    evaluate.add_argument("--expected-manifest-sha256", required=True)
    evaluate.add_argument("--ckpt-dir", type=Path, required=True)
    evaluate.add_argument("--out-dir", type=Path, required=True)
    evaluate.add_argument("--resume", action="store_true")

    analyse = subparsers.add_parser("analyse")
    analyse.add_argument("--bank", type=Path, required=True)
    analyse.add_argument("--expected-bank-sha256", required=True)
    analyse.add_argument("--seal-manifest", type=Path, required=True)
    analyse.add_argument("--expected-manifest-sha256", required=True)
    analyse.add_argument("--ckpt-dir", type=Path, required=True)
    analyse.add_argument("--out-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _activate_profile(args.profile)
    if args.command == "prepare-bank":
        _prepare_bank(args.bank)
        return
    if args.command == "prepare-seal":
        _prepare_seal(
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            plan_path=args.plan,
            ckpt_dir=args.ckpt_dir,
            manifest_path=args.manifest,
        )
        return
    if args.command == "analyse":
        _analyse_existing(
            bank_path=args.bank,
            expected_bank_sha256=args.expected_bank_sha256,
            seal_manifest_path=args.seal_manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            ckpt_dir=args.ckpt_dir,
            out_dir=args.out_dir,
        )
        return
    _run_evaluation(
        bank_path=args.bank,
        expected_bank_sha256=args.expected_bank_sha256,
        seal_manifest_path=args.seal_manifest,
        expected_manifest_sha256=args.expected_manifest_sha256,
        ckpt_dir=args.ckpt_dir,
        out_dir=args.out_dir,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
