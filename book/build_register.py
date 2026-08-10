#!/usr/bin/env python3
"""Build a register of legal citations (SCOTUS, USC/IRC, CFR, Treasury Decisions,
constitutional refs, IRS forms) from the cleaned MD, mapped to authoritative URLs.
Emits link_register.md (human) and link_register.json (for HTML enrichment)."""
import re, json, sys
from collections import defaultdict, OrderedDict

MD = "Book - Dave Champion - Income Tax - Shattering the Myths.md"
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

# Curated case-name corrections (OCR repair / recovered from Table of Authorities),
# keyed by normalized reporter cite. Reporter cite drives the (deterministic) URL.
CASE_FIXES = {
    "231 U.S. 399": "Stratton's Independence, Ltd. v. Howbert",
    "417 F.2d 1002": "United States v. Moylan",
    "338 U.S. 680": "United States v. Alpers",
    "466 U.S. 475": "United States v. Rodgers",
    "361 U.S. 431": "United States v. Mersky",
    "440 U.S. 472": "National Muffler Dealers Assn. v. United States",
    "755 F.2d 790": "CWT Farms, Inc. v. Commissioner of Internal Revenue",
    "809 F.2d 1427": "United States v. Murphy",
    "470 F.2d 585": "Heating Co. v. United States",
    "57 F.2d 877": "American Airways, Inc. v. Wallace",
    "34 S. Ct. 421": "Billings v. United States",
    "232 U.S. 261": "Billings v. United States",
}
def norm_reporter(rep_raw):
    r = re.sub(r"[.\s]", "", rep_raw).upper()
    return {"F2D": "F.2d", "F3D": "F.3d", "F": "F.", "FED": "F.",
            "SCT": "S. Ct.", "LED": "L. Ed."}.get(r, rep_raw.strip())

cases = {}   # normalized reporter cite -> {name, reporter, url, pages:set, count}
for m in re.finditer(cite_rx, text):
    vol, rep_raw, pg = m.group(1), m.group(2), m.group(3)
    rep = re.sub(r"[.\s]", "", rep_raw).upper()  # US, SCT, LED, F2D, F3D, F, FED
    # look back up to 80 chars for a case name
    back = text[max(0, m.start()-90):m.start()]
    nm = re.findall(name_rx, back)
    name = clean_name(nm[-1]) if nm else ""
    if rep == "US":
        key = norm_us(vol, pg)
        url = f"https://supreme.justia.com/cases/federal/us/{vol}/{pg}/"
        court = "U.S. Supreme Court"
    elif rep in ("F2D","F3D","F","FED"):
        key = f"{vol} {norm_reporter(rep_raw)} {pg}"
        q = (name or key).replace(" ", "+")
        url = f"https://www.courtlistener.com/?q={q}"
        court = "Federal court (F.)"
    else:  # parallel SCOTUS reporters
        key = f"{vol} {norm_reporter(rep_raw)} {pg}"
        url = f"https://www.courtlistener.com/?q={key.replace(' ','+')}"
        court = "U.S. Supreme Court (parallel cite)"
    e = cases.setdefault(key, {"name": name, "court": court, "url": url,
                                "reporter": rep, "count": 0, "pages": set()})
    e["count"] += 1
    if name and not e["name"]:
        e["name"] = name
    e["pages"].add(page_at(m.start()))

# apply curated name corrections (authoritative over OCR)
for k, nm in CASE_FIXES.items():
    if k in cases:
        cases[k]["name"] = nm

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
    {"cite":k, "case_name":v["name"], "court":v["court"], "url":v["url"],
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
    entry = {"cite":k, "occurrences":v["count"], "pages":pset(v["pages"]),
             "in_mapping_file": url is not None,
             "url": url or f"https://babel.hathitrust.org/cgi/ls?q1=%22Treasury+Decision+{num}%22;a=srchls;lmt=ft"}
    if url is None:
        entry["note"] = "NOT YET in TREASURY_DECISIONS.md — add it there; fallback is a HathiTrust search."
    out["treasury_decisions"].append(entry)
out["constitution"] = [
    {"ref":k, "url":v.get("url") or const_url(k), "occurrences":v["count"]}
    for k,v in sorted(const.items(), key=lambda kv:-kv[1]["count"])]
out["irs_forms"] = [
    {"form":k, "url":form_url(k), "occurrences":v["count"], "pages":pset(v["pages"])}
    for k,v in sorted(forms.items(), key=lambda kv:-kv[1]["count"])]

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
L.append("| Cite | Case name (OCR) | Court | Occ. | Pages | Link |")
L.append("|---|---|---|---:|---|---|")
for c in out["scotus_and_courts"]:
    flag = " **verify**" if (not c["case_name"] or c["court"].startswith("Federal") or "parallel" in c["court"]) else ""
    pgs=", ".join(c["pages"][:6])
    L.append(f"| {c['cite']} | {c['case_name'] or '—'}{flag} | {c['court']} | {c['occurrences']} | {pgs} | [link]({c['url']}) |")

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
L.append("_URLs are sourced from the shared mapping `transcription-agent/TREASURY_DECISIONS.md` "
         "(single source of truth, updated over time). Rows marked **add to mapping** are cited "
         "in this book but not yet in that file._\n")
L.append("| T.D. | Occ. | Pages | Status | Link |")
L.append("|---|---:|---|---|---|")
for c in out["treasury_decisions"]:
    pgs=", ".join(c["pages"][:6])
    status = "in mapping" if c["in_mapping_file"] else "**add to mapping**"
    L.append(f"| {c['cite']} | {c['occurrences']} | {pgs} | {status} | [link]({c['url']}) |")

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

open("link_register.md","w",encoding="utf-8").write("\n".join(L)+"\n")

print("SCOTUS/court cites :", len(out["scotus_and_courts"]))
print("USC/IRC sections   :", len(out["usc_title26_irc"]))
print("CFR cites          :", len(out["cfr"]))
print("Treasury Decisions :", len(out["treasury_decisions"]))
print("Constitution refs  :", len(out["constitution"]))
print("IRS forms          :", len(out["irs_forms"]))
print("wrote link_register.md + link_register.json")
