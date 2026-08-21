#!/usr/bin/env python3
"""Check the direct and Schur estimates of the reduced DAE action channel.

NPZ direct schema: h (n_h,), f_plus and f_minus with shape (n_h,n_x,n_u).
Optional Schur arrays: f_u (n_x,n_u), f_y (n_x,n_y),
g_u (n_y,n_u), g_y (n_y,n_y).
All evaluations must come from equilibrium algebraic re-solves with the same
gauge and active mode; this script cannot verify that experimental premise.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('npz',type=Path); ap.add_argument('--output',type=Path); a=ap.parse_args()
    with np.load(a.npz,allow_pickle=False) as z:
        h=np.asarray(z['h'],dtype=float).reshape(-1)
        fp=np.asarray(z['f_plus'],dtype=float); fm=np.asarray(z['f_minus'],dtype=float)
        optional={k:np.asarray(z[k],dtype=float) for k in ('f_u','f_y','g_u','g_y') if k in z}
    if fp.shape!=fm.shape or fp.ndim!=3 or fp.shape[0]!=h.size: raise ValueError('f_plus/f_minus must be (n_h,n_x,n_u)')
    if np.any(h<=0): raise ValueError('h must be positive')
    direct=(fp-fm)/(2*h[:,None,None])
    rows=[]
    for i in range(h.size):
        rec={'h':float(h[i]),'frobenius_norm':float(np.linalg.norm(direct[i]))}
        if i>0:
            den=max(float(np.linalg.norm(direct[i])),np.finfo(float).tiny)
            rec['relative_change_from_previous_h']=float(np.linalg.norm(direct[i]-direct[i-1])/den)
        rows.append(rec)
    result={'status':'HYPOTHETICAL_INPUT_RECIPE','direct_fd_rows':rows,'direct_fd_finest':direct[-1].tolist()}
    if len(optional)==4:
        fu,fy,gu,gy=(optional[k] for k in ('f_u','f_y','g_u','g_y'))
        if gy.shape[0]!=gy.shape[1]: raise ValueError('g_y must be square')
        X=np.linalg.solve(gy,gu)
        schur=fu-fy@X
        residual=gy@X-gu
        result.update({'g_y_condition_number':float(np.linalg.cond(gy)),'g_y_solve_relative_residual':float(np.linalg.norm(residual)/max(np.linalg.norm(gu),np.finfo(float).tiny)),'schur_channel':schur.tolist(),'direct_schur_absolute_mismatch':float(np.linalg.norm(direct[-1]-schur)),'direct_schur_relative_mismatch':float(np.linalg.norm(direct[-1]-schur)/max(np.linalg.norm(schur),np.finfo(float).tiny))})
    else:
        result['schur_note']='Supply all of f_u, f_y, g_u, g_y for the independent reconstruction.'
    result['premise_warning']='Register solver tolerances, active-mode logs, gauge, and a materiality threshold before classifying the channel.'
    text=json.dumps(result,indent=2)
    if a.output: a.output.write_text(text+'\n',encoding='utf-8')
    print(text); return 0
if __name__=='__main__': raise SystemExit(main())
