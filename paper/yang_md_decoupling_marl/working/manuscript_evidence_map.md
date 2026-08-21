# Manuscript logic and evidence map

## Fixed paper identity

- **Title:** *Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning*
- **Paper type:** evaluation / negative-result paper with a constructive structured-control companion
- **One-sentence story:** on the tested direct-​M/D interface, a strong structured controller exhausts the registered static/PI law bank and three fixed-budget MARL arms fail physical guards; a separate 350-member piecewise-schedule study later supplies one bounded partial-transfer witness, while the repaired information contract yields a cleanly measured negative runtime-message increment and a distinct energy-port controller passes both development and unseen gates, without identifying the cause of the MARL failure.
- **Primary claim unit:** one modified Kundur topology, one ANDES version, registered finite banks, direct-​M/D Object A, and three training seeds.
- **Auxiliary claim unit:** feasibility-native energy-port Object B, first on disclosed development data and then on a one-use unseen bank; never pooled numerically with Object A.

## Thinking-template table

| Element | Manuscript answer | Evidence boundary |
|---|---|---|
| Research background | Parallel VSGs are electrically coupled; adaptive M/D and MARL are plausible coordination tools. | Verified literature only. |
| Existing limitation | Reward gains and message availability do not prove physical common/differential decoupling; zero-action baselines overstate learning value. | Evaluation logic plus cited MARL protocol literature. |
| Key question | Can matched four-actor MARL improve both registered physical endpoints over a strong deterministic direct-​M/D controller without common/action harm? | R399 and R402. |
| Challenge 1 | Define decoupling as an input-output endpoint rather than as a coordinate transform. | Route contract and R399. |
| Challenge 2 | Audit whether the intended runtime-message comparison actually preserves its registered information contract. | R400 contract, R402 defect audit, R410 repair re-execution. |
| Challenge 3 | Interpret a negative learner without claiming universal infeasibility. | Conditional theory plus R408/R409 constructive counterexample. |
| Method module 1 | Signed common/differential probes, localized disturbances, and guard-first classification. | R399/R402. |
| Method module 2 | Strong deterministic finite bank and outcome-seeing finite oracle. | R399. |
| Method module 3 | Scalar TD3, nominal no-message CD-MATD3, and message CD-MATD3 with matched budgets, followed by an information-contract audit and a repaired re-execution. | R402 plus the imported final causal-validation bundle plus R410/CLM-1215. |
| Method module 4 | Reduced-model exact-separation proposition and first-order M/D authority lemma. | User-supplied derivations, corrected and bounded in manuscript. |
| Companion module | 0.4-Hz ring-edge bandpass through feasibility-native energy ports. | R408 development and R409 unseen gate. |
| Main contribution | A physically guarded negative MARL evaluation with a scope-bounding positive companion and an explicit causal non-identifiability audit. | Same-line evidence; no universal MARL or single-cause claim. |

## Research questions and current answers

| RQ | Question | Current answer |
|---|---|---|
| RQ1 | Can a deterministic direct-​M/D controller materially reduce both physical endpoints? | Yes on development data: −60.79% off-diagonal and −64.13% differential energy vs zero, all guards pass. |
| RQ2 | Is additional headroom present in the registered finite deterministic family? | Not in the original static/PI bank: the outcome-seeing oracle selects the development law on all four evaluation profiles. In the separately frozen 350-member piecewise-schedule family, R458 selects one development-only winner that passes every guard on two of four fixed evaluation profiles. Neither result is global optimality or a transfer probability. |
| RQ3 | Do the tested MARL arms improve the strong comparator? | No. Median ratios are 4.12/2.92, 4.16/3.13, and 5.09/3.30 for cross/differential endpoints; all blocks fail guards. |
| RQ4 | Do runtime neighbour messages add a positive increment? | No, measured cleanly. With the mask enforced in every actor path, the message arm shows −78.43% off-diagonal and −26.74% differential three-seed-median improvement over the repaired no-message arm; both arms still fail all physical guards. Single-factor contrast within the tested bundle (CLM-1215). |
| RQ5 | Do these failures prove decoupling or finite-order control impossible? | No. The energy-port K=3.5 controller enters Q on development and passes unseen data at $r_d=0.938218,r_{cross}=0.793730$. |

## Claim ledger

| Manuscript claim | Authoritative source | Allowed wording | Forbidden extension |
|---|---|---|---|
| Four actors independently execute bounded delta-M/delta-D at 0.2 s in a 60-Hz modified Kundur model. | `paper/yang_md_decoupling_marl/reports/R399.md` | Exact object and timing. | Hardware, EMT, field, topology generalisation. |
| Deterministic development improvements are 60.79% and 64.13%. | R399 / CLM-1140 | “Relative to zero action on two development profiles.” | Universal superiority or unseen-bank effect. |
| Finite oracle gives 0% incremental improvement on four evaluation profiles. | R399 / CLM-1140 | “Within the same nine-law family.” | All controllers or all causal policies are exhausted. |
| A development-only selection over 350 fixed piecewise direct-M/D schedules yields one winner that is guard-clean on both development profiles and two of four fixed evaluation profiles. | `paper/yang_md_decoupling_marl/reports/R458.md` / CLM-1430 | Bounded finite-bank existence and partial-transfer witness; name the eval-a TV failure and eval-d 4.85% versus 5% threshold failure. | 50% transfer probability, topology generalisation, learner discoverability, stability, safety, or unrestricted controller-class feasibility. |
| Nine learning runs complete; 40 JSON files contain 216 learning and 24 deterministic trajectories, 240 total (both executions). | `results/research_loop/r410_message_repair/formal_manifest.json#/evaluation_records` plus the frozen 3×3×4×6 + 1×4×6 design | The manifest count supersedes the erroneous 264 wording in the R402 feed and CLM-1155; use file and trajectory hierarchy explicitly. | More seeds, independent-policy replication, or a held-out learner gate. |
| Learning ratios and guard failures. | R410 / CLM-1215 (fresh re-execution; R402 / CLM-1155 remains the historical canary) | Canary-level bounded negative result. | “MARL cannot work” or “SAC fails.” |
| Under the repaired information contract the message arm shows a negative three-seed-median increment over the matched no-message arm (−78.43% off-diagonal, −26.74% disturbance differential). | R410 / CLM-1215 | Single-factor within-bundle contrast; both arms still fail the physical guards; R410 values supersede R402 for these arms and the R410-vs-R402 absolute comparison is two-factor (R402 trained under the pre-repair slew projector). | Communication is useless or harmful in general; guard-passing message benefit; a causal increment beyond the tested bundle. |
| Static homogenization fails physical guard. | `paper/yang_md_decoupling_marl/reports/R405.md` / CLM-1180 | Ideal structural intuition is insufficient in the full finite-window DAE test. | Proposition 1 is false. |
| Bandpass K=3.5 and K=4.0 enter Q on development. | `paper/yang_md_decoupling_marl/reports/R408.md` / CLM-1195 | Constructive development candidates on Object B. | MARL or direct-​M/D success. |
| Small-gain anomaly is reference semantics; physical leakage is negligible. | R408 / CLM-1200 | Specific to the measured auxiliary map and bank. | Exact physical zero sum for all states. |
| Frozen K=3.5 passes the unseen bank. | `paper/yang_md_decoupling_marl/reports/R409.md` / CLM-1210 | $r_d=0.938218,r_{cross}=0.793730$, all guards, one topology and one bank. | Distributional, topology, EMT, or hardware generalisation. |
| Distinct five-seed edge-action study has no neural increment over its classical controller. | `paper/icems2026/reports/R338.md` / CLM-0905 | Non-pooled mechanism triangulation in Discussion. | Four VSG actors, same action object, or a larger main-study sample. |
| Adding a common channel changes offline feasibility from 10/16 to 16/16. | `paper/decoupling_marl_model_first/reports/R363.md` / CLM-0965 | Non-pooled action-basis mechanism evidence. | Causal controller, nonlinear simulation, information realizability, or learning. |
| Outcome-seeing energy residual lowers differential ratio to 0.818 but leaves both cross ratios at 1.0. | `paper/paralleled_vsg_marl/reports/R382.md` / CLM-1055 | Non-pooled evidence that one endpoint is not joint decoupling. | Deployable control, global headroom, or MARL value. |
| Exact separation iff homogeneous M,D. | Corrected derivation from user-supplied solution files | Ideal balanced symmetric reduced model only. | Full DAE, approximate finite-window, or recovered non-Laplacian matrix. |
| Zero-bias M/D feedback is absent from the local first-order Jacobian. | Corrected derivation from user-supplied solution files | Smooth multiplicative coefficient model near equilibrium. | Universal nonlinear or cubic-order impossibility. |
| CD objectives omit explicit action-effort/slew penalties and differ from the registered physical decision contract. | `src/andes_rl_kundur/agents/cd_matd3.py#physical_costs` and `scripts/run_r402_cd_matd3_canary.py#_train_one` | Verified design mismatch; consistent with but not identified as a cause of action stress or endpoint degradation. | Sole-cause or dominant-cause wording. |
| The original no-message execution masked neighbour slots only at interaction/evaluation, not inside actor updates; R410 repaired the contract and re-measured the contrast. | Imported final causal-validation source audit (defect) + R410 / CLM-1215 (repair and measurement) | Historical defect described in past tense; the R410 contrast is the clean single-factor measurement. Exact historical post-amendment source lineage remains incomplete. | A clean message ablation in the historical execution, a communication-value estimate beyond the tested bundle, or proof that the defect caused the historical endpoint failure. |
| Executed learned actions are statefully slew projected, while the actor state omits the previous executed action and actor/target objectives optimize unslewed outputs. | Imported final causal-validation source audit, corroborated against the preserved/current projector and learner | Post-hoc action-interface mismatch and credible failure hypothesis. | Dominant-cause, convergence, or physical-effect wording without a paired intervention. |
| Retained final-20 multipliers are small and touch zero. | Six R402 training manifests, summarized in the imported R402 causal audit | Tail-only post-hoc diagnostic; final values remain positive and actor-gradient exposure is unlogged. | The common objective was deleted throughout training or had negligible gradient contribution. |
| Budget completion with `convergence_diagnostics_valid=true`. | `scripts/run_r402_cd_matd3_canary.py#_train_one` | Execution-validity check only. | Convergence, nonconvergence, or a directional claim about more training. |

## Assessment of the supplied mathematical files

### Useful in the draft

1. **Exact reduced-model separation criterion.** It supplies a clean structural explanation and can be proved by high-frequency Markov parameters.
2. **First-order multiplicative-authority lemma.** It explains why dynamic M/D feedback is a difficult local channel and why an additive power-like port can be more direct.
3. **One-sided theorem refinement.** Under the full projected channels and subspace-preserving coupling assumptions, either complete cross-block rational identity alone forces homogeneous diagonal M and D.
4. **Index-1 DAE boundary.** Algebraic elimination gives $B_{u,r}=f_u-f_yg_y^{-1}g_u$, which may be nonzero even when the differential equation has no direct additive action term. This prevents transferring the ODE lemma to the ANDES DAE without the actual Jacobians.
5. **Nonsmooth order bound.** With same bias, locally Lipschitz feedback, a shared first-order map, and one common active mode, controller trajectories differ by at most $O(\varepsilon^2)$ on a fixed horizon; the actual implementation has not undergone the amplitude-scaling test needed to claim that order empirically.
6. **Rejection of a product lower bound.** The measured point $1.0346\times0.6778=0.7013<1.045$ directly rules out the proposed bound for the measured class.
7. **FIR-Youla/SLS direction.** It is an appropriate future route for a bounded controller-class certificate if the response parameterization and internal-stability conditions are made rigorous.

### Must not enter as established results

1. “All finite-order LTI controllers are infeasible.” R408/R409 provide a constructive counterexample on Object B.
2. “Any causal controller is infeasible.” The finite outcome-seeing oracle ranges over nine laws, not over all causal policies or action sequences.
3. “Policy differences first appear at cubic odd order.” The implemented law and asymmetric decoder are nonsmooth; only the first-order Jacobian statement is retained.
4. “The energy-port map has a fixed decoded sum of 800.” The actual map is state-dependent and asymmetric. R408 found normalized zero sum only to numerical precision and an approximately quadratic, negligible physical leak only in the $K\le0.1$ small-gain regime; higher gains scale differently.
5. “MARL failed because the baseline has a nonzero bias.” The strong deterministic controller's static bias is not established; causality among reward, initialization, features, and exploration was not isolated.
6. “The SLSQP script is a certificate.” Solver termination is not a conic dual certificate and does not itself establish a valid Youla/SLS closed-loop parameterization.
7. “The actual DAE supplies no additive first-order channel.” The required $f_y,g_y,g_u,f_u$ matrices have not been identified for the project plant.
8. “The energy-port controller succeeds because of the DAE Schur-complement channel.” The formula establishes a possible path, not the cause of the measured result.
9. “The actual signed-probe controller difference is quadratic.” The imported $O(\varepsilon^2)$ result is conditional theory; the required amplitude ladder and common-mode logs do not exist in the current evidence line.
10. “The common constraint was removed throughout training.” Only final-20 multiplier and cost values are retained; the exact actor-update gradient contribution is unavailable.
11. “CD-MATD3 failed to converge.” Completing 43,200 steps with finite diagnostics establishes execution validity, not optimization convergence or nonconvergence.
12. “Runtime messages are intrinsically useless or harmful.” The repaired bundle measures a negative three-seed-median message increment (−78.43% off-diagonal, −26.74% disturbance differential), but only inside a guard-failing regime for one tested bundle; the general statement stays forbidden.
13. “Action/interface mismatch dominates optimization failure.” R402 and the energy-port study use unmatched objects, and the available evidence does not rank objective, optimization, information, decoder, or action-channel mechanisms causally.

## R402 causal-audit disposition

- **Verified design facts:** the nominal no-message actor-update path violates its intended mask; the stateful executed-action slew map is absent from the actor state and target-action semantics; the CD objectives omit explicit effort/slew penalties and are not identical to the registered endpoint/guard contract; and the multiplier update and action decoder are mechanically as stated. These are post-hoc source-audit findings with incomplete immutable R402 execution-source provenance, not identified outcome causes.
- **Bounded post-hoc diagnostics:** retained tail multipliers are small and touch zero; learned actions are more stressed than the deterministic reference; neither observation identifies an endpoint-degradation cause.
- **Strong alternatives that remain open:** critic/optimization and replay adequacy, partial observability, credit assignment, decoder conditioning, distribution shift, and limited incremental direct-M/D headroom near the strong comparator.
- **Counter-evidence against a single reward explanation:** scalar TD3 also fails under a different reward that includes aggregate action-related terms.
- **Conference-paper decision (superseded by the owner-authorized R410 repair):** the audit's "no retraining required" was an option under the manuscript-only stage; the owner directed the single-factor mask repair instead, executed as R410/CLM-1215. Correct the count, remove convergence and dominant-cause wording, disclose missing diagnostics, and preserve the R408/R409 object separation.
- **Future discriminating evidence:** first repair and test the information mask and stateful-action semantics through paired single-factor interventions with complete gradient, critic, replay, multiplier, and message-intervention logs; actual DAE/finite-horizon authority matrices would address a different mechanism question. None is authorized in the manuscript-only stage.

## U1--U9 external-mathematics intake after R458

The canonical intake is
`paper/yang_md_decoupling_marl/working/gpt_pro_unresolved_math_solution_20260821/IMPORT_NOTE.md`;
the external answer is non-authoritative and passed only conditionally.

| Item | Evidence-map disposition | Drafting action |
|---|---|---|
| U1 | Current artifacts identify neither a feasible 10-tap differential Youla/SLS witness nor an infeasibility certificate. | Use only as a certificate non-identifiability boundary; prohibit controller-class impossibility. |
| U2 | The access/reward/donor factorial is a valid future causal design, with no observed outcome and no current training authority. | Future work only; do not imply population message value. |
| U3 | The stateful slew projector makes previous executed action part of the Markov state and requires projected-action consistency in critic and target semantics. | Safe implementation limitation; do not invent a Bellman-bias magnitude. |
| U4 | Expected common quadratic cost is not an inner approximation of the exact per-profile guard intersection. | Safe constraint-hierarchy statement; the conservative common-only bound is not a recommended budget. |
| U5 | Total M/D sensitivity includes equilibrium and all sampled I/O, discretization, controller, headroom, and denominator derivatives. | Safe generic identity; no numerical Object-B derivative or A-only causal attribution. |
| U6 | Endpoint failure and closed-loop stability are distinct; the available nonlinear endpoint threshold is only conditionally bracketed in 0--0.2 s. | Safe bounded statement; no pole-crossing, phase-margin, or robust-delay claim. |
| U7 | The supplied generic bilinear-leading-term proposition omits the pure-action quadratic term. | Block original wording. Require one fixed smooth mode plus nearby-command equilibrium invariance, or retain the `u^2` term. |
| U8 | Approximate common/differential separation depends on commutators, I/O leakage, heterogeneity, and resolvent/Schur conditioning jointly. | Safe structural limitation; no numerical DAE cross-energy bound. |
| U9 | Sealed R458/CLM-1430 takes priority branch 1 and returns `GUARD-CLEAN-TRANSFER` on two fixed evaluation profiles. | Enter only as a finite-bank witness; not a probability or topology claim. |

No item in this table authorizes a new experiment. Missing U1/U2/U5--U8
observables remain prospective work requiring a new frozen evidence round.

## Four-point self-consistency check

1. **Problem–method:** the physical endpoint/guard problem is answered by signed-probe evaluation and guarded fixed-budget comparisons, while the source audit prevents the flawed information contrast from being treated as a matched ablation.
2. **Method–result:** every numerical result names its action object, split, reference, and guard status.
3. **Result–claim:** negative learning evidence is bounded to the tested bundle; positive energy-port evidence is bounded to one topology and two registered banks.
4. **Title–evidence:** the fixed title is acceptable only because the abstract says the paper evaluates the MARL objective rather than claiming MARL success. No successful-MARL claim appears.

## Next evidence path

1. Keep the K=3.5 energy-port controller frozen; do not retune on the consumed unseen bank.
2. Test topology and parameter perturbations with a prospectively frozen protocol and the same guards.
3. Only after structural robustness is shown, consider EMT or controller-delay evidence.
4. If learning is revisited, use a baseline-anchored residual on the successful energy-port structure with hard no-harm projection; do not reopen an unstructured direct-​M/D sweep.
5. Treat FIR-Youla/SLS as a separate mathematical-certification project until its assumptions and dual evidence are complete.
6. If a stronger mechanism claim is needed, extract the actual index-1 DAE Jacobians and algebraic conditioning prospectively; until then, retain the DAE result only as a limitation on Lemma 1.
