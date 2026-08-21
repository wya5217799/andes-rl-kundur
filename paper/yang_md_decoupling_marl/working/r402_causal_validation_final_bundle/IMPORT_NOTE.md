# R402 causal-validation final bundle: import and disposition

## Source and verification

- Imported from `C:\Users\27443\Downloads\R402_causal_validation_final_deliverables\r402_validation_final` on 2026-08-16.
- Original archive SHA-256: `16b96ce4f70ab253a143097aa62b99eb70c6eaf8cc5ece89dc7ffc7be38b2752`.
- Audited input archive: `r402_causal_validation_v1.zip`, SHA-256 `3876b06d735d181e77105bfecdf0ed7d594c85251921f3fd5810965d32d84332`.
- All 47 hashes listed by the imported bundle passed local verification.
- The supplied tests were rerun against the 203-MB input package: `9 passed`.

The imported files are preserved verbatim under `source/`. They are an external
audit and design aid, not a replacement for formal guards, current claims,
same-line feeds, or sealed result artifacts.

## Accepted findings

1. The independent raw-data recomputation confirms 40 evaluation JSON files,
   240 trajectories (216 learning and 24 deterministic), and the registered
   `CANARY-FAIL`. The maximum reported endpoint recomputation difference is
   below `2e-18`.
2. A post-hoc audit of the preserved implementation finds that the nominal
   no-message arm masks neighbour slots for environment interaction and final
   evaluation, while replay stores the unmasked observation and online/target
   actor updates consume unmasked actor rows. The message-minus-no-message
   comparison is therefore descriptive, not a clean runtime-message causal
   ablation.
3. Executed learned actions pass through a stateful slew projector whose
   previous-action memory is absent from the seven-slot actor observation.
   Replay contains the executed action, but target and online actor objectives
   optimize unslewed actor outputs. This is a learning/action-interface
   mismatch and a credible shared failure mechanism, but its physical effect
   was not isolated by a paired intervention.
4. The CD training costs and the registered signed-pair physical decision
   metrics are different mathematical objects. The scalar arm's default action
   terms penalize squared fleet-mean parameter changes, so cancelling
   componentwise actions can evade that penalty. These are objective-design
   facts, not identified causes of the endpoint degradation.
5. Normalized boundary saturation and physical M/D lower-clamp occupancy are
   distinct diagnostics. The imported clamp counts are post-hoc and must not be
   presented as preregistered endpoints.

## Qualifications and rejected promotions

- The bundle calls several code facts `PROVED-MATHEMATICALLY`. The manuscript
  uses the narrower phrase `post-hoc source-code audit` because proof of code
  semantics is not proof of outcome causation.
- The copied runner, learner, controller, and runner-test hashes do not all
  match the earlier R402 rehearsal source hashes, and R402 has no
  `formal_execution.json`. The two critical interface findings are corroborated
  in the preserved source copy and current repository, but the exact
  post-amendment execution-source lineage is incomplete. This is a provenance
  limitation, not permission to rewrite history.
- The deterministic controller alone applies the declared 50-to-60 observation
  adapter, whereas the learning arms train and evaluate on the legacy scale.
  This is retained as a contract/comparator ambiguity; it does not establish a
  causal failure because each learner sees the same scale at training and
  evaluation.
- `root_cause_ranking.csv` is a hypothesis-prioritization aid, not scientific
  evidence. No dominant R402 root cause is identified.
- The reference patches, successor contract, and E0-E8 execution runbook are
  prospective design material. They were not applied to the repository and do
  not authorize training, fresh banks, new ANDES simulation, or DAE extraction
  during the current manuscript-only stage.

## Manuscript disposition

The draft should retain the bounded learning-versus-deterministic canary result,
but it must stop calling the nominal no-message arm a clean matched information
ablation. The negative message-arm difference may be reported only as a
descriptive bundle comparison. The slew-state mismatch and missing diagnostic
logs belong in Discussion and Limitations as unresolved implementation and
optimization explanations.

## Further GPT Pro mathematics

No additional complex mathematical study is required to complete the current
ICEMS conference draft. The existing conditional modal-separation proposition,
first-order authority lemma, and energy-port constructive counterexample already
bound the paper away from an impossibility claim. A future successor study may
formalize a small Markov-state lemma for the stateful slew map or export the
actual R402 DAE/LTV authority matrices, but neither would repair the historical
message ablation or identify a physical root cause without a prospective paired
experiment.
