#!/usr/bin/env python3
"""Build the interactive HTML edition of *The American Tax Bible* (Thomas Freed)
from the reflowed Markdown, styled identically to book #1's edition.

Differences from book #1's build_html.py (by design):
- **1:1 PDF pages** — the MD page anchors are the PDF *sequence* number, so the
  per-page back-link maps straight through (no printed->physical offset).
- **Line-preserving paragraphs** — extract_md.py already reflowed prose to one
  line per paragraph and kept ragged blocks (lists, statute subsections, the
  book's own Table of Contents) line-by-line. So intra-block source newlines are
  rendered as <br> (book #1 space-joins, which would flatten those blocks).
- **Keep the book's detailed TOC** — it is real content (now one clean entry per
  line); we do NOT drop dot-leader lines or synthesise a replacement.
- **Underscore-run protection** — reproduced forms have signature rules (____)
  that must not be parsed as italics.

Citation URLs are resolved exactly as book #1 does: look them up in the shared
register (../../citations/link_register.json) and fall back to the same
deterministic construction the register itself uses, so nothing goes unlinked.
Book-#2-only citations (see ../new_citations.md) resolve via those fallbacks.
"""
import re, html, json, unicodedata
from urllib.parse import quote

MD  = "American Tax Bible.md"
OUT = "American Tax Bible.html"
PDF = "American Tax Bible.pdf"
PDF_HREF = quote(PDF)
REGISTER = "../../citations/link_register.json"
TD_SIDECAR = "../../citations/treasury_decisions.json"   # {num: url}, built by book #1

# ---------- Treasury Decision map (build-time fallback hrefs; JS refetches live) ----------
td_map = {}
try:
    td_map = json.load(open(TD_SIDECAR, encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    pass

# ---------- helpers ----------
def phys_page(label):
    # MD anchors already carry the physical PDF sequence number.
    return int(label) if label.isdigit() and 1 <= int(label) <= 100000 else None

_slugs = set()
def slug(text):
    s = unicodedata.normalize("NFKD", text)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "sec"
    base = s; i = 2
    while s in _slugs:
        s = f"{base}-{i}"; i += 1
    _slugs.add(s); return s

def strip_md(t):
    return re.sub(r"[*_`]", "", t).strip()

# ---------- citation regexes ----------
CASE_US = re.compile(r"\b(\d{1,3})\s+U\.S\.\s+(\d{1,4})\b")
CASE_F  = re.compile(r"\b(\d{1,3})\s+F\.?\s?(2d|3d)\s+(\d{1,4})\b")
USC     = re.compile(r"\b26\s+U\.?S\.?C\.?\s*§?\s*(\d{1,5}[A-Za-z]?)\b")
CFR     = re.compile(r"\b(\d{1,2})\s+C\.?F\.?R\.?\s*(?:Part\s*)?§?\s*(\d+(?:\.\d+)?(?:-\d+)?)?")
AMEND   = re.compile(r"\b(16th|Sixteenth|14th|Fourteenth|13th|Thirteenth)\s+Amendment\b")
TD      = re.compile(r"\bT\.?D\.?\s*(\d{3,5})\b")
FORM    = re.compile(r"\bForm\s+(\d{3,4}(?:[- ]?[A-Z]{1,3})?)\b")
AMAP = {"16th":"amendment-16","sixteenth":"amendment-16","14th":"amendment-14",
        "fourteenth":"amendment-14","13th":"amendment-13","thirteenth":"amendment-13"}
ROMAN2INT = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7}
CLAUSE = re.compile(r"Art(?:icle|\.)\s*([IVX]+|\d+)\s*[.,]\s*Sec(?:tion|\.)\s*(\d+)"
                    r"(?:\s*[.,]\s*Cl(?:ause|\.)\s*(\d+))?", re.I)
ACT = re.compile(r"\b((?:[A-Z][A-Za-z'\-]+\s+){0,4}"
    r"(?:Tariff|Revenue|Tax|Security|Reserve|Firearms|Retirement|Reduction|Restructuring|"
    r"Contribution|Contributions|Unemployment|Patriot|Income\s+Tax|Corporation\s+Tax)\s+Act)"
    r"(?:\s+of\s+\d{4}|\s+\[\d{4}\])?")
EO = re.compile(r"(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?(\d{4,5})")
REG11 = re.compile(r"\b1\.1-1(?:\([a-z]\))?")
SECONDARY = re.compile(r"(Black|Bouvier)['’]s Law Dictionary")
LOC_STATUTES = "https://www.loc.gov/collections/united-states-statutes-at-large/"
SECONDARY_URL = {"black":"https://thelawdictionary.org/",
                 "bouvier":"https://www.constitution.org/1-Law/bouvier/bouvier.html"}
EO_URL_OVERRIDES = {"10289":"https://www.trumanlibrary.gov/library/executive-orders/10289/executive-order-10289"}

# ---------- load the shared register as the source of truth for curated URLs ----------
def rk(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())
reg_url = {}
act_url = {}
try:
    REG = json.load(open(REGISTER, encoding="utf-8"))
    for e in REG.get("scotus_and_courts", []):
        reg_url[("case", rk(e["cite"]))] = e["url"]
    for e in REG.get("usc_title26_irc", []):
        reg_url[("usc", rk(e["section"].split("§")[-1]))] = e["url"]
    for e in REG.get("cfr", []):
        reg_url[("cfr", rk(e["cite"]))] = e["url"]
    for e in REG.get("constitution", []):
        reg_url[("const", rk(e["ref"]))] = e["url"]
    for e in REG.get("irs_forms", []):
        reg_url[("form", rk(e["form"]))] = e["url"]
    for e in REG.get("treasury_decisions", []):
        reg_url[("td", re.sub(r"\D", "", e["cite"]))] = e["url"]
    for e in REG.get("acts_of_congress", []):
        act_url[rk(e["act"])] = e["url"]
except FileNotFoundError:
    REG = None

def A(href, cls, inner, extra=""):
    return f'<a class="cite {cls}" href="{href}" target="_blank" rel="noopener"{extra}>{inner}</a>'

def look(kind, key, fallback):
    return reg_url.get((kind, rk(key)), fallback)

def _artnum(a):
    a = a.strip().upper(); return ROMAN2INT.get(a) or (int(a) if a.isdigit() else None)
def _clause_b(m):
    an = _artnum(m.group(1))
    if not an: return None
    return A(f"https://constitution.congress.gov/browse/article-{an}/section-{m.group(2)}/", "const", m.group(0))
def _caseus_b(m):
    return A(look("case", f"{m.group(1)} US {m.group(2)}",
        f"https://supreme.justia.com/cases/federal/us/{m.group(1)}/{m.group(2)}/"), "case", m.group(0))
def _casef_b(m):
    return A(look("case", m.group(0), "https://www.courtlistener.com/?q=" + quote(m.group(0))), "case", m.group(0))
def _usc_b(m):
    return A(look("usc", m.group(1), f"https://www.law.cornell.edu/uscode/text/26/{m.group(1)}"), "stat", m.group(0))
def _cfr_b(m):
    title, part = m.group(1), m.group(2)
    fb = f"https://www.law.cornell.edu/cfr/text/{title}" + (f"/{part}" if part else "")
    return A(look("cfr", f"{title} CFR" + (f" §{part}" if part else ""), fb), "reg", m.group(0))
def _reg11_b(m):
    return A("https://www.law.cornell.edu/cfr/text/26/1.1-1", "reg", m.group(0))
def _amend_b(m):
    return A(look("const", m.group(1) + " Amendment",
        "https://constitution.congress.gov/constitution/" + AMAP[m.group(1).lower()] + "/"), "const", m.group(0))
def _td_b(m):
    return A(look("td", m.group(1),
        td_map.get(m.group(1), f"https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+{m.group(1)}%22;a=srchls;lmt=ft")),
        "td", m.group(0), f' data-td="{m.group(1)}"')
def _act_b(m):
    name = re.sub(r"\s+", " ", m.group(1)).strip()
    name = re.sub(r"^(The|An?)\s+", "", name); name = re.sub(r"^[A-Z]{2,5}\s+(?=[A-Z][a-z])", "", name)
    return A(act_url.get(rk(m.group(0)), act_url.get(rk(name), LOC_STATUTES)), "act", m.group(0))
def _eo_b(m):
    return A(EO_URL_OVERRIDES.get(m.group(1),
        f"https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=Executive+Order+{m.group(1)}"), "eo", m.group(0))
def _form_b(m):
    return A(look("form", "Form " + m.group(1),
        "https://www.irs.gov/forms-pubs/about-form-" + m.group(1).strip().lower().replace(" ", "-")), "form", m.group(0))
def _sec_b(m):
    return A(SECONDARY_URL[m.group(1).lower()], "secondary", m.group(0))

# priority order (first = most specific / wins overlaps)
RULES = [("const_clause", CLAUSE, _clause_b), ("case", CASE_US, _caseus_b), ("case", CASE_F, _casef_b),
         ("reg", REG11, _reg11_b), ("cfr", CFR, _cfr_b), ("usc", USC, _usc_b), ("amendment", AMEND, _amend_b),
         ("td", TD, _td_b), ("act", ACT, _act_b), ("eo", EO, _eo_b), ("form", FORM, _form_b),
         ("secondary", SECONDARY, _sec_b)]
CONFLICTS = []

def _ov(a, b): return a[0] < b[1] and b[0] < a[1]

def enrich_segment(s):
    cands = []
    for pri, (name, rx, build) in enumerate(RULES):
        for m in rx.finditer(s):
            h = build(m)
            if h: cands.append([m.start(), m.end(), pri, name, h])
    if not cands: return s
    selected = []
    for c in sorted(cands, key=lambda c: (c[2], c[0])):
        if not any(_ov(c, sel) for sel in selected): selected.append(c)
    sel_ids = {id(c) for c in selected}
    for c in selected:
        comp = sorted({d[3] for d in cands if id(d) not in sel_ids and d[3] != c[3] and _ov(c, d)})
        c.append(comp or None)
    out = []; pos = 0
    for start, end, pri, name, h, conf in sorted(selected, key=lambda c: c[0]):
        out.append(s[pos:start])
        if conf:
            h = h.replace('class="cite ', 'class="cite conflict ', 1).replace(
                '<a ', f'<a title="link conflict — also matches: {", ".join(conf)}" data-conflict="{",".join(conf)}" ', 1)
            CONFLICTS.append((s[start:end], name, conf))
        out.append(h); pos = end
    out.append(s[pos:]); return "".join(out)

def inline(text):
    t = html.escape(text)
    # protect runs of >=2 underscores (form/signature rules) from italic parsing
    prot = []
    t = re.sub(r"_{2,}", lambda m: prot.append(m.group(0)) or f"\x00{len(prot)-1}\x00", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![A-Za-z0-9])_(?=\S)(.+?)(?<=\S)_(?![A-Za-z0-9])", r"<em>\1</em>", t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: prot[int(m.group(1))], t)
    parts = re.split(r"(<[^>]+>)", t)
    return "".join(p if p.startswith("<") else enrich_segment(p) for p in parts)

# ---------- pass 1: scan headings for nav ----------
lines = open(MD, encoding="utf-8").read().split("\n")
heads = []            # (level, text, slug)
head_slug = {}        # line index -> (level, text, slug)
for i, l in enumerate(lines):
    m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", l)
    if m:
        lvl = len(m.group(1)); txt = strip_md(m.group(2))
        sg = slug(txt)
        head_slug[i] = (lvl, txt, sg)
        if lvl <= 5: heads.append((lvl, txt, sg))

# ---------- pass 2: convert body ----------
TITLE_LINES = {"THE AMERICAN", "TAX BIBLE", "By", "Thomas Freed"}
body = []
para = []
cur_page = 0
title_done = False

# styled title block up front (skips the raw front-matter title lines on page 1)
body.append('<p class="titleblock booktitle"><strong>The American Tax Bible</strong></p>')
body.append('<p class="titleblock byline"><em>by Thomas Freed</em></p>')

def flush_para():
    global para
    if para:
        body.append("<p>" + "<br>\n".join(inline(x) for x in para) + "</p>")
        para = []

for i, l in enumerate(lines):
    s = l.strip()

    # skip the raw front-matter title lines on page 1 (replaced by the block above)
    if not title_done and cur_page <= 1 and strip_md(s) in TITLE_LINES:
        if strip_md(s) == "Thomas Freed":
            title_done = True
        continue

    if i in head_slug:
        flush_para()
        lvl, txt, sg = head_slug[i]
        h = min(lvl, 5) if lvl <= 5 else 6
        body.append(f'<h{h} id="{sg}">{html.escape(txt)}</h{h}>')
        continue

    m = re.match(r"^<!-- page: (.+?) -->$", s)
    if m:
        flush_para()
        lbl = m.group(1); cur_page = int(lbl) if lbl.isdigit() else cur_page
        ph = phys_page(lbl)
        if ph:
            body.append(f'<div class="pagebreak"><a id="p-{html.escape(lbl)}" class="pageref" '
                        f'href="{PDF_HREF}#page={ph}" target="_blank" rel="noopener" '
                        f'title="Open page {html.escape(lbl)} of the source PDF">'
                        f'<span class="pdf-ico" aria-hidden="true">PDF</span>&nbsp;p.{html.escape(lbl)}</a></div>')
        else:
            body.append(f'<div class="pagebreak"><span id="p-{html.escape(lbl)}" class="pageref nolink" '
                        f'title="page {html.escape(lbl)} (no PDF mapping)">p.{html.escape(lbl)}</span></div>')
        continue

    if s == "":
        flush_para(); continue

    para.append(s)

flush_para()
content = "\n".join(body)

# ---------- citation conflict report ----------
from collections import Counter as _Counter
_conf_summary = _Counter((c[1], ", ".join(c[2])) for c in CONFLICTS)
with open("citation_conflicts.txt", "w", encoding="utf-8") as _r:
    _r.write(f"CITATION LINK CONFLICTS — {len(CONFLICTS)} total occurrences\n")
    _r.write("(winner rule linked; the listed rule(s) also matched the same span and were suppressed)\n\n")
    for (winner, comp), n in _conf_summary.most_common():
        _r.write(f"  {n:4d}  {winner:14s} vs {comp}\n")
    _r.write("\n--- distinct spans ---\n")
    for txt in sorted({c[0] for c in CONFLICTS}):
        _r.write(f"  {txt}\n")

# ---------- sidebar nav (the 8 "book" sections) ----------
sidebar = ['<ol class="nav-list">']
for lvl, txt, sg in heads:
    sidebar.append(f'<li class="lvl{lvl}"><a href="#{sg}">{html.escape(txt.title() if txt.isupper() else txt)}</a></li>')
sidebar.append("</ol>")
sidebar = "\n".join(sidebar)

CSS = """
:root{--ink:#1c1a17;--muted:#8a8072;--rule:#e6e0d6;--bg:#faf7f2;--paper:#fffdf9;
--link:#7a1f1f;--cite:#0b5c8a;--nav:#f3efe8;--maxw:760px}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:Georgia,'Iowan Old Style','Times New Roman',serif;line-height:1.62;font-size:19px}
a{color:var(--link)}
.wrap{display:grid;grid-template-columns:300px minmax(0,1fr);gap:0;align-items:start}
#sidebar{position:sticky;top:0;height:100vh;overflow:auto;background:var(--nav);
border-right:1px solid var(--rule);padding:1.1rem 1rem 3rem}
#sidebar h1{font-family:'Playfair Display',Georgia,serif;font-size:1.02rem;line-height:1.3;
margin:.2rem 0 1rem;color:var(--ink)}
#sidebar .byline{font-size:.8rem;color:var(--muted);margin:-0.6rem 0 1rem}
.nav-list{list-style:none;margin:0;padding:0;font-family:'Inter',system-ui,sans-serif;font-size:.82rem}
.nav-list li{margin:.12rem 0}
.nav-list a{color:#4a4034;text-decoration:none;display:block;padding:.15rem .35rem;border-radius:5px}
.nav-list a:hover{background:#e7e0d4;color:var(--link)}
.nav-list a.active{background:#e2d8c6;color:var(--link);font-weight:600}
.nav-list .lvl1,.nav-list .lvl2{font-weight:700}
.nav-list .lvl3{font-weight:600}
.nav-list .lvl4{padding-left:.9rem}
.nav-list .lvl5{padding-left:1.7rem;font-style:italic}
main{padding:2.4rem clamp(1rem,5vw,3rem) 6rem;max-width:calc(var(--maxw) + 6rem);margin:0 auto}
h1,h2,h3,h4,h5,h6{font-family:'Playfair Display',Georgia,serif;line-height:1.2;color:#241f1a;
scroll-margin-top:1rem}
h1{font-size:1.9rem;border-bottom:2px solid var(--rule);padding-bottom:.3rem;margin-top:2.6rem;
text-align:center;letter-spacing:.04em}
h2{font-size:1.55rem;margin-top:2.4rem}
h3{font-size:1.3rem;margin-top:2rem}
h4{font-size:1.08rem;margin-top:1.7rem;letter-spacing:.02em}
h5{font-size:.98rem;text-transform:uppercase;letter-spacing:.06em;color:#5b5348;margin-top:1.5rem}
h6{font-size:1.2rem;text-transform:uppercase;letter-spacing:.08em;color:#3a332b;font-weight:700;
text-align:center;margin:2rem auto 1rem;max-width:var(--maxw)}
p{margin:0 0 1.05rem}
main>p{max-width:var(--maxw)}
em{font-style:italic}
strong{font-weight:700}
.pagebreak{clear:both;text-align:right;max-width:var(--maxw);margin:.5rem 0 1rem;
border-top:1px dotted var(--rule);padding-top:.35rem}
.pageref{display:inline-block;font-family:'Inter',sans-serif;font-size:.7rem;color:var(--cite);
text-decoration:none;border:1px solid #cfe0ea;border-radius:5px;padding:.1rem .45rem;
background:#f2f8fb;white-space:nowrap;line-height:1.4}
.pageref .pdf-ico{font-size:.58rem;font-weight:700;letter-spacing:.03em;color:#fff;background:var(--cite);
border-radius:3px;padding:.03rem .24rem;margin-right:.15rem}
.pageref:hover{background:#e2f0f7;border-color:var(--cite);box-shadow:0 1px 3px rgba(11,92,138,.2)}
.pageref.nolink{color:var(--muted);border:1px dashed var(--rule);background:transparent;opacity:.65;cursor:default}
.pageref.nolink .pdf-ico{display:none}
.cite{text-decoration:none;color:var(--cite);border-bottom:1px dotted var(--cite)}
.cite:hover{background:#eaf3f8}
.cite.case{color:#0b5c8a;border-color:#0b5c8a}
.cite.stat,.cite.reg{color:#5a3d8a;border-color:#5a3d8a}
.cite.const{color:#1d6b45;border-color:#1d6b45}
.cite.td{color:#a05a00;border-color:#a05a00}
.cite.form{color:#7a1f1f;border-color:#c8a0a0}
.cite.act{color:#0b6b5e;border-color:#0b6b5e}
.cite.eo{color:#8a5a00;border-color:#8a5a00}
.cite.secondary{color:#555;border-color:#999}
.cite.conflict{background:#fff3cf;border-bottom:2px double #c9a227}
.cite.conflict::after{content:"\\26A0";font-size:.6em;vertical-align:super;color:#b8860b;margin-left:.05em}
.titleblock{max-width:var(--maxw);text-align:center;font-family:'Playfair Display',Georgia,serif;margin:0 auto}
.titleblock.booktitle{font-size:2rem;line-height:1.15;margin:1.5rem auto .3rem}
.titleblock.byline{font-size:1.1rem;color:#5b5348;margin:.2rem auto 1.6rem}
#menu-btn{display:none;position:fixed;top:.6rem;left:.6rem;z-index:20;background:var(--paper);
border:1px solid var(--rule);border-radius:6px;font-size:1.2rem;padding:.25rem .55rem;cursor:pointer}
#totop{position:fixed;right:1rem;bottom:1rem;background:var(--link);color:#fff;text-decoration:none;
border-radius:50%;width:2.5rem;height:2.5rem;display:none;align-items:center;justify-content:center;
font-size:1.2rem;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.legend{font-family:'Inter',sans-serif;font-size:.72rem;color:var(--muted);border-top:1px solid var(--rule);
margin-top:1.4rem;padding-top:.7rem}
.legend b{color:#4a4034}
@media(max-width:860px){
 .wrap{grid-template-columns:1fr}
 #sidebar{position:fixed;left:0;top:0;width:82%;max-width:320px;z-index:15;transform:translateX(-100%);
 transition:transform .2s;box-shadow:2px 0 14px rgba(0,0,0,.15)}
 #sidebar.open{transform:none}
 #menu-btn{display:block}
 body{font-size:18px}
 .pageref{float:none;display:inline-block;margin:0 .3rem}
}
"""

JS = """
const links=[...document.querySelectorAll('.nav-list a')];
const map=new Map(links.map(a=>[a.getAttribute('href').slice(1),a]));
const obs=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting){
 links.forEach(a=>a.classList.remove('active'));const a=map.get(e.target.id);if(a){a.classList.add('active');}}});},
 {rootMargin:'-10% 0px -80% 0px'});
document.querySelectorAll('main [id]').forEach(el=>{if(map.has(el.id))obs.observe(el);});
const sb=document.getElementById('sidebar'),mb=document.getElementById('menu-btn');
mb&&mb.addEventListener('click',()=>sb.classList.toggle('open'));
sb&&sb.addEventListener('click',e=>{if(e.target.tagName==='A'&&innerWidth<=860)sb.classList.remove('open');});
const tt=document.getElementById('totop');
addEventListener('scroll',()=>{tt.style.display=scrollY>600?'flex':'none';});
// DYNAMIC Treasury Decision links from the shared sidecar (update without rebuild)
fetch('../../citations/treasury_decisions.json').then(r=>r.ok?r.json():{}).then(m=>{
 document.querySelectorAll('a.cite.td[data-td]').forEach(a=>{
  const u=m[a.dataset.td]; if(u) a.href=u;});
}).catch(()=>{});
"""

htmlout = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The American Tax Bible — Thomas Freed</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<button id="menu-btn" aria-label="Toggle contents">☰</button>
<div class="wrap">
<aside id="sidebar">
<h1>The American<br>Tax Bible</h1>
<div class="byline">Thomas Freed — interactive edition</div>
<div class="byline"><a href="../new_citations.md" style="color:var(--link);text-decoration:none">New citations (this book) →</a></div>
{sidebar}
<div class="legend"><b>Link colours:</b> <span style="color:#0b5c8a">cases</span>,
<span style="color:#5a3d8a">statutes / regs</span>, <span style="color:#1d6b45">Constitution</span>,
<span style="color:#a05a00">Treasury Decisions</span>, <span style="color:#7a1f1f">IRS forms</span>,
<span style="color:#0b6b5e">Acts</span>, <span style="color:#8a5a00">Exec. Orders</span>, <span style="color:#555">reference works</span>.
Links with a <span style="background:#fff3cf;border-bottom:2px double #c9a227">yellow ⚠ highlight</span> are where two link rules overlapped (resolved by precedence — hover to see the conflict).
The blue <span style="background:#0b5c8a;color:#fff;border-radius:3px;padding:0 .2rem;font-size:.62rem">PDF</span> p.N
tags in the right margin open that page of the source PDF.</div>
</aside>
<main>
{content}
</main>
</div>
<a id="totop" href="#" title="Back to top">↑</a>
<script>{JS}</script>
</body>
</html>
"""

open(OUT, "w", encoding="utf-8").write(htmlout)
print(f"wrote {OUT}  ({len(htmlout):,} bytes)")
print(f"nav sections: {len(heads)}  ->  {', '.join(t for _,t,_ in heads)}")
print(f"citation conflicts: {len(CONFLICTS)} occurrences, {len({c[0] for c in CONFLICTS})} distinct spans")
