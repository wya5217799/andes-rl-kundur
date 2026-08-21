# U1–U9 真实性补证数据请求包

## 结论

现有解答的**数学恒等式、反例和条件性命题**大多不需要新增数据才能成立；真正缺少的是把这些命题绑定到本项目具体对象、给出数值证书、并允许第三方独立复算的证据。

补证应分为四个层级：

1. **可追溯**：代码版本、环境、随机种子、命令、输入输出哈希完整；
2. **可复算**：从原始矩阵/轨迹而非摘要标量重算每个结论；
3. **可证伪**：每个命题都有明确支持、反驳和停止分支；
4. **不过度外推**：线性、局部、有限库、固定算法、分布性和部署性结论严格分开。

最关键的新增内容不是九套独立数据，而是七个共享证据包：

- `WP0`：全局可复现与来源证明；
- `WP1`：Object A / Object B 完整模型、单位、控制器、headroom 与 profile 协议导出；
- `WP2`：U1 FIR-Youla/SLS 原始—对偶证书；
- `WP3`：U3/U4 原始执行轨迹、Bellman 语义和 exact guard 重算；
- `WP4`：U5–U8 导数、分数延迟、二阶 tensor、共差模条件数计算；
- `WP5`：U2 新的 `3×3×2` 因果实验；
- `WP6`：冻结执行 R458，并在需要概率结论时另做独立分布性 successor。

其中 `WP1` 一次完成后可同时补齐 U1、U5、U6、U7、U8 的大部分缺口。

## 文件说明

- `01_codex_master_task.md`：可直接交给 Codex 的总任务书。
- `02_data_requirements_by_bundle.md`：按共享工作包列出必须产生的数据、用途和最小/完整版本。
- `03_u1_u9_requirement_matrix.md`：逐项说明 U1–U9 还缺什么、什么数据能升级什么结论。
- `04_output_tree_and_schemas.md`：建议目录、文件名、字段和数组维数。
- `05_acceptance_tests_and_stop_rules.md`：机械验收门槛、失败分支和禁止补写规则。
- `06_claim_upgrade_and_limit_matrix.md`：补证后允许写到什么强度，仍禁止写什么。
- `07_execution_order_checklist.md`：Codex 执行顺序和交付检查表。
- `templates/`：manifest、claim-evidence map 和逐步轨迹格式模板。

## 最高优先级

按论文可信度收益排序：

1. `WP0 + WP1`：没有完整模型与 provenance，后续数值均无法独立审计；
2. `WP3-U3`：先确认 raw/executed action 与 replay/target 一致，否则 U2 新训练仍会被污染；
3. `WP2-U1`：产生命名控制器类的可行 witness 或正对偶下界；
4. `WP4-U7/U8`：把“零一阶 authority”和“异质性不等于 cross energy”变成项目数值结果；
5. 冻结执行 `R458`；
6. 最后运行高成本 `U2` factorial。

## 不能被新增数据自动解决的边界

- U2 的有限预算实验最多识别**该算法、架构、预算和 bank 下的消息语义效应**。除非另有神经网络全局优化下界或收敛证书，不能把它升级为总体 `I*`。
- U9 的四个固定 eval profiles 只能给 finite-bank witness。要估计 transfer probability，必须另行声明 profile generator 并独立抽样。
- U1 的证书只覆盖封存的 FIR 类、模型、窗口、bank、系数 bound 和 active mode，不覆盖“所有控制器”。
- 非线性/HIL/EMT/部署安全需要新的对象级验证，不由局部 LTI 或有限轨迹自动推出。
