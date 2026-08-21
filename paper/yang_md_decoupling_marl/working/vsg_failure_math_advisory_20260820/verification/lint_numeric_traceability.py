#!/usr/bin/env python3
"""Heuristic audit for long empirical-looking numerals without nearby evidence IDs.

This is a review aid, not a proof: equations and symbolic design constants may
be legitimate without JSON evidence. It flags decimal literals with at least
four significant digits or scientific notation when their paragraph contains
neither an evidence identifier nor the word HYPOTHETICAL.
"""
from __future__ import annotations
import argparse,re,json
from pathlib import Path
NUM=re.compile(r'(?<![A-Za-z_])[-+]?((\d+\.\d{3,})|(\d+(?:\.\d+)?[eE][-+]?\d+))(?![A-Za-z_])')
EVID=re.compile(r'\[[A-Z]\d(?:-[A-Z])?-[EDS]\d{2}(?:[^\]]*)\]')
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('paths',nargs='+',type=Path); a=ap.parse_args(); flags=[]
    files=[]
    for p in a.paths: files.extend(sorted(p.rglob('*.md')) if p.is_dir() else [p])
    for p in files:
        text=p.read_text(encoding='utf-8'); offset=0
        for para in re.split(r'\n\s*\n',text):
            nums=[m.group(0) for m in NUM.finditer(para)]
            if nums and not EVID.search(para) and 'HYPOTHETICAL' not in para.upper():
                line=text[:offset].count('\n')+1
                flags.append({'file':str(p),'line':line,'numbers':nums[:8],'excerpt':' '.join(para.split())[:300]})
            offset+=len(para)+2
    print(json.dumps({'flag_count':len(flags),'flags':flags},indent=2,ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
