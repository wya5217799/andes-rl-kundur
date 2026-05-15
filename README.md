# andes-rl-kundur

Multi-agent SAC control of virtual synchronous generator (VSG) inertia
and damping on the modified Kundur 4-bus system, reproducing
Yang et al., IEEE TPWRS 2023, on the ANDES quasi-static phasor backend.

## Status

ANDES main path completed at R37 (2026-05-16). Repository is a continuing
research workbench: post-review revisions, journal resubmission,
ablations, and new algorithm experiments happen here. The codebase was
refactored into a standard Python src-layout on 2026-05-16 (see
`docs/adr/0001-src-layout.md` for the long-form rationale).

## Getting started

### Reading orientation

1. `CONTEXT.md` — glossary + 14 architecture decisions.
2. `memory/STATE.md` — auto-rendered current headlines, open
   decisions, latest round, latest handoff.
3. Latest file in `memory/handoffs/` — what was in progress at last
   handoff.
4. `_legacy/RESEARCH_TRAIL.md` — full causal chain R01..R37 (frozen).

### Install

ANDES requires WSL (see `docs/eng-notes/NOTES_ANDES.md`). Inside the
WSL `andes_venv`:

```bash
pip install -e .          # installs andes-rl-kundur in editable mode
```

The scripts under `scripts/` are runnable without `pip install -e .`
because each one adds `src/` to `sys.path` itself.

### Running training

```bash
# Default V4 paper-faithful training (Kundur, 4 VSGs, SAC × 4)
/home/<user>/andes_venv/bin/python scripts/train.py \
    --episodes 75 --seed 49 --save-dir results/v4_h50_s49

# Resume / fine-tune from a prior checkpoint directory
/home/<user>/andes_venv/bin/python scripts/train.py \
    --episodes 1000 --seed 49 \
    --resume results/v4_h50_s49 \
    --save-dir results/v4_h50_s49_resumed

# Shared-actor warmstart across all four agents
/home/<user>/andes_venv/bin/python scripts/train.py \
    --episodes 500 \
    --warmstart-shared results/phase9_shared/agent_shared.pt \
    --save-dir results/v4_warmstart
```

### Running evaluation

```bash
# No-control baseline (paper Fig 6/8)
/home/<user>/andes_venv/bin/python scripts/eval_no_control.py

# DDIC evaluation on one checkpoint
/home/<user>/andes_venv/bin/python scripts/eval_ddic.py \
    --ckpt-dir results/v4_h50_s49 --suffix best --label r21

# Batch evaluation across all seeds + 6-axis ranking
/home/<user>/andes_venv/bin/python scripts/eval_all_seeds.py

# HAWE inference-time ensemble (paper Asset 5)
/home/<user>/andes_venv/bin/python scripts/eval_ensemble.py \
    --ckpt-dirs results/v4_h50_s49 results/v4_ws8 \
    --suffixes best best --weights 0.98 0.02 --agg weighted \
    --label hawe_w9802
```

### Memory subsystem

See `MEMORY.md`. Run `python memory/tools/validate.py` before commits.
Regenerate `memory/STATE.md` via `python memory/tools/render.py`.

## Layout

| Path | Contents |
|------|----------|
| `src/andes_rl_kundur/` | Library code (agents, env, evaluation, probes, utils, config, scenarios contract) |
| `scripts/` | Runnable entry points (train + 4 eval drivers) |
| `tests/` | pytest regression suite |
| `artifacts/paper/` | IEEE journal manuscript + figure scripts + figures |
| `artifacts/dissertation/` | UNNC FYP dissertation |
| `memory/` | Claim ledger + rounds + handoffs + auto-rendered STATE.md |
| `docs/` | ADRs, engineering notes, design specs |
| `results/` | Gitignored except `whitelist/` (paper-cited checkpoints/JSON) |
| `_legacy/` | Frozen source-of-truth docs and ancestor modules |

## Testing

```bash
/home/<user>/andes_venv/bin/python -m pytest tests/
```

`tests/test_v4_env_regression.py` runs a ~90 s end-to-end no-control
roll-out and compares against `results/research_loop/eval_v4_baseline_PRE_REFACTOR/`
at 1e-9 tolerance. Both LS1 and LS2 must remain bit-identical.

## Citations

If you reference findings from this repo, cite claim IDs:
"… achieved 0.444 6-axis score (CLM-0005)."

Claim IDs are stable; numerical values may be superseded — check
`status: current` before quoting.

## License

TBD (private repo).
