# Draft update queue — yang-md-decoupling-marl

草稿批次更新契约的实例。单一真源 = 各 feed 的 `Manuscript mapping` 段
(feed_check 强制存在)；本文件只持指针与已知冲突点，不复制 feed 结论。

## 状态

- 草稿批次更新只在批次节点执行：manuscript lane 轮 / manuscript-refresh /
  提交冻结（CLAUDE.md 手稿线生命周期）。
- **R473 统计口径需降级（外部深审 2026-08-23，`working/gpt_pro_r474_placebo_review_deep_20260823/01_R474_DEEP_REVIEW.md` F-04）**：
  R473 的 "Holm-controlled p=0.015625" 是零效应符号翻转检验；正确口径是
  直接材料性检验（H0: effect <= log(1.10)），R473 六个 critic 差值下
  p=2/64=0.03125 > 0.025 不通过。**论文中 18.8% 数字的 "Holm 控制材料性"
  措辞必须降级或等待 R475 结果**；R475（2026-08-23 启动，直接材料性 Holm
  口径）完成后按 R475 结果写入。
- **R474 abort（2026-08-23）**：外部深审证明 pi(i)=(i+2) 对角复制 P 违反
  守卫逐槽值池条件；R474 已关闭（零新鲜分片），R475 以行置换 P + 全新鲜
  2x2 + 直接材料性 Holm 重做（运行中）。
- 当前：R475 训练中（48 片，预计 2026-08-24 凌晨完成）；等批次节点一次性处理。
- 新增对照输入：GPT chat 审核解答（2026-08-22，`working/U1_U9_audited_solution_20260822.md`）
  逐条给出可写/禁止措辞；批次更新时对照其 U1/U4/U5/U6/U7/U8/U9 各节，
  尤其 U1 有限类不可行证书与 U7 的 pure-q^2 措辞边界。
- U1 升级（agent-results 包，2026-08-22）：精确有理支撑证书已本机复证
  （序列化 binary64 QY10 SOCP 的 t 下界 0.0599381277975427... > 0），
  稿中 U1 措辞可从此数值容差版本升级为严格证书版本。
- U2 边界（agent-results 包，2026-08-22，已对源码核实）：P 源读外生随机
  策略 donor 库、N 源读当前受控轨迹，边际审计仅覆盖 donor 库内部；
  R473 完成后的结论只能写「真实邻居源 vs 外生 donor 源的总算法效应」，
  不能写纯语义邻居信息效应（R473 feed 已按此措辞落地）。
- 待对照 feed（最新 → 旧）：R473, R469, R468, R467, R465, R464, R463 —
  逐条对照各自 `Manuscript mapping` 段。
- 已知冲突点：R464 (U1 Youla 证书) vs 草稿 §3.5 / §6.4 的「只有蓝图、
  没有证书」表述 — 批次更新时必须修订草稿这两处。

## 使用

- 批次更新时：逐条对照队列中 feed 的 Manuscript mapping 段，改完删除
  对应行。
- 新 feed 完成：只写 feed 的 Manuscript mapping 段；mapping 断言与草稿
  现有文字冲突时 feed 当场标 `CONFLICT`（历史 feed 不回填）。
