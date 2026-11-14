# User request — 2026-11-14 — digest tile + full citation linking + book link

Recorded verbatim before any action, per the user's explicit instruction.

> let's create a final tile on page https://dogthathunts.github.io/transcript-summaries/dave-champion-income-tax.html
> which is a summary of all of the transcripts; let's add a citation link for "Shattering The Myths" book back to
> the DrRality.com page where Dave sells his book; all elements in the summaries that can be linked via the
> citation register should be so linked, not just the first instance; we will break policy here
>
> the new tile should be the first tile, and be labeled 'DIGEST' in large courier font with a light blue background
> following the style of tiles established for the video summaries; we may replace it with a graphic later
>
> on the tiles where we show the date, the date should preceed the word count, and be seperated with a hyphen:
> "MMM YYYY - <word count>", etc
>
> record this prompt in an MD file before any action
> questions?

## Status

Questions resolved 2026-11-14:
1. **Book URL:** https://drreality.news/store/ (confirmed resolving, HTTP 200). User's "DrRality.com"
   was a typo/approximation for drreality.news (Dave Champion's "Dr Reality" site/podcast).
2. **Policy-break scope:** "just this document" — the every-occurrence linking exception applies ONLY
   to the new digest page, not to `publisher/citations.py`'s site-wide linker (which stays
   first-mention-only for every other post, including the other Dave Champion video summaries).
3. **Digest content:** finish the real 45-video synthesis now — full claim extraction + synthesis
   over all 45 rows (the 33 original + 12 new tax rows), not a stopgap or shortened version.

Work now proceeding: pull the 12 new rows' transcripts, extract claims (same P1-P4 framing as the
original 33-row synthesis), merge into an updated synthesis, link every citation occurrence on this
page specifically, publish as a new page, and add the DIGEST tile (first position, courier font,
light blue background) to the index page. Also: date-format fix on all tiles ("MMM YYYY - <word
count>", hyphen-separated, date first) and the Shattering the Myths -> drreality.news/store/ link.

## Done (2026-11-14)

- **Transcripts pulled and claims extracted** for all 12 new rows via 4 parallel subagents (same
  P1-P4 framing), saved to `/tmp/dc_claims_*.md` (not committed — scratch; the synthesis below is
  the durable output). **Row 5612 resolved a long-standing gap**: it's the only video across all
  45 to name the full 10-TD list behind the "Form 1040 is for non-resident aliens" claim (1928,
  1953, 2013, 2190, 2313, 2401, 2402, 2815, 2988, 6500) — every other video just gives a count.
- **`DAVE_CHAMPION_FULL_DIGEST.md`** written — the real 45-video synthesis (not a stopgap),
  extending the original's reinforcement/contradiction sections with the new batch's findings
  (3 new contradictions: the two→three→four-class drift, `Gould v. Gould`'s no-implication rule
  applied asymmetrically to Champion's own inference in row 5602, and the "zero forms required"
  claim in row 5600 contradicted by its own worked example). Every citation linked on every
  occurrence (the agreed policy exception, scoped to this page only).
- **`TREASURY_DECISIONS.md`** (transcription-agent repo) updated: 4 new TDs added (1953, 2013,
  2190, 2402 — the first three via HathiTrust fallback, no local source found; 2402 via its
  existing local transcript page), "cited in" rows extended for TDs that recur in the new batch.
- **Published** `docs/dave-champion-full-digest.html` (new page, transcript-summaries repo) and
  the **DIGEST tile** (first position, courier font, `--accent-soft` background, additive-only
  CSS) on the index page — both confirmed live via the GitHub API.
- **Shattering the Myths -> drreality.news/store/** added to `publisher/citations.py`
  (`_SECONDARY_LINKS`), normal site-wide first-mention policy (not the digest's exception).
  40 tests passing.
- **Date format fixed** on all 45 video tiles: single `.meta` span, `"MMM YYYY - <word count>"`,
  date first — reverted the earlier two-span "opposite" layout per the corrected spec.
