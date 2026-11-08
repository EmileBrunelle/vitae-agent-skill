# Regional and language conventions — router

Apply the conventions of the market being applied to, not the user's locale. When the region is ambiguous, ask. Send the version in the language *and spelling variant* of the job posting.

**Load only what you need:** this file gives the file list and the universal rules; each market file opens with an "At a glance" (except the add-on files [`quebec.md`](regional/quebec.md), [`quebec-outbound.md`](regional/quebec-outbound.md), [`europe-to-north-america.md`](regional/europe-to-north-america.md) and [`india-outbound.md`](regional/india-outbound.md)) (paper, photo, CV language, personal data, verb style, length) and carries the depth; the per-market depth lives in `regional/<market>.md` — read ONLY the file for the target market:

- [`regional/north-america.md`](regional/north-america.md) — Canada, Québec, USA (us-letter; EN, FR-QC; no photo/age; length 1-2 p.)
- [`regional/quebec.md`](regional/quebec.md) — Québec only, read IN ADDITION to [`north-america.md`](regional/north-america.md): only when the TARGET market is Québec (a Québec employer or posting; a Québec address alone does not make it the target)
- [`regional/quebec-outbound.md`](regional/quebec-outbound.md) — read IN ADDITION to the target market's file when the candidate holds Québec credentials (DEC, AEC, DEP, Québec university degree, Québec order membership) and targets ANY market other than Québec
- [`regional/europe-to-north-america.md`](regional/europe-to-north-america.md) — read IN ADDITION to [`north-america.md`](regional/north-america.md) when the TARGET market is USA, Canada or Québec and the candidate's credentials or CV habits are European (the target market wins over the address)
- [`regional/india-outbound.md`](regional/india-outbound.md) — read IN ADDITION to the target market's file when the candidate holds Indian credentials or Indian CV habits (3-year bachelor's, ICAI, NBA, ECA, ACS) and targets USA, Canada, UK, Ireland, Australia or NZ
- [`regional/france.md`](regional/france.md) — France (a4; FR; photo declining; 1 p.)
- [`regional/uk-ireland.md`](regional/uk-ireland.md) — UK, Ireland (British spelling; no photo)
- [`regional/dach.md`](regional/dach.md) — Germany, Austria, Switzerland (Lebenslauf, photo and Zeugnisse customs)
- [`regional/australia-nz.md`](regional/australia-nz.md) — Australia, New Zealand (one file, two *non-interchangeable* markets — a4; no photo; work rights, APS, engineer registration)
- [`regional/spain.md`](regional/spain.md) — Spain only, never Latin America (a4; no consent clause, títulos oficiales vs propios, convocatorias)
- [`regional/india.md`](regional/india.md) — India (a4; resume vs biodata, CA/architect titles, CTC, campus and PSU hiring)
- [`regional/brazil-latam.md`](regional/brazil-latam.md) — Brazil, Mexico, Argentina, Chile, Colombia (one file, *non-interchangeable* markets — read the country section; Gupy ATS, CREA/CRC titles)
- [`regional/southeast-asia.md`](regional/southeast-asia.md) — Indonesia, Malaysia, Singapore, Philippines, Vietnam, Thailand (one file, six *non-interchangeable* markets — read the country section, never the file average)
- [`regional/maghreb.md`](regional/maghreb.md) — Morocco, Algeria, Tunisia (one file, three *non-interchangeable* markets — same warning)

**If the target market has no file, do not infer from training data** — markets outside this set (Middle East, East Asia…) do not form a bloc: conventions vary more inside that group than between Europe and North America (Japan's rirekisho is a rigid form with photo and age; China expects photos for domestic employers but not multinationals). Verify with a current local source or ask, label the assumption in the deliverable — and consider contributing the file. The same warning applies *inside* a multi-market file: Singapore and Thailand share one and disagree on nearly every axis (photo, personal data, formality).

Cautions the market files compress: **us-letter is firm only in North America and Philippines print; Mexico, Chile and Colombia are LOW confidence** (see [`regional/brazil-latam.md`](regional/brazil-latam.md)); **a national ID number never belongs on a CV in any market listed**; a **Thai** document's Buddhist-Era year (B.E. = CE + 543) must be converted before it reaches a foreign reader; and where a photo is expected, the DACH mechanics apply (formal, front-facing, plain background) — Indonesia and the Philippines additionally fix a print size.

## Universal rules (every market)

- In every tense-based convention, the **current role is written in the present tense**, finished roles in the convention's past form.
- Anti-discrimination norms shift everywhere toward *no photo, no personal data* on the CV; when in doubt, omit and tell the user the local custom. **The CV photo rule never applies to LinkedIn** — a profile photo is expected on LinkedIn in every market.
- Employment gaps: present honestly — real month+year dates, no camouflage via year-only ranges; a short neutral mention beats an unexplained hole, and the candidate decides the wording.
- Hobbies/interests: personality signal in France/Germany, filler in the US/UK unless directly relevant — see the market file.
- **Protected titles exist in many fields and jurisdictions** (health, law, finance, engineering…). The market files give known cases; the list is never exhaustive — check the target country's professional regulator for any regulated-sounding field. Rule of thumb everywhere: header title = unregulated role name + degree in parentheses; the degree carries the professional signal legally.
- **Gloss local institutions and diplomas** for foreign readers: keep the original name + a short gloss rather than a lossy translation. The gloss may only restate what the fact sheet says; any explanation of your own ("two-year pre-university program") is an addition — flag it to the user for approval, never print it unapproved (SKILL.md: page text is facts only).
- **Translation is adaptation, not word-mapping.** Watch for calques (FR→EN "within a team" → "on a team"); include a native-reviewer pass in the adversarial loop for any translated version.
- Set `lang:` on `#set text(...)` per document — it drives hyphenation and smart-quote behavior.
- **The target market caps the visual audacity dial, never raises it.** A conservative target market forces `sober` ([`references/design/core.md`](design/core.md) § colour; `scripts/pick_design.py --conservative`), whatever the candidate's field or the design family. Whether a market is conservative for this purpose is established the same way as everything else in this file — the market's own file, current sources, or the user — never assumed from training data, and the assumption gets labelled in the deliverable when it cannot be verified. A market may also cap it *below* the candidate's request; the dial is only ever raised by the explicit request of the candidate or user.

## Section names per language

| | FR | EN |
|---|---|---|
| Profile | Profil | Profile / Summary |
| Experience (target field) | Expérience en (domaine) | (Field) Experience |
| Other experience | Autre expérience professionnelle | Other Professional Experience |
| Education | Formation | Education |
| Skills | Compétences techniques | Technical Skills / Skills |
| Soft skills | Compétences générales | Core Strengths |
| Languages | Langues | Languages |

Derive the target-field section name with the same pattern for any field ("Expérience en soins infirmiers", "Nursing Experience"). Keep names close to conventional stems — a qualifier after a conventional stem is safe; fully exotic names risk ATS misclassification.

**Accepted variants** (the lexical skeleton is part of the anti-clone system — [`references/design/core.md`](design/core.md) § Section labels; each design family carries its own defaults and `scripts/pick_design.py` draws a variant per candidate):

| | FR | EN |
|---|---|---|
| Profile | Profil · Sommaire | Profile · Summary · Professional Summary |
| Skills | Compétences techniques · Compétences et outils · Expertise | Technical Skills · Skills & Tools · Skills · Expertise · Technical Stack |
| Soft skills | Compétences générales · Forces · *(omise)* | Core Strengths · Strengths · Working Style · *(dropped)* |

**Education**, **Languages** and the experience sections do NOT vary: their stems are what ATS section classifiers key on. Where a market file names one convention explicitly, that wins over the draw.
