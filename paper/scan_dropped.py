"""Find inline math spans in the md that start with _ or ^ (likely dropped base tokens)."""
import re
from pathlib import Path

md = Path("papers/cordis-spatiotemporal-composability.md").read_text(encoding="utf-8")
chunks = re.split(r"\n---\n", md)

pattern = re.compile(r"(?<!\$)\$(?!\$)(_[^$\n]+?|\^[^$\n]+?)\$(?!\$)")
hits = []
for c in chunks:
    pageno = None
    for l in c.splitlines():
        if l.strip().isdigit() and len(l.strip()) <= 3:
            pageno = l.strip()
    for m in pattern.finditer(c):
        start = max(0, m.start() - 40)
        end = min(len(c), m.end() + 40)
        hits.append((pageno, m.group(1), re.sub(r"\s+", " ", c[start:end])))

out = Path("papers/verify/dropped-token-scan.md")
lines = ["# 行内公式开头缺词扫描（$ 后直接是 _ 或 ^）", "", f"共 {len(hits)} 处", ""]
for pageno, frag, ctx in hits:
    lines.append(f"- **page {pageno}**: `${frag}$` — …{ctx}…")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"found {len(hits)} suspect spans")
