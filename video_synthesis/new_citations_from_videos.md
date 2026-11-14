# New citations — Dave Champion video synthesis

Citations found in the video-transcript synthesis (`DAVE_CHAMPION_TAX_SYNTHESIS.md`
/ `_KIMI.md`) that are **not yet** in the shared register
(`citations/link_register.json`, built by `citations/build_register.py` from
book #1's text and `books/american-tax-bible/build_new_citations.py`'s diff of
book #2 — this file is the same pattern, for the video corpus instead of a
book). Not merged into the live register directly: `build_register.py`
regenerates `link_register.json` from scratch on every run, so a hand-edit
would be silently dropped on the next rebuild. Park here; fold into the
merged multi-book register when that work lands (`MIGRATION.md` §3).

Each entry's URL is already used in the synthesis Markdown files directly
(hand-written links, which don't depend on the JSON register — that register
only drives the automated *book*-edition HTML linker). This file exists so
the entries aren't lost / re-researched later.

| Citation | URL | Verification (2026-11-13) |
|---|---|---|
| *Moore v. United States*, 602 U.S. 572 (2024) | https://www.law.cornell.edu/supremecourt/text/22-800 | Same URL already live and marked "verified to resolve" in the sibling `transcription-agent/publisher/citations.py` `_CASE_LINKS` map. Citation (602 U.S. 572, decided 2024-06-20, docket 22-800) cross-confirmed via Wikipedia/Ballotpedia/SCOTUSblog. Justia's URL for this case (`supreme.justia.com/cases/federal/us/2023/22-800/`, matching the register's usual style) could not be fetch-verified — Justia returns a Cloudflare bot challenge (HTTP 403) to automated requests — so Cornell LII was used instead as the independently-verified source. |
| Form W-9 | https://www.irs.gov/forms-pubs/about-form-w-9 | `curl` HEAD → HTTP 200. Already in `publisher/citations.py` `_FORM_URLS`. |
| Form W-4 | https://www.irs.gov/forms-pubs/about-form-w-4 | `curl` HEAD → HTTP 200. Already in `publisher/citations.py` `_FORM_URLS`. |

Already-covered citations used by the synthesis (no new entry needed — linked
straight from the existing register / sibling map):
- Brushaber v. Union Pacific Railroad, 240 U.S. 1 — `scotus_and_courts`
- Steward Machine Co. v. Davis, 301 U.S. 548 — `scotus_and_courts` (synthesis text spells it "Stewart Machine" — an ASR artifact per the doc's own fidelity caveat; left as-is in the prose, linked to the correctly-named case)
- 26 U.S.C. § 3401, § 3402 — `usc_title26_irc` (Cornell LII, subsection letters stripped per the publisher's citation-linking convention)
- Form 1040, Form 1099 — `irs_forms`

**Not linked — Treasury Decisions.** The synthesis text only gives counts
("7 → 9 → 11 TDs") from the videos, never specific `T.D. NNNN` numbers, so
there is nothing to link without either (a) guessing a number, which the
no-fabrication rule forbids, or (b) re-reading the 33 transcripts to pull the
actual TD numbers out — a separate, larger task. Flagged, not done.
