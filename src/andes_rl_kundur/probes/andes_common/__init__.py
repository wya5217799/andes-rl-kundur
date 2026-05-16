"""ANDES-specific probe utilities, shared across r0X scripts and probes/kundur/agent_state/.

Sibling to `probes/kundur/probe_state` (Simulink CVS) — this layer is for ANDES
DAE-level introspection that doesn't require a trained ckpt or a Simulink
runtime.

Public API:

    # Introspection (R10 governor forensic)
    from probes.andes_common import (
        introspect_model,         # list .v vars on an ANDES model
        try_read_v,               # tolerant first-match attr reader
        safe_get,                 # None-on-failure attr fetch
    )

    # Trace runners (R11/R13/R14/R15/R16/R17/R20 patterns)
    from probes.andes_common import (
        run_zero_action_trace,    # 1 episode zero-action, max_df / final_df
        run_trained_policy_trace, # 1 episode with trained SAC actors
        run_h_scan,               # zero-action across H grid
        run_variant_ablation,     # same scenario, different env patches
        compute_settling_time,    # paper-faithful settling around final_df
    )

    # Probe classification ladder (R45 C4 rename from "verdict" to disambiguate
    # from memory/rounds/RNN/verdict.md round ledger entity)
    from probes.andes_common import (
        ProbeClassification, ClassificationRule, resolve_probe_ladder,
        governor_wiring_ladder,   # R10 standard ladder
        root3_residual_ladder,    # R14/R15/R16 standard ladder
    )

    # Paper constants
    from probes.andes_common import (
        LS1_DELTA_U, LS2_DELTA_U, SCENARIOS,
        PAPER_FIG6, PAPER_FIG8, PAPER_BENCHMARKS,
        EQ12_DH_RANGE, EQ12_DD_RANGE,
        H_PAPER_AREA1, H_PAPER_AREA2, H_EQ12_BOX_MIDDLE, H_EQ12_BOX_UPPER,
    )

See ``probes/andes_common/README.md`` for the decision tree
"何时写新 probe / 用哪个 helper / 怎么命名".
"""
from __future__ import annotations

from andes_rl_kundur.probes.andes_common.paper_constants import (
    DEFAULT_PROBE_SEED,
    DEFAULT_PROBE_STEPS_LONG,
    DEFAULT_PROBE_STEPS_SHORT,
    EQ12_DD_RANGE,
    EQ12_DH_RANGE,
    H_EQ12_BOX_MIDDLE,
    H_EQ12_BOX_UPPER,
    H_PAPER_AREA1,
    H_PAPER_AREA2,
    H_TEST_POINTS,
    KUNDUR_AREA1_H,
    KUNDUR_AREA2_H,
    KUNDUR_GENROU_M_SYS_BASE,
    LS1_DELTA_U,
    LS1_NAME,
    LS2_DELTA_U,
    LS2_NAME,
    PAPER_BENCHMARKS,
    PAPER_DT,
    PAPER_FIG6,
    PAPER_FIG8,
    PAPER_T_EPISODE,
    LSFigureBenchmark,
    SCENARIOS,
)
from andes_rl_kundur.probes.andes_common.tracers import (
    compute_settling_time,
    run_h_scan,
    run_trained_policy_trace,
    run_variant_ablation,
    run_zero_action_trace,
)
from andes_rl_kundur.probes.andes_common.utils import (
    introspect_model,
    safe_get,
    try_read_v,
)
from andes_rl_kundur.probes.andes_common.probe_classifier import (
    ClassificationRule,
    ProbeClassification,
    governor_wiring_ladder,
    resolve_probe_ladder,
    root3_residual_ladder,
)

__all__ = [
    # utils
    "introspect_model", "safe_get", "try_read_v",
    # tracers
    "run_zero_action_trace", "run_trained_policy_trace",
    "run_h_scan", "run_variant_ablation",
    "compute_settling_time",
    # probe classification (renamed from "verdict" in R45 C4)
    "ProbeClassification", "ClassificationRule", "resolve_probe_ladder",
    "governor_wiring_ladder", "root3_residual_ladder",
    # paper constants
    "LS1_DELTA_U", "LS2_DELTA_U", "LS1_NAME", "LS2_NAME", "SCENARIOS",
    "LSFigureBenchmark", "PAPER_FIG6", "PAPER_FIG8", "PAPER_BENCHMARKS",
    "EQ12_DH_RANGE", "EQ12_DD_RANGE",
    "KUNDUR_AREA1_H", "KUNDUR_AREA2_H", "KUNDUR_GENROU_M_SYS_BASE",
    "DEFAULT_PROBE_STEPS_SHORT", "DEFAULT_PROBE_STEPS_LONG",
    "DEFAULT_PROBE_SEED", "PAPER_DT", "PAPER_T_EPISODE",
    "H_TEST_POINTS", "H_PAPER_AREA1", "H_PAPER_AREA2",
    "H_EQ12_BOX_MIDDLE", "H_EQ12_BOX_UPPER",
]
