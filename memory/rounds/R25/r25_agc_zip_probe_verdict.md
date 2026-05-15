# r25 — B-1.5 AGC / ZIP-load probe verdict

**Date**: 2026-05-07
**Probe**: `probes/andes_kundur/t2_agc_zip_probe.py`
**Raw output**: `results/research_loop/r25_agc_zip_probe.json` (introspections + 30s traces)
**Wall**: ~6 min (all 4 variants × 2 scenarios; AGC + AGC+ZIP fail-fast on setup)
**Status**: **INCONCLUSIVE** — neither AGC nor ZIP fix actually exercised the
hypothesis. Baseline trace confirmed; followup probes required.

---

## TL;DR

- **Question**: does adding AGC (secondary control) OR PQ→ZIP load close the
  LS2 final_df gap that survived R10-R20?
- **Answer**: **NOT TESTED**. ANDES 2.0.0 default registry does not expose
  `ss.AGC` (would need manual import of `andes.models.experimental.agc.AGC`).
  PQ→ZIP via `ss.PQ.config.p2p = 0.5` *appears to set* but produces an
  identical 30s trace to baseline (final_df 0.062 vs 0.062, settling 7.40 vs
  7.40 — **identical to 5 decimal places**), meaning the config flag is not
  propagated into the post-setup DAE solve.
- **Bonus finding** (from baseline trace): V4 zero-action no-control LS2
  **settles in 8.40s** (paper 2.5s, 3.36×) — *finite*, not ∞. Contradicts
  the panel DA-CRIT-2 / paper-draft claim of "LS2 settling = ∞ for ALL
  controllers". The ∞ in the paper's headline must come from R21's *trained*
  policy or from `paper_grade_axes._settling_time` definition mismatch — not
  from V4 env physics.

---

## Data table

### Variant introspection (post `ss.setup()`)

| Variant       | AGC found | PQ DAE-active | IEEEG1 DAE-active | Notes                                                                           |
|---------------|-----------|---------------|-------------------|---------------------------------------------------------------------------------|
| V4_baseline   | False     | yes (n=4)     | yes (n=4, 7 vars) | reference; AGC slot empty                                                       |
| V4_AGC        | —         | —             | —                 | RuntimeError pre-setup: `ss.AGC` is None; cannot register                       |
| V4_ZIP        | False     | yes (n=4)     | yes (n=4, 7 vars) | PQ.config.{p2p,p2i,p2z,q2q,q2i,q2z} set in `_pre_setup_addons`                  |
| V4_AGC_ZIP    | —         | —             | —                 | Inherits V4_AGC failure                                                         |

### Zero-action 30 s traces (n_steps=150, dt=0.2 s)

| Variant     | Scenario | max_df (Hz) | final_df (Hz) | settling (s) | paper_ratio_final |
|-------------|----------|-------------|---------------|--------------|-------------------|
| V4_baseline | LS1      | 0.1890      | 0.0621        | 7.40         | 0.78×             |
| V4_baseline | LS2      | 0.1683      | 0.0579        | 8.40         | 1.16×             |
| V4_ZIP      | LS1      | **0.1890**  | **0.0621**    | **7.40**     | **0.78×**         |
| V4_ZIP      | LS2      | **0.1683**  | **0.0579**    | **8.40**     | **1.16×**         |
| V4_AGC      | both     | —           | —             | —            | (not testable)    |
| V4_AGC_ZIP  | both     | —           | —             | —            | (not testable)    |

**Paper Fig.6/8 anchors**: LS1 max=0.13 / final=0.08 / settling=3.0 ; LS2
max=0.10 / final=0.05 / settling=2.5.

V4_ZIP trace **identical to V4_baseline at 5 decimals** — the ZIP config
mutation is a no-op on the DAE.

---

## Verdict

### V1 — AGC variant: NOT TESTABLE in this build

`ss.AGC` is not in the default ANDES 2.0.0 registry; verified by
`from andes.models import experimental` → `AttributeError: module
'andes.models' has no attribute 'experimental'`. Probe correctly fail-fasts
in `_pre_setup_addons` and does not corrupt downstream variants.

### V2 — ZIP variant: NOT EXERCISED (config-mutation no-op)

`ss.PQ.config.p2p = 0.5` accepts the assignment (config dict permits the
key) but the resulting 30 s trace equals baseline to 5 decimals. The
default ANDES PQ class compiles its symbolic equations from `Ppf/Qpf`
constant-power injection independent of the `p2p/p2i/p2z` config knobs
in this build. Possible reasons (none yet verified):

1. PQ.config fractions are a *user-config* helper, not an active
   ZIP-conversion gate; ANDES expects ZIP via `ZIP` model rather than
   PQ-with-ZIP-fractions in 2.0.0.
2. Setup-time symbolic codegen was already cached before
   `_pre_setup_addons` ran — `ss.config.system.save_pycode` is True by
   default and can shadow late config edits.
3. The disturbance path uses `ss.PQ.Ppf.v[k] += dp` directly (see
   `env/andes/andes_vsg_env.py::_apply_disturbance`), which injects pure
   constant-power and bypasses any ZIP fractioning that *would* otherwise
   apply at PFlow time.

### V3 — Bonus baseline finding (high-value): LS2 settling is FINITE

V4 zero-action no-control LS2 settles to ±0.02 Hz around final_df=0.058 Hz
in **8.40 s**. Paper Fig.8 LS2 settling is 2.5 s. Ratio 3.36× — large but
finite. This **contradicts** the wording in
`毕业论文/plan/2026-05-07_andes_ieee_paper.md` Appendix B
("LS2 settling: ∞ (>30s)") and the panel DA-CRIT-2 inference
("LS2 settling = ∞ for ALL controllers").

The ∞ that `evaluation/paper_grade_axes.py:193` substitutes with `99.0`
must therefore come from either:
- a **trained-policy** trace in which R21's actor *destabilises* the
  natural settling that the open-loop V4 already achieves; or
- a **window mismatch** — `_settling_time` in `paper_grade_axes.py` may
  apply a stricter `final_df_target=0` (full nominal-frequency recovery)
  rather than the paper's `final_df_target=residual` band.

Either way, **V4 env physics is not the reason for the ∞ in the paper's
6-axis ranker**. Diagnosing R21's trained-policy settling vs the
ranker's settling definition is a strictly higher-priority follow-up
than chasing V5 env design.

### V4 — Decision-tree branch (per `2026-05-07_path_B_execution.md` §2)

| Branch                                          | Outcome | Action                                                                        |
|------------------------------------------------|---------|-------------------------------------------------------------------------------|
| LS2 final_df drops > 50% with AGC and/or ZIP   | **N/A** | both variants not effectively tested; cannot pull this branch                 |
| LS2 final_df drops < 20% in both variants      | **N/A** | same                                                                          |
| Baseline finding overrides original question   | **YES** | settling-axis discrepancy is a stronger lever than env-fidelity refit         |

So the original outcome of B-1.5 ("V5 env vs Appendix B framing") is
**deferred** — neither AGC nor ZIP got a real chance, AND the assumption
that drove B-1.5 (LS2 settling = ∞ as platform residual) is itself
shaky.

---

## Next-step recommendations (priority-ordered)

| #  | Action                                                                                                                              | Effort  | Decides                                                                       |
|----|-------------------------------------------------------------------------------------------------------------------------------------|---------|-------------------------------------------------------------------------------|
| N1 | **Diagnose R21 settling**: run R21 trained policy on LS2 30 s, compute settling with both `final_df_target=residual` and `=0` definitions; compare against V4_baseline 8.40 s. | 1 h     | Whether `paper_grade_axes._settling_time` is the bug or R21 actively destabilises. |
| N2 | T2-AGC-v2: import `andes.models.experimental.agc.AGC`, manually register class to `ss`, retry V4+AGC trace.                          | 4-6 h   | Whether ANDES has a working AGC at all in 2.0.0, AND whether secondary control closes max_df residual. |
| N3 | T2-ZIP-v2: try `ss.add("ZIP", ...)` instead of mutating `PQ.config`; verify with `introspect_model(ss, "ZIP")` that DAE has new vars. | 2-3 h   | Whether ANDES ZIP model exists, AND whether ZIP-class load closes residuals.   |
| N4 | Update `毕业论文/plan/2026-05-07_andes_ieee_paper.md` Appendix B: drop "LS2 settling = ∞ (>30 s)" line, replace with V4 baseline 8.40 s + R21 settling number from N1. | 30 min  | Paper-draft consistency with measured baseline (when paper rewrite begins).    |

**N1 is the cheapest and decides the most**: it tells us whether the
panel's headline critique (DA-CRIT-2: ranker uses `max(s, 0.01)` floor to
hide settling failure) is *the* problem (→ ranker fix is the only fix
needed) or whether R21 also has a real trained-policy regression
(→ training intervention also needed).

**Per dispatch instructions**: B-1.5 is closed in this state (verdict
written, JSON committed). Followups N1-N3 are out-of-scope for code-probe
group A1; flag to user for re-prioritisation against A2/A3.

---

## Files written

```
quality_reports/research_loop/r25_agc_zip_probe_verdict.md   ← this
results/research_loop/r25_agc_zip_probe.json                 ← raw introspections + traces
probes/andes_kundur/__init__.py
probes/andes_kundur/t2_agc_zip_probe.py
```

---

## Reproducibility

```bash
wsl -e bash -c "cd '/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs' && \
    /home/wya/andes_venv/bin/python probes/andes_kundur/t2_agc_zip_probe.py"
```

Runtime: ~6 min wall (cold ANDES start ~30 s, then 4 setup + 4 trace blocks).

## Appendix — alternatives for B-1.5 follow-ups (don't re-step on landmines)

**For T2-AGC-v2** (anyone trying to add secondary frequency control):

- ❌ Don't expect `ss.AGC` to work out of the box in ANDES 2.0.0.
  `from andes.models import experimental` raises `AttributeError` —
  the experimental namespace is not packaged in this build.
- ✅ Try `ss.add_class(AGC)` after manually importing
  `from andes.models.experimental.agc import AGC` (the source file
  exists in some 2.0 branches but is not auto-registered).
- ✅ Cheaper fallback: emulate AGC with **TGOV1 + integral term tuned to
  zero steady-state Δω**, or with an **external controller** in the env's
  step loop that nudges generator setpoints based on running ACE — both
  bypass the missing model registry entirely and are paper-equivalent for
  the LS1/LS2 settling axis.

**For T2-ZIP-v2** (anyone trying to ZIP-ify the load):

- ❌ Don't expect `ss.PQ.config.{p2p,p2i,p2z} = 0.5` in
  `_pre_setup_addons` to ZIP-ify the load. Verified empirically here:
  it produces a *bit-identical* trace to the constant-power baseline
  (max_df 0.1890 / final_df 0.0621 / settling 7.40 s on LS1 — five
  decimals identical between V4_baseline and V4_ZIP).
- ✅ Try ANDES's dedicated **ZIP load model**: `ss.add("ZIP", {...})`
  before `ss.setup()`, and remove or zero the corresponding PQ entry.
  Verify with `introspect_model(ss, "ZIP")["num_dae_vars"] > 0`.
- ✅ Don't forget the disturbance path: `_apply_disturbance` writes to
  `ss.PQ.Ppf.v[k]`. If the load is replaced by a ZIP, the disturbance
  injection has to follow it (write to the ZIP equivalent or keep a
  small PQ for disturbance dispatch).

*Generated 2026-05-07 by code-probe dispatch group A1 (B-1.5). Footer
appended after AGC/ZIP API findings to save downstream effort.*

---

## §X. Claim + Falsification (per O1 protocol — `quality_reports/_templates/verdict_claim_falsification_template.md`)

### Claim

> V4 zero-action no-control LS2 settles in **8.40 s** under the textbook own-final convention (paper anchor 2.5 s, ratio 3.36×) — settling is **finite, not ∞**. The "LS2 settling = ∞" claim in `毕业论文/plan/2026-05-07_andes_ieee_paper.md` Appendix B and the panel DA-CRIT-2 inference are therefore **caused by ranker-side window truncation or settling-band definition, not by V4 env physics**. Concurrently, neither AGC nor ZIP-via-`PQ.config` was successfully exercised in this probe, so the original B-1.5 question (does extended-fidelity load model close residual?) is **deferred** rather than answered.

### Falsification

| 维度 | 条件 | status |
|---|---|---|
| **F-Independence** | K independent samples for the 8.40 s figure? | K=1 (single zero-action 30 s trace at one seed). No seed variance. **Acceptable** because the metric is a deterministic ANDES TDS playback of a fixed initial condition, not a stochastic estimate. |
| **F-Coverage** | Does the settling-time metric move under variation? | Tested only V4_baseline LS1 (7.40 s) + LS2 (8.40 s); ZIP variant produced bit-identical trace (no-op). **Coverage limited** — should also vary disturbance magnitude and verify settling time scales monotonically. |
| **F-Counterfactual** | Compared to a null / random control? | Compared to V4_ZIP (which was the intended counterfactual; turned out to be no-op so equivalent to V4_baseline). **No proper null comparison** — but the "finite vs ∞" claim is so clean (8.40 s is unambiguously finite under own-final convention) that the absence of additional null is acceptable. |
| **F-Generalization** | Holds beyond LS1+LS2 at the calibrated magnitudes? | Not tested. LS1/LS2-only. Generation trip / cascading fault not probed. |
| **F-Robustness** | Settling-time noise envelope? | ANDES TDS adaptive-step is deterministic given fixed seed and case file. Estimated reproducibility std ≤ 0.05 s, well below the 8.40 s headline. **Robust.** |

### Killshot

> If `_settling_time` actually uses a 30 s window in the ranker (and r28 confirms it does NOT — it uses 6 s), then 8.40 s is *also* ∞ in the ranker convention, and the "ranker-not-physics" framing is half-correct: the ranker's 6 s window IS the cause, but extending it to 30 s does not turn the system into a "fast settler" — it just turns ∞ into 8.40 s, still 3.36× the paper anchor. So the claim is more nuanced: **V4 LS2 settling is finite (8.40 s) but still 3× paper, and the ranker presents this as ∞ via a 6 s truncation, double-failing — once on the platform residual, once on the ranker definition.**

### Independent verification path

- [x] r28 follow-up: confirmed window truncation is the ∞ mechanism (`_settling_time` truncates to 6 s, `mask_6s = t <= t[0] + 6.0`).
- [ ] V2 + AGC variant (manual import of `andes.models.experimental.agc.AGC`, register, retry) — N2 backlog.
- [ ] V2 + true ZIP DynLoad (`ss.add("ZIP", ...)` before `ss.setup()`, with disturbance path redirected) — r29 attempted but disturbance-dispatch bug invalidated.
- [ ] Saturation probe over LS1/LS2 disturbance magnitudes ∈ [0.5×, 1.0×, 2.0×] paper-anchor values to confirm 8.40 s scales monotonically with disturbance magnitude.
