"""Reconcile txt vs md per page at symbol level; rank pages for vision review."""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

MD = Path("papers/cordis-spatiotemporal-composability.md").read_text(encoding="utf-8")
TXT = Path("papers/cordis-spatiotemporal-composability.txt").read_text(encoding="utf-8")

# --- LaTeX command -> Unicode symbol map (for counting md symbols) ---
# Symbols whose PDF glyph is composed (e.g. \neq renders "=" + combining slash),
# so txt extraction cannot see them; excluded from mismatch scoring.
RENDER_ARTIFACT = set("≠∣⊨∅")

CMD2SYM = {
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "partial": "∂", "circ": "∘", "times": "×", "to": "→", "mapsto": "↦",
    "in": "∈", "neq": "≠", "approx": "≈", "simeq": "≃", "perp": "⊥",
    "bot": "⊥", "top": "⊤", "leq": "≤", "geq": "≥", "equiv": "≡",
    "sim": "∼", "leftarrow": "←", "Leftarrow": "⇐", "Rightarrow": "⇒",
    "Leftrightarrow": "⇔", "leftrightarrow": "↔", "subseteq": "⊆",
    "supseteq": "⊇", "subset": "⊂", "supset": "⊃", "setminus": "∖",
    "cup": "∪", "cap": "∩", "oplus": "⊕", "otimes": "⊗", "star": "⋆",
    "diamond": "⋄", "infty": "∞", "forall": "∀", "exists": "∃",
    "wedge": "∧", "vee": "∨", "neg": "¬", "vdash": "⊢", "models": "⊨",
    "vDash": "⊨", "sqsubseteq": "⊑", "sqsupseteq": "⊒", "emptyset": "∅",
    "varnothing": "∅", "langle": "⟨", "rangle": "⟩", "langle": "⟨",
    "cdot": "·", "ell": "ℓ", "nabla": "∇", "sum": "∑", "prod": "∏",
    "int": "∫", "bigcup": "⋃", "bigcap": "⋂", "bullet": "•",
    "propto": "∝", "parallel": "∥", "cong": "≅", "asymp": "≍",
    "le": "≤", "ge": "≥", "ne": "≠", "pm": "±", "mp": "∓", "div": "÷",
    "Re": "ℜ", "Im": "ℑ", "aleph": "ℵ", "hbar": "ℏ", "sharp": "♯",
    "flat": "♭", "natural": "♮", "triangle": "△", "square": "□",
    "Box": "□", "checkmark": "✓", "colon": ":", "mid": "∣", "nmid": "∤",
    "downharpoonright": "⇁", "rightharpoonup": "⇀", "leftharpoonup": "↼",
    "rightleftharpoons": "⇌", "leftrightharpoons": "⇋",
    "rightarrow": "→", "longrightarrow": "⟶", "prec": "≺", "lhd": "⊲",
    "coloneqq": "≔", "notin": "∉", "lor": "∨", "nvDash": "⊭", "land": "∧",
    "iff": "⇔", "dots": "…",
}
# math-ish Unicode chars to count in txt (and in md prose)
SYMBOL_CLASS = re.compile(
    "[ΓΔΘΛΞΠΣΥΦΨΩαβγδεζηθικλμνξπρστυφχψω∂∘×→↦∈≠≈≃⊥⊤≤≥≡∼←⇐⇒⇔↔⊆⊇⊂⊃∖∪∩⊕⊗⋆⋄∞∀∃∧∨¬⊢⊨⊑⊒∅⟨⟩·ℓ∇∑∏∫⋃⋂•∝∥≅≍±∓÷ℜℑℵℏ△□✓∣∤⇁⇀↼⇌⇋ᵢⱼₖⁿᵐℓ₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹𝔗𝔈𝔅𝔇≺⊲≔∉⊭…]"
)

# --- split txt into pages ---
parts = re.split(r"===== PAGE (\d+) =====\n", TXT)
txt_pages = {}
for i in range(1, len(parts) - 1, 2):
    txt_pages[int(parts[i])] = parts[i + 1]

# --- split md into pages on --- separators ---
md_chunks = re.split(r"\n---\n", MD)
print(f"md chunks: {len(md_chunks)}, txt pages: {len(txt_pages)}")

def page_symbols_txt(page_text: str) -> Counter:
    # Mathematical Alphanumeric Symbols (math italic/bold/fraktur) decompose to base chars
    norm = unicodedata.normalize("NFKD", page_text)
    return Counter(SYMBOL_CLASS.findall(norm))

FONT_CMD = re.compile(r"\\(mathfrak|mathcal|mathbb|mathbf|mathrm|mathsf)\{([^}]{1,8})\}")

def page_symbols_md(page_text: str) -> Counter:
    c = Counter(SYMBOL_CLASS.findall(page_text))
    # count LaTeX commands as their symbols
    for cmd, sym in CMD2SYM.items():
        n = len(re.findall(r"\\" + cmd + r"(?![a-zA-Z])", page_text))
        if n:
            c[sym] += n
    # \mathfrak{E} etc. -> count the argument character
    for m in FONT_CMD.finditer(page_text):
        arg = unicodedata.normalize("NFKD", m.group(2))
        for ch in arg:
            if SYMBOL_CLASS.match(ch):
                c[ch] += 1
    # LaTeX sub/superscripts -> Unicode sub/superscript digits (txt emits ₁ etc.)
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    sup_map = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    for m in re.finditer(r"_([0-9])", page_text):
        c[m.group(1).translate(sub_map)] += 1
    for m in re.finditer(r"\^([0-9])", page_text):
        c[m.group(1).translate(sup_map)] += 1
    return c

def md_density(page_text: str) -> tuple[int, int]:
    disp = len(re.findall(r"\$\$(.+?)\$\$", page_text, re.S))
    inline = len(re.findall(r"(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)", page_text))
    return disp, inline

rows = []
for idx, chunk in enumerate(md_chunks):
    # find page number: last bare-digit line in chunk
    nums = [int(l) for l in chunk.splitlines() if l.strip().isdigit() and len(l.strip()) <= 3]
    pageno = nums[-1] if nums else idx + 1
    t = txt_pages.get(pageno, "")
    if not t:
        rows.append({"page": pageno, "note": "no txt page", "score": 0, "density": (0, 0)})
        continue
    ct = page_symbols_txt(t)
    cm = page_symbols_md(chunk)
    all_syms = set(ct) | set(cm)
    score = 0
    diffs = []
    for s in sorted(all_syms, key=lambda z: -abs(ct[z] - cm[z])):
        d = abs(ct[s] - cm[s])
        # representation noise: txt flattens sub/superscripts (₁⁰…), \coloneqq renders
        # as ":=", \dots as "..."; these cannot be compared at symbol level
        if d and s != "•" and s not in RENDER_ARTIFACT and s not in "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹…≔":
            score += d
            diffs.append((s, ct[s], cm[s]))
    disp, inline = md_density(chunk)
    rows.append({
        "page": pageno, "score": score, "density": [disp, inline],
        "top_diffs": diffs[:8],
    })

# rank: math-dense pages first by density, then by mismatch score
dense = [r for r in rows if r["density"][0] >= 2 or r["density"][1] >= 12]
suspicious = [r for r in rows if r["score"] >= 6 and r not in dense]
selected = sorted(dense, key=lambda r: -r["score"])
flagged = sorted(suspicious, key=lambda r: -r["score"])

out = Path("papers/verify")
out.mkdir(parents=True, exist_ok=True)
(out / "reconciliation.json").write_text(
    json.dumps({"dense": selected, "flagged": flagged, "all": rows}, ensure_ascii=False, indent=1),
    encoding="utf-8",
)
lines = [
    "# 对账报告：txt（文本层）vs md（LlamaParse）逐页符号比对",
    "",
    f"- md 分页块: {len(md_chunks)}；txt 页: {len(txt_pages)}",
    f"- 公式密集页（display≥2 或 inline≥12）: {len(selected)}",
    f"- 仅按符号差异标记的可疑页（score≥6）: {len(flagged)}",
    "",
    "## 公式密集页（按差异分数降序）",
    "| 页 | 差异分 | display | inline | 主要差异 (符号: txt/md) |",
    "|---|---|---|---|---|",
]
for r in selected:
    d = "; ".join(f"{s}: {a}/{b}" for s, a, b in r["top_diffs"][:5]) or "—"
    lines.append(f"| {r['page']} | {r['score']} | {r['density'][0]} | {r['density'][1]} | {d} |")
lines += ["", "## 其余可疑页", "| 页 | 差异分 | display | inline | 主要差异 |", "|---|---|---|---|---|"]
for r in flagged:
    d = "; ".join(f"{s}: {a}/{b}" for s, a, b in r["top_diffs"][:5]) or "—"
    lines.append(f"| {r['page']} | {r['score']} | {r['density'][0]} | {r['density'][1]} | {d} |")
(out / "report-reconciliation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"dense pages: {len(selected)}, flagged-only: {len(flagged)}")
print(f"pages needing review: {len(selected) + len(flagged)}")
