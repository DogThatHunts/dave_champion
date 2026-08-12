# PDF → Markdown Conversion — Prompt & Playbook

_A reusable, book-agnostic procedure for turning a book PDF into a clean, emphasis-
and pagination-preserving Markdown edition, plus a citation "abstraction" pass that
parks new citations for the downstream HTML build. Distilled from converting
**Income Tax: Shattering The Myths** (Dave Champion, scanned OCR) and **The American
Tax Bible** (Thomas Freed, digitally-produced) in this repo._

> **Agent brief.** You are converting a source PDF into `<Title>.md`: an accurate text
> edition that preserves **bold/italic**, **pagination** (as anchors), and **structure**
> (headings, lists, quoted documents), then abstracts the legal citations and parks the
> new ones for the HTML generator. Work in an isolated venv. Do the recon FIRST — it
> decides which path you take. Prefer deterministic, re-runnable generator scripts over
> hand-editing the MD. Validate every run against the checklist. Do not silently drop
> content; when you strip or skip something, it must be recoverable and logged.

---

## 0. What this produces

| Artifact | Purpose |
|---|---|
| `<Title>.md` | The clean Markdown edition (source of truth for the HTML build). |
| `<Title>.md` `<!-- page: N -->` anchors | One per PDF page (PDF **sequence** number), for back-links. |
| `new_citations.md` | **Human** report: citations in this book absent from the shared register. |
| `new_citations.json` | **Machine** "parked" allowlist consumed by the HTML build (see §Step 4). |
| `extract_md.py`, `build_new_citations.py` | The deterministic, re-runnable generators. |

The HTML edition is a **separate** downstream step (`build_html.py`, see §Step 6). Keep
MD generation and HTML generation decoupled: the MD must be correct on its own.

---

## 1. Inputs & prerequisites

- **Source PDF** in the working dir.
- **Python venv** with **PyMuPDF** (`import pymupdf`, legacy alias `fitz`). The system
  Python may lack PDF libs — create a local `.venv`.
- **Tesseract** (`brew install tesseract`) — only if recon finds image-only pages.
  Needs a non-sandboxed shell for `brew` (run in dangerous mode or have the owner install).
- Optional CLI: `pdffonts`, `pdftotext`, `pdfinfo` (poppler) for recon cross-checks.
- The **shared citation register** (`citations/link_register.json`) to diff against.

---

## 2. Per-book config block  ← fill this in during recon

The method is universal; these values are book-specific. Populate them in Step 1 and use
them throughout. (Values shown are the worked example for *The American Tax Bible*.)

```python
PDF          = "American Tax Bible.pdf"
TITLE        = "American Tax Bible"          # -> <Title>.md / .html
PAGE_ANCHORS = "pdf-sequence"                # anchors are the physical PDF page (1:1)

# --- page geometry (points; PDF is 612x792 letter here) ---
TOP_MARGIN   = 55.0     # y below this = running-head zone
BOT_MARGIN   = 710.0    # y above this = folio/footer zone
HEAD_SIZE    = (11.0, 12.6)   # size range of the running-head text

# --- chrome signature: the publisher's own running head/footer font family ---
CHROME_FONT_PREFIX = "CIDFont"   # book body & chrome are subsetted CIDFont+Fn here
FOOTER_TEXT  = "AMERICAN TAX BIBLE"   # literal footer band text to strip (besides folios)

# --- section ("book"/chapter) heads promoted to '# ' headings ---
BOOK_HEADS   = {"GENESIS","EXODUS","REVELATION","SALVATION",
                "THE BOOK OF CRYER","THE BOOK OF JOHN","THE BOOK OF TOMMY",
                "THE BOOK OF THE FREED"}

# --- pages that are images only (need OCR); 0-based PDF index ---
IMAGE_ONLY   = {93,94,95,96,97,98,348,349,690,727}

# --- reflow tunables (usually leave as-is) ---
PARA_GAP     = 24.0     # vertical gap (pt) that starts a new paragraph
FILL_BAND    = 25.0     # right-edge tolerance for "line reached the margin"
FILL_FRAC    = 0.6      # fraction of non-final lines that must be "full" -> prose
```

**On PAGE_ANCHORS:** if the PDF's text carries printed folios that differ from the PDF
sequence (roman front-matter, per-section resets, etc.), still anchor on the **PDF
sequence** (`i+1`). Any printed→physical offset belongs in the HTML build, not here. Our
digitally-produced book maps **1:1**; the scanned book needed measured offsets *downstream*.

---

## 3. Procedure (ordered, agent-executable)

### Step 1 — Recon & classify  (decides everything downstream)

Run a span/geometry probe over the whole PDF and record:

1. **Digitally-produced vs scanned OCR.** `pg.get_text("text")` returns accurate text on
   digital PDFs (skip any de-OCR/proofread stage). Scanned books have a noisy/absent text
   layer → they need the OCR-cleanup + multi-agent proofread pipeline instead (out of scope
   here; see book #1's `clean.py`/`proofread.py`).
2. **Emphasis recoverability.** Body fonts are often subsetted `CIDFont+Fn` whose *names*
   say nothing about weight/style — but **PyMuPDF span `flags` recover it**:
   `bold = flags & 16` (bit 4), `italic = flags & 2` (bit 1). Verify on 2–3 sample pages.
3. **Chrome geometry.** Find the running head (top-margin span) and printed folio/footer
   (bottom-margin span). Record their **font signature** (family prefix + size + bold) so
   you strip only the publisher's chrome and never the reproduced documents' own headers.
4. **Section heads.** List the distinct running-head values and their page transitions →
   the `BOOK_HEADS` set (major sections to promote to `#` headings).
5. **Image-only pages.** `IMAGE_ONLY = {i : len(page.get_text().strip()) < 20 and page.get_images()}`.
6. **Page-number scheme.** Note printed folios and whether they reset per section (record
   for the HTML build; the MD anchors stay on PDF sequence regardless).

Fill in the §2 config block from these findings.

### Step 2 — Extract to Markdown  (`extract_md.py`)

Walk every page's `get_text("dict")` blocks → lines → spans and emit MD. Core rules
(full detail in §4):

- **Emphasis** from flags → wrap runs in `**bold**` / `_italic_` / `**_bold-italic_**`.
- **Strip chrome:** a top-margin (`y<TOP_MARGIN`) span in `CHROME_FONT_PREFIX`, bold, in
  `HEAD_SIZE` is the running head → drop (and, if its text ∈ `BOOK_HEADS`, mark a section
  transition). A bottom-margin (`y>BOT_MARGIN`) `CHROME_FONT_PREFIX` span that is pure
  digits or `FOOTER_TEXT` is the folio/footer → drop. **Reproduced documents use real
  fonts (Times/Arial/Courier), so their headers/footers are NOT stripped.**
- **Page anchor:** emit `<!-- page: N -->` (N = PDF sequence) before each page's content.
- **Section headings:** when `BOOK_HEADS` changes, emit `# <Head>`.
- **Reflow:** group lines into paragraphs by `PARA_GAP`; classify each paragraph as
  **prose** (≥`FILL_FRAC` of non-final lines reach the block's right margin within
  `FILL_BAND`) → join to ONE line; else **ragged** (lists, statute subsections, forms) →
  keep line breaks. TOC blocks (≥3 lines, ≥2 with dotted leaders) → coalesce to one entry
  per line, page number inline. (See §4.)
- **Emphasis hygiene:** neutralise punctuation/whitespace-only spans (no `_,_`/`_"_`
  seams); merge same-style runs a wrap split with a single space (`_a_ _b_`→`_a b_`).
- **OCR** the `IMAGE_ONLY` pages inline (Step 3).

Emit `<Title>.md`. Keep a params header; the script must be re-runnable and idempotent.

### Step 3 — OCR the image-only pages  (tesseract, inline)

For each `IMAGE_ONLY` page, render and OCR **inline** (not a placeholder):

```python
pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)   # margins give tesseract context
# invert if the page's embedded artwork is predominantly dark (white-on-black cover/photo)
if embedded_image_mean(page) < 110:
    pix.invert_irect()
res = subprocess.run(["tesseract","-","stdout","--psm","3","-l","eng"],
                     input=pix.tobytes("png"), capture_output=True)
text = res.stdout.decode("utf-8", errors="replace").strip()   # tesseract emits non-UTF8 on stderr
```

Prefix the block with a marker (e.g. `> _[Reproduced image — OCR]_`). Notes:
- Full-page grayscale render at 300 dpi handles normal document scans well.
- **Invert** only when the *embedded image's* mean is dark — the full page mean is
  misled by white margins. Stylised/decorative covers may still OCR poorly; accept and log.
- Decode as **bytes** (`errors="replace"`); `text=True` chokes on tesseract's binary chatter.

### Step 4 — Abstract citations & park the new ones  (`build_new_citations.py`)

Reuse the **same regexes** as the shared register builder (`citations/build_register.py`)
so extraction is consistent, then **diff** against `citations/link_register.json` and emit
**two** artifacts:

1. `new_citations.md` — human report of cites present in this book, absent from the register
   (cases, IRC/USC sections, CFR, Treasury Decisions, constitution + clauses, Acts, EOs,
   forms, secondary), with occurrences, this-book page numbers, and proposed URLs.
2. `new_citations.json` — **parked allowlist** for the HTML build. Schema:

```json
{
  "usc_sections": ["7608","7609","6502", "..."],
  "cases":   [{"cite":"460 F.3d 79","url":"https://www.courtlistener.com/?q=460%20F.3d%2079"}],
  "cfr":     [{"cite":"26 CFR §31.3402", "url":"..."}],
  "acts":    [{"act":"Corporation Excise Tax Act of 1909","url":"..."}],
  "clauses": [{"citation":"Article I, Section 8, Clause 1","url":"..."}],
  "forms":   [{"form":"Form 2555","url":"..."}],
  "treasury_decisions": [], "executive_orders": [], "secondary": []
}
```

**Why the allowlist matters.** The HTML linker links unambiguous inline patterns via
deterministic URLs already (US/F cases, explicit `26 U.S.C. § N`, CFR, Acts, clauses,
amendments, forms). The one gap is **bare IRC section refs** (`§ 7608(a)`, `section 7608`)
— ubiquitous in tax books but ambiguous in general, so they are NOT auto-linked. The HTML
build should link a bare `§/section NNNN` to Cornell Title 26 **only if `NNNN` is in
`new_citations.json.usc_sections`** (∪ the sections already in the shared register). This
"parks" the new cites so the HTML run links exactly the real sections — no false positives.

**Extraction lessons to bake in:**
- **Case-name separator varies by book.** Some books write `Name, 17 U.S. 316` (comma),
  others `Name. 481 U.S. 465` (period). Use `[.,]?` between name and volume or you will
  silently extract **zero** cases.
- Cites may wrap across a line/newline (`713 F.2d\n1423`); `\s+` between reporter and page
  covers it.
- Accept the register's known noise class (a few `"Tax Act"` fragments, old-code `§ 22`) —
  it is a human-vetted diff, not an authority.

### Step 5 — Validate  (see §7 checklist)

### Step 6 — Handoff to the HTML build  (`build_html.py`)

The HTML generator consumes: `<Title>.md`, `citations/link_register.json` (curated URL
overrides), `new_citations.json` (parked allowlist), and the shared
`citations/treasury_decisions.json` sidecar. Book-agnostic requirements it must honour —
these differ from a scanned-book builder and are easy to get wrong:

- **1:1 page mapping** when anchors are PDF sequence (`phys_page(label)=int(label)`); apply
  measured offsets only for printed-folio books.
- **Line-preserving paragraphs:** render intra-block newlines as `<br>` (reflowed prose is
  already one line; ragged lists/statutes keep their breaks). Do **not** space-join all
  lines — that flattens the structure the extractor worked to preserve.
- **Keep the book's own detailed TOC** (it is real content now); do not drop dot-leader
  lines or synthesise a replacement.
- **Protect underscore runs** (`____` signature/form rules) from italic parsing.
- Styled title block; sidebar nav from the `#` section heads; Treasury-Decision links
  resolved live from the sidecar; conflict report for overlapping link rules.

---

## 4. Extractor internals (rule detail)

**Emphasis wrapping.** Merge adjacent same-style spans; push leading/trailing whitespace
**outside** the markers (`_ x _` is invalid MD). A span with **no letters/digits** (lone
punctuation/space) is emitted **neutral** — never wrapped — which kills `_,_`/`_"_` seams
at the source. After a paragraph is assembled, run `tidy_emphasis`: collapse `_( +)_`→`\1`
and `\*\*( +)\*\*`→`\1` (merges runs a wrap/reflow split with a space); **spaces only, not
newlines**, so ragged line breaks survive.

**Prose vs ragged (the reflow discriminator).** Measure each line's right edge `x1` from
its PyMuPDF bbox. `parmax = max(x1)`. A paragraph is **prose** iff
`sum(x1 >= parmax - FILL_BAND for non-final lines) / len(non-final) >= FILL_FRAC`. Prose →
join all lines with single spaces (one line per paragraph, no mid-sentence breaks). Ragged
→ keep `\n` between lines. Indented block-quotes have their own (smaller) `parmax`, so they
still read as prose; enumerations/lists are ragged and stay line-by-line.

**TOC coalescing.** A block with ≥3 lines and ≥2 dotted-leader lines is a Table of
Contents: accumulate title lines, attach the trailing page number inline (keep the dotted
leaders; numbers left-justified in the text flow), and let bold section labels
(`**GENESIS**`) stand on their own line. One entry per line, no rollover.

**De-hyphenation:** OFF by default. Legal text rarely soft-hyphenates; joining
hyphen-split words risks corrupting real compounds (`self-employment`). A line-end hyphen
becomes `word- word` after reflow — accepted.

---

## 5. Parameters & tunables

| Name | Default | Meaning |
|---|---|---|
| `TOP_MARGIN` / `BOT_MARGIN` | 55 / 710 pt | running-head / folio strip zones |
| `HEAD_SIZE` | (11.0, 12.6) | running-head text size range |
| `PARA_GAP` | 24 pt | vertical gap that starts a new paragraph |
| `FILL_BAND` | 25 pt | right-edge tolerance for a "full" (wrapped) line |
| `FILL_FRAC` | 0.6 | share of non-final lines that must be full → prose |
| OCR dpi / colorspace | 300 / GRAY | page render for tesseract |
| OCR invert threshold | mean < 110 | invert dark (white-on-black) artwork |
| tesseract psm | 3 | fully automatic page segmentation |
| bold / italic flag bits | 16 / 2 | `flags & 16` = bold, `flags & 2` = italic |

---

## 6. Locked decisions & conventions

1. **MD now, HTML later** — the MD must stand alone; typeface/layout live in HTML/CSS.
2. **Anchor on PDF sequence**; printed→physical offsets are the HTML build's job.
3. **Strip only publisher chrome** (font-signature test); never touch reproduced documents.
4. **Prose reflows; lists/quotes/statutes keep line breaks** (fill-fraction test).
5. **TOC kept** as one-line entries with dotted leaders + left-justified page numbers.
6. **No de-hyphenation.**
7. **OCR image-only pages inline** (never placeholders); invert dark artwork.
8. **Citations abstracted, new ones parked** as `new_citations.json` for the HTML run.
9. **Copyright:** publish only with the owner's explicit direction.

---

## 7. Validation checklist

**MD:**
- [ ] `<!-- page: N -->` count == PDF page count; N runs 1..pages with no gaps.
- [ ] `# ` section headings == expected `BOOK_HEADS` count, in order.
- [ ] Every `IMAGE_ONLY` page has an OCR block (or a logged low-yield note).
- [ ] Seam scan: `0` occurrences of `_ _` and `** **`; `0` pure-punctuation italics.
- [ ] Spot-check: a prose page (single-line paragraphs), a list page (line breaks kept),
      a TOC page (one entry/line), a reproduced-document page (own headers intact).

**Citations:**
- [ ] Case count > 0 (guards the comma/period separator bug).
- [ ] `new_citations.md` + `new_citations.json` written; allowlist non-empty where expected.

**HTML (downstream):**
- [ ] page back-links == page count; `0` unmapped (or offsets deliberately applied).
- [ ] `<a>` opens == closes; `0` nested anchors; `0` unresolved conflicts (or reported).
- [ ] Prose paragraphs have no `<br>`; ragged blocks retain `<br>`.
- [ ] Bare IRC sections on the allowlist are now linked; off-list numbers stay plain.

---

## 8. Known limitations / gotchas

- **Decorative/dark cover pages** OCR poorly even inverted — accept and log; hand-fix titles.
- **Bare `section N` is ambiguous** — link only via the parked allowlist, never blanket.
- **2-item lists** whose lines happen to be equal-length can misclassify as prose (rare).
- **Tesseract subprocess** must be read as bytes (`errors="replace"`).
- **`brew install`** needs a non-sandboxed shell.
- **Footnote-number italics** (`_16_`) and **form rules** (`____`) are faithful source, not
  defects — leave them; just protect `____` from italic parsing in the HTML build.
```
