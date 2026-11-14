# New citations — Dave Champion video synthesis (RESOLVED 2026-11-14)

Historical record. This file originally parked citations found in the video-transcript
synthesis that weren't yet in the shared register, because hand-editing
`link_register.json` directly doesn't survive `build_register.py`'s next
rebuild. **As of 2026-11-14, all of them are resolved** — two by that same
day's IRS-form regex fix (which made book #1's own W-9/W-4 mentions
auto-detectable via normal text scanning, so they no longer needed manual
help), and the rest via a durable "manual additions" block added directly to
`build_register.py` (entries tagged `"source": "video_synthesis_2026-11-13"`
in `link_register.json`, so they regenerate on every future rebuild instead
of needing to be re-parked).

| Citation | URL | How it's resolved now |
|---|---|---|
| *Moore v. United States*, 602 U.S. 572 (2024) | https://www.law.cornell.edu/supremecourt/text/22-800 | `build_register.py`'s manual-additions block (`scotus_and_courts`) — never appears in book #1's text, so it will never be auto-detected; this is the permanent home for it. |
| Form W-9 | https://www.irs.gov/forms-pubs/about-form-w-9 | **Auto-detected.** Book #1 says "Form W-9" 33 times — once the 2026-11-13 regex fix landed, normal text scanning found it; no manual entry needed. |
| Form W-4 | https://www.irs.gov/forms-pubs/about-form-w-4 | **Auto-detected**, same fix — book #1 says "Form W-4" 40 times. |

Three more were added to the same manual-additions block 2026-11-14 (also
never found in either book's text — video/publisher-side-only citations):
Form 1099-NEC (`irs.gov/instructions/i1099mec` — the real IRS slug for the
*combined* 1099-MISC/1099-NEC instructions, not a typo), Form 1099-INT
(`irs.gov/instructions/i1099int`), Form 1099-DIV (`irs.gov/instructions/i1099div`)
— all user-supplied, all verified resolving.

Already-covered citations used by the synthesis (no new entry needed — linked
straight from the existing register / sibling map):
- Brushaber v. Union Pacific Railroad, 240 U.S. 1 — `scotus_and_courts`
- Steward Machine Co. v. Davis, 301 U.S. 548 — `scotus_and_courts` (synthesis text spells it "Stewart Machine" — an ASR artifact per the doc's own fidelity caveat; left as-is in the prose, linked to the correctly-named case)
- 26 U.S.C. § 3401, § 3402 — `usc_title26_irc` (Cornell LII, subsection letters stripped per the publisher's citation-linking convention)
- Form 1040, Form 1099, Form 1099-R, Form 1099-MISC — `irs_forms` (all now auto-detected)

**Still not linked — Treasury Decisions in this specific synthesis file.** The
original 33-row synthesis text only gives counts ("7 → 9 → 11 TDs") from the
videos, never specific `T.D. NNNN` numbers. This was separately resolved for
the *45-video* digest (`DAVE_CHAMPION_FULL_DIGEST.md`) — row 5612 named the
full 10-TD list, added to `transcription-agent/TREASURY_DECISIONS.md` and
from there into `citations/treasury_decisions.json` (now 16 entries). The
original 33-row file itself was not retroactively updated with TD numbers;
not asked for.
