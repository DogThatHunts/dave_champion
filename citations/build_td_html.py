#!/usr/bin/env python3
"""Render Treasury Decision Markdown transcripts (td_<num>.md) to styled HTML.

Minimal, deterministic Markdown -> HTML for the simple structure these files use:
  # title            -> <h1 class="title">
  > blockquote lines -> a <aside class="meta"> (the Source/Extraction/Note block)
  ---                -> section rule
  <!-- page: N -->   -> a page marker with an anchor (#p-N)
  blank-line blocks  -> <p>, intra-block single newlines -> <br> (faithful layout)
  [text](url)        -> <a>

Styling reuses the register/edition palette (Georgia serif, cream paper).
Run from citations/.  Usage: python3 build_td_html.py [td_2382 ...]
"""
import html
import os
import re
import sys

TD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treasury_decisions")
PAGE_RE = re.compile(r"^<!--\s*page:\s*(\d+)\s*-->$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline(text):
    """Escape, then linkify [text](url) and **bold**."""
    text = html.escape(text)
    text = LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">'
                  f'{m.group(1)}</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def render(md):
    lines = md.split("\n")
    out, i = [], 0
    title = "Treasury Decision"
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            title = ln[2:].strip()
            out.append(f'<h1 class="title">{inline(title)}</h1>')
            i += 1
        elif ln.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i].lstrip(">").strip())
                i += 1
            inner = "<br>".join(inline(b) for b in block if b)
            out.append(f'<aside class="meta">{inner}</aside>')
        elif ln.strip() == "---":
            out.append('<hr>')
            i += 1
        elif PAGE_RE.match(ln.strip()):
            n = PAGE_RE.match(ln.strip()).group(1)
            out.append(f'<div class="page" id="p-{n}">page {n}</div>')
            i += 1
        elif ln.strip() == "":
            i += 1
        else:  # a paragraph: gather until blank / page / rule
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(">") \
                    and lines[i].strip() != "---" and not PAGE_RE.match(lines[i].strip()):
                para.append(lines[i])
                i += 1
            body = "<br>".join(inline(p) for p in para)
            out.append(f"<p>{body}</p>")
    return title, "\n".join(out)


CSS = """
:root{--ink:#1c1a17;--muted:#8a8072;--rule:#e6e0d6;--bg:#faf7f2;--paper:#fffdf9;--link:#7a1f1f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Georgia,'Times New Roman',serif;line-height:1.6;font-size:18px}
main{max-width:44rem;margin:0 auto;padding:2.5rem clamp(1rem,4vw,2rem) 6rem}
a.home{font-family:Inter,system-ui,sans-serif;font-size:.8rem;color:var(--link);text-decoration:none}
h1.title{font-family:'Playfair Display',Georgia,serif;font-size:1.9rem;margin:.6rem 0 1rem}
.meta{background:var(--paper);border:1px solid var(--rule);border-left:3px solid #a05a00;
      border-radius:4px;padding:.7rem .9rem;margin:0 0 1.5rem;font-family:Inter,system-ui,sans-serif;
      font-size:.82rem;line-height:1.5;color:#5b5348}
.meta a{color:var(--link)}
hr{border:0;border-top:1px solid var(--rule);margin:1.4rem 0}
.page{font-family:Inter,system-ui,sans-serif;font-size:.68rem;text-transform:uppercase;
      letter-spacing:.08em;color:var(--muted);border-top:1px dotted var(--rule);
      padding-top:.5rem;margin:1.6rem 0 .6rem;scroll-margin-top:1rem}
p{margin:0 0 1rem;max-width:40rem}
strong{font-weight:600}
"""

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — transcript</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><main>
<a class="home" href="../../link_register.html" target="_blank" rel="noopener">← Citation link register</a>
{body}
</main></body></html>"""


def build(folder, num):
    src = os.path.join(TD_DIR, folder, f"td_{num}.md")
    if not os.path.isfile(src):
        print(f"  ! {src} not found")
        return
    with open(src) as f:
        title, body = render(f.read())
    out = os.path.join(TD_DIR, folder, f"td_{num}.html")
    with open(out, "w") as f:
        f.write(HTML.format(title=html.escape(title), css=CSS, body=body))
    print(f"  ✓ {folder}/td_{num}.html")


def main():
    want = set(sys.argv[1:])
    for folder in sorted(os.listdir(TD_DIR)):
        m = re.match(r"td_(\d+)$", folder)
        if not m:
            continue
        num = m.group(1)
        if want and folder not in want and num not in want:
            continue
        if os.path.isfile(os.path.join(TD_DIR, folder, f"td_{num}.md")):
            build(folder, num)


if __name__ == "__main__":
    main()
