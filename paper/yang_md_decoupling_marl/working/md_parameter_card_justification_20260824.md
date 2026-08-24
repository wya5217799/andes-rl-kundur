# M/D parameter-card justification

Status: project-calibration contract for corrected revalidation; not a strict
Yang benchmark card and not primary-source physical validation.

The repository's canonical Yang fact base records action increments
`ΔH=[-100,+300]` and `ΔD=[-200,+600]`, but it does not supply baseline `H0`
or `D0`, nor enough unit/base information to reconstruct a unique physical
benchmark card. Therefore the current `H0=100 s`, `M0=200 s`, and `D0=100`
values must not be attributed to Yang et al.

These values are inherited project calibration values from the established V4
configuration. They are held fixed here solely to isolate the device-base to
system-base conversion correction. No controller outcome from the corrected
or historical banks was used to choose them. With `M=2H`, the registered
device-base `ΔM=[-200,+600]` map corresponds exactly to the reported
`ΔH=[-100,+300]` range; the damping increment range is retained unchanged.

The historical runtime-readback claim in `memory/claims/CLM-0740.md` concerns a
different 60-Hz model-first object. It may corroborate that runtime M/D values
are observable, but it does not justify this V4 parameter card.

Consequently, Phase 1 can support only a corrected project-calibration finite
bank. A future claim of strict Yang physical benchmarking requires a new,
prospectively sourced parameter card and a separate plan.

Authoritative repository anchors:

- `docs/paper/kd_4agent_paper_facts.md` (Yang action ranges and missing
  baseline/unit facts)
- `src/andes_rl_kundur/env/andes/v4_config.py` (inherited project calibration)
- `src/andes_rl_kundur/env/andes/md_convention.py` (base conversion contract)
- `memory/claims/CLM-0740.md` (explicitly non-substitutable historical object)
