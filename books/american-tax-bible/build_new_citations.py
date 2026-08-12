#!/usr/bin/env python3
"""build_new_citations.py — citation diff for *The American Tax Bible* (Thomas Freed).

Extracts legal citations from `American Tax Bible.md` using the SAME regex logic
as the repo-root `citations/build_register.py` (book #1's register builder), then
diffs against `citations/link_register.json` and writes a LOCAL list of only the
NEW citations (present in this book, absent from the shared register) to
`new_citations.md`, ready to fold into a merged multi-book register later.

Run from books/american-tax-bible/:  .venv/bin/python build_new_citations.py
"""
import re, json, os
from collections import defaultdict, OrderedDict
from urllib.parse import quote

MD = "American Tax Bible.md"
REGISTER = "../../citations/link_register.json"
OUT = "new_citations.md"

text = open(MD, encoding="utf-8").read()

page_marks = [(m.start(), m.group(1)) for m in re.finditer(r"<!-- page: ([^ ]+) -->", text)]
def page_at(pos):
    lo = "?"
    for off, lbl in page_marks:
        if off <= pos: lo = lbl
        else: break
    return lo
def _pkey(x): return (0, int(x)) if x.isdigit() else (1, 0, x)
def pset(s): return sorted((x for x in s if x != "?"), key=_pkey)

# ============================ extraction (mirrors build_register.py) =========

# ---- 1. SCOTUS / court cases ----
STATE_RPT = (r"U\.?\s?S\.?|S\.?\s?Ct\.?|L\.?\s?Ed\.?|F\.?\s?2d|F\.?\s?3d|F\.?\s?Supp\.?|F\.?|"
             r"Cal|Tenn|S\.?\s?W\.?\s?2d|S\.?\s?W\.?|App\.?\s?D\.?C\.?")
CASE_FULL = re.compile(
    r"([A-Z][A-Za-z.'’&\-]*(?:\s+(?:of|the|ex|rel\.?|and|&|[A-Z][A-Za-z.'’&\-]*)){0,6}\s+v\.?\s+"
    r"[A-Z][A-Za-z.'’&\-]*(?:\s+(?:of|the|and|&|[A-Z][A-Za-z.'’&\-]*)){0,6})[.,]?\s+"
    r"(\d{1,3})\s+(" + STATE_RPT + r")\s+(\d{1,4})(?:,?\s*(?:at\s*)?([\d–\-]+))?(?:[\s,]*\((\d{4})\))?")
def clean_case_name(n):
    n = re.sub(r"[*_]", "", n)
    n = re.sub(r"\s+", " ", n).strip().rstrip(".")
    n = re.sub(r"^(Supreme Court\. In |Court\. In |In re |In |Amendment was |see |See )", "", n)
    return n
def norm_reporter(rep_raw):
    r = re.sub(r"[.\s]", "", rep_raw).upper()
    return {"F2D":"F.2d","F3D":"F.3d","FSUPP":"F. Supp.","F":"F.","FED":"F.",
            "SCT":"S. Ct.","LED":"L. Ed.","US":"U.S.","CAL":"Cal.","TENN":"Tenn.",
            "SW2D":"S.W.2d","SW":"S.W.","APPDC":"App. D.C."}.get(r, rep_raw.strip())
cases = {}
for m in CASE_FULL.finditer(text):
    name = clean_case_name(m.group(1))
    vol, rraw, pg, pin, year = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
    rn = re.sub(r"[.\s]", "", rraw).upper()
    key = f"{vol} {rn} {pg}"
    disp = f"{vol} {norm_reporter(rraw)} {pg}"
    if rn == "US":
        url = f"https://supreme.justia.com/cases/federal/us/{vol}/{pg}/"; court = "U.S. Supreme Court"
    elif rn in ("F2D","F3D","F","FSUPP"):
        url = None; court = "Federal court"
    else:
        url = None; court = "State / other court"
    e = cases.setdefault(key, {"name":name,"cite":disp,"pin":pin,"year":year,"court":court,
                               "url":url,"count":0,"pages":set()})
    e["count"] += 1
    if len(name) > len(e["name"]): e["name"] = name
    if year and not e["year"]: e["year"] = year
    if pin and not e["pin"]: e["pin"] = pin
    e["pages"].add(page_at(m.start()))
for key, e in cases.items():
    if e["url"] is None:
        e["url"] = "https://www.courtlistener.com/?q=" + quote(f'{e["name"]} {e["cite"]}')
    e["full"] = (f'{e["name"]}. {e["cite"]}' + (f' at {e["pin"]}' if e["pin"] else "")
                 + (f' ({e["year"]})' if e["year"] else ""))

# ---- 2. USC / Title 26 (IRC) ----
usc = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"(?:26\s*U\.?\s?S\.?\s?C\.?|Title\s+26)\s*§*\s*(\d{1,5})([A-Za-z]?)(?![.\-]\d)(?:\(([a-z0-9]+)\))?", text):
    sec = m.group(1) + (m.group(2) or "")
    usc[sec]["count"] += 1; usc[sec]["pages"].add(page_at(m.start()))
for m in re.finditer(r"(?:[Ss]ection|§)\s*(\d{2,5})([A-Za-z]?)(?![.\-]\d)\b", text):
    if len(m.group(1)) >= 2:
        sec = m.group(1) + (m.group(2) or "")
        usc[sec]["count"] += 1; usc[sec]["pages"].add(page_at(m.start()))

# ---- 3. CFR ----
cfr = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"(\d{1,2})\s*C\.?\s?F\.?\s?R\.?\s*(?:Part\s*)?§?\s*([\d]+(?:\.[\d]+)?(?:-[\d]+)?)?", text):
    title, part = m.group(1), (m.group(2) or "").strip()
    key = f"{title} CFR" + (f" §{part}" if part else "")
    cfr[key]["count"] += 1; cfr[key]["pages"].add(page_at(m.start()))
    cfr[key]["title"] = title; cfr[key]["part"] = part

# ---- 4. Treasury Decisions ----
td = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"T\.?\s?D\.?\s*(\d{3,5})", text):
    k = f"T.D. {m.group(1)}"
    td[k]["count"] += 1; td[k]["pages"].add(page_at(m.start()))

# ---- 5. Constitution & founding docs ----
const = defaultdict(lambda: {"count":0,"pages":set()})
CMAP = {"16th Amendment":"amendment-16","Sixteenth Amendment":"amendment-16",
        "14th Amendment":"amendment-14","Fourteenth Amendment":"amendment-14",
        "13th Amendment":"amendment-13","Article I":"article-1","Article IV":"article-4",
        "Preamble":"preamble"}
for label in CMAP:
    n = len(re.findall(re.escape(label), text))
    if n: const[label]["count"] = n
FOUNDING = {"Declaration of Independence":"https://www.archives.gov/founding-docs/declaration-transcript",
            "Articles of Confederation":"https://www.archives.gov/milestone-documents/articles-of-confederation"}
for label, url in FOUNDING.items():
    n = len(re.findall(re.escape(label), text))
    if n: const[label]["count"] = n; const[label]["url"] = url

# ---- 6. IRS forms ----
forms = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"Form\s+(\d{3,4}[- ]?[A-Z]{0,3})", text):
    k = "Form " + m.group(1).strip().replace("  "," ")
    forms[k]["count"] += 1; forms[k]["pages"].add(page_at(m.start()))

# ---- 7. Constitutional Article/Section/Clause ----
ROMAN2INT = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7}
INT2ROMAN = {v:k for k,v in ROMAN2INT.items()}
def _artnum(a):
    a = a.strip().upper()
    return ROMAN2INT.get(a) or (int(a) if a.isdigit() else None)
clauses = {}
CLAUSE_RX = re.compile(
    r"Art(?:icle|\.)\s*([IVX]+|\d+)\s*[.,]\s*Sec(?:tion|\.)\s*(\d+)"
    r"(?:\s*[.,]\s*Cl(?:ause|\.)\s*(\d+))?", re.I)
for m in CLAUSE_RX.finditer(text):
    an = _artnum(m.group(1))
    if not an: continue
    sec, cl = m.group(2), m.group(3)
    disp = f"Article {INT2ROMAN.get(an, an)}, Section {sec}" + (f", Clause {cl}" if cl else "")
    e = clauses.setdefault(disp, {"count":0, "pages":set(),
        "url":f"https://constitution.congress.gov/browse/article-{an}/section-{sec}/"})
    e["count"] += 1; e["pages"].add(page_at(m.start()))

# ---- 8. Named Acts of Congress ----
LOC_STATUTES = "https://www.loc.gov/collections/united-states-statutes-at-large/"
ACT_URLS = {
    "Social Security Act":"https://www.ssa.gov/OP_Home/ssact/ssact.htm",
    "Federal Reserve Act":"https://www.federalreserve.gov/aboutthefed/fract.htm",
    "Patriot Act":"https://www.congress.gov/bill/107th-congress/house-bill/3162",
    "Paperwork Reduction Act":"https://www.congress.gov/bill/96th-congress/senate-bill/1411",
}
ACT_RX = re.compile(
    r"\b((?:[A-Z][A-Za-z'\-]+\s+){0,4}"
    r"(?:Tariff|Revenue|Tax|Security|Reserve|Firearms|Retirement|Reduction|Restructuring|"
    r"Contribution|Contributions|Unemployment|Patriot|Income\s+Tax|Corporation\s+Tax)\s+Act)"
    r"(?:\s+of\s+(\d{4})|\s+\[(\d{4})\])?")
acts = {}
for m in ACT_RX.finditer(text):
    name = re.sub(r"\s+", " ", m.group(1)).strip()
    name = re.sub(r"^(The|An?)\s+", "", name)
    name = re.sub(r"^[A-Z]{2,5}\s+(?=[A-Z][a-z])", "", name)
    name = name.replace("Insurance Contribution Act", "Insurance Contributions Act")
    if name.lower() in ("the act", "act", "lord act"): continue
    year = m.group(2) or m.group(3)
    full = name + (f" of {year}" if year and f"of {year}" not in name else "")
    url = next((u for k,u in ACT_URLS.items() if k in name), LOC_STATUTES)
    e = acts.setdefault(full, {"count":0, "pages":set(), "url":url,
                               "official": any(k in name for k in ACT_URLS)})
    e["count"] += 1; e["pages"].add(page_at(m.start()))

# ---- 9. Executive Orders ----
EO_URL_OVERRIDES = {"10289":"https://www.trumanlibrary.gov/library/executive-orders/10289/executive-order-10289"}
eos = {}
for m in re.finditer(r"(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?(\d{4,5})", text):
    num = m.group(1)
    e = eos.setdefault(num, {"count":0, "pages":set(),
        "url":EO_URL_OVERRIDES.get(num,
            f"https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=Executive+Order+{num}")})
    e["count"] += 1; e["pages"].add(page_at(m.start()))

# ---- 10. Secondary authorities ----
SECONDARY = {"Black's Law Dictionary":"https://thelawdictionary.org/",
             "Bouvier's Law Dictionary":"https://www.constitution.org/1-Law/bouvier/bouvier.html"}
secondary = {}
for name, url in SECONDARY.items():
    n = len(re.findall(name.replace("'", "[’']"), text))
    if n: secondary[name] = {"count":n, "url":url}

# ---- 11. IRS / Treasury guidance docs ----
IRS_DOCS = [
    ("Internal Revenue Manual", r"Internal Revenue Manual", "https://www.irs.gov/irm"),
    ("Cumulative Bulletin", r"Cumulative Bulletin", "https://www.irs.gov/internal-revenue-bulletins"),
    ("Treasury Orders", r"Treasury Orders?", "https://home.treasury.gov/about/general-information/orders-and-directives"),
    ("IRS Determination Letters", r"Determination Letters?", "https://www.irs.gov/individuals/understanding-your-irs-notice-or-letter"),
]
irs_docs = []
for label, pat, url in IRS_DOCS:
    n = len(re.findall(pat, text))
    if n: irs_docs.append({"document":label, "url":url, "occurrences":n})

def usc_url(sec): return f"https://www.law.cornell.edu/uscode/text/26/{sec}"
def cfr_url(e):
    return (f"https://www.law.cornell.edu/cfr/text/{e['title']}/{e['part']}" if e.get("part")
            else f"https://www.law.cornell.edu/cfr/text/{e['title']}")
def const_url(label): return f"https://constitution.congress.gov/constitution/{CMAP[label]}/"
def form_url(k):
    return f"https://www.irs.gov/forms-pubs/about-form-{k.replace('Form ','').strip().lower()}"

# ============================ diff against the shared register ================
reg = json.load(open(REGISTER, encoding="utf-8"))
def keyset(section, field):
    return {str(item.get(field, "")).strip() for item in reg.get(section, [])}

existing = {
    "cases":   keyset("scotus_and_courts", "cite"),
    "usc":     {re.sub(r"^26 U\.S\.C\. §\s*", "", s).strip() for s in keyset("usc_title26_irc", "section")},
    "cfr":     keyset("cfr", "cite"),
    "td":      keyset("treasury_decisions", "cite"),
    "const":   keyset("constitution", "ref"),
    "forms":   keyset("irs_forms", "form"),
    "clauses": keyset("constitutional_clauses", "citation"),
    "acts":    keyset("acts_of_congress", "act"),
    "eos":     {e.replace("E.O. ", "") for e in keyset("executive_orders", "executive_order")},
    "secondary": keyset("secondary_authorities", "work"),
    "irs_docs":  keyset("irs_treasury_documents", "document"),
}

# Assemble NEW-only rows per category.
new = OrderedDict()
new["cases"] = [dict(full=v["full"], court=v["court"], url=v["url"], occ=v["count"], pages=pset(v["pages"]))
                for k, v in sorted(cases.items(), key=lambda kv:-kv[1]["count"]) if v["cite"] not in existing["cases"]]
new["usc"] = [dict(section=f"26 U.S.C. § {k}", url=usc_url(k), occ=v["count"], pages=pset(v["pages"]))
              for k, v in sorted(usc.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["usc"]]
new["cfr"] = [dict(cite=k, url=cfr_url(v), occ=v["count"], pages=pset(v["pages"]))
              for k, v in sorted(cfr.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["cfr"]]
new["td"] = [dict(cite=k, url=f"https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+{k.split()[-1]}%22;a=srchls;lmt=ft",
                  occ=v["count"], pages=pset(v["pages"]))
             for k, v in sorted(td.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["td"]]
new["const"] = [dict(ref=k, url=v.get("url") or const_url(k), occ=v["count"])
                for k, v in sorted(const.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["const"]]
new["forms"] = [dict(form=k, url=form_url(k), occ=v["count"], pages=pset(v["pages"]))
                for k, v in sorted(forms.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["forms"]]
new["clauses"] = [dict(citation=k, url=v["url"], occ=v["count"], pages=pset(v["pages"]))
                  for k, v in sorted(clauses.items()) if k not in existing["clauses"]]
new["acts"] = [dict(act=k, url=v["url"], official=v["official"], occ=v["count"], pages=pset(v["pages"]))
               for k, v in sorted(acts.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["acts"]]
new["eos"] = [dict(eo=f"E.O. {k}", url=v["url"], occ=v["count"], pages=pset(v["pages"]))
              for k, v in sorted(eos.items()) if k not in existing["eos"]]
new["secondary"] = [dict(work=k, url=v["url"], occ=v["count"])
                    for k, v in sorted(secondary.items(), key=lambda kv:-kv[1]["count"]) if k not in existing["secondary"]]
new["irs_docs"] = [d for d in irs_docs if d["document"] not in existing["irs_docs"]]

# ============================ emit new_citations.md ===========================
def pgs(p): return ", ".join(p[:8]) + (" …" if len(p) > 8 else "")
L = ["# New citations — *The American Tax Bible* (Thomas Freed)\n",
     "Citations found in this book that are **not yet** in the shared register "
     "(`citations/link_register.json`, built from book #1). Page numbers are this "
     "book's PDF sequence (`<!-- page: N -->` anchors). Generated by "
     "`build_new_citations.py` — re-run to refresh. Fold these into the merged "
     "multi-book register later.\n"]

L += ["\n## 1. SCOTUS & court cases  ({} new)\n".format(len(new["cases"])),
      "| Full citation | Court | Occ. | Pages | Link |", "|---|---|---:|---|---|"]
for c in new["cases"]:
    L.append(f"| {c['full']} | {c['court']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

L += ["\n## 2. Title 26 U.S.C. (IRC) sections  ({} new)\n".format(len(new["usc"])),
      "| Section | Occ. | Pages | Cornell LII |", "|---|---:|---|---|"]
for c in new["usc"]:
    L.append(f"| {c['section']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

L += ["\n## 3. Code of Federal Regulations  ({} new)\n".format(len(new["cfr"])),
      "| Cite | Occ. | Pages | Cornell LII |", "|---|---:|---|---|"]
for c in new["cfr"]:
    L.append(f"| {c['cite']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

L += ["\n## 4. Treasury Decisions  ({} new)\n".format(len(new["td"])),
      "_Fallback links are HathiTrust searches; add canonical URLs to the shared TD mapping._\n",
      "| T.D. | Occ. | Pages | Source |", "|---|---:|---|---|"]
for c in new["td"]:
    L.append(f"| {c['cite']} | {c['occ']} | {pgs(c['pages'])} | [search]({c['url']}) |")

L += ["\n## 5. Constitution & founding documents  ({} new)\n".format(len(new["const"])),
      "| Reference | Occ. | Source |", "|---|---:|---|"]
for c in new["const"]:
    L.append(f"| {c['ref']} | {c['occ']} | [link]({c['url']}) |")

L += ["\n## 6. IRS forms  ({} new)\n".format(len(new["forms"])),
      "| Form | Occ. | Pages | IRS |", "|---|---:|---|---|"]
for c in new["forms"]:
    L.append(f"| {c['form']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

L += ["\n## 7. Constitutional provisions (Article / Section / Clause)  ({} new)\n".format(len(new["clauses"])),
      "| Provision | Occ. | Pages | Constitution Annotated |", "|---|---:|---|---|"]
for c in new["clauses"]:
    L.append(f"| {c['citation']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

L += ["\n## 8. Named Acts of Congress  ({} new)\n".format(len(new["acts"])),
      "| Act | Occ. | Pages | Source |", "|---|---:|---|---|"]
for c in new["acts"]:
    tag = "" if c["official"] else " _(Statutes at Large)_"
    L.append(f"| {c['act']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}){tag} |")

L += ["\n## 9. Executive Orders  ({} new)\n".format(len(new["eos"])),
      "| Executive Order | Occ. | Pages | Federal Register |", "|---|---:|---|---|"]
for c in new["eos"]:
    L.append(f"| {c['eo']} | {c['occ']} | {pgs(c['pages'])} | [link]({c['url']}) |")

if new["secondary"]:
    L += ["\n## 10. Secondary authorities  ({} new)\n".format(len(new["secondary"])),
          "| Work | Occ. | Source |", "|---|---:|---|"]
    for c in new["secondary"]:
        L.append(f"| {c['work']} | {c['occ']} | [link]({c['url']}) |")

if new["irs_docs"]:
    L += ["\n## 11. IRS & Treasury guidance documents  ({} new)\n".format(len(new["irs_docs"])),
          "| Document | Occ. | Source |", "|---|---:|---|"]
    for c in new["irs_docs"]:
        L.append(f"| {c['document']} | {c['occurrences']} | [link]({c['url']}) |")

open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")

total = sum(len(v) for v in new.values())
print(f"NEW citations (not in shared register): {total}")
for k, v in new.items():
    print(f"  {k:10} {len(v)}")
print(f"wrote {OUT}")
