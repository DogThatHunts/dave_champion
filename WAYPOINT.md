# Waypoint — dave_champion

_Last updated: 2026-11-14_

> **2026-11-14 — decision: fold citation improvements into the register (not yet
> executed, planning only).** User asked to move this week's citation fixes into
> the central citations register (`citations/link_register.json`) rather than
> leaving them scattered across `publisher/citations.py`'s own curated maps.
> Two objections raised and accepted as the right approach:
> 1. **Hand-editing `link_register.json` directly won't survive the next
>    `build_register.py` run** (it regenerates from book-text scanning every
>    time — same problem that put Moore v. United States and Forms W-9/W-4 into
>    `video_synthesis/new_citations_from_videos.md` as a parked diff instead of
>    the live register in the first place). Durable fix: add a small
>    "known additions, not derived from book-text scanning" block directly into
>    `build_register.py` (mirrored in `build_new_citations.py`) so these survive
>    every future rebuild.
> 2. **Most of this week's additions already live in the register** and need no
>    porting: Brushaber's ASR variants (a publisher-side regex widen only, no
>    new case), the four Acts (Federal Reserve/Social Security/Patriot/Paperwork
>    Reduction — copied *from* the register originally), and the Grace
>    Commission (already added to `SECONDARY` yesterday).
>
> **Decisions on open scope questions:**
> - **Yes** — fold in yesterday's parked `new_citations_from_videos.md` entries
>   (Moore v. United States, Form W-9, Form W-4) at the same time; same
>   durability problem, same fix.
> - **"Shattering the Myths" → `drreality.news/store/`**: include it, but
>   tagged as a **Dave-Champion-only** entry, with a way to *not* blindly reuse
>   it on a future Champion video batch without reconsidering it first (e.g. the
>   link could go stale, or the user may want a different promo link by then).
>   **Open design question, not yet resolved**: the register has no per-entry
>   "re-confirm before reuse" or batch-scoping mechanism today — needs one
>   before this entry is added, not after.
>
> Plan for folding in the parked entries (item 1) follows in chat; not yet
> executed.
>
> **Plan refined, then approved:** checking the register directly first showed
> most of the original "parked" list is already resolved — yesterday's regex
> fix auto-detected `Form W-9`/`W-4`/`1099`/`1099-R`/`1099-MISC` via normal
> book-text scanning, durably. Only two things genuinely need manual
> injection (never appear in either book's text, so scanning will never find
> them): *Moore v. United States* (602 U.S. 572) and three 1099 variants.
> **User supplied the exact URLs for those three** — instructions pages, not
> the simpler "about-form" pages used on the publisher side:
> `Form 1099-NEC` → `irs.gov/instructions/i1099mec` (confirmed: this is the
> real IRS slug for the *combined* "Instructions for Forms 1099-MISC and
> 1099-NEC" — not a typo, as first assumed; verified it covers 1099-NEC in
> detail), `Form 1099-INT` → `irs.gov/instructions/i1099int`, `Form 1099-DIV`
> → `irs.gov/instructions/i1099div` — all three confirmed resolving (200).
> Confirmed no conflict with the "book-derived citations belong in the master
> register too, in case encountered elsewhere" principle — that's exactly
> what the plan already does. Proceeding to execute.
>
> **Executed (commit `5b1d5ec`):** added the durable "manual additions" block to
> `build_register.py` — *Moore v. United States* (602 U.S. 572) and Forms
> 1099-NEC/INT/DIV (user-supplied URLs: `i1099mec`, `i1099int`, `i1099div`,
> all verified 200) now in `link_register.json`, tagged
> `"source": "video_synthesis_2026-11-13"`, surviving every future rebuild.
> Both books + the book-2 diff rebuilt as a regression check — byte-identical
> output, no regressions. `new_citations_from_videos.md` converted from an
> active parking lot to a resolved historical record.
>
> **Session resting point (2026-11-14):** repo clean, nothing uncommitted.
> Carried forward, open: the linkify()/register unification itself (`NEXT_
> ITERATION.md` §26, not built), the *Shattering the Myths* Dave-Champion-only
> scoping/re-confirmation mechanism (not designed — that entry stays out of
> the register until it is), and TDs 2090/2109/4707 still lacking a local
> source.

> **2026-11-14 — Full 45-video digest + DIGEST tile.** User asked for the real
> 45-video synthesis (not a stopgap), published as a public digest page with a
> DIGEST tile (first position) on the income-tax index, plus a citation link
> for *Income Tax: Shattering the Myths* back to Dave Champion's own store
> (`drreality.news/store/`) and an explicit, scoped exception letting every
> citation on that one page link on every occurrence (not just first — the
> site-wide linker is untouched). See `video_synthesis/
> DIGEST_TILE_REQUEST_2026-11-14.md` for the full request record and
> `video_synthesis/DAVE_CHAMPION_FULL_DIGEST.md` for the synthesis itself.
> Pulled all 12 new rows' transcripts and ran claim extraction via 4 parallel
> subagents — **row 5612 resolved a gap this project had carried since the
> original synthesis**: the only video in all 45 that names the full
> 10-Treasury-Decision list behind the recurring "Form 1040 is for
> non-resident aliens" claim (1928, 1953, 2013, 2190, 2313, 2401, 2402, 2815,
> 2988, 6500); every other video only gives a count. 4 new TDs added to
> `transcription-agent/TREASURY_DECISIONS.md`. Published and confirmed live
> via the GitHub API: the digest page, the DIGEST tile, and a date-format fix
> on all 45 video tiles (single line, "MMM YYYY - word count", date first).
>
> **Same-day polish:** user supplied the DIGEST tile's final graphic (kept
> as-is); `DAVE_CHAMPION_FULL_DIGEST.md` dropped "AI" from "not the AI
> summaries" -> "not the summaries"; added color-coded confidence badges
> (High green / Medium orange / Low pink) on the publish side; fixed a
> real, site-wide CSS bug where tile date/word-count lines never actually
> bottom-aligned (`.post-card-body` wasn't a flex container, so the
> existing `margin-top: auto` had nothing to push against). Full detail in
> `transcription-agent/WAYPOINT.md` §0a17. User also corrected the confidence
> badge colors same day — High=red/Medium=amber/Low=green (desaturated),
> not the initial green/orange/pink.
>
> **Flagged, not built:** this register and `transcription-agent/publisher/
> citations.py`'s video-summary linker are two fully separate systems —
> neither feeds the other, which is why every citation gap found this week
> had to be added by hand to both. Possibly a major improvement if unified.
> See `transcription-agent/NEXT_ITERATION.md` §26 and `MIGRATION.md`'s
> deferred list.

> **2026-11-13 — Video synthesis moved in + citation-register fixes.** Moved the
> three Dave Champion video-synthesis files from `transcription-agent/` repo root
> into `video_synthesis/` here (`DAVE_CHAMPION_TAX_SYNTHESIS.md`, `_KIMI.md`,
> `DAVE_CHAMPION_SYNTHESIS_PROMPT.md`) — see that dir's own files for the
> 33→45-row expansion plan (rows 5596–5613 from a new `youtube_follow` batch,
> 6 excluded as non-tax health content, flagged in the Queue sheet) and
> `new_citations_from_videos.md` for citations added while backfilling links
> into the existing 33-row synthesis.
>
> **Found + fixed while doing that backfill (full writeup: `citations/
> CITATION_LINKING.md`'s "Low-confidence mappings" section):**
> - W-9/W-4/W-2 were **never linkable anywhere** — `build_register.py`,
>   `build_new_citations.py`, and both books' `build_html.py` all shared one
>   digit-only form regex that structurally couldn't match a letter-prefixed
>   form. Book #1 says "W-9" 54×/"W-4" 58×/"W-2" 32× and zero were linked.
>   Fixed in all 4 files; both editions rebuilt (confirmed live: 28 W-9 links
>   in book #1, 16 W-4/W-2 in book #2).
> - 6 of 18 `irs_forms` register entries were dead links (mechanically
>   guessed, never checked) — 4 are real but discontinued forms from the
>   1910s–40s (left unlinked, not guessed at); 1099-MISC and 1040-NR needed
>   corrected slugs; added SS-5 (an SSA form).
> - **`transcription-agent/TREASURY_DECISIONS.md`** (the real source of truth
>   for the TD sidecar, `citations/treasury_decisions.json`) updated so 9 of
>   12 TDs point at their local verified transcript page instead of a generic
>   HathiTrust search. While fixing this, caught a second bug: `build_html.py`'s
>   path to that file was off by one directory level, so every run was
>   **silently wiping `treasury_decisions.json` to `{}`** — caught before any
>   commit, restored from git, path fixed, and a guard added so a future wrong
>   path fails loud instead of erasing the sidecar.
> - TD 2090, 2109, 4707 still have no local source — searched treasury.gov/
>   irs.gov/archive.org, came up empty; HathiTrust search remains the link.
>
> **2026-11-14 follow-up — cleanup + republish.** Removed two orphaned, untracked
> HTML files from this repo's root (`Dave Champion — Income Tax.html`,
> `dave_champion_tax_synthesis.html`) — unreferenced duplicate renders of the
> synthesis, now properly living in `video_synthesis/`; `index.html` never linked
> to either, confirmed no other file referenced them before deleting. Separately,
> the user's own spot-check of the **published video summaries** (a different
> pipeline — `transcription-agent/publisher/citations.py`, not this repo's book
> builders) turned up its own bugs: bare "Form 1099" missing from its curated map,
> plural forms ("W-9s"/"1040s") never linking, and no Acts-of-Congress category at
> all (so "the Federal Reserve Act" never linked). All fixed there — see that
> repo's `WAYPOINT.md` §0a16 and `publisher/CITATION_LINKING.md`. The 11
> already-published tax-row summaries (5596, 5597, 5598, 5600, 5602, 5603, 5605,
> 5606, 5608, 5610, 5612) were flagged for republish (Queue `gh_publish_state` →
> `publish`) so they pick up the fix on the publisher's next 30-min cycle. All
> 11 were manually force-published the same session (confirmed live via the
> GitHub API, not the Pages CDN, which lags ~20-30s) — plus 5602's own
> Brushaber-ASR-variant link fix, confirmed separately.
>
> **Same-day follow-up — the Grace Commission.** Found while spot-checking
> rows 5596/5605/5606: "the Grace Commission" cited 3× in book #1 and in 3
> of the new video summaries, never linked anywhere. Added to
> `secondary_authorities` (archive.org's full report, verified resolving —
> see `citations/CITATION_LINKING.md`'s new section for the fix detail,
> including a second bug: `build_html.py`'s secondary-authority linker is
> hardcoded, not register-driven, so the register addition alone did
> nothing until both books' `build_html.py` were also widened). Book #1
> rebuilt (3 links confirmed); the 3 video rows republished and confirmed
> live via the GitHub API.
>
> **Verified, not a bug:** a second Grace Commission mention on two of the
> three rows looked unlinked on spot-check — confirmed it's the existing
> "first mention only per summary" policy on the video-summary side
> (`transcription-agent/publisher/CITATION_LINKING.md`), already applying
> uniformly to every citation type there. No change made; left as-is.

> **Reorg DONE (2026-08-11):** multi-book layout with a shared citation library — see
> [`MIGRATION.md`](MIGRATION.md). Executed the *relocate + retarget* pass: `book/` →
> `books/income-tax-shattering-the-myths/`, `American_Tax_Bible_book/book/` →
> `books/american-tax-bible/`, cross-book docs → `comparisons/`, prompt → `docs/`; old
> `/book/` URL kept as a redirect stub. **Deferred to a follow-up:** the merged
> multi-book register (§3) and unifying the two `build_html.py` into one shared builder
> (§2) — each book still has its own builder; the register is still book-#1-only.
>
> **Pipeline playbook:** [`PDF_TO_MD_PROMPT.md`](docs/PDF_TO_MD_PROMPT.md) — the reusable,
> book-agnostic PDF→MD conversion spec + agent prompt (recon → extract → OCR → citation
> abstraction/parking → validate → HTML handoff). Specs a **parked `new_citations.json`**
> allowlist for the HTML build — **spec only, not yet implemented** (build_new_citations.py
> still emits the `.md` report; HTML allowlist-linking of bare IRC sections is pending).

## Goal
Publish the project's HTML pages as a live site via GitHub Pages. **New major workstream:**
an interactive HTML edition of the book *Income Tax: Shattering The Myths*
(in `books/income-tax-shattering-the-myths/`).

---

## Book edition (`books/income-tax-shattering-the-myths/`) — interactive HTML

**Status: ✅ LIVE & published**  _(URL changed in the 2026-08-11 reorg; verified live 2026-08-12)_
- Edition: https://dogthathunts.github.io/dave_champion/books/income-tax-shattering-the-myths/
- Link register (HTML): https://dogthathunts.github.io/dave_champion/citations/link_register.html
- The old `…/book/` URL is **retired** — redirect stubs were added then removed as
  redundant, so `/book/` now 404s (confirmed). No inbound links relied on it.
- Source PDF **is now published** (`books/income-tax-shattering-the-myths/Book - …Shattering the Myths.pdf`,
  ~16 MB) so the edition's per-page back-links resolve.

> **GitHub Pages runs with Jekyll DISABLED** — a `.nojekyll` file at the repo root makes
> Pages copy files verbatim (no Liquid/Markdown/theme). Required: Book #2's OCR'd MD
> contains literal `{{` from scanned IRS forms, which Jekyll's Liquid parser choked on and
> **failed the whole deploy** (site silently stuck on the old commit). Keep `.nojekyll`;
> don't rely on any Jekyll feature. Our real "build" is the local Python generators.

Pipeline (deterministic, re-runnable generators). The register builders live in the shared
`citations/`; `clean.py`/`proofread.py`/`build_html.py` live in the book dir. **Build order matters:**
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
   for the clean `/books/income-tax-shattering-the-myths/` URL). Reads/writes the shared
   `citations/` (register in, `treasury_decisions.json` sidecar out).

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

### 🔧 Reported for NEXT SESSION (owner feedback 2026-08-10)
1. **Table of Contents looks wrong.** The in-page generated Contents (`.toc-list` in
   `build_html.py`) is centered with a jumble of font sizes and reads as inconsistent —
   especially against the **left-justified body**. The body chapter headings + their epigraphs
   (e.g. "Introduction" followed by the George Orwell epigraph) stay left-justified, so the
   centered gold/tiered TOC clashes with them. Revisit the TOC styling from the CSS added in the
   "Style title block + Table of Contents" commit — likely reconsider centering vs left-align and
   the size gradations; confirm the intended look with the owner.
2. **Some PDF back-links are incoherent with the HTML text.** A number of `PDF p.N` pills open a
   PDF page that doesn't match the surrounding HTML prose. Root cause is almost certainly the
   printed→physical page-offset mapping in `build_html.py` (`phys_page()`, arabic +23 / roman +11)
   being wrong for some ranges (front matter, roman/arabic boundary, or OCR'd page labels that are
   off). Audit the offsets against the now-published PDF and fix per-range.
3. TOC items "embedded in the text" (body section headings) were intentionally left unchanged
   (gold applied to TOC only) — but that's part of why #1 looks mismatched. Decide the consistent
   treatment across TOC + body.

### Book edition — next steps (optional)
- [x] **Verify the edition byline links on the live site** — DONE (2026-08-13): both editions'
      byline links confirmed live with `target="_blank" rel="noopener"` (build `57d7cf1`) —
      Book #1 `Link register →` and Book #2 `New citations →` open in a new tab.
- [ ] **Make the case linker policy-compliant** (`citations/CITATION_LINKING.md`): anchor the
      full `case_name + cite` span (from `link_register.json` `full_citation`), not just the bare
      reporter cite — e.g. link *"Tandy Leather Company v. United States, 347 F.2d 693"*. Do it
      once in the shared/edition builder so both books inherit it. Owner deferred (2026-08-12).
- [ ] Replace the placeholder root `index.html` with real home-page content.
- [ ] Add T.D. 2382 to `../transcription-agent/TREASURY_DECISIONS.md`; recover more OCR tail if desired.

### Treasury Decisions — deferred (owner, 2026-08-13)
- [ ] **Re-present the TD relationship lines on the register** (owner, 2026-08-13): the inline
      "Supersedes / Superseded by / Amended by" lines were **removed from the rendered register**
      (HTML + md) for now — the render loops are commented out in `build_register.py` and
      `build_register_html.py`, but the **data is still in `link_register.json`**
      (`entry["relations"]`) and the unused `VERB_LABEL` import is left in place. Decide the
      proper presentation next session (tie in with the highlighting item below) and re-enable.
- [ ] **Clean up the Treasury Decisions section of the link register** (`citations/`):
      (a) **verify/repair links** — external (HathiTrust) + local PDF + transcript links all
      resolve; fix any dead/wrong ones. (b) **formatting/layout** — tidy the TD table
      columns/notes/status for readability. (c) **ordering** — sort the TD table in **ascending
      numerical order by T.D. number**, even though this overrides the register's default sort
      (currently by occurrence count, desc, in `build_register.py`).
- [ ] **Highlight supersession relationships on the TD transcript DETAIL pages** (detail pages
      only — not the register rows; amends/amended-by are NOT highlighted, supersede only):
      - a **"Supersedes: …"** line → **bright green** highlight (this TD replaces an older one).
      - a **"Superseded by: …"** line → **pink** highlight (draws attention that this TD is
        obsolete). Example: on **T.D. 2382**, the header line *"Superseded by: T.D. 2401 —
        Revision of T.D. 2382 of October 19, 1916"* should get the pink highlight.
      Implement in `build_td_html.py` (style the `.meta` relationship lines) + a class emitted
      from the `> **Supersedes/Superseded by:**` header rows written by `build_td_markdown.py`.

---

## Book #2 — *The American Tax Bible* (`books/american-tax-bible/`)

_Note: moved from `American_Tax_Bible_book/book/` in the 2026-08-11 reorg; `new_citations.md`
now lives inside the book dir. Historical paths below refer to the pre-reorg location._

**Status: 🟢 MD edition built (2026-08-11); citation diff + HTML still to do**

### ✅ Done this session (2026-08-11)
- Installed **tesseract 5.5.3** via `brew install tesseract` (eng/osd/snum).
- Wrote `American_Tax_Bible_book/book/extract_md.py` (PyMuPDF span walk) and built
  **`American Tax Bible.md`** — 766 pages, 1.73 MB. Verified: 8 book sections
  (`# GENESIS`/CRYER/JOHN/TOMMY/`EXODUS`/`REVELATION`/THE FREED/`SALVATION`),
  766 `<!-- page: N -->` anchors (PDF sequence), 10 image-only pages OCR'd inline,
  bold/italic recovered from span flags.
- Extractor logic: strip running head (top-margin CIDFont bold) + printed folio
  (bottom CIDFont digits / "AMERICAN TAX BIBLE" band); reproduced-doc pages keep
  their own headers (non-CIDFont fonts). Reflow by vertical-gap (`PARA_GAP=24pt`).
  OCR renders full page @300dpi grayscale, inverts if artwork is dark (p94 cover).
- Known tail issue: p94 is a stylized dark book cover — OCR only recovers
  "Second Edition" (decorative, low value). TOC dot-leader page numbers land on
  their own lines (cosmetic; TOC regenerated for HTML later).

- **Citation diff done** — `build_new_citations.py` reuses `citations/build_register.py`'s
  regexes on the new MD, diffs against `citations/link_register.json`, writes
  `American_Tax_Bible_book/new_citations.md`: **329 new cites** (63 cases, 190 IRC
  sections, 15 CFR, 21 Acts, 6 clauses, +1 const). NOTE: book #2 formats case cites
  with a **comma** ("Name, 17 U.S. 316"); book #1's regex only allowed a period, so the
  book-#2 script uses `[.,]?` — port this back if the register is ever merged. Same
  known noise as book #1 (a few "Tax Act" fragments) — vet before folding in.
- **HTML style preview done** — `build_html_preview.py` renders any page range reusing
  book #1's `<style>` verbatim; `preview_p1-10.html` (title + TOC + GENESIS) verified via
  headless-Chrome screenshot, matches book #1's look. TOC dot-leader page numbers are
  rejoined in the preview renderer. Full citation-enriched build (`build_html.py`) is the
  next real step.

- **Reflow repair done (owner feedback)** — `extract_md.py` now reflows **prose** to
  one line per paragraph (no mid-sentence carriage returns) while **preserving** ragged
  blocks (lists, enumerations, reproduced-statute subsections). Discriminator: a
  paragraph is prose when ≥60% (`FILL_FRAC`) of its non-final lines reach the block's
  right margin within `FILL_BAND=25pt` (measured from PyMuPDF line bboxes). **TOC** blocks
  (≥3 lines, ≥2 with dotted leaders) are coalesced by `coalesce_toc()` to one entry per
  line — wrapped titles joined, page number kept inline (dotted leaders retained, numbers
  left-justified), bold section labels stand alone. Decisions: keep leaders, prose-only
  reflow, NO de-hyphenation (owner). MD regenerated; preview re-verified via screenshot.
- **Emphasis seams cleaned** — `wrap_line()` now neutralises punctuation/whitespace-only
  spans (no more `_,_` / `_"_`), and `tidy_emphasis()` merges same-style runs a wrap/reflow
  split with a single space (`_subject-_ _matter_` → `_subject- matter_`, `**a** **b**` →
  `**a b**`; newlines not merged, so ragged/list breaks survive). Whole-MD scan: 0 `_ _`
  / 0 `** **` seams, 0 pure-punct italics. Remaining `_16_`-style italics are faithful
  source footnote numbers; `_____` runs are literal form/signature lines. MD regenerated
  (now 1,720,779 chars); `preview_p1-10.html` recreated and screenshot-verified.

- **Full `build_html.py` done** — book #2's interactive edition
  (`American Tax Bible.html`, ~2.3 MB) styled identically to book #1. Adapts book #1's
  citation-linking engine (same RULES/precedence, shared `citations/link_register.json`
  as URL source of truth + deterministic fallbacks so book-#2-only cites still link).
  **Key deltas from book #1's builder:** (1) **1:1 PDF pages** — MD anchors are the PDF
  sequence, so `phys_page()` maps straight through (766 back-links, 0 unmapped);
  (2) **line-preserving paragraphs** — intra-block newlines → `<br>` (book #1 space-joins,
  which would flatten our ragged lists/statutes); prose is already one line so no `<br>`;
  (3) **keeps the book's own detailed TOC** (real content now; no dot-leader drop, no
  synthetic TOC); (4) **underscore-run protection** in `inline()` so form/signature `____`
  aren't parsed as italics; (5) styled title block for THE AMERICAN / TAX BIBLE / Thomas
  Freed; sidebar nav = the 8 book sections; TD links resolve live from the shared sidecar.
  Validated: 1840 cite links, 0 conflicts, 0 nested anchors, balanced tags, screenshot OK.

### ⏭ Next (optional): make TOC entries clickable (needs printed→PDF-seq map, per-book
reset); richer sub-section nav; publish (fold into the MIGRATION.md books/<slug>/ layout).

New, **separate** book by **Thomas Freed** — `American Tax Bible.pdf` (18 MB, 766 pages,
letter). NOT the Dave Champion book. Goal: a clean **Markdown** edition preserving
**emphasis + pagination + structure** (MD now; an HTML edition like book #1 is intended
*later* — typeface/layout can't live in MD, only in HTML/CSS).

### Key findings (recon)
- **Clean, digitally-produced PDF** (Adobe Acrobat 6.0, 2018) — NOT scanned OCR like book #1.
  So we **skip** `clean.py` / multi-agent proofread; the text layer is accurate.
- Body text is set in **subsetted `CIDFont+Fn`** fonts (generic names — the *name* tells us
  nothing about weight/style). BUT **PyMuPDF's span `flags` recover bold/italic correctly**
  even on these (bit 4 = bold, bit 1 = italic). Verified on pp. 50/56/121. → **font-aware
  emphasis extraction is feasible.**
- Structured as Bible-style "books": bold size-12 running head per page (`THE BOOK OF CRYER`,
  `EXODUS`, `THE BOOK OF JOHN`, …) + a small **printed page number that resets per section**
  (≠ PDF sequence). Plan: strip running head/number, emit `<!-- page: N -->` anchors on **PDF
  sequence** (like book #1), and turn each new "book" head into a section heading.
- Many **reproduced source documents** (statutes, IRS letters, court filings) embedded: most are
  **live selectable text** (real Times/Courier fonts). Only **~10 image-only pages** (of 766)
  would need OCR — and **`tesseract` is NOT installed**. 751/766 pages extract as live text.

### Decisions (from owner, 2026-08-11)
1. Deliverable: **MD now, HTML later.**
2. Emphasis: **font-aware** (recover bold/italic via PyMuPDF flags).
3. Citations: **diff vs the repo-root `citations/` register** (book #1's), and write a **local
   list of only the NEW cites** in this book, to fold into the register later.

### Tooling set up
- `American_Tax_Bible_book/book/.venv` — Python venv with **PyMuPDF 1.28.2** (`fitz`) installed
  (system is Python 3.14 with no PDF libs). `pdftotext`/`pdffonts`/`pdfinfo` available; no
  `tesseract`/`mutool`/`qpdf`/`gs`.
- **⏭ PENDING (next session, dangerous mode):** owner will restart Claude in dangerous mode to
  install **tesseract** via `brew install tesseract` (sandboxed `brew` was blocked this session).
  Owner confirmed OCR the ~10 image-only pages **inline** (not placeholders). After install:
  verify `tesseract --version`, then OCR image-only pages during the MD build.

### Plan (not yet built)
- [ ] **First:** `brew install tesseract` (needs dangerous mode — owner restarting Claude for this).
- [ ] `extract_md.py` (PyMuPDF): page-by-page span walk → paragraphs; wrap bold→`**`, italic→`_`;
      strip running head + printed page number; emit `<!-- page: N -->` (PDF seq); promote each new
      "BOOK OF …" head to a heading; **OCR the ~10 image-only pages inline** via tesseract
      (owner chose inline OCR, not placeholders).
- [ ] Citation extractor → diff against `citations/link_register.json` → local
      `American_Tax_Bible_book/new_citations.md` (cites present in this book, absent from register).
- [ ] Verify emphasis/pagination on a sample; decide printed-vs-PDF page mapping (note per-section
      reset) for the eventual HTML back-links.

---

## Site (GitHub Pages)

## Status: ✅ Live (multi-section; Jekyll disabled) — verified 2026-08-12

**Live site:** https://dogthathunts.github.io/dave_champion/

| URL | Purpose |
|-----|---------|
| `/dave_champion/` | Placeholder home (`index.html`), links to the whiteboard page |
| `/dave_champion/whiteboard_income_tax.html` | Whiteboard: Income Tax page (styled) |
| `/dave_champion/books/income-tax-shattering-the-myths/` | **Book #1 edition** (Dave Champion) |
| `/dave_champion/books/american-tax-bible/American%20Tax%20Bible.html` | **Book #2 edition** (Thomas Freed) |
| `/dave_champion/citations/link_register.html` | Shared citation **link register** |
| `/dave_champion/citations/treasury_decisions.json` | TD num→URL sidecar (fetched by the editions) |
| `/dave_champion/comparisons/Books_compared_legal_theory.html` | Legal-theory comparison of the two books |

_Old `/dave_champion/book/` (Book #1's pre-reorg URL) now 404s — retired, no redirect._

## Repo
- **GitHub:** https://github.com/DogThatHunts/dave_champion (public)
- **Account:** DogThatHunts · **Branch:** `main`
- **Pages source:** deploy from `main` / root (`/`), **Jekyll disabled** via repo-root `.nojekyll`
  (see the Book-edition note — Book #2's OCR'd `{{` broke Jekyll; static-copy only now).

### Layout (top level)
- `books/<slug>/` — one self-contained dir per book (edition HTML + source PDF + generators)
- `citations/` — shared library: register builders, `link_register.*`, TD sidecar + local TD PDFs, `CITATION_LINKING.md`
- `comparisons/` — cross-book docs (legal-theory comparison, `Tax_acts_compared.xlsx`)
- `docs/` — reusable `PDF_TO_MD_PROMPT.md`
- root — `index.html` (placeholder home), `whiteboard_income_tax.html`, `dry_fasting_summary.css`, `.nojekyll`, `WAYPOINT.md`, `MIGRATION.md`

### .gitignore behavior
```
*.css                     # except !dry_fasting_summary.css (live site needs it)
.DS_Store
__pycache__/  *.pyc  .venv/
**/settings.local.json
```
Ignores stray CSS (keeps the one stylesheet), macOS cruft, Python build/venv artifacts, and
local editor/agent settings. Book source PDFs and the local TD PDFs **are** committed (see the
Git-LFS-rejected decision below).

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

## Repo file size / Git LFS — RESOLVED (2026-08-12)
Binary assets (PDFs) are committed straight into git history:
- `citations/treasury_decisions/` — local TD source PDFs, **~4.5 MB** total (`td_2815`
  alone ~2.4 MB).
- `books/income-tax-shattering-the-myths/Book - …Shattering the Myths.pdf` — **~16 MB**
  (kept so the edition's `PDF p.N` back-links resolve).
- `books/american-tax-bible/American Tax Bible.pdf` — **~18 MB** (Book #2 source).
- Total: ~37 MB of PDF bytes; whole `.git` ~45 MB. Each PDF is stored **once**
  (verified: 1 blob apiece). Renames/`git mv` are free — only *replacing a PDF's
  content* adds a new permanent copy to history.

**Decision: keep committing the PDFs as-is. Git LFS was rejected** — GitHub Pages does
NOT resolve LFS objects (it serves the ~130-byte pointer stub, not the file), which
would break every served PDF: the Book #1 page back-links and the local Treasury-Decision
PDFs. LFS also only reclaims history via a disruptive `git lfs migrate` rewrite and adds
a client dependency + separate bandwidth quota. If repo size ever becomes a real problem,
host the PDFs **outside git** (GitHub **Release** asset or a bucket/CDN) and link to
absolute URLs — do **not** use LFS for anything Pages must serve. (Full rationale in
`MIGRATION.md`.)

## Citation register — extracted to a shared private repo (2026-08-16)

`citations/link_register.json` was merged with `transcription-agent/publisher/citations.py`'s
curated maps into a new **private** standalone repo, `citation-register` — the single
source of truth going forward for this book, Book #2 (american-tax-bible), and two
new companion projects that cite the same body of law from interview-transcript
summaries: `KL_on_Crrow` (Crrow777 Radio) and `KL_on_RiceRadio`
(RiceTVX/Stranger Than Fiction) — same speaker "KL," different shows.

**Update 2026-08-16:** `citation-register` is now live —
https://github.com/DogThatHunts/citation-register (private). This repo's `citations/`
still has NOT been switched to consume it (no submodule wiring yet — `dave_champion`'s
`link_register.json` here is untouched and still what `build_register_html.py`
actually reads for the published page). **Explicitly on hold** — owner decision
2026-08-16 was to hold off wiring up `dave_champion` and the KL projects
(`KL_on_Crrow`, `KL_on_RiceRadio`) as submodule consumers for now. This repo's
local `citations/` files remain the live source for the published site until
that wiring happens.

**Update 2026-08-15:** Book #2's `new_citations.md` (328 citations, not just the
~63 cases originally scoped) has now been verified against primary sources and
merged into `citation-register/register.json` — see that repo's `CHANGELOG.md`
"dave_champion Book #2 (american-tax-bible) merge (Phase 1, completed)". Still has
**no effect on this repo's published page** (same reason as above — `citations/`
here isn't wired to the shared register yet). The submodule wiring itself, plus the
matching wiring for `transcription-agent/publisher`, remains explicitly parked as
its own follow-up (Phases 2–3) — not started. When it does happen, note that the
merge surfaced and fixed 5 cross-book duplicate `acts_of_congress` entries (this
book's Book #1 citations had registered several of the same acts as Book #2 under
different informal names) and flagged one further unresolved cross-book dedup
opportunity in `citation-register/TBD_later.md` item 8.

Two things resolved during the merge, one deferred:
- Fixed a broken `Form 1099 MISC` URL (literal space) and three OCR-garbled USC section
  citations (`340l`, `770I`, `77O` → folded into `3401` / `7701`) — see
  `citation-register/TBD_later.md` "Resolved log".
- Found `transcription-agent/publisher/citations.py`'s curated case map mislabels
  *Coppedge v. United States*, 369 U.S. 438 (1962) as "Coppedge v. Kansas" — unrelated to
  this book's actual citation, *Coppage v. Kansas*, 236 U.S. 1 (1915). Added a
  disambiguation comment in the book's `.md` source next to the Ch. 4 endnote (**HTML not
  rebuilt this cycle** — the comment doesn't render, so the live page is unaffected until
  the next build). **Update 2026-08-16:** the citations.py mislabel itself is now fixed
  and pushed (`transcription-agent` commit `a4123ff`) — its full pytest suite wasn't
  runnable in the fixing environment (missing `requests`), only verified in isolation;
  see that repo's `WAYPOINT.md` for the caveat. Full detail:
  `citation-register/TBD_later.md`.
- **Deferred, no action taken:** Brushaber and Butchers' Union Co. resolve to the same
  case/cite in both sources but via different hosts (Justia vs. Cornell LII) — a style
  choice for a future register-wide pass, not a correctness issue. Tracked in
  `citation-register/TBD_later.md`.
