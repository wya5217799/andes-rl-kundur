# R386 verdict -- clean four-REGCV1 object passes

**Date**: 2026-08-14
**Status**: completed -- `REGCV1-CLEAN-INIT-PASS`
**Type**: experiment
**Wall**: 0.38 s formal execution; one valid zero-input trajectory

## TL;DR

R386 corrects only the source capture timing and validly passes every frozen
structural-absence, mapping, initialization-reference, native solver,
diagnostic, finite-value, and short zero-input drift guard. It opens only a
new signed dynamic Pref/Qref authority gate; training remains prohibited.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0105 closed positive by CLM-1075.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R386.md`

## Technical disposition

- Exact packaged static data and unchanged Kundur connectivity are retained.
- Four REGCV1 devices map one-to-one to the four static generators; all legacy
  dynamic/event objects and forbidden DAE names are structurally absent.
- Correctly timed static `p/q` rows exactly match post-init `Pref/Qref`.
- Native initialization and 0.2-s zero-input TDS complete with zero bad
  initialization residuals, finite values, and drift below native tolerance.
- No perturbation, controller, reward, or training occurs. The next gate
  requires separate prospective registration.

## 给 PI 的话

**发生了什么**：我们只修正了读取基准数值的时刻，没有改变网络、设备参数或判定标准。修正后，四台新设备都能正确接入并完成初始化，短时无扰动运行也全部通过检查。

**这说明什么**：现在可以确认，这套设备建模方案本身能够在原有网络上成立，之前的问题来自旧设备残留和取值时序，而不是必须更换平台或拓扑。但是这还没有证明设备接受指令后能按方向和幅度改变实际功率。

**下一步做什么**：另开一轮很小的指令响应实验，分别轻微改变每台设备的两类指令，检查实际功率方向、设备归属和相互干扰。通过之前不做控制器比较，也不开始训练。
