# r29 — N4 / T2-ZIP-v2 verdict

**Date**: 2026-05-07
**Probe**: `probes/andes_kundur/t2_zip_v2_probe.py`
**Raw output**: `results/research_loop/r29_zip_v2_probe.json`
**Wall**: ~3 min
**Status**: **APPARENTLY DRAMATIC IMPROVEMENT, BUT VALIDITY SUSPECT**.
The numerical traces look like a 70-94 % residual closure (LS2 settle
9.80 → 1.80 s, final_df 0.058 → 0.004 Hz), but the most likely mechanism
is **disturbance dispatch is no longer reaching the system** once the
ZIP DynLoad takes over the PQ pair in TDS. Recommend a sanity check
before declaring the residual closed.

---

## TL;DR

> Adding ANDES ZIP DynLoad (paired with each PQ via IdxParam `pq`) at
> 50 % constant-P + 50 % constant-Z (kpp=50, kpz=50, in *percent* per
> ANDES convention) yields:
>
> | Variant         | LS1 max_df | LS1 final_df | LS2 max_df | LS2 final_df | LS2 settle (paper-target) |
> |-----------------|-----------:|-------------:|-----------:|-------------:|--------------------------:|
> | V4_baseline     | 0.1890     | 0.0621       | 0.1683     | 0.0579       | 9.80 s                    |
> | V4_ZIP_50_50    | **0.0437** | **0.0040**   | **0.0437** | **0.0040**   | **1.80 s**                |
> | V4_ZIP_100_Z    | 0.0580     | 0.0098       | 0.0580     | 0.0098       | 1.80 s                    |
>
> If this were a clean physics result it would be the dispatch's
> single-largest finding — V5 env adoption + paper Appendix B reframed
> from "irreducible residual" to "extended fidelity model closes 90 % of
> the gap". **But the LS1 and LS2 columns produce nearly bit-identical
> numbers** (max_df 0.0437 / 0.0437; final_df 0.0040 / 0.0040), and
> these numbers are roughly the *zero-disturbance noise floor* of the
> V4 system. That symmetry is a strong red flag: a real physics effect
> would not produce identical responses to two opposite-sign disturbances
> on different buses.
>
> **Most likely cause**: the disturbance dispatch in
> `env/andes/andes_vsg_env.py::_apply_disturbance` writes
> `ss.PQ.Ppf.v[k] += dp` to inject the load step, but in this configuration
> ZIP has taken over the PQ pair's TDS dynamics, and ZIP's internal `p0`
> is frozen at PFlow time. Mutating `PQ.Ppf` after PFlow no longer changes
> the actual injected power, so the system sees ~0 disturbance.
>
> **Verdict**: invalid result, do not adopt V5/ZIP env on the strength
> of these numbers. AGC + ZIP follow-up (N4) is therefore **fully closed
> without producing actionable evidence**: AGC is not in the ANDES 2.0.0
> registry at all (r25 finding) and ZIP requires a redesign of the
> disturbance path before it can be tested fairly.

---

## Probe summary table

```
LS1 (paper Fig.6: max=0.13Hz, final=0.08Hz, settling=3.0s)
  variant           max_df   final_df  settle_C2_30s  settle_C3_30s
  V4_baseline       0.1890     0.0621           6.00           7.40
  V4_ZIP_50_50      0.0437     0.0040            inf           0.00
  V4_ZIP_100_Z      0.0580     0.0098            inf           0.00

LS2 (paper Fig.8: max=0.10Hz, final=0.05Hz, settling=2.5s)
  variant           max_df   final_df  settle_C2_30s  settle_C3_30s
  V4_baseline       0.1683     0.0579           9.80           8.40
  V4_ZIP_50_50      0.0437     0.0040           1.80           0.00
  V4_ZIP_100_Z      0.0580     0.0098           1.80           0.00
```

(C2 = settling around paper-target band; C3 = settling around own-final
value with full 30 s window. C3 = 0.00 means trajectory enters the band
within the first measurement step, consistent with near-zero amplitude.)

---

## Mechanism analysis (why the numbers are suspect)

### Symptom 1 — LS1 and LS2 produce identical traces

LS1 disturbs `PQ_Bus14` by **−2.48 p.u.** (load reduction).
LS2 disturbs `PQ_Bus15` by **+1.88 p.u.** (load increase).
Two scenarios with **opposite-sign, different-magnitude, different-bus**
disturbances should produce two different frequency responses.

Under ZIP_50_50 they instead produce identical max_df = 0.0437 Hz and
identical final_df = 0.0040 Hz (to 4 decimals). Under ZIP_100_Z they
produce identical max_df = 0.0580, final_df = 0.0098. **No physics
in a power system makes these values exactly equal**. The simplest
explanation: the system sees no disturbance at all in either case; the
small residuals are PFlow / TDS init noise of the same shape regardless
of which `delta_u` was supposedly applied.

### Symptom 2 — The "zero-disturbance floor"

V4 zero-action zero-disturbance baseline (e.g. `delta_u = {"PQ_Bus14": 0.0}`)
typically produces frequency oscillations in the 0.001-0.01 Hz range
during the first second of TDS as the model settles (governor / AVR
transient response from the small algebraic mismatch in initialisation).
The 0.0040 / 0.0098 Hz final_df numbers fit this profile exactly.

### Symptom 3 — Settling at t=0.00 s under C3 (own-final)

C3 = "first time |Δf - own_final| < 0.02 Hz over 0.5 s window". Reporting
**0.00 s** means the trajectory enters the band on the first step. This
is consistent with a near-flat trace (oscillation amplitude ≪ 0.02 Hz),
which is what one would see if the disturbance never actually fired.

### Hypothesis — ANDES ZIP/PQ dispatch interaction

ANDES `ZIP` model is a `DynLoad` paired to a static `PQ` via `pq`
IdxParam. At PFlow time, `ZIP.p0` is initialised from the paired PQ's
`Ppf` × the kpp/kpi/kpz fractions. At TDS time, ZIP injects:

    P_ZIP(V) = ZIP.p0 * (kpp/100 + kpi/100 * V/V0 + kpz/100 * (V/V0)^2)

`ZIP.p0` is frozen at PFlow exit; it is **not** updated when one mutates
`ss.PQ.Ppf` later. Meanwhile, the PQ contribution at TDS time is governed
by ANDES's PQ-replaced-by-ZIP rule (PQ becomes a no-op once a ZIP is
paired against it, or contributes only the residual fraction).

Net effect: `_apply_disturbance` writes to `PQ.Ppf` but the actual TDS
injection is dominated by `ZIP.p0` which never sees the change. The
system effectively runs with no disturbance.

### What a fix would look like

The probe needs to dispatch the disturbance through the ZIP model
itself, not through PQ. Two options:

1. **Toggle a parallel ZIP** at the disturbance bus with `u=1` and a
   programmed step (use `ss.Toggle` or `ss.Fault` to flip state at
   t = 0.5 s).
2. **Re-run PFlow at every disturbance** so `ZIP.p0` re-inherits the
   updated `PQ.Ppf`. Costly (PFlow is slow) but most paper-faithful.

Either option requires `env/andes/andes_vsg_env.py::_apply_disturbance`
to be made aware of the ZIP variants. This is real env-class work
(several hours), not a probe-tier fix.

---

## Confirmation experiment (Z1) — RAN 2026-05-07, hypothesis CONFIRMED

```
Scenario              max_df          final_df       n_steps
ZERO_at_Bus14         0.043747        0.003980       150
LS1_at_Bus14          0.043747        0.003980       150     <-- 'real' LS1
ZERO_at_Bus15         0.043747        0.003980       150
LS2_at_Bus15          0.043747        0.003980       150     <-- 'real' LS2
```

**All four scenarios produce bit-identical traces to 6 decimal places**.
A disturbance of −2.48 p.u. at Bus 14, +1.88 p.u. at Bus 15, and zero
disturbance at either bus produce numerically the same frequency
trajectory in the V4_ZIP_50_50 environment. This is impossible if the
disturbance is reaching the system; therefore the disturbance is NOT
reaching the system.

**ZIP-v2 outcome is officially INVALID**. The 70-94 % "residual closure"
in §"Probe summary table" reflects the V4 + ZIP system's free response
from a quiescent steady state, not the response to the LS1 / LS2 load
steps. No paper claim should rest on these traces.

---

## Verdict

| Claim                                                                    | Evidence                                                            | Status                                       |
|---------------------------------------------------------------------------|---------------------------------------------------------------------|----------------------------------------------|
| ANDES has a real ZIP DynLoad model                                       | `from andes.models.dynload.zip import ZIP` works                    | confirmed                                    |
| ZIP can be paired with each PQ pre-setup                                 | introspect_model(ss, "ZIP") returns n=4, num_dae_vars=1, active=True | confirmed                                    |
| ZIP closes 70-94 % of the cross-platform residual                        | numbers above                                                       | **suspect — likely artifact**                |
| ZIP receives disturbance dispatch correctly via `PQ.Ppf` mutation        | identical LS1/LS2 traces, near-zero max_df                          | **rejected** (with high confidence)          |
| AGC + ZIP combined could still close residual after a disturbance-path fix | not tested                                                          | open, but blocked by AGC unavailability (r25) |
| Decision-tree (path_B_execution.md §2): "LS2 final_df drops > 50 %"      | technically yes, but reason is invalid                              | **do not pull this branch**                   |
| Decision-tree: "LS2 final_df drops < 20 %"                               | not directly tested under valid disturbance                         | open                                         |

**Net for paper**: the V4 → V5 env upgrade is **NOT** justified by these
numbers. Keep V4. Keep the Appendix B "irreducible residual" framing
until a properly-dispatched ZIP probe lands. The "ZIP load model
attempted; preliminary numbers point to disturbance-path interaction"
sentence can go in §VII-D as a study limitation, but should not drive
manuscript revisions.

---

## Next-step recommendations (priority-ordered)

| #   | Action                                                                                                                                                               | Effort | Decides                                                                                                                                |
|-----|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------------------------------------------------------------------------------------------------------------------------------------|
| Z1  | **Confirmation experiment** above — run probe with `delta_u={"PQ_Bus14": 0.0}` on V4_ZIP_50_50; expect identical trace.                                              | 5 min  | Invalidates ZIP-v2 conclusively, OR reveals an unexpected effect to investigate.                                                       |
| Z2  | Redesign `_apply_disturbance` to dispatch through Toggle / Fault for ZIP variants, then re-run probe.                                                                 | 4-6 h  | Whether ZIP load model genuinely closes the LS1/LS2 residual or not.                                                                   |
| Z3  | If Z2 outcome positive (real residual closure): write V5 env subclass (`AndesMultiVSGEnvV5(AndesMultiVSGEnvV4)` with ZIP attached + Toggle dispatch).                | 1 d    | V5 env adoption decision.                                                                                                              |
| Z4  | If Z2 outcome negative (no closure): document in r29 appendix and **close N4 as "no V5 needed"**.                                                                    | 30 min | Final closure of the AGC + ZIP follow-up line.                                                                                         |
| Z5  | **Closure on N4 line as a whole**: AGC unavailable (r25) + ZIP requires non-trivial env redesign (this verdict). No "easy fix" closes the cross-platform residual.   | —      | Paper can defensibly state "we tested two model-extension hypotheses (AGC, ZIP); neither delivered an evidenced residual closure".      |

**Recommendation**: do Z1 (5 min), then if confirmed go to Z5
(≈ 1-paragraph paper note in §VII-D). Skip Z2/Z3/Z4 unless the user
specifically wants to push residual closure for a method-paper headline.

---

## Files written

```
quality_reports/research_loop/r29_zip_v2_verdict.md   ← this
results/research_loop/r29_zip_v2_probe.json           ← raw introspections + 30s traces
probes/andes_kundur/t2_zip_v2_probe.py                ← driver (kp=50/100 percentage fix included)
```

---

## Reproducibility

```bash
# Note: Probe v1 used 0.5/0.5 fractions and triggered an ANDES initialisation
# error ("ZIP total kp and 100 should be equal"). The current driver uses
# percentage values (kpp=50, kpz=50) per ANDES convention.

wsl -e bash -c "cd '/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs' && \
    /home/wya/andes_venv/bin/python probes/andes_kundur/t2_zip_v2_probe.py"
```

Runtime ≈ 3 min wall.

---

*Generated 2026-05-07 by code-probe dispatch followup N4 / T2-ZIP-v2.
Closes the AGC + ZIP residual-closure investigation line, modulo the
recommended Z1 confirmation experiment. The disturbance-path-failure
hypothesis is the simplest and best-supported explanation for the
observed numerical outcome and should be verified before any paper
revision relies on the ZIP-v2 traces.*

---

## §X. Claim + Falsification (per O1 protocol)

### Claim

> Adding ANDES ZIP DynLoad with 50% constant-P + 50% constant-Z fractioning **appears to** drop V4 LS2 settling from 9.80 s to 1.80 s (90% gap closure to paper 2.5 s) and final_df from 0.058 Hz to 0.004 Hz, but the **bit-identical LS1 vs LS2 traces** (max_df 0.0437 / 0.0437; final_df 0.0040 / 0.0040 — 5 decimal places) are a strong signature that **disturbance dispatch is no longer reaching the system** once ZIP takes over the PQ pair in TDS. The result is therefore **invalid** — V5 / ZIP env should not be adopted on the strength of these numbers without a Z1 sanity-check showing the disturbance is actually injected.

### Falsification

| 维度 | 条件 | status |
|---|---|---|
| **F-Independence** | K independent traces for the LS1 vs LS2 comparison? | **K=1 each scenario, ONE configuration**. The bit-identical LS1 vs LS2 outcome IS the independence violation — physically independent disturbances must produce different responses; identical responses indicate the disturbance signal is the same value (zero) for both. |
| **F-Coverage** | Did the probe vary disturbance magnitude, ZIP fractioning, etc.? | 2 ZIP variants (50/50 and 100% Z); both produced LS1 = LS2. Adequate to detect the bug pattern; not adequate to characterise true ZIP behaviour. |
| **F-Counterfactual** | Compared to V4_baseline (no ZIP) under same probe? | Yes — V4_baseline produces LS1 ≠ LS2 (max_df 0.189 vs 0.168, final_df 0.062 vs 0.058) as expected. The contrast V4_baseline-distinct vs V4_ZIP-identical is the load-bearing falsification of the "ZIP closes residual" claim. |
| **F-Generalization** | Holds for other ZIP load library choices (vs PQ.config, vs ANDES ZIP DynLoad model)? | r25 already showed `PQ.config.{p2p}` is no-op. r29 tested ANDES ZIP DynLoad. Both fail to test the actual physics question — both are **methodology failures, not negative results on the physics**. |
| **F-Robustness** | Numerical reproducibility of the bit-identical LS1=LS2 finding? | ANDES TDS deterministic; result reproducible. The 5-decimal identity is a structural artifact, not numerical noise. **Robust diagnosis of the bug.** |

### Killshot

> If the "bit-identical LS1=LS2" interpretation is wrong (i.e., the system actually responds to both disturbances with this small magnitude because ZIP truly damps everything), then ZIP closes 90% of the residual and V5 should be adopted. **Required to rule this out**: Z1 sanity-check — run V4_ZIP_50_50 with disturbance magnitudes 0×, 1×, 2× the calibrated values; if the response scales linearly with magnitude, the disturbance is reaching the system and ZIP really does damp it; if response is constant (independent of magnitude), the disturbance bypass hypothesis is confirmed and the result is invalid. **Without Z1, the verdict status remains "invalid result, do not adopt V5".**

### Independent verification path

- [ ] **Z1 disturbance-magnitude sanity check** (highest priority): run V4_ZIP_50_50 at disturbance magnitudes ∈ {0×, 0.5×, 1×, 2×} calibrated values. Linear scaling → ZIP works. Constant response → disturbance bypass.
- [ ] Inspect `_apply_disturbance` path with `print(ss.PQ.Ppf.v)` before and after disturbance application — confirm the mutation actually affects the PQ component used by the ZIP-replaced load.
- [ ] If disturbance bypass confirmed: redirect dispatch to write `ss.ZIP.kpp.v[k]` or analogous parameter; retry probe.
- [ ] If disturbance bypass refuted: V5 / ZIP env adoption pathway is real, advance to V5 paper-faithful retrain plan.


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
