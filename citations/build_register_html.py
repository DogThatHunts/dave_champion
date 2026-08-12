#!/usr/bin/env python3
"""Render link_register.json -> link_register.html, styled to match the book edition.
Regenerate whenever the register changes (kept in sync with the JSON source of truth)."""
import json, html
from urllib.parse import quote

REG = json.load(open("link_register.json", encoding="utf-8"))

# (json key, section title, colour class, primary field [linked], [(field, header, kind)])
# kind: "text" | "pages" (list joined)
SECTIONS = [
    ("scotus_and_courts", "SCOTUS & Court Cases", "case", "full_citation",
     [("court","Court","text"),("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("usc_title26_irc", "Title 26 U.S.C. — Internal Revenue Code", "stat", "section",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("cfr", "Code of Federal Regulations", "reg", "cite",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("treasury_decisions", "Treasury Decisions", "td", "cite",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("constitution", "Constitution & Founding Documents", "const", "ref",
     [("occurrences","Occ.","text")]),
    ("constitutional_clauses", "Constitutional Provisions (Article / Section / Clause)", "const", "citation",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("acts_of_congress", "Named Acts of Congress", "act", "act",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("executive_orders", "Executive Orders", "eo", "executive_order",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("irs_forms", "IRS Forms", "form", "form",
     [("occurrences","Occ.","text"),("pages","Pages","pages")]),
    ("irs_treasury_documents", "IRS & Treasury Guidance Documents", "td", "document",
     [("occurrences","Occ.","text")]),
    ("secondary_authorities", "Secondary Authorities (reference works)", "secondary", "work",
     [("occurrences","Occ.","text")]),
]

PRIM_HEADER = {"full_citation":"Full citation","section":"Section","cite":"Citation",
    "ref":"Reference","citation":"Provision","act":"Act","executive_order":"Executive Order",
    "form":"Form","document":"Document","work":"Work"}
def esc(x): return html.escape(str(x))
def cell(v, kind):
    if kind == "pages":
        return ", ".join(esc(p) for p in (v or [])[:8])
    return esc(v if v is not None else "")

nav, body = [], []
for key, title, cls, prim, cols in SECTIONS:
    items = REG.get(key, [])
    if not items: continue
    sid = key.replace("_","-")
    nav.append(f'<li><a href="#{sid}">{esc(title)}</a> <span class="n">{len(items)}</span></li>')
    body.append(f'<section id="{sid}"><h2>{esc(title)} <span class="count">{len(items)}</span></h2>')
    heads = "".join(f"<th>{esc(h)}</th>" for _,h,_ in cols)
    body.append(f'<table><thead><tr><th>{esc(PRIM_HEADER.get(prim,"Citation"))}</th>{heads}</tr></thead><tbody>')
    for it in items:
        url = it.get("url","")
        local = it.get("local_path","")
        label = esc(it.get(prim,""))
        # Prefer the local source document when we have one; keep the external
        # URL as a secondary link. Notes (e.g. possible mislabels) render inline.
        if local:
            href = quote(local)
            link = (f'<a class="cite {cls}" href="{href}">{label}</a>'
                    f'<span class="src"> · local copy · '
                    f'<a href="{esc(url)}" target="_blank" rel="noopener">external</a></span>')
        elif url:
            link = f'<a class="cite {cls}" href="{esc(url)}" target="_blank" rel="noopener">{label}</a>'
        else:
            link = label
        if it.get("note"):
            link += f'<span class="note">⚠ {esc(it["note"])}</span>'
        tds = "".join(f"<td>{cell(it.get(f), kind)}</td>" for f,_,kind in cols)
        body.append(f"<tr><td>{link}</td>{tds}</tr>")
    body.append("</tbody></table></section>")

CSS = """
:root{--ink:#1c1a17;--muted:#8a8072;--rule:#e6e0d6;--bg:#faf7f2;--paper:#fffdf9;--link:#7a1f1f;--nav:#f3efe8}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Georgia,'Times New Roman',serif;line-height:1.5;font-size:17px}
.wrap{display:grid;grid-template-columns:320px minmax(0,1fr)}
#sidebar{position:sticky;top:0;height:100vh;overflow:auto;background:var(--nav);border-right:1px solid var(--rule);padding:1.1rem 1rem 3rem}
#sidebar h1{font-family:'Playfair Display',Georgia,serif;font-size:1rem;line-height:1.3;margin:.2rem 0 .3rem}
#sidebar .sub{font-size:.8rem;color:var(--muted);margin:0 0 1rem}
#sidebar a.home{font-family:'Inter',sans-serif;font-size:.8rem;color:var(--link);text-decoration:none}
.nav-list{list-style:none;margin:1rem 0 0;padding:0;font-family:'Inter',system-ui,sans-serif;font-size:.82rem}
.nav-list li{margin:.2rem 0;display:flex;justify-content:space-between;gap:.5rem}
.nav-list a{color:#4a4034;text-decoration:none}.nav-list a:hover{color:var(--link)}
.nav-list .n{color:var(--muted);font-size:.72rem}
main{padding:2rem clamp(1rem,4vw,3rem) 6rem;max-width:1000px}
h1.title{font-family:'Playfair Display',Georgia,serif;font-size:1.8rem;margin:.2rem 0}
.lede{color:#5b5348;max-width:70ch;margin:.4rem 0 2rem}
h2{font-family:'Playfair Display',Georgia,serif;font-size:1.3rem;border-bottom:2px solid var(--rule);padding-bottom:.3rem;margin:2.4rem 0 .8rem;scroll-margin-top:1rem}
h2 .count{font-family:'Inter',sans-serif;font-size:.8rem;color:var(--muted);font-weight:400}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin-bottom:1rem}
th{text-align:left;font-family:'Inter',sans-serif;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border-bottom:1px solid var(--rule);padding:.35rem .5rem}
td{border-bottom:1px solid var(--rule);padding:.4rem .5rem;vertical-align:top}
td:nth-child(n+2){font-family:'Inter',sans-serif;font-size:.82rem;color:#5b5348;white-space:nowrap}
.cite{text-decoration:none;border-bottom:1px dotted currentColor}
.cite.case{color:#0b5c8a}.cite.stat,.cite.reg{color:#5a3d8a}.cite.const{color:#1d6b45}
.cite.td{color:#a05a00}.cite.form{color:#7a1f1f}.cite.act{color:#0b6b5e}.cite.eo{color:#8a5a00}.cite.secondary{color:#555}
.cite:hover{background:#eee}
.src{font-family:'Inter',sans-serif;font-size:.7rem;color:var(--muted)}
.src a{color:var(--muted)}
.note{display:block;font-family:'Inter',sans-serif;font-size:.72rem;color:#a05a00;margin-top:.15rem;white-space:normal}
@media(max-width:860px){.wrap{grid-template-columns:1fr}#sidebar{position:static;height:auto}td:nth-child(n+2){white-space:normal}}
"""

nav_html = "\n".join(nav)
body_html = "\n".join(body)
out = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link Register — Income Tax: Shattering The Myths</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="wrap">
<aside id="sidebar">
<h1>Link Register</h1>
<div class="sub">Income Tax: Shattering The Myths</div>
<ul class="nav-list">
{nav_html}
</ul>
</aside>
<main>
<h1 class="title">Link Register</h1>
<p class="lede">Every citable authority referenced in <em>Income Tax: Shattering The Myths</em>, linked to an
authoritative source (SCOTUS → Justia; USC/CFR → Cornell LII; Constitution → Constitution Annotated;
Acts → official government sources / Library of Congress; Treasury Decisions → IRS / HathiTrust).
Generated from <code>link_register.json</code>.</p>
{body_html}
</main>
</div></body></html>
"""
open("link_register.html","w",encoding="utf-8").write(out)
print(f"wrote link_register.html ({len(out):,} bytes; {sum(len(REG.get(k,[])) for k,*_ in SECTIONS)} entries)")
