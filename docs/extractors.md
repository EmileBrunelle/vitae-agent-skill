# PDF text extractors on résumés: measured behaviour

For AI agents, and the developers they advise, choosing or configuring a PDF text extractor for résumé parsing or an ATS. Only measured facts and the advice they support; anything inferred is marked *(inferred)*.

## 1. Scope and method

- **Corpus**: 51 PDFs built from vitae main @ 25f5e22 (2026-11-26): 14 Typst template families in two variants each, test fixtures (including German and Russian), 3 templates (résumé, letter, academic CV), one right-to-left (Arabic) and one CJK fixture. A second, earlier probe (45 PDFs, same kind of corpus, same day) covered pdfminer.six, pdf.js and pdf-parse; its per-PDF results were not kept, so those rows are summaries.
- **Reference**: poppler `pdftotext` in default mode (no `-layout`), the mode the vitae gate uses. Extractors are compared to it, not to the ground truth: where `pdftotext` itself is imperfect, a diff is not proof of a fault.
- **Failures counted**: lost tokens, glued tokens (`me@example.comFirstname`), lost or split email/URL/phone, wrong phone digits (OCR), heading and reading-order damage, RTL and CJK handling.
- **Caveat**: all PDFs come from Typst. Typst emits no space glyphs and places header blocks as separate text objects, which is what several engines trip on. Other generators (Word, LibreOffice, LaTeX) may behave differently; this is not measured.

## 2. Ranking

"Contact losses" = emails, URLs or phones not recoverable as whitespace-delimited tokens (PdfPig and pdf-reader counts also include split-only cases, so read them as an upper bound). Logical order = Arabic words in reading order and letters not reversed.

| Engine | Version | Mode | Contact losses | Glued tokens | RTL | Verdict |
|---|---|---|---|---|---|---|
| poppler pdftotext | reference | default | 0 (reference) | 0 | logical, bidi re-applied | Reference |
| MuPDF (PyMuPDF) | 1.28.2 | `get_text()` default | 0 | none material | order reversed; bidi marks U+202B/U+202C emitted | Good |
| MuPDF | 1.28.2 | `get_text(sort=True)` | 15 of 51 PDFs | yes (name + contact) | n/a | Avoid |
| pymupdf4llm | not recorded | markdown | none seen | none seen | order reversed | Good (markdown tables on the academic CV) |
| Apache PDFBox | 3.0.8 | default | 0 | 0 | logical | Good |
| PDFBox | 3.0.8 | sort by position | 0 | 0 | logical | Usable, reorders blocks on 20 PDFs |
| Apache Tika | 4.2.0 | `--text` | 0 | 0 | logical | Good; adds link targets |
| PdfPig | 0.1.16 | `ContentOrderTextExtractor` | 1 (academic CV) | 3 | letters reversed | Good |
| PdfPig | 0.1.16 | Docstrum + UnsupervisedReadingOrder | 3 (year ranges read as phones, noise) | 0 | letters reversed | Usable |
| PdfPig | 0.1.16 | `page.Text` | 91 (mostly split) | 873 | letters reversed | Avoid |
| pdf-reader (Ruby) | 2.16.0 | `page.runs` merged | 0 | 35 | letters reversed | Usable |
| pdf-reader | 2.16.0 | `page.text` | 6 | 47 | letters reversed | Avoid |
| pdf-reader | 2.16.0 | `page.runs(merge: false)` | 131 | 215 | partial | Unusable (no spaces) |
| pdfminer.six | not recorded | default | none seen | none seen | characters reversed | Good except RTL |
| pdf.js / pdf-parse (Node) | 6.5 / 2.4.5 | default | none seen | none seen | word order reversed | Good except RTL |
| pdf-parse | 1.1.1 (bundles pdf.js 1.10) | default | 0 | none seen | n/a | Avoid: drops tokens in 5 cases |
| Tesseract OCR | 5.5.4 | psm 3, eng+fra | email 15/52, URL 12/93, phone 3/48 missed at 300 dpi | n/a | not RTL-specific | Fallback only |

Versions marked "not recorded" were not captured in the sources. Full environment in section 7.

## 3. Per engine

**poppler / MuPDF default / PDFBox default / Tika.** All four follow content-stream order and agreed with the reference. MuPDF default: only cosmetic diffs (dash and bracket spacing, `2/2` footers, bidi marks). PDFBox and Tika: 12 and 14 PDFs differ, only through `1/2` vs `1 / 2` spacing, `–[YYYY]` spacing and small block reorders; no lost contact. Tika additionally appends `mailto:`, `tel:` and `https://` link-annotation targets, which gives the full LinkedIn URL.

**MuPDF `sort=True`.** Loses a contact token in 15 of 51 PDFs: email lost in 5 (clause-index, editorial-serif), URL glued to the name in 10 (swiss-grid, keyline-corporate and their fixtures). Cause: in two-zone headers the name (22-24 pt, left) and the right-aligned contact column (9 pt) have overlapping y ranges; sorting merges them into one line and emits nothing for the backward x jump, giving `me@example.comFirstname Lastname`. The PDF is fine. An experiment adding a trailing glyph (NBSP, ZWSP) after each contact item did not help; only changing the header geometry would.

**PDFBox `sort`.** No loss, but headings leave their own line (15 PDFs) and blocks reorder (20 PDFs) because side-by-side columns interleave. Prefer the default.

**PdfPig.** `page.Text` returns raw letter order: the name glued to the next block (`Lastname[Target`, `github.com/handleFirstname`), 873 glued tokens. `ContentOrderTextExtractor` matches `pdftotext` on 44 of 51 PDFs (academic CV: `r.fontaine@udem.exampleT.`). Docstrum is clean on headers and unaffected by two-zone layouts, but reading order of other blocks was not scored.

**pdf-reader.** `page.text` interleaves characters where blocks overlap in y: the name line of the main template comes out as `[Target tit[City, Region]fact(555) 555-0100— [Degme@example.comcts state it]`. It drops text (academic CV: 14 tokens and whole lines such as a funding line; color-band families: 4 tokens; clause-index: final letters, `AVAILABILITY` heading) and eats spaces after commas (`title,as`). One LinkedIn URL was truly lost (quiet-luxury fixture). `page.runs` (merged) had no losses but still glues some tokens (`FirstnameLastname`, `TECHNICALSTACK`); in clause-index it prints contact before the name. `page.runs(merge: false)` has no space characters at all.

Root cause of the `page.text` losses (from the library source, `lib/pdf/reader/page_layout.rb`): it builds a character grid with row count = floor(page height / mean font size), so row pitch = page height / row count; each run goes to row round(y / pitch) and later runs overwrite earlier ones on the same row. Two lines with baselines closer than the pitch collide, and whole lines vanish or merge (`Université Lavalatorial Structures`); on the academic CV the pitch is 10.42 pt (mean font 10.29 pt) and the lines were 9.49 pt apart. The threshold depends on the document's mean font size, so dense layouts (academic CVs, tight entry spacing) are most exposed. `page.runs` has no such loss. vitae does not adjust templates for this: a fix would be content-dependent and fragile.

**pdfminer.six / pdf.js / pdf-parse 2.x.** Correct on everything except RTL. pdfminer.six also put the contact lines after "Experience" on one swiss-grid fixture. **pdf-parse 1.1.1** is still widely installed and drops tokens: "Ph.D." and "2018" in the academic CV, "Summary" in clause-index.

**RTL.** Typst and LibreOffice store Arabic glyphs in visual order (the rule in `references/ats.md`). Only `pdftotext` re-applies bidi among the engines of the earlier probe; this probe adds that PDFBox and Tika return logical order. MuPDF and pdf.js reverse word order, pdfminer.six reverses characters, pdf-reader and PdfPig return reversed letters (0 of 5 Arabic tokens match the reference). CJK survived in all engines tested (MuPDF, PdfPig, pdf-reader, PDFBox, Tika; character counts equal the reference).

## 4. OCR fallback (Tesseract 5.5.4)

Run offline, psm 3, 54 pages at 150 and 300 dpi; languages eng+fra, deu, rus, ara, chi_sim+jpn.

| | 300 dpi | 150 dpi |
|---|---|---|
| word recall, median / min | 0.996 / 0.970 | 0.996 / 0.978 |
| emails recovered | 37/52 | 40/52 |
| URLs recovered | 81/93 | 81/93 |
| phones recovered | 45/48 | 46/48 |
| section headings | 162/166 | 163/166 |

- **Body text is not the problem** (recall at least 0.97 everywhere); the loss sits in the contact block.
- **Fails**: (1) a small grey right-aligned contact column whose lines share a y band with a 24 pt name (swiss-grid, keyline-corporate, editorial-serif): lines merge into the name line, email and LinkedIn are lost in 12 of 12 PDFs; the same column cropped alone is read exactly, so the cause is line segmentation. (2) Small muted digits beside a large bold name (clause-index): the phone is *wrong, not absent* (`(558) 955-0100`, `(ss) 285-0100`), which an ATS would index. (3) White-on-dark labels and monograms (hard-edge): headings 6/9 at 300 dpi, `PROFILE` missing.
- **Not a problem**: ligatures, thin weights, icons, decorative rules, 8.5-10.5 pt body text, accent-coloured headings, RTL and CJK scripts themselves. One dropped dot in a hyphenated address (`r.fontaine@` read `rfontaine@`).
- **Resolution**: 150 dpi was not worse than 300 dpi (contacts 86.5% vs 84.5%); no resolution effect observed.

## 5. Advice for ATS developers

1. Use a content-order mode (`pdftotext` default, MuPDF `get_text()`, PDFBox default, Tika, PdfPig `ContentOrderTextExtractor`); every y-sorting or raw-text mode in section 2 produced losses or glue.
2. Do not rely on naive y-sort or raw page text; two-zone headers (name left, contact right) break MuPDF `sort=True` and PdfPig `page.Text`. This is a property of the geometry, not of Typst.
3. Validate phones and emails rather than trusting OCR digits: Tesseract produced well-formed but wrong phone numbers.
4. Use link annotations as a second source for contacts: Tika exposes `mailto:`, `tel:` and `https://` targets. *(Inferred: this should hold for any PDF generator that writes link annotations; the corpus only tested Typst.)*
5. For Arabic or Hebrew *(Hebrew inferred)*, apply the Unicode bidi algorithm to the output or use an engine that logically orders (`pdftotext`, PDFBox, Tika). Strip U+202B/U+202C where present.
6. With pdf-reader, use `page.runs` (merged), never `page.text`: its row grid overwrites lines closer than one mean-font-size pitch. Or use a layout-aware engine.
7. Avoid pdf-parse 1.1.1; migrate to 2.x or pdf.js directly.
8. Treat OCR as a fallback and diff its contact fields against any text layer; do not upsample to 300 dpi for gain.

## 6. Template changes

vitae templates are being adjusted where a measured failure has a layout cause (two-zone headers); this document describes the engines as measured on the pre-adjustment corpus.

## 7. Test environment

Corpus built 2026-11-26 from vitae commit 25f5e22 with `typst compile --root src <src.typ> pdf/<name>.pdf`, Typst CLI 0.15.1. Host: Fedora 45, kernel 7.3.4-300.fc45.x86_64. Reference and renders: poppler 26.08.0 (`pdftotext <pdf> -`, `pdftoppm -r 150|300` to PNG).

| Engine | Version | Runtime | Invocation |
|---|---|---|---|
| poppler pdftotext | 26.08.0 | native | `pdftotext <pdf> -` (default, no `-layout`) |
| PyMuPDF / MuPDF | 1.28.2 / 1.28.2 | Python 3.15.2 (probe venv) | `page.get_text()`, `page.get_text(sort=True)` |
| pymupdf4llm | not recorded | Python | markdown conversion, defaults |
| PDFBox | 3.0.8 | OpenJDK 25.0.5 | `PDFTextStripper`, default and `setSortByPosition(true)` |
| Tika | 4.2.0 | OpenJDK 25.0.5 | `TikaCLI --text` (tika-app plus standard parser deps) |
| PdfPig | 0.1.16 | .NET SDK 10.0.113 | `page.Text`; `ContentOrderTextExtractor`; Docstrum + `UnsupervisedReadingOrder` |
| pdf-reader | 2.16.0 | Ruby 4.0.9 | `page.text`; `page.runs`; `page.runs(merge: false)` |
| pdfminer.six | version unknown | Python | earlier probe, defaults |
| pdf.js | 6.5 | Node | earlier probe, text content |
| pdf-parse | 2.4.5 and 1.1.1 (bundles pdf.js 1.10) | Node | earlier probe, defaults |
| Tesseract | 5.5.4 (leptonica 1.87) | Fedora (latest at build) container, `--network=none` | psm 3; eng+fra, deu+eng, rus+eng, ara+eng, chi_sim+jpn+eng; packs `tesseract-langpack-{eng,fra,deu,rus,ara,chi_sim,jpn}`; input `pdftoppm -r 150|300` PNG |
| PHP smalot/pdfparser | pending | pending | probe not finished when this was written |

The gate venv (`~/.cache/vitae-venv`) is Python 3.15.2 with typst 0.15.2; it is not an extractor under test. pypdfium2 5.15.2 was used in the probe venv as a cross-check only.
