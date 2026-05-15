# results/ Manifest

This directory is gitignored except for `whitelist/` (paper-cited checkpoints
and eval JSON) and this manifest itself.

## Why

Training artifacts can reach GB scale per round. Storing everything in git would
bloat the repo and slow clones. The whitelist contains only what the paper
directly cites; everything else is local-only.

## How to bring local artifacts in

Sibling local directory (not committed) contains the full training results.
Symlink or copy as needed:

```powershell
# Example: bring R21 best.pt from the source repo
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\results"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\results"
Copy-Item "$SRC\<run_dir>\best.pt" "$DST\<run_dir>\"
```

## Whitelist contents

| Path | Source | Cited by | Notes |
|------|--------|----------|-------|
| `whitelist/andes_paper_alignment_6axis_2026-05-07.json` | r30 ranker fix re-rank | paper §V-A, §V-B | post-fix headline ranking (CLM ledger source) |

(Update this table when adding files to whitelist/.)

## What is NOT in whitelist

- Per-step trajectory dumps from training runs
- Per-seed full result trees (e.g., `andes_dfloor_seed42/`)
- Intermediate ensemble eval JSON files
- Smoke test logs

These are reproducible from the code in this repo + the artifacts in the source
repo. If a future paper or revision needs to cite them, add to whitelist.
