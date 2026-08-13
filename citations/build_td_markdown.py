#!/usr/bin/env python3
"""Extract Treasury Decision PDFs -> per-TD Markdown transcripts.

Deterministic, re-runnable pipeline (LIGHT cleanup — faithful to source):
  - PDFs with a usable text layer  -> pdftotext
  - image-only PDFs (no text)      -> pdftoppm @300dpi + tesseract OCR
  - T.D. 8734                       -> authoritative IRS .txt (cleaner than the PDF),
                                       falling back to pdftotext if the fetch fails.

Old HathiTrust bulletin scans contain SEVERAL consecutive decisions on one page;
each starts with a "(T. D. NNNN.)" header. We slice to the TARGET decision using
those headers. Modern single-decision docs are taken whole.

Writes <folder>/content.md with a small metadata header + <!-- page: N --> anchors.
Only content.md is written; PDFs are never modified. Run from citations/.

Usage:  python3 build_td_markdown.py [td_2382 td_2401 ...]   # default: all configured
"""
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote

from td_relations import load_relations, VERB_LABEL

RELATIONS = load_relations()

TD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treasury_decisions")

# method: "text" (pdftotext) | "ocr" (tesseract) | "irs-txt"
# slice:  True  -> slice out just this decision from a multi-decision scan
#         False -> the whole PDF is this one decision
# "ocr": True marks OCR-derived text (tesseract, or a HathiTrust embedded-OCR text
# layer) — its within-paragraph soft line breaks get reflowed (see
# docs/OCR_TEXT_RECONSTITUTION.md). Born-digital text and the authoritative IRS
# .txt keep their intentional line breaks (no "ocr").
TDS = [
    {"num": "1928", "folder": "td_1928", "method": "text", "slice": True, "ocr": True},
    {"num": "2313", "folder": "td_2313", "method": "text", "slice": True},
    {"num": "2382", "folder": "td_2382", "method": "ocr",  "slice": True, "ocr": True},
    {"num": "2401", "folder": "td_2401", "method": "text", "slice": True, "ocr": True},
    # 2402 shares the combined "TD 2401, TD 2402.pdf"; the dup folder was removed,
    # so read from td_2401's PDF and write td_2402/td_2402.md (no duplicate PDF).
    {"num": "2402", "folder": "td_2402", "src_folder": "td_2401",
     "method": "text", "slice": True, "ocr": True},
    {"num": "2815", "folder": "td_2815", "method": "ocr",  "slice": True, "ocr": True,
     "note": "The 2-page scan also carries the next decision, T.D. 2816; this file "
             "is sliced to the T.D. 2815 section. (The earlier 'may actually be 2816' "
             "caveat is resolved — the scan's own header reads (T.D. 2815.).)"},
    {"num": "2988", "folder": "td_2988", "method": "text", "slice": True, "ocr": True},
    {"num": "6500", "folder": "td_6500", "method": "text", "slice": False},
    {"num": "8734", "folder": "td_8734", "method": "irs-txt", "slice": False,
     "ext_txt": "https://www.irs.gov/pub/irs-regs/td8734.txt"},
    {"num": "8881", "folder": "td_8881", "method": "text", "slice": False},
]

# Header that opens a decision on the old bulletins, e.g. "(T. D. 2401.)".
# Tolerant of OCR spacing / comma-for-period.
HEADER_RE = re.compile(r"\(\s*T\s*[.,]\s*D\s*[.,]?\s*(\d{3,4})\s*[.,]?\s*\)")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def hathitrust(num):
    return (f"https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+{num}"
            "%22;a=srchls;lmt=ft")


def ext_ref(spec):
    """(label, url) for the external secondary reference."""
    if spec.get("ext_txt"):
        return "IRS (authoritative full text)", spec["ext_txt"]
    return "HathiTrust full-text search", hathitrust(spec["num"])


def pdf_path(folder):
    d = os.path.join(TD_DIR, folder)
    if not os.path.isdir(d):
        return None
    pdfs = sorted(f for f in os.listdir(d) if f.lower().endswith(".pdf"))
    return os.path.join(d, pdfs[0]) if pdfs else None


def extract_pages(spec, pdf):
    """Return a list of page strings (one per PDF page)."""
    if spec["method"] == "irs-txt":
        r = run(["curl", "-fsS", "--max-time", "30", spec["ext_txt"]])
        if r.returncode == 0 and r.stdout.strip():
            spec["_source_used"] = "IRS .txt (" + spec["ext_txt"] + ")"
            return [r.stdout]
        # fall back to the local PDF text layer
        spec["_source_used"] = "local PDF text layer (IRS .txt fetch failed)"
        spec["method"] = "text"

    if spec["method"] == "text":
        spec.setdefault("_source_used", "local PDF text layer (pdftotext)")
        r = run(["pdftotext", "-layout", pdf, "-"])
        return r.stdout.split("\f")

    if spec["method"] == "ocr":
        spec.setdefault("_source_used", "local scan, OCR (pdftoppm 300dpi + tesseract)")
        pages = []
        # Scratch dir inside the repo: the sandbox TMPDIR isn't readable by the
        # tesseract/leptonica subprocess, but a repo-local dir is.
        with tempfile.TemporaryDirectory(dir=TD_DIR) as tmp:
            base = os.path.join(tmp, "p")
            run(["pdftoppm", "-r", "300", "-gray", pdf, base])
            imgs = sorted(f for f in os.listdir(tmp) if f.endswith(".pgm"))
            for img in imgs:
                # tesseract's stdout ("-") comes back empty in this env; write a file.
                stem = os.path.join(tmp, img + ".out")
                run(["tesseract", os.path.join(tmp, img), stem])
                with open(stem + ".txt") as fh:
                    pages.append(fh.read())
        return pages
    raise ValueError(spec["method"])


def clean(text, reflow=False):
    """Light, deterministic OCR/layout cleanup — faithful, no rewriting.

    reflow=True (OCR'd text): join within-paragraph soft line breaks into spaces so
    each paragraph is continuous flowing text; blank-line paragraph breaks are kept.
    See docs/OCR_TEXT_RECONSTITUTION.md.
    """
    text = text.replace("\r", "")
    if reflow:
        # OCR text: de-hyphenate across a line end, tolerating spaces around the
        # hyphen/break (e.g. "dis- \nclose", "non-\n resident") so reflow doesn't
        # leave a visible mid-word space.
        text = re.sub(r"(\w)-[ \t]*\n[ \t]*(\w)", r"\1\2", text)
    else:
        # non-reflowed (born-digital / .txt): keep line breaks; conservative join.
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        # normalise the citation token: "T. D." / "T, D." -> "T.D."
        ln = re.sub(r"\bT\s*[.,]\s*D\s*\.", "T.D.", ln)
        # drop spaces before closing punctuation and after opening bracket
        ln = re.sub(r"\s+([,.;:!?%)\]])", r"\1", ln)
        ln = re.sub(r"([(\[])\s+", r"\1", ln)
        lines.append(ln)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    if reflow:
        # collapse single (soft) newlines to a space; keep blank-line paragraph breaks
        out = re.sub(r"(?<!\n)\n(?!\n)", " ", out)
        out = re.sub(r"[ \t]{2,}", " ", out)
    return out


def slice_to_target(full, num):
    """Slice from this decision's header to the next decision's header."""
    heads = [(m.start(), m.group(1)) for m in HEADER_RE.finditer(full)]
    start = next((pos for pos, n in heads if n == num), None)
    if start is None:
        return full, False  # no explicit header; keep whole doc
    end = len(full)
    for pos, n in heads:
        if pos > start and n != num:
            end = pos
            break
    return full[start:end].strip(), True


def build(spec):
    pdf = pdf_path(spec.get("src_folder", spec["folder"]))
    if not pdf:
        print(f"  ! {spec['folder']}: no PDF found")
        return
    os.makedirs(os.path.join(TD_DIR, spec["folder"]), exist_ok=True)
    pages = extract_pages(spec, pdf)
    cleaned = [clean(p, reflow=spec.get("ocr", False)) for p in pages]

    # Assemble body with page anchors; slice afterwards so anchors survive.
    body = "\n\n".join(
        f"<!-- page: {i} -->\n\n{pg}" for i, pg in enumerate(cleaned, 1) if pg
    )
    sliced = False
    if spec.get("slice"):
        body, sliced = slice_to_target(body, spec["num"])

    # Link back to the source document(s): the local scan/PDF + external reference.
    out_dir = os.path.join(TD_DIR, spec["folder"])
    pdf_rel = os.path.relpath(pdf, out_dir)
    ext_label, ext_url = ext_ref(spec)
    sources = [f"[local scan (PDF)]({quote(pdf_rel)})", f"[{ext_label}]({ext_url})"]

    header = [f"# Treasury Decision {spec['num']}", ""]
    # Inter-TD relationships (supersedes / superseded by / amends / amended by),
    # each linking to the other decision's transcript page.
    for rel in RELATIONS.get(spec["num"], []):
        link = f"[T.D. {rel['to']}](../td_{rel['to']}/td_{rel['to']}.html)"
        basis = f" — {rel['basis']}" if rel.get("basis") else ""
        header.append(f"> **{VERB_LABEL[rel['verb']]}:** {link}{basis}")
        header.append(">")
    header.append("> **Source(s):** " + " · ".join(sources))
    header.append(">")
    src = spec.get("_source_used", "local PDF")
    header.append(f"> **Extraction:** {src}. Light deterministic cleanup; "
                  "faithful transcription (original spelling/OCR quirks preserved).")
    if sliced:
        header.append(">")
        header.append(f"> **Note:** extracted from a multi-decision bulletin scan; "
                      f"this file is only the T.D. {spec['num']} section.")
    if spec.get("note"):
        header.append(">")
        header.append(f"> ⚠ {spec['note']}")
    header += ["", "---", ""]

    md = "\n".join(header) + body + "\n"
    name = f"td_{spec['num']}.md"
    out = os.path.join(out_dir, name)
    with open(out, "w") as f:
        f.write(md)
    write_relation_markers(spec, out_dir)
    print(f"  ✓ {spec['folder']}/{name}  ({len(body):,} chars, "
          f"{'sliced' if sliced else 'whole'}, {src.split(' (')[0]})")


def write_relation_markers(spec, out_dir):
    """Drop an UPPERCASE marker file per relationship so it can't be missed when
    browsing the folder (e.g. SUPERSEDES__td_2382.md). Name-encoded; regenerated
    from td_relations.json. Stale markers are cleared first."""
    for f in os.listdir(out_dir):
        if re.match(r"(SUPERSEDES|SUPERSEDED_BY|AMENDS|AMENDED_BY)__td_\d+\.md$", f):
            os.remove(os.path.join(out_dir, f))
    for rel in RELATIONS.get(spec["num"], []):
        verb = rel["verb"].upper().replace(" ", "_")
        fn = f"{verb}__td_{rel['to']}.md"
        with open(os.path.join(out_dir, fn), "w") as f:
            f.write(f"# T.D. {spec['num']} — {rel['verb'].upper()} — T.D. {rel['to']}\n\n")
            if rel.get("basis"):
                f.write(f"{rel['basis']}.\n\n")
            f.write(f"Related decision transcript: "
                    f"[T.D. {rel['to']}](../td_{rel['to']}/td_{rel['to']}.html)\n\n"
                    f"_Marker generated by build_td_markdown.py from "
                    f"`citations/td_relations.json`._\n")


def main():
    want = set(sys.argv[1:])
    specs = [s for s in TDS if not want or s["folder"] in want or s["num"] in want]
    print(f"Building {len(specs)} TD transcript(s)…")
    for s in specs:
        build(s)


if __name__ == "__main__":
    main()
