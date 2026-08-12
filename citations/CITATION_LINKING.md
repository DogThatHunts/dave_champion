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
