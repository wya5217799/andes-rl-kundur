# Owner decision: bounded message-contrast repair round before ICEMS 2026 final paper (2026-08-16)

## Decision

The repository owner directed in the 2026-08-16 session: the manuscript must
not ship with the R402 message-contrast hole (the nominal no-message arm's
actor updates consumed unmasked neighbour slots, so the recorded
message-minus-no-message difference is not a clean information contrast), and
the repair experiment must be executed now before the final-paper deadline.
This registers the owner decision authorizing **one bounded evidence round**
on this line: apply the single-factor mask fix and re-execute the matched
learning comparison on the R402-identical contract, then integrate the
verified outcome into the manuscript.

## Scope of the authorized round

1. **Single-factor repair.** Apply the actor-training-mask contract fix
   (audit reference fix `0001_fix_no_message_actor_training_mask.patch` from
   `working/r402_causal_validation_final_bundle`) so that
   `cd_matd3_no_message` zeroes neighbour slots in every actor path —
   online, target, and update. No other learner, runner, reward, or
   estimator change.
2. **R402-identical re-execution.** All three arms
   (`yang_scalar_td3`, `cd_matd3_no_message`, `cd_matd3_message`) × seeds
   401/402/403 (9 runs), 43,200 interaction steps per run, the same
   development/evaluation profile partition as R402, identical
   hyperparameters, checkpoint rule, estimators, and physical guards.
   Scalar and message arm code paths are unchanged by the fix and serve as
   drift/reproducibility anchors against the R402 records.
3. **Pre-registered comparisons.** (a) the same physical guard
   classification as R402 against the deterministic reference; (b) a clean
   seed-median message increment of the message arm over the repaired
   no-message arm on both physical endpoints, the first valid measurement of
   the runtime-message contrast.
4. **Manuscript integration.** Update `manuscript/manuscript.md` §4.3/§5.2
   (and §7 if warranted) and `working/manuscript_evidence_map.md` with the
   verified result, replacing the descriptive-only message wording with the
   measured single-factor contrast.

## Authority boundaries (unchanged or narrowed)

- Only the mask fix enters learner code. The slew/state mismatch, the
  50-to-60 observation-adapter ambiguity, and the CD objective-to-gate gap
  remain unfixed and disclosed exactly as in R402.
- No title change, no algorithm replacement, no energy-port work, no fresh
  unseen bank. Reuse of the R402 profile partition is explicitly authorized
  here because the comparability of the message contrast requires the
  identical profiles, seeds, and estimators.
- Physical execution enters evidence prospectively through the full round
  lifecycle on this line; preflight before any ANDES/training run.
- If the repaired execution changes the R402 classification outcome (e.g.,
  any repaired arm passes the registered physical guards), the round pauses
  at the claim gate for an owner decision before any manuscript
  restructure.

## Records

- Decision doc: this file
  (`working/route_owner_decision_message_repair_2026-08-16.md`)
- Round: `memory/rounds/R41x` (reserved by the atomic tool)
- Results: `results/research_loop/r41x_*` (create-only, hashed)
- Feed: `paper/yang_md_decoupling_marl/reports/R41x.md`
