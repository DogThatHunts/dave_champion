#!/usr/bin/env python3
"""
extract_md.py — American Tax Bible (Thomas Freed) → clean Markdown edition.

The source PDF is digitally produced (not scanned), so the text layer is
accurate. We walk spans page-by-page, recover bold/italic from PyMuPDF span
flags, strip the book's own running head + printed page number (kept only as
`<!-- page: N -->` anchors on the PDF sequence), promote each "book" running
head to a section heading, and OCR the handful of image-only pages inline.

Chrome vs. content:
  * Running head  = top-margin (y<55) span in a CIDFont, bold  -> strip.
  * Printed folio = bottom-margin (y>710) CIDFont span that is pure digits
                    or the literal "AMERICAN TAX BIBLE" footer band -> strip.
  Reproduced documents (statutes, IRS letters, court filings) are set in real
  fonts (TimesNewRoman, Arial, Courier, ...), so their headers/footers are NOT
  in a CIDFont and correctly survive.

Emphasis: PyMuPDF flags bit 4 (16) = bold, bit 1 (2) = italic — reliable even
for the subsetted CIDFont bodies. Contiguous same-style runs are wrapped in
Markdown, with surrounding whitespace pushed outside the markers.

Usage:  .venv/bin/python extract_md.py [--pages A-B] [--out FILE]
"""
import argparse, re, subprocess, sys
import pymupdf

PDF = "American Tax Bible.pdf"
OUT = "American Tax Bible.md"

TOP_MARGIN = 55.0      # y below this = running-head zone
BOT_MARGIN = 710.0     # y above this = footer zone
HEAD_SIZE = (11.0, 12.6)
PARA_GAP = 24.0        # vertical gap (pt) above which a new paragraph starts
FILL_BAND = 25.0       # right-edge tolerance (pt) for "line reached the margin"
FILL_FRAC = 0.6        # fraction of non-final lines that must be full -> prose

# Known "book" section heads (bold CIDFont running heads). Front-matter head
# "AMERICAN TAX BIBLE" is chrome, not a section.
FOOTER_TEXT = "AMERICAN TAX BIBLE"
BOOK_HEADS = {
    "GENESIS", "EXODUS", "REVELATION", "SALVATION",
    "THE BOOK OF CRYER", "THE BOOK OF JOHN", "THE BOOK OF TOMMY",
    "THE BOOK OF THE FREED",
}
IMAGE_ONLY = {93, 94, 95, 96, 97, 98, 348, 349, 690, 727}  # 0-based PDF idx


def is_cid(font):
    return font.startswith("CIDFont")


def _strip_md(s):
    return re.sub(r"[*_]", "", s)


def coalesce_toc(mds):
    """Collapse a Table-of-Contents block to one entry per line: wrapped titles
    are joined, the trailing page number is kept inline (dotted leaders intact),
    and bold section labels (e.g. **GENESIS**) stand on their own line."""
    entries, buf = [], []
    for l in mds:
        s = _strip_md(l).strip()
        if re.fullmatch(r"\*\*.*\*\*", l.strip()):           # bold section label
            if buf:
                entries.append(" ".join(buf)); buf = []
            entries.append(l.strip()); continue
        has_leader = re.search(r"[.…]{2,}", s)
        if re.fullmatch(r"\d{1,4}", s) and buf:              # lone page-number line
            entries.append(" ".join(buf) + " " + s); buf = []
        elif has_leader and re.search(r"\d{1,4}$", s):       # leaders + number = whole entry
            entries.append((" ".join(buf) + " " if buf else "") + l.strip()); buf = []
        else:                                                # title (possibly wrapped)
            buf.append(l.strip())
    if buf:
        entries.append(" ".join(buf))
    return entries


def tidy_emphasis(s):
    """Merge adjacent same-style emphasis runs left separated by a space when a
    line-wrap or reflow split them, e.g. `_subject-_ _matter_` -> `_subject-
    matter_` and `**a** **b**` -> `**a b**`. Only single-line spaces are merged
    (not newlines), so ragged/list line breaks are preserved."""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"_( +)_", r"\1", s)
        s = re.sub(r"\*\*( +)\*\*", r"\1", s)
    return s


def reflow(groups):
    """groups: list of paragraphs, each a list of (x0, x1, md). Returns MD blocks.
    Prose paragraphs (most non-final lines reach the block's right margin) are
    joined to a single line; ragged blocks (lists, statute subsections, forms)
    keep their line breaks; TOC blocks are coalesced to one entry per line."""
    out = []
    for g in groups:
        mds = [m for _, _, m in g]
        x1s = [x for _, x, _ in g]
        leaders = sum(1 for m in mds if re.search(r"[.…]{2,}", _strip_md(m)))
        if len(mds) >= 3 and leaders >= 2:                   # Table of Contents
            out.append("\n".join(coalesce_toc(mds)))
            continue
        if len(mds) == 1:
            out.append(mds[0]); continue
        parmax = max(x1s)
        non_final = x1s[:-1]
        full = sum(1 for v in non_final if v >= parmax - FILL_BAND)
        if non_final and full / len(non_final) >= FILL_FRAC:  # prose -> reflow
            out.append(" ".join(m.strip() for m in mds))
        else:                                                 # ragged -> keep breaks
            out.append("\n".join(mds))
    return [tidy_emphasis(b) for b in out]


def wrap_line(spans):
    """spans: list of (text, bold, italic) -> Markdown string for one line."""
    # Merge adjacent spans that share styling to avoid ``**a****b**`` seams.
    runs = []
    for text, b, i in spans:
        if not text:
            continue
        # A span with no letters/digits (lone punctuation or whitespace) should
        # not carry its own emphasis — that produces seams like `_,_` or `_"_`.
        # Treat it as neutral so it merges with its neighbours instead.
        if not re.search(r"[A-Za-z0-9]", text):
            b = i = False
        if runs and runs[-1][1] == b and runs[-1][2] == i:
            runs[-1] = (runs[-1][0] + text, b, i)
        else:
            runs.append([text, b, i])
    parts = []
    for text, b, i in runs:
        if not (b or i):
            parts.append(text)
            continue
        # Push leading/trailing whitespace outside the emphasis markers.
        m = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S)
        lead, core, trail = m.group(1), m.group(2), m.group(3)
        if not core:
            parts.append(text)
            continue
        mark = ("**" if b else "") + ("_" if i else "")
        parts.append(f"{lead}{mark}{core}{mark[::-1]}{trail}")
    return "".join(parts)


def ocr_page(page):
    """OCR an image-only page. Render the full page at 300 dpi grayscale (gives
    tesseract the white margins for context). If the page's embedded artwork is
    predominantly dark (white-on-black cover/photo), invert first."""
    pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
    dark = False
    for im in page.get_images(full=True):
        ip = pymupdf.Pixmap(page.parent, im[0])
        if ip.n > 1:
            ip = pymupdf.Pixmap(pymupdf.csGRAY, ip)
        if sum(ip.samples) / max(1, len(ip.samples)) < 110:
            dark = True
        break
    if dark:
        pix.invert_irect()
    res = subprocess.run(
        ["tesseract", "-", "stdout", "--psm", "3", "-l", "eng"],
        input=pix.tobytes("png"), capture_output=True,
    )
    return res.stdout.decode("utf-8", errors="replace").strip()


def extract_page(page, idx):
    """Return (markdown_body, new_book_or_None, printed_folio_or_None)."""
    if idx in IMAGE_ONLY:
        text = ocr_page(page)
        body = "\n".join(l.rstrip() for l in text.splitlines())
        return (f"> _[Reproduced image — OCR]_\n\n{body}\n", None, None)

    d = page.get_text("dict")
    new_book = None
    folio = None
    lines = []  # (y_top, md_text)

    for blk in d["blocks"]:
        if blk.get("type") != 0:
            continue  # image block — surrounding text handled per-page
        for line in blk["lines"]:
            y_line = line["bbox"][1]
            spans = []
            for s in line["spans"]:
                raw = s["text"]
                if not raw.strip():
                    spans.append((raw, False, False))
                    continue
                y = s["bbox"][1]
                font = s["font"]
                bold = bool(s["flags"] & 16)
                ital = bool(s["flags"] & 2)
                t = raw.strip()

                # --- strip running head (top-margin CIDFont bold) ---
                if y < TOP_MARGIN and is_cid(font) and bold and HEAD_SIZE[0] <= s["size"] <= HEAD_SIZE[1]:
                    if t in BOOK_HEADS:
                        new_book = t
                    # else: "AMERICAN TAX BIBLE" front-matter head / chrome
                    continue
                # --- strip printed folio / footer band (bottom CIDFont) ---
                if y > BOT_MARGIN and is_cid(font) and (re.fullmatch(r"\d+", t) or t == FOOTER_TEXT):
                    if re.fullmatch(r"\d+", t):
                        folio = int(t)
                    continue

                spans.append((raw, bold, ital))
            md = wrap_line(spans).rstrip()
            if md.strip():
                lines.append((y_line, line["bbox"][0], line["bbox"][2], md.strip()))

    # Sort top-to-bottom (left-to-right for spans sharing a baseline, e.g. a TOC
    # title and its right-aligned page number), then group into paragraphs by
    # vertical gap. reflow() decides prose (join to one line) vs ragged/TOC.
    lines.sort(key=lambda r: (round(r[0]), r[1]))
    groups, cur, prev_y = [], [], None
    for y, x0, x1, md in lines:
        if prev_y is not None and (y - prev_y) > PARA_GAP:
            if cur:
                groups.append(cur); cur = []
        cur.append((x0, x1, md))
        prev_y = y
    if cur:
        groups.append(cur)

    body = "\n\n".join(reflow(groups))
    return (body, new_book, folio)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="1-based PDF page range A-B (inclusive)")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    doc = pymupdf.open(PDF)
    lo, hi = 0, doc.page_count - 1
    if args.pages:
        a, b = args.pages.split("-")
        lo, hi = int(a) - 1, int(b) - 1

    chunks = []
    cur_book = None
    for idx in range(lo, hi + 1):
        page = doc[idx]
        body, new_book, folio = extract_page(page, idx)
        seg = [f"<!-- page: {idx + 1} -->"]
        if new_book and new_book != cur_book:
            cur_book = new_book
            seg.append(f"\n# {new_book}\n")
        if body.strip():
            seg.append(body)
        chunks.append("\n".join(seg))

    md = "\n\n".join(chunks) + "\n"
    with open(args.out, "w") as f:
        f.write(md)
    print(f"Wrote {args.out}: {len(md):,} chars, pages {lo+1}-{hi+1}", file=sys.stderr)


if __name__ == "__main__":
    main()
