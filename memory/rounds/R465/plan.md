---
round: R465
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R465 plan — U5 complete Object-B total M/D sensitivity

**Opened**: 2026-08-21
**Driver**: Replace R449's explicitly A-only attribution with a fixed-coordinate, full-model total derivative that reinitializes the DAE at every registered log-M/log-D point and independently checks the resulting transfer and energy derivatives.
**Parent**: CLM-1400/R449 partial A-channel audit; CLM-1435/R459 complete Object B export; external U5 identity and data request are acceptance inputs, not numerical evidence.

## TL;DR

Run thirteen unique Object B model jobs at `rho=0` and paired `rho=±0.04,±0.02,±0.01` for each of `logM` and `logD`, export every equilibrium/DAE/continuous/sampled matrix, then compute total sampled-model, controller/headroom, full 0--Nyquist closed-loop transfer, finite-band energy, and 30-step energy derivatives. Use a common physical gauge complement, ZOH Frechet derivatives, two Richardson levels, and direct transfer reconstruction so no A-only component is promoted to a causal conclusion.

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Classification and frozen object

- Work class: **evidence**; create-only root `results/research_loop/r465_u5_total_sensitivity`.
- Object B only: R459/R447 four-VSG energy-port local model, 60-Hz physical-frequency output, four normalized active-power commands mapped by the R272 upper-headroom vector, and three active-PQ disturbance ports. Object A, direct-M/D MARL, R452 schedules, and nonlinear performance ratios are not pooled.
- Parameters are physical counterfactuals `M_i(rho)=200 exp(rho)` and `D_i(rho)=100 exp(rho)` for all four VSGs, one family at a time. Other configuration, case, seed, control coefficients, headroom contract, finite-difference input bridge, sample period `Ts=0.2 s`, and active device set remain fixed.
- Grid is frozen before execution: `rho in {0, ±0.04, ±0.02, ±0.01}`. Each point is independently reset/initialized and exports state/algebraic values, residuals, discrete flags, DAE Jacobians, descriptor reduction, continuous and sampled `A/B/C/D`, controller/headroom arrays, names, hashes, and runtime.

### Coordinates, gauge, and derivatives

- Derivatives use one nominal orthonormal complement of the physically labelled uniform-angle gauge. Every perturbed realization must have gauge-output norm, complement leakage, and transfer mismatch within `1e-9`; the same complement prevents a rho-dependent similarity basis from contaminating matrix derivatives.
- For every array `F`, form centered differences `D_h`, `D_h/2`, `D_h/4`; form Richardson estimates `R_h=(4D_h/2-D_h)/3` and `R_h/2=(4D_h/4-D_h/2)/3`. The registered total derivative is `R_h/2`.
- Convergence passes when `||R_h/2-R_h||/max(||R_h/2||,1e-12) <= 0.01`; near-zero arrays instead use maximum absolute discrepancy `<=1e-9`. A nonconvergent component is retained and explicitly labelled conditioning failure, never silently dropped.
- Construct the block continuous ZOH matrix `M=Ts[[A_c,B_c],[0,0]]`; compare `expm_frechet(M,M_rho)` against the registered direct sampled `A/B` derivative. Relative discrepancy must be `<=1e-5` or absolute discrepancy `<=1e-9` for near-zero components.

### Full loop and energy chain

- Frequency grid contains 1025 points covering the zero-frequency limit through the 2.5-Hz Nyquist frequency. Because the local-PI controller itself has a pole at exact DC, the first evaluation point is frozen at `1e-8 Hz` and explicitly labelled as the DC-limit proxy; the plant is gauge-reduced. Export `Pc,Pw,K,L,S,G` plus each total rho derivative and both condition numbers `cond(zI-A)` and `cond(I+PcK)`.
- Both conditioning arrays must be finite and have maximum `<=1e12`; otherwise the affected parameter is `TOTAL-DERIVATIVE-INVALID` rather than numerically extrapolated.
- Controllers are the frozen exact full-feedthrough K=3.5 differential ring bandpass candidate and local PI reference. Controller and headroom arrays are rebuilt at every point; their derivatives are included even if verified as numerical zero.
- Negative feedback uses `u=-K y`, `L=PcK`, `S=(I+L)^-1`, `G=S Pw`, and
  `G_rho=S[Pw_rho-(Pc_rho K+Pc K_rho)G]`.
- Export differential-output energy over 0.3--0.5 Hz and a 30-step impulse bank for both controllers, their total derivatives, and `d log(E_candidate/E_reference)/d rho`, including the reference denominator derivative.
- Direct centered differences of the completely rebuilt `G`, band energy, finite-window energy, and log ratio at all three step levels must agree with the registered derivative under the same 1% relative/`1e-9` absolute rule.
- No gain/phase margin is computed because U5 is a sensitivity audit, not a delay or robustness round.

### Theory intake

- **Algebraic identity to verify numerically**: the total derivative contains equilibrium/DAE reduction, all sampled `A/B/C/D` channels, controller/headroom, return difference, and candidate/reference denominator terms; compare formula, Frechet ZOH, and complete direct rebuilds.
- **Mechanism prediction P1**: R449's A-only split is not sufficient to identify the dominant physical cause. Observable: compare total log-ratio derivative with the A-only value and export the non-A residual; `supported` means a material discrepancy above 1% of the total or a classification change, `refuted` means agreement within 1%, and `undecidable` means derivative/conditioning/mode gates fail.
- **Mechanism prediction P2**: fixed-mode local total derivatives are identifiable. Observables: equal active-mode hashes, equilibrium residuals `<=1e-4`, stable gauge complement, Richardson convergence, Frechet agreement, and direct full-loop agreement. Any mode change yields `MODE-SPECIFIC-NOT-TOTAL`; numerical failure yields `TOTAL-DERIVATIVE-INVALID`.
- No coordinate-dependent A/B/C/D component is called a physical invariant or unique cause.

### Capacity and formal launch contract

- Thirteen unique point jobs run concurrently with one orchestrator, one native numerical-library thread per process, and no duplicate scientific job. This uses 14 WSL Python processes within the measured 17-process host ceiling; R460 measured a stable 15-worker rung with 50.96% greater throughput than eight workers and >20% projected WSL memory headroom.
- GPU is not selected: ANDES initialization and dense matrices near 102 states are CPU/DAE work, and no measured GPU path exists.
- `capacity_evidence`: `memory/rounds/R465/capacity_evidence.json`; `host_process_budget=17`; `other_reserved_processes=0`.
- `formal_entry`: `scripts/run_r465_u5_total_sensitivity.py` via `scripts/andes_scratch.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r465_u5_total_sensitivity.py rehearse`.
- `rehearsal_scope`: nominal plus one `logD,+0.01` representative point, source/parent/case/runtime checks, output absence, common-gauge compatibility, schema, and a reduced direct/Frechet computation; no formal attempt or result root.
- `rehearsal_checks`: source and parent hashes, installed ANDES/case, initialized residuals, shape/name/mode equality, finite arrays, one-thread environment, no live competing research process, and formal output absence.
- `wsl_python_processes=14`; `native_threads_per_process=1`; formal commands are `rehearse`, `prepare`, and `run`; retry policy is none. Any post-seal pre-output failure aborts R465 and requires a successor.
- Pre-seal rehearsal note: the first rehearsal incorrectly tested the allowed observable-to-unobservable upper-right block of the quotient realization and therefore stopped before writing rehearsal/capacity artifacts. The corrected gate tests the lower-left gauge-to-retained block `U^T A v_g`, matching R464's quotient condition; thresholds, rho grid, model, and outcome tree are unchanged.

## Gate

### Outcomes

- `TOTAL-SENSITIVITY-VALID`: all point/mode/gauge/residual gates pass and both parameters meet Richardson, Frechet, full-transfer, band-energy, finite-window, and denominator checks.
- `MODE-SPECIFIC-NOT-TOTAL`: any paired point changes the registered active-mode hash; export one-sided/mode-specific data but make no smooth total-derivative claim.
- `TOTAL-DERIVATIVE-INVALID`: source, coordinate, convergence, conditioning, Frechet, direct-loop, or denominator checks fail.
- P1 is separately `SUPPORTED`, `REFUTED`, or `UNDECIDABLE`; it cannot strengthen the main validity class.
- Stop after classification. No retuning of `h`, grid, threshold, controller, or model; a successor is required for any alternate numerical class.

## 资产保护契约

Preserve R449, R459--R464, all parent models/results, paper-cited assets, and imported GPT material byte-for-byte. Add only the R465 adapter, prospective lifecycle records, create-only raw/derivative bundle, feed, claim, verdict, and registrations.

## Cross-references

- CLM-1400 / R449: explicitly partial A-channel sensitivity, not total attribution.
- Measured comparison path: `results/research_loop/r449_p1_sensitivity/formal_analysis.json`; its A-only candidate/reference terms are diagnostic inputs only.
- CLM-1435 / R459: complete Object B model, units, mappings, controllers, and measured hardware ladder.
- `paper/yang_md_decoupling_marl/working/gpt_pro_unresolved_math_solution_20260821/01_complete_solution.md#u5--完整闭环-md-灵敏度`: algebraic identity and scope limits.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/`: U5 required arrays and acceptance tests.
