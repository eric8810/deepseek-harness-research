"""Per-page vision verification of the LlamaParse LaTeX against the rendered PDF page.

Usage:
  python page_vision.py <page> [--provider <id> --model <id>] [--adjudicate]

Writes:
  papers/verify/work/page-NN-<mode>.json   raw vision model output
  papers/verify/work/page-NN-prompt.txt    the prompt that was sent
"""
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

MD = Path("papers/cordis-spatiotemporal-composability.md").read_text(encoding="utf-8")
TXT = Path("papers/cordis-spatiotemporal-composability.txt").read_text(encoding="utf-8")
VERIFY = Path("papers/verify")
WORK = VERIFY / "work"
WORK.mkdir(parents=True, exist_ok=True)

MD_CHUNKS = re.split(r"\n---\n", MD)
TXT_PARTS = re.split(r"===== PAGE (\d+) =====\n", TXT)
TXT_PAGES = {int(TXT_PARTS[i]): TXT_PARTS[i + 1] for i in range(1, len(TXT_PARTS) - 1, 2)}

CHUNK_BY_PAGE = {}
for idx, chunk in enumerate(MD_CHUNKS):
    nums = [int(l) for l in chunk.splitlines() if l.strip().isdigit() and len(l.strip()) <= 3]
    pageno = nums[-1] if nums else idx + 1
    CHUNK_BY_PAGE[pageno] = chunk

DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.S)
INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)")


def extract_math(chunk: str):
    disp = DISPLAY_RE.findall(chunk)
    inline = INLINE_RE.findall(chunk)
    return disp, inline


def build_prompt(page: int, adjudicate: str | None = None) -> str:
    chunk = CHUNK_BY_PAGE[page]
    disp, inline = extract_math(chunk)
    txt_page = TXT_PAGES[page]

    # keep only symbol-bearing lines from the txt layer to shrink the prompt
    symbolish = re.compile(r"[\u2200-\u22FF\u0370-\u03FF\u1D400-\u1D7FF→←↦∘·⋯]")
    txt_lines = [l for l in txt_page.splitlines() if symbolish.search(l)]

    disp_block = "\n\n".join(
        f"[{i + 1}] $$ {d.strip()} $$" for i, d in enumerate(disp)
    )
    inline_block = "\n".join(f"- ${m}$" for m in inline) if inline else "(none)"

    lines = [
        "You are verifying the LaTeX transcription of ONE page (an OCR of a formal PL paper, Cordis).",
        "The page image is the authoritative source of truth for STRUCTURE: subscripts vs inline, "
        "superscripts, fractions, aligned multi-line equations, inference rules, bracket grouping.",
        "The appended text-layer extraction is authoritative for symbol IDENTITY (which Greek letter, "
        "which operator) but NOT for structure: its sub/superscripts are flattened and fractions are linearized.",
        "Candidate LaTeX from the OCR, display formulas first:",
        disp_block or "(no display formulas on this page)",
        "",
        "Candidate inline math:",
        inline_block,
        "",
        "Text-layer extraction of the same page (symbol identity ground truth):",
        "```",
        "\n".join(txt_lines),
        "```",
        "",
    ]
    if adjudicate:
        lines += [
            "A previous vision pass produced this assessment; you are the second opinion:",
            "```",
            adjudicate,
            "```",
            "Where the previous pass and the text layer disagree, decide using the image.",
        ]
    lines += [
        "Report EXACTLY in this format, in English:",
        "## Display formulas",
        "For each numbered display formula: `[N] OK` or `[N] FIX -> <corrected LaTeX between $ ... $>` "
        "with a one-line reason. Include nothing else for OK entries.",
        "## Inline math errors",
        "Only errors: `<wrong fragment> -> <corrected LaTeX>` plus a short context phrase from the text. "
        "If none: write `none`.",
        "## Notes",
        "Any structural caveat (e.g. ambiguous grouping, unreadable glyph). If none: write `none`.",
        "",
        "STRICT RULES:",
        "- Do NOT report prose italics, font styling, or single-letter variables in running text as errors; "
        "only wrong math CONTENT counts (wrong symbol, wrong operator, wrong subscript/superscript "
        "placement, wrong grouping, missing or extra terms).",
        "- Trust the text layer for symbol identity; only overrule it when the image clearly shows otherwise.",
        "- When the candidate LaTeX and the text layer agree, treat that as strong evidence of correctness "
        "even if you are uncertain from the image alone.",
        "Do not add preamble, do not restate the whole page.",
    ]
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    page = int(args[0])
    provider, model = "dimcode-api-oauth", "gpt-5.6-luna"
    adjudicate = None
    if "--adjudicate" in args:
        prev = WORK / f"page-{page:02d}-vision.json"
        if not prev.exists():
            sys.exit(f"no previous pass at {prev}")
        adjudicate = json.loads(prev.read_text(encoding="utf-8")).get("text", "")
        provider, model = "dimcode-api-oauth", "gpt-5.6-sol"
    for i, a in enumerate(args):
        if a == "--provider":
            provider = args[i + 1]
        if a == "--model":
            model = args[i + 1]

    mode = "adjudicate" if adjudicate else "vision"
    prompt = build_prompt(page, adjudicate)
    (WORK / f"page-{page:02d}-{mode}-prompt.txt").write_text(prompt, encoding="utf-8")

    img = VERIFY / "pages" / f"page-{page:02d}.png"
    cmd = [
        "dim", "image", "read", str(img),
        "--prompt", prompt,
        "--provider", provider, "--model", model,
        "--json", "--timeout", "300000",
    ]
    print(f"page {page}: calling {provider}/{model} ({mode})", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    raw = (proc.stdout or "") + (proc.stderr or "")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"ok": False, "error": raw[:500]}
    out = WORK / f"page-{page:02d}-{mode}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if data.get("ok"):
        print(f"page {page}: ok, output {len(data.get('text', ''))} chars -> {out.name}")
        # per-page corrections record (never touches the original md)
        if mode == "vision":
            corrections = VERIFY / "corrections"
            corrections.mkdir(parents=True, exist_ok=True)
            text = data.get("text", "")
            inline_section = text.split("## Inline math errors")[1].split("## Notes")[0] if "## Inline math errors" in text else "none"
            has_fixes = "FIX" in text or inline_section.strip().lower() not in ("", "none", "- none", "none.")
            status = "发现问题" if has_fixes else "未发现问题"
            rec = corrections / f"page-{page:02d}.md"
            rec.write_text(
                f"# Page {page} 视觉复核\n\n"
                f"- 模型: {provider}/{model}\n- 状态: {status}\n\n"
                f"## 模型输出\n\n{text}\n",
                encoding="utf-8",
            )
            print(f"page {page}: corrections -> {rec}")
    else:
        print(f"page {page}: FAILED {data.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
