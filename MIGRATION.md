# Migration plan — multi-book layout with a shared citation library

_Planned 2026-08-11._

## Status — RELOCATE + RETARGET pass DONE (2026-08-11)
Executed the structural reorg and path retargeting only:
- `book/` → `books/income-tax-shattering-the-myths/`; `American_Tax_Bible_book/book/` →
  `books/american-tax-bible/` (with `new_citations.md` pulled into the book dir);
  cross-book artifacts → `comparisons/`; `PDF_TO_MD_PROMPT.md` → `docs/`.
- All builder paths retargeted; all three pipelines (book #1 register+edition, book #2
  citation-diff+edition) rebuild clean from their new homes.
- Old `/book/` and `/book/link_register.html` kept as meta-refresh **redirect stubs**.
- **Not created this pass** (deliberate, low-risk): `site/` (root landing files stay at
  root so their live URLs don't break) and `shared/` (edition-builder unification deferred).

**Still DEFERRED (follow-up):**
- §2 unify book #1 & #2 `build_html.py` into one `shared/build_edition.py` (config-driven).
- §3 make `citations/build_register.py` multi-book / merged with `by_book` provenance
  (book #2 still uses its own `build_new_citations.py` diff in the meantime).
- **Case-linker compliance** with `citations/CITATION_LINKING.md`: make `build_html.py`
  wrap the full `case_name + cite` span (from `link_register.json`'s `full_citation`),
  not just the bare reporter cite. Do it once in the shared/edition builder. The policy
  is written; the linkers are not yet compliant (case name currently sits outside `<a>`).

**RESOLVED — repo file size / Git LFS (2026-08-12):** **LFS rejected.** GitHub Pages
does not resolve LFS objects — it serves the ~130-byte pointer stub, not the file — so
moving the PDFs to LFS would break every *served* PDF: Book #1's `PDF p.N` page
back-links and the local Treasury-Decision PDFs under `citations/treasury_decisions/`.
LFS also only reclaims history via a disruptive `git lfs migrate` history rewrite
(force-push, all later SHAs change), and adds a client dependency (`git lfs install`)
plus a separate metered bandwidth quota. **Decision: keep committing the PDFs as-is.**
Each PDF is stored once (verified: 1 blob apiece, ~37 MB total; whole `.git` ~45 MB);
`git mv`/renames are free — only *replacing a PDF's content* bloats history permanently.
If repo size ever becomes a real problem, host the PDFs **outside git** (a GitHub
**Release** asset or a bucket/CDN) and point the links at absolute URLs — do **not** use
LFS for anything Pages must serve.

_Original decisions (locked with the owner):_
1. **Full rename** of book #1 into `books/<slug>/` (accepts breaking the live `/book/` URL — mitigated by a redirect stub, step 6). ✅ done
2. **One merged register** across all books (per-entry book provenance). ⏳ deferred
3. Reorg executed in a **later** pass; this document is the checklist. ✅ relocate pass done

---

## Target layout

```
dave_champion/
├─ books/
│  ├─ income-tax-shattering-the-myths/       # was book/  (Dave Champion)
│  │  ├─ index.html                # generated edition (Pages serves this) — clean URL /books/<slug>/
│  │  ├─ <book>.html               # same content, long filename
│  │  ├─ <book>.pdf                # source PDF (served; page back-links resolve against it)
│  │  └─ src/                      # inputs + book-specific scripts (NOT served)
│  │     ├─ clean.py, proofread.py, proofread_chunks/, proofread_*.json
│  │     ├─ <book>.md              # cleaned+proofread build input
│  │     ├─ <book>.raw-ocr.md, <book>.pre-proofread.md
│  │     └─ pdf_reference.txt, cleanup_report.txt, citation_conflicts.txt
│  └─ american-tax-bible/                     # was American_Tax_Bible_book/book/  (Thomas Freed)
│     ├─ index.html / <book>.html / <book>.pdf   (once built)
│     └─ src/  (extract_md.py, .venv, <book>.md, intermediates)
├─ citations/                       # SHARED citation library (code + assets + MERGED output)
│  ├─ build_register.py             # takes a BOOKS list as input (see §3)
│  ├─ build_register_html.py
│  ├─ link_register.{json,md,html}  # merged across all books
│  ├─ treasury_decisions.json       # sidecar (num → canonical URL)
│  └─ treasury_decisions/td_<num>/*.pdf   # shared local source docs
├─ shared/                          # book-agnostic generators, parametrized by book path
│  └─ build_edition.py              # was book/build_html.py
├─ site/                            # GitHub Pages landing (root URL)
│  ├─ index.html, whiteboard_income_tax.html, dry_fasting_summary.css
├─ WAYPOINT.md, MIGRATION.md
└─ (sibling repo, unchanged) ../transcription-agent/TREASURY_DECISIONS.md
```

**Why `index.html` at the book root (no `dist/`):** keeps the clean URL
`/dave_champion/books/<slug>/`. The source PDF must be servable anyway (back-links),
so it lives at the served level; everything not served goes in `src/`.
_Alternative considered: a `dist/` subdir — rejected because it makes the URL
`/books/<slug>/dist/`._

---

## 1. File moves (git mv — preserve history)

**Book #1** (`book/` → `books/income-tax-shattering-the-myths/`):
| From | To |
|---|---|
| `book/Book - …Myths.md` | `books/income-tax-shattering-the-myths/src/Book - …Myths.md` |
| `book/Book - …Myths.raw-ocr.md` | `…/src/` |
| `book/Book - …Myths.pre-proofread.md` | `…/src/` |
| `book/Book - …Myths.pdf` | `books/income-tax-shattering-the-myths/Book - …Myths.pdf` (served) |
| `book/Book - …Myths.html`, `book/index.html` | `books/income-tax-shattering-the-myths/` (served) |
| `book/clean.py`, `book/proofread.py` | `…/src/` |
| `book/proofread_chunks/`, `proofread_*.json`, `pdf_reference.txt`, `cleanup_report.txt`, `citation_conflicts.txt` | `…/src/` |
| `book/build_html.py` | `shared/build_edition.py` (generalized — §2) |
| `book/.gitignore` | fold into root/book-level gitignore (§5) |

**Book #2** (`American_Tax_Bible_book/book/` → `books/american-tax-bible/`):
| From | To |
|---|---|
| `American_Tax_Bible_book/book/extract_md.py` | `books/american-tax-bible/src/extract_md.py` |
| `American_Tax_Bible_book/book/American Tax Bible.pdf` | `books/american-tax-bible/American Tax Bible.pdf` |
| `American_Tax_Bible_book/book/.venv`, `.claude/` | `books/american-tax-bible/src/` (venv is gitignored) |
| remove empty `American_Tax_Bible_book/` afterward | — |

**Landing site** → `site/`: `index.html`, `whiteboard_income_tax.html`, `dry_fasting_summary.css`.
_(`Tax_acts_compared.xlsx` — decide: `site/` asset, a book `src/`, or leave at root. Currently untracked.)_

**`citations/` stays put** — already the shared library.

---

## 2. `shared/build_edition.py` (was `book/build_html.py`) — generalize

Currently hardcodes book #1 paths and is run from `book/`. Change to **take a book
directory as input** (CLI arg or a small per-book `book.toml`/`book.json` config) and
run from repo root.

Path changes (old cwd `book/` → new: run from repo root with `BOOK=books/<slug>`):
| Ref (today) | New |
|---|---|
| `MD  = "Book - …md"` | `f"{BOOK}/src/Book - …md"` |
| `OUT = "Book - …html"`, `index.html` | `f"{BOOK}/…"` |
| `PDF = "Book - …pdf"` (+ `PDF_HREF`) | `f"{BOOK}/…"` (href stays relative to the served page) |
| `TD_FILE = "../../transcription-agent/TREASURY_DECISIONS.md"` | `"../transcription-agent/TREASURY_DECISIONS.md"` (root-relative) |
| reads `../citations/link_register.json` | `"citations/link_register.json"` |
| writes `../citations/treasury_decisions.json` | `"citations/treasury_decisions.json"` |
| sidebar link `../citations/link_register.html` | **relative to served page**: `../../citations/link_register.html` |
| runtime `fetch('../citations/treasury_decisions.json')` | `fetch('../../citations/treasury_decisions.json')` |

⚠ **Two different "relative" bases** — don't conflate:
- **Build-time file reads/writes** are relative to the **cwd (repo root)** → `citations/…`.
- **Links inside the generated HTML** are relative to the **served page**
  (`books/<slug>/index.html`) → `../../citations/…`. Book depth changed from 1 to 2, so
  every in-HTML `../citations/` becomes `../../citations/`.

Per-book front-matter that must become config (not hardcoded): title, byline, source
PDF filename, and the page-offset constants `PAGE_OFFSET_ARABIC=23` / `PAGE_OFFSET_ROMAN=11`
(book-specific — book #2 will differ).

---

## 3. `citations/build_register.py` — make it multi-book (MERGED register)

Today it reads ONE MD (`../book/…md`) from cwd `citations/`. Redesign:

- **Input:** a list of books, e.g. `BOOKS = [("income-tax-shattering-the-myths", ".../src/…md"), ("american-tax-bible", ".../src/…md")]` (or discover `books/*/src/*.md`). Run from repo root or from `citations/` — pick one and make all paths match.
- **Accumulation:** scan each book, tag every hit with its book slug. Each register
  entry gains **per-book provenance** instead of a single `occurrences`/`pages`:
  ```json
  { "cite": "…", "url": "…",
    "occurrences": 11,                     // aggregate across books
    "by_book": { "income-tax-shattering-the-myths": {"occurrences": 6, "pages": ["172","197"]},
                 "american-tax-bible":              {"occurrences": 5, "pages": ["88"]} } }
  ```
- **Shared assets unchanged:** `treasury_decisions/td_<num>/*.pdf` local-doc scan and the
  T.D. 2815→2816 caveat stay global (a document is a document regardless of which book cites it).
- **Path updates:** `TD_FILE` → `../transcription-agent/…` (if run from root) and drop the
  `../book/` MD hardcode in favor of the BOOKS list.

`build_register_html.py`: add a **"Cited in" column / book badges** per entry (render the
`by_book` keys). Local-first dual-link + notes logic is unchanged.

**Book #2 "new cites" workflow** (from WAYPOINT): once book #2's MD exists, a merged run
surfaces which cites are new (present in `by_book` for `american-tax-bible` only) — that
replaces the "local list of new cites" idea; the merge *is* the fold-in.

---

## 4. New build order (multi-book)

```
# per book, as needed:
books/<slug>/src/clean.py            # (book #1 only — OCR)
books/<slug>/src/proofread.py …      # (book #1 only)
books/<slug>/src/extract_md.py       # (book #2 — font-aware extraction)

# shared, after all book MDs exist:
citations/build_register.py          # merged register over ALL books
citations/build_register_html.py
shared/build_edition.py books/<slug> # once per book
```

---

## 5. `.gitignore` consolidation

- Root `.gitignore` already ignores `*.css` (with a `!dry_fasting_summary.css` exception) —
  that exception path moves to `site/dry_fasting_summary.css`; update it.
- `book/.gitignore` rules (`*.pdf` except the source PDF, `*.raw-ocr.md`, `proofread_chunks/`,
  `__pycache__/`, etc.) should move to a **per-book** `.gitignore` template under
  `books/<slug>/` (or a root rule scoped to `books/**`).
- Ignore `books/*/src/.venv/`.
- **File-size / Git LFS: RESOLVED** — keep committing the PDFs; LFS rejected because
  Pages won't serve LFS-tracked files (see the "RESOLVED" note near the top of this doc).

---

## 6. GitHub Pages — mitigate the broken `/book/` URL

Renaming changes the published edition URL:
`…/dave_champion/book/` → `…/dave_champion/books/income-tax-shattering-the-myths/`.

- **Redirect stub:** keep a tiny `book/index.html` (meta-refresh + canonical link) pointing
  at the new path so existing links / the published register link don't 404. This is the
  ONE thing intentionally left at the old path.
- Update the register's "← Back to the interactive edition" href and the book's
  "Link register →" href to the new depths (§2).
- Update WAYPOINT's published URLs.

---

## 7. Verify (after execution)

- `git status` shows only intended renames (history preserved via `git mv`).
- Rebuild all three stages; 0 errors.
- Book #1 edition: inline citation links, `PDF p.N` back-links, TD `fetch()`, and
  "Link register →" all resolve at the new depth (test over HTTP, not `file://`).
- Register HTML: local-first TD links + 2815 note intact; new "Cited in" column renders.
- Old `/book/` redirect resolves to the new URL.

---

## Execution order (low-risk sequence)

1. Create `books/`, `shared/`, `site/` dirs.
2. `git mv` book #1 into `books/<slug>/` (+ `src/` split); `git mv` book #2; move landing → `site/`.
3. `git mv book/build_html.py shared/build_edition.py`; generalize (§2).
4. Update `citations/build_register.py` + `build_register_html.py` (§3).
5. Update `.gitignore`s (§5); add `book/index.html` redirect stub (§6).
6. Rebuild (§4) + verify (§7).
7. One reviewed commit; then reconfigure/redeploy Pages and confirm the live URL + redirect.
