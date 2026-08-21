#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/extracted/gpt_pro_math_pack_20260820" >&2
  exit 2
fi
SRC=$(cd "$1" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
python "$HERE/verify_evidence.py" --source-root "$SRC" --advisory-root "$ROOT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python "$HERE/rebuild_evidence.py" --source-root "$SRC" --output-root "$TMP/rebuilt"
python "$HERE/compare_evidence_rebuild.py" "$ROOT/evidence/evidence_register.csv" "$TMP/rebuilt/evidence/evidence_register.csv"
python "$HERE/c1_exact_conic_dual_checker.py" "$HERE/examples/HYPOTHETICAL_c1_dual_example.json"
python "$HERE/lint_numeric_traceability.py" "$ROOT/problems" "$ROOT/report" > "$ROOT/qa/numeric_trace_lint.json"
echo "All deterministic evidence checks completed. Review qa/numeric_trace_lint.json manually; it is heuristic and non-failing."
