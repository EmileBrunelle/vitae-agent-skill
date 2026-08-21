# Regional and language conventions — router

Apply the conventions of the market being applied to, not the user's locale.
When the region is ambiguous, ask. Send the version in the language *and
spelling variant* of the job posting.

**Load only what you need:** this file gives the overview and the universal
rules; the per-market depth lives in `regional/<market>.md` — read ONLY the
file for the target market:

- `regional/north-america.md` — Canada, Québec, USA
- `regional/france.md`
- `regional/uk-ireland.md`
- `regional/dach.md` — Germany, Austria, Switzerland
- `regional/southeast-asia.md` — Indonesia, Malaysia, Singapore,
  Philippines, Vietnam, Thailand (one file, six *non-interchangeable*
  markets — read the country section, never the file average)

**If the target market has no file, do not infer from training data** —
markets outside this set (Middle East, East Asia, Latin America…) do not form
a bloc: conventions vary more inside that group than between Europe and North
America (Japan's rirekisho is a rigid form with photo and age; China expects
photos for domestic employers but not multinationals; Brazil/Mexico track US
norms). Verify with a current local source or ask, label the assumption in
the deliverable — and consider contributing the file. The same warning applies
*inside* a multi-market file: Singapore and Thailand share one and disagree on
nearly every axis of the matrix below.

## Quick matrix (orientation only — details in the market files)

The market files carry only their deltas from this table.

| Market | Paper | Photo on CV | CV language | Personal data | Formality / verb style | Length norm |
|---|---|---|---|---|---|---|
| Canada / Québec / USA | us-letter | Never | EN, or FR for Québec | None (no age, no marital status) | Verb-first bullets; EN past tense / FR-QC infinitive | 1 p. junior, 2 p. max |
| France | a4 | Declining, often advised against | FR | Omit by default; hobbies are a plus | Formal; noun phrases / past participle | 1 p. strongly preferred |
| UK / Ireland | a4 | Never | EN, British spelling | None | Verb-first bullets, past tense | 1 p. early-career, 2 p. beyond |
| Germany / Austria / CH | a4 | Still expected by ~2/3 outside tech | DE (EN for intl. roles) | Birth date still common | Very formal, tabular Lebenslauf, noun phrases | 1-2 p. + attachments (Zeugnisse) |
| Indonesia | a4 | Expected (« pas foto », print-sized); optional in private tech | ID; EN for multinationals/startups | Traditional biodata now discouraged (UU PDP); hobbies normal | Formal; separate « surat lamaran » expected | 1-2 p. + scanned attachments |
| Malaysia | a4 | Contested — check the posting | EN by default; BM for government/GLC | Drop DOB / marital / IC; CGPA expected | Moderately formal; summary + skills block first | 1 p. fresh grad, 2-3 p. experienced |
| Singapore | a4 | Discouraged (TAFEP; WFA 2025) | EN, British spelling | None (no NRIC — PDPC advisory) | Anglo-Saxon baseline, verb-first bullets | 1 p., 2 p. senior |
| Philippines | us-letter ("short bond"); a4 accepted digitally | Expected (2×2 in ID photo) | EN, American spelling | Rich by custom and contracting; Character References still normal | Formal; local sections (Seminars and Trainings, Eligibility) | 1 p. fresh grad, 2 p. at 5+ yrs |
| Vietnam | a4 | Optional on the modern CV | VI; EN for FDI; VI+EN bilingual is real | Off the CV — those fields belong to the notarised sơ yếu lý lịch | Formal; state sector also wants the stamped form | 1-2 p. |
| Thailand | a4 (LOW confidence — verify) | Expected, formal studio headshot | TH; EN for multinationals | Customary (incl. military status) though PDPA tells employers not to ask | Formal; expected-salary field is standard | 1-2 p. |

Cautions the matrix compresses: **paper is us-letter in exactly two places**
(North America, and Philippines print); **a national ID number never belongs
on a CV in any market listed**; a **Thai** document's Buddhist-Era year
(B.E. = CE + 543) must be converted before it reaches a foreign reader; and
where a photo is expected, the DACH mechanics apply (formal, front-facing,
plain background) — Indonesia and the Philippines additionally fix a print
size.

## Universal rules (every market)

- In every tense-based convention, the **current role is written in the
  present tense**, finished roles in the convention's past form.
- Anti-discrimination norms shift everywhere toward *no photo, no personal
  data* on the CV; when in doubt, omit and tell the user the local custom.
  **The CV photo rule never applies to LinkedIn** — a profile photo is
  expected on LinkedIn in every market.
- Employment gaps: present honestly — real month+year dates, no camouflage
  via year-only ranges; a short neutral mention beats an unexplained hole,
  and the candidate decides the wording.
- Hobbies/interests: personality signal in France/Germany, filler in the
  US/UK unless directly relevant — see the market file.
- **Protected titles exist in many fields and jurisdictions** (health, law,
  finance, engineering…). The market files give known cases; the list is
  never exhaustive — check the target country's professional regulator for
  any regulated-sounding field. Rule of thumb everywhere: header title =
  unregulated role name + degree in parentheses; the degree carries the
  professional signal legally.
- **Gloss local institutions and diplomas** for foreign readers: keep the
  original name + a short gloss rather than a lossy translation.
- **Translation is adaptation, not word-mapping.** Watch for calques (FR→EN
  "within a team" → "on a team"); include a native-reviewer pass in the
  adversarial loop for any translated version.
- Set `lang:` on `#set text(...)` per document — it drives hyphenation and
  smart-quote behavior.
- **The target market caps the visual audacity dial, never raises it.** A
  conservative target market forces `sober` (`references/design.md` § colour;
  `scripts/pick_design.py --conservative`), whatever the candidate's field or
  the design family. Whether a market is conservative for this purpose is
  established the same way as everything else in this file — the market's own
  file, current sources, or the user — never assumed from training data, and
  the assumption gets labelled in the deliverable when it cannot be verified.
  A market may also cap it *below* the candidate's request; the dial is only
  ever raised by the explicit request of the candidate or user.

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

Derive the target-field section name with the same pattern for any field
("Expérience en soins infirmiers", "Nursing Experience"). Keep names close to
conventional stems — a qualifier after a conventional stem is safe; fully
exotic names risk ATS misclassification.

**Accepted variants** (the lexical skeleton is part of the anti-clone system —
`references/design.md` § Section labels; each design family carries its own
defaults and `scripts/pick_design.py` draws a variant per candidate):

| | FR | EN |
|---|---|---|
| Profile | Profil · Sommaire | Profile · Summary · Professional Summary |
| Skills | Compétences techniques · Compétences et outils · Expertise | Technical Skills · Skills & Tools · Skills · Expertise · Technical Stack |
| Soft skills | Compétences générales · Forces · *(omise)* | Core Strengths · Strengths · Working Style · *(dropped)* |

**Education**, **Languages** and the experience sections do NOT vary: their
stems are what ATS section classifiers key on. Where a market file names one
convention explicitly, that wins over the draw.
