"""Render PNG previews of the figure PDFs (audit helper, not a deliverable)."""
from pathlib import Path
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed; skipping preview render")
    sys.exit(0)

figs = Path(__file__).resolve().parents[1]
outdir = Path(__file__).resolve().parent
for p in sorted(figs.glob("fig*.pdf")):
    doc = fitz.open(p)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    out = outdir / (p.stem + "_preview.png")
    pix.save(out)
    print(out, pix.width, pix.height)
