#!/usr/bin/env python3
"""Evaluate the exact discrete integer-delay law from a complex nominal loop.

NPZ schema: `omega` (rad/sample), complex `L0`, and optional complex `N`,
nonnegative `weights`, positive scalar `E_local`, integer `delays`, and
positive scalar `sample_period`. Physical-time output is omitted unless the
sample period is supplied by the project.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

def sensitivity(L0:np.ndarray,omega:np.ndarray,n:int)->np.ndarray:
    return 1.0/(1.0+L0*np.exp(-1j*n*omega))

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('npz',type=Path); ap.add_argument('--output',type=Path); a=ap.parse_args()
    with np.load(a.npz,allow_pickle=False) as z:
        omega=np.asarray(z['omega'],dtype=float); L0=np.asarray(z['L0'],dtype=complex)
        delays=np.asarray(z['delays'],dtype=int) if 'delays' in z else np.arange(0,3,dtype=int)
        N=np.asarray(z['N'],dtype=complex) if 'N' in z else None
        weights=np.asarray(z['weights'],dtype=float) if 'weights' in z else np.ones_like(omega)
        E_local=float(np.asarray(z['E_local']).item()) if 'E_local' in z else None
        Ts=float(np.asarray(z['sample_period']).item()) if 'sample_period' in z else None
    if omega.shape!=L0.shape or weights.shape!=omega.shape: raise ValueError('omega, L0, weights must have identical shapes')
    if np.any(weights<0) or np.sum(weights)<=0: raise ValueError('weights must be nonnegative and nonzero')
    S0=sensitivity(L0,omega,0); rows=[]
    for n in delays.tolist():
        if n<0: raise ValueError('delays must be nonnegative integers')
        Sn=sensitivity(L0,omega,n)
        exact_ratio=np.abs(Sn/S0)**2
        rec={'delay_steps':int(n),'min_pointwise_sensitivity_power_ratio':float(np.min(exact_ratio)),'max_pointwise_sensitivity_power_ratio':float(np.max(exact_ratio)),'weighted_mean_sensitivity_power_ratio':float(np.sum(weights*exact_ratio)/np.sum(weights))}
        if Ts is not None:
            if Ts<=0: raise ValueError('sample_period must be positive')
            rec['delay_seconds']=float(n*Ts)
        if N is not None:
            if N.shape!=omega.shape: raise ValueError('N shape mismatch')
            energy=float(np.sum(weights*np.abs(N*Sn)**2))
            rec['predicted_candidate_energy']=energy
            if E_local is not None:
                if E_local<=0: raise ValueError('E_local must be positive')
                rec['predicted_endpoint_ratio']=energy/E_local
        rows.append(rec)
    result={'status':'HYPOTHETICAL_INPUT_RECIPE','rows':rows,'warning':'This computes an endpoint curve only when N, weights, and a fixed same-bank E_local are supplied. It is not a stability certificate.'}
    text=json.dumps(result,indent=2)
    if a.output: a.output.write_text(text+'\n',encoding='utf-8')
    print(text); return 0
if __name__=='__main__': raise SystemExit(main())
