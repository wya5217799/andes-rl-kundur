#!/usr/bin/env python3
"""Check Proposition P1.1 from matched complex-response finite differences.

NPZ schema
----------
Required: Gk_minus, Gk_0, Gk_plus, Gl_minus, Gl_0, Gl_plus, h.
Complex response arrays may be (n_frequency,) for one h or
(n_h,n_frequency). `h` is scalar or (n_h,). Optional `weights` is a
nonnegative frequency vector shared by all rows; default is uniform.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

def energy(g:np.ndarray,w:np.ndarray)->np.ndarray:
    return np.sum(w*np.abs(g)**2,axis=-1)

def inner(a:np.ndarray,b:np.ndarray,w:np.ndarray)->np.ndarray:
    return np.sum(w*np.conj(a)*b,axis=-1)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('npz',type=Path); ap.add_argument('--output',type=Path); a=ap.parse_args()
    with np.load(a.npz,allow_pickle=False) as z:
        data={k:np.asarray(z[k]) for k in ['Gk_minus','Gk_0','Gk_plus','Gl_minus','Gl_0','Gl_plus']}
        h=np.asarray(z['h'],dtype=float).reshape(-1)
        nfreq=data['Gk_0'].shape[-1]
        w=np.asarray(z['weights'],dtype=float) if 'weights' in z else np.ones(nfreq)
    if np.any(w<0) or np.sum(w)<=0: raise ValueError('weights must be nonnegative and nonzero')
    w=w.reshape((1,)* (data['Gk_0'].ndim-1)+(nfreq,))
    for k,v in data.items():
        if v.shape[-1]!=nfreq: raise ValueError(f'{k}: frequency dimension mismatch')
        if v.ndim==1: data[k]=v[None,:]
    nh=data['Gk_0'].shape[0]
    if h.size==1: h=np.repeat(h,nh)
    if h.size!=nh or np.any(h<=0): raise ValueError('h must be positive scalar or length n_h')
    H=h.reshape(-1,1)
    dGk=(data['Gk_plus']-data['Gk_minus'])/(2*H)
    dGl=(data['Gl_plus']-data['Gl_minus'])/(2*H)
    Ek0=energy(data['Gk_0'],w); El0=energy(data['Gl_0'],w)
    if np.any(Ek0<=0) or np.any(El0<=0): raise ValueError('center energies must be positive')
    candidate=2*np.real(inner(data['Gk_0'],dGk,w))/Ek0
    reference=2*np.real(inner(data['Gl_0'],dGl,w))/El0
    rhs=candidate-reference
    rp=energy(data['Gk_plus'],w)/energy(data['Gl_plus'],w)
    rm=energy(data['Gk_minus'],w)/energy(data['Gl_minus'],w)
    lhs=(np.log(rp)-np.log(rm))/(2*h)
    rows=[]
    for i in range(nh):
        rows.append({'h':float(h[i]),'lhs_central_dlog_ratio':float(lhs[i]),'candidate_term':float(candidate[i]),'reference_term':float(reference[i]),'rhs_difference':float(rhs[i]),'absolute_mismatch':float(abs(lhs[i]-rhs[i]))})
    result={'status':'HYPOTHETICAL_INPUT_RECIPE','rows':rows,'convergence_note':'Register h values and compare the mismatch and successive estimates before interpreting a mechanism.'}
    text=json.dumps(result,indent=2)
    if a.output: a.output.write_text(text+'\n',encoding='utf-8')
    print(text); return 0
if __name__=='__main__': raise SystemExit(main())
