from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r292_formal_v3.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_r292_formal_v3", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_formal_v3_preserves_matrix_statistics_and_uses_v3_screen() -> None:
    module = _load_script()

    assert module.FORMAL.ARMS == (
        "q0",
        "central_vector_s101",
        "central_vector_s137",
        "central_vector_s173",
        "distributed_edge_s101",
        "distributed_edge_s137",
        "distributed_edge_s173",
    )
    assert module.FORMAL.BOOTSTRAP_RESAMPLES == 20_000
    assert module.FORMAL.BOOTSTRAP_SEED == 2026073102
    assert module.FORMAL.SHARD_COUNT == 3
    assert module.FORMAL.SCREEN_SUMMARY == (
        ROOT / "results/r292_fresh_bank_v3/screen_summary.json"
    )
    assert module.FORMAL.DEFAULT_OUT == ROOT / "results/r292_formal_evaluation_v3"
    sources = module._source_paths()
    assert sources["execution_amendment_v3"].name == (
        "execution_amendment_20260731_v3.json"
    )
    assert sources["formal_v3_adapter"] == SCRIPT
    assert sources["recovery_v3_launcher"].name == (
        "run_r292_recovery_v3_unattended.sh"
    )
