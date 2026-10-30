# Step 3 — Decide versions

3. **Decide versions.** Default deliverables: a 1-page and a 2-page version per
   language, and both of them **print-safe (light background), which is the
   canonical build and the one that ships** — nobody controls whether the
   recipient prints or photocopies the PDF, so look at the render in grayscale
   too. A screen-first dark build is a *supplement* only, on explicit request
   and for a controlled context (a portfolio page): same source, palette
   toggle, contrast recomputed on the real background, and the fill/separation
   gate stays on the light build because a dark page is all ink
   (`references/design.md` § The destination support). Audience heuristic (North-American markets): 1-page for startups,
   walk-ins and spontaneous applications; 2-pages for established companies and
   consulting firms. **A stricter regional norm from step 2 always wins** (e.g.
   France: 1 page; UK: 1 page early-career). When the regional standard asks
   for more pages than the honest content fills, scale typography and margins
   up rather than inventing content, and say so in your final message.
   Versions are living: if the same posting type blocks two or more reviewed
   applications on framing alone (title, ordering) — not a one-off — build
   that dedicated variant once instead of prescribing repeated manual
   retailoring. Keep ONE canonical source tree; delivered copies are
   regenerated from it (companion-guide.md, Delivery package) — a
   hand-maintained working copy plus a hand-maintained delivery copy WILL
   drift.
   **A cover letter follows the identical doctrine — one per posting, never a
   generic one.** The gabarit (`templates/letter.typ`, importing `lib.typ`
   exactly like the CV) lives in the canonical tree; what ships is one
   instance per posting, in that posting's delivery folder next to the
   `cv.typ` targeted for the same posting, with the CV's accent, font and
   name/contact line copied in — never re-derived. Three paragraphs: (1) why
   this employer specifically, not a line that would survive being
   copy-pasted onto another posting; (2) the two or three proofs from
   `FAITS.md` that answer the requirements the posting actually names; (3)
   availability and a close. Rule 1 applies with no exception: nothing in the
   letter that is not already in `FAITS.md`. Gate it with `python3
   scripts/verify_letter.py letter.typ EMPLOYER "JOB TITLE"` — one page, and
   the employer and exact job title both present in the extracted text; it
   shares none of `verify.py`'s fill/separation/ink thresholds, which are
   calibrated for a CV's density and mean nothing on prose.
   **The target language governs the WHOLE package, not just the CV.** The
   companion guide, the read-me, every requested format (the .docx included),
   and the folder and file NAMES are in the candidate's language. No language
   suffix when only one language ships — `guide.pdf`, not `guide-ar.pdf`: the
   recipient has no reason to see the production machinery. Harvested from
   four consecutive corrections in one session (2026-08-27: « le guide qu'on
   lui envoie devrait être en arabe seulement », « mets les titres de dossier,
   le lisez-moi et tout en arabe aussi », « Pas guide-ar, juste guide », « T'as
   fait de CV sur format Word en Arabe »). A polished CV inside a French-named
   folder with a French read-me is unusable without an intermediary, and it
   advertises that the document is tool output in translation. For a
   right-to-left language this also covers the read-me's own text direction.
