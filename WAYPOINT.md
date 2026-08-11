# Waypoint — dave_champion

_Last updated: 2026-08-10_

## Goal
Publish the project's HTML pages as a live site via GitHub Pages. **New major workstream:**
an interactive HTML edition of the book *Income Tax: Shattering The Myths* (in `book/`).

---

## Book edition (`book/`) — interactive HTML

**Status: ✅ LIVE & published**
- Edition: https://dogthathunts.github.io/dave_champion/book/
- Link register (HTML): https://dogthathunts.github.io/dave_champion/book/link_register.html
- Source PDF **is now published** (`book/Book - …Shattering the Myths.pdf`, ~16 MB) so the
  edition's per-page back-links resolve.

Pipeline (deterministic, re-runnable generators, all in `book/`). **Build order matters:**
`clean.py` → `proofread.py chunk` → `proofread.py apply` → `build_register.py` →
`build_register_html.py` → `build_html.py`.
1. `clean.py` — raw OCR → cleaned MD (`Book - …Shattering the Myths.md`). Strips
   running heads/footers/page-numbers (kept as `<!-- page: N -->` anchors), rebuilds
   3 duplicate zones, applies safe OCR fixes. Backup: `…raw-ocr.md`.
2. `proofread.py` — Stage-2 proofreading. `chunk` → `proofread_chunks/` (57 pieces); a multi-agent
   **workflow** wrote exact before→after edits; `apply` applies `proofread_edits.json` +
   `proofread_recovery.json` (global unique-match fixes) with a hallucination guardrail
   (`_suspicious`; bypass a vetted edit with `"force":true`; `"all":true` = replace-all).
   ~1,230 fixes applied incl. 52+ handwriting removals. Pre-proofread backup: `…pre-proofread.md`.
   Do NOT run `proofread.py chunk` on an already-proofread MD (edits are keyed to clean-MD chunks).
3. `build_register.py` — proofread MD → `link_register.md` + `link_register.json`. 11 sections:
   cases (full "Name. Cite at pin (Year)" → Justia), USC/CFR → Cornell LII, Treasury Decisions
   (from `../transcription-agent/TREASURY_DECISIONS.md`), Constitution + founding docs, IRS forms,
   constitutional Article/Section/Clause, named Acts, Executive Orders, secondary authorities,
   IRS/Treasury guidance docs. Curated `CASE_FIXES`, `ACT_URLS`, `FOUNDING`, `CFR §1.1-1`.
4. `build_register_html.py` — `link_register.json` → `link_register.html` (styled like the edition).
5. `build_html.py` — proofread MD + `link_register.json` → the HTML edition (+ `index.html` copy
   for the clean `/book/` URL) + `treasury_decisions.json` sidecar.

**Edition features:**
- Centered title block + Table of Contents (DEDICATION style); TOC entries sized by seniority
  (h1–h3 larger dark ink, h4–h5 smaller dark gold). ALL-CAPS section headers centered/enlarged.
- ~559 inline citation links across 11 categories, colour-coded (legend in sidebar), **driven by
  `link_register.json`**. A precedence engine resolves overlapping link rules and would highlight
  conflicts (currently 0); report in `citation_conflicts.txt`.
- ~404 per-page `PDF p.N` back-links (printed→physical page via offsets: arabic +23, roman +11).
- Treasury-Decision links resolved **at load time** from `treasury_decisions.json` (fetch) — update
  the mapping without rebuilding the HTML.
- Validated each build: 0 broken in-page links, 0 unbalanced tags, 0 nested anchors, 0 dot-leaders.

### ⚠️ Known issues / debt (book edition)
- Small **tail of residual OCR errors** the proofread agents didn't catch (26 per-chunk misses were
  recovered via `proofread_recovery.json`; more may remain). Fixed on request as spotted.
- **Dynamic TD fetch + PDF back-links need HTTP** (GitHub Pages ✓; `file://` blocks the TD fetch).
- Register flags T.D. 2382 (cited in book, not yet in `TREASURY_DECISIONS.md` — owner to add) and a
  few `verify` cases (F./parallel cites without deterministic URLs). Acts without clean govt URLs
  fall back to LoC Statutes at Large. Constitutional links are section-level (clause named in text).
- **Copyright:** the book is © 2010 Dave Champion; the full text + PDF are published publicly per
  the owner's direction.

### Book edition — next steps (optional)
- [ ] Replace the placeholder root `index.html` with real home-page content.
- [ ] Add T.D. 2382 to `../transcription-agent/TREASURY_DECISIONS.md`; recover more OCR tail if desired.

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
