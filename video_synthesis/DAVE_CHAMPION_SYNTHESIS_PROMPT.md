# Prompt: Generate / Regenerate `DAVE_CHAMPION_TAX_SYNTHESIS.md`

This is a self-contained, paste-ready prompt for a fresh agent (or a future
session) to rebuild the cross-video synthesis of Dave Champion's income-tax
videos from scratch. It captures the goal, the exact source set, how to obtain
the transcripts, the analytical framing, and the output contract so the result
is reproducible.

Run it from the repo root (`/Users/edward/Projects/transcription-agent`) on a
machine with the poller's Drive OAuth credentials in `.env`.

---

## Task

Produce a ~1.5-page Markdown file, `DAVE_CHAMPION_TAX_SYNTHESIS.md`, that
synthesizes the argument Dave Champion makes across his income-tax videos —
**calling out inconsistencies and contradictions, and noting where assertions
are reinforced.** Work from the **transcripts** (the primary source), not the
AI-generated summaries; bottom out the highest-confidence tensions against the
actual transcript passages before asserting them. Defer external citation links
(to statutes/cases/TDs) to a later pass — but tag each finding with the source
video(s) so any claim can be traced back.

## Source set (the 33 "tax index" rows)

The curated tax videos are the rows on the income-tax index page
(`docs/dave-champion-income-tax.html` in the public `transcript-summaries`
repo; slugs end in the sheet row number). As of the last build:

```
1217 1218 1219 1220 1221 1222 1223 1224 1225 1226 1227 1230 1231 1232 1233
1234 1235 1236 1237 1239 1241 1243 1244 1245 1246 1247 1249 1250 1251 1252
1253 1254 1255
```

To re-derive the list (in case the index changed), pull the slugs from the
published index:

```bash
gh api repos/DogThatHunts/transcript-summaries/contents/docs/dave-champion-income-tax.html \
  --jq '.content' | base64 -d \
  | grep -oE 'href="posts/[a-z0-9-]+\.html"' | sed -E 's#.*-([0-9]+)\.html"#\1#' | sort -un
```

## Step 1 — Pull the transcripts from Google Drive

Each Queue row's transcript is a Drive `.txt` file linked in column I
(`transcript_drive_link`, `COL["transcript_drive_link"] = 9`). The poller's
personal OAuth (which created the files) can read them back under the
`drive.file` scope. Read the row → link map from the sheet, extract the file
IDs, and download to `/tmp/tax_transcripts/rowNNNN.txt`.

- Sheet access: `mac-poller/sheets_queue.py` → `SheetsQueue(os.environ["GOOGLE_CREDENTIALS_PATH"], os.environ["GOOGLE_SHEETS_ID"])`, read `Queue!A1:Q`, index by sheet row number.
- Drive creds (note: `GOOGLE_CREDENTIALS_PATH` is **not** an authorized-user file — build creds explicitly like `drive_uploader.py` does):

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
creds = Credentials(
    token=None,
    refresh_token=os.environ["DRIVE_OAUTH_REFRESH_TOKEN"],
    client_id=os.environ["DRIVE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["DRIVE_OAUTH_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/drive.file"],
)
creds.refresh(Request())
# build("drive","v3",...).files().get_media(fileId=...) → MediaIoBaseDownload
```

Extract each file ID with `re.search(r"/d/([^/]+)/", link)`. Expect ~33 files,
~1.2M chars (~200k words) total; row 1249 alone is a ~25k-word interview.

## Step 2 — Fan out readers to extract claims (do NOT read all 33 into one context)

Spawn parallel subagents (Agent tool, `general-purpose`), each reading 2–3
transcripts (row 1249 alone — it's huge). This keeps each context small and
parallelizes ~200k words. Give every reader the **same framing** so outputs are
comparable.

**The thesis (state it to every reader):** the federal income tax, as written,
was never imposed on ordinary Americans earning domestic income in the fifty
states.

**The four pillars (classify each claim under exactly one):**

- **P1 Definitional** — terms of art (`employee`, `wages`, `income`, `includes`,
  `U.S. person`, `trade or business`, `state`) are narrow and exclude ordinary
  Americans.
- **P2 Forms/withholding** — W-4/W-9/W-2/1040/1099/I-9 apply only to
  federally-connected persons; signing them self-inflicts a false legal
  presumption; illegal employer withholding.
- **P3 Constitutional** — 16th Amendment, Brushaber, Moore v. United States,
  direct vs. indirect/excise, apportionment, sales tax, tariffs; the income tax
  is an excise on a privilege and labor/property are rights.
- **P4 Jurisdiction/enforcement** — "state"/"United States" = D.C./territories;
  levies, criminal cases, computer/records fraud, the "definition" scam, hidden
  Treasury Decisions, the insider "cabal."

**Per-video output contract for each reader:**

```
### row<N> — <short title>
- **Thesis stance:** one sentence.
- **Claims:** up to 10 bullets (up to 20 for the long interview), each:
  `[P#] <claim in one crisp sentence> | mechanism: <statute/case/form/definition he cites> | caveat: <exception/qualification/hedge he states, or "none stated">`
- **Internal tension:** contradictions/qualifications WITHIN this video (or "none noted").
- **Specific authorities cited:** statutes, cases, forms, TDs, agencies named.
```

Instructions to every reader: transcripts are raw ASR (unreliable punctuation,
mis-hearings — e.g. "Brushaber" → "Bruce Schaefer"). Quote short phrases where a
claim is unusually **absolute** (those are what later conflict) and where he
**hedges/concedes** (interviews surface hedges the scripted videos omit). Do NOT
editorialize on whether he is legally correct — faithfully capture what he
asserts. The entire response is captured as data; no preamble.

Steer specific readers: 1227 (how he distinguishes convicted tax protesters —
Snipes/Schiff/Rose/Meredith/Jackson — from his own theory, and what he concedes
courts reject); 1231 (his exact "includes" mechanics); 1252 (exactly which
case/ruling he says held ordinary Americans owe no tax, verbatim); 1253 (whether
he treats Social Security the same as, or differently from, the income tax).

## Step 3 — Synthesize

Cluster the extracted claims:

- **Reinforcement** = claims that recur near-verbatim across many videos (list
  the rows). These are the load-bearing spine. Note the *structural* fact that
  reinforcement is largely by restatement (fixed opening thesis + bio hook), and
  that the P1-definitional and P3-constitutional-excise derivations are presented
  as mutually confirming though they are logically distinct routes.
- **Contradictions/tensions** = pair claims that conflict. The richest seam:
  the *same conclusion* reached via *different, sometimes incompatible*
  mechanisms (foreign-person vs. government-employee vs. territorial-jurisdiction
  vs. constitutional-excise). The deepest known contradiction: the §3402 /
  Chapter 24 wage-withholding class is defined as "government employees only"
  (e.g. row 1246) vs. "non-resident aliens only" (e.g. row 1247) — the same
  statute, opposite covered class. **Verify the top finding(s) directly against
  the transcripts** (grep the two files) before labelling High.

Also flag, distinctly, any claim that conflicts with an **external** authority
he cites (not with himself) — label it `[claim vs. source]` (e.g. his reading of
*Moore v. United States*, which actually upheld the tax against the taxpayers).

## Step 4 — Output conventions

- **Length:** ~1.5 pages.
- **Framing:** central thesis → four pillars → "Where the argument reinforces
  itself" → "Inconsistencies & contradictions" → a short "pattern underneath"
  close.
- **Attribution:** tag every finding with `(see: <rows>)` — comma-separated row
  numbers.
- **Citation links (2026-11-13 — no longer deferred):** link every named case,
  IRC section, and IRS form on first mention, against `citations/link_register.json`
  first, then the sibling `transcription-agent/publisher/citations.py` map
  (verified-resolving curated URLs) for anything missing from the register.
  Do NOT invent a URL — if neither source has it, leave it unlinked and log it
  in `new_citations_from_videos.md` (the register itself is rebuilt from
  scratch by `build_register.py` on every run, so don't hand-edit it directly;
  park new entries in that file instead, same pattern as book #2's
  `build_new_citations.py` diff). Treasury Decisions usually can't be linked
  from the synthesis alone — the videos give counts, not `T.D. NNNN` numbers;
  that needs a transcript grep, not a citation-register lookup.
- **Confidence legend** up top: **High** = same statute/claim stated two opposing
  ways, quotable both sides; **Medium** = real tension, partly reconcilable as
  emphasis/context; **Low** = minor or likely wording/ASR artifact.
- **Fidelity caveat** up top: the analysis is grounded in transcripts, but a
  flagged contradiction could be substantive or an artifact of ASR/summary —
  labelled accordingly.
- Link the header to the live index page where natural.

## Optional — republish the styled page

The synthesis is also published (unlinked) at
`docs/dave-champion-income-tax-synthesis.html` in the public repo. To
regenerate that page, render the Markdown with `publisher.renderer.markdown_to_html`
(strip the `#` H1 → hero title), wrap it in the site template pointing at
`assets/style.css`, keep the `noindex, nofollow` meta, and apply the
page-scoped **cool / dark-navy** inline `<style>` override (do NOT edit the
shared `style.css`). Push via `publisher.github_client.GitHubClient(..., dry_run=False)`
(`dry_run` defaults to True — must pass False to actually write). Do not add a
link from the tax index unless asked.

## 2026-11-13 update — rows 5596–5613 (new `youtube_follow` batch)

A fresh batch of 18 Dave Champion videos landed via `youtube_follow` at rows
5596–5613. Dedup check: compared video IDs against the existing 33-row tax
index (rows 1217–1255) — **no overlaps**, nothing to retire.

Like the original 1217–1255 batch (39 submitted, only 33 curated into the
tax index — Dave Champion's channel mixes income-tax/law content with
health/diet content), this batch is mixed too. Per the user's call, **6 rows
are excluded as not-tax-at-all (health/diet)** and flagged in the Queue sheet
(new column `AG`, `dave_champion_scope_note`, dated 2026-11-13):

```
5601  Americans Are The Sickest People In Human History
5604  existential threat to Big Pharma, Big Med, Big Food
5607  Boundless Body Podcast (off-the-cuff, general)
5609  Media Lies Can Cause Physical Harm
5611  GOUT or GALLSTONES
5613  Carnivore / Alzheimer's
```

The remaining 12 are slated for inclusion:

```
5596  Dowling Interviews Champion About The Income Tax Scam
5597  COMMON LAW TRUSTS - What You NEED to know
5598  STOP Demanding a Form W-9
5599  After this interview, you will never see the U.S. govt the same way
5600  WHITEBOARD Showing Why Ordinary Americans Don't Owe Income Tax
5602  The Americans Who Lie In Order To Enslave You
5603  How The IRS TRICKS You Into Paying Income Tax
5605  So Many Things The Govt Doesn't Want You To Understand
5606  Chris Moffet / Unplugged Alpha — truth of the income tax
5608  The Income Tax Does NOT Apply To YOU
5610  IRS Documents Show Payroll Withholding Is ONLY For Aliens
5612  Treasury Dept Says Wage Withholding Is Only For Foreigners
```

**Resolved 2026-11-13:** user confirmed 5599 and 5602 are in. Final count:
33 existing + 12 new = **45** tax-index rows once this batch lands (the
user's earlier 43 was the 2-row gap now closed).

**Citation-register diff — do it in this pass, not deferred**, per the user
2026-11-13. Rationale: `citations/link_register.json` (and
`treasury_decisions.json`) already carries ~most of the statutes/cases Dave
Champion repeats (16th Amdt, Brushaber, specific IRC/CFR sections, named
TDs) because the two books cover the same arguments — so for any citation a
new video names that **already has a register entry**, linking it is a
mechanical, already-verified match, not new research, so there's no
fabrication risk in doing it now. Only a citation with **no** register
match needs the slower verified-lookup treatment (`citations/CITATION_LINKING.md`
rules) — those get logged as `[UNLINKED — new citation, needs verification]`
rather than guessed at, and that's the only part that's genuinely a "later
pass." So: diff each reader's "Specific authorities cited" list (already
part of the Step 2 output contract below) against the register by `cite`
string within the matching category (`scotus_and_courts`, `usc_title26_irc`,
`cfr`, `treasury_decisions`, `constitution`, `irs_forms`,
`constitutional_clauses`, `acts_of_congress`, `secondary_authorities`), pull
`url` for matches, and flag misses for a follow-up verification pass. The
original 33-row synthesis still has no citation links at all (by the
original deferred-to-later-pass decision); whether to backfill those too is
open — ask before doing it, since it's a second, larger piece of work.

**Status as of 2026-11-13 (next step: wait for these to finish, per the Mac
poller/summarizer/publisher pipeline, before pulling transcripts):**
- Transcribing (poller): 5596, 5599 — bot-block deferral
- Summarizing: 5603 (`generating`)
- Everything else in the 12 (5597, 5598, 5600, 5602, 5605, 5606, 5608, 5610,
  5612): already `published`.

**Update 2026-11-14:** 5596 and 5603 finished (transcribed + summarized +
published) since the note above. Only **5599** is still outstanding
(transcription not yet attempted). Separately, the user's spot-check of the
published summaries found real bugs in the **video-summary** citation linker
(`transcription-agent/publisher/citations.py` — a different pipeline from
this project's book builders): bare "Form 1099" missing from its curated
map, plurals ("W-9s"/"1040s") never linking, and no Acts-of-Congress category
at all. Fixed there (see that repo's `WAYPOINT.md` §0a16 and
`publisher/CITATION_LINKING.md`). The 11 already-published tax rows (5596,
5597, 5598, 5600, 5602, 5603, 5605, 5606, 5608, 5610, 5612) were re-flagged
for republish so they pick up the fix; 5599 will get it on its first
publish, no republish needed. **Next step is still the same:** wait for
5599, then proceed with steps 1–5 (now folding in the TD-number transcript
grep per the earlier note above).

**Update 2026-11-14 (later same day):** corrected the above to a proper
withdraw-then-republish instead of a bare overwrite. `gh_publish_state` set
to `withdraw` for all 11 rows (deletes the stale post file, drops it from
`posts.json`, rebuilds the index) and `gh_published_url` cleared in the
sheet. Once the publisher's next cycle confirms `withdrawn`, these need
flipping back to `publish` for a second cycle to regenerate fresh with the
fixed linker — not yet done. Next step otherwise unchanged: wait for 5599
and this withdraw/republish pair, then proceed with steps 1–5.
