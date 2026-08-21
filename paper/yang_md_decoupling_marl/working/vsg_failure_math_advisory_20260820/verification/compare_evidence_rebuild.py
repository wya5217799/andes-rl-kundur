#!/usr/bin/env python3
"""Compare a rebuilt evidence register against the delivered register by ID."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def load(path:Path):
    return {r['evidence_id']:r for r in csv.DictReader(path.open(encoding='utf-8',newline=''))}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('reference',type=Path); ap.add_argument('rebuilt',type=Path); a=ap.parse_args()
    x=load(a.reference); y=load(a.rebuilt); errors=[]
    if set(x)!=set(y):
        errors.append({'missing_in_rebuilt':sorted(set(x)-set(y)),'extra_in_rebuilt':sorted(set(y)-set(x))})
    fields=['problem_id','status','description','source_path','json_pointer_or_range','value','unit','derivation','source_evidence_ids','notes']
    for eid in sorted(set(x)&set(y)):
        diff={f:(x[eid][f],y[eid][f]) for f in fields if x[eid][f]!=y[eid][f]}
        if diff: errors.append({'evidence_id':eid,'differences':diff})
    print(json.dumps({'reference_count':len(x),'rebuilt_count':len(y),'errors':errors},indent=2,ensure_ascii=False))
    return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())
