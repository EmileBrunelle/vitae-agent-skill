# Field pack: academic CV

Load this file when the document is an academic CV: a faculty job search, a tenure/promotion file, a qualification dossier, or an academic appointment — never for an industry résumé, even from a candidate with a PhD.

The workflow, the data file, the correctness properties and the gate (`scripts/verify_academic.py`) are in [`academic-mode.md`](academic-mode.md); this file is the genre knowledge.

This file does not layer on top of the industry conventions elsewhere in this skill — it **replaces** them for this genre. The reasons live in the "Why this genre is different" note below; the rules follow.

**Confidence markers used throughout:** *(verified — source, date)* means a current source was checked; *(assumed)* means a reasonable inference from the one real specimen and general practice, not independently confirmed; *(confirm before relying on this)* flags something genuinely unclear that must be checked before it goes in a candidate's document. Do not upgrade an assumed convention to verified without checking a current source — a made-up regional convention costs more than admitting it isn't checked.

## Why this genre is different

An academic CV is exhaustive and cumulative, not curated: a career-spanning list of publications, talks, grants, and supervision, often 10+ pages. The unit that matters is the **entry** (one publication, one talk, one grant), not the section or the page. Page count is an output of the career, not a target; a section is not split across a "device budget" the way an industry résumé's whitespace is — there is no equivalent industry-mode check to run here (page totals, fill ratio, section-boundary spacing). Whatever verification this genre eventually gets must be built around counting and ordering entries, not around page geometry.

## Canonical sections

Order below is the research-track default, most common in North America. Mandatory = **M**, optional = **o**.

| # | Section | | Notes |
|---|---|---|---|
| 1 | Contact / general information | M | Name, title + affiliation, professional address, email, website, ORCID, and the **CV's own revision date**. |
| 2 | Education | M | Degree, institution, year, thesis title, advisor. |
| 3 | Appointments / positions | M | Include postdocs, visiting positions, sabbaticals. |
| 4 | Honors and awards | o | |
| 5 | **Publications**, split by type | M | Sub-list order is the main disciplinary variable — see Discipline differences below. |
| 6 | **Talks** | M | Invited plenaries → invited talks → conference talks → seminars → posters, in that descending order of prestige. |
| 7 | **Funding / grants** | M in Canada | Agency, program, role (PI / co-PI), amount, period. |
| 8 | **Supervision and mentoring** | M in Canada | PhD, master's, postdoc, internships; dates, thesis title, trainee's current position if known. |
| 9 | Teaching | M | Course code, title, level, term, enrollment; course/program development. |
| 10 | Service | M | Peer review (name the journals), agency review panels, thesis committees, editorial boards, departmental/faculty committees, conference organizing, learned societies. |
| 11 | Knowledge mobilization / outreach | o | Growing weight — funding agencies' descriptive CVs now value this explicitly. |
| 12 | Affiliations, languages | o | Two lines, never more. |
| 13 | References | o | Mostly a US convention — see Regional differences. |

**Never on an academic CV:** a summary/profile hook, photo, date of birth, marital status, a keyword-style "skills" list, skill-level bars or dots, or any graphic device that isn't a dated list. The specimen this file was built from has a 5-line header — that is the norm, not an economy measure.

### Two invariants that hold across every section

1. **Every entry carries a date.** An undated entry is one a committee cannot place in a trajectory.
2. **Strict reverse chronology inside each section**, no exceptions by grouping — except a leading block of "submitted" / "accepted, forthcoming" entries at the top of the publication list, which precedes the dated ones.

## Regional differences

**Québec / Canada** *(assumed for the section structure — supported by the specimen and by the agency rules confirmed below; the agency facts themselves are verified)*:
- Funding (#7) and supervision (#8) are the most scrutinized sections — they are what agencies count. Never fold them into a generic "other activities" section.
- Amounts in CAD, explicit role, full period.
- No personal data, no photo (same rule as the skill's industry mode).
- Bilingual reality: a French CV is normal within the Québec network; English for a search outside Québec. The skill's standing rule — the target language governs the whole deliverable — applies unchanged.

**France:**
- A CNU qualification application goes through the **Galaxie/Odyssée** platform with a fixed set of required pieces (thesis, defense report, publication list, up to 3 works) *(verified — galaxie.enseignementsup-recherche.gouv.fr; 2026 campaign: filing window Nov 3 – Dec 15, 2025)*.
- **Each CNU section publishes its own recommendations, and they differ meaningfully by discipline** *(verified — cnu25.emath.fr and doctoral-school guides explicitly tell candidates to check the target section's own page)*. Do not hard-code a CNU rule here: go read the target section's page and cite it in the deliverable.
- French-specific section names: "Qualification CNU section NN", "Responsabilités collectives", "Diffusion / vulgarisation".
- Teaching load is counted in hours with the CM / TD / TP breakdown, often in HETD (heures équivalent TD) *(confirm before relying on this — the vocabulary is certain, whether it's mandatory on a free-form CV is not)*.

**United States** *(verified — university career-services guidance, see Sources)*:
- Free length, no personal data, no photo.
- **Section order flips by institution type**: at a research-intensive institution, Publications/Grants move up right after Education; at a teaching-focused college, Teaching moves **ahead of** Publications. Ask which institution type is targeted — never guess it from the field alone.
- Non-peer-reviewed publications get their **own, separate** section ("Other / non-peer-reviewed publications"); mixing them into the refereed list reads as padding.
- References often appear on the CV itself or on a separate page — the reverse of the European norm.
- Research statement / teaching statement / diversity statement are **separate documents**, out of scope for the CV.

**Not covered:** UK, DACH, and the rest of the world. Do not invent — the same rule [`regional.md`](regional.md) already states applies here: if the market has no file, verify with a current source or ask, and label the assumption in the deliverable.

## Funding agency formats: firm recommendation — do not target them

Verified as of September 2026:

- **FRQ** (Québec): the technical bridge between FRQnet and the Canadian Common CV was disabled on December 19, 2025; no FRQ program requires the CCV in 2026. The current reference format is the **CV-FRQ**, a descriptive CV filled directly into the "CV-FRQ" section of the FRQnet application portal *(verified — frq.gouv.qc.ca)*.
- **The three federal agencies (NSERC / CIHR / SSHRC)**: a gradual move from the CCV to a **narrative-style tri-agency CV**, started in 2025, rolling out competition by competition (e.g. NSERC Discovery Horizons 2027) *(verified — cihr-irsc.gc.ca, sshrc-crsh.canada.ca, nserc-crsng.canada.ca)*.
- **France**: CNU qualification goes through Odyssée with fixed required pieces *(verified, see above)*.

Do not target any of these formats — CCV, CV-FRQ, tri-agency narrative CV, NIH biosketch, or any other agency portal form:

1. **They are not documents, they are portal forms** — a set of online fields with character limits and closed dropdown lists, not a composed PDF. There is nothing for a document template to produce.
2. **They are actively changing right now**, in two jurisdictions at once, rollout by rollout. Anything hard-coded here would be stale within one cycle.
3. The shift toward **narrative / descriptive** formats runs opposite to a countable, enumerated list — these are two different genres, not two templates of the same one.

What this field pack does instead, which has real, lasting value: **structure the candidate's data so it pours into these forms.** Every entry in the candidate's data source (see [`academic-mode.md`](academic-mode.md), "Data source") should carry the fields agencies ask for — role, amount, currency, period, peer-review status, author order, DOI. Feed the form; do not imitate it.

## Discipline differences

What actually changes the **order** or **weight** of sections. Anything not listed here is minor and should be asked about, not invented.

**Mathematics / theoretical computer science:**
- **Refereed conference proceedings are primary publications, not talks.** Filing them under "talks" is a costly misreading in CS — they belong in their own sub-list alongside journal articles. This is the single most consequential discipline difference in this file.
- **Author order is alphabetical** in mathematics: position carries no information. Never mark "first author," never bold the candidate's name as if it signals a leading contribution *(assumed, but a very well-established disciplinary convention)*.
- **Preprints (arXiv)** are a legitimate, expected section.
- **Seminars**: a long list is normal and expected here; the same length would read as padding in most other disciplines.
- Software, datasets, and tables are countable artifacts, often hosted externally rather than listed in the CV — treat as an optional section.

**Experimental sciences (biology, health, chemistry):**
- **Funding and lab personnel dominate**: sections #7 and #8 move up, often right after publications.
- **Author position carries information** (first / last / corresponding) and must be marked — the exact opposite of the math convention.
- Conference contributions produce **posters and abstracts**, ranked low and never mixed with articles.
- Bibliometrics (h-index, impact factors): sometimes listed, contested. Default to omitting them; add only on explicit request, and never compute them — an invented metric is a fabricated fact.

**Humanities and social sciences:**
- **Books and book chapters outrank articles.** The publication sub-list order inverts: books → edited volumes → chapters → articles.
- Solo authorship is the norm; author-position questions do not arise.
- Discipline-specific sections: **book reviews**, translations, editorial work, curatorial work depending on the field.
- Teaching weighs relatively more; funding weighs less.

**Minor, do not model:** the internal order of talk sub-types, how "accepted" is distinguished from "forthcoming," and the entry count at which a list gets split into sub-lists. These follow the target department's own practice — ask, don't decide.

## Sources (checked September 13, 2026)

- FRQ — CV-FRQ and the end of the CCV bridge (disabled Dec 19, 2025): FRQ, « CV-FRQ » and « Nouvelle étape dans le projet d’implantation du CV-FRQ : fin de la passerelle vers le CVC » (consulted 2026-11)
- CIHR — transition to the tri-agency CV: CIHR, « Transition to the Tri-agency CV » (consulted 2026-11)
- SSHRC — narrative-style CV: SSHRC, « Tri-agency CV » (consulted 2026-11)
- NSERC — introducing the tri-agency CV: NSERC, « NSERC to introduce the tri-agency CV for two funding opportunities » (consulted 2026-11)
- Galaxie / Odyssée — CNU qualification, required pieces and 2026 calendar: Ministère de l’Enseignement supérieur et de la Recherche, Galaxie, « Qualification aux fonctions de maître de conférences et de professeur des universités — Odyssée » (consulted 2026-11)
- CNU section 25 (mathematics) — section-specific recommendations: CNU section 25, « Qualification » (consulted 2026-11)
- UPenn Career Services — CV for a faculty job search (section order): University of Pennsylvania Career Services, « CVs for Faculty Job Applications » (consulted 2026-11)
- Dynamic Ecology — non-refereed publications in a separate section: Dynamic Ecology, « Formatting a CV for a faculty job application » (2016-08-25)

Anything above not tied to one of these sources is marked *(assumed)* or *(confirm before relying on this)* in the body of this file.
