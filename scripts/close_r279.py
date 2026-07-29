#!/usr/bin/env python3
# ruff: noqa: E402
"""Close R279 from the immutable formal summary and ledger contracts."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from andes_rl_kundur.evaluation.sealed_bank import canonical_json_bytes, sha256_bytes, sha256_file

SUMMARY = ROOT / "results/r279_formal_evaluation/formal_summary.json"
PROVENANCE = ROOT / "results/r279_formal_evaluation/provenance.json"
CLAIM = ROOT / "memory/claims/CLM-0605.md"
QUESTION = ROOT / "memory/questions/Q-0041.md"
VERDICT = ROOT / "memory/rounds/R279/verdict.md"
CLOSURE = ROOT / "results/r279_formal_evaluation/closure_provenance.json"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
PI_HEADER = "## 给 PI 的话"
PRIMARY = ("normalized_sync_loss_hz2", "fast_inter_area_iae_hz_s")

def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object: {path}")
    return payload

def _effect_h(summary: dict[str, Any], contrast: str, endpoint: str) -> tuple[float, list[float]]:
    row = summary["hierarchical_bootstrap"][contrast][endpoint]["ratio_of_means_percent"]
    return float(row["point"]), [float(x) for x in row["percentile_95_interval"]]

def _effect_p(summary: dict[str, Any], endpoint: str) -> tuple[float, list[float]]:
    row = summary["paired_bootstrap"]["causal_vs_q0"]["endpoints"][endpoint]["ratio_of_means_percent"]
    return float(row["point"]), [float(x) for x in row["percentile_95_interval"]]

def _fmt(effect: tuple[float, list[float]]) -> str:
    point, interval = effect
    return f"{point:+.6f}% [{interval[0]:+.6f}%, {interval[1]:+.6f}%]"

def _question_status(classification: str) -> str:
    if classification in {"MARL-IDENTIFIABLE-POSITIVE", "CAUSAL-EXPLANATION-SUFFICIENT", "CENTRALIZED-EXPLANATION-SUFFICIENT"}:
        return "closed-positive"
    if classification in {"LEARNED-VALUE-NOT-MARL-IDENTIFIABLE", "INVALID"}:
        return "closed-partial"
    return "closed-negative"

def _write_question(classification: str) -> None:
    text = QUESTION.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("Q-0041 frontmatter missing")
    meta = yaml.safe_load(match.group(1)) or {}
    meta.update({"status": _question_status(classification), "opened_round": "R279", "closed_round": "R279", "closed_by": "CLM-0605"})
    body = match.group(2).rstrip() + f"\n\n- Closed by CLM-0605 after the sealed fresh-bank result: `{classification}`.\n"
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    QUESTION.write_text(f"---\n{dumped}\n---\n{body}", encoding="utf-8")

def _claim_statement(summary: dict[str, Any]) -> str:
    classification = summary["decision"]["classification"]
    n = summary["completion"]["observed_complete"]
    lines = [
        f"R279 closes the reviewer-identifiability experiment as {classification}.",
        f"All {n} frozen fresh-bank controller trajectories were analysed across q=0, one causal comparator, three centralized TD3 seeds, and three parameter-shared TD3 seeds; no seed selection was performed.",
    ]
    for endpoint in PRIMARY:
        lines.append(f"For {endpoint}, causal vs q=0 was {_fmt(_effect_p(summary, endpoint))}; shared vs q=0 was {_fmt(_effect_h(summary, 'shared_vs_q0', endpoint))}; shared vs causal was {_fmt(_effect_h(summary, 'shared_vs_causal', endpoint))}; shared vs centralized was {_fmt(_effect_h(summary, 'shared_vs_centralized', endpoint))}.")
    guards = summary["decision"]["validity_guards"]
    lines.append("Formal validity guards: " + ", ".join(f"{name}={value}" for name, value in guards.items()) + ".")
    lines.append("This result answers Q-0041 only; it does not relabel R278, authorize HAWE, or modify the ICEMS manuscript.")
    return "\n\n".join(lines)

def _write_claim(summary: dict[str, Any]) -> None:
    classification = summary["decision"]["classification"]
    meta = {
        "id": "CLM-0605", "type": "finding", "trust": "V", "status": "current",
        "statement": _claim_statement(summary), "round": "R279",
        "provenance": [
            "memory/rounds/R279/plan.md", "memory/rounds/R279/formal_seal.json",
            "results/r279_causal_guard/causal_guard_summary.json", "results/r279_matched_training/training_matrix_summary.json",
            "results/r279_fresh_bank/screen_summary.json", "results/r279_fresh_bank/formal_bank.json",
            "results/r279_formal_evaluation/formal_summary.json", "results/r279_formal_evaluation/provenance.json",
            "memory/rounds/R279/verdict.md",
        ],
        "tags": ["r279", "q0041", "reviewer-identifiability", "fresh-bank", "multi-seed", classification.lower()],
        "closes_question": ["Q-0041"],
    }
    CLAIM.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=88).strip() + "\n---\n", encoding="utf-8")

def _pi_body(summary: dict[str, Any]) -> str:
    classification = summary["decision"]["classification"]
    sync = _fmt(_effect_h(summary, "shared_vs_q0", PRIMARY[0]))
    inter = _fmt(_effect_h(summary, "shared_vs_q0", PRIMARY[1]))
    reason = summary["decision"]["reason"]
    return "\n\n".join([
        "**这一轮干了什么**：我没有继续挑幸运种子，而是把简单因果反馈、几乎同参数量的集中式 TD3、参数共享 TD3 放进同一个冻结实验里；三种新种子全部保留，控制器冻结后才生成并筛选全新的扰动库。",
        f"**结果（一句话）**：正式分类是 **{classification}**。共享 TD3 相对 q=0 的同步损失结果为 {sync}，前三秒区域间 IAE 为 {inter}；判定理由是：{reason}。",
        "**这意味着什么**：这轮回答的是‘过去看到的提升到底是不是 MARL 特有’。无论结果正负，都不能再用 seed 49 或 HAWE 包装结论；必须以因果基线、集中式基线和三种子 fresh-bank 证据为准。",
        "**默认下一步**：先停实验，保持论文文件不动。下一次只根据这个正式分类调整论文叙事和图表，不再改奖励、网络、动作幅值或基线来补救结果。",
    ])

def _write_verdict(summary: dict[str, Any]) -> str:
    classification = summary["decision"]["classification"]
    rows = []
    for endpoint in PRIMARY:
        rows.append(f"| `{endpoint}` | `{_fmt(_effect_p(summary, endpoint))}` | `{_fmt(_effect_h(summary, 'shared_vs_q0', endpoint))}` | `{_fmt(_effect_h(summary, 'shared_vs_causal', endpoint))}` | `{_fmt(_effect_h(summary, 'shared_vs_centralized', endpoint))}` |")
    pi = _pi_body(summary)
    text = f"""# R279 verdict — reviewer-driven MARL identifiability

**Status**: COMPLETED — `{classification}`
**Claim**: CLM-0605
**Question**: Q-0041

## TL;DR

{summary['decision']['reason']}. The prospective analysis used every frozen seed and fresh-bank case, with no seed or checkpoint selection.

## Measured result

| Endpoint | Causal vs q=0 | Shared vs q=0 | Shared vs causal | Shared vs centralized |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

Completed trajectories: {summary['completion']['observed_complete']} / {summary['completion']['expected']}. Classification: `{classification}`.

## Interpretation

The experiment distinguishes physical feedback value, centralized learned value, and parameter-sharing-specific value under one matched action and information contract. R278 remains a historical `PILOT-NO-GO`; R279 does not rescue or relabel it.

## Questions opened (this round)

- None.

## Questions closed (this round)

- Q-0041 — `{_question_status(classification)}` by CLM-0605 as `{classification}`.

## Questions advanced (this round, status unchanged)

- None.

## Verification

- Formal summary SHA-256: `{sha256_file(SUMMARY)}`
- Formal provenance SHA-256: `{sha256_file(PROVENANCE)}`
- Formal seal SHA-256: `{summary['formal_seal_sha256']}`
- Fresh formal bank SHA-256: `{summary['formal_bank_sha256']}`

{PI_HEADER}

{pi}
"""
    VERDICT.write_text(text, encoding="utf-8")
    return pi

def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)

def main() -> None:
    if CLOSURE.exists() and VERDICT.exists():
        print("R279 closure already complete; refusing to overwrite immutable closure.")
        return
    if VERDICT.exists():
        raise FileExistsError("R279 verdict already exists without closure provenance")
    summary = _load(SUMMARY)
    if summary.get("round") != "R279" or summary.get("phase") != "fresh-bank-eight-arm-formal":
        raise ValueError("not the R279 formal summary")
    if sha256_file(PROVENANCE) == "":
        raise ValueError("formal provenance missing")
    classification = summary["decision"]["classification"]
    _write_claim(summary)
    _write_question(classification)
    pi = _write_verdict(summary)
    _run("memory/tools/validate.py")
    _run("memory/tools/dual_metric_lint.py", "--claim", "CLM-0605")
    _run("memory/tools/close_round.py", "R279", "completed")
    _run("memory/tools/render.py")
    _run("memory/tools/validate.py")
    closure = {
        "schema_version": 1, "round": "R279", "classification": classification,
        "formal_summary_sha256": sha256_file(SUMMARY), "formal_provenance_sha256": sha256_file(PROVENANCE),
        "claim_sha256": sha256_file(CLAIM), "question_sha256": sha256_file(QUESTION),
        "verdict_sha256": sha256_file(VERDICT), "state_sha256": sha256_file(ROOT / "memory/STATE.md"),
        "paper_files_modified": False, "pi_briefing": pi,
    }
    data = canonical_json_bytes(closure)
    CLOSURE.write_bytes(data)
    digest = sha256_bytes(data)
    CLOSURE.with_name(CLOSURE.name + ".sha256").write_text(f"{digest}  {CLOSURE.name}\n", encoding="utf-8")
    print(f"[closed] R279 classification={classification} closure_sha256={digest}")
    print("\n" + pi)

if __name__ == "__main__":
    main()
