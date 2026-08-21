"""PPVSM1 - projected-passive dual-droop VSM (ANDES 2.0.0 device model).

Motivation:
    The stock REGF2 grid-forming model is stopped by R392/CLM-1105: two
    positive-real local modes carried jointly by coupled internal loops, plus
    two conserved integrator directions per device (power limit PI and power
    signal lag). PPVSM1 implements the PI-authorized structural redesign:

    1. the Psen/Psig/limit-PI chain is deleted (conserved directions removed);
    2. the VSM angle loop is the dissipative swing equation
       mf * d(INTw)/dt = Pc(eta) - Pe  with  d(delta)/dt = sat(w0*eta),
       eta = INTw - 1, and Pc the projection of the P-f droop onto
       [Pmin, Pmax];
    3. the Q-V outer loop is the gradient flow
       d(rho)/dt = -k_rho * sat(Qe - Qc(V), +-rho_rate_max)  with
       V = exp(rho) and Qc the projection of the Q-V droop onto
       [Qmin, Qmax];
    4. the inner voltage/current PI cascade and Te output filter are
       retained, with an added virtual resistor Rv in the filter-current
       equations and feedforward;
    5. no PLL enters the main loop.

    This file is a repo-local ANDES model, loaded with andes.load(...,

    addfile=...) and added to the static case via System.add.
"""

from andes.core import (Algeb, ConstService, ExtAlgeb, ExtService, IdxParam,
                        Model, ModelData, NumParam, State)
from andes.core.block import GainLimiter, Integrator, Lag, PIController


class PPVSM1Data(ModelData):
    """PPVSM1 model data."""

    def __init__(self):
        ModelData.__init__(self)

        self.bus = IdxParam(model='ACNode',
                            info="interface bus id",
                            mandatory=True,
                            status_parent=True,
                            )
        self.gen = IdxParam(info="static generator index",
                            model='StaticGen',
                            mandatory=True,
                            replaces=True,
                            )
        self.Sn = NumParam(default=900.0, tex_name='S_n',
                           info='Model MVA base',
                           unit='MVA',
                           )
        self.fn = NumParam(default=60.0, info="rated frequency",
                           tex_name='f',
                           )
        self.mf = NumParam(default=0.15, info='VSM virtual inertia',
                           tex_name='M_f',
                           )
        self.wdrp = NumParam(default=0.033, info="frequency droop",
                             tex_name='omega_drp',
                             )
        self.Qdrp = NumParam(default=0.045, info="voltage droop",
                             tex_name='Q_drp',
                             )
        self.krho = NumParam(default=20.0, info='Q-V gradient gain (system base)',
                             tex_name='k_rho',
                             non_negative=True,
                             )
        self.rho_rate_max = NumParam(default=10.0,
                                     info='max d(rho)/dt (system base)',
                                     non_negative=True,
                                     )
        self.rho_rate_min = NumParam(default=-10.0,
                                     info='min d(rho)/dt (system base)',
                                     )
        self.rf = NumParam(default=0.0, info="filter resistance",
                           z=True, tex_name='r_a',
                           )
        self.xf = NumParam(default=0.2, info="filter reactance",
                           z=True, tex_name='x_s',
                           )
        self.Rv = NumParam(default=0.05, info='virtual resistor (system base)',
                           tex_name='R_v',
                           non_negative=True,
                           )
        self.KPv = NumParam(default=3, tex_name='K_Pv',
                            info='voltage PI proportional gain',
                            non_negative=True,
                            )
        self.KIv = NumParam(default=10.0, tex_name='K_Iv',
                            info='voltage PI integral gain',
                            non_negative=True,
                            )
        self.KPi = NumParam(default=0.5, tex_name='K_Pi',
                            info='current PI proportional gain',
                            non_negative=True,
                            )
        self.KIi = NumParam(default=20.0, tex_name='K_Ii',
                            info='current PI integral gain',
                            non_negative=True,
                            )
        self.Te = NumParam(default=0.005, tex_name='T_e',
                           info='output filter time constant',
                           unit='s',
                           )
        self.Pmax = NumParam(default=1.0, tex_name='P_max',
                             info='max. active power',
                             non_negative=True, power=True,
                             )
        self.Pmin = NumParam(default=-1.0, tex_name='P_min',
                             info='min. active power',
                             power=True,
                             )
        self.Qmax = NumParam(default=1.0, tex_name='Q_max',
                             info='max. reactive power',
                             non_negative=True, power=True,
                             )
        self.Qmin = NumParam(default=-1.0, tex_name='Q_min',
                             info='min. reactive power',
                             power=True,
                             )
        self.dwmax = NumParam(default=75.0, tex_name='dw_max',
                              info='max frequency deviation',
                              )
        self.dwmin = NumParam(default=-75.0, tex_name='dw_min',
                              info='min frequency deviation',
                              )


class PPVSM1Model(Model):
    """PPVSM1 variables, services, and equations."""

    def __init__(self, system, config):
        Model.__init__(self, system, config)
        self.flags.tds = True
        self.group = 'RenGen'

        self.a = ExtAlgeb(model='Bus', src='a', indexer=self.bus,
                          tex_name='theta', info='Bus voltage angle',
                          e_str='-ue * Pe',
                          )
        self.v = ExtAlgeb(model='Bus', src='v', indexer=self.bus,
                          tex_name='Vbus', info='Bus voltage magnitude',
                          e_str='-ue * Qe',
                          )

        self.p0s = ExtService(model='StaticGen', src='p', indexer=self.gen,
                              tex_name='P_0s', info='total P of static gen',
                              )
        self.q0s = ExtService(model='StaticGen', src='q', indexer=self.gen,
                              tex_name='Q_0s', info='total Q of static gen',
                              )
        self.Pref = ConstService(v_str='p0s', tex_name='P_ref',
                                 info='P dispatch (system pu)',
                                 )
        self.Qref = ConstService(v_str='q0s', tex_name='Q_ref',
                                 info='Q dispatch (system pu)',
                                 )
        self.vref = ExtService(model='StaticGen', src='v', indexer=self.gen,
                               tex_name='V_ref', info='initial v of static gen',
                               )
        self.w0 = ConstService(v_str='2 * pi * fn', tex_name='w_0',
                               info='rated angular frequency',
                               )
        self.DP = ConstService(v_str='1 / wdrp', tex_name='D_P',
                               info='P-f droop slope',
                               )

        self.Id0 = ConstService(tex_name='I_d0', v_str='Pref / v')
        self.Iq0 = ConstService(tex_name='I_q0', v_str='- Qref / v')
        self.vd0 = ConstService(tex_name='v_d0', v_str='v')
        self.vq0 = ConstService(tex_name='v_q0', v_str='0')
        self.udref0 = ConstService(tex_name='u_dref0',
                                   v_str='vd0 + (rf + Rv) * Id0 - xf * Iq0',
                                   )
        self.uqref0 = ConstService(tex_name='u_qref0',
                                   v_str='vq0 + (rf + Rv) * Iq0 + xf * Id0',
                                   )

        # --- VSM swing loop ---
        self.Pc = GainLimiter(u='Pref - DP * (INTw_y - 1)', K=1, R=1,
                              lower=self.Pmin, upper=self.Pmax,
                              info='projected P-f droop command',
                              )
        self.dw = GainLimiter(u='w0 * (INTw_y - 1)', K=1, R=1,
                              lower=self.dwmin, upper=self.dwmax,
                              info='frequency deviation',
                              )
        self.INTw = Integrator(u='(Pc_y - Pe) / mf', T=1, K=1, y0='1',
                               info='VSM speed integrator',
                               )
        self.delta = State(info='virtual delta', unit='rad',
                           v_str='a', tex_name='delta', e_str='dw_y',
                           )

        # --- Q-V gradient flow ---
        self.Qc = GainLimiter(u='Qref - (V - vref) / Qdrp', K=1, R=1,
                              lower=self.Qmin, upper=self.Qmax,
                              info='projected Q-V droop command',
                              )
        self.rho_rate = GainLimiter(u='- krho * (Qe - Qc_y)', K=1, R=1,
                                    lower=self.rho_rate_min,
                                    upper=self.rho_rate_max,
                                    info='rate-limited Q-V gradient',
                                    )
        self.rho = State(info='log voltage magnitude', unit='',
                         v_str='ln(v)', tex_name='rho', e_str='rho_rate_y',
                         )
        self.V = Algeb(info='terminal voltage magnitude', unit='pu',
                       v_str='v', e_str='exp(rho) - V',
                       tex_name='V_t',
                       )

        # --- inner voltage/current cascade (retained from the REGF1 seam) ---
        self.PIvd = PIController(u='V - vd', kp=self.KPv, ki=self.KIv,
                                 x0='Id0',
                                 )
        self.PIvq = PIController(u='- vq', kp=self.KPv, ki=self.KIv,
                                 x0='Iq0',
                                 )
        self.PIId = PIController(u='PIvd_y - Id', kp=self.KPi, ki=self.KIi,
                                 )
        self.PIIq = PIController(u='PIvq_y - Iq', kp=self.KPi, ki=self.KIi,
                                 )

        self.udref = Algeb(tex_name='u_dref', info='ud reference',
                           v_str='udref0',
                           e_str='PIId_y + vd + (rf + Rv) * Id - xf * Iq - udref',
                           )
        self.uqref = Algeb(tex_name='u_qref', info='uq reference',
                           v_str='uqref0',
                           e_str='PIIq_y + vq + (rf + Rv) * Iq + xf * Id - uqref',
                           )
        self.udLag = Lag(u='udref', T=self.Te, K=1)
        self.uqLag = Lag(u='uqref', T=self.Te, K=1)

        # --- interface equations ---
        self.vd = Algeb(tex_name='V_d', info='d-axis bus voltage',
                        e_str='v * cos(delta - a) - vd', v_str='vd0',
                        )
        self.vq = Algeb(tex_name='V_q', info='q-axis bus voltage',
                        e_str='- v * sin(delta - a) - vq', v_str='vq0',
                        )
        self.Id = Algeb(tex_name='I_d', info='d-axis current',
                        v_str='Id0', diag_eps=True,
                        e_str='vd + (rf + Rv) * Id - xf * Iq - udLag_y',
                        )
        self.Iq = Algeb(tex_name='I_q', info='q-axis current',
                        v_str='Iq0', diag_eps=True,
                        e_str='vq + (rf + Rv) * Iq + xf * Id - uqLag_y',
                        )
        self.Pe = Algeb(tex_name='P_e', info='active power injection',
                        e_str='vd * Id + vq * Iq - Pe', v_str='Pref',
                        )
        self.Qe = Algeb(tex_name='Q_e', info='reactive power injection',
                        e_str='- vd * Iq + vq * Id - Qe', v_str='Qref',
                        )


class PPVSM1(PPVSM1Data, PPVSM1Model):
    """Projected-passive dual-droop VSM."""

    def __init__(self, system, config):
        PPVSM1Data.__init__(self)
        PPVSM1Model.__init__(self, system, config)
