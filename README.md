# andes-rl-kundur

Multi-agent reinforcement learning control of virtual synchronous generator (VSG)
inertia and damping on the modified Kundur 4-bus system, reproducing
Yang et al., IEEE TPWRS 2023, using the ANDES quasi-static phasor backend.

## Status (as of 2026-05-21, R259)

Active research workbench. Algorithmic plateau (R86, CLM-0148/0149: critic Q
monotone along action axis, argmax at boundary ±1) confirmed structural across
91 trials. Current focus: reward-shaping and mechanism characterisation
(R255–R259 probe-first protocol). Project SOTA: 4-way same-seed cross-algorithm
HAWE ensemble (CLM-0295, R154).

The Python package was refactored into a standard `src/` layout on 2026-05-16
(see `docs/adr/0001-src-layout.md`).

## Getting started

### Reading orientation

1. `AGENTS.md` — Codex new-session bootstrap for the automatic research loop.
2. `memory/RESEARCH_PROGRAM.md` — TPWRS thesis, phase gates, ranked questions,
   evidence requirements, and pivot rules.
3. `CONTEXT.md` — glossary + architecture decisions (AD-01 … AD-14).
4. `memory/STATE.md` — auto-rendered headlines, open questions, latest round.
5. `docs/adr/` — ADRs covering src layout, paper-faithful split, PI
   briefing contract, V5 REGCA1 plant, and ANDES-only platform decision.

### Install

ANDES requires WSL (see `docs/eng-notes/NOTES_ANDES.md`). Inside WSL `andes_venv`:

```bash
pip install -e .          # installs andes-rl-kundur in editable mode
```

Scripts under `scripts/` add `src/` to `sys.path` themselves and run without
the pip install step.

### Running training

```bash
# Default V4 paper-faithful training (Kundur 4-bus, 4 VSGs, TD3-LSTM × 4)
/home/<user>/andes_venv/bin/python scripts/train.py \
    --episodes 75 --seed 49 --algo td3_lstm --save-dir results/v4_lstm_s49

# Resume from a prior checkpoint directory
/home/<user>/andes_venv/bin/python scripts/train.py \
    --episodes 500 --seed 49 --algo td3_lstm \
    --resume results/v4_lstm_s49 \
    --save-dir results/v4_lstm_s49_resumed
```

### Running evaluation

```bash
# No-control baseline (paper Fig 6/8)
/home/<user>/andes_venv/bin/python scripts/eval_no_control.py

# Single-checkpoint DDIC evaluation
/home/<user>/andes_venv/bin/python scripts/eval_ddic.py \
    --ckpt-dir results/v4_lstm_s49 --suffix best --label r21

# 11-axis paper-grade ranking
/home/<user>/andes_venv/bin/python scripts/score_run.py \
    --ckpt-dirs results/v4_lstm_s49 --label v4_lstm_s49

# HAWE inference-time ensemble (paper Asset 5)
/home/<user>/andes_venv/bin/python scripts/eval_ensemble.py \
    --ckpt-dirs results/v4_lstm_s49 results/v4_lstm_s54 \
    --suffixes best best --weights 0.98 0.02 --agg weighted \
    --label hawe_w9802
```

### Memory subsystem

```bash
python memory/tools/research_goal.py --json # select/resume one TPWRS-aligned goal
python memory/tools/validate.py        # check claim/question/round schema
python memory/tools/render.py          # regenerate memory/STATE.md
python memory/tools/status.py          # operational dashboard (training, active rounds)
python memory/tools/round_preflight.py R<N>   # pre-launch checklist for a new round
python memory/tools/baselines.py --match <run> # look up measured baselines
python memory/tools/dual_metric_lint.py       # audit paper-reward-ablation claims
```

See `MEMORY.md` for the full memory-subsystem design.

## Layout

| Path | Contents |
|------|----------|
| `src/andes_rl_kundur/` | Library code: agents, env (V4 + V5), evaluation, probes, utils, config, scenarios |
| `scripts/` | Runnable entry points: train, 4 eval drivers, round experiment drivers (r99–r259), score_run |
| `probes/` | Round-level probe scripts |
| `tests/` | pytest regression suite (35+ tests) |
| `memory/` | Claim ledger (CLM-0001–CLM-0485+), rounds (R01–R259), tools, STATE.md |
| `docs/` | ADRs (0001–0005), engineering notes, design specs, paper deviation log |
| `results/` | Gitignored except `whitelist/` (paper-cited checkpoints + JSON) |
| `_legacy/` | Frozen ancestor modules and pre-refactor research trail |

## Agents

| Class | File | Notes |
|-------|------|-------|
| SAC | `sac.py` | Original paper algo |
| SAC-CTDE | `sac_ctde.py` | Centralised-training decentralised-execution |
| TD3 | `td3.py` | Baseline |
| TD3-LSTM | `td3_lstm.py` | R79+ SOTA base (LSTM tau=0.001, warmup=5) |
| TD3-LSTM2 | `td3_lstm2.py` | Two-layer LSTM variant |
| TD3-LSTM-hreg | `td3_lstm_hreg.py` | Hidden-state regularisation |
| TD3-LSTM-warmh0 | `td3_lstm_warmh0.py` | Warm hidden-state initialisation |
| TD3-QR-LSTM | `td3_qr_lstm.py` | Quantile-regression critic |
| TD3-QR-LSTM-hreg | `td3_qr_lstm_hreg.py` | QR + hidden-state reg |
| TD3-AFE-LSTM | `td3_afe_lstm.py` | Adaptive feature extraction |
| TD3-QR-AFE-LSTM | `td3_qr_afe_lstm.py` | QR + AFE |
| TD3-Transformer | `td3_transformer.py` | Transformer actor (R82; deterministic-eval collapse known) |

## Testing

```bash
/home/<user>/andes_venv/bin/python -m pytest tests/
```

Key regression contracts:
- `test_v4_env_regression.py` — full no-control roll-out at 1e-9 tolerance
  (both LS1 and LS2 must remain bit-identical against the PRE_REFACTOR baseline).
- `test_reserve_round.py` — 30 cases pinning atomic mkdir + active-round detection + GC.
- `test_paper_grade_axes_v31.py` — paper-grade scoring regression (Asset 4).

## Citations

When referencing findings, cite claim IDs:

> "… achieved 0.4139 cum_rf score (CLM-0295)."

Claim IDs are stable. Numerical values may be superseded — check
`status: current` before quoting. Use `python memory/tools/query.py --best cum_rf`
to find the current best.

## License

Released under the [MIT License](LICENSE).
