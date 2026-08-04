from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "probes/r302_vector_eval_training_gate.py"
SPEC = importlib.util.spec_from_file_location("r302_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r302 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r302)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
        encoding="ascii",
    )


def test_training_gate_blocks_when_fixed_classical_exhausts_observed_headroom(
    tmp_path: Path,
) -> None:
    eval_path = tmp_path / "eval.json"
    r292_path = tmp_path / "r292.json"
    r299_path = tmp_path / "r299.json"
    r300_path = tmp_path / "r300.json"
    r301_path = tmp_path / "r301.json"
    _write_json(
        eval_path,
        {
            "contract": {"execution_profile": "vector_power"},
            "source": {"trace_count": 36},
            "validity": {
                "diagnostic_pass": True,
                "input_integrity": {
                    "sidecar_sha256": {"verified_count": 36},
                },
                "execution_contract": {"violation_count": 0},
            },
            "evidence_status": {"status": "EXTERNAL_AUTHORITY_REQUIRED"},
        },
    )
    _write_json(
        r292_path,
        {
            "decision": {
                "classification": "INVALID",
                "validity_guards": {"relative_no_harm_all_candidate_arms": False},
            },
            "relative_guards_vs_q0": {
                f"distributed_edge_s{seed}": {"pass": False}
                for seed in (101, 137, 173)
            },
        },
    )
    _write_json(
        r299_path,
        {
            "classification": "CLASSICAL-RETUNE",
            "analysis": {
                "oracle_over_best_fixed": {
                    "fast_inter_area_iae_hz_s": 0.99996,
                    "normalized_sync_loss_hz2": 1.00093,
                },
                "local_information_signal": {"pooled_spearman": 0.35},
            },
        },
    )
    _write_json(r300_path, {"classification": "VALID-2KV-PASS"})
    _write_json(
        r301_path,
        {
            "classification": "2KV-SUFFICIENT-NO-BLIND-ESCALATION",
            "next_action": {"nonlinear_higher_gain_probe_authorized": False},
        },
    )

    summary = r302.build_summary(
        eval_path=eval_path,
        r292_path=r292_path,
        r299_path=r299_path,
        r300_path=r300_path,
        r301_path=r301_path,
    )

    assert summary["classification"] == "EVAL-READY-TRAINING-BLOCKED"
    assert summary["evaluator_gate"]["passed"] is True
    assert summary["training_gate"]["authorized"] is False
    assert summary["training_gate"]["adaptive_headroom_identified"] is False
    assert summary["training_gate"]["prior_distributed_no_harm_seed_count"] == 0
    assert summary["training_gate"]["prospective_prerequisites"] == {
        "reproducible_2kv_failure_axis": False,
        "local_information_necessity_demonstrated": False,
        "matched_classical_comparator_frozen": True,
        "neural_action_authority_frozen": False,
        "pretraining_kill_probe_passed": False,
    }
    assert summary["next_probe"]["train_neural_agent"] is False

    _write_json(
        r299_path,
        {
            "classification": "CLASSICAL-RETUNE",
            "analysis": {
                "oracle_over_best_fixed": {
                    "fast_inter_area_iae_hz_s": 0.98,
                    "normalized_sync_loss_hz2": 0.98,
                },
                "local_information_signal": {"pooled_spearman": 0.8},
            },
        },
    )
    partial = r302.build_summary(
        eval_path=eval_path,
        r292_path=r292_path,
        r299_path=r299_path,
        r300_path=r300_path,
        r301_path=r301_path,
    )
    assert partial["training_gate"]["adaptive_headroom_identified"] is True
    assert partial["training_gate"]["local_information_association_pass"] is True
    assert partial["training_gate"]["authorized"] is False
    assert partial["classification"] == "EVAL-READY-TRAINING-BLOCKED"
