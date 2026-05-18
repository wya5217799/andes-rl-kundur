"""AndesMultiVSGEnvV5 — V4 + REGCA1 plant 风机 (R80+, ADR-0004).

V5 是 V4 的子类, 仅 plant 风机模型不同:

- **V4 plant**: G4 用 GENROU + ZERO_G4_INERTIA hack (M=0.1, D=0) 当低惯量
  风机, W2 用 GENCLS M=0.1 当 100 MW 风电场.
- **V5 plant** (cfg.wind_model="regca1", V5 default):
    - G4: 整条链 (GENROU + IEEEG1 + EXST1 + TGOV1 + EXDC2) u=0 disable,
      attach ANDES REGCA1 + REECA1 到 Bus 4 (G4 grid-side PV slot).
    - W2: 跳过 V4 的 GENCLS WF2, 直接 attach REGCA1 + REECA1 到 Bus 8.

V5 fallback (cfg.wind_model="gencls") 走 V4 的 _build_system, 用于
sanity check (V5 scaffold 没污染 V4 plant). 这条退路应该跟 V4 env
bit-identical (模 1e-9).

控制对象 (4 ESS VSG @ Bus 12/16/14/15) 和 reward / action / R58 audit
全部从 V4Config 继承不变. V5 只动 plant.

Framing 是 paper-deviation. 详 docs/adr/0004-v5-env-regca1-plant-paper-deviation.md
和 docs/adr/0005-andes-only-drop-simulink-1to1.md.
"""
from __future__ import annotations

import andes
import numpy as np

from .andes_vsg_env_v4 import AndesMultiVSGEnvV4
from .v5_config import V5Config


# ANDES kundur_full.xlsx 里 G4 在 bus 4, GENROU idx=4. 这是 ANDES case
# 编号, 不是 paper Fig.3 拓扑图的 "bus 11". V4 env 同样用 idx=4 直接
# 操作 G4 (CLM-0040 ZERO_G4_INERTIA path).
G4_BUS_ANDES: int = 4
G4_GENROU_IDX: int = 4


class AndesMultiVSGEnvV5(AndesMultiVSGEnvV4):
    """V4 + plant 风机升级到 ANDES REGCA1 (R80+).

    V5 仅 override ``_pre_setup_addons`` 和 ``_build_system`` 中的 plant
    风机部分. 控制对象 / reward / action / obs 全跟 V4 一样.
    """

    def __init__(
        self,
        random_disturbance: bool = True,
        comm_fail_prob: float | None = None,
        *,
        config: V5Config | None = None,
        comm_delay_steps: int = 0,
        forced_link_failures=None,
    ):
        cfg = config or V5Config.v5_default()
        if not isinstance(cfg, V5Config):
            raise TypeError(
                f"AndesMultiVSGEnvV5 requires V5Config, got {type(cfg).__name__}. "
                f"V5Config 继承 V4Config 加 wind_model knob."
            )
        # V4 __init__ 接受 V4Config; V5Config is-a V4Config 走得通,
        # V4 只读 V4 字段, V5 字段我们自己读.
        super().__init__(
            random_disturbance=random_disturbance,
            comm_fail_prob=comm_fail_prob,
            config=cfg,
            comm_delay_steps=comm_delay_steps,
            forced_link_failures=forced_link_failures,
        )
        self.config: V5Config = cfg  # type narrowing

    # ─── Override: G4 governor/AVR 跳过 if wind_model=="regca1" ───────

    def _pre_setup_addons(self, ss) -> None:
        """V5: 给 4 GENROU 加 IEEEG1+EXST1, 但跳过 G4 (idx=4) 若 wind_model=regca1.

        V4 给所有 4 个 GENROU 都装 IEEEG1+EXST1. V5 在 REGCA1 模式下 G4
        GENROU 会被 disable, 不应该再给它装 governor/AVR (装了也马上 u=0).
        gencls fallback 模式跟 V4 完全一样.
        """
        assert len(ss.GENROU.idx.v) > 0, (
            "GENROU idx not populated pre-setup; "
            "andes.load(setup=False) API likely changed."
        )
        skip_g4_gov = (self.config.wind_model == "regca1")
        for syn_idx in ss.GENROU.idx.v:
            if skip_g4_gov and syn_idx == G4_GENROU_IDX:
                continue
            ss.IEEEG1.add(idx=f"GOV_{syn_idx}", syn=syn_idx)
            ss.EXST1.add(idx=f"AVR_{syn_idx}", syn=syn_idx)

    # ─── Override: _build_system 走 REGCA1 路径 ──────────────────────

    def _build_system_w2_only(self):
        """V5 cycle 3c GREEN: W2 GENCLS → REGCA1+REECA1, G4 保留 V4 hack.

        和 V4 _build_system 区别只有一处: W2 (Bus 8) 不再 add GENCLS M=0.1,
        改 add REGCA1 "WF2_R" + REECA1 "WF2_E". G4 整条链 (GENROU + IEEEG1
        + EXST1 + TGOV1 + EXDC2) 跟 V4 一样 + ZERO_G4_INERTIA hack 把 G4
        GENROU M/D 调零. 详见 v5_config.V5Config.v5_default() docstring.
        """
        ss = andes.load(self.case_path, default_config=True, setup=False)
        self._g4_genrou_idx = G4_GENROU_IDX

        for new_bus in self.VSG_BUSES:
            if new_bus not in list(ss.Bus.idx.v):
                ss.add("Bus", {
                    "idx": new_bus, "name": f"Bus{new_bus}",
                    "Vn": self.NEW_BUS_VN,
                    "v0": 1.0, "a0": 0.0,
                    "area": 1 if new_bus in (12, 16) else 2,
                })
        for new_bus, parent_bus in self.NEW_BUS_CONNECTIONS.items():
            ss.add("Line", {
                "idx": f"Line_{parent_bus}_{new_bus}",
                "bus1": parent_bus, "bus2": new_bus,
                "Vn1": self.NEW_BUS_VN, "Vn2": self.NEW_BUS_VN,
                "r": self.NEW_LINE_R, "x": self.NEW_LINE_X, "b": self.NEW_LINE_B,
            })
        for load_bus, load_params in self.NEW_LOADS.items():
            ss.add("PQ", {
                "idx": f"PQ_Bus{load_bus}", "bus": load_bus,
                "Vn": self.NEW_BUS_VN,
                "p0": load_params["p0"], "q0": load_params["q0"],
            })

        self.vsg_idx = []
        for i, bus in enumerate(self.VSG_BUSES):
            vsg_id = f"VSG_{i+1}"
            gen_id = f"SG_VSG_{i+1}"
            ss.add("PV", {
                "idx": gen_id, "name": f"VSG{i+1}", "bus": bus,
                "Vn": self.NEW_BUS_VN, "Sn": self.VSG_SN,
                "p0": 0.5, "q0": 0.0,
                "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
            })
            ss.add("GENCLS", {
                "idx": vsg_id, "bus": bus, "gen": gen_id,
                "Vn": self.NEW_BUS_VN, "Sn": self.VSG_SN,
                "M": self.M0[i], "D": self.D0[i],
                "ra": 0.001, "xd1": 0.15,
            })
            self.vsg_idx.append(vsg_id)

        # ─── W2 plant: GENCLS → REGCA1+REECA1 (V5 唯一物理改动) ────────
        ss.add("PV", {
            "idx": "SG_WF2", "name": "WF2_Bus8", "bus": self.WF2_BUS,
            "Vn": self.NEW_BUS_VN, "Sn": self.WF2_SN,
            "p0": self.WF2_P0, "q0": 0.0,
            "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
        })
        ss.add("REGCA1", {
            "idx": "WF2_R", "bus": self.WF2_BUS, "gen": "SG_WF2",
            "Sn": self.config.wf2_regca1_sn,
        })
        ss.add("REECA1", {
            "idx": "WF2_E", "reg": "WF2_R",
            "PFFLAG": 0, "VFLAG": 0, "QFLAG": 0, "PFLAG": 0, "PQFLAG": 0,
        })

        # ─── G4 链跟 V4 一样: IEEEG1+EXST1 加到所有 GENROU (含 G4) ─────
        # 这里 _pre_setup_addons 跑 V4 行为 (skip_g4_gov=False), 因为
        # w2_only 模式下 G4 GENROU 仍 active, 跟 V4 一致 governor 链
        skip_g4_gov_saved = self.config.wind_model == "regca1"
        # 临时把 wind_model 解释为 gencls 让 _pre_setup_addons 走 V4 路径,
        # 实际我们直接调 V4 的 super()._pre_setup_addons 更干净
        AndesMultiVSGEnvV4._pre_setup_addons(self, ss)

        ss.setup()

        for i, vsg_id in enumerate(self.vsg_idx):
            ss.GENCLS.set("D", vsg_id, self.D0_HETEROGENEOUS[i], attr="v")

        # V4 ZERO_G4_INERTIA hack (跟 V4 完全一致)
        if self.ZERO_G4_INERTIA and hasattr(self, "_g4_genrou_idx"):
            genrou_idx_list = list(ss.GENROU.idx.v)
            if self._g4_genrou_idx in genrou_idx_list:
                ss.GENROU.set("M", self._g4_genrou_idx, 0.1, attr="v")
                ss.GENROU.set("D", self._g4_genrou_idx, 0.0, attr="v")

        return ss

    def _build_system(self):
        """V5 plant 总入口, 按 wind_model 分支:
        - gencls            → V4 _build_system bit-identical
        - regca1_w2_only    → _build_system_w2_only (W2 升级 only, V5 default)
        - regca1            → 下面这段 (G4+W2 都换, R80 cycle 3a 实测不可用)
        """
        if self.config.wind_model == "gencls":
            # V5 fallback: V4 plant bit-identical. 直接走 V4 _build_system.
            return super()._build_system()

        if self.config.wind_model == "regca1_w2_only":
            # V5 cycle 3c minimal-impl: 只换 W2 REGCA1, G4 保留 V4 hack.
            return self._build_system_w2_only()

        # V5 REGCA1 both path (cycle 3a 实测不可用, 留作未来研究入口).
        ss = andes.load(self.case_path, default_config=True, setup=False)

        # G4 GENROU idx 留个引用, 跟 V4 一致
        self._g4_genrou_idx = G4_GENROU_IDX

        # ─── (V4-identical) Add 4 VSG buses + tie lines + disturbance loads ──
        for new_bus in self.VSG_BUSES:
            if new_bus not in list(ss.Bus.idx.v):
                ss.add("Bus", {
                    "idx": new_bus, "name": f"Bus{new_bus}", "Vn": self.NEW_BUS_VN,
                    "v0": 1.0, "a0": 0.0,
                    "area": 1 if new_bus in (12, 16) else 2,
                })
        for new_bus, parent_bus in self.NEW_BUS_CONNECTIONS.items():
            ss.add("Line", {
                "idx": f"Line_{parent_bus}_{new_bus}",
                "bus1": parent_bus, "bus2": new_bus,
                "Vn1": self.NEW_BUS_VN, "Vn2": self.NEW_BUS_VN,
                "r": self.NEW_LINE_R, "x": self.NEW_LINE_X, "b": self.NEW_LINE_B,
            })
        for load_bus, load_params in self.NEW_LOADS.items():
            ss.add("PQ", {
                "idx": f"PQ_Bus{load_bus}", "bus": load_bus,
                "Vn": self.NEW_BUS_VN,
                "p0": load_params["p0"], "q0": load_params["q0"],
            })

        # ─── (V4-identical) 4 VSGs (GENCLS) on new buses ────────────────
        self.vsg_idx = []
        for i, bus in enumerate(self.VSG_BUSES):
            vsg_id = f"VSG_{i+1}"
            gen_id = f"SG_VSG_{i+1}"
            ss.add("PV", {
                "idx": gen_id, "name": f"VSG{i+1}", "bus": bus,
                "Vn": self.NEW_BUS_VN, "Sn": self.VSG_SN,
                "p0": 0.5, "q0": 0.0,
                "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
            })
            ss.add("GENCLS", {
                "idx": vsg_id, "bus": bus, "gen": gen_id,
                "Vn": self.NEW_BUS_VN, "Sn": self.VSG_SN,
                "M": self.M0[i], "D": self.D0[i],
                "ra": 0.001, "xd1": 0.15,
            })
            self.vsg_idx.append(vsg_id)

        # ─── (V5 NEW) W2 plant 升级: REGCA1+REECA1 替代 V4 的 GENCLS ──
        # V4 在这里 add PV "SG_WF2" + GENCLS "WF2" (M=0.1, D=0). V5 改为
        # PV "SG_WF2" + REGCA1 "WF2_R" + REECA1 "WF2_E". PV slot 保留以
        # 提供 power-flow-side static gen 边界.
        ss.add("PV", {
            "idx": "SG_WF2", "name": "WF2_Bus8", "bus": self.WF2_BUS,
            "Vn": self.NEW_BUS_VN, "Sn": self.WF2_SN,
            "p0": self.WF2_P0, "q0": 0.0,
            "pmax": 5.0, "pmin": 0.0, "qmax": 5.0, "qmin": -5.0, "v0": 1.0,
        })
        ss.add("REGCA1", {
            "idx": "WF2_R", "bus": self.WF2_BUS, "gen": "SG_WF2",
            "Sn": self.config.wf2_regca1_sn,
        })
        ss.add("REECA1", {
            "idx": "WF2_E", "reg": "WF2_R",
            "PFFLAG": 0, "VFLAG": 0, "QFLAG": 0, "PFLAG": 0, "PQFLAG": 0,
        })

        # ─── (V5 NEW) G4 plant 升级: REGCA1+REECA1 + 旧 G4 链 disable ──
        # 找 G4 grid-side slot (Kundur full 里 PV idx=4 在 bus 4)
        g4_static_idx = None
        for i, b in enumerate(ss.PV.bus.v):
            if int(b) == G4_BUS_ANDES:
                g4_static_idx = ss.PV.idx.v[i]
                break
        if g4_static_idx is None:
            for i, b in enumerate(ss.Slack.bus.v):
                if int(b) == G4_BUS_ANDES:
                    g4_static_idx = ss.Slack.idx.v[i]
                    break
        if g4_static_idx is None:
            raise RuntimeError(
                f"V5 G4 wire 失败: Kundur Bus {G4_BUS_ANDES} 没有 StaticGen "
                f"(PV/Slack) record. ANDES kundur_full case 结构变了?"
            )
        ss.add("REGCA1", {
            "idx": "G4_R", "bus": G4_BUS_ANDES, "gen": g4_static_idx,
            "Sn": self.config.g4_regca1_sn,
        })
        ss.add("REECA1", {
            "idx": "G4_E", "reg": "G4_R",
            "PFFLAG": 0, "VFLAG": 0, "QFLAG": 0, "PFLAG": 0, "PQFLAG": 0,
        })

        # IEEEG1 + EXST1 (跳过 G4, 通过 _pre_setup_addons)
        self._pre_setup_addons(ss)

        ss.setup()

        # (V4-identical) 异质 D₀ 套到 4 个 VSG
        for i, vsg_id in enumerate(self.vsg_idx):
            ss.GENCLS.set("D", vsg_id, self.D0_HETEROGENEOUS[i], attr="v")

        # ─── (V5 NEW) G4 链 disable: GENROU + TGOV1 + EXDC2 全 u=0 ────
        # paper Sec.II 立场是 G4 是风机, 用 REGCA1 接管. V4 是 ZERO_G4_INERTIA
        # 把 M/D 调零的 hack (CLM-0040); V5 干脆把整链 u=0 disable, ANDES
        # init 仍 attempt residual (warning), 但 TDS 时 u·eqn 乘 0 强制 trivial,
        # 物理上 G4 GENROU 不参与, 由 REGCA1 接管. probe r80_regca1_wire_check
        # 已验证此路径 pflow + 1-step TDS PASS.
        if G4_GENROU_IDX in list(ss.GENROU.idx.v):
            ss.GENROU.set("u", G4_GENROU_IDX, 0, attr="v")
        for mname in ("TGOV1", "IEEEG1", "EXDC2", "EXST1"):
            m = getattr(ss, mname, None)
            if m is None or m.n == 0 or not hasattr(m, "syn"):
                continue
            for i, syn_idx in enumerate(m.syn.v):
                if syn_idx == G4_GENROU_IDX:
                    m.set("u", m.idx.v[i], 0, attr="v")

        # 注意: V5 不再走 V4 的 ZERO_G4_INERTIA 路径 (M=0.1 hack), 因为 G4
        # GENROU 已经整体 u=0, M/D 数值无关紧要. config.zero_g4_inertia 在
        # wind_model=="regca1" 时被忽略 (V5Config.__post_init__ 已记笔记).

        return ss
