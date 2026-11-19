#!/usr/bin/env python3
"""Build a register of legal citations (SCOTUS, USC/IRC, CFR, Treasury Decisions,
constitutional refs, IRS forms) from the cleaned MD, mapped to authoritative URLs.
Emits link_register.md (human) and link_register.json (for HTML enrichment)."""
import re, json, sys
import urllib.request, urllib.error
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
# NOTE (2026-11-13): widened from digit-only (`\d{3,4}[- ]?[A-Z]{0,3}`) to also
# catch letter-prefixed forms ("W-9", "W-4", "W-2", "I-9", "W-8BEN") — the old
# pattern required the token to START with a digit, so it silently never
# matched any W-/I- form no matter how often the book named it. Found while
# backfilling citations into the video synthesis: book #1 says "Form W-9" 54x,
# "Form W-4" 58x, "Form W-2" 32x, and NONE were ever linked. Still requires
# the literal word "Form" before the token (same ambiguity guard as before —
# a bare "W-9s" with no "Form" prefix is still not captured).
forms = defaultdict(lambda: {"count":0,"pages":set()})
FORM_RX = re.compile(r"Form\s+([A-Z]{0,2}-?\d{1,4}(?:[- ]?[A-Z]{1,4})?)")
for m in FORM_RX.finditer(text):
    k = "Form " + re.sub(r"\s+", "-", m.group(1).strip())
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
    # Not strictly "non-government" (it's a presidential commission report),
    # but no other category fits either -- added 2026-11-13, cited 3x in
    # book #1. archive.org has the full report (PDF + OCR text, verified
    # resolving); the Reagan Library's page is a finding-aid description
    # only, not the document.
    "Grace Commission": "https://archive.org/details/GraceCommissionReport",
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
# Curated overrides for forms whose live URL doesn't follow the plain
# about-form-<lowercased-number> pattern, or that aren't IRS forms at all.
# URLs copied from the sibling transcription-agent publisher's _FORM_URLS map
# (already verified there) rather than re-guessed.
FORM_URL_OVERRIDES = {
    "Form W-9": "https://www.irs.gov/forms-pubs/about-form-w-9",
    "Form W-4": "https://www.irs.gov/forms-pubs/about-form-w-4",
    "Form W-2": "https://www.irs.gov/forms-pubs/about-form-w-2",
    "Form W-8BEN": "https://www.irs.gov/forms-pubs/about-form-w-8-ben",
    "Form I-9": "https://www.uscis.gov/i-9",  # USCIS form, not IRS
    "Form 1040NR": "https://www.irs.gov/forms-pubs/about-form-1040-nr",  # real slug is hyphenated; book text has no hyphen
    # SSA form, not IRS. URL corroborated by multiple independent search
    # results (ssa.gov, teachmepersonalfinance.com, immi-usa.com all agree)
    # but could not be curl-verified — ssa.gov 403s all automated requests,
    # same bot-protection pattern seen on Justia/HathiTrust this session.
    "Form SS-5": "https://www.ssa.gov/forms/ss-5.pdf",
}

_FORM_URL_CACHE: dict = {}

def _url_resolves(url: str) -> bool:
    if url in _FORM_URL_CACHE:
        return _FORM_URL_CACHE[url]
    ok = False
    try:
        req = urllib.request.Request(url, method="HEAD",
                                      headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status == 200
    except Exception:
        ok = False
    _FORM_URL_CACHE[url] = ok
    return ok

unresolved_forms = []  # (form, guessed_url) pairs that failed verification — reported, not linked

def form_url(k):
    if k in FORM_URL_OVERRIDES:
        return FORM_URL_OVERRIDES[k]
    slug = k.replace("Form ", "").strip().lower()
    url = f"https://www.irs.gov/forms-pubs/about-form-{slug}"
    if _url_resolves(url):
        return url
    unresolved_forms.append((k, url))
    return None

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
# Treasury Decisions come from tds.json in the DogThatHunts/treasury-decisions repo
# (local checkout ~/Projects/treasury-decisions, a sibling of law_sovereignty), the
# single source of truth since 2026-11-19. It replaced TREASURY_DECISIONS.md (URLs),
# the local citations/treasury_decisions/td_<N>/ scans and td_relations.json here.
# A missing tds.json STOPS the build: the old code swallowed a bad path and silently
# fell back to HathiTrust for every TD (2026-11-16), which must not happen again.
import os
_TDS_JSON = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "..", "..", "treasury-decisions", "tds.json"))
try:
    _TDS = json.load(open(_TDS_JSON, encoding="utf-8"))["tds"]
except (OSError, ValueError, KeyError) as e:
    raise SystemExit(f"build_register: cannot read {_TDS_JSON} ({e}); "
                     "clone DogThatHunts/treasury-decisions next to law_sovereignty")
td_map = {n: t["page"] for n, t in _TDS.items()}
# Known caveats about the scans (surfaced in the register, not silently trusted).
TD_LOCAL_NOTES = {
}
def td_local_path(num):
    """URL of the TD's scan (PDF) in treasury-decisions, or None."""
    t = _TDS.get(num)
    return t["pdf"] if t else None
def td_transcript_path(num):
    """URL of the TD's transcript page in treasury-decisions, or None."""
    t = _TDS.get(num)
    return t["page"] if t else None
TD_RELATIONS = {n: t.get("relations", []) for n, t in _TDS.items() if t.get("relations")}
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
        notes.append("NOT YET in treasury-decisions (tds.json); add it there. Fallback is a HathiTrust search.")
    if num in TD_LOCAL_NOTES:
        notes.append(TD_LOCAL_NOTES[num])
    if notes:
        entry["note"] = " ".join(notes)
    out["treasury_decisions"].append(entry)
out["constitution"] = [
    {"ref":k, "url":v.get("url") or const_url(k), "occurrences":v["count"]}
    for k,v in sorted(const.items(), key=lambda kv:-kv[1]["count"])]
out["irs_forms"] = [
    {"form":k, "url":url, "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(forms.items(), key=lambda kv:-kv[1]["count"])
    if (url := form_url(k)) is not None]  # unresolved (404) guesses are dropped, not linked — see unresolved_forms
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

# ---------- manual additions (NOT derived from scanning this book's text) ----------
# These citations are known-relevant to the broader Dave Champion corpus (the
# video-transcript synthesis) but never appear in book #1's own text, so the
# scanning loops above can never find them no matter how the regexes are
# tuned. Added 2026-11-14 per the user: citations found anywhere in the
# corpus belong in this one master register, in case they're ever encountered
# elsewhere, not just scattered across each consumer's own curated map. Each
# entry carries a "source" field recording where it actually came from.
# Unlike the scanning loops, these do NOT get overwritten/lost on a re-run —
# they're appended here every time, so they're durable by construction.
MANUAL_SCOTUS = [
    {"cite": "602 U.S. 572", "case_name": "Moore v. United States",
     "full_citation": "Moore v. United States, 602 U.S. 572 (2024)",
     "year": "2024", "court": "U.S. Supreme Court",
     "url": "https://www.law.cornell.edu/supremecourt/text/22-800",
     "occurrences": 0, "pages": [],
     "source": "video_synthesis_2026-11-13"},
]
MANUAL_FORMS = [
    # User-supplied URLs (2026-11-14), verified resolving (HTTP 200).
    {"form": "Form 1099-NEC", "url": "https://www.irs.gov/instructions/i1099mec",
     "occurrences": 0, "pages": [], "source": "video_synthesis_2026-11-13"},
    {"form": "Form 1099-INT", "url": "https://www.irs.gov/instructions/i1099int",
     "occurrences": 0, "pages": [], "source": "video_synthesis_2026-11-13"},
    {"form": "Form 1099-DIV", "url": "https://www.irs.gov/instructions/i1099div",
     "occurrences": 0, "pages": [], "source": "video_synthesis_2026-11-13"},
]
# T.D. 2090/2109/4707 are cited on-camera (rows 1247, 1217, 1253) but never appear
# in book #1's text, so the scanning loop above can never produce them — same
# reason MANUAL_SCOTUS/MANUAL_FORMS exist. "summary" is a new field (2026-11-14,
# researched via web search + a public-domain 1915 treatise's verbatim text, since
# HathiTrust/Google Books both block automated search-within-book access to the
# relevant volumes) — plain prose explaining what the decision actually says,
# which "url" alone can't carry and which TREASURY_DECISIONS.md's table format
# doesn't have room for either (its Notes section carries the full version).
# Nothing downstream reads "summary" yet (build_html.py's td_map only ever reads
# ("td", ...)["url"]), so adding it is additive — no existing consumer breaks.
MANUAL_TD = [
    {"cite": "T.D. 2090", "occurrences": 0, "pages": [],
     "in_mapping_file": "2090" in td_map,
     "url": td_map.get("2090",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+2090%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("2090"),
     "transcript_path": td_transcript_path("2090"),
     "summary": (
         "Dec. 14, 1914 — \"Synopsis of rulings on questions relating to the income "
         "tax imposed by Section 2 of the Act of October 3, 1913.\" A large "
         "alphabetical (A-Z) digest of dozens of unrelated administrative rulings "
         "(deductions, withholding, annuities, fiduciaries, bad debts, etc.) for IRS "
         "officers. It does not define who the income tax applies to as a class of "
         "filer. Verbatim text (pp. 1456-1486) found in the public-domain 1915 "
         "treatise \"Foster's Income Tax\" (non-government mirror, link not durable). "
         "Primary source found 2026-11-16: HathiTrust uc1.a0001809318 seq 271-294 "
         "(24 pages, the full digest), downloaded via browser and merged into the "
         "local PDF above. Pages 271-287 carry Google's original OCR text layer; "
         "pages 288-294 (which had none -- image-only Google scans) were run "
         "through tesseract (300dpi gray via pdftoppm, matching the pattern "
         "already used for td_2382/td_2815) and merged back in with a real text "
         "layer, same day. All 24 pages are now searchable/extractable."),
     "source": "video_synthesis_2026-11-14"},
    {"cite": "T.D. 2109", "occurrences": 0, "pages": [],
     "in_mapping_file": "2109" in td_map,
     "url": td_map.get("2109",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+2109%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("2109"),
     "transcript_path": td_transcript_path("2109"),
     "summary": (
         "Dec. 28, 1914 — \"Amendment of Article 8 of Regulations 33, providing for "
         "the collection of tax on income of non-resident aliens.\" A narrow "
         "procedural amendment setting withholding mechanics specifically for "
         "non-resident aliens' U.S.-source income, alongside (not instead of) the "
         "citizen/resident-alien rules the same regulations already covered. Genuinely "
         "about non-resident aliens, but regulates one filer category among several — "
         "doesn't confine the tax to that category. Verbatim text (pp. 1487-1488) in "
         "the same Foster treatise. Primary source found 2026-11-16: HathiTrust "
         "uc1.a0001809318 seq 317-318 (2 pages, full decision text, text layer "
         "present), downloaded and merged into the local PDF above."),
     "source": "video_synthesis_2026-11-14"},
    {"cite": "T.D. 4707", "occurrences": 0, "pages": [],
     "in_mapping_file": "4707" in td_map,
     "url": td_map.get("4707",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+4707%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("4707"),
     "transcript_path": td_transcript_path("4707"),
     "summary": (
         "Nov. 16, 1936 -- \"Liquor Tax Administration Act. Openings for "
         "ventilation or heating in internal revenue bonded warehouses.\" "
         "Amends paragraph 3 of T.D. 4651, setting warehouse construction/"
         "ventilation specs for bonded liquor warehouses. Chas. T. Russell, "
         "Acting Commissioner; Stephen B. Gibbons, Acting Secretary of the "
         "Treasury. PRIMARY SOURCE FOUND AND VERIFIED 2026-11-16: HathiTrust "
         "'Internal revenue bulletin 1936' (uiug.30112102075568), seq 1717 -- "
         "this REFUTES the previous inferred guess kept in this file's history: "
         "that T.D. 4707 was part of a November 1936 batch of Social Security/"
         "SS-5 implementing decisions, based only on its number being close to "
         "T.D. 4704 (the actual SS account-number decision). It is NOT -- it's "
         "an unrelated liquor-tax warehouse regulation. **Row 1253 cites T.D. "
         "4707 re: the SS-5 application -- that citation is a misattribution "
         "in the source video, not a sourcing gap on our end: Champion says "
         "\"4707\" on camera but reads text that is actually T.D. 4704's. "
         "HAND-CORRECTED 2026-11-16, based on this research: row 1253's "
         "citation is now tracked against T.D. 4704 (see that entry), not "
         "this one. T.D. 4707 itself is correctly sourced above and real, "
         "just not actually cited anywhere in the Dave Champion corpus."),
     "source": "video_synthesis_2026-11-16"},
    {"cite": "T.D. 4704", "occurrences": 0, "pages": [],
     "local_path": td_local_path("4704"),
     "transcript_path": td_transcript_path("4704"),
     "in_mapping_file": "4704" in td_map,
     "url": td_map.get("4704",
         "https://babel.hathitrust.org/cgi/pt?id=uiug.30112102075568&seq=1640"),
     "summary": (
         "Nov. 5, 1936 (XV-45-8383) -- \"Identification of taxpayers under "
         "Title VIII of the Social Security Act -- Assignment of "
         "identification numbers to employers and account numbers to "
         "employees.\" Article 5 (p. 21): \"Every individual who is an "
         "employee on November 24, 1936, shall file an application for an "
         "account number on Form SS-5\" -- the exact line row 1253 quotes "
         "on-camera, attributed there to \"Treasury Decision 4707.\" "
         "HAND-CORRECTED 2026-11-16: verified by content (HathiTrust "
         "'Internal revenue bulletin 1936', uiug.30112102075568, seq "
         "1640-1643) that this text is T.D. 4704, not T.D. 4707 (an unrelated "
         "liquor-tax warehouse decision, see that entry) -- Champion "
         "misspoke the number on camera. Row 1253's citation moved here from "
         "T.D. 4707."),
     "source": "video_synthesis_2026-11-16"},
    {"cite": "T.D. 1953", "occurrences": 0, "pages": [],
     "in_mapping_file": "1953" in td_map,
     "url": td_map.get("1953",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+1953%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("1953"),
     "transcript_path": td_transcript_path("1953"),
     "summary": (
         "March 2, 1914 -- \"Extension of time for filing returns under "
         "income-tax law by citizens of the United States living abroad.\" "
         "Falls in Treasury Decisions Under Internal Revenue Laws, Vol. 16 "
         "(Jan.-Dec. 1914, covers T.D. 1927-2112) -- same volume as T.D. "
         "2090/2109. Cited on-camera (row 5612, per transcription-agent/"
         "TREASURY_DECISIONS.md), recited as part of a 10-TD list, not "
         "individually discussed. Primary source found 2026-11-16: HathiTrust "
         "uc1.a0001809318 seq 46 (1 page, complete, text layer present), "
         "downloaded and saved to the local PDF above."),
     "source": "video_synthesis_2026-11-16"},
    {"cite": "T.D. 2013", "occurrences": 0, "pages": [],
     "in_mapping_file": "2013" in td_map,
     "url": td_map.get("2013",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+2013%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("2013"),
     "transcript_path": td_transcript_path("2013"),
     "summary": (
         "Aug. 12, 1914 -- \"Nonresident aliens -- Amendment of article 8 of "
         "Regulations 33, providing for the collection of tax on income of "
         "nonresident aliens derived from trades or professions in the United "
         "States.\" Same Vol. 16 as T.D. 1953/2090/2109. Cited on-camera (row "
         "5612), recited as part of a 10-TD list. Primary source found "
         "2026-11-16: HathiTrust uc1.a0001809318 seq 130-131 (2 pages, "
         "complete, text layer present), downloaded and merged into the local "
         "PDF above."),
     "source": "video_synthesis_2026-11-16"},
    {"cite": "T.D. 2190", "occurrences": 0, "pages": [],
     "in_mapping_file": "2190" in td_map,
     "url": td_map.get("2190",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+2190%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("2190"),
     "transcript_path": td_transcript_path("2190"),
     "summary": (
         "April 21, 1915 -- \"Income tax -- Temporary certificate, Form 1005.\" "
         "Falls in Treasury Decisions Under Internal Revenue Laws, Vol. 17 "
         "(Jan.-Dec. 1915, covers T.D. 2113-2276) -- a different volume from "
         "T.D. 2090/2109/1953/2013 (Vol. 16), same bound item though "
         "(uc1.a0001809318 covers v.16-19). Cited on-camera (row 5612), "
         "recited as part of a 10-TD list. Primary source found 2026-11-16: "
         "HathiTrust seq 490 (1 page, complete, text layer present), "
         "downloaded and saved to the local PDF above."),
     "source": "video_synthesis_2026-11-16"},
    {"cite": "T.D. 2402", "occurrences": 0, "pages": [],
     "in_mapping_file": "2402" in td_map,
     "url": td_map.get("2402",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+2402%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("2401"),
     "transcript_path": td_transcript_path("2402"),
     "relations": [
         {"verb": r["verb"], "num": r["to"], "basis": r.get("basis", ""),
          "transcript": td_transcript_path(r["to"])}
         for r in TD_RELATIONS.get("2402", [])],
     "summary": (
         "Nov. 29, 1916 — \"Amending T.D. 2313 of March 21, 1916, as to payment "
         "of income tax for nonresident aliens, so as to relieve their agents or "
         "representatives in the United States from the duty of paying tax for "
         "said nonresident aliens in certain cases.\" Has a local transcript "
         "(extracted from the same multi-decision bulletin PDF as T.D. 2401,  "
         "citations/treasury_decisions/td_2402/) but, unlike those two, is never "
         "literally cited by number in either book's text -- only reachable via "
         "T.D. 2401/2313's relations field -- same reason MANUAL_TD exists for "
         "2090/2109/4707. Cited on-camera (row 5612, per transcription-agent/"
         "TREASURY_DECISIONS.md)."),
     "source": "td_local_copy_backfill_2026-11-16"},
    {"cite": "T.D. 8881", "occurrences": 0, "pages": [],
     "in_mapping_file": "8881" in td_map,
     "url": td_map.get("8881",
         "https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+8881%22;a=srchls;lmt=ft"),
     "local_path": td_local_path("8881"),
     "transcript_path": td_transcript_path("8881"),
     "summary": (
         "May 22, 2000 (65 FR 32152) — \"Revisions to Regulations Relating to "
         "Withholding of Tax on Certain U.S. Source Income Paid to Foreign "
         "Persons and Revisions of Information Reporting Regulations.\" "
         "Amends its companion T.D. 8734 (sections 1441-1443, 6041 et al.), "
         "effective Jan. 1, 2001 -- same withholding-on-foreign-persons ground "
         "Champion leans on for both. Cited in 7 video rows per "
         "transcription-agent/TREASURY_DECISIONS.md (1234, 1239, 1243, 1247, "
         "1249, 1254, 5600), never in either book's text -- same reason "
         "MANUAL_TD exists for 2090/2109/4707/2402. Re-sourced 2026-11-16: the "
         "local PDF previously here was a mismatched 2001 FAA aviation rule "
         "(removed); the IRS hosts the real document directly at "
         "irs.gov/pub/irs-regs/td8881.pdf (HTTP 200 -- the prior \"404 "
         "confirmed\" note only ever checked the .txt extension, which does "
         "404). A web search's first candidate for the April 2001 correction "
         "notice (govinfo.gov .../01-8136.pdf) turned out to be the SAME "
         "wrong aviation document by a different route -- verified by content "
         "before trusting it, not by filename/size match alone."),
     "source": "td_8881_resourced_2026-11-16"},
]

# ---------- manual additions from American Tax Bible (book #2) backfill ----------
# Book #2's own build_new_citations.py diffs its text against this register and
# parks what's missing in new_citations.md (331 entries as of 2026-11-15) rather
# than folding it in -- same durability problem MANUAL_SCOTUS/FORMS/TD exist for.
# User asked (2026-11-15) to fold the full parked batch in, explicitly skipping
# per-entry live URL verification -- these URLs are the SAME deterministic/
# courtlistener-search constructions build_html.py's own fallback already
# produces for an unregistered cite, so folding them changes no book-2 rendering;
# the point is making them available register-wide (video synthesis, other
# books), per the same principle MANUAL_SCOTUS was added under. NOT verified to
# resolve -- some guessed IRS form "about-form-*" URLs may 404 (unlike the
# scanning loop's own form_url(), which drops unresolved guesses). A few
# regex/OCR artifacts were spotted but left as-is per that same instruction
# (e.g. "01 CFR", "26 U.S.C. § 14418", "Pot Paperwork Reduction Act",
# "For Certain Excise Tax Act") -- flag for human cleanup, not auto-fixed.

MANUAL_BOOK2_IMPORT_SCOTUS = [
    {"cite": "486 U.S. 800", "case_name": "Christianson v. Colt Industries Operating Co",
     "full_citation": "Christianson v. Colt Industries Operating Co. 486 U.S. 800", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/486/800/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "449 U.S. 368", "case_name": "Firestone Tire & Rubber Co. v. Risjord",
     "full_citation": "Firestone Tire & Rubber Co. v. Risjord. 449 U.S. 368", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/449/368/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "920 F.2d 619", "case_name": "United States v. Collins",
     "full_citation": "United States v. Collins. 920 F.2d 619 at 629", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Collins%20920%20F.2d%20619", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "177 U.S. 505", "case_name": "Shoshone Mining Co. v. Rutter",
     "full_citation": "Shoshone Mining Co. v. Rutter. 177 U.S. 505 at 513 (1900)", "year": "1900", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/177/505/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "490 U.S. 545", "case_name": "Finley v. United States",
     "full_citation": "Finley v. United States. 490 U.S. 545 (1989)", "year": "1989", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/490/545/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "755 F.2d 517", "case_name": "Lovell v. United States",
     "full_citation": "Lovell v. United States. 755 F.2d 517 at 518", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Lovell%20v.%20United%20States%20755%20F.2d%20517", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "632 F.2d 706", "case_name": "Broughton v. United States",
     "full_citation": "Broughton v. United States. 632 F.2d 706", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Broughton%20v.%20United%20States%20632%20F.2d%20706", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "503 U.S. 249", "case_name": "Connecticut National Bank v. Germain",
     "full_citation": "Connecticut National Bank v. Germain. 503 U.S. 249", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/503/249/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "460 F.3d 79", "case_name": "Murphy v. I.R.S",
     "full_citation": "Murphy v. I.R.S. 460 F.3d 79", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Murphy%20v.%20I.R.S%20460%20F.3d%2079", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "498 F.2d 1160", "case_name": "United States v. Critzer",
     "full_citation": "United States v. Critzer. 498 F.2d 1160", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Critzer%20498%20F.2d%201160", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "762 F.2d 361", "case_name": "United States v. Mallas",
     "full_citation": "United States v. Mallas. 762 F.2d 361", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Mallas%20762%20F.2d%20361", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "607 F.2d 92", "case_name": "States v. Garber",
     "full_citation": "States v. Garber. 607 F.2d 92 at 97-98", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=States%20v.%20Garber%20607%20F.2d%2092", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "713 F.2d 1423", "case_name": "United States v. Dahlstrom",
     "full_citation": "United States v. Dahlstrom. 713 F.2d 1423 at 1429", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Dahlstrom%20713%20F.2d%201423", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "830 F.2d 150", "case_name": "United States v. Heller",
     "full_citation": "United States v. Heller. 830 F.2d 150", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Heller%20830%20F.2d%20150", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "942 F.2d 1125", "case_name": "United States v. Harris",
     "full_citation": "United States v. Harris. 942 F.2d 1125", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Harris%20942%20F.2d%201125", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "496 F.2d 204", "case_name": "United States v. Insco",
     "full_citation": "United States v. Insco. 496 F.2d 204", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Insco%20496%20F.2d%20204", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "766 F.2d 676", "case_name": "United States v. Anzalone",
     "full_citation": "United States v. Anzalone. 766 F.2d 676 at 681-82", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Anzalone%20766%20F.2d%20676", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "779 F.2d 1559", "case_name": "United States v. Denemark",
     "full_citation": "United States v. Denemark. 779 F.2d 1559", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Denemark%20779%20F.2d%201559", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "780 F.2d 758", "case_name": "United States v. Varbel",
     "full_citation": "United States v. Varbel. 780 F.2d 758 at 762", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Varbel%20780%20F.2d%20758", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "781 F.2d 1432", "case_name": "United States v. Dela Espriella",
     "full_citation": "United States v. Dela Espriella. 781 F.2d 1432", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Dela%20Espriella%20781%20F.2d%201432", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "796 F.2d 244", "case_name": "United States v. Larson",
     "full_citation": "United States v. Larson. 796 F.2d 244", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Larson%20796%20F.2d%20244", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "240 U.S. 115", "case_name": "Tyee Realty Co. v. Anderson",
     "full_citation": "Tyee Realty Co. v. Anderson. 240 U.S. 115 at 36", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/240/115/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "802 F.2d 10", "case_name": "United States v. Turano",
     "full_citation": "United States v. Turano. 802 F.2d 10 at 12", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Turano%20802%20F.2d%2010", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "171 F.2d 464", "case_name": "Jandorf's Estate v. Commissioner",
     "full_citation": "Jandorf's Estate v. Commissioner. 171 F.2d 464 at 465", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Jandorf%27s%20Estate%20v.%20Commissioner%20171%20F.2d%20464", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "751 F.2d 85", "case_name": "Ficalora v. Commissioner",
     "full_citation": "Ficalora v. Commissioner. 751 F.2d 85 at 87", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Ficalora%20v.%20Commissioner%20751%20F.2d%2085", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "845 F.2d 43", "case_name": "United States v. Sitka",
     "full_citation": "United States v. Sitka. 845 F.2d 43 at 46", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Sitka%20845%20F.2d%2043", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "133 F.2d 894", "case_name": "Keasbey & Mattison Co. v. Rothensies",
     "full_citation": "Keasbey & Mattison Co. v. Rothensies. 133 F.2d 894 at 897", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Keasbey%20%26%20Mattison%20Co.%20v.%20Rothensies%20133%20F.2d%20894", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "277 F.2d 16", "case_name": "Penn Mutual Indemnity Co. v. Commissioner",
     "full_citation": "Penn Mutual Indemnity Co. v. Commissioner. 277 F.2d 16 at 19", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Penn%20Mutual%20Indemnity%20Co.%20v.%20Commissioner%20277%20F.2d%2016", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "89 F.2d 775", "case_name": "White Packing Co. v. Robertson",
     "full_citation": "White Packing Co. v. Robertson. 89 F.2d 775 at 779", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=White%20Packing%20Co.%20v.%20Robertson%2089%20F.2d%20775", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "972 F.2d 723", "case_name": "United States v. Gaumer",
     "full_citation": "United States v. Gaumer. 972 F.2d 723 at 725", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Gaumer%20972%20F.2d%20723", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "724 F.2d 469", "case_name": "Parker v. Commissioner",
     "full_citation": "Parker v. Commissioner. 724 F.2d 469 at 471", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Parker%20v.%20Commissioner%20724%20F.2d%20469", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "791 F.2d 68", "case_name": "Coleman v. Commissioner",
     "full_citation": "Coleman v. Commissioner. 791 F.2d 68 at 70", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Coleman%20v.%20Commissioner%20791%20F.2d%2068", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "614 F.2d 617", "case_name": "United States v. Francisco",
     "full_citation": "United States v. Francisco. 614 F.2d 617 at 619", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Francisco%20614%20F.2d%20617", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "670 F.2d 923", "case_name": "United States v. Lawson",
     "full_citation": "United States v. Lawson. 670 F.2d 923 at 927", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Lawson%20670%20F.2d%20923", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "363 U.S. 509", "case_name": "Aquilino v. United States",
     "full_citation": "Aquilino v. United States. 363 U.S. 509 at 512-13", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/363/509/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "575 F.2d 1097", "case_name": "United States v. Baldwin",
     "full_citation": "United States v. Baldwin. 575 F.2d 1097 at 1098", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Baldwin%20575%20F.2d%201097", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "247 F. 669", "case_name": "Samet v. Farmers' & Merchants' Nat. Bank",
     "full_citation": "Samet v. Farmers' & Merchants' Nat. Bank. 247 F. 669 at 671", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Samet%20v.%20Farmers%27%20%26%20Merchants%27%20Nat.%20Bank%20247%20F.%20669", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "617 F.2d 1293", "case_name": "St. Louis Union Trust Co. v. United States",
     "full_citation": "St. Louis Union Trust Co. v. United States. 617 F.2d 1293 at 1301", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=St.%20Louis%20Union%20Trust%20Co.%20v.%20United%20States%20617%20F.2d%201293", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "252 F.2d 434", "case_name": "Sims v. United States",
     "full_citation": "Sims v. United States. 252 F.2d 434 at 437", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Sims%20v.%20United%20States%20252%20F.2d%20434", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "356 F.2d 269", "case_name": "Kolb v. Berlin",
     "full_citation": "Kolb v. Berlin. 356 F.2d 269 at 271", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Kolb%20v.%20Berlin%20356%20F.2d%20269", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "514 F.2d 794", "case_name": "United States v. Briggs",
     "full_citation": "United States v. Briggs. 514 F.2d 794 at 798", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Briggs%20514%20F.2d%20794", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "970 F.2d 750", "case_name": "James v. United States",
     "full_citation": "James v. United States. 970 F.2d 750 at 755", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=James%20v.%20United%20States%20970%20F.2d%20750", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "886 F.2d 714", "case_name": "Inc. v. West Virginia Workers' Comp. Fund",
     "full_citation": "Inc. v. West Virginia Workers' Comp. Fund. 886 F.2d 714 at 719", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Inc.%20v.%20West%20Virginia%20Workers%27%20Comp.%20Fund%20886%20F.2d%20714", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "337 S.W.2d 453", "case_name": "Jack Cole Co. v. MacFarland",
     "full_citation": "Jack Cole Co. v. MacFarland. 337 S.W.2d 453 at 455-56", "year": "", "court": "State / other court",
     "url": "https://www.courtlistener.com/?q=Jack%20Cole%20Co.%20v.%20MacFarland%20337%20S.W.2d%20453", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "830 F.2d 985", "case_name": "United States v. Albertini",
     "full_citation": "United States v. Albertini. 830 F.2d 985 at 989", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Albertini%20830%20F.2d%20985", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "321 U.S. 219", "case_name": "Commissioner v. Lane-Wells Co",
     "full_citation": "Commissioner v. Lane-Wells Co. 321 U.S. 219 at 222", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/321/219/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "8 F.2d 913", "case_name": "Updike v. United States",
     "full_citation": "Updike v. United States. 8 F.2d 913 at 915", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Updike%20v.%20United%20States%208%20F.2d%20913", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "354 F.2d 323", "case_name": "True v. United States",
     "full_citation": "True v. United States. 354 F.2d 323 at 324", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=True%20v.%20United%20States%20354%20F.2d%20323", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "260 F. Supp. 423", "case_name": "United States v. Carlson",
     "full_citation": "United States v. Carlson. 260 F. Supp. 423 at 425", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Carlson%20260%20F.%20Supp.%20423", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "774 F.2d 426", "case_name": "Counts v. Commissioner",
     "full_citation": "Counts v. Commissioner. 774 F.2d 426 at 427", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Counts%20v.%20Commissioner%20774%20F.2d%20426", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "793 F.2d 139", "case_name": "Beard v. Commissioner",
     "full_citation": "Beard v. Commissioner. 793 F.2d 139", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Beard%20v.%20Commissioner%20793%20F.2d%20139", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "627 F.2d 830", "case_name": "United States v. Moore",
     "full_citation": "United States v. Moore. 627 F.2d 830 at 834", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Moore%20627%20F.2d%20830", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "951 F.2d 1189", "case_name": "United States v. Dawes",
     "full_citation": "United States v. Dawes. 951 F.2d 1189 at 1192", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Dawes%20951%20F.2d%201189", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "947 F.2d 1356", "case_name": "United States v. Hicks",
     "full_citation": "United States v. Hicks. 947 F.2d 1356 at 1360", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Hicks%20947%20F.2d%201356", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "712 F.2d 195", "case_name": "Steinbrecher v. Commissioner",
     "full_citation": "Steinbrecher v. Commissioner. 712 F.2d 195 at 198", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Steinbrecher%20v.%20Commissioner%20712%20F.2d%20195", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "920 F.2d 220", "case_name": "United States v. Bowers",
     "full_citation": "United States v. Bowers. 920 F.2d 220 at 222", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Bowers%20920%20F.2d%20220", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "954 F.2d 698", "case_name": "United States v. Neff",
     "full_citation": "United States v. Neff. 954 F.2d 698 at 699", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Neff%20954%20F.2d%20698", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "672 F.2d 875", "case_name": "United States v. Pilcher",
     "full_citation": "United States v. Pilcher. 672 F.2d 875 at 877", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Pilcher%20672%20F.2d%20875", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "535 F.2d 400", "case_name": "United States v. Ballard",
     "full_citation": "United States v. Ballard. 535 F.2d 400 at 404", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=United%20States%20v.%20Ballard%20535%20F.2d%20400", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "505 F.2d 1026", "case_name": "Melo v. U.S",
     "full_citation": "Melo v. U.S. 505 F.2d 1026 at 18", "year": "", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Melo%20v.%20U.S%20505%20F.2d%201026", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "311 U.S. 457", "case_name": "Millken v. Meyer",
     "full_citation": "Millken v. Meyer. 311 U.S. 457 at 61", "year": "", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/311/457/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "306 F.2d 260", "case_name": "Amos Treat & Co. v. Securities & Exchange Commission",
     "full_citation": "Amos Treat & Co. v. Securities & Exchange Commission. 306 F.2d 260 (1962)", "year": "1962", "court": "Federal court",
     "url": "https://www.courtlistener.com/?q=Amos%20Treat%20%26%20Co.%20v.%20Securities%20%26%20Exchange%20Commission%20306%20F.2d%20260", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "184 U.S. 578", "case_name": "Eidman v. Martinez",
     "full_citation": "Eidman v. Martinez. 184 U.S. 578 at 583 (1902)", "year": "1902", "court": "U.S. Supreme Court",
     "url": "https://supreme.justia.com/cases/federal/us/184/578/", "occurrences": 0, "pages": [],
     "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_USC = [
    {"section": "26 U.S.C. § 7608", "url": "https://www.law.cornell.edu/uscode/text/26/7608",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7609", "url": "https://www.law.cornell.edu/uscode/text/26/7609",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7603", "url": "https://www.law.cornell.edu/uscode/text/26/7603",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6502", "url": "https://www.law.cornell.edu/uscode/text/26/6502",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7604", "url": "https://www.law.cornell.edu/uscode/text/26/7604",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 22", "url": "https://www.law.cornell.edu/uscode/text/26/22",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6201", "url": "https://www.law.cornell.edu/uscode/text/26/6201",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1332", "url": "https://www.law.cornell.edu/uscode/text/26/1332",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6335", "url": "https://www.law.cornell.edu/uscode/text/26/6335",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6065", "url": "https://www.law.cornell.edu/uscode/text/26/6065",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1442", "url": "https://www.law.cornell.edu/uscode/text/26/1442",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1443", "url": "https://www.law.cornell.edu/uscode/text/26/1443",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1463", "url": "https://www.law.cornell.edu/uscode/text/26/1463",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6212", "url": "https://www.law.cornell.edu/uscode/text/26/6212",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6203", "url": "https://www.law.cornell.edu/uscode/text/26/6203",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6332", "url": "https://www.law.cornell.edu/uscode/text/26/6332",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7433", "url": "https://www.law.cornell.edu/uscode/text/26/7433",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7809", "url": "https://www.law.cornell.edu/uscode/text/26/7809",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7214", "url": "https://www.law.cornell.edu/uscode/text/26/7214",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 86", "url": "https://www.law.cornell.edu/uscode/text/26/86",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7321", "url": "https://www.law.cornell.edu/uscode/text/26/7321",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7612", "url": "https://www.law.cornell.edu/uscode/text/26/7612",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6330", "url": "https://www.law.cornell.edu/uscode/text/26/6330",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7213", "url": "https://www.law.cornell.edu/uscode/text/26/7213",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 25", "url": "https://www.law.cornell.edu/uscode/text/26/25",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 17", "url": "https://www.law.cornell.edu/uscode/text/26/17",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6320", "url": "https://www.law.cornell.edu/uscode/text/26/6320",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1273", "url": "https://www.law.cornell.edu/uscode/text/26/1273",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1331", "url": "https://www.law.cornell.edu/uscode/text/26/1331",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7402", "url": "https://www.law.cornell.edu/uscode/text/26/7402",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6420", "url": "https://www.law.cornell.edu/uscode/text/26/6420",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 884", "url": "https://www.law.cornell.edu/uscode/text/26/884",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6053", "url": "https://www.law.cornell.edu/uscode/text/26/6053",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 881", "url": "https://www.law.cornell.edu/uscode/text/26/881",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 511", "url": "https://www.law.cornell.edu/uscode/text/26/511",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4948", "url": "https://www.law.cornell.edu/uscode/text/26/4948",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5291", "url": "https://www.law.cornell.edu/uscode/text/26/5291",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 62", "url": "https://www.law.cornell.edu/uscode/text/26/62",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 115", "url": "https://www.law.cornell.edu/uscode/text/26/115",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3101", "url": "https://www.law.cornell.edu/uscode/text/26/3101",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6159", "url": "https://www.law.cornell.edu/uscode/text/26/6159",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6325", "url": "https://www.law.cornell.edu/uscode/text/26/6325",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6061", "url": "https://www.law.cornell.edu/uscode/text/26/6061",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3202", "url": "https://www.law.cornell.edu/uscode/text/26/3202",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4411", "url": "https://www.law.cornell.edu/uscode/text/26/4411",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 931", "url": "https://www.law.cornell.edu/uscode/text/26/931",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7213A", "url": "https://www.law.cornell.edu/uscode/text/26/7213A",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7802", "url": "https://www.law.cornell.edu/uscode/text/26/7802",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 101", "url": "https://www.law.cornell.edu/uscode/text/26/101",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3290", "url": "https://www.law.cornell.edu/uscode/text/26/3290",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7302", "url": "https://www.law.cornell.edu/uscode/text/26/7302",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7303", "url": "https://www.law.cornell.edu/uscode/text/26/7303",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7403", "url": "https://www.law.cornell.edu/uscode/text/26/7403",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7432", "url": "https://www.law.cornell.edu/uscode/text/26/7432",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 71", "url": "https://www.law.cornell.edu/uscode/text/26/71",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7613", "url": "https://www.law.cornell.edu/uscode/text/26/7613",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4423", "url": "https://www.law.cornell.edu/uscode/text/26/4423",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6501", "url": "https://www.law.cornell.edu/uscode/text/26/6501",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4221", "url": "https://www.law.cornell.edu/uscode/text/26/4221",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 2032A", "url": "https://www.law.cornell.edu/uscode/text/26/2032A",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3102", "url": "https://www.law.cornell.edu/uscode/text/26/3102",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3505", "url": "https://www.law.cornell.edu/uscode/text/26/3505",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4002", "url": "https://www.law.cornell.edu/uscode/text/26/4002",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4051", "url": "https://www.law.cornell.edu/uscode/text/26/4051",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4071", "url": "https://www.law.cornell.edu/uscode/text/26/4071",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4219", "url": "https://www.law.cornell.edu/uscode/text/26/4219",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4401", "url": "https://www.law.cornell.edu/uscode/text/26/4401",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4483", "url": "https://www.law.cornell.edu/uscode/text/26/4483",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4611", "url": "https://www.law.cornell.edu/uscode/text/26/4611",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4662", "url": "https://www.law.cornell.edu/uscode/text/26/4662",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4972", "url": "https://www.law.cornell.edu/uscode/text/26/4972",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4980B", "url": "https://www.law.cornell.edu/uscode/text/26/4980B",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4980D", "url": "https://www.law.cornell.edu/uscode/text/26/4980D",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4980F", "url": "https://www.law.cornell.edu/uscode/text/26/4980F",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5005", "url": "https://www.law.cornell.edu/uscode/text/26/5005",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5043", "url": "https://www.law.cornell.edu/uscode/text/26/5043",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5232", "url": "https://www.law.cornell.edu/uscode/text/26/5232",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5364", "url": "https://www.law.cornell.edu/uscode/text/26/5364",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5418", "url": "https://www.law.cornell.edu/uscode/text/26/5418",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5703", "url": "https://www.law.cornell.edu/uscode/text/26/5703",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 5751", "url": "https://www.law.cornell.edu/uscode/text/26/5751",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 305", "url": "https://www.law.cornell.edu/uscode/text/26/305",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 10", "url": "https://www.law.cornell.edu/uscode/text/26/10",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 512", "url": "https://www.law.cornell.edu/uscode/text/26/512",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1235", "url": "https://www.law.cornell.edu/uscode/text/26/1235",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 645", "url": "https://www.law.cornell.edu/uscode/text/26/645",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1231", "url": "https://www.law.cornell.edu/uscode/text/26/1231",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6303", "url": "https://www.law.cornell.edu/uscode/text/26/6303",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7301", "url": "https://www.law.cornell.edu/uscode/text/26/7301",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7208", "url": "https://www.law.cornell.edu/uscode/text/26/7208",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7271", "url": "https://www.law.cornell.edu/uscode/text/26/7271",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7207", "url": "https://www.law.cornell.edu/uscode/text/26/7207",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6621", "url": "https://www.law.cornell.edu/uscode/text/26/6621",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7401", "url": "https://www.law.cornell.edu/uscode/text/26/7401",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6321", "url": "https://www.law.cornell.edu/uscode/text/26/6321",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1001", "url": "https://www.law.cornell.edu/uscode/text/26/1001",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6532", "url": "https://www.law.cornell.edu/uscode/text/26/6532",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3201", "url": "https://www.law.cornell.edu/uscode/text/26/3201",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 74", "url": "https://www.law.cornell.edu/uscode/text/26/74",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6104", "url": "https://www.law.cornell.edu/uscode/text/26/6104",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 433", "url": "https://www.law.cornell.edu/uscode/text/26/433",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7605", "url": "https://www.law.cornell.edu/uscode/text/26/7605",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7606", "url": "https://www.law.cornell.edu/uscode/text/26/7606",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7607", "url": "https://www.law.cornell.edu/uscode/text/26/7607",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7610", "url": "https://www.law.cornell.edu/uscode/text/26/7610",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7611", "url": "https://www.law.cornell.edu/uscode/text/26/7611",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1340", "url": "https://www.law.cornell.edu/uscode/text/26/1340",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1345", "url": "https://www.law.cornell.edu/uscode/text/26/1345",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4612", "url": "https://www.law.cornell.edu/uscode/text/26/4612",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 704", "url": "https://www.law.cornell.edu/uscode/text/26/704",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3224", "url": "https://www.law.cornell.edu/uscode/text/26/3224",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 250", "url": "https://www.law.cornell.edu/uscode/text/26/250",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 270", "url": "https://www.law.cornell.edu/uscode/text/26/270",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 251", "url": "https://www.law.cornell.edu/uscode/text/26/251",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 891", "url": "https://www.law.cornell.edu/uscode/text/26/891",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 55", "url": "https://www.law.cornell.edu/uscode/text/26/55",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6654", "url": "https://www.law.cornell.edu/uscode/text/26/6654",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4911", "url": "https://www.law.cornell.edu/uscode/text/26/4911",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4940", "url": "https://www.law.cornell.edu/uscode/text/26/4940",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4971", "url": "https://www.law.cornell.edu/uscode/text/26/4971",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4981", "url": "https://www.law.cornell.edu/uscode/text/26/4981",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4985", "url": "https://www.law.cornell.edu/uscode/text/26/4985",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6213", "url": "https://www.law.cornell.edu/uscode/text/26/6213",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6512", "url": "https://www.law.cornell.edu/uscode/text/26/6512",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 40", "url": "https://www.law.cornell.edu/uscode/text/26/40",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 501", "url": "https://www.law.cornell.edu/uscode/text/26/501",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 877", "url": "https://www.law.cornell.edu/uscode/text/26/877",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7491", "url": "https://www.law.cornell.edu/uscode/text/26/7491",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7430", "url": "https://www.law.cornell.edu/uscode/text/26/7430",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 14418", "url": "https://www.law.cornell.edu/uscode/text/26/14418",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7206", "url": "https://www.law.cornell.edu/uscode/text/26/7206",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1204", "url": "https://www.law.cornell.edu/uscode/text/26/1204",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6301", "url": "https://www.law.cornell.edu/uscode/text/26/6301",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 408", "url": "https://www.law.cornell.edu/uscode/text/26/408",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6166", "url": "https://www.law.cornell.edu/uscode/text/26/6166",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 6531", "url": "https://www.law.cornell.edu/uscode/text/26/6531",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3211", "url": "https://www.law.cornell.edu/uscode/text/26/3211",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3221", "url": "https://www.law.cornell.edu/uscode/text/26/3221",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3301", "url": "https://www.law.cornell.edu/uscode/text/26/3301",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3404", "url": "https://www.law.cornell.edu/uscode/text/26/3404",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3451", "url": "https://www.law.cornell.edu/uscode/text/26/3451",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 72", "url": "https://www.law.cornell.edu/uscode/text/26/72",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 73", "url": "https://www.law.cornell.edu/uscode/text/26/73",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 75", "url": "https://www.law.cornell.edu/uscode/text/26/75",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 76", "url": "https://www.law.cornell.edu/uscode/text/26/76",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 77", "url": "https://www.law.cornell.edu/uscode/text/26/77",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 78", "url": "https://www.law.cornell.edu/uscode/text/26/78",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 80", "url": "https://www.law.cornell.edu/uscode/text/26/80",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 81", "url": "https://www.law.cornell.edu/uscode/text/26/81",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 82", "url": "https://www.law.cornell.edu/uscode/text/26/82",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 83", "url": "https://www.law.cornell.edu/uscode/text/26/83",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 84", "url": "https://www.law.cornell.edu/uscode/text/26/84",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 85", "url": "https://www.law.cornell.edu/uscode/text/26/85",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 87", "url": "https://www.law.cornell.edu/uscode/text/26/87",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 88", "url": "https://www.law.cornell.edu/uscode/text/26/88",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 89", "url": "https://www.law.cornell.edu/uscode/text/26/89",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 90", "url": "https://www.law.cornell.edu/uscode/text/26/90",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 54", "url": "https://www.law.cornell.edu/uscode/text/26/54",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1655", "url": "https://www.law.cornell.edu/uscode/text/26/1655",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 200", "url": "https://www.law.cornell.edu/uscode/text/26/200",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 4502", "url": "https://www.law.cornell.edu/uscode/text/26/4502",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3371", "url": "https://www.law.cornell.edu/uscode/text/26/3371",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7342", "url": "https://www.law.cornell.edu/uscode/text/26/7342",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 602", "url": "https://www.law.cornell.edu/uscode/text/26/602",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 603", "url": "https://www.law.cornell.edu/uscode/text/26/603",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 102", "url": "https://www.law.cornell.edu/uscode/text/26/102",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1102", "url": "https://www.law.cornell.edu/uscode/text/26/1102",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1110", "url": "https://www.law.cornell.edu/uscode/text/26/1110",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3410", "url": "https://www.law.cornell.edu/uscode/text/26/3410",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3413", "url": "https://www.law.cornell.edu/uscode/text/26/3413",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1335", "url": "https://www.law.cornell.edu/uscode/text/26/1335",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 341", "url": "https://www.law.cornell.edu/uscode/text/26/341",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7803", "url": "https://www.law.cornell.edu/uscode/text/26/7803",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 301", "url": "https://www.law.cornell.edu/uscode/text/26/301",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 302", "url": "https://www.law.cornell.edu/uscode/text/26/302",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 303", "url": "https://www.law.cornell.edu/uscode/text/26/303",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 304", "url": "https://www.law.cornell.edu/uscode/text/26/304",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 306", "url": "https://www.law.cornell.edu/uscode/text/26/306",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 307", "url": "https://www.law.cornell.edu/uscode/text/26/307",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 308", "url": "https://www.law.cornell.edu/uscode/text/26/308",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 309", "url": "https://www.law.cornell.edu/uscode/text/26/309",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 310", "url": "https://www.law.cornell.edu/uscode/text/26/310",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3321", "url": "https://www.law.cornell.edu/uscode/text/26/3321",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3322", "url": "https://www.law.cornell.edu/uscode/text/26/3322",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 3323", "url": "https://www.law.cornell.edu/uscode/text/26/3323",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7426", "url": "https://www.law.cornell.edu/uscode/text/26/7426",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7422", "url": "https://www.law.cornell.edu/uscode/text/26/7422",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 1304", "url": "https://www.law.cornell.edu/uscode/text/26/1304",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"section": "26 U.S.C. § 7521", "url": "https://www.law.cornell.edu/uscode/text/26/7521",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_CFR = [
    {"cite": "26 CFR §601.106", "url": "https://www.law.cornell.edu/cfr/text/26/601.106",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "27 CFR §170", "url": "https://www.law.cornell.edu/cfr/text/27/170",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §602", "url": "https://www.law.cornell.edu/cfr/text/26/602",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "01 CFR", "url": "https://www.law.cornell.edu/cfr/text/01",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "5 CFR", "url": "https://www.law.cornell.edu/cfr/text/5",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "28 CFR", "url": "https://www.law.cornell.edu/cfr/text/28",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "1 CFR §3.1", "url": "https://www.law.cornell.edu/cfr/text/1/3.1",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "1 CFR §51", "url": "https://www.law.cornell.edu/cfr/text/1/51",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "2 CFR", "url": "https://www.law.cornell.edu/cfr/text/2",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §31.6001", "url": "https://www.law.cornell.edu/cfr/text/26/31.6001",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §1.312-6", "url": "https://www.law.cornell.edu/cfr/text/26/1.312-6",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §31.3402", "url": "https://www.law.cornell.edu/cfr/text/26/31.3402",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §31", "url": "https://www.law.cornell.edu/cfr/text/26/31",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §301.6331-2", "url": "https://www.law.cornell.edu/cfr/text/26/301.6331-2",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"cite": "26 CFR §301.7602", "url": "https://www.law.cornell.edu/cfr/text/26/301.7602",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_CONST = [
    {"ref": "Fourteenth Amendment", "url": "https://constitution.congress.gov/constitution/amendment-14/",
     "occurrences": 0, "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_FORMS = [
    {"form": "Form 2433", "url": "https://www.irs.gov/forms-pubs/about-form-2433",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 2290", "url": "https://www.irs.gov/forms-pubs/about-form-2290",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 720", "url": "https://www.irs.gov/forms-pubs/about-form-720",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 1215", "url": "https://www.irs.gov/forms-pubs/about-form-1215",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 2039", "url": "https://www.irs.gov/forms-pubs/about-form-2039",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 668-A", "url": "https://www.irs.gov/forms-pubs/about-form-668-a",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 940", "url": "https://www.irs.gov/forms-pubs/about-form-940",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 943", "url": "https://www.irs.gov/forms-pubs/about-form-943",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 11-B", "url": "https://www.irs.gov/forms-pubs/about-form-11-b",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form CT-1", "url": "https://www.irs.gov/forms-pubs/about-form-ct-1",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 11-C", "url": "https://www.irs.gov/forms-pubs/about-form-11-c",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 637", "url": "https://www.irs.gov/forms-pubs/about-form-637",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 730", "url": "https://www.irs.gov/forms-pubs/about-form-730",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 843", "url": "https://www.irs.gov/forms-pubs/about-form-843",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 872-B", "url": "https://www.irs.gov/forms-pubs/about-form-872-b",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 1363", "url": "https://www.irs.gov/forms-pubs/about-form-1363",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 2758", "url": "https://www.irs.gov/forms-pubs/about-form-2758",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 4136", "url": "https://www.irs.gov/forms-pubs/about-form-4136",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 942", "url": "https://www.irs.gov/forms-pubs/about-form-942",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 1065", "url": "https://www.irs.gov/forms-pubs/about-form-1065",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 11", "url": "https://www.irs.gov/forms-pubs/about-form-11",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 5384", "url": "https://www.irs.gov/forms-pubs/about-form-5384",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 5385", "url": "https://www.irs.gov/forms-pubs/about-form-5385",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 6197", "url": "https://www.irs.gov/forms-pubs/about-form-6197",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 6478", "url": "https://www.irs.gov/forms-pubs/about-form-6478",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 6627", "url": "https://www.irs.gov/forms-pubs/about-form-6627",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 8109", "url": "https://www.irs.gov/forms-pubs/about-form-8109",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 8849", "url": "https://www.irs.gov/forms-pubs/about-form-8849",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 9117", "url": "https://www.irs.gov/forms-pubs/about-form-9117",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 2555-F", "url": "https://www.irs.gov/forms-pubs/about-form-2555-f",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 2555-EZ", "url": "https://www.irs.gov/forms-pubs/about-form-2555-ez",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 668-W", "url": "https://www.irs.gov/forms-pubs/about-form-668-w",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 668", "url": "https://www.irs.gov/forms-pubs/about-form-668",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 8857", "url": "https://www.irs.gov/forms-pubs/about-form-8857",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 106", "url": "https://www.irs.gov/forms-pubs/about-form-106",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"form": "Form 4443", "url": "https://www.irs.gov/forms-pubs/about-form-4443",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_CLAUSES = [
    {"citation": "Article I, Section 10", "url": "https://constitution.congress.gov/browse/article-1/section-10/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"citation": "Article I, Section 10, Clause 1", "url": "https://constitution.congress.gov/browse/article-1/section-10/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"citation": "Article I, Section 8", "url": "https://constitution.congress.gov/browse/article-1/section-8/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"citation": "Article I, Section 8, Clause 18", "url": "https://constitution.congress.gov/browse/article-1/section-8/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"citation": "Article I, Section 9", "url": "https://constitution.congress.gov/browse/article-1/section-9/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"citation": "Article I, Section 9, Clause 5", "url": "https://constitution.congress.gov/browse/article-1/section-9/",
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
]
MANUAL_BOOK2_IMPORT_ACTS = [
    {"act": "Corporate Tax Act of 1909", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Corporation Excise Tax Act of 1909", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Simmons Tariff Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Underwood-Simmons Tariff Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Revenue Act of 1916", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Underwood Simmons Tariff Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Tariff Act of 1913", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Revenue Act of 1938", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Paperwork Reduction Act of 1980", "url": "https://www.congress.gov/bill/96th-congress/senate-bill/1411", "official_source": True,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Corporation Excise Tax Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Revenue Act of 1926", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Income Tax Act of 1894", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Tariff Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Certain Excise Tax Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "For Certain Excise Tax Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Pot Paperwork Reduction Act", "url": "https://www.congress.gov/bill/96th-congress/senate-bill/1411", "official_source": True,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Income Tax Act of 1916", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Revenue Act of 1934", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Paperwork Reduction Act of 1995", "url": "https://www.congress.gov/bill/96th-congress/senate-bill/1411", "official_source": True,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Revenue Act of 1978", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
    {"act": "Contributions Act", "url": "https://www.loc.gov/collections/united-states-statutes-at-large/", "official_source": False,
     "occurrences": 0, "pages": [], "source": "american_tax_bible_backfill_2026-11-15"},
]

_existing_scotus_cites = {e["cite"] for e in out["scotus_and_courts"]}
out["scotus_and_courts"] += [e for e in MANUAL_SCOTUS if e["cite"] not in _existing_scotus_cites]
_existing_forms = {e["form"] for e in out["irs_forms"]}
out["irs_forms"] += [e for e in MANUAL_FORMS if e["form"] not in _existing_forms]
_existing_tds = {e["cite"] for e in out["treasury_decisions"]}
out["treasury_decisions"] += [e for e in MANUAL_TD if e["cite"] not in _existing_tds]

_existing_scotus_cites2 = {e["cite"] for e in out["scotus_and_courts"]}
out["scotus_and_courts"] += [e for e in MANUAL_BOOK2_IMPORT_SCOTUS if e["cite"] not in _existing_scotus_cites2]
_existing_usc_sections = {e["section"] for e in out["usc_title26_irc"]}
out["usc_title26_irc"] += [e for e in MANUAL_BOOK2_IMPORT_USC if e["section"] not in _existing_usc_sections]
_existing_cfr_cites = {e["cite"] for e in out["cfr"]}
out["cfr"] += [e for e in MANUAL_BOOK2_IMPORT_CFR if e["cite"] not in _existing_cfr_cites]
_existing_const_refs = {e["ref"] for e in out["constitution"]}
out["constitution"] += [e for e in MANUAL_BOOK2_IMPORT_CONST if e["ref"] not in _existing_const_refs]
_existing_forms2 = {e["form"] for e in out["irs_forms"]}
out["irs_forms"] += [e for e in MANUAL_BOOK2_IMPORT_FORMS if e["form"] not in _existing_forms2]
_existing_clauses = {e["citation"] for e in out["constitutional_clauses"]}
out["constitutional_clauses"] += [e for e in MANUAL_BOOK2_IMPORT_CLAUSES if e["citation"] not in _existing_clauses]
_existing_acts = {e["act"] for e in out["acts_of_congress"]}
out["acts_of_congress"] += [e for e in MANUAL_BOOK2_IMPORT_ACTS if e["act"] not in _existing_acts]

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
L.append("_Treasury Decisions are hosted in [treasury-decisions](https://dogthathunts.github.io/treasury-decisions/) "
         "(its `tds.json` is the single source of truth): a transcript page and the scan for each. Rows marked "
         "**add to mapping** are cited in this book but not yet hosted there._\n")
L.append("| T.D. | Occ. | Pages | Status | Source |")
L.append("|---|---:|---|---|---|")
for c in out["treasury_decisions"]:
    pgs=", ".join(c["pages"][:6])
    status = "in mapping" if c["in_mapping_file"] else "**add to mapping**"
    if c.get("local_path"):
        src = f"[transcript]({c['url']}) · [scan]({c['local_path']})"
    else:
        src = f"[link]({c['url']})"
    if c.get("transcript_path") and c["transcript_path"] != c["url"]:
        src += f" · [transcript]({c['transcript_path']})"
    # NOTE: relationship lines (supersedes/superseded by/amended by) are intentionally
    # NOT rendered on the register for now — the data is kept in link_register.json
    # (entry["relations"]); proper presentation is deferred to next session (see WAYPOINT).
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
if unresolved_forms:
    print(f"IRS forms UNRESOLVED (guessed URL 404'd, left unlinked): {len(unresolved_forms)}")
    for k, u in unresolved_forms:
        print(f"  - {k}  (tried: {u})")
print("wrote link_register.md + link_register.json")
