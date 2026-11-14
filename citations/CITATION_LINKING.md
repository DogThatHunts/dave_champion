# Citation-linking policy — dave_champion book editions

_Applies to every book under `books/` in this repo. The shared citation library
(`citations/`) is the single source of truth for URLs; each book's `build_html.py` is
the **linker** that turns inline references in the text into `<a>` anchors._

_Sibling policy: the transcript-summaries pipeline has its own linker documented in
`../../transcription-agent/publisher/CITATION_LINKING.md` (curated case-name map for
short prose summaries). This file is the **book-edition** policy; they differ because
books quote full "Name v. Name, `<reporter cite>`" citations while summaries usually
cite a case by bare name._

---

## Headline rule — court cases: link the WHOLE citation

When a case appears with its name **and** a reporter cite, the anchor MUST wrap the
**entire citation** — case name through the reporter cite (and pincite/parenthetical
if adjacent) — not just the bare reporter numbers.

**Target (this policy):**
```html
<a class="cite case" href="…347 F.2d 693…"><em>Tandy Leather Company v. United States</em>, 347 F.2d 693</a> (5th Cir. 1965)
```

**NOT** (bare-cite only — case name stranded outside the link):
```html
<em>Tandy Leather Company v. United States</em>, <a class="cite case" href="…347 F.2d 693…">347 F.2d 693</a> (5th Cir. 1965)
```

Rationale: the reader's eye (and a click target) belongs on the *named* authority, not
a string of reporter digits. The register already stores the exact span to use —
`case_name` + `full_citation` in `link_register.json` (built by `build_register.py`'s
`CASE_FULL` regex + `CASE_FIXES` name corrections).

Sub-cases:
- **Bare cite, no name in text** (`347 F.2d 693` alone) → link the bare cite.
- **Name, no cite** (`Tandy Leather, supra` / short-form) → OPTIONAL: may link the
  short name to the same target as the full citation. Nice-to-have, not required.
- **Ambiguity / OCR-garbled name** → fall back to linking the bare cite only; do not
  guess a span across a mangled name.

## Other citation types (link the canonical token)

| Type | What gets the link | URL source |
|---|---|---|
| USC / IRC sections | the section token (`26 U.S.C. § 61`, or a bare `§ 61` **only if allow-listed** — see below) | Cornell LII |
| CFR | the cite (`26 CFR §1.1-1`) | Cornell LII |
| Treasury Decisions | `T.D. NNNN` | local PDF if present (`treasury_decisions/td_<num>/`), else the shared TD mapping / HathiTrust — **local primary, external secondary** |
| Constitution / amendments | the reference phrase | Constitution Annotated |
| Named Acts, Executive Orders, IRS forms, secondary authorities | the name/number token | curated maps in `build_register.py` |

**Bare `§/section NNNN` guard:** ubiquitous and ambiguous in tax prose, so a bare
section number is auto-linked **only if it is allow-listed** — present in the shared
register or (for a per-book run) in that book's parked `new_citations.json`. This
prevents false-positive links on stray numbers.

**First-mention vs every-mention:** book editions link **every** occurrence (unlike the
summaries linker, which links only the first mention per document). Overlapping link
rules are resolved by a precedence engine and reported in `citation_conflicts.txt`.

---

## ⚠ Implementation status (2026-08-12)

- ✅ **Data is ready:** `link_register.json` already carries `case_name` + `full_citation`
  for every case, so the full span is available to the linker.
- ❌ **Linkers are NOT yet compliant:** both `books/*/build_html.py` currently match only
  the bare reporter regex (`CASE_US`/`CASE_F`) and anchor just the reporter cite — the
  case name is left outside the `<a>` (see any *Tandy* occurrence in Book #2's HTML).
- **TODO:** extend the case linker to wrap `case_name + cite` (drive the span from the
  register's `full_citation`, or widen the regex to include the preceding
  `Name v. Name,` run). Do it once in the shared/edition builder so both books inherit it.
  Tracked in `MIGRATION.md` deferred list.

Until that code change lands, the rule above is the **target**, not the current output.

---

## ✅ Low-confidence mappings found AND fixed 2026-11-13

Found while backfilling citations into the video synthesis (`video_synthesis/`).
Two separate problems, both worth a dedicated pass over the actual book builds
(not just the video synthesis, which only needed hand-written links and
sidesteps all of this):

**1. W-9/W-4/W-2/I-9/W-8BEN were never captured — a code bug, not a data gap.
Fixed 2026-11-13.** `build_register.py`'s IRS-forms regex was
`r"Form\s+(\d{3,4}[- ]?[A-Z]{0,3})"` — digits only after "Form". It
structurally could not match a letter-prefixed form ("W-9", not "Form W-9" in
natural prose), so these forms never entered the register no matter how often
the book said them. **Confirmed this was a real, large gap, not an edge
case:** book #1 (*Income Tax: Shattering the Myths*) says "W-9" 54 times,
"W-4" 58 times, "W-2" 32 times — and **zero** were hyperlinked in the
published book HTML, because the *same* digit-only regex was duplicated a
third time in `build_html.py`'s live `FORM` linker, so a register entry alone
wouldn't have helped without also fixing the renderer. `build_new_citations.py`
(book #2) and its own `build_html.py` had the identical regex (4 copies of one
bug total) — book #2's W-4 (17×)/W-2 (16×) mentions had the same gap.
**Fix:** widened the capture group in all four files to
`[A-Z]{0,2}-?\d{1,4}(?:[- ]?[A-Z]{1,4})?` (still requires the literal word
"Form" first — same ambiguity guard as before, so a bare "W-9s" with no
"Form" prefix is still not captured, by design). Added verified URLs for
W-9/W-4/W-2/W-8BEN/I-9 (copied from the sibling `transcription-agent/
publisher/citations.py` `_FORM_URLS` map, already verified there) to a new
`FORM_URL_OVERRIDES` dict in `build_register.py`. Rebuilt both books —
confirmed live: 28 W-9 links in book #1's HTML, 16 W-4/W-2 links in book #2's.

**2. ~22% of the existing `irs_forms` entries were dead links — mechanically
generated, never checked. Fixed 2026-11-13.** `form_url()` built
`about-form-{slug}` from whatever the regex matched, with no resolution
check, despite this file's own rule ("confirm the URL resolves first") — that
rule was followed for hand-added curated entries but not by the automated
extractor. Checked all 18 entries: **6 were dead** — `Form 1043`, `Form 1044`,
`Form 1040W`, `Form 1031` (all four are genuine historical/discontinued forms
with no current IRS page — confirmed against the book's actual text, e.g.
"Form 1043 is a monthly list return of taxes withheld... by licensed banks" —
real but obsolete since the 1910s–40s; left unlinked, not guessed), `Form
1099 MIS` (an OCR/regex artifact of "1099-MISC", truncated by the old `{0,3}`
letter cap and a stray space instead of a hyphen — fixed to the correct
`1099-misc` slug), and `Form 1040NR` (real form, just needed the hyphenated
slug `1040-nr`). Also added `Form SS-5` (an SSA form, not IRS — URL
corroborated by multiple independent search results; ssa.gov 403s all
automated verification the same way Justia/HathiTrust do, so it's trusted on
convergent-source evidence, not a resolving `curl`, same standard used for
Moore v. United States earlier in this session). **Fix:** `form_url()` now
does a live HEAD check (reusing the TD resolver's existing pattern in this
same file) and drops — rather than emits — any guessed URL that 404s,
printing an `IRS forms UNRESOLVED` list on every build run so a future miss
is visible instead of silent.

**3. Treasury Decisions — the live book pages served a worse link than what's
already on disk for 9 of 12 TDs. Fixed 2026-11-13.** `citations/
treasury_decisions/` has a local verified PDF *and* a pre-built `td_<n>.html`
page for TD 1928, 2313, 2382, 2401, 2402, 2815, 2988, 6500, 8734, 8881, but
the book's rendered pages were resolving TD links from `treasury_decisions.json`
(a flat number→URL sidecar, fetched client-side at runtime by the book HTML —
see `build_html.py`'s comment), which pointed all of them at the generic
HathiTrust full-text-search fallback instead. **Root source of the sidecar is
`transcription-agent/TREASURY_DECISIONS.md`** (`build_html.py` rebuilds
`treasury_decisions.json` from it on every run) — fixed there, in that file's
URL column, to the local `td_<n>.html` page for all 9 (plus TD 8734, which
already had a working IRS `.txt` link but now gets the nicer local page too,
for consistency — it itself links through to both the PDF and HathiTrust).
**Found and fixed a second, more serious bug while doing this:**
`build_html.py`'s path to `TREASURY_DECISIONS.md` was off by one directory
level and silently swallowed the resulting `FileNotFoundError`, so every run
of `build_html.py` **wiped `treasury_decisions.json` to `{}`** — caught
before anything was committed (restored from git), path fixed, and a guard
added that refuses to shrink the sidecar and prints a loud warning instead.
The genuinely low-confidence ones remain the 3 with **no local source at
all** — TD 2090, 2109, 4707 — searched treasury.gov/irs.gov (nothing
pre-1990s) and archive.org's catalog (right 1914–15 bulletin volume not
findable under an indexed identifier); HathiTrust search remains the best
available link for these three. Likely leads for a manual follow-up, given
to the user directly: the HathiTrust catalog records for *Treasury Decisions
Under Internal Revenue Laws, Vol. 16* (1914, covers TD 1927–2112, so both
2090 and 2109) and the UNT "mocat" library catalog entries that surfaced
repeatedly in search (`mocat.library.unt.edu/catalog/242-ch1145` and
neighboring IDs) — both 403 to automated fetches (same bot-protection as
Justia) but may work in a real browser. TD 4707 (tied to Social Security/SS-5,
row 1253) is likely a 1930s Cumulative Bulletin entry; IRS Cumulative
Bulletins from that era are sometimes on archive.org under "Internal Revenue
Cumulative Bulletin [year]".

**Scope note:** none of this blocked the video-synthesis backfill (that work
linked straight to verified URLs by hand, same as `new_citations_from_videos.md`
documents) — it affected the automated book-edition pipeline
(`build_register.py` / `build_new_citations.py` / `build_html.py` ×2), now
fixed and rebuilt. Cross-referenced from `MIGRATION.md`'s deferred list
(updated to reflect the fix).

---

## ✅ Grace Commission added 2026-11-13 (new secondary-authority entry)

Found while spot-checking the republished video summaries: "the Grace
Commission" (the President's Private Sector Survey on Cost Control,
1982–84) is cited 3× in book #1 and never linked, plus cited by name in
three of the new video summaries (rows 5596, 5605, 5606). No existing
category fit cleanly — not a case, Act, form, or TD — so it went into
`secondary_authorities` despite that category's own "non-government
reference works" framing; no better home existed, and the mechanism (name
match + verified URL) works the same regardless.

**Source found:** archive.org has the full report (`archive.org/details/
GraceCommissionReport` — PDF + OCR'd text, verified resolving). The Reagan
Library's own page is a finding-aid description of its holdings, not the
document itself, so archive.org was used as the actual citable source.

**A second bug found doing this:** `build_html.py`'s `SECONDARY` rule (both
books) is a **hardcoded regex + dict, not register-driven** — unlike IRS
forms or Treasury Decisions, which read `link_register.json`/
`treasury_decisions.json` at build time, secondary authorities were matched
by a literal `(Black|Bouvier)['’]s Law Dictionary` pattern baked into each
`build_html.py`. Adding "Grace Commission" to the register alone (via
`build_register.py`'s `SECONDARY` dict) did nothing until this hardcoded
pattern was also widened in both books' `build_html.py` — confirmed by
rebuilding book #1 once with only the register change and finding 0 links,
then again after fixing `build_html.py` and finding all 3. Book #2 has 0
current occurrences but was updated for consistency (same mirrored-file
discipline as the IRS-form regex fix above).
