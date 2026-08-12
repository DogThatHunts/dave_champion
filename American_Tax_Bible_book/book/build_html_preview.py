#!/usr/bin/env python3
"""build_html_preview.py — quick HTML preview of the first N pages of
*The American Tax Bible*, styled identically to book #1's interactive edition
(`../../book/Book - …Shattering the Myths.html`).

Reuses book #1's <style> block verbatim (shared look/feel), renders the MD
(emphasis + page anchors + book headings) into the same sidebar+main shell.
This is a STYLE preview — full citation enrichment / TOC generation is the later
`build_html.py` step. Run from American_Tax_Bible_book/book/:

    .venv/bin/python build_html_preview.py [--pages 1-10]
"""
import argparse, re, html

MD = "American Tax Bible.md"
BOOK1 = "../../book/Book - Dave Champion - Income Tax - Shattering the Myths.html"
PDF = "American Tax Bible.pdf"
OUT = "preview_p1-10.html"


def md_inline(s):
    """Escape HTML, then apply **bold** / _italic_ markdown."""
    s = html.escape(s, quote=False)
    # bold+italic first (**_x_**), then bold, then italic
    s = re.sub(r"\*\*_(.+?)_\*\*", r"<strong><em>\1</em></strong>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![A-Za-z0-9])_(.+?)_(?![A-Za-z0-9])", r"<em>\1</em>", s)
    return s


def render_pages(md, lo, hi):
    # Split into (page_no, text) segments on the page anchors.
    parts = re.split(r"<!-- page: (\d+) -->", md)
    # parts = [pre, num, body, num, body, ...]
    out = []
    for i in range(1, len(parts), 2):
        n = int(parts[i])
        if n < lo or n > hi:
            continue
        body = parts[i + 1].strip("\n")
        # page pill (right-margin), linking into the source PDF at page n
        out.append(
            f'<div class="pagebreak"><a class="pageref" '
            f'href="{html.escape(PDF)}#page={n}" target="_blank" '
            f'title="Open PDF page {n}"><span class="pdf-ico">PDF</span> p.{n}</a></div>'
        )
        for block in re.split(r"\n\s*\n", body):
            block = block.strip("\n")
            if not block.strip():
                continue
            hm = re.match(r"^(#{1,6})\s+(.*)$", block.strip())
            if hm:
                lvl = len(hm.group(1))
                slug = re.sub(r"[^a-z0-9]+", "-", hm.group(2).lower()).strip("-")
                out.append(f'<h{lvl} id="{slug}">{md_inline(hm.group(2))}</h{lvl}>')
                continue
            raw = [l for l in block.split("\n") if l.strip()]
            # Rejoin TOC dot-leader entries with the page number that reflow
            # pushed onto the next line (e.g. "Introduction …… " + "1").
            merged = []
            for l in raw:
                if merged and re.fullmatch(r"\s*\d{1,4}\s*", l) and re.search(r"[.…]{2,}\s*$", merged[-1]):
                    merged[-1] = merged[-1].rstrip() + " " + l.strip()
                else:
                    merged.append(l)
            lines = [md_inline(l) for l in merged]
            out.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="1-10")
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.pages.split("-"))

    md = open(MD, encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", open(BOOK1, encoding="utf-8").read(), re.S).group(0)
    body_html = render_pages(md, lo, hi)

    # Section anchors present in this range (for the sidebar).
    heads = [(len(m.group(1)), m.group(2).strip())
             for m in re.finditer(r"^(#{1,6})\s+(.*)$", md[:md.find(f"<!-- page: {hi+1} -->")]
                                   if f"<!-- page: {hi+1} -->" in md else md, re.M)]
    def slug(t):
        return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    nav = "\n".join(
        f'<li class="lvl{min(l,5)}"><a href="#{slug(t)}">{html.escape(t.title())}</a></li>'
        for l, t in heads[:12])

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The American Tax Bible — Thomas Freed (preview, pp. {lo}–{hi})</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
{style}
</head>
<body>
<button id="menu-btn" aria-label="Toggle contents">☰</button>
<div class="wrap">
<aside id="sidebar">
<h1>The American<br>Tax Bible</h1>
<div class="byline">Thomas Freed — interactive edition</div>
<div class="byline"><em>Style preview · pages {lo}–{hi}</em></div>
<ol class="nav-list">
<li class="lvl3"><a href="#top">Front matter &amp; Contents</a></li>
{nav}
</ol>
<div class="legend"><b>Preview note:</b> this is a visual style preview of the first
{hi-lo+1} pages, reusing book&nbsp;#1's stylesheet. Bold/italic are recovered from the
source PDF; the blue <span style="background:#0b5c8a;color:#fff;border-radius:3px;padding:0 .2rem;font-size:.62rem">PDF</span>&nbsp;p.N
tags open that page of the source PDF. Inline citation links and a generated Table of
Contents come in the full build.</div>
</aside>
<main id="top">
<p class="titleblock booktitle"><strong>The American Tax Bible</strong></p>
<p class="titleblock byline"><em>by Thomas Freed</em></p>
{body_html}
</main>
</div>
<a id="totop" href="#top">↑</a>
<script>
const sb=document.getElementById('sidebar'),mb=document.getElementById('menu-btn');
mb&&mb.addEventListener('click',()=>sb.classList.toggle('open'));
const tt=document.getElementById('totop');
addEventListener('scroll',()=>{{tt.style.display=scrollY>500?'flex':'none';}});
</script>
</body>
</html>
"""
    open(OUT, "w", encoding="utf-8").write(doc)
    print(f"wrote {OUT} ({len(doc):,} bytes), pages {lo}-{hi}")


if __name__ == "__main__":
    main()
