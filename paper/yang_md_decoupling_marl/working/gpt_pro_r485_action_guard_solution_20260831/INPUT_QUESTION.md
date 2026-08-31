---
schema: math-problem-draft/v1
outcome: drafted
problem_id: R485-ACTION-GUARD-CONSTRUCT-001
project_id: andes-rl-kundur
authority_selector: R485/r485-formal-20260829-a
authority_source_ref: memory/rounds/R485/formal_seal.json
authority_content_digest: 3d5865619b21d4276a0c07616c136c690beefc4f779d65d48f7a0bf3e04ade7f
profile_ref: none
profile_digest: none
faithfulness_status: verified
---

# Math Problem Draft: R485 action guard 的构念有效性

## Handoff

- Original research question: 是否需要提取重要数学问题，我可以让gpt pro  回答
- Decision context: 仔细检查研究是否有问题，有没有硬伤
- Extraction summary: R485 的算术、哈希、lineage 和注册裁决已由 sealed-data replay 独立复算一致；唯一可能实质改变 `0/208 complete-contract` 科学解释的问题，是 normalized action RMS/total variation 相对 deterministic comparator 的乘法比值，究竟只测量 command activity，还是足以承载 physical stress/no-harm 含义。本草案只抽取这一项，不求解、不修改注册裁决。

## Selected sources

| Source ID | Locator | Content digest | Used for |
|---|---|---|---|
| S0 | `memory/rounds/R485/formal_seal.json` | `3d5865619b21d4276a0c07616c136c690beefc4f779d65d48f7a0bf3e04ade7f` | attempt、source 与 config authority |
| S1 | `memory/rounds/R485/plan.md` | `b97491a26837b14121a20baf2359e942461aef3aaa783a1d2e27c01656b16bc5` | 注册 claim、complete guard 与解释边界 |
| S2 | `memory/rounds/R485/config.json` | `58ce96255b7afbfb9fc8831d6311454b3c5b3ae9c4159bbc4351ced1db58a835` | profiles、阈值、action bounds 与 horizon |
| S3 | `results/research_loop/r485_60hz_source_factorial/r485-formal-20260829-a/formal_analysis.json` | `2dad35d8e7f559bbcfa124dbae3628aa0d9ceae3ccfbe77996330c891927409b` | 832 profile decisions、121/208、0/208、ratio distributions |
| S4 | `tmp/r485_postrun_data_audit.json` | `2c50e19448f405a39541f9786e7cfcd7e83e1f0e931037cca0456ee959cf132d` | 独立 replay、continuous ratios、Pareto 与 training diagnostics |
| S5 | `src/andes_rl_kundur/evaluation/r484_tail_guard.py` | `172d7b03ca8e7dbe06e812fac6c05d4e51d4330b8deed6c95541a236fc557978` | per-profile complete-guard conjunction |
| S6 | `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py` | `bb5cb7aafe4b03b556dbeca24773cfecc4d31955e4e6eb7e94b379107a6bb87c` | action RMS 与 total variation 的精确定义 |

## Top-level problem

在 R485 的冻结 benchmark 中，候选 learner 与 deterministic comparator 都以同一组 normalized command coordinates 记录 action。对每个 profile，注册规则要求候选的 action RMS 和 action total variation 均不超过 comparator 的 `1.10` 倍。请判定：

> 仅由 P0-P9，是否能推出该 conjunction 是一个 well-conditioned、在 horizon / sampling rate / channel count 变化下解释稳定、并且对 physical actuator stress 或 physical harm 有效的 no-harm criterion？若不能，请给出最小反例或缺失条件，区分 `fatal metric mismatch`、`construct-limited but usable as comparator-relative command activity` 与 `valid physical-stress proxy under explicit assumptions`，并写出每种 verdict 对 `0/208 complete-contract` 可支持的最强表述。

## Variables, domains, and units

| Name | Domain | Units | Meaning |
|---|---|---|---|
| `i` | frozen set of 208 policies | none | policy/seed cell |
| `p` | `{A,B,C,D}` | none | fixed same-bank profile |
| `r` | `{1,...,6}` | none | scenario record within one profile |
| `t` | `{0,...,149}` | sample index | 30 s trace at `Δt=0.2 s` |
| `c` | `{1,...,8}` | none | four VSGs times two normalized command channels |
| `a[i,p,r,t,c]` | `[-1,1]` | normalized command, dimensionless | executed candidate action |
| `b[p,r,t,c]` | `[-1,1]` | normalized command, dimensionless | executed deterministic-comparator action |
| `R(x)` | non-negative real | normalized command, dimensionless | RMS over all 6×150×8 entries |
| `V(x)` | non-negative real | normalized command, dimensionless | sum over records/time of the mean absolute adjacent change across 8 channels, including zero-to-first-action change |
| `m` | positive real | dimensionless | allowed action multiplier; registered value `m=1.10` |
| `H[i,p]` | Boolean | none | all non-action frequency/peak/RoCoF and validity guards pass |
| `E[i]` | Boolean | none | both aggregate endpoint ratios are at most `0.95` |

The exact registered action summaries are

`R(x) = sqrt((1/(6·150·8)) Σ_r Σ_t Σ_c x[r,t,c]^2)`

and, with `x[r,-1,c]=0`,

`V(x) = Σ_r Σ_t (1/8) Σ_c |x[r,t,c] - x[r,t-1,c]|`.

## Target

- Description: establish the logical and dimensional status of `R(a)<=mR(b)` and `V(a)<=mV(b)` as a physical no-harm criterion, and the strongest claim permitted by each admissible status.
- Type: implication proof, refutation by counterexample, or conditional theorem with explicit missing assumptions.
- Units: dimensionless inequalities; any physical-stress conclusion must introduce and check its physical units and action-to-actuator map explicitly.

## Premises

| Premise ID | Role | Exact statement | Selected source IDs |
|---|---|---|---|
| P0 | verified_fact | The frozen roster contains 208 policy/seed cells, four same-bank profiles, six records per profile and 150 samples per record; the sealed replay verifies 848 evaluation files, 5,088 trajectories and 763,200 steps with no hash, lineage, conversion, reward or summary mismatch. | S0-S4 |
| P1 | verified_fact | Candidate and comparator arrays are stored in the same eight normalized command-coordinate slots and obey the registered action bounds and slew checks. | S2, S3, S5, S6 |
| P2 | verified_fact | `R` and `V` are exactly the formulas stated above; `V` sums record-level time variation after averaging across the eight channels. | S6 |
| P3 | engineering_choice | The registered per-profile action guard is the conjunction `R(a)<=1.10R(b)` and `V(a)<=1.10V(b)`; a policy passes the complete contract only if every profile also passes all other guards and both aggregate endpoints. | S1-S3, S5 |
| P4 | verified_fact | All 832/832 candidate/profile blocks fail `action_rms_no_harm` and all 832/832 fail `action_variation_no_harm`; therefore no policy passes even one complete profile guard and `0/208` pass the complete contract. | S3, S4 |
| P5 | verified_fact | Among the endpoint-qualified policies, five pass every non-action guard. Their action multipliers needed for a complete pass are approximately `123.11`, `126.03`, `131.01`, `134.11`, and `137.04`, far above `1.10`; the full-roster action-only break-even range is approximately `97.66-140.25`. | S3, S4 |
| P6 | verified_fact | Comparator denominators are finite and not numerically near zero: profile-level action RMS is approximately `0.0547-0.0709` and total variation approximately `1.58-3.20`; representative candidate values are approximately `0.39-0.49` and `189-216`. | S3, S4 |
| P7 | verified_fact | The registered 4×4 sensitivity grid with action multipliers up to `2.00` has zero complete passes; this is not a borderline-threshold result. | S1, S3, S4 |
| P8 | unknown | No selected source supplies a calibrated physical actuator wear, energy, thermal, fatigue, saturation-duty or hardware-stress model that maps normalized commands to physical harm. | S0-S6 |
| P9 | hypothesis | Lower comparator-relative normalized-command RMS and time variation are scientifically meaningful proxies for lower physical actuator stress/harm across these learner and deterministic-controller implementations. | none |

## Required conclusions and admissible verdicts

- Required conclusions: (1) audit numerator/denominator commensurability; (2) derive how `R` and `V` scale with records, horizon, `Δt`, channel count and normalization; (3) test whether P0-P8 imply physical no-harm or only command-activity no-harm; (4) provide a smallest counterexample when the implication fails; (5) state the minimal additional assumptions under which a physical-stress implication would hold; (6) map the result to the strongest defensible interpretation of `0/208` without changing the frozen arithmetic.
- Admissible verdicts: `proved`, `refuted_by_counterexample`, `conditional`, `information_insufficient`.
- Requested classification label: one of `fatal metric mismatch`, `construct-limited command-activity metric`, or `valid physical-stress proxy under explicit assumptions`.

## Statement-faithfulness audit

| Check | Status | Defect or source locator |
|---|---|---|
| Authority/attempt | verified | S0 binds R485 and `r485-formal-20260829-a`. |
| Roster/horizon/cases | verified | S2-S4 bind 208×4 policy/profile blocks and 6×150 record/step layout. |
| Formula and zero initial action | verified | S6 defines RMS, zero-to-first difference and record-level variation sum. |
| Inequality direction and conjunction | verified | S5 uses candidate `<= 1.10 × reference` for both action metrics inside an all-guards conjunction. |
| Numeric conditioning evidence | verified | S3-S4 show finite, non-negligible denominators and very large observed ratios. |
| Candidate/comparator physical semantics | unverified | The same normalized slots are recorded, but selected sources do not prove identical actuator dynamics or physical stress meaning. |
| Physical units/model | unverified | P8 records the missing action-to-hardware stress map; the draft does not invent one. |
| Registered verdict preservation | verified | The question audits interpretation; it does not post-hoc replace `m=1.10` or alter `0/208`. |

## Subgoal ledger

| Obligation ID | Exact statement | Allowed premise IDs | Depends on | Acceptable failure certificate | Project-side check |
|---|---|---|---|---|---|
| G0 | Verify that every compared numerator and denominator has the same coordinate normalization, record roster, time grid and channel aggregation. | P0-P3 | none | an explicit mismatch table | reopen S2, S5, S6 and one candidate/reference raw pair |
| G1 | Derive scaling of `R` and `V` under duplicated horizon, changed `Δt`, duplicated channels and affine action renormalization. | P1-P3 | G0 | counterexample showing non-invariance | reproduce the formulas symbolically and numerically |
| G2 | Bound ratio conditioning using the observed denominator ranges; distinguish numerical instability from construct mismatch. | P4-P7 | G0 | condition-number or perturbation bound | check S3-S4 distributions |
| G3 | Decide whether P0-P8 imply any physical-stress/no-harm ordering. | P0-P8 | G0-G2 | two minimal counterexamples: physically benign but ratio-failing, and physically harmful but ratio-passing | domain review of any added actuator model |
| G4 | State the weakest added assumptions that make `R/V` monotone upper bounds or proxies for a named physical stress quantity. | P1-P3, P8-P9 | G3 | proof that no non-vacuous bridge follows without new data/model | dimensional and sign audit of each assumption |
| G5 | For each requested classification label, state exactly what `0/208` does and does not establish. | P3-P9 | G2-G4 | an explicit `information_insufficient` boundary | compare wording with S1 claim ceiling |
| G6 | If suggesting a replacement diagnostic, label it prospective/secondary and prove it does not retroactively change the registered R485 verdict. | P0, P3-P9 | G3-G5 | no defensible alternative without actuator semantics | require a new registration before future use |

## Claim boundary

This draft can support a decision about whether R485's `0/208 complete-contract` should be described as failure of a frozen comparator-relative **normalized command-activity** guard, or may additionally be interpreted as physical actuator-stress/no-harm evidence under explicit assumptions. It cannot by itself establish hardware safety, actuator wear, energy use, thermal or fatigue limits, generalization to unseen seeds/profiles/topologies, or universal MARL impossibility. It cannot post-hoc change the registered `0/208` arithmetic or `VALID-MIXED` label; a fatal construct mismatch would instead require downgrading the scientific meaning of the complete guard and prospectively registering a repaired metric.

## Blocking reasons

none for extraction. The missing physical action-to-stress bridge is deliberately preserved as P8/P9 and may cause the solver to return `conditional` or `information_insufficient`.
