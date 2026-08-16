"""Apply all confirmed corrections to produce the verified copy.

Rules carry expected occurrence counts; any mismatch aborts before writing.
The original papers/cordis-spatiotemporal-composability.md is never modified.
"""
import re
import sys
from pathlib import Path

SRC = Path("papers/cordis-spatiotemporal-composability.md")
OUT = Path("papers/cordis-spatiotemporal-composability.verified.md")

md = SRC.read_text(encoding="utf-8")


def apply(pattern, repl, expected, label):
    global md
    n = len(re.findall(pattern, md, re.S))
    if n != expected:
        print(f"ABORT {label}: found {n}, expected {expected}")
        sys.exit(1)
    md = re.sub(pattern, repl, md, count=expected, flags=re.S)
    print(f"ok {label}: {n}")


# --- confirmed math corrections (page, description) ---
# p7: equation (2) ellipsis
apply(r"\\mapsto \.\.\. \\}", r"\\mapsto \\ldots \\}", 1, "p7 ellipsis")
# p18: Definition 24 relation
apply(r"\\cong_k", r"\\simeq_k", 2, "p18 cong->simeq")
# p25: script V
apply(r"on \$V_k\$", r"on $\\mathcal{V}_k$", 1, "p25 mathcal V")
# p46: claim (2) subscript
apply(r"\\theta_m\^\{b'\}", r"\\theta_n^{b'}", 1, "p46 theta_n")
# p51: epsilon -> edit
apply(r"\$\\epsilon\^\{t\+1\}\$", r"$edit^{t+1}$", 1, "p51 edit")
# p40: Table 1 + Lemma 54 dropped tokens
apply(r"edit\$\^t \\circ \\Psi\^t\$", r"$edit^t \\circ \\Psi^t$", 1, "p40 edit^t circ Psi^t")
apply(r"installed\$_n\^t \\wedge \\neg\$", r"$installed_n^t \\wedge \\neg$", 1, "p40 installed neg")
apply(r"installed\$_n\^t \\wedge\$", r"$installed_n^t \\wedge$", 1, "p40 installed wedge")
apply(r"installed\$_n\^\{t\+1\} \\Rightarrow\$", r"$installed_n^{t+1} \\Rightarrow$", 2, "p40 installed t+1")
apply(r"installed\$_n\$", r"$installed_n$", 2, "p40 installed_n")
apply(r"edit\$\^t\$", r"$edit^t$", 4, "p40 edit^t")
apply(r"step\$\^t\$", r"$step^t$", 6, "p40 step^t")
apply(r"id\$_\\(Gamma)\$", r"$\\text{id}_\\Gamma$", 10, "p40 id_Gamma")
apply(r"pr\$_1 \\circ i\$", r"$\\text{pr}_1 \\circ i$", 4, "p40 pr1 circ i")
apply(r"dom\(\$F_\\gamma\$\)", r"$\\text{dom}(F_\\gamma)$", 2, "p40 dom(F_gamma)")
apply(r"\$\\theta_n \\neq\$ Inactive\(\$-\$\)", r"$\\theta_n \\ne \\text{Inactive}(-)$", 1, "p40 Inactive(-)")

# --- formatting: \eqno(N) -> \tag{N} (KaTeX-compatible) ---
apply(r"\\eqno\s*\(\s*(\d+)\s*\)", r"\\tag{\1}", 42, "eqno->tag")

# --- formatting: page artifacts ---
md = re.sub(r"(?im)^deepseek logo\s*$", "", md)  # header image text
md = re.sub(r"\n---\n", "\n\n", md)               # LlamaParse page separators
md = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", md)       # bare page-number lines
# collapse 3+ blank lines to 2
md = re.sub(r"\n{3,}", "\n\n", md)

# --- closure checks ---
leftover = re.findall(r"(?<!\$)\$(?!\$)(_[^$\n]+?|\^[^$\n]+?)\$(?!\$)", md)
print(f"remaining dropped-token spans: {len(leftover)}")
for s in leftover[:10]:
    print("  ", s[:60])
disp = len(re.findall(r"\$\$(.+?)\$\$", md, re.S))
print(f"display blocks: {disp}")

OUT.write_text(md, encoding="utf-8")
print(f"wrote {OUT} ({len(md)} chars)")
