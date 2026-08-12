#!/usr/bin/env python3
"""Render Books_compared_legal_theory.md to a self-contained, cool-blue HTML page.

Deliberately dependency-free (the system Python is externally managed and has no
`markdown` package). Handles the subset of Markdown used in the source doc:
headings, GFM pipe tables, ordered/unordered lists, horizontal rules, paragraphs,
inline `code`, **bold**, and _italic_/*italic* (boundary-safe so intra-word
underscores like file_names are left alone).
"""
import html
import re
from pathlib import Path

SRC = Path(__file__).with_name("Books_compared_legal_theory.md")
OUT = Path(__file__).with_name("Books_compared_legal_theory.html")

# ---------------------------------------------------------------- inline spans
_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# _italic_ and *italic* — require word boundaries so file_names stay intact
_ITAL_U_RE = re.compile(r"(?<![\w`])_(?=\S)(.+?)(?<=\S)_(?![\w])")
_ITAL_A_RE = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])")


def inline(text: str) -> str:
    """Escape then apply inline markdown. Code spans are protected from emphasis."""
    codes = []

    def stash(m):
        codes.append(html.escape(m.group(1)))
        return f"\x00{len(codes) - 1}\x00"

    text = _CODE_RE.sub(stash, text)
    text = html.escape(text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITAL_U_RE.sub(r"<em>\1</em>", text)
    text = _ITAL_A_RE.sub(r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", text)
    return text


# ------------------------------------------------------------------- block gen
def render(md: str) -> str:
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]

        # blank
        if not line.strip():
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            out.append("<hr>")
            i += 1
            continue

        # heading
        m = re.match(r"(#{1,6})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue

        # table (line starts with |, next line is a separator row)
        if line.lstrip().startswith("|") and i + 1 < n and re.search(r"\|?\s*:?-{2,}", lines[i + 1]):
            tbl, i = _table(lines, i)
            out.append(tbl)
            continue

        # unordered list
        if re.match(r"\s*[-*]\s+", line):
            lst, i = _list(lines, i, ordered=False)
            out.append(lst)
            continue

        # ordered list
        if re.match(r"\s*\d+\.\s+", line):
            lst, i = _list(lines, i, ordered=True)
            out.append(lst)
            continue

        # paragraph (gather until blank / block boundary)
        para = []
        while i < n and lines[i].strip() and not re.match(
            r"(#{1,6}\s|\s*[-*]\s+|\s*\d+\.\s+|-{3,}\s*$)", lines[i]
        ) and not lines[i].lstrip().startswith("|"):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def _cells(row: str):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def _table(lines, i):
    header = _cells(lines[i])
    i += 2  # skip header + separator
    body = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        body.append(_cells(lines[i]))
        i += 1
    h = "".join(f"<th>{inline(c)}</th>" for c in header)
    rows = []
    for r in body:
        r = (r + [""] * len(header))[: len(header)]
        rows.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    tbl = (
        '<div class="tablewrap"><table>\n<thead><tr>'
        + h
        + "</tr></thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody></table></div>"
    )
    return tbl, i


def _list(lines, i, ordered):
    tag = "ol" if ordered else "ul"
    pat = r"\s*\d+\.\s+(.*)" if ordered else r"\s*[-*]\s+(.*)"
    items = []
    while i < len(lines) and re.match(pat, lines[i]):
        items.append(inline(re.match(pat, lines[i]).group(1).strip()))
        i += 1
    return f"<{tag}>" + "".join(f"<li>{it}</li>" for it in items) + f"</{tag}>", i


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Two &ldquo;Tax Honesty&rdquo; Books Compared &mdash; Legal-Theory Analysis</title>
<style>
  :root {{
    --ink:#0d2137; --ink-soft:#274b6d; --muted:#5b7793;
    --blue:#1f6feb; --blue-deep:#0b3d91; --blue-bright:#3b9dff;
    --bg:#eef4fb; --panel:#ffffff; --line:#cfe0f2;
    --accent:#e7f1fd; --code-bg:#eaf2fd; --shadow:0 10px 40px rgba(11,61,145,.12);
  }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    margin:0; color:var(--ink);
    background:linear-gradient(160deg,#dcebfb 0%,#eef4fb 30%,#f4f8fd 100%);
    background-attachment:fixed;
    font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 22px 90px; }}
  header.hero {{
    margin:0 0 34px; padding:52px 44px 40px;
    background:linear-gradient(135deg,var(--blue-deep) 0%,var(--blue) 55%,var(--blue-bright) 100%);
    color:#fff; border-radius:0 0 22px 22px; box-shadow:var(--shadow);
    position:relative; overflow:hidden;
  }}
  header.hero::after {{
    content:""; position:absolute; right:-80px; top:-80px; width:280px; height:280px;
    background:radial-gradient(circle,rgba(255,255,255,.18),transparent 70%);
  }}
  header.hero h1 {{ margin:0 0 6px; font-size:2.05rem; line-height:1.2; color:#fff; border:0; }}
  header.hero p.sub {{ margin:8px 0 0; max-width:760px; color:#dcebff; font-size:1.02rem; }}
  header.hero em {{ color:#fff; font-style:italic; }}
  header.hero .tag {{
    display:inline-block; margin-bottom:16px; padding:5px 13px; border-radius:999px;
    background:rgba(255,255,255,.16); color:#eaf3ff; font-size:.72rem;
    letter-spacing:.14em; text-transform:uppercase; font-weight:600;
  }}
  main {{
    background:var(--panel); border:1px solid var(--line); border-radius:16px;
    padding:16px 46px 50px; box-shadow:var(--shadow);
  }}
  h1,h2,h3,h4 {{ color:var(--ink); line-height:1.25; }}
  main > h1 {{ font-size:1.7rem; }}
  h2 {{
    font-size:1.42rem; margin:2.4em 0 .7em; padding-bottom:.32em;
    border-bottom:3px solid var(--blue); color:var(--blue-deep);
  }}
  h2:first-of-type {{ margin-top:1em; }}
  h3 {{ font-size:1.12rem; margin:1.8em 0 .5em; color:var(--ink-soft); }}
  h4 {{ font-size:1rem; margin:1.5em 0 .4em; color:var(--ink-soft); }}
  p {{ margin:.75em 0; }}
  a {{ color:var(--blue); }}
  strong {{ color:var(--blue-deep); }}
  em {{ color:var(--ink-soft); }}
  hr {{ border:0; border-top:1px solid var(--line); margin:2.4em 0; }}
  ul,ol {{ padding-left:1.4em; }}
  li {{ margin:.34em 0; }}
  li::marker {{ color:var(--blue); }}
  code {{
    background:var(--code-bg); color:#0b3d91; padding:.08em .4em; border-radius:5px;
    font:.86em/1.4 "SF Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    border:1px solid #d6e6fa; white-space:nowrap;
  }}
  .tablewrap {{ overflow-x:auto; margin:1.4em 0; border-radius:12px; box-shadow:0 4px 18px rgba(11,61,145,.08); }}
  table {{ border-collapse:collapse; width:100%; font-size:.9rem; background:#fff; }}
  thead th {{
    background:linear-gradient(135deg,var(--blue-deep),var(--blue));
    color:#fff; text-align:left; font-weight:600; padding:12px 13px;
    position:sticky; top:0; vertical-align:bottom;
  }}
  thead th strong, thead th em {{ color:#fff; }}
  tbody td {{ padding:11px 13px; border-top:1px solid var(--line); vertical-align:top; }}
  tbody tr:nth-child(odd) td {{ background:var(--accent); }}
  tbody tr:hover td {{ background:#d8e8fb; }}
  td:first-child {{ font-weight:600; color:var(--ink-soft); white-space:nowrap; }}
  /* intro block (the leading emphasized paragraphs) */
  main > p:first-of-type, main > p:nth-of-type(2) {{
    background:var(--accent); border-left:4px solid var(--blue-bright);
    padding:14px 20px; border-radius:0 10px 10px 0;
  }}
  footer {{ margin-top:40px; color:var(--muted); font-size:.82rem; text-align:center; }}
  @media (max-width:640px) {{
    header.hero {{ padding:38px 22px 30px; }}
    header.hero h1 {{ font-size:1.55rem; }}
    main {{ padding:8px 20px 34px; }}
    h2 {{ font-size:1.22rem; }}
  }}
</style>
</head>
<body>
  <header class="hero">
    <div class="wrap" style="padding-bottom:0;max-width:1080px">
      <span class="tag">Legal-Theory Comparison</span>
      <h1>Two &ldquo;Tax Honesty&rdquo; Books Compared</h1>
      <p class="sub">Champion, <em>Income Tax: Shattering the Myths</em> &nbsp;vs.&nbsp;
      Freed, <em>The American Tax Bible</em> &mdash; a side-by-side analysis of their
      income-tax legal arguments: shared thesis, divergences, and contradictions.</p>
    </div>
  </header>
  <div class="wrap">
    <main>
{body}
    </main>
    <footer>Generated from Books_compared_legal_theory.md</footer>
  </div>
</body>
</html>
"""


def main():
    md = SRC.read_text(encoding="utf-8")
    # Drop the first H1 (it's reproduced in the hero header) to avoid duplication.
    md = re.sub(r"\A#\s+.*\n", "", md, count=1)
    body = render(md)
    OUT.write_text(TEMPLATE.format(body=body), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
