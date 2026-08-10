# Waypoint — dave_champion

_Last updated: 2026-08-07_

## Goal
Publish the project's HTML pages as a live site via GitHub Pages. **New major workstream:**
an interactive HTML edition of the book *Income Tax: Shattering The Myths* (in `book/`).

---

## Book edition (`book/`) — interactive HTML

**Status: ✅ built + proofread (local); ⚠️ not yet published**

Pipeline (deterministic, re-runnable generators, all in `book/`). **Build order matters:**
`clean.py` → `proofread.py chunk` → `proofread.py apply` → `build_register.py` → `build_html.py`.
1. `clean.py` — raw OCR → cleaned MD (`Book - …Shattering the Myths.md`). Strips
   running heads/footers/page-numbers (kept as `<!-- page: N -->` anchors), rebuilds
   3 duplicate zones, applies safe OCR fixes. Backup: `…raw-ocr.md`. Report: `cleanup_report.txt`.
2. `proofread.py` — Stage-2 proofreading. `chunk` partitions the cleaned MD into
   `proofread_chunks/` (57 pieces); a multi-agent **workflow** wrote exact before→after
   edits per chunk; `apply` applies `proofread_edits.json` in place with a hallucination
   guardrail. **1,212 edits applied** (OCR/split/punct/quote) + **52 handwriting removals**
   (garbled signatures/margin notes deleted). Pre-proofread backup: `…pre-proofread.md`.
   Log: `proofread_apply_log.json`. Reproducible: same clean MD + `proofread_edits.json` → same result.
3. `build_register.py` — proofread MD → `link_register.md` + `link_register.json`
   (SCOTUS→Justia, USC/CFR→Cornell LII, Constitution→Constitution Annotated, IRS forms,
   Treasury Decisions sourced from `../transcription-agent/TREASURY_DECISIONS.md`).
4. `build_html.py` — proofread MD + `link_register.json` → the HTML edition + `treasury_decisions.json`.

**Output:** `Book - Dave Champion - Income Tax - Shattering the Myths.html` (single self-contained file):
- Sticky sidebar nav + a generated **Contents** (replaces the OCR dot-leader TOC; all links resolve).
- Inline citation enrichment **driven by `link_register.json`** (433 links; verified the register
  is the source, not re-derived — e.g. F-cites use the register's case-name query URLs).
- **404 per-page PDF back-links** rendered as right-aligned `PDF p.N` pills (printed page →
  physical PDF page via measured offsets: arabic +23, roman +11). 4 OCR-junk labels left unlinked.
- Treasury Decision links resolved **at load time** from `treasury_decisions.json` (fetch), so the
  mapping can update without rebuilding the HTML.
- Validated: 0 broken in-page links, 0 unbalanced tags, 0 leaked dot-leaders.

### ⚠️ Known issues / debt (book edition)
- **OCR proofreading pass is DONE** (hybrid: multi-agent workflow, 1,212 edits + 52 handwriting
  removals, quotes preserved verbatim, structure intact). Residual: **26 edits missed** (agent's
  `before` string didn't match exactly — those specific OCR errors remain; see `proofread_apply_log.json`).
  The book still contains a small tail of OCR errors the agents didn't catch; a second sweep could
  reduce it further but returns diminish.
- **PDF back-links need the PDF served alongside the HTML.** The 16 MB PDF is currently untracked
  in git, so on GitHub Pages those `#page=` links will 404 until the PDF is published (or the links
  are pointed elsewhere).
- **Dynamic TD + PDF links need HTTP** (GitHub Pages fine; opening via `file://` blocks the TD fetch).
- Register still flags T.D. 2382 (cited in book, not yet in `TREASURY_DECISIONS.md` — owner to add)
  and ~7 `verify` cases (F./parallel cites without deterministic URLs).

### Book edition — next steps
- [ ] Dedicated typo / OCR-correction proofreading pass over the cleaned MD (fold fixes into `clean.py`).
- [ ] Decide PDF-hosting for the live site (publish the PDF, or repoint page links).
- [ ] Wire the book HTML into the site / `index.html`; confirm TD dynamic fetch + PDF links over HTTPS.

---

## Site (GitHub Pages)

## Status: ✅ Live and styled

**Live site:** https://dogthathunts.github.io/dave_champion/

| URL | Purpose |
|-----|---------|
| `/dave_champion/` | Placeholder home (`index.html`), links to the whiteboard page |
| `/dave_champion/whiteboard_income_tax.html` | Whiteboard: Income Tax page (styled) |
| `/dave_champion/dry_fasting_summary.css` | Stylesheet used by the whiteboard page |

## Repo
- **GitHub:** https://github.com/DogThatHunts/dave_champion (public)
- **Account:** DogThatHunts · **Branch:** `main`
- **Pages source:** deploy from `main` / root (`/`)

### Tracked files
- `index.html` — placeholder home page linking to the whiteboard page
- `whiteboard_income_tax.html` — references `dry_fasting_summary.css` (relative path, line 8)
- `dry_fasting_summary.css`
- `.gitignore`

### .gitignore behavior
```
*.css
!dry_fasting_summary.css
```
Ignores all CSS **except** `dry_fasting_summary.css` (which the live site needs).
Any *other* `.css` file added later stays out of the repo.

## History / key decisions
1. Created public repo, pushed `whiteboard_income_tax.html` + `dry_fasting_summary.css`.
2. Added `.gitignore` (`*.css`) and untracked the CSS — this broke live styling.
3. Added placeholder `index.html` (root URL had no index → would 404 otherwise).
4. Enabled GitHub Pages (branch `main`, root).
5. Re-tracked `dry_fasting_summary.css` via a `!`-exception so styles load live.

## Verified
- Build status: `built` (no errors).
- `/` → 200, `whiteboard_income_tax.html` → 200, `dry_fasting_summary.css` → 200 (`text/css`).
- CSS link in the HTML is a correct relative path.

## Notes / dependencies
- Google Fonts (Playfair Display + Inter) load from Google's CDN via a `<link>` in
  the HTML `<head>` — requires the viewer to be online; not vendored in the repo.
- Pages rebuilds automatically ~30–60s after each push.

## Open / next steps
- [ ] Replace the placeholder `index.html` with real home-page content.
- [ ] (Optional) Vendor the Google Fonts locally to remove the CDN dependency.
