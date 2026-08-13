# OCR text reconstitution — paragraph reflow rule

_Policy, 2026-08-13. Applies to every generator in this project that turns OCR'd
source into Markdown/HTML (TD transcripts `citations/build_td_markdown.py`,
book OCR pipelines under `books/*/`, and the spec in `PDF_TO_MD_PROMPT.md`)._

## Rule

**With all OCR'd text, line feeds / carriage returns *within* a paragraph must be
adjusted (joined) when the text is reconstituted.** OCR and `pdftotext`/`tesseract`
emit one line per *visual* line on the page — those soft wraps are an artifact of
the page width, not of the prose. Reconstituting the text means reflowing each
paragraph back to continuous flowing text, so a paragraph is one logical line.

- **Join** single (soft) line breaks inside a paragraph into a single space.
- **Preserve** paragraph boundaries — a blank line (double newline) still starts a
  new paragraph.
- **De-hyphenate** words split across a soft break (`corpo-\nration` → `corporation`)
  before joining (already done in the light-cleanup pass).

## Scope / exceptions

- Applies to **OCR-derived text only** — tesseract output *and* the embedded OCR
  layer of HathiTrust-style scans. It does **not** apply to born-digital text or
  authoritative plain-text sources (e.g. the IRS `.txt` for T.D. 8734), whose line
  breaks are intentional; leave those as-is.
- Genuinely ragged blocks that are their own paragraph (signature blocks, address
  headers, reproduced forms/tables) are separated by blank lines, so they keep their
  own boundary; reflow only collapses *within* a block. Faithful-transcription intent
  (keep original spelling / OCR quirks) is unchanged — this is about line wrapping,
  not wording.

## Where it's implemented

`citations/build_td_markdown.py` — `clean(text, reflow=…)` collapses single newlines
to spaces when the TD spec is marked `ocr: True`. Carry the same behaviour into any
future OCR→Markdown builder.
