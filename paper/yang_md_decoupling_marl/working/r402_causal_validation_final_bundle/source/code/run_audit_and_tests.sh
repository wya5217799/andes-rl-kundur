#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 <extracted-package-root> <output-dir> [source-zip]" >&2
  exit 2
fi

PACKAGE_ROOT=$(realpath "$1")
OUTPUT_DIR=$(realpath -m "$2")
SOURCE_ZIP=${3:-}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DELIVERY_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

args=(
  --package-root "$PACKAGE_ROOT"
  --output-dir "$OUTPUT_DIR"
)
if [[ -n "$SOURCE_ZIP" ]]; then
  args+=(--source-zip "$(realpath "$SOURCE_ZIP")")
fi

python "$SCRIPT_DIR/r402_validation_audit.py" "${args[@]}"
R402_PACKAGE_ROOT="$PACKAGE_ROOT" pytest -q "$DELIVERY_ROOT/tests"
