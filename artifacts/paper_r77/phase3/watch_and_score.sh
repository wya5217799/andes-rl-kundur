#!/bin/bash
# watch_and_score.sh — wait for bisect.sh to finish, then auto-run
# score_bisect.py over all 8 e3_bisect_* dirs. Idempotent.
set -e
REPO=/mnt/c/Users/27443/Desktop/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
STATUS=$REPO/results/r77_phase3/e3_STATUS.txt
SCORE_LOG=$REPO/results/r77_phase3/score_bisect.log

ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] [watch_and_score] start, polling for bisect completion" >> $SCORE_LOG

# Poll every 60s for the completion marker in e3_STATUS.txt
while true; do
  if grep -q "=== E3 bisect complete ===" $STATUS 2>/dev/null; then
    echo "[$(ts)] [watch_and_score] bisect.sh finished, starting scoring" >> $SCORE_LOG
    break
  fi
  sleep 60
done

cd $REPO
$PY artifacts/paper_r77/phase3/score_bisect.py >> $SCORE_LOG 2>&1 || \
  echo "[$(ts)] [watch_and_score] WARN score_bisect.py exited non-zero" >> $SCORE_LOG

echo "[$(ts)] [watch_and_score] running collect.py" >> $SCORE_LOG
$PY artifacts/paper_r77/phase3/collect.py >> $SCORE_LOG 2>&1 || \
  echo "[$(ts)] [watch_and_score] WARN collect.py exited non-zero" >> $SCORE_LOG

echo "[$(ts)] [watch_and_score] DONE" >> $SCORE_LOG
