#!/usr/bin/env python3
"""Build a register of legal citations (SCOTUS, USC/IRC, CFR, Treasury Decisions,
constitutional refs, IRS forms) from the cleaned MD, mapped to authoritative URLs.
Emits link_register.md (human) and link_register.json (for HTML enrichment)."""
import re, json, sys
from collections import defaultdict, OrderedDict
from urllib.parse import quote

MD = "../books/income-tax-shattering-the-myths/Book - Dave Champion - Income Tax - Shattering the Myths.md"
text = open(MD, encoding="utf-8").read()

# ---- page-anchor tracking: map char offset -> nearest preceding page label ----
page_marks = [(m.start(), m.group(1)) for m in re.finditer(r"<!-- page: ([^ ]+) -->", text)]
def page_at(pos):
    lo = "?"
    for off, lbl in page_marks:
        if off <= pos: lo = lbl
        else: break
    return lo

def norm_us(vol, page):
    return f"{vol} U.S. {page}"

# ---------- 1. SCOTUS / reporter citations, paired with a preceding case name ----------
# case name pattern: "Name v. Name" possibly italicised, appearing shortly before the cite.
name_rx = r"([A-Z][A-Za-z.'’&-]+(?:\s+[A-Z][A-Za-z.'’&-]+){0,4}\s+v\.?\s+[A-Z][A-Za-z.'’&-]+(?:\s+[A-Z][A-Za-z.'’&-]+){0,4})"
cite_rx = r"(\d{1,3})\s+(U\.?\s?S\.?|S\.?\s?Ct\.?|L\.?\s?Ed\.?|F\.?\s?2d|F\.?\s?3d|Fed\.?|F\.?)\s+(\d{1,4})"

def clean_name(n):
    n = re.sub(r"[*_]", "", n).strip().rstrip(".").strip()
    n = re.sub(r"\s+", " ", n)
    # common OCR repairs in case names
    for a,b in [("Dovle","Doyle"),("Hvlton","Hylton"),("Framers","Farmers"),
                ("Benzieer","Benziger"),("Naglee","Naglee"),("Macomber","Macomber"),
                ("Brushaber","Brushaber"),("Smietanka","Smietanka")]:
        n = re.sub(rf"\b{a}\b", b, n)
    return n

# Curated case-name corrections (OCR repair / recovered from the Table of Authorities),
# keyed by NORMALISED cite ("<vol> <REPORTER-nospace-upper> <page>").
CASE_FIXES = {
    "231 US 399": "Stratton's Independence, Ltd. v. Howbert",
    "417 F2D 1002": "United States v. Moylan",
    "338 US 680": "United States v. Alpers",
    "466 US 475": "United States v. Rodgers",
    "361 US 431": "United States v. Mersky",
    "440 US 472": "National Muffler Dealers Assn. v. United States",
    "755 F2D 790": "CWT Farms, Inc. v. Commissioner of Internal Revenue",
    "809 F2D 1427": "United States v. Murphy",
    "470 F2D 585": "Economy Plumbing & Heating Co. v. United States",
    "57 F2D 877": "American Airways, Inc. v. Wallace",
    "34 SCT 421": "Billings v. United States",
    "232 US 261": "Billings v. United States",
    "247 US 165": "William E. Peck & Co. v. Lowe",
    "141 US 468": "American Net & Twine Co. v. Worthington",
    "255 US 509": "Merchants' Loan & Trust Co. v. Smietanka",
    "111 US 746": "Butchers' Union Co. v. Crescent City Co.",
}
def norm_reporter(rep_raw):
    r = re.sub(r"[.\s]", "", rep_raw).upper()
    return {"F2D":"F.2d","F3D":"F.3d","FSUPP":"F. Supp.","F":"F.","FED":"F.",
            "SCT":"S. Ct.","LED":"L. Ed.","US":"U.S.","CAL":"Cal.","TENN":"Tenn.",
            "SW2D":"S.W.2d","SW":"S.W.","APPDC":"App. D.C."}.get(r, rep_raw.strip())

STATE_RPT = (r"U\.?\s?S\.?|S\.?\s?Ct\.?|L\.?\s?Ed\.?|F\.?\s?2d|F\.?\s?3d|F\.?\s?Supp\.?|F\.?|"
             r"Cal|Tenn|S\.?\s?W\.?\s?2d|S\.?\s?W\.?|App\.?\s?D\.?C\.?")
CASE_FULL = re.compile(
    r"([A-Z][A-Za-z.'’&\-]*(?:\s+(?:of|the|ex|rel\.?|and|&|[A-Z][A-Za-z.'’&\-]*)){0,6}\s+v\.?\s+"
    r"[A-Z][A-Za-z.'’&\-]*(?:\s+(?:of|the|and|&|[A-Z][A-Za-z.'’&\-]*)){0,6})\.?\s+"
    r"(\d{1,3})\s+(" + STATE_RPT + r")\s+(\d{1,4})(?:,?\s*(?:at\s*)?([\d–\-]+))?(?:[\s,]*\((\d{4})\))?")

def clean_case_name(n):
    n = re.sub(r"\s+", " ", n).strip().rstrip(".")
    n = re.sub(r"^(Supreme Court\. In |Court\. In |In re |In |Amendment was |see |See )", "", n)
    for a,b in [("Dovle","Doyle"),("Hvlton","Hylton"),("Framers","Farmers"),
                ("Benzieer","Benziger"),("Speckels","Spreckels"),("Stales","States"),
                ("Movlan","Moylan"),("Merskv","Mersky"),("Citv","City")]:
        n = re.sub(rf"\b{a}\b", b, n)
    return n

cases = {}   # normalised cite -> {name, cite, pin, year, court, url, count, pages}
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
    if key in CASE_FIXES: e["name"] = CASE_FIXES[key]
    if e["url"] is None:
        e["url"] = "https://www.courtlistener.com/?q=" + quote(f'{e["name"]} {e["cite"]}')
    e["full"] = (f'{e["name"]}. {e["cite"]}' + (f' at {e["pin"]}' if e["pin"] else "")
                 + (f' ({e["year"]})' if e["year"] else ""))

# ---------- 2. USC / Title 26 (IRC) sections ----------
# IMPORTANT: exclude dotted/decimal cites (e.g. §31.0-2, §1.1441-1, §301.7701-11) —
# those are CFR *regulation* numbers, not IRC statute sections. The negative
# lookahead (?![.\-]\d) drops them so they don't masquerade as bare IRC sections.
usc = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"(?:26\s*U\.?\s?S\.?\s?C\.?|Title\s+26)\s*§*\s*(\d{1,5})([A-Za-z]?)(?![.\-]\d)(?:\(([a-z0-9]+)\))?", text):
    sec = m.group(1) + (m.group(2) or "")
    usc[sec]["count"] += 1
    usc[sec]["pages"].add(page_at(m.start()))
# bare "section NNNN" references (IRC is Title 26); same decimal-exclusion applies
for m in re.finditer(r"(?:[Ss]ection|§)\s*(\d{2,5})([A-Za-z]?)(?![.\-]\d)\b", text):
    sec = m.group(1) + (m.group(2) or "")
    if len(m.group(1)) >= 2:
        usc[sec]["count"] += 1
        usc[sec]["pages"].add(page_at(m.start()))

# ---------- 3. CFR sections ----------
cfr = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"(\d{1,2})\s*C\.?\s?F\.?\s?R\.?\s*(?:Part\s*)?§?\s*([\d]+(?:\.[\d]+)?(?:-[\d]+)?)?", text):
    title, part = m.group(1), (m.group(2) or "").strip()
    key = f"{title} CFR" + (f" §{part}" if part else "")
    cfr[key]["count"] += 1
    cfr[key]["pages"].add(page_at(m.start()))
    cfr[key]["title"] = title
    cfr[key]["part"] = part

# ---------- 4. Treasury Decisions ----------
td = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"T\.?\s?D\.?\s*(\d{3,5})", text):
    k = f"T.D. {m.group(1)}"
    td[k]["count"] += 1
    td[k]["pages"].add(page_at(m.start()))

# ---------- 5. Constitutional refs ----------
const = defaultdict(lambda: {"count":0,"pages":set()})
CMAP = {"16th Amendment":"amendment-16","Sixteenth Amendment":"amendment-16",
        "14th Amendment":"amendment-14","Fourteenth Amendment":"amendment-14",
        "13th Amendment":"amendment-13","Article I":"article-1","Article IV":"article-4",
        "Preamble":"preamble"}
for label in CMAP:
    n = len(re.findall(re.escape(label), text))
    if n: const[label]["count"] = n
# founding documents (not part of the Constitution) with their own authoritative URLs
FOUNDING = {"Declaration of Independence": "https://www.archives.gov/founding-docs/declaration-transcript",
            "Articles of Confederation": "https://www.archives.gov/milestone-documents/articles-of-confederation"}
for label, url in FOUNDING.items():
    n = len(re.findall(re.escape(label), text))
    if n:
        const[label]["count"] = n
        const[label]["url"] = url

# ---------- 6. IRS forms ----------
forms = defaultdict(lambda: {"count":0,"pages":set()})
for m in re.finditer(r"Form\s+(\d{3,4}[- ]?[A-Z]{0,3})", text):
    k = "Form " + m.group(1).strip().replace("  "," ")
    forms[k]["count"] += 1
    forms[k]["pages"].add(page_at(m.start()))

# ---------- 7. Constitutional Article/Section/Clause citations (section-level links) ----------
ROMAN2INT = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7}
INT2ROMAN = {v:k for k,v in ROMAN2INT.items()}
def _artnum(a):
    a = a.strip().upper()
    return ROMAN2INT.get(a) or (int(a) if a.isdigit() else None)
clauses = {}   # canonical display -> {count, pages, url}
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

# ---------- 8. Named Acts of Congress ----------
# Curated official/government URLs where a clean one exists; historical Statutes-at-Large
# era acts fall back to the Library of Congress Statutes at Large collection.
LOC_STATUTES = "https://www.loc.gov/collections/united-states-statutes-at-large/"
ACT_URLS = {
    "Social Security Act": "https://www.ssa.gov/OP_Home/ssact/ssact.htm",
    "Federal Reserve Act": "https://www.federalreserve.gov/aboutthefed/fract.htm",
    "Patriot Act": "https://www.congress.gov/bill/107th-congress/house-bill/3162",
    "Paperwork Reduction Act": "https://www.congress.gov/bill/96th-congress/senate-bill/1411",
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
    name = re.sub(r"^[A-Z]{2,5}\s+(?=[A-Z][a-z])", "", name)          # drop leading acronym (e.g. "FDIC ")
    name = name.replace("Insurance Contribution Act", "Insurance Contributions Act")  # normalise
    if name.lower() in ("the act", "act", "lord act"): continue
    year = m.group(2) or m.group(3)
    full = name + (f" of {year}" if year and f"of {year}" not in name else "")
    url = next((u for k,u in ACT_URLS.items() if k in name), LOC_STATUTES)
    e = acts.setdefault(full, {"count":0, "pages":set(), "url":url,
                               "official": any(k in name for k in ACT_URLS)})
    e["count"] += 1; e["pages"].add(page_at(m.start()))

# ---------- 9. Executive Orders ----------
# Pre-1994 EOs aren't in the Federal Register's online index, so the default is a
# search URL. Where we have a better canonical source, override it here.
EO_URL_OVERRIDES = {
    "10289": "https://www.trumanlibrary.gov/library/executive-orders/10289/executive-order-10289",
}
eos = {}
for m in re.finditer(r"(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?(\d{4,5})", text):
    num = m.group(1)
    e = eos.setdefault(num, {"count":0, "pages":set(),
        "url":EO_URL_OVERRIDES.get(num,
            f"https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=Executive+Order+{num}")})
    e["count"] += 1; e["pages"].add(page_at(m.start()))

# ---------- 10. Secondary authorities (reference works; non-government) ----------
SECONDARY = {
    "Black's Law Dictionary": "https://thelawdictionary.org/",
    "Bouvier's Law Dictionary": "https://www.constitution.org/1-Law/bouvier/bouvier.html",
}
secondary = {}
for name, url in SECONDARY.items():
    pat = name.replace("'", "[’']")
    n = len(re.findall(pat, text))
    if n: secondary[name] = {"count":n, "url":url}

# ---------- 11. IRS / Treasury guidance documents ----------
IRS_DOCS = [
    ("Internal Revenue Manual", r"Internal Revenue Manual", "https://www.irs.gov/irm"),
    ("Cumulative Bulletin", r"Cumulative Bulletin", "https://www.irs.gov/internal-revenue-bulletins"),
    ("Treasury Orders", r"Treasury Orders?", "https://home.treasury.gov/about/general-information/orders-and-directives"),
    ("IRS Determination Letters", r"Determination Letters?", "https://www.irs.gov/individuals/understanding-your-irs-notice-or-letter"),
]
irs_docs=[]
for label,pat,url in IRS_DOCS:
    n=len(re.findall(pat,text))
    if n: irs_docs.append({"document":label,"url":url,"occurrences":n})
# IRS notice codes (CPnn) — capability; the book cites none, but any that appear link to IRS
cp_notices={}
for m in re.finditer(r"\bCP[- ]?(\d{2,4})[A-Z]?\b", text):
    num=m.group(1)
    cp_notices.setdefault(num,{"count":0,"url":f"https://www.irs.gov/individuals/understanding-your-cp{num}-notice"})
    cp_notices[num]["count"]+=1
for num,v in sorted(cp_notices.items()):
    irs_docs.append({"document":f"Notice CP{num}","url":v["url"],"occurrences":v["count"]})

# ---------- URL builders ----------
def usc_url(sec):  return f"https://www.law.cornell.edu/uscode/text/26/{sec}"
def cfr_url(e):
    if e.get("part"):
        return f"https://www.law.cornell.edu/cfr/text/{e['title']}/{e['part']}"
    return f"https://www.law.cornell.edu/cfr/text/{e['title']}"
def const_url(label): return f"https://constitution.congress.gov/constitution/{CMAP[label]}/"
def form_url(k):
    slug=k.replace('Form ','').strip().lower()
    return f"https://www.irs.gov/forms-pubs/about-form-{slug}"

# ---------- emit JSON ----------
def _pkey(x):
    return (0, int(x)) if x.isdigit() else (1, 0, x)  # arabic numeric first, then roman/other
def pset(s): return sorted((x for x in s if x!="?"), key=_pkey)
out = OrderedDict()
out["scotus_and_courts"] = [
    {"cite":v["cite"], "case_name":v["name"], "full_citation":v["full"],
     "year":v["year"], "court":v["court"], "url":v["url"],
     "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(cases.items(), key=lambda kv:-kv[1]["count"])]
# general reference for the IRC as a whole -> official U.S. Code (OLRC, House.gov)
IRC_GENERAL_URL = "https://uscode.house.gov/browse/prelim@title26&edition=prelim"
irc_general = [{"section":"Internal Revenue Code (Title 26)", "url":IRC_GENERAL_URL,
                "occurrences":len(re.findall(r"Internal Revenue Code", text)), "pages":[]}]
out["usc_title26_irc"] = [e for e in irc_general if e["occurrences"]] + [
    {"section":f"26 U.S.C. § {k}", "url":usc_url(k), "occurrences":v["count"],
     "pages":pset(v["pages"])}
    for k,v in sorted(usc.items(), key=lambda kv:-kv[1]["count"])]
# general references for the CFR as a whole (Cornell LII CFR landing page)
CFR_GENERAL_URL = "https://www.law.cornell.edu/cfr/text"
cfr_general = [
    {"cite":"Code of Federal Regulations", "url":CFR_GENERAL_URL,
     "occurrences":len(re.findall(r"Code of Federal Regulations", text)), "pages":[]},
    {"cite":"CFR", "url":CFR_GENERAL_URL,
     "occurrences":len(re.findall(r"\bCFR\b", text)), "pages":[]},
]
# bare reg cites written without a "CFR" prefix (e.g. "1.1-1(a)") -> Cornell LII, section-level
_11_url = "https://www.law.cornell.edu/cfr/text/26/1.1-1"
for sub in ["(a)","(b)"]:
    n=len(re.findall(re.escape(f"1.1-1{sub}"), text))
    if n: cfr_general.append({"cite":f"26 CFR §1.1-1{sub}", "url":_11_url,
                              "occurrences":n, "pages":[]})
out["cfr"] = [e for e in cfr_general if e["occurrences"]] + [
    {"cite":k, "url":cfr_url(v), "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(cfr.items(), key=lambda kv:-kv[1]["count"])]
# Treasury Decision URLs come from the shared source of truth (single mapping,
# maintained in the transcription-agent repo, updated over time).
TD_FILE = "../../transcription-agent/TREASURY_DECISIONS.md"
td_map = {}
try:
    for line in open(TD_FILE, encoding="utf-8"):
        mnum = re.search(r"\*\*T\.D\.\s*(\d+)\*\*", line)
        urls = re.findall(r"https?://[^\s|)]+", line)  # canonical = last URL column
        if mnum and urls:
            td_map[mnum.group(1)] = urls[-1]
except FileNotFoundError:
    pass

# Local source documents: prefer a locally-stored copy when we have one.
# Scanned from citations/treasury_decisions/td_<num>/*.pdf (relative to this script).
# We record BOTH the local path and the external URL (dual-link) for now.
import os
TD_LOCAL_DIR = "treasury_decisions"
# Known caveats about the local scans (surfaced in the register, not silently trusted).
TD_LOCAL_NOTES = {
    "2815": "The 2-page scan also carries the next decision, T.D. 2816 (the earlier "
            "'may be 2816' mislabel caveat is resolved — the scan's header reads T.D. 2815).",
}
def td_local_path(num):
    """Return the relative path to a locally-stored TD PDF, or None."""
    d = os.path.join(TD_LOCAL_DIR, f"td_{num}")
    if not os.path.isdir(d):
        return None
    pdfs = sorted(f for f in os.listdir(d) if f.lower().endswith(".pdf"))
    return os.path.join(d, pdfs[0]) if pdfs else None
def td_transcript_path(num):
    """Return the relative path to the rendered HTML transcript, or None."""
    p = os.path.join(TD_LOCAL_DIR, f"td_{num}", f"td_{num}.html")
    return p if os.path.isfile(p) else None
from td_relations import load_relations, VERB_LABEL
TD_RELATIONS = load_relations()
out["treasury_decisions"] = []
# general reference: Treasury Decisions are published by the IRS in the Internal Revenue Bulletin
_td_general = len(re.findall(r"Treasury Decisions", text))
if _td_general:
    out["treasury_decisions"].append({
        "cite":"Treasury Decisions (general)", "occurrences":_td_general, "pages":[],
        "in_mapping_file": True,
        "url":"https://www.irs.gov/internal-revenue-bulletins"})
for k,v in sorted(td.items(), key=lambda kv:-kv[1]["count"]):
    num = k.replace("T.D.", "").strip()
    url = td_map.get(num)
    local = td_local_path(num)
    entry = {"cite":k, "occurrences":v["count"], "pages":pset(v["pages"]),
             "in_mapping_file": url is not None,
             "url": url or f"https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+{num}%22;a=srchls;lmt=ft"}
    if local:
        # prefer the local source document; keep the external URL as a secondary link
        entry["local_path"] = local
    tr = td_transcript_path(num)
    if tr:
        entry["transcript_path"] = tr
    rels = TD_RELATIONS.get(num)
    if rels:
        entry["relations"] = [
            {"verb": r["verb"], "num": r["to"], "basis": r.get("basis", ""),
             "transcript": td_transcript_path(r["to"])}
            for r in rels]
    notes = []
    if url is None:
        notes.append("NOT YET in TREASURY_DECISIONS file — add it there; fallback is a HathiTrust search.")
    if num in TD_LOCAL_NOTES:
        notes.append(TD_LOCAL_NOTES[num])
    if notes:
        entry["note"] = " ".join(notes)
    out["treasury_decisions"].append(entry)
out["constitution"] = [
    {"ref":k, "url":v.get("url") or const_url(k), "occurrences":v["count"]}
    for k,v in sorted(const.items(), key=lambda kv:-kv[1]["count"])]
out["irs_forms"] = [
    {"form":k, "url":form_url(k), "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(forms.items(), key=lambda kv:-kv[1]["count"])]
out["constitutional_clauses"] = [
    {"citation":k, "url":v["url"], "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(clauses.items())]
out["acts_of_congress"] = [
    {"act":k, "url":v["url"], "official_source":v["official"],
     "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(acts.items(), key=lambda kv:-kv[1]["count"])]
out["executive_orders"] = [
    {"executive_order":f"E.O. {k}", "url":v["url"], "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(eos.items())]
out["secondary_authorities"] = [
    {"work":k, "url":v["url"], "occurrences":v["count"]}
    for k,v in sorted(secondary.items(), key=lambda kv:-kv[1]["count"])]
out["irs_treasury_documents"] = irs_docs

json.dump(out, open("link_register.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)

# ---------- emit Markdown ----------
L=[]
L.append("# Link Register — *Income Tax: Shattering The Myths*\n")
L.append("Authoritative-source links for enriching the interactive HTML edition. "
         "URLs are deterministic where the source allows (Justia for *U.S. Reports*, "
         "Cornell LII for USC/CFR, Constitution Annotated). Items marked **verify** "
         "need a human check — usually because the case name was OCR-garbled or the "
         "cite is a lower-court/parallel reporter without a deterministic URL.\n")
L.append(f"- Source text: `{MD}`")
L.append(f"- Generated by `build_register.py` (re-run to refresh)\n")

L.append("\n## 1. SCOTUS & court cases\n")
L.append("_Full citation (name · reporter cite · year). U.S. Reports link to Justia; other courts to a CourtListener search._\n")
L.append("| Full citation | Court | Occ. | Pages | Link |")
L.append("|---|---|---:|---|---|")
for c in out["scotus_and_courts"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['full_citation']} | {c['court']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

L.append("\n## 2. Title 26 U.S.C. (Internal Revenue Code) sections\n")
L.append("_Note: bare “section NNNN” references in the text are IRC (Title 26) sections; verify a few against context (a handful may be quoting other titles)._\n")
L.append("| Section | Occ. | Pages | Cornell LII |")
L.append("|---|---:|---|---|")
for c in out["usc_title26_irc"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['section']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

L.append("\n## 3. Code of Federal Regulations (CFR)\n")
L.append("| Cite | Occ. | Pages | Cornell LII |")
L.append("|---|---:|---|---|")
for c in out["cfr"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['cite']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

L.append("\n## 4. Treasury Decisions (T.D.)\n")
L.append("_External URLs are sourced from the shared mapping `transcription-agent/TREASURY_DECISIONS.md` "
         "(single source of truth, updated over time). Where a **local copy** is stored under "
         "`citations/treasury_decisions/td_<num>/`, it is the primary source and the external link is kept "
         "as a secondary. Rows marked **add to mapping** are cited in this book but not yet in that file._\n")
L.append("| T.D. | Occ. | Pages | Status | Source |")
L.append("|---|---:|---|---|---|")
for c in out["treasury_decisions"]:
    pgs=", ".join(c["pages"][:6])
    status = "in mapping" if c["in_mapping_file"] else "**add to mapping**"
    if c.get("local_path"):
        src = f"[local copy]({quote(c['local_path'])}) · [external]({c['url']})"
    else:
        src = f"[link]({c['url']})"
    if c.get("transcript_path"):
        src += f" · [transcript]({quote(c['transcript_path'])})"
    for r in c.get("relations", []):
        tgt = (f"[T.D. {r['num']}]({quote(r['transcript'])})"
               if r.get("transcript") else f"T.D. {r['num']}")
        src += f"<br>{VERB_LABEL[r['verb']]} {tgt}"
    if c.get("note"):
        src += f"<br>⚠ {c['note']}"
    L.append(f"| {c['cite']} | {c['occurrences']} | {pgs} | {status} | {src} |")

L.append("\n## 5. Constitution & founding documents\n")
L.append("_Constitution refs link to the Constitution Annotated; founding documents (e.g. the Declaration of Independence) link to the National Archives._\n")
L.append("| Reference | Occ. | Source |")
L.append("|---|---:|---|")
for c in out["constitution"]:
    L.append(f"| {c['ref']} | {c['occurrences']} | [link]({c['url']}) |")

L.append("\n## 6. IRS forms\n")
L.append("_Links point to current IRS “About Form” pages; the book often discusses historical versions._\n")
L.append("| Form | Occ. | Pages | IRS |")
L.append("|---|---:|---|---|")
for c in out["irs_forms"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['form']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

L.append("\n## 7. Constitutional provisions (Article / Section / Clause)\n")
L.append("_Deep-linked to the Constitution Annotated (congress.gov) at the section level._\n")
L.append("| Provision | Occ. | Pages | Constitution Annotated |")
L.append("|---|---:|---|---|")
for c in out["constitutional_clauses"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['citation']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

L.append("\n## 8. Named Acts of Congress\n")
L.append("_Official government sources where a clean one exists (SSA, Federal Reserve, congress.gov); "
         "historical Statutes-at-Large-era acts link to the Library of Congress Statutes at Large collection._\n")
L.append("| Act | Occ. | Pages | Source |")
L.append("|---|---:|---|---|")
for c in out["acts_of_congress"]:
    pgs=", ".join(c["pages"][:6])
    tag = "" if c["official_source"] else " _(Statutes at Large)_"
    L.append(f"| {c['act']} | {c['occurrences']} | {pgs} | [link]({c['url']}){tag} |")

L.append("\n## 9. Executive Orders\n")
L.append("_Linked to a Federal Register search for the numbered order._\n")
L.append("| Executive Order | Occ. | Pages | Federal Register |")
L.append("|---|---:|---|---|")
for c in out["executive_orders"]:
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['executive_order']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

if out["secondary_authorities"]:
    L.append("\n## 10. Secondary authorities (reference works)\n")
    L.append("_Reference works cited in the text (non-government sources)._\n")
    L.append("| Work | Occ. | Source |")
    L.append("|---|---:|---|")
    for c in out["secondary_authorities"]:
        L.append(f"| {c['work']} | {c['occurrences']} | [link]({c['url']}) |")

if out["irs_treasury_documents"]:
    L.append("\n## 11. IRS & Treasury guidance documents\n")
    L.append("_IRS/Treasury document types cited in the text, linked to official sources. "
             "(No numbered IRS notice codes such as CP54 are cited anywhere in the book.)_\n")
    L.append("| Document | Occ. | Source |")
    L.append("|---|---:|---|")
    for c in out["irs_treasury_documents"]:
        L.append(f"| {c['document']} | {c['occurrences']} | [link]({c['url']}) |")

open("link_register.md","w",encoding="utf-8").write("\n".join(L)+"\n")

print("SCOTUS/court cites :", len(out["scotus_and_courts"]))
print("USC/IRC sections   :", len(out["usc_title26_irc"]))
print("CFR cites          :", len(out["cfr"]))
print("Treasury Decisions :", len(out["treasury_decisions"]))
print("Constitution refs  :", len(out["constitution"]))
print("IRS forms          :", len(out["irs_forms"]))
print("wrote link_register.md + link_register.json")
