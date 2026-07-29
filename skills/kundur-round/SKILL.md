---
name: kundur-round
description: andes-rl-kundur 仓库流程 canonical — 一轮研究从选题到 PI
  交付的完整步骤、feed 契约、护栏。仓库内会话经 CLAUDE.md 指针到达;
  不进全局技能目录。
---

# Kundur Round — 仓库流程 canonical

本文件是 andes-rl-kundur 研究流程的唯一过程真源。仓库事实（schema、
工具目录、代码约定、模板）留在 CLAUDE.md 与各模板文件，本文件只持
**过程**并用指针取细节。仓库根: `C:\Users\27443\Desktop\andes-rl-kundur`。

词汇: **round** = 一次可证伪调查 (plan + verdict); **feed** = 实验实质
的唯一完整写处; **ledger** = claims / questions / rounds 骨架三件套。

## 1. 会话启动 (步骤)

1. 读 `memory/RESEARCH_PROGRAM.md`、`memory/STATE.md`、`CLAUDE.md`。
2. `python memory/tools/research_goal.py --json`。
3. 报 active round → 先 resume 并闭环它，再领新轮; 报 ready goal →
   用它的原文 objective / required_reading / scope_limits / verification /
   stop_when, 不改写。

完成判据: 能说出当前唯一 active question id, 或 "队列空"。

## 2. Round 生命周期 (步骤)

1. **领号**: `reserve_round.py --strict-no-active`; 收尾前
   `reserve_claim.py --round R<N>` — claim id 必须先于 feed 存在
   (feed 内联数字要挂它)。ID 永不手挑。
2. **plan**: `memory/rounds/R<N>/plan.md` — 冻结契约 (什么变/什么固定)、
   预注册判定树、scope_limits、资产保护清单。caveman Chinese。
3. **preflight**: `python memory/tools/round_preflight.py R<N>` —
   exit 2 = BLOCK, 修完再跑。
4. **执行**: 影响结论的识别/筛选/判定逻辑全部进 `probes/`; 可复用
   implementation 进 `src/andes_rl_kundur/`, `scripts/` 只做稳定 execution
   adapter (完整 seam 与 lifecycle 见 `docs/repo-hygiene/executables.md`);
   正式评估 seal-before-trace、产物不可变、逐文件 .sha256。
   ANDES 只能 WSL: `MSYS_NO_PATHCONV=1 wsl /home/wya/andes_venv/bin/python`。
5. **收尾** (严格顺序):
   a. feed (契约见 §3)
   b. claim 注册卡 (形态见 CLAUDE.md "写 claim 的时机与形态")
   c. verdict 骨架 (模板 `memory/rounds/_TEMPLATE_VERDICT.md`)
   d. programme 问题若关闭: 块归档 `memory/RESEARCH_PROGRAM_CLOSED.md`,
      `priority_questions` 回 []
   e. `close_round.py R<N> completed`
   f. `validate.py` 绿 → `render.py` → `"$DAIMON_USER_PYTHON" -m pytest tests -q` 绿
   g. **给 PI 的话原文贴进对话** (ADR-0003); 指向文件不算交付

完成判据: validate 绿、round state=completed、PI 话已出现在对话里、
无事实同时住在两个 ledger 家里。

## 3. Feed 契约 (参考)

feed 是原料, 供后续起草会话翻成论文正文; 人类可读性不在目标内。
一切规则服务一个性质: 起草者两跳取到任何事实 (report → pointer →
source), 且任何事实不遇见第二遍。

### 单一真源分配表

每个实验事实只住一个家, 别处一律指针:

| 家 | 放 | 不放 |
|---|---|---|
| results JSON / traces | 全部测量数字、守卫行、哈希 | 解释 |
| **feed** | 解释、有界结论、手稿映射、头条数字 (每个挂 claim id) | 数据表、守卫明细、逐格转储 |
| claim 卡 | 分类判定 + 主头条数字对 + 范围短语 + provenance 指针 | 每级表格、位置子表、守卫细节 |
| verdict.md | 骨架: Status 行、TL;DR ≤3 句、3 个 Q 节、给 PI 的话 + feed 指针 | 分析、数字表 |
| STATE.md | 无 — render.py 自动渲染, 永不手改 | — |

论文要引的数字设计内存两份 (results 为源, feed 为取料面); 第三份是
fork, 删掉。

### 位置与语言

- 有手稿线: `paper/<line>/reports/<slug>.md` (当前线
  `paper/sci_upgrade_survey/reports/`); 无手稿线: `results/<run>/FEED.md`。
- 英文 (喂英文论文); 用户显式语言要求优先。

### 节契约 (按序)

1. **Identity** — round/claim id、日期、commit、脚本、seal/合约哈希。
   完成判据: 每个路径在盘上可解。
2. **Frozen setup** — 什么固定什么变, 指契约文件; ≤5 行。
3. **Observations** — 每条一个子弹: 解释过的发现 + 指针
   (`path:line` / JSON 字段 / claim id)。内联只允许论文会引的头条
   数字, 且每个挂 claim id; 其余数据留在 results 文件里被指。
4. **Conclusions** — 有界陈述, 每条标证据等级 (analytic > linearized
   small-signal > sealed-bank time-domain > self-evaluated); 措辞强度
   不越级。
5. **Limits** — 范围正面陈述 ("covers X only; Y untested"), 含每个
   预注册失败 flag。
6. **Manuscript mapping** — 每条 observation 映射到目标节/图, 或给
   明确 stay-out 理由。
7. **Open threads** (可选, 最后) — 每个标 resolved-by / pending /
   unauthorized; 被后续轮关闭时回改旧报告该行为删除线+指针, 不删行。

### 规则

- 指针优先: 事实已住在 claim / verdict / results 里就指, 重述即 fork。
- 写陈述不写叙述: 无动机散文、无过渡、无简报腔。
- 密度帽两页; 超了说明抄了数据, 回到指针。

### 完成判据

每个路径可解、每个内联数字挂 claim id、每条 observation 有手稿映射或
stay-out、任何数据两跳可达、feed 里没有任何事实被 claim 卡或 verdict
正文重述。

## 4. 护栏 (硬; 操作清单 — rationale 各见其源)

- 先 probe 后训练; 用 kill/pivot 门避免纯算力搜索 (政策:
  `memory/RESEARCH_PROGRAM.md` "Autonomous research policy" / "Kill and
  pivot rules")。
- 固定拓扑上不追 algorithm-only SOTA (R86 结构性 plateau, CLM-0148/0149)。
- paper-cited 资产 (`base_env.py`、`andes_vsg_env_v4.py`、`train.py`、
  `paper_grade_axes.py`) 只在新 round + claim 里改 (原则:
  CLAUDE.md 工程原则 3)。
- baseline 只用 `baselines.py` 查 measured, 不估 (原则: CLAUDE.md
  工程原则 2)。
- 单机最多 3 个并行 WSL python (约定: CLAUDE.md 代码约定)。
- 语言: plan/verdict 用 caveman Chinese; question/claim/feed 用英文;
  PI 话中文五小段 ≤30 行 (模板: `memory/rounds/_TEMPLATE_VERDICT.md`)。

## 5. 手稿线 (参考)

做 SCI 线的任何稿子工作 (手稿、修订、补实验、投稿) 先读
`paper/sci_upgrade_survey/LINE.md` — 锁定决策、措辞红线、资产指针。
新手稿线注册到 `RESEARCH_PROGRAM.md` 的 `## Manuscript lines`。

## 指针 (仓库文件, 各持其事实)

- `CLAUDE.md` — 工程原则、memory schema、ledger 形态规则、工具目录、
  代码约定
- `memory/rounds/_TEMPLATE_VERDICT.md` — verdict 骨架模板 (validate.py
  强制节)
- `memory/tools/*.py` — 自文档 (docstring 含 motivation/usage/失败模式)
- `paper/sci_upgrade_survey/LINE.md` — 当前手稿线状态
