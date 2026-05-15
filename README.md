# andes-rl-kundur

Multi-agent SAC control of virtual synchronous generator (VSG) inertia and
damping on the modified Kundur 4-bus system, reproducing Yang et al. TPWRS
2023 on the ANDES quasi-static phasor backend.

## Status

ANDES main path completed (R37, 2026-05-08). Repository is a continuing
research workbench: post-review revisions, journal resubmission, ablations,
and new baselines happen here.

## Getting started

### Reading orientation
1. `memory/STATE.md` — auto-rendered ~50 lines, current headlines + open
   decisions + latest round + latest handoff. Read this first.
2. Latest file in `memory/handoffs/` — ongoing work, what's pending.
3. `_legacy/RESEARCH_TRAIL.md` — full causal chain R01-R37 (frozen).

### Running training
ANDES requires WSL. See `scenarios/kundur/NOTES_ANDES.md`.

```bash
# In WSL
wsl -e bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  <wsl_python> scenarios/kundur/train_andes_v4.py"
```

### Memory subsystem
See `MEMORY.md`. Run `python memory/tools/validate.py` before commits.
Regenerate `memory/STATE.md` via `python memory/tools/render.py`.

## Layout
- `env/`, `scenarios/`, `agents/`, `evaluation/`, `probes/`, `scripts/` —
  ANDES code + research probes
- `paper/` — IEEE journal manuscript + figure scripts + figures
- `dissertation/` — UNNC FYP dissertation
- `memory/` — claim ledger + rounds + handoffs + auto-rendered STATE.md
- `_legacy/` — frozen source-of-truth docs from predecessor repo
- `results/` — gitignored except `whitelist/` (paper-cited ckpts/JSON)

## Citations

If you reference findings from this repo, cite claim IDs:
"… achieved 0.444 6-axis score (CLM-0005)."

Claim IDs are stable; numerical values may be superseded — check `status:
current` before quoting.

## License

TBD (private repo).
