# andes-rl-kundur

Multi-agent reinforcement learning control of virtual synchronous generator (VSG)
inertia and damping on the modified Kundur 4-bus system, reproducing
Yang et al., IEEE TPWRS 2023, using the ANDES quasi-static phasor backend.

## Status

This is an active research workbench. Current research state is generated from
the ledger in `memory/STATE.md`; programme gates and the authorized question
queue live in `memory/RESEARCH_PROGRAM.md`. This README intentionally carries
no copied round number, headline metric, or "current focus" snapshot.

The Python package was refactored into a standard `src/` layout on 2026-05-16
(see `docs/adr/0001-src-layout.md`).

## Getting started

### Reading orientation

1. `AGENTS.md` — Codex new-session bootstrap; it runs the bounded
   `memory/tools/session_context.py` adapter.
2. `memory/RESEARCH_PROGRAM.md` — durable TPWRS policy, read when the context
   adapter selects research work.
3. `CONTEXT.md` — domain glossary; individual architecture decisions are in
   `docs/adr/`.
4. `memory/STATE.md` — on-demand auto-rendered headlines and history, not a
   mandatory cold-start read.
5. `docs/README.md` — document taxonomy and durable homes.
6. `docs/adr/` — accepted architecture decisions.

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
/home/<user>/andes_venv/bin/python scripts/andes_scratch.py scripts/train.py \
    --episodes 75 --seed 49 --algo td3_lstm --save-dir results/v4_lstm_s49

# Resume from a prior checkpoint directory
/home/<user>/andes_venv/bin/python scripts/andes_scratch.py scripts/train.py \
    --episodes 500 --seed 49 --algo td3_lstm \
    --resume results/v4_lstm_s49 \
    --save-dir results/v4_lstm_s49_resumed
```

### Running evaluation

```bash
# No-control baseline (paper Fig 6/8)
/home/<user>/andes_venv/bin/python scripts/andes_scratch.py scripts/eval_no_control.py

# Single-checkpoint DDIC evaluation
/home/<user>/andes_venv/bin/python scripts/andes_scratch.py scripts/eval_ddic.py \
    --ckpt-dir results/v4_lstm_s49 --suffix best --label r21 \
    --out-dir results/eval_ddic_r21

# 11-axis paper-grade ranking
/home/<user>/andes_venv/bin/python scripts/score_run.py \
    --ckpt-dirs results/v4_lstm_s49 --label v4_lstm_s49

# HAWE inference-time ensemble (paper Asset 5)
/home/<user>/andes_venv/bin/python scripts/andes_scratch.py scripts/eval_ensemble.py \
    --ckpt-dirs results/v4_lstm_s49 results/v4_lstm_s54 \
    --suffixes best best --weights 0.98 0.02 --agg weighted \
    --label hawe_w9802 --out-dir results/eval_hawe_w9802
```

### Memory subsystem

```bash
python memory/tools/research_goal.py --json # select/resume one TPWRS-aligned goal
python memory/tools/session_context.py --json # bounded cold-start route
python memory/tools/feed_check.py <feed> # pre-draft publication gate
python memory/tools/validate.py        # check claim/question/round schema
python memory/tools/render.py          # regenerate memory/STATE.md
python memory/tools/status.py          # operational dashboard (training, active rounds)
python memory/tools/round_preflight.py R<N>   # pre-launch checklist for a new round
python memory/tools/baselines.py --match <run> # look up measured baselines
python memory/tools/dual_metric_lint.py       # audit paper-reward-ablation claims
```

The memory-subsystem contract lives in `CLAUDE.md`.

## Layout

| Path | Contents |
|------|----------|
| `src/andes_rl_kundur/` | Library code: agents, env (V4 + V5), evaluation, probes, utils, config, scenarios |
| `scripts/` | Stable training, evaluation, maintenance, and round execution adapters; lifecycle is declared in the repository contract |
| `probes/` | Conclusion-affecting, question-specific investigation scripts |
| `tests/` | pytest regression suite |
| `memory/` | Claim/question/round/note ledger, tools, and generated STATE.md |
| `docs/` | Document taxonomy, ADRs, engineering notes, research investigations, and governance |
| `paper/<line>/` | Registered manuscript source, feed reports, corpus, and drafts |
| `results/` | Gitignored except `whitelist/` (paper-cited checkpoints + JSON) |
| `tmp/` | Ignored scratch, caches, and ephemeral review output |
| `skills/` | Repository-local process adapters; they do not replace code or evidence |
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

- `test_repo_governance_cli.py` — repository contract, delivery registry,
  executable lifecycle, navigation, and debt-ratchet behavior.
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
