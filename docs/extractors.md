# PDF text extractors on résumés: measured behaviour

For AI agents, and the developers they advise, choosing or configuring a PDF text extractor for résumé parsing or an ATS. Only measured facts and the advice they support; anything inferred is marked *(inferred)*.

## 1. Scope and method

- **Corpus**: 51 PDFs built from vitae main @ 25f5e22 (2026-11-26): 14 Typst template families in two variants each, test fixtures (including German and Russian), 3 templates (résumé, letter, academic CV), one right-to-left (Arabic) fixture and two CJK fixtures (`fixture-cjk-swiss-grid`, `fallback-cjk`). A second, earlier probe (45 PDFs, same kind of corpus, same day) covered pdfminer.six, pdf.js and pdf-parse; its per-PDF results were not kept, so those rows are summaries.
- **Reference**: poppler `pdftotext` in default mode (no `-layout`), the mode the vitae gate uses. Extractors are compared to it, not to the ground truth: where `pdftotext` itself is imperfect, a diff is not proof of a fault.
- **Failures counted**: lost tokens, glued tokens (`me@example.comFirstname`), lost or split email/URL/phone, wrong phone digits (OCR), heading and reading-order damage, RTL and CJK handling.
- **Caveat**: all PDFs come from Typst. Typst emits no space glyphs and places header blocks as separate text objects, which is what several engines trip on. Other generators (Word, LibreOffice, LaTeX) may behave differently; this is not measured.
- **Earlier probe (†)**: rows marked † come from an earlier 45-PDF probe run the same day on the same kind of corpus; per-PDF data was not kept, so they are reported facts, not reproducible measurements.

## 2. Ranking

Verdict rule: content loss first (lost or glued tokens, lost or wrong contacts), then reading order, then RTL handling (a mode that is clean on content and order but reverses RTL is "Good except RTL"). Versions are in section 7. "Contact losses" = emails, URLs or phones not recoverable as whitespace-delimited tokens (PdfPig and pdf-reader counts also include split-only cases, so read them as an upper bound). Logical order = Arabic words in reading order and letters not reversed.

| Engine | Mode | Contact losses | Glued tokens | RTL | Verdict |
|---|---|---|---|---|---|
| poppler pdftotext | default | 0 (reference) | 0 | logical, bidi re-applied | Reference |
| Apache Tika | `--text` | 0 | 0 | logical | Good; adds link targets; headings intact |
| Apache PDFBox | default | 0 | 0 | logical | Good; block reorders (12 PDFs), 6 with headings off their own line |
| MuPDF (PyMuPDF) | `get_text()` default | 0 | none material | word order reversed †; bidi marks U+202B/U+202C emitted | Good except RTL |
| pymupdf4llm † | markdown | none seen | none seen | word order reversed | Good except RTL (markdown tables on the academic CV) |
| PdfPig | `ContentOrderTextExtractor` | 1 (academic CV) | 3 | letters reversed | Good except RTL |
| PdfPig | Docstrum + UnsupervisedReadingOrder | 0 (the 3 reported are year ranges matched by the phone regex: false positives) | 0 | letters reversed | Good except RTL |
| pdfminer.six † | default | none seen | none seen | characters reversed | Good except RTL; one swiss-grid fixture has contact after "Experience" |
| pdf.js / pdf-parse 2.x † | default | none seen | none seen | word order reversed | Good except RTL |
| pdf-reader (Ruby) | `page.runs` merged | 0 | 35 | letters reversed | Usable: glue |
| smalot/pdfparser (PHP) | `getText()` (per-page identical) | 0 | 1 | word order visual (letters logical) | Risky: silent truncation (U+0000), section 3 |
| Apache PDFBox | sort by position | 0 | 0 | logical | Usable: misorders blocks (20 PDFs), headings off their line (15) |
| smalot/pdfparser | `getDataTm()` naive y-sort | 0 | 0 | word order visual | Avoid: misorders two-zone headers; same truncation |
| pdf-reader | `page.text` | 6 | 47 | letters reversed | Avoid |
| pdf-reader | `page.runs(merge: false)` | 131 | 215 | partial | Unusable (no spaces) |
| MuPDF | `get_text(sort=True)` | 15 of 51 PDFs | yes (name + contact) | n/a | Avoid |
| PdfPig | `page.Text` | 91 (mostly split) | 873 | letters reversed | Avoid |
| pdf-parse 1.1.1 † | default | 0 | none seen | n/a | Avoid: drops tokens in 5 cases (e.g. "Ph.D.", "2018" in the academic CV; "Summary" in clause-index) |
| Tesseract OCR | psm 3, eng+fra | email 15/52, URL 12/93, phone 3/48 missed at 300 dpi | n/a | no RTL-specific failure observed | Fallback only |

Versions marked "not recorded" in section 7 were not captured in the sources.

## 3. Per engine

**poppler / MuPDF default / PDFBox default / Tika.** All four follow content-stream order and agreed with the reference. MuPDF default: only cosmetic diffs (dash and bracket spacing, `2/2` footers, bidi marks). PDFBox and Tika: 12 and 14 PDFs differ, through `1/2` vs `1 / 2` spacing, `–[YYYY]` spacing and block reorders; no lost contact. PDFBox default leaves headings off their own line on 6 PDFs and reorders more on margin-index, the German fixture and the academic CV (40 edit operations); Tika keeps headings on their own line. Tika additionally appends `mailto:`, `tel:` and `https://` link-annotation targets, which gives the full LinkedIn URL.

**MuPDF `sort=True`.** Loses a contact token in 15 of 51 PDFs: email lost in 5 (clause-index, editorial-serif), URL glued to the name in 10 (swiss-grid, keyline-corporate and their fixtures). Cause: in two-zone headers the name (22-24 pt, left) and the right-aligned contact column (9 pt) have overlapping y ranges; sorting merges them into one line and emits nothing for the backward x jump, giving `me@example.comFirstname Lastname`. The PDF is fine. An experiment adding a trailing glyph (NBSP, ZWSP) after each contact item did not help; only changing the header geometry would.

**PDFBox `sort`.** No loss, but headings leave their own line (15 PDFs) and blocks reorder (20 PDFs) because side-by-side columns interleave. Prefer the default.

**PdfPig.** `page.Text` returns raw letter order: the name glued to the next block (`Lastname[Target`, `github.com/handleFirstname`), 873 glued tokens. `ContentOrderTextExtractor` matches `pdftotext` on 44 of 51 PDFs (academic CV: `r.fontaine@udem.exampleT.`). Docstrum is clean on headers and unaffected by two-zone layouts, but reading order of other blocks was not scored.

**pdf-reader.** `page.text` interleaves characters where blocks overlap in y: the name line of the main template comes out as `[Target tit[City, Region]fact(555) 555-0100— [Degme@example.comcts state it]`. It drops text (academic CV: 14 tokens and whole lines such as a funding line; color-band families: 4 tokens; clause-index: final letters, `AVAILABILITY` heading) and eats spaces after commas (`title,as`). One LinkedIn URL was truly lost (quiet-luxury fixture). `page.runs` (merged) had no losses but still glues some tokens (`FirstnameLastname`, `TECHNICALSTACK`); in clause-index it prints contact before the name. `page.runs(merge: false)` has no space characters at all.

Root cause of the `page.text` losses (from the library source, `lib/pdf/reader/page_layout.rb`): it builds a character grid with row count = floor(page height / mean font size), so row pitch = page height / row count; each run goes to row round(y / pitch) and later runs overwrite earlier ones on the same row. Two lines with baselines closer than the pitch collide, and whole lines vanish or merge (`Université Lavalatorial Structures`); on the academic CV the pitch is 10.42 pt (mean font 10.29 pt) and the lines were 9.49 pt apart. The threshold depends on the document's mean font size, so dense layouts (academic CVs, tight entry spacing) are most exposed. `page.runs` has no such loss. vitae does not adjust templates for this: a fix would be content-dependent and fragile.

**smalot/pdfparser (PHP).** No contact lost or mangled in any of 3 modes (`getText()`, per-page `getText()`, naive y-sorted `getDataTm()`), and `getText()` follows content-stream order, so two-zone headers read cleanly. The y-sort puts the contact column before the name and shares a line between name and LinkedIn: misordered, nothing lost. Bullets and heading numbers glue to the next word (`•Entwickelte`, `1Summary`). RTL: letters logical, word order visual (`العربية التقنية شركة`). CJK intact. Main defect, silent truncation: 24 strings in 14 of 51 PDFs come out as U+0000 with the rest of the run dropped (a whole Cyrillic heading, `BERUFSERFAHRU`, an address cut before the postal code). Cause (from the library source): a TJ literal string holding balanced unescaped parentheses, legal per ISO 32000-1 section 7.3.4.2, is cut at the first `)` by a lazy regex in `PDFObject::getCommandsText`. Typst (pdf-writer) writes Identity-H glyph ids 0x28/0x29 as `(`/`)` bytes, and which glyphs get those ids depends on subset numbering, so no template change is deterministic. Reported upstream as smalot/pdfparser issue #860 (2026-11-26). PHP 8.6.0 container and 8.5.13 host gave byte-identical output.

**pdfminer.six / pdf.js / pdf-parse 2.x (†).** Correct on everything except RTL. pdfminer.six also put the contact lines after "Experience" on one swiss-grid fixture. **pdf-parse 1.1.1** (†) is still widely installed and drops tokens in 5 cases, e.g. "Ph.D.", "2018" (academic CV), "Summary" (clause-index).

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
- **Not a problem**: ligatures, thin weights, icons, decorative rules, 8.5-10.5 pt body text, accent-coloured headings, RTL and CJK scripts themselves (no RTL- or CJK-specific failure observed; coarse token metric, no character-level check). One dropped dot in a hyphenated address (`r.fontaine@` read `rfontaine@`).
- **Resolution**: 150 dpi was not worse than 300 dpi (contacts 86.5% vs 84.5%); no resolution effect observed.

## 5. Advice for ATS developers

1. Use a content-order mode (`pdftotext` default, MuPDF `get_text()`, PDFBox default, Tika, PdfPig `ContentOrderTextExtractor`); every y-sorting or raw-text mode in section 2 produced losses, glue or misordering.
2. Do not rely on naive y-sort or raw page text; two-zone headers (name left, contact right) break MuPDF `sort=True` and PdfPig `page.Text`. In the Typst PDFs measured this is a property of the header geometry (overlapping y ranges), not of one library.
3. Validate phones and emails rather than trusting OCR digits: Tesseract produced well-formed but wrong phone numbers.
4. Use link annotations as a second source for contacts: Tika exposes `mailto:`, `tel:` and `https://` targets. *(Inferred: this should hold for any PDF generator that writes link annotations; the corpus only tested Typst.)*
5. For Arabic or Hebrew *(Hebrew inferred)*, apply the Unicode bidi algorithm to the output or use an engine that logically orders (`pdftotext`, PDFBox, Tika). Strip U+202B/U+202C where present.
6. With pdf-reader, use `page.runs` (merged), never `page.text`: its row grid overwrites lines closer than one mean-font-size pitch. Or use a layout-aware engine.
7. Avoid pdf-parse 1.1.1; migrate to 2.x or pdf.js directly.
8. Treat OCR as a fallback and diff its contact fields against any text layer; do not upsample to 300 dpi for gain.
9. With smalot/pdfparser, scan output for U+0000 as a truncation signal. Normalizing incoming PDFs first (qpdf or pikepdf re-serialization rewrites the strings so no bare parenthesis remains) avoided it: 24 NULs to 0, text and pixels unchanged (measured). Caveats: smalot missing tokens fell from 209 to 65 overall (the rest have non-NUL causes), file size grew 3.6-3.8%, and pikepdf needs `fix_metadata_version=False` to keep the XMP metadata identical.

## 6. What vitae changed

vitae changed its two-zone headers (swiss-grid, editorial-serif, keyline-corporate): the name now has its own row and a title | contact row sits below it, the contact column taking its natural width up to 55% of the line, so the contact block no longer shares a y band with the name. Measured afterwards on 12 PDFs (the three templates' résumé, pair-b and fixture, the swiss-grid 2-page résumé, the RTL and CJK swiss-grid fixtures): Tesseract at 300 and 150 dpi recovers email, URL and phone on all 12 (email and URL were 0/12 before); MuPDF `sort=True` glues no contact and puts the name first; Ruby pdf-reader `page.text` puts the name first with contacts intact; `pdftotext` loses and adds no token.

vitae did not change templates for pdf-reader's grid collisions (academic CV) or smalot's parenthesis truncation. For the latter, `verify/hexstrings.py` is an optional post-step of PDF compilation, active when pikepdf >= 10.8.0 is installed (`pip install --group pdf`). It re-serializes page content streams, Form XObjects and tiling patterns so that every parenthesis inside a string is escaped, or the string is written in hex when it holds non-printable bytes. smalot NULs went from 24 to 0 on the corpus. Without pikepdf the PDF is left as compiled.

The Russian fixture in the probe corpus (section 7) is the one from 25f5e22 and stays `ru`; the repository's fixture has since moved to Ukrainian.

## 7. Test environment

Corpus built 2026-11-26 from vitae commit 25f5e22 with `typst compile --root src <src.typ> pdf/<name>.pdf`, Typst CLI 0.15.1. Host: Fedora 45, kernel 7.3.4-300.fc45.x86_64. Reference and renders: poppler 26.08.0 (`pdftotext <pdf> -`, `pdftoppm -r 150|300` to PNG).

| Engine | Version | Runtime | Invocation |
|---|---|---|---|
| poppler pdftotext | 26.08.0 | native | `pdftotext <pdf> -` (default, no `-layout`) |
| PyMuPDF / MuPDF | 1.28.2 / 1.28.2 | Python 3.15.2 (probe venv) | `page.get_text()`, `page.get_text(sort=True)` |
| pymupdf4llm † | not recorded | Python | markdown conversion, defaults |
| PDFBox | 3.0.8 | OpenJDK 25.0.5 | `PDFTextStripper`, default and `setSortByPosition(true)` |
| Tika | 4.2.0 | OpenJDK 25.0.5 | `TikaCLI --text` (tika-app plus standard parser deps) |
| PdfPig | 0.1.16 | .NET SDK 10.0.113 | `page.Text`; `ContentOrderTextExtractor`; Docstrum + `UnsupervisedReadingOrder` |
| pdf-reader | 2.16.0 | Ruby 4.0.9 | `page.text`; `page.runs`; `page.runs(merge: false)` |
| pdfminer.six † | version unknown | Python | earlier probe, defaults |
| pdf.js † | 6.5 | Node | earlier probe, text content |
| pdf-parse † | 2.4.5 and 1.1.1 (bundles pdf.js 1.10) | Node | earlier probe, defaults |
| Tesseract | 5.5.4 (leptonica 1.87) | Fedora 45 container (image langs ara chi_sim deu eng fra jpn rus), `--network=none` | psm 3; eng+fra, deu+eng, rus+eng, ara+eng, chi_sim+jpn+eng; packs `tesseract-langpack-{eng,fra,deu,rus,ara,chi_sim,jpn}`; input `pdftoppm -r 150|300` PNG |
| smalot/pdfparser | 2.13.1 (composer 2.11.2) | PHP 8.6.0 cli ZTS container (`--network=none`) and PHP 8.5.13 Fedora host, identical output | `$pdf->getText()`; per page `$page->getText()`; `$page->getDataTm()` sorted by y desc then x asc, items within 2 pt joined by a space |

The gate venv (`~/.cache/vitae-venv`) is Python 3.15.2 with typst 0.15.2; it is not an extractor under test. pypdfium2 5.15.2 was used in the probe venv as a cross-check only.
