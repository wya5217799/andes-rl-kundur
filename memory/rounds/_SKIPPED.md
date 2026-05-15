# Skipped round numbers

Some round IDs are reserved but never materialized as `RNN/` directories.
Each gap has a one-line reason here so that audits and `validate.py`
don't treat them as missing data.

- **R09** — skipped. Round naming jumped to R10 (no work was done as R09).
- **R12–R19** — skipped. Internal 8 round IDs reserved during the R10–R17
  forensic sprint but never materialized as separate dirs; the
  "Pivot 2 (R10–R17)" phrasing in `CLM-0010` refers to investigations
  recorded inside `R10/round_10_to_17_unified_verdict.md` (one verdict
  bundled the whole sweep), not eight individual round directories.
- **R31, R32** — skipped. Round numbers allocated for stochastic ensemble
  (R31) and per-axis ensemble (R32) negative findings; outcomes were
  folded into `R30` (ensemble baseline) and `R33` (HAWE weight sweep)
  respectively rather than getting their own dirs.

## Policy

- **Forward**: when a new round is opened, use the next sequential ID
  (`R{max_existing + 1}`). Don't reserve IDs you don't immediately use.
- **Backward**: don't backfill gaps. Existing skipped IDs stay listed
  here; new gaps would only appear if a planned round is explicitly
  abandoned, in which case add a line here with the reason.
