#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
ZIP="$ROOT/source_package/gpt_pro_math_pack_20260820.zip"
[[ -f "$ZIP" ]] || { echo "Missing bundled source ZIP: $ZIP" >&2; exit 2; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP/source"
"$HERE/run_all_checks.sh" "$TMP/source"
