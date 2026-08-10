#!/usr/bin/env python3
"""Proofreading pipeline (Stage 2, hybrid). Two modes:

  python3 proofread.py chunk    # partition the cleaned MD into chunk files for agents
  python3 proofread.py apply    # apply proofread_edits.json back onto the MD (in place)

Design: agents return EXACT before->after edits (never rewritten prose), applied by
string match. Anything not explicitly edited stays byte-identical — no silent rewrites,
legal quotes preserved unless an agent names a specific OCR fix. Fully reproducible:
given the same chunks + proofread_edits.json, `apply` yields the same MD.
"""
import sys, os, json, re

MD  = "Book - Dave Champion - Income Tax - Shattering the Myths.md"
DIR = "proofread_chunks"
MANIFEST = os.path.join(DIR, "manifest.json")
EDITS = "proofread_edits.json"
RECOVERY = "proofread_recovery.json"   # global unique-match fixes for per-chunk misses
TARGET = 150   # ~lines per chunk; break at the next blank line after this

def do_chunk():
    lines = open(MD, encoding="utf-8").read().split("\n")
    os.makedirs(DIR, exist_ok=True)
    chunks = []      # list of (start, end)  end exclusive
    start = 0
    n = len(lines)
    while start < n:
        end = min(start + TARGET, n)
        # extend to the next blank line so we don't split mid-paragraph
        while end < n and lines[end].strip() != "":
            end += 1
        chunks.append((start, end))
        start = end
        # skip leading blanks into next chunk cleanly (they belong to next range start)
    manifest = []
    for i, (a, b) in enumerate(chunks):
        text = "\n".join(lines[a:b])
        path = os.path.join(DIR, f"chunk_{i:03d}.md")
        open(path, "w", encoding="utf-8").write(text)
        manifest.append({"id": i, "file": path, "start_line": a+1, "end_line": b})
    json.dump(manifest, open(MANIFEST, "w"), indent=2)
    # sanity: reassembly must equal original
    reassembled = "\n".join("\n".join(lines[a:b]) for a,b in chunks)
    assert reassembled == "\n".join(lines), "partition is not lossless!"
    print(f"wrote {len(chunks)} chunks to {DIR}/ (reassembly verified lossless)")

def _new_words(before, after):
    """alphabetic word-tokens (len>=3) present in `after` but not in `before`."""
    wb = set(w.lower() for w in re.findall(r"[A-Za-z]{3,}", before))
    wa = set(w.lower() for w in re.findall(r"[A-Za-z]{3,}", after))
    return wa - wb

def _suspicious(e):
    """Flag likely hallucinations. OCR fixes legitimately introduce a corrected word,
    so we do NOT flag those. The real hazard is a *deletion* (handwriting) that invents
    prose, or any edit that adds several new multi-letter words while growing the text."""
    b, a, r = e["before"], e["after"], e.get("reason", "")
    new4 = {w for w in _new_words(b, a) if len(w) >= 4}
    if r == "handwriting" and len(new4) >= 2:
        return f"handwriting deletion invented words {sorted(new4)}"
    if len(a) > len(b) + 20 and len(new4) >= 3:
        return f"edit grew text and added words {sorted(new4)}"
    return ""

def do_apply():
    manifest = json.load(open(MANIFEST))
    edits_by_chunk = json.load(open(EDITS))   # {"0":[{before,after,reason}], ...}
    out_parts = []
    applied = skipped = flagged = 0
    log = []
    for m in manifest:
        cid = str(m["id"])
        text = open(m["file"], encoding="utf-8").read()
        for e in edits_by_chunk.get(cid, []):
            b, a = e["before"], e["after"]
            if b == "" or b == a:
                continue
            sus = "" if e.get("force") else _suspicious(e)
            if sus:
                flagged += 1; log.append((cid, "FLAG", sus, f"{b[:50]!r}->{a[:50]!r}")); continue
            cnt = text.count(b)
            if cnt == 1:
                text = text.replace(b, a); applied += 1
            elif cnt == 0:
                skipped += 1; log.append((cid, "MISS", e.get("reason",""), b[:60]))
            else:
                if e.get("all"):
                    text = text.replace(b, a); applied += 1
                else:
                    skipped += 1; log.append((cid, f"AMBIG({cnt})", e.get("reason",""), b[:60]))
        out_parts.append(text)
    corrected = "\n".join(out_parts)
    # final recovery pass: global unique-match fixes (edits whose per-chunk `before`
    # didn't match exactly; hand-verified, applied against the assembled document).
    rec_applied = rec_skipped = 0
    if os.path.exists(RECOVERY):
        for e in json.load(open(RECOVERY)):
            b, a = e["before"], e["after"]
            if corrected.count(b) == 1:
                corrected = corrected.replace(b, a); rec_applied += 1
            else:
                rec_skipped += 1; log.append(("recovery", f"count={corrected.count(b)}", "", b[:60]))
    open(MD, "w", encoding="utf-8").write(corrected)
    json.dump(log, open("proofread_apply_log.json","w"), indent=2)
    print(f"applied {applied}, skipped {skipped}, FLAGGED {flagged}; "
          f"recovery: {rec_applied} applied, {rec_skipped} skipped")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "chunk": do_chunk()
    elif mode == "apply": do_apply()
    else: print(__doc__); sys.exit(1)
