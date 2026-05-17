# R59 verdict — PI Briefing Layer

**Date**: 2026-05-17
**Status**: **COMPLETE**
**Type**: infrastructure
**Wall**: ~1 hr

## TL;DR

R59 加了一层 PI Briefing Layer：verdict.md 第 4 个 mandatory section
`## 给 PI 的话`（R≥59 强制），soft cap ≤ 30 行；validate.py 强制存
在 + warn 超长；render.py 把最新 R≥59 briefing 抄到 STATE.md 顶部新
段 `## 给 PI 的简报（最新一轮）`，并按 `memory/glossary.yml` 做 first-use
内联术语注解；CLAUDE.md 加 agent chat-delivery 契约（写完 verdict
必须在 chat 复述简报全文）。设计动因：2026-05-17 `/grill-with-docs`
session 揭出用户不要决策权要参与感。完整设计 see ADR-0003。

## Trigger

用户 2026-05-17 `/grill-with-docs` interview 中说"项目给我的汇报很多
我听不懂"。grilling 6 个回合后定位根因不是术语而是**研究故事丢了**。
用户的运营级原话："我很多时候懒得决策，关键是我要理解，研究时我要有
参与感，ai很多时候比我更懂技术。"

## What changed (file-by-file)

- `memory/rounds/_TEMPLATE_VERDICT.md` — 加第 4 mandatory section + 5 子段
- `memory/tools/validate.py` — `PI_BRIEFING_CUTOFF=59` + `PI_BRIEFING_LINE_CAP=30`；
  `validate_verdict_structure` 对 R≥59 强制；`_warn_pi_briefing_length` soft warn
- `memory/tools/render.py` — `_extract_pi_briefing` + `_extract_pi_briefing_headline` +
  `_load_glossary` + `_annotate_first_use`；新顶部段 `## 给 PI 的简报（最新一轮）`，
  新底部段 `## 历史简报`（最多 5 行）
- `memory/glossary.yml` — 新文件，13 个种子术语
- `memory/tools/tests/test_validate.py` — 7 个新测试（cutoff / 长度 cap / round-num parse）
- `memory/tools/tests/test_render.py` — 8 个新测试（抽取 / 历史 / glossary first-use /
  Chinese-embedded 边界 / 长短语优先 / no-glossary fallback）
- `CLAUDE.md` — 加 Round verdict contract 第 4 行 + Agent chat-delivery contract 段
- `CONTEXT.md` — 加 3 个 glossary 条目（PI 简报 / 术语速查 / AI 自治 vs PI 参与）
- `docs/adr/0003-pi-briefing-layer.md` — 新 ADR
- `memory/rounds/R59/plan.md` + `verdict.md` — round 自身

## Verification

- `pytest memory/tools/tests/test_validate.py memory/tools/tests/test_render.py`
  → **73 passed**（含 15 个新测试）
- `python memory/tools/validate.py` → **OK: 67 claims, 7 questions, 37 warnings**
  （0 errors；37 warnings 全是 R01–R58 的预存 soft 提示，无新 R59 issue）
- 本 verdict 自身有 `## 给 PI 的话` 段 ≤ 30 非空行 — dogfood pass

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：把你"汇报听不懂"的吐槽变成了基础设施——verdict 加了一个
强制段 `## 给 PI 的话`，render 时自动把最新一轮的内容抄到 STATE.md 顶
部，并对像 LSTM、HAWE 这种术语**首次出现**自动加一句解释。从 R59 起
生效，老轮次不动。

**结果（一句话）**：73 个测试全绿；STATE.md 顶部现在第一眼就是"给 PI
的简报"，不再让你去翻 verdict.md。

**意外**：grilling 中你说"懒得决策、要参与感"那句把整个药方掀翻了——
原本我以为要做"PI 决策队列"，结果发现你要的是**研究伙伴体验**。所以
默认行为变成"AI 自治 + 沉默 = 默认走"，你想插一脚才需要说话。

**我默认下一步做**：让你试用一段时间。下一轮（R60+）开始我会按这个新
契约写简报。如果术语速查有词没收录，我加进 `memory/glossary.yml`。

**你想插一脚就说**：现在就有几件事可以挑——(1) 5 个子段是否够、要不要
增减；(2) 30 行 soft cap 是否合适；(3) glossary 第一批 13 个术语想加
减谁。沉默 = 这套契约就这么用。
