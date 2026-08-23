# R474 code review B — guardrails §A implementation audit

**Reviewer**: independent subagent (science-guard focus)
**Round**: R474 (same-time-permutation placebo, 60 P-cell retrain)
**Commits reviewed**: 8cc2ccb, 1712eeb, 04b1bd0, 6b40175

**Decision**: PASS (after fixes)

## Round 1 (FAIL) — blocker and fix

- **BLOCKER** the realized-slot check and unit tests were built on a slot convention
  the real env does not implement (`COMM_ADJ` asymmetry: device 0 lists [i+1, i-1],
  devices 1..3 list [i-1, i+1]); per-slot pool equality is unsatisfiable under the
  true layout.
  FIXED: `source_rows` P fills the channels per the true env layout
  (cols 3,4 <- d_omega of (i+2); cols 5,6 <- omega_dot of (i+2)); `routing_check`
  checks channel-block source-pool equality against the real `COMM_ADJ`, tuple-changed
  and non-neighbour against the real adjacency, and realized slot identity against the
  true wiring for both N and P; unit tests build joints from the real COMM_ADJ and
  genuinely discriminate correct from broken wiring (empirically re-probed: correct
  wiring passes all flags; pi=(i+1) -> non_neighbour=False; identity -> changed=False;
  pair-block/scrambled joints -> realized=False).
- **MINORs** (non-blocking, recorded): imported donor manifest retains its legacy
  `splits` section (no R474 path reads it; `donor_bank_npz_not_imported: True`);
  `_no_donor_reachable` is a textual gate (definitional; call-graph audit confirms no
  R474 entry point reaches donor functions).

## Per-property table (re-review, all VERIFIED)

| Guardrail §A property | Verdict |
|---|---|
| A.1 same-time permutation purity (no donor bank) | VERIFIED |
| A.2 pool equality (per feature channel, real COMM_ADJ source pools) | VERIFIED |
| A.2 every source tuple changed | VERIFIED |
| A.2 no P source is a true neighbour | VERIFIED |
| A.2 same contemporaneous pool | VERIFIED (definitional) |
| A.2 realized-slot wiring verification | VERIFIED |
| No-donor reachability / npz non-import / splits unread | VERIFIED |
| Reuse legitimacy (48 N/0 cells, deterministic evals) | VERIFIED |
| Wording boundary (A.3, no intrinsic claim) | VERIFIED |
