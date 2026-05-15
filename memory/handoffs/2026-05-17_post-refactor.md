# Handoff — post-refactor pickup state (2026-05-17)

**Branch**: `main` (refactor branch merged, 18 commits pushed)
**Last round**: R37 (code architecture refactor + 5-cand deepening pass)
**Active research target**: "更好的 agent" — break the 0.137 multi-seed
attractor / exceed HAWE 0.439 ceiling.

## Where things stand

- 14 architecture decisions executed (CONTEXT.md § AD-01 .. AD-14)
- 7 deepening candidates resolved (V4Config, EpisodeResult, _SACBase,
  Check Protocol, LSFigureBenchmark rename + Cand 5 absorbed + Cand 6
  already shipped)
- 4 hidden bugs found and fixed (monitor import, CLM-0040 G4 inertia
  silent inheritance, deviation_summary lying about G4 state,
  torch.load(weights_only=False) RCE)
- 21 pytest tests pass at 1e-9 bit-identical to PRE_REFACTOR baseline
- `scripts/eval_no_control.py` reproduces max_df = 0.189 / 0.168
  byte-identical

## Run-this-first sanity ladder

```bash
# 1. Import smoke (3 s)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python \
  -c 'from andes_rl_kundur import AndesMultiVSGEnvV4, SACAgent, BaseAgent; print(\"OK\")'"

# 2. Full test suite (~1.7 min)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python -m pytest tests/"

# 3. End-to-end no-control eval (~1 min)
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python scripts/eval_no_control.py"
# Expect: LS1 max_df=0.189, LS2 max_df=0.168
```

## Next-step menu (sorted by ROI)

### A — Validate infra end-to-end with a real 75-ep training
```bash
/home/wya/andes_venv/bin/python scripts/train.py \
    --episodes 75 --seed 49 --save-dir results/post_refactor_smoke_s49
```
Currently queued in the background of the merge session. Confirms the
new V4Config + EpisodeResult + train loop path produces a usable
checkpoint and that the cum_rf / 6-axis numbers stay in R21 ballpark.

### B — TD3 alternative to SAC (highest research ROI)
`_SACBase` is ready; add `agents/td3.py` with a TD3Agent that
inherits the actor / replay scaffold and writes its own update().
SAC's entropy bonus is what pulls the actor back to near-zero (R32
finding); TD3 has none. Multi-seed sweep on V4 env to test whether
the 0.137 attractor breaks.

### C — G4 inertia preserved baseline (CLM-0040 follow-up)
Set `V4Config(zero_g4_inertia=False)` and retrain. The paper-faithful
Kundur 4-SG baseline that R15 forensic recommended has never been run
end-to-end. Result may shift the published numbers materially.

### D — Curriculum learning on disturbance magnitude
V4 env's `DIST_MIN` / `DIST_MAX` are class-level; with V4Config they
can be per-instance. Start training on `DIST_MIN=0.1, DIST_MAX=0.5`
then ramp up to paper's 0.5..2.0. Avoids early lucky-basin entrapment.

### E — Plug-in Check for r_max_df gating (Cand 2 seam)
Write a simple research-rule check (e.g. "abort if max_df > 0.5 Hz
for 5 consecutive episodes") to exercise the new `register_check()`
seam in real training. Confirms the extension path before we trust
it for harder research questions.

## Where the bodies are buried (anti-patterns to remember)

- **WSL only**: ANDES never runs on Windows-side python. Always
  `wsl bash -c "/home/wya/andes_venv/bin/python ..."` (not raw
  `wsl -e python` — Git Bash translates the path).
- **Max 3 parallel WSL python processes**: R23 finding — TDS internal
  stiffness mis-judges under contention.
- **ZERO_G4_INERTIA=True is paper-headline numbers**: any False
  experiment must be flagged as non-paper-reproducible.
- **paper_grade_axes.py is paper-cited**: changes require a new round
  + claim. Path moves alone are fine but get a CLM-NNNN claim entry.

## Open questions for next session

- Choose A → (B or C). I recommend A first to confirm infra is solid,
  then B (TD3) as the highest-ROI research move.
- Decide whether to set up GitHub Actions CI (~30 min one-off).
- Decide whether to spin up GPU cloud (Vast.ai / Modal) for parallel
  multi-seed sweeps — bypass the 3-process WSL limit.
