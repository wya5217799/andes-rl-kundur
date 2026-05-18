#!/bin/bash
# bisect.sh — E3 code-drift bisection R58 -> R65 (v2: git-archive based)
#
# Original v1 used `git worktree add --detach` which failed with
# `error: reset died of signal 1` under nohup detachment on WSL.
# v2 uses `git archive` to extract the commit's tree into /tmp/bisect-<SHA>/
# without touching the git index, then trains from there. No worktree
# bookkeeping, no SIGHUP-triggered reset failure.
#
# Config: matches the R57-alpha baseline used by CLM-0104 to expose
# the -19% LSTM regression — seed=51, warmup=5, tau=default (0.005),
# h=64.

set -e
REPO=/mnt/c/Users/27443/Desktop/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
OUT=$REPO/results/r77_phase3
STATUS=$OUT/e3_STATUS.txt
TMP=/tmp/r77_bisect
mkdir -p $OUT $TMP

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
status() { echo "[$(ts)] $*" | tee -a $STATUS; }

status "=== E3 bisect v2 (git-archive based) ==="
status "Target config: --algo td3_lstm --seed 51 --warmup 5 (default tau)"
status "Reference: R57-alpha had v_6axis=0.526; R66 same config gave 0.4259 (CLM-0104)"

for SHA in e8427df 43d203b 2752a8f 1a3a4ad 48c466c 6671e8d 6c27ae1 4c5327a; do
  R="${SHA_R[$SHA]}"
  EXTRACT=$TMP/bisect-$SHA
  SAVE=$OUT/e3_bisect_${R}_${SHA}
  mkdir -p $SAVE

  status "[E3 $R $SHA] extracting commit tree to $EXTRACT"
  rm -rf $EXTRACT
  mkdir -p $EXTRACT
  cd $REPO
  git archive --format=tar $SHA | tar -x -C $EXTRACT

  status "[E3 $R $SHA] training (save to $SAVE)"
  cd $EXTRACT
  $PY scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 75 --seed 51 --hidden-size 64 \
    --lstm-lr-warmup-eps 5 --save-dir $SAVE \
    > $SAVE/train.log 2>&1 || status "[E3 $R $SHA] WARN train.py exited non-zero"
  status "[E3 $R $SHA] training done"

  cd $REPO
  rm -rf $EXTRACT
done

status "=== E3 bisect complete ==="
status "Next: eval each ckpt under current main-worktree score_run.py for"
status "      a v3.1 score under the v3.1 ranker. Look for the cliff."
