from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r287_weak_grid_stress.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("r287_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_overrides_only_declared_execution_identity() -> None:
    adapter = _load_adapter()
    kernel = adapter._load_kernel()

    assert kernel.ROUND_ID == "R287"
    assert kernel.QUESTION == "Q-0046"
    assert kernel.PHASE == "weak-tie-stress-extension"
    assert kernel.TIE_K_LEVELS == (2.5, 3.0)
    assert kernel.SHARD_COUNT == 3
    assert kernel.HIERARCHICAL_BOOTSTRAP_SEED == 2026073001
    assert kernel.ARMS == (
        "q0",
        "centralized_s17",
        "centralized_s53",
        "centralized_s89",
    )
    assert kernel.PRIMARY_ENDPOINTS == (
        "normalized_sync_loss_hz2",
        "fast_inter_area_iae_hz_s",
    )


def test_manifest_provenance_keeps_parent_and_current_plan() -> None:
    adapter = _load_adapter()
    kernel = adapter._load_kernel()
    parent = {
        "path": "scripts/run_r286_weak_grid_td.py",
        "sha256": kernel.sha256_file(adapter.PARENT_RUNNER),
    }
    payload = {
        "sources": {
            "script": parent,
            "plan": {
                "path": "memory/rounds/R286/plan.md",
                "sha256": "old",
            },
        }
    }

    adapted = adapter._adapt_manifest(kernel, payload)

    assert payload["sources"]["plan"]["path"] == "memory/rounds/R286/plan.md"
    assert adapted["sources"]["parent_runner"] == parent
    assert adapted["sources"]["script"]["path"] == (
        "scripts/run_r287_weak_grid_stress.py"
    )
    assert adapted["sources"]["plan"]["path"] == "memory/rounds/R287/plan.md"
    assert adapted["adapter_contract"]["overrides"]["tie_k_levels"] == [
        2.5,
        3.0,
    ]
