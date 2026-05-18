#!/bin/bash
# bisect.sh — E3 code-drift bisection R58 -> R65
# Runs in parallel with launch.sh (Phase 3 E2/E4/E1) since ANDES allows
# up to 3 parallel WSL python processes. Each commit gets its own git
# worktree under .wt/bisect-<SHA>; ckpts go into the main worktree's
# results/r77_phase3/ so cleanup just removes .wt/ entries.
#
# Config: matches the R57-alpha baseline used by CLM-0104 to expose
# the -19% LSTM regression — seed=51, warmup=5, tau=default (0.005),
# h=64.

set -e
REPO=/mnt/c/Users/27443/Desktop/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
OUT=$REPO/results/r77_phase3
STATUS=$OUT/e3_STATUS.txt
mkdir -p $OUT $REPO/.wt

declare -A SHA_R=(
  [e8427df]=R58
  [43d203b]=R59
  [2752a8f]=R60
  [1a3a4ad]=R61
  [48c466c]=R62
  [6671e8d]=R63
  [6c27ae1]=R64
  [4c5327a]=R65
)

ts() { date '+%Y-%m-%d %H:%M:%S'; }
status() { echo "[$(ts)] $*" >> $STATUS; echo "[$(ts)] $*"; }

status "=== E3 bisect launch (parallel with Phase 3 main) ==="
status "Target config: --algo td3_lstm --seed 51 --warmup 5 (default tau=0.005)"
status "Reference: R57-alpha had v_6axis=0.526; R66 same config gave 0.4259 (-19%, CLM-0104)"

for SHA in e8427df 43d203b 2752a8f 1a3a4ad 48c466c 6671e8d 6c27ae1 4c5327a; do
  R="${SHA_R[$SHA]}"
  WT=$REPO/.wt/bisect-$SHA
  SAVE=$OUT/e3_bisect_${R}_${SHA}
  mkdir -p $SAVE

  status "[E3 $R $SHA] adding worktree $WT"
  cd $REPO
  if [ -d "$WT" ]; then
    git worktree remove -f $WT 2>>$STATUS || true
  fi
  git worktree add -f --detach $WT $SHA >> $STATUS 2>&1

  status "[E3 $R $SHA] training (save to $SAVE)"
  cd $WT
  $PY scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 75 --seed 51 --hidden-size 64 \
    --lstm-lr-warmup-eps 5 --save-dir $SAVE \
    > $SAVE/train.log 2>&1 || status "[E3 $R $SHA] WARN train.py exited non-zero"
  status "[E3 $R $SHA] training done"

  cd $REPO
  git worktree remove -f $WT >> $STATUS 2>&1 || true
done

status "=== E3 bisect complete ==="
status "Next: eval each ckpt with score_run.py from main worktree,"
status "      look for the v3.1 cliff between adjacent commits."
