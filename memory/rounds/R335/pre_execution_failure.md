# R335 pre-execution failure

- Stage: installed-runtime verification, before formal-attempt reservation and
  before any physical trajectory.
- Frozen seal SHA-256:
  `99b9480ab5c4ebd3c162e0a53f8535d4088b67794620006b5c5b567394a10f31`.
- Observed exception: `KeyError: 'case'` in
  `run_r335_disturbance_package._verify_installed_andes`.
- Root cause: the R335 adapter called the inherited R333 installed-source
  verifier and then expected it to return a `case` member. That inherited
  verifier returns only `version`, `package_root`, and `sources`. The already
  audited R334 adapter performs the missing official Kundur-case lookup and
  hash verification as a separate wrapper.
- Scope audit: `results/r335_disturbance_package` did not exist after the
  failure. No `formal_attempt.json`, failure artifact, physical record, fit,
  holdout record, analysis, controller action, training step, or manuscript
  result was created.
- Disposition: abort R335 as a pre-execution engineering failure. A successor
  may preserve the complete R335 scientific contract byte-for-byte apart from
  round/event identity and repair only the installed-case verifier. It must
  reserve a new round, preflight, re-seal every source, and execute once. R335
  has no scientific outcome and supports no claim.
