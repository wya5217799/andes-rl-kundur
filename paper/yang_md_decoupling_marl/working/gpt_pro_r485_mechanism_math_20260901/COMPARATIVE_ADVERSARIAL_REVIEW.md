# Comparative adversarial review — two R485 mechanism-math returns

## Project verdict

**`ADVERSARIAL QUALIFIED PASS`**. Prefer the undated second return for machine
replay and mathematical exposition, but do not inherit its whole narrative.
The useful result is a narrow command-path explanation, not a root-cause
certificate.

Both returns agree on the load-bearing result: under the registered
componentwise rate limiter and common per-record zero reset,

\[
\operatorname{TV}_c(p)+\sum_{n,i}|r_{n,T-1,i,c}-p_{n,T-1,i,c}|
\leq \operatorname{TV}_c(r).
\]

Thus the limiter cannot create the registered normalized command TV. The
formal R485 result remains 121/208 endpoint-qualified and 0/208
complete-contract-qualified.

## Which return is stronger

| Issue | Dated first return | Undated second return | Project decision |
|---|---|---|---|
| Package integrity | 4/4 hashes match | 4/4 hashes match | Tie |
| TV theorem | Correct self-contained induction | Same theorem, more compact source correspondence | Accept the shared theorem |
| Repo-side verifier | Rebuilds the result, but its own comparison fails on eight non-load-bearing floats; maximum absolute drift `8.56e-5` | Rebuilds from the original ZIP and passes its expected certificate on the repo runtime | Prefer the second verifier |
| Mechanism decomposition | Correctly rejects a unique decomposition | Gives the explicit missing fourth cell and shows why both interaction and Shapley allocation depend on it | Prefer the second proof; keep numeric allocations out of the main paper |
| Actor sensitivity | Local active-set Jacobians, radii, and endpoint secants | Kink-aware straight-path partition over all 14,400 included state segments | Prefer the second numerical certificate, but only for the one included checkpoint |
| RMS interpretation | Rejects dominant-source wording | Adds an exact temporal mean/variance identity and a direct counterexample | Prefer the second analysis |
| Overall label | `CERTIFIED-BOUNDED-MECHANISM` is too broad as an overall label | `QUALIFIED-DESCRIPTIVE-ONLY` is safer, although its separate `PROVED` completion label is still too easy to overread | Use project label `ADVERSARIAL QUALIFIED PASS` |

## Independent checks

- The second verifier ran against the exact original ZIP and extracted input
  tree on Python 3.14.3 / NumPy 2.4.3 / Torch 2.10.0 CPU. It exited zero after
  28.334 seconds and its recursive expected-certificate comparison passed.
- A separate partition audit sampled 257 of 14,400 actor paths, covering
  11,505 ReLU pieces and 34,515 interior points. The largest discrepancy
  between the claimed affine piece and a direct network evaluation was
  `1.14e-15`; a 257-point dense path sum never exceeded the certified path
  variation beyond `1.23e-15` numerical noise.
- A direct trace-only audit covered 192 record-agent-channel tracks. Every
  projected value stayed between the previous and raw command, maximum slew
  was exactly 0.25, and the smallest TV terminal-residual slack was positive
  (`1047.14`).
- Direct trace recomputation reproduced the included-checkpoint temporal
  variance fractions: 37.45%--51.23% of raw RMS-squared energy. This is
  incompatible with interpreting a near-one aggregate RMS ratio as evidence
  that the actor output is nearly static.

Machine details are in `GPT_PRO_RETURN_V2/REPO_RECHECK.json`.

## Adversarial limits the external answers understate

1. **The mean anchors are acausal diagnostics.** A within-record mean uses the
   entire 150-step record, including future values. It is useful for post-hoc
   attribution but is not an online controller intervention or implementable
   information pattern.
2. **The coverage is not representative sampling.** The 24 policies are a
   fixed 8-arm by 3-seed subset of 208 policies, and the path certificate uses
   only the included `an_cn_r0`, seed 501 checkpoint. The four profiles are
   fixed records. None supports a population probability or a claim about a
   typical policy.
3. **Frozen observations remove plant feedback.** Replacing actor inputs while
   retaining recorded observations identifies an actor-path contrast. It does
   not show how the modified command would change later observations,
   trajectories, endpoints, or training.
4. **Constant-anchor RMS changes two input groups.** The constant-anchor cell
   replaces both observations and previous-action slots by record means. Its
   norm ratio cannot be assigned to a single quasi-static source. The missing
   fourth factorial cell prevents a unique full-grid decomposition.
5. **The theorem is about normalized command TV.** It does not establish
   physical actuator energy, wear, fatigue, thermal stress, absolute safety,
   stability, or the TV of every downstream physical realization.
6. **The reset assumption matters.** The terminal-residual inequality is used
   with the R485 per-record zero reset. It must not be silently transferred to
   a warm-start or cross-record state convention.

## What helps the paper

Use only three additions, all in Discussion or a compact exploratory
supplement:

1. one displayed inequality showing that the registered limiter cannot be the
   source of excess normalized TV;
2. the frozen-observation, full-record-mean diagnostic: fixed/actual raw-TV
   ratios `0.0710--0.2046` in all 48 tested channel-policy cells;
3. the neutral RMS statement: constant-anchor/actual raw-RMS ratio at least
   0.90 in 141/192 fixed cells (M 54/96, D 87/96), followed by the one-checkpoint
   warning that temporal variation still contributes 37.45%--51.23% of raw
   RMS-squared energy.

The paper-facing interpretation is: the limiter structurally attenuates TV;
the learned actor is strongly sensitive to its time-varying previous-action
input on the tested frozen paths; and comparable aggregate RMS under a constant
anchor does **not** establish a quasi-static dominant source.

Do not put the representative Shapley allocations, product spectral bounds,
local Jacobian distribution, or the word `PROVED` in the main paper. They add
technical surface without closing the causal gap and would invite an avoidable
review objection.

## Experiment decision

No new simulation or training is required for the current paper. A genuine
causal-mechanism upgrade would require prospectively defined, non-anticipative
input replacements and new closed-loop plant trajectories across a declared
policy/profile population. That is a successor experiment, not a submission
prerequisite for the bounded R485 paper.
