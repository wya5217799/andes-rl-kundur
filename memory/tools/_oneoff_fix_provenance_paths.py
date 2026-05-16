"""One-off: rewrite stale provenance paths in CLM frontmatter.

Maps known path migrations from pre-R37 src-layout and Codex R45
archive moves. Idempotent: a second run produces no diff. Delete
after R53 lands.
"""
import re
from pathlib import Path

MAPPING = {
    # pre-R37 src-layout
    "env/andes/": "src/andes_rl_kundur/env/andes/",
    "evaluation/paper_grade_axes.py": "src/andes_rl_kundur/evaluation/paper_grade_axes.py",
    "probes/andes_common/": "src/andes_rl_kundur/probes/andes_common/",
    "config.py": "src/andes_rl_kundur/config.py",
    # paper / dissertation moves to artifacts/
    "paper/main.tex": "artifacts/paper/main.tex",
    "paper/figures/": "artifacts/paper/figures/",
    "dissertation/main.tex": "artifacts/dissertation/main.tex",
    # Codex R45 archive
    "scripts/_r38_score_td3_sweep.py": "scripts/_archive/round_scripts/_r38_score_td3_sweep.py",
    "scripts/_r40_score_phi_zero_sweep.py": "scripts/_archive/round_scripts/_r40_score_phi_zero_sweep.py",
    "scripts/_r41_score_A_sac_phi0.py": "scripts/_archive/round_scripts/_r41_score_A_sac_phi0.py",
    "scripts/_r41_score_B_normalized.py": "scripts/_archive/round_scripts/_r41_score_B_normalized.py",
    "scripts/_r41_score_C_td3_200ep.py": "scripts/_archive/round_scripts/_r41_score_C_td3_200ep.py",
    "scripts/_r42_score_alpha_sac_norm.py": "scripts/_archive/round_scripts/_r42_score_alpha_sac_norm.py",
    "scripts/research_loop/eval_v4_ensemble.py": "scripts/eval_ensemble.py",
}

ROOT = Path(__file__).resolve().parents[2]
total = 0
for f in sorted((ROOT / "memory" / "claims").glob("CLM-*.md")):
    text = f.read_text(encoding="utf-8")
    new = text
    for old_p, new_p in MAPPING.items():
        # Match path-as-list-item (leading "- " or "- " with whitespace)
        new = re.sub(rf"(- ){re.escape(old_p)}", rf"\1{new_p}", new)
    if new != text:
        f.write_text(new, encoding="utf-8")
        total += 1
        print(f"rewrote {f.name}")
print(f"\ntotal: {total} files rewritten")
