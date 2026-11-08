# Regional and language conventions — router

Apply the conventions of the market being applied to, not the user's locale. When the region is ambiguous, ask. Send the version in the language *and spelling variant* of the job posting.

**Load only what you need:** this file gives the file list and the universal rules; the per-market depth lives in `regional/<region>/…` — read ONLY the file(s) for the target market, listed below with their load condition. Each market file opens with an "At a glance" (profile columns: paper, photo, CV language, personal data, verb style, length); the add-on files (Québec, `to-…` and `outbound…` files) do not, and always come on top of the target market's file.

North America
- [`regional/north-america/us-canada.md`](regional/north-america/us-canada.md) — Canada, Québec, USA (us-letter; EN, FR-QC; no photo/age; length 1-2 p.; French outside Québec: see `francophone-canada.md`)
- [`regional/north-america/us-canada-government.md`](regional/north-america/us-canada-government.md) — read IN ADDITION to `us-canada.md` only when the target posting is a US federal (USAJOBS) or Government of Canada (GC Jobs) job: 2-page USAJOBS limit, per-job fields, GC Jobs screening-question rules
- [`regional/north-america/francophone-canada.md`](regional/north-america/francophone-canada.md) — read IN ADDITION to `us-canada.md` when the target market is NB, NS, PEI, Ontario or Manitoba AND (the CV is in French OR the employer is francophone); never for a Québec target. Sources loaded for NB, Ontario, PEI, Manitoba and federal jobs; for NS only the posting practice (French as requirement or asset), no level scale
- [`regional/north-america/quebec/market.md`](regional/north-america/quebec/market.md) — read IN ADDITION to `us-canada.md` only when the TARGET market is Québec (a Québec employer or posting; a Québec address alone does not make it the target): length and verbs, protected titles, ATS, OQLF diploma names
- [`regional/north-america/quebec/education.md`](regional/north-america/quebec/education.md) — Québec target AND the education section needs it: foreign diplomas (MIFI evaluation), degree in progress, stopped studies, transfers, DEC-BAC, AEC and bootcamps, GPA
- [`regional/north-america/quebec/outbound-common.md`](regional/north-america/quebec/outbound-common.md) — when the candidate holds Québec credentials (DEC, AEC, DEP, Québec university degree, Québec order membership) and targets ANY market other than Québec: read it IN ADDITION to the target market's file, plus ONE of the next two files
  - [`regional/north-america/quebec/outbound-north-america.md`](regional/north-america/quebec/outbound-north-america.md) — target English Canada or USA
  - [`regional/north-america/quebec/outbound-france.md`](regional/north-america/quebec/outbound-france.md) — target France (includes Québec–France double degrees)
- [`regional/europe/to-north-america.md`](regional/europe/to-north-america.md) — read IN ADDITION to `us-canada.md` when the TARGET market is USA, Canada or Québec and the candidate's credentials or CV habits are European (the target market wins over the address)

Europe
- [`regional/europe/france.md`](regional/europe/france.md) — France (a4; FR; photo declining; 1 p.)
- [`regional/europe/uk-ireland.md`](regional/europe/uk-ireland.md) — UK, Ireland (British spelling; no photo)
- [`regional/europe/dach.md`](regional/europe/dach.md) — Germany, Austria, Switzerland (Lebenslauf, photo and Zeugnisse customs)
- [`regional/europe/spain.md`](regional/europe/spain.md) — Spain only, never Latin America (a4; no consent clause, títulos oficiales vs propios, convocatorias)

India
- [`regional/india/market.md`](regional/india/market.md) — India (a4; resume vs biodata, CA/architect titles, CTC, campus and PSU hiring)
- [`regional/india/to-anglosphere.md`](regional/india/to-anglosphere.md) — read IN ADDITION to the target market's file when the candidate holds Indian credentials or Indian CV habits (3-year bachelor's, ICAI, NBA, ECA, ACS) and targets USA, Canada, UK, Australia or NZ (not Ireland or continental Europe: see below)
- [`regional/india/to-europe/common.md`](regional/india/to-europe/common.md) — Indian credentials targeting Germany, Ireland, the Netherlands or France: read it IN ADDITION to the target market's file, plus the target's file only (degree evaluation; Blue Card and carte talent diploma conditions):
  - [`regional/india/to-europe/germany.md`](regional/india/to-europe/germany.md) — Germany (anabin/ZAB)
  - [`regional/india/to-europe/ireland.md`](regional/india/to-europe/ireland.md) — Ireland (NARIC Ireland)
  - [`regional/india/to-europe/netherlands.md`](regional/india/to-europe/netherlands.md) — the Netherlands (Nuffic)
  - [`regional/india/to-europe/france.md`](regional/india/to-europe/france.md) — France (ENIC-NARIC France)

Asia
- [`regional/asia/outbound.md`](regional/asia/outbound.md) — read IN ADDITION to the target market's file when the candidate holds Pakistani, Bangladeshi, Nepali, Philippine or Chinese credentials (2-year bachelor's, K-12 reform, CHSI/CSSD) and targets a market outside their home country (India: [`regional/india/to-anglosphere.md`](regional/india/to-anglosphere.md))
- [`regional/asia/east-asia/japan.md`](regional/asia/east-asia/japan.md) — read when the CV goes to a Japanese employer (including a foreign applicant moving to Japan: status-of-residence evidence, HSP points, JLPT wording) or the candidate has Japanese home habits (rirekisho vs shokumu keirekisho); official-source facts only, no full market file
- [`regional/asia/east-asia/korea.md`](regional/asia/east-asia/korea.md) — read when the CV goes to a Korean employer (including a foreign applicant moving to Korea: E-7 wage floors, apostille, TOPIK) or the candidate has Korean home habits (hiring-law personal-data ban); official-source facts only, no full market file
- [`regional/asia/east-asia/taiwan.md`](regional/asia/east-asia/taiwan.md) — read only when the target is Taiwan AND the candidate is a foreign professional (work permit or Gold Card, TOCFL, Employment Service Act discrimination list); official-source facts only, no full market file
- [`regional/asia/southeast-asia/`](regional/asia/southeast-asia/overview.md) — six *non-interchangeable* markets, one file each: read ONLY the target country's file, never the file average ([`overview.md`](regional/asia/southeast-asia/overview.md) only for the cross-country comparison):
  - [`regional/asia/southeast-asia/indonesia.md`](regional/asia/southeast-asia/indonesia.md) — Indonesia
  - [`regional/asia/southeast-asia/malaysia.md`](regional/asia/southeast-asia/malaysia.md) — Malaysia
  - [`regional/asia/southeast-asia/singapore.md`](regional/asia/southeast-asia/singapore.md) — Singapore
  - [`regional/asia/southeast-asia/philippines.md`](regional/asia/southeast-asia/philippines.md) — Philippines
  - [`regional/asia/southeast-asia/vietnam.md`](regional/asia/southeast-asia/vietnam.md) — Vietnam
  - [`regional/asia/southeast-asia/thailand.md`](regional/asia/southeast-asia/thailand.md) — Thailand

Middle East
- [`regional/middle-east/gulf/market.md`](regional/middle-east/gulf/market.md) — the CV goes to an employer in the UAE, Saudi Arabia or Qatar and the candidate is an expatriate (work authorisation, notice, probation, mobility; no CV-custom source, so no photo/DOB/nationality rule; three *non-interchangeable* markets; Kuwait, Oman and Bahrain: no file)
  - [`regional/middle-east/gulf/nationalisation.md`](regional/middle-east/gulf/nationalisation.md) — read IN ADDITION when the target role may be reserved for nationals or quota-driven
  - [`regional/middle-east/gulf/credentials.md`](regional/middle-east/gulf/credentials.md) — read IN ADDITION when a degree or licence will be verified (engineering, health, law; UAE "skilled" permit)
- [`regional/middle-east/near-east/outbound.md`](regional/middle-east/near-east/outbound.md) — read IN ADDITION to the target market's file when the candidate holds Egyptian, Lebanese or Jordanian credentials (alone or mixed) and targets Québec/Canada or Europe, or asks about Egyptian military status
- [`regional/middle-east/near-east/jordan-foreign-workers.md`](regional/middle-east/near-east/jordan-foreign-workers.md) — a non-Jordanian targets a job in Jordan
- [`regional/middle-east/near-east/turkiye-foreign-workers.md`](regional/middle-east/near-east/turkiye-foreign-workers.md) — a non-Turkish national targets a job in Türkiye

Oceania, Latin America, Africa
- [`regional/oceania/australia-nz.md`](regional/oceania/australia-nz.md) — Australia, New Zealand (one file, two *non-interchangeable* markets — a4; no photo; work rights, APS, engineer registration)
- [`regional/latin-america/brazil-latam.md`](regional/latin-america/brazil-latam.md) — Brazil, Mexico, Argentina, Chile, Colombia (one file, *non-interchangeable* markets — read the country section; Gupy ATS, CREA/CRC titles)
- [`regional/africa/maghreb.md`](regional/africa/maghreb.md) — Morocco, Algeria, Tunisia (one file, three *non-interchangeable* markets — same warning)
- [`regional/africa/maghreb-outbound/common.md`](regional/africa/maghreb-outbound/common.md) — read IN ADDITION to the target market's file when the candidate holds Moroccan, Algerian or Tunisian credentials (alone or mixed with other countries') and targets Québec/Canada or Europe, plus ONE of:
  - [`regional/africa/maghreb-outbound/to-quebec-canada.md`](regional/africa/maghreb-outbound/to-quebec-canada.md) — target Québec or English Canada (MIFI, IRCC ECA, OIQ)
  - [`regional/africa/maghreb-outbound/to-europe.md`](regional/africa/maghreb-outbound/to-europe.md) — target France; Belgium, Spain and Germany not covered
  - [`regional/africa/maghreb-outbound/transnational.md`](regional/africa/maghreb-outbound/transnational.md) — read IN ADDITION when a credential was earned on a campus abroad of a foreign school, delivered under a foreign partnership, or is a double/joint diploma (LaSalle Maroc/Tunis, delocalised Québec AEC, Dauphine Tunis)

**If the target market has no file, do not infer from training data** — markets outside this set (China, Kuwait, Oman, Bahrain, other Middle East and Asian markets…) do not form a bloc: conventions vary more inside that group than between Europe and North America (China, which has no file, expects photos for domestic employers but not multinationals; Japan, Korea and Taiwan have only official-source facts, in the three [`regional/asia/east-asia/`](regional/asia/east-asia/japan.md) files: the rirekisho has an MHLW sample form with photo and age fields, but MHLW says employers may use other forms; the Gulf and Near East files cover foreign workers, not a CV-custom source). Verify with a current local source or ask, label the assumption in the deliverable — and consider contributing the file. The same warning applies *inside* a multi-market file: Singapore and Thailand are neighbouring markets and disagree on nearly every axis (photo, personal data, formality).

Cautions the market files compress: **us-letter is firm only in North America and Philippines print; Mexico, Chile and Colombia are LOW confidence** (see [`regional/latin-america/brazil-latam.md`](regional/latin-america/brazil-latam.md)); **a national ID number never belongs on a CV in any market listed**; a **Thai** document's Buddhist-Era year (B.E. = CE + 543) must be converted before it reaches a foreign reader; and where a photo is expected, the DACH mechanics apply (formal, front-facing, plain background) — Indonesia and the Philippines additionally fix a print size.

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
