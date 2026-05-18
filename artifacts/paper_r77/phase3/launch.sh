#!/bin/bash
# phase3_launch.sh — Phase 3 R77 review-revision experiments
# Sequential execution (ANDES single-session-per-process limit on WSL).
# Total wall ~29h: E2 ~3h + E4 ~5h + E1 ~21h.
#
# Outputs under results/r77_phase3/.
# Marker file r77_phase3/STATUS.txt updated after each experiment.

set -e
REPO=/mnt/c/Users/27443/Desktop/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
OUT=$REPO/results/r77_phase3
LOG=$OUT/launch.log
STATUS=$OUT/STATUS.txt
mkdir -p $OUT

# tee everything to launch.log
exec > >(tee -a $LOG) 2>&1
cd $REPO

ts() { date '+%Y-%m-%d %H:%M:%S'; }
status() { echo "[$(ts)] $*" >> $STATUS; echo "[$(ts)] $*"; }

status "=== Phase 3 launch ==="
status "REPO=$REPO  PY=$PY"
status "Sequential schedule: E2 (3 reruns, ~3h) -> E4 (5 critic-reroll, ~5h) -> E1 (3 seeds x 500ep, ~21h)"

# ─── E2: s59 wu20 re-train 3x for within-version SD ────────────────
status "--- E2 starting (s59 wu20 re-train x3 for within-version SD) ---"
for i in 1 2 3; do
  # Vary seed-offset to get fresh RNG init while keeping seed=59 nominal
  OFFSET=$((100 * i))  # 100, 200, 300
  SAVE=$OUT/e2_s59_rerun_${i}_off${OFFSET}
  mkdir -p $SAVE
  status "[E2 rerun $i] seed=59 seed_offset=$OFFSET save=$SAVE"
  $PY scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 75 --seed 59 --seed-offset $OFFSET \
    --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001 \
    --save-dir $SAVE > $SAVE/train.log 2>&1
  status "[E2 rerun $i] done. log: $SAVE/train.log"
done
status "--- E2 complete ---"

# ─── E4: critic-init re-roll on 5 dead seeds ────────────────────────
# Approximation: --seed-offset shifts the full torch RNG which re-rolls
# the actor + critic + buffer init. Pure-critic-only re-roll would
# require train.py modification (out of scope for this run); the full-
# RNG re-roll is the closest available proxy.
status "--- E4 starting (dead-seed critic-init re-roll, 5 seeds) ---"
for SEED in 49 53 57 58 60; do
  SAVE=$OUT/e4_reroll_s${SEED}_off1000
  mkdir -p $SAVE
  status "[E4 reroll] seed=$SEED seed_offset=1000 save=$SAVE"
  $PY scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 75 --seed $SEED --seed-offset 1000 \
    --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001 \
    --save-dir $SAVE > $SAVE/train.log 2>&1
  status "[E4 reroll s$SEED] done. log: $SAVE/train.log"
done
status "--- E4 complete ---"

# ─── E1: 3 seeds x 500-ep convergence curve ────────────────────────
status "--- E1 starting (3 seeds x 500ep convergence) ---"
for SEED in 54 56 59; do
  SAVE=$OUT/e1_500ep_s${SEED}
  mkdir -p $SAVE
  status "[E1 500-ep] seed=$SEED save=$SAVE"
  $PY scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 500 --seed $SEED \
    --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001 \
    --save-dir $SAVE > $SAVE/train.log 2>&1
  status "[E1 s$SEED] done. log: $SAVE/train.log"
done
status "--- E1 complete ---"

status "=== Phase 3 ALL DONE ==="

# ─── E3 / E6 markers (not auto-executed) ────────────────────────────
cat > $OUT/e3_TODO.md <<EOF
# E3 — Code-drift bisection (manual setup required)

Bisect the 19% LSTM regression between R58 (e8427df) and R65 (4c5327a)
across these 6 commits:

  R58 e8427df  Paper-strict audit
  R59 43d203b  PI Briefing Layer
  R60 2752a8f  Q-0006/0007/0009 triple-probe
  R61 1a3a4ad  Q-0007 full impl + SAC HAWE neg
  R62 48c466c  Q-0007 真重训 + TD3+Q7 +24pp
  R63 6671e8d  Autonomous hyper sweep
  R64 6c27ae1  lr=3e-3 unlocks SOTA
  R65 4c5327a  SAC + new hyper

Procedure (one worktree per commit):

  for SHA in e8427df 43d203b 2752a8f 1a3a4ad 48c466c 6671e8d 6c27ae1 4c5327a; do
    git worktree add \$REPO/.wt/bisect-\$SHA \$SHA
    (cd \$REPO/.wt/bisect-\$SHA && \$PY scripts/train.py \\
       --algo td3_lstm --normalize-actions --episodes 75 --seed 51 \\
       --hidden-size 64 --lstm-lr-warmup-eps 5 --tau 0.005 \\
       --save-dir \$REPO/results/r77_phase3/e3_bisect_\$SHA \\
       > \$REPO/results/r77_phase3/e3_bisect_\$SHA.log 2>&1)
    git worktree remove \$REPO/.wt/bisect-\$SHA
  done

Then \$PY scripts/score_run.py --label e3_bisect ... and look for the
v3.1 cliff between adjacent commits. The leading suspect (R61 monitor
extension) should be the first commit with the -19% drop.

Wall: ~8h (8 commits x 1h). Not auto-run because each commit requires
git worktree add/remove and re-installation of dependencies.
EOF

cat > $OUT/e6_TODO.md <<EOF
# E6 — NE-39 second benchmark (BLOCKED by ADR-01)

ADR-01: "NE39 envs were never completed (M0<20 -> TDS divergence;
REGCA1 -> 6 algebraic+state var DAE bloat)."

Approach: would need to (1) re-enable an NE39 env class in
src/andes_rl_kundur/env/andes/ (currently in _legacy/), (2) confirm
M0 >= 20 for all 10 SGs, (3) run a single-seed sanity train at 75 ep.
If TDS converges, run 3-seed v3.1 comparison against Kundur.

Wall: ~1 week including env re-enable. Defer to follow-up paper.

Alternative second benchmarks if NE-39 stays blocked:
- IEEE 68-bus reduced-equivalent NETS-NYPS interconnect
- WSCC 9-bus (smaller, faster)
EOF

status "E3 + E6 TODO markers written."
status "Phase 3 launch script complete."
