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

**If the target market has no file, do not infer from training data** —
markets outside this set (Middle East, Asia, Latin America…) do not form a
bloc: conventions vary more inside that group than between Europe and North
America (Japan's rirekisho is a rigid form with photo and age; China expects
photos for domestic employers but not multinationals; Brazil/Mexico track US
norms). Verify with a current local source or ask, label the assumption in
the deliverable — and consider contributing the file.

## Quick matrix (orientation only — details in the market files)

| Region | Paper | Photo on CV | Verb form | Length norm |
|---|---|---|---|---|
| Canada / Québec / USA | us-letter | Never | EN past tense / FR-QC infinitive | 1 p. junior, 2 p. max |
| France | a4 | Declining, often advised against | Noun phrases / past participle | 1 p. strongly preferred |
| UK / Ireland | a4 | Never | Past tense | 1 p. early-career, 2 p. beyond |
| Germany / Austria / CH | a4 | Still expected by ~2/3 outside tech | Noun phrases (Lebenslauf) | 1-2 p. + attachments |

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
