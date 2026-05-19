---
round: R59
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R59 plan — PI Briefing Layer

**Date**: 2026-05-17
**Type**: infrastructure
**Wall budget**: ~1 hr

## Trigger

`/grill-with-docs` interview (2026-05-17 06:30) 揭出根因：

- 用户痛点不是术语听不懂，是**研究故事丢了**
- 用户自我定位是 "研究伙伴 / co-author"，**不是签字官**
- "AI 自治 + PI 参与" — AI 保留技术决策权，PI 通过简报"插一脚"
- "汇报很多" → 禁止加新文件；要在已有载体上加结构

完整设计 see `docs/adr/0003-pi-briefing-layer.md`.

## What changes

1. `memory/rounds/_TEMPLATE_VERDICT.md` 加第 4 mandatory section
   `## 给 PI 的话`，5 个固定子段
2. `memory/tools/validate.py`：R59+ verdict 强制含该段；soft-warn 超过 30 行
3. `memory/tools/render.py`：把最新 R59+ verdict 的该段抄到 STATE.md
   顶部新段 `## 给 PI 的简报（最新一轮）`；历史一句话归档到底部
   `## 历史简报`
4. `memory/glossary.yml` 新文件——项目术语 → 一句话定义
5. render.py 对简报做 first-use 内联注解（`LSTM(能记前几步的网络)`）
6. `CLAUDE.md` 加 agent 行为契约：写完 verdict 必须在 chat 复述简报
7. `CONTEXT.md` glossary 加三个新术语

## What does NOT change

- R01..R58 老 verdict 不强制回填（cutoff = R59）
- claim / question schema 不动
- handoffs 不动
- 现有 3 个 Q-section 不动

## Acceptance

- `python memory/tools/validate.py` 全绿（含本轮 R59 verdict）
- `python memory/tools/render.py` 输出 STATE.md 顶部含 `## 给 PI 的简报（最新一轮）`
- 简报里 LSTM/PI 简报 等术语在首次出现时被自动加注
- 本轮 R59 verdict.md 自带 `## 给 PI 的话` 段 — dogfood
- `pytest memory/tools/tests/test_validate.py memory/tools/tests/test_render.py` 全绿
- agent（即本会话）在写完 R59 verdict 后，在 chat 中复述 `## 给 PI 的话` 全文

## Risks

- 老 verdict 不回填 → STATE.md "历史简报" 段在 R59-R60 期间空
- glossary.yml 漂移：术语演进后定义可能过时
- chat 复述契约无 tooling 强制 → 全靠 CLAUDE.md 文字约束 + agent 自律
