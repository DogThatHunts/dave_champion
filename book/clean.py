#!/usr/bin/env python3
"""Structural + safe-OCR cleanup for the Dave Champion book MD.
Reads the raw-ocr backup, writes cleaned MD + a change report.
Re-runnable and non-destructive to the raw source."""
import re, sys, unicodedata
from collections import defaultdict

RAW = "Book - Dave Champion - Income Tax - Shattering the Myths.raw-ocr.md"
OUT = "Book - Dave Champion - Income Tax - Shattering the Myths.md"
REPORT = "cleanup_report.txt"

report = []
def log(cat, ln, before, after=""):
    report.append((cat, ln, before.rstrip(), after.rstrip()))

src = open(RAW, encoding="utf-8").read()
lines = src.split("\n")

# ---------- helpers ----------
def norm(s):
    s = re.sub(r"[*_#>|`]", " ", s)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s

ROMAN = re.compile(r"^[ivxlcdm]+$", re.I)

# Chapter/running-head titles (normalized) -> strip only when level-6 plain / bare footer.
RUNNING_HEADS = {norm(x) for x in [
    "Dave Champion", "Income Tax: Shattering The Myths", "Table of Contents",
    "Introduction", "How To Read This Book", "Rules of the Game",
    "Origins and Evolution", "Interpretations and Perceptions", "Income v. Income",
    "Then as Now", "If Not You, Then Who?", "In Their Own Words",
    "Working the Marks", "Thrashing About", "And The Answer Is",
    "The Right Handgun", "Acknowledgments", "Table of Authorities & Notes",
    "Index", "The Lies They Tell To Cover The Lies They've Told",
    "The Good, The Bad, And The Mistaken", "Tricks Of The Trade", "This and That",
    "The Dave Champion Show and Other Resources", "Revision notes (2025)",
]}
# "Employee - Who Me" running head appears with garbled punctuation; match loosely.
def is_employee_head(n):
    return n.startswith("employee") and "who" in n and "me" in n

# ---------- PASS 1: per-line structural transforms ----------
out = []
for i, ln in enumerate(lines):
    raw = ln
    stripped = ln.strip()

    # 1a. bare page-number line: **12**  /  **ii**  /  **V**
    m = re.match(r"^\*\*\s*([ivxlcdmIVXLCDM0-9]{1,6})\s*\*\*\s*$", stripped)
    if m:
        val = m.group(1)
        out.append(f"<!-- page: {val} -->")
        log("page->anchor", i+1, raw, f"<!-- page: {val} -->")
        continue

    # 1b. heading that is really a page number: ###### **V**  /  ###### 5
    m = re.match(r"^#{1,6}\s+\*{0,2}\s*([ivxlcdmIVXLCDM0-9]{1,6})\s*\*{0,2}\s*$", stripped)
    if m and (ROMAN.match(m.group(1)) or m.group(1).isdigit()):
        val = m.group(1)
        out.append(f"<!-- page: {val} -->")
        log("page-head->anchor", i+1, raw, f"<!-- page: {val} -->")
        continue

    # 1c. level-6 heading handling
    m = re.match(r"^######\s+(.*\S)\s*$", stripped)
    if m:
        body = m.group(1)
        has_bold = "**" in body
        n = norm(body)
        # genuine bold subsection -> keep (but demote later if desired). Keep as-is.
        if has_bold and n not in RUNNING_HEADS and not is_employee_head(n):
            out.append(raw)
            continue
        # plain running head OR bold running-head duplicate -> drop
        if n in RUNNING_HEADS or is_employee_head(n):
            log("drop-runhead", i+1, raw)
            continue
        # single-letter / tiny junk heads (u,o,c) and stray fragments
        if len(n) <= 2:
            log("drop-junk-head", i+1, raw)
            continue
        # remaining plain level-6 headings that aren't known running heads are
        # mis-detected sentence fragments / list items / epigraphs -> de-heading.
        out.append(body)
        log("deheaded-fragment", i+1, raw, body)
        continue

    # 1d. bare plain-text footer line equal to a running head (e.g. lone "How To Read This Book")
    n = norm(stripped)
    is_footer_title = (n in RUNNING_HEADS or is_employee_head(n)
                       or n.endswith("income tax shattering the myths"))
    if (stripped and is_footer_title and not stripped.startswith("#")
            and "**" not in stripped and len(stripped.split()) <= 9):
        # only strip if it's an isolated line (surrounded by blanks) -> running footer
        prev_blank = (i == 0) or (lines[i-1].strip() == "")
        next_blank = (i == len(lines)-1) or (lines[i+1].strip() == "")
        if prev_blank and next_blank:
            log("drop-footer", i+1, raw)
            continue

    out.append(raw)

# ---------- PASS 2: collapse resulting multiple blank lines ----------
collapsed = []
blank = False
for ln in out:
    if ln.strip() == "":
        if blank:
            continue
        blank = True
    else:
        blank = False
    collapsed.append(ln)
out = collapsed

# ---------- PASS 3: paragraph-level de-duplication (DISABLED) ----------
# The three adjacent re-OCR zones OVERLAP rather than cleanly duplicate, so blind
# paragraph-dedup fragments the text. These 3 zones are reconstructed by hand
# against the PDF reference after this script runs. Kept here (guarded) for record.
WINDOW = 22
if False:
  pass
DEDUP = False
paras, cur = [], []
for ln in out:
    if ln.strip() == "":
        if cur:
            paras.append(cur); cur=[]
        paras.append([])   # blank marker
    else:
        cur.append(ln)
if cur: paras.append(cur)

recent = []  # list of (norm, para)
kept = []
for p in paras:
    if not p or all(l.strip()=="" for l in p):
        kept.append(p); continue
    text = " ".join(p)
    n = norm(text)
    if DEDUP and len(n) > 80 and any(n == rn for rn in recent[-WINDOW:]):
        log("drop-dup-para", 0, text[:200])
        continue
    recent.append(n)
    kept.append(p)

out = []
for p in kept:
    if not p:
        out.append("")
    else:
        out.extend(p)

# collapse blanks again
collapsed=[]; blank=False
for ln in out:
    if ln.strip()=="":
        if blank: continue
        blank=True
    else: blank=False
    collapsed.append(ln)
out=collapsed

# ---------- PASS 4: safe OCR text fixes ----------
text = "\n".join(out)
ocr_counts = defaultdict(int)
def sub(pat, repl, text, flags=0, name=None):
    new, n = re.subn(pat, repl, text, flags=flags)
    if n: ocr_counts[name or pat] += n
    return new

# pronoun "1" -> "I" before common verbs/contractions
verbs = ("am","believe","have","share","think","want","will","do","don","was",
         "had","would","could","can","know","saw","see","feel","said","mean",
         "long","encourage","presume","suspect","thought","need","m","ve","d","ll",
         "wrote","found","suggest","hope","spent","went","told","get","gave")
text = sub(r"(?<![\w.])1\s+(?=(?:"+ "|".join(verbs) +r")\b)", "I ", text, name="1->I (pronoun)")
text = sub(r"(?<![\w.])1'(?=(m|ve|d|ll)\b)", "I'", text, name="1'->I' (contraction)")

# merged words (unambiguous, high-frequency in this OCR)
for bad, good in [("ifyou","if you"),("Ifyou","If you"),("ofthe","of the"),
                  ("Ofthe","Of the"),("tothe","to the"),("inthe","in the"),
                  ("onthe","on the"),("atlarge","at large"),("tofurnish","to furnish"),
                  ("ofpretended","of pretended"),("ofnot","of not"),("thatthe","that the"),
                  ("isthe","is the"),("forthe","for the"),("andthe","and the"),
                  ("ofa","of a"),("ofthis","of this"),("ofthat","of that"),
                  ("ofour","of our"),("ofyour","of your"),("ofits","of its"),
                  ("ofincome","of income"),("thanthe","than the"),("withthe","with the")]:
    text = sub(r"\b"+bad+r"\b", good, text, name=f"merge:{bad}")

out = text.split("\n")

# ---------- PASS 5: reconstruct the 3 overlapping re-OCR duplicate zones ----------
# Each zone duplicates a run of pages that were re-scanned when the 2025 revision was
# inserted. We keep the complete copy and delete the redundant one, anchoring on unique
# text so this stays correct if earlier line numbers shift.
def collapse_between(lines, key_first, key_second=None, merge=False,
                     startswith=False, contains=False, label=""):
    key_second = key_second or key_first
    def hit(l, key):
        s = l.strip()
        return s.startswith(key) if startswith else (key in l if contains else s == key)
    ai = next((k for k,l in enumerate(lines) if hit(l, key_first)), None)
    bi = next((k for k in range(ai+1, len(lines)) if hit(lines[k], key_second)), None) if ai is not None else None
    if ai is None or bi is None:
        report.append(("ZONE-MISS", 0, label, "")); return lines
    if merge:  # copy1 ends mid-sentence; splice copy2's continuation onto it
        merged = lines[ai].rstrip() + " " + lines[bi].strip() + " "
        new = lines[:ai] + [merged] + lines[bi+1:]
    else:      # identical trailing paragraph in both copies; keep first, drop the span between
        new = lines[:ai+1] + lines[bi+1:]
    report.append(("dedup-zone", ai+1, f"{label}: removed lines {ai+2}..{bi+1}", ""))
    return new

# Zone 1 — Revision notes / Treasury Decisions: splice copy1 tail to copy2 continuation
out = collapse_between(out,
    "When this book was published in 2010, I was aware of eight Treasury Decisions",
    "by nonresident aliens with US source income",
    merge=True, startswith=True, label="revision-notes")
# Zone 2 — Origins & Evolution (Chapter 2): keep complete copy1, drop copy2
out = collapse_between(out,
    "This situation created a dilemma for the States.",
    startswith=True, label="origins-evolution")
# Zone 3 — T.D. 8734 / section 3406 (pp.130-131): keep copy A, drop copy B
out = collapse_between(out,
    "Now that you understand how this particular system works, let me give the full text.",
    contains=True, label="td8734-3406")

# ---------- write ----------
open(OUT, "w", encoding="utf-8").write("\n".join(out))

# ---------- report ----------
cats = defaultdict(int)
for c,_,_,_ in report: cats[c]+=1
with open(REPORT,"w",encoding="utf-8") as r:
    r.write("CLEANUP REPORT\n==============\n\n")
    r.write(f"raw lines : {len(lines)}\n")
    r.write(f"out lines : {len(out)}\n\n")
    r.write("Structural changes by category:\n")
    for c in sorted(cats): r.write(f"  {c:22s} {cats[c]}\n")
    r.write("\nOCR fixes by pattern:\n")
    for k in sorted(ocr_counts): r.write(f"  {k:28s} {ocr_counts[k]}\n")
    r.write("\n--- items flagged for manual REVIEW ---\n")
    for c,ln,b,a in report:
        if c.startswith("REVIEW"):
            r.write(f"  L{ln}: {b}\n")
    r.write("\n--- dropped duplicate paragraphs (first 200 chars) ---\n")
    for c,ln,b,a in report:
        if c=="drop-dup-para":
            r.write(f"  {b}\n")
    r.write("\n--- all dropped running-heads/footers/junk ---\n")
    for c,ln,b,a in report:
        if c in ("drop-runhead","drop-footer","drop-junk-head"):
            r.write(f"  [{c}] L{ln}: {b}\n")

print(f"raw={len(lines)} out={len(out)} lines")
for c in sorted(cats): print(f"  {c:22s} {cats[c]}")
print("OCR:")
for k in sorted(ocr_counts): print(f"  {k:28s} {ocr_counts[k]}")
