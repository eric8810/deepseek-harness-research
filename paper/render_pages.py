"""Render all PDF pages to PNG at 170 DPI for vision verification."""
from pathlib import Path

import pymupdf

SRC = Path("papers/cordis-spatiotemporal-composability.pdf")
OUT = Path("papers/verify/pages")
OUT.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open(SRC)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=170)
    out = OUT / f"page-{i + 1:02d}.png"
    pix.save(out)
print(f"rendered {len(doc)} pages")
