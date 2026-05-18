"""R89 — Regression test for F1: ANDES vs env nominal frequency consistency.

This test is **deliberately RED** to lock in the F1 finding from
`memory/rounds/R89/verdict.md` + `results/r89_kundur_audit/audit_report.md`.

Bug: ANDES default `kundur/kundur_full.xlsx` has all GENROU machines at
``fn=60.0 Hz``, but the project's `base_env.FN=50.0 Hz`
(``scenarios.contract.KUNDUR.fn=50.0``) interprets ANDES `omega_pu` via
``freq_hz = omega * self.FN``. ANDES integrates a 60 Hz system, env labels
output as 50 Hz: max_df is underreported by factor 50/60 ≈ 0.833.

This test asserts they match. **It currently fails** (50 ≠ 60). The failure
is the deliberate audit signal. A fix in R90+ should either:
  - re-export `kundur_full.xlsx` with `fn=50.0` (build a 50-Hz baseline)
  - OR override GENROU.fn=50.0 in V4 env `_build_system()` after load
  - OR adjust `base_env.FN` to 60.0 + accept paper-deviation in narrative
(the choice has paper-narrative implications, deferred to ADR-0006).

Run:
    pytest -xvs tests/test_v4_fn_consistency.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_JSON = ROOT / "results" / "r89_kundur_audit" / "summary.json"
PROBE_JSON = ROOT / "probes" / "r89_andes_kundur_full.json"


def _load_andes_fn() -> float:
    """Read GENROU.fn from cached ANDES kundur_full.json dump.

    Uses cached file to avoid needing ANDES installed on Windows. If the
    cache is missing, the test xfails with a regenerate hint (CI/WSL only).
    """
    if not PROBE_JSON.exists():
        pytest.xfail(
            f"Missing {PROBE_JSON.relative_to(ROOT)}; regenerate via:\n  "
            "wsl bash -c 'cat /home/wya/andes_venv/lib/python3.12/site-packages/"
            f"andes/cases/kundur/kundur_full.json' > {PROBE_JSON.relative_to(ROOT)}"
        )
    d = json.loads(PROBE_JSON.read_text(encoding="utf-8"))
    fns = sorted({float(g["fn"]) for g in d["GENROU"]})
    assert len(fns) == 1, f"Non-uniform GENROU fn across machines: {fns}"
    return fns[0]


def _load_env_fn() -> float:
    """Read contract.KUNDUR.fn without importing the full env (no ANDES needed)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "contract",
        ROOT / "src" / "andes_rl_kundur" / "scenarios" / "contract.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return float(mod.KUNDUR.fn)


@pytest.mark.xfail(reason="R89 F1 — known fn=60 vs FN=50 mismatch, see verdict.md",
                   strict=True)
def test_andes_fn_matches_env_fn():
    """Detect 50/60 Hz mismatch (deliberately xfail — see module docstring)."""
    andes_fn = _load_andes_fn()
    env_fn = _load_env_fn()
    assert abs(andes_fn - env_fn) < 0.1, (
        f"ANDES GENROU.fn={andes_fn} Hz ≠ env contract KUNDUR.fn={env_fn} Hz.\n"
        f"Impact: base_env.py converts omega_pu→Hz using FN={env_fn}, "
        f"but ANDES integrates at {andes_fn} Hz. Reported max_df underestimates "
        f"physical max_df by factor {env_fn/andes_fn:.3f} "
        f"({(1-env_fn/andes_fn)*100:.1f}% under-reporting)."
    )


def test_r89_audit_report_present():
    """Sanity: R89 audit ran and emitted summary.json + audit_report.md.

    Soft check that the audit deliverable is present in the repo (so the
    regression xfail above remains anchored to a real audit report).
    """
    if not AUDIT_JSON.exists():
        pytest.skip(
            f"R89 audit not run yet. Run: python scripts/r89_parameter_audit.py"
        )
    summary = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    assert summary["genrou"]["F1_fn_mismatch"] is True, (
        "Audit summary should record F1_fn_mismatch=True"
    )
    assert summary["pq"]["F5_capacitive_q"] is True
    assert summary["tgov1"]["F4_all_active"] is True
