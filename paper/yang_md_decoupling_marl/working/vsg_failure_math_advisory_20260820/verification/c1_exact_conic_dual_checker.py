#!/usr/bin/env python3
"""Exact rational checker for the dual of a standard-form SOCP.

Primal convention:
    minimize c^T x
    subject to A x = b
               G x + s = h,  s in K
Dual convention:
    maximize -b^T y - h^T z
    subject to c + A^T y + G^T z = 0, z in K*.

Input JSON stores every scalar as an integer, decimal string, or fraction
string such as "17/100". Supported self-dual cones are nonnegative orthants
and Lorentz/SOC blocks. This checker proves an exact dual lower bound for the
provided rationalized conic data; it does not prove that those data correctly
represent the VSG plant or controller class.
"""
from __future__ import annotations
import argparse,json
from fractions import Fraction
from pathlib import Path

def F(x): return x if isinstance(x,Fraction) else Fraction(str(x))
def vec(xs): return [F(x) for x in xs]
def mat(xs): return [vec(r) for r in xs]
def dot(a,b): return sum((x*y for x,y in zip(a,b)),Fraction(0))
def transpose(M): return list(map(list,zip(*M))) if M else []
def mat_t_vec(M,v,ncol):
    if not M: return [Fraction(0) for _ in range(ncol)]
    return [dot(col,v) for col in transpose(M)]
def in_cones(z,cones):
    pos=0; checks=[]
    for block in cones:
        typ=block['type']; dim=int(block['dim']); q=z[pos:pos+dim]
        if len(q)!=dim: return False,[{'error':'cone partition exceeds z length'}]
        if typ=='nonnegative': ok=all(x>=0 for x in q); margin=min(q) if q else Fraction(0)
        elif typ=='soc':
            if dim<1: return False,[{'error':'SOC dimension must be positive'}]
            margin=q[0]*q[0]-sum((x*x for x in q[1:]),Fraction(0)); ok=q[0]>=0 and margin>=0
        else: return False,[{'error':f'unsupported cone type {typ}'}]
        checks.append({'type':typ,'dim':dim,'ok':ok,'exact_margin':str(margin)})
        pos+=dim
    if pos!=len(z): return False,checks+[{'error':f'cone dimensions sum to {pos}, z has {len(z)}'}]
    return all(c.get('ok',False) for c in checks),checks

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('certificate',type=Path); a=ap.parse_args()
    d=json.loads(a.certificate.read_text(encoding='utf-8'))
    c=vec(d['c']); A=mat(d.get('A',[])); b=vec(d.get('b',[])); G=mat(d['G']); h=vec(d['h']); y=vec(d.get('y',[])); z=vec(d['z'])
    n=len(c)
    errors=[]
    if len(G)!=len(h) or any(len(r)!=n for r in G): errors.append('G/h dimensions invalid')
    if len(A)!=len(b) or any(len(r)!=n for r in A): errors.append('A/b dimensions invalid')
    if len(y)!=len(b) or len(z)!=len(h): errors.append('dual vector dimensions invalid')
    if errors:
        print(json.dumps({'verified':False,'errors':errors},indent=2)); return 1
    aty=mat_t_vec(A,y,n); gtz=mat_t_vec(G,z,n)
    stationarity=[c[i]+aty[i]+gtz[i] for i in range(n)]
    cone_ok,cone_checks=in_cones(z,d['cones'])
    objective=-dot(b,y)-dot(h,z)
    verified=all(v==0 for v in stationarity) and cone_ok and objective>0
    out={'verified':verified,'exact_stationarity_residual':[str(v) for v in stationarity],'cone_checks':cone_checks,'exact_dual_lower_bound':str(objective),'positive_lower_bound':objective>0,'scope':'Exact only for the rational conic data and declared phase-I convention supplied in this file.'}
    print(json.dumps(out,indent=2))
    return 0 if verified else 1
if __name__=='__main__': raise SystemExit(main())
