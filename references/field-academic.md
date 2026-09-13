# Field pack: academic CV

Load this file when the document is an academic CV: a faculty job search, a
tenure/promotion file, a qualification dossier, or an academic appointment —
never for an industry résumé, even from a candidate with a PhD.

This file does not layer on top of the industry conventions elsewhere in this
skill — it **replaces** them for this genre. The reasons live in the
"Why this genre is different" note below; the rules follow.

**Confidence markers used throughout:** *(verified — source, date)* means a
current source was checked; *(assumed)* means a reasonable inference from the
one real specimen and general practice, not independently confirmed; *(confirm
before relying on this)* flags something genuinely unclear that must be
checked before it goes in a candidate's document. Do not upgrade an assumed
convention to verified without checking a current source — a made-up regional
convention costs more than admitting it isn't checked.

## Why this genre is different

An academic CV is exhaustive and cumulative, not curated: a career-spanning
list of publications, talks, grants, and supervision, often 10+ pages. The
unit that matters is the **entry** (one publication, one talk, one grant), not
the section or the page. Page count is an output of the career, not a target;
a section is not split across a "device budget" the way an industry résumé's
whitespace is — there is no equivalent industry-mode check to run here (page
totals, fill ratio, section-boundary spacing). Whatever verification this
genre eventually gets must be built around counting and ordering entries, not
around page geometry.

## Canonical sections

Order below is the research-track default, most common in North America.
Mandatory = **M**, optional = **o**.

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

**Never on an academic CV:** a summary/profile hook, photo, date of birth,
marital status, a keyword-style "skills" list, skill-level bars or dots, or
any graphic device that isn't a dated list. The specimen this file was built
from has a 5-line header — that is the norm, not an economy measure.

### Two invariants that hold across every section

1. **Every entry carries a date.** An undated entry is one a committee cannot
   place in a trajectory.
2. **Strict reverse chronology inside each section**, no exceptions by
   grouping — except a leading block of "submitted" / "accepted, forthcoming"
   entries at the top of the publication list, which precedes the dated ones.

## Regional differences

**Québec / Canada** *(assumed for the section structure — supported by the
specimen and by the agency rules confirmed below; the agency facts themselves
are verified)*:
- Funding (#7) and supervision (#8) are the most scrutinized sections — they
  are what agencies count. Never fold them into a generic "other activities"
  section.
- Amounts in CAD, explicit role, full period.
- No personal data, no photo (same rule as the skill's industry mode).
- Bilingual reality: a French CV is normal within the Québec network; English
  for a search outside Québec. The skill's standing rule — the target
  language governs the whole deliverable — applies unchanged.

**France:**
- A CNU qualification application goes through the **Galaxie/Odyssée**
  platform with a fixed set of required pieces (thesis, defense report,
  publication list, up to 3 works) *(verified —
  galaxie.enseignementsup-recherche.gouv.fr; 2026 campaign: filing window
  Nov 3 – Dec 15, 2025)*.
- **Each CNU section publishes its own recommendations, and they differ
  meaningfully by discipline** *(verified — cnu25.emath.fr and doctoral-school
  guides explicitly tell candidates to check the target section's own page)*.
  Do not hard-code a CNU rule here: go read the target section's page and cite
  it in the deliverable.
- French-specific section names: "Qualification CNU section NN",
  "Responsabilités collectives", "Diffusion / vulgarisation".
- Teaching load is counted in hours with the CM / TD / TP breakdown, often in
  HETD (heures équivalent TD) *(confirm before relying on this — the
  vocabulary is certain, whether it's mandatory on a free-form CV is not)*.

**United States** *(verified — university career-services guidance, see
Sources)*:
- Free length, no personal data, no photo.
- **Section order flips by institution type**: at a research-intensive
  institution, Publications/Grants move up right after Education; at a
  teaching-focused college, Teaching moves **ahead of** Publications. Ask
  which institution type is targeted — never guess it from the field alone.
- Non-peer-reviewed publications get their **own, separate** section ("Other
  / non-peer-reviewed publications"); mixing them into the refereed list
  reads as padding.
- References often appear on the CV itself or on a separate page — the
  reverse of the European norm.
- Research statement / teaching statement / diversity statement are
  **separate documents**, out of scope for the CV.

**Not covered:** UK, DACH, and the rest of the world. Do not invent — the same
rule `regional.md` already states applies here: if the market has no file,
verify with a current source or ask, and label the assumption in the
deliverable.

## Funding agency formats: firm recommendation — do not target them

Verified as of September 2026:

- **FRQ** (Québec): the technical bridge between FRQnet and the Canadian
  Common CV was disabled on December 19, 2025; no FRQ program requires the
  CCV in 2026. The current reference format is the **CV-FRQ**, a descriptive
  CV filled directly into the "CV-FRQ" section of the FRQnet application
  portal *(verified — frq.gouv.qc.ca)*.
- **The three federal agencies (NSERC / CIHR / SSHRC)**: a gradual move from
  the CCV to a **narrative-style tri-agency CV**, started in 2025, rolling
  out competition by competition (e.g. NSERC Discovery Horizons 2027)
  *(verified — cihr-irsc.gc.ca, sshrc-crsh.canada.ca, nserc-crsng.canada.ca)*.
- **France**: CNU qualification goes through Odyssée with fixed required
  pieces *(verified, see above)*.

Do not target any of these formats — CCV, CV-FRQ, tri-agency narrative CV,
NIH biosketch, or any other agency portal form:

1. **They are not documents, they are portal forms** — a set of online fields
   with character limits and closed dropdown lists, not a composed PDF. There
   is nothing for a document template to produce.
2. **They are actively changing right now**, in two jurisdictions at once,
   rollout by rollout. Anything hard-coded here would be stale within one
   cycle.
3. The shift toward **narrative / descriptive** formats runs opposite to a
   countable, enumerated list — these are two different genres, not two
   templates of the same one.

What this field pack does instead, which has real, lasting value:
**structure the candidate's data so it pours into these forms.** Every entry
in the candidate's data source (see below) should carry the fields agencies
ask for — role, amount, currency, period, peer-review status, author order,
DOI. Feed the form; do not imitate it.

## Discipline differences

What actually changes the **order** or **weight** of sections. Anything not
listed here is minor and should be asked about, not invented.

**Mathematics / theoretical computer science:**
- **Refereed conference proceedings are primary publications, not talks.**
  Filing them under "talks" is a costly misreading in CS — they belong in
  their own sub-list alongside journal articles. This is the single most
  consequential discipline difference in this file.
- **Author order is alphabetical** in mathematics: position carries no
  information. Never mark "first author," never bold the candidate's name as
  if it signals a leading contribution *(assumed, but a very well-established
  disciplinary convention)*.
- **Preprints (arXiv)** are a legitimate, expected section.
- **Seminars**: a long list is normal and expected here; the same length
  would read as padding in most other disciplines.
- Software, datasets, and tables are countable artifacts, often hosted
  externally rather than listed in the CV — treat as an optional section.

**Experimental sciences (biology, health, chemistry):**
- **Funding and lab personnel dominate**: sections #7 and #8 move up, often
  right after publications.
- **Author position carries information** (first / last / corresponding) and
  must be marked — the exact opposite of the math convention.
- Conference contributions produce **posters and abstracts**, ranked low and
  never mixed with articles.
- Bibliometrics (h-index, impact factors): sometimes listed, contested.
  Default to omitting them; add only on explicit request, and never compute
  them — an invented metric is a fabricated fact.

**Humanities and social sciences:**
- **Books and book chapters outrank articles.** The publication sub-list
  order inverts: books → edited volumes → chapters → articles.
- Solo authorship is the norm; author-position questions do not arise.
- Discipline-specific sections: **book reviews**, translations, editorial
  work, curatorial work depending on the field.
- Teaching weighs relatively more; funding weighs less.

**Minor, do not model:** the internal order of talk sub-types, how
"accepted" is distinguished from "forthcoming," and the entry count at which
a list gets split into sub-lists. These follow the target department's own
practice — ask, don't decide.

## Data source: structured file alongside FAITS.md

`FAITS.md` keeps its usual role: identity, appointments, education, and
anything needing a provenance tag discussed with the candidate — same
discipline as the skill's rule 1 (no fact without a source). It carries more
weight here than in industry mode: an invented publication is not
embellishment, it is research misconduct. Every publication entry additionally
needs a public, verifiable identifier (DOI, arXiv ID, or publisher URL) — this
is exactly the "what's the portfolio equivalent in this field?" question the
skill already asks for any field.

The 200+ enumerated entries (publications, talks, grants, supervision,
service) do not belong in `FAITS.md` line by line — they belong in a
structured data file, readable by both the template engine and any future
verification tooling without adding a dependency (TOML is a reasonable
choice: readable natively by Typst's `toml()` and by Python's stdlib
`tomllib`). Each entry should carry:
- `date` (mandatory — see the two invariants above),
- `src` — the same provenance convention as `FAITS.md`,
- the fields the funding agencies ask for (role, amount, currency, period,
  peer-review status, author order, DOI/identifier).

This data file, not the rendered document, is the source of truth for
section counts and ordering — any correctness check must compare the
rendered output back against this file, never read the rendered output alone
and call that verification.

## Correctness properties this genre must satisfy

These are properties a correct academic CV has, stated as rules for whoever
builds or reviews this document — not a description of any particular
checking tool.

- **A. Counts round-trip.** For every section, the number of entries declared
  in the data source equals the number of entries the rendered document
  actually shows. This is the single most valuable property: it catches an
  entry swallowed at a page break, broken list numbering, column
  interleaving on extraction, or a duplicated entry — and it verifies the
  document's actual purpose (a committee counts 25 articles; the document
  had better show 25). Where entries are numbered (common in math/CS,
  `[25]`, `[24]`…), the numbering must also be contiguous and monotonic.
- **B. Strict reverse chronology per section.** The sequence of years in each
  section is non-increasing, after a declared-length prefix of undated
  entries ("submitted," "forthcoming"). This is the most common real defect
  on a CV maintained by hand over many years, and it is a genuine failure,
  not a style preference — declare the prefix length explicitly for any
  section that is legitimately chronological in the other direction; never
  guess it.
- **C. No orphaned section heading at the bottom of a page.** The last line
  of content on a page is never a section or sub-section heading; a heading
  is always followed by at least two lines of its own entries on the same
  page.
- **D. No entry split across a page break.** The first line of content on
  every page (running head excluded) is either a section heading or the
  start of a new dated entry — never the continuation of one. This is the
  honest replacement for "no section ever split," applied at the entry
  level instead of the section level. It costs a last page that sometimes
  ends 1-3 lines short — with no fill target (see below), that cost is free.
- **E. Running head and pagination beyond 2 pages.** Every page carries the
  candidate's surname and "page n of N." An academic dossier gets printed,
  stapled, photocopied, and passed around a committee one page at a time —
  unlike an ATS-scanned industry résumé, there is no parser here that skips
  header/footer regions, so this is safe and expected in this genre even
  though the skill's industry-mode rule warns against putting anything
  load-bearing in a header/footer.

**What is measured and reported, never turned into a failure:** page count,
last-page fill, prose-vs-list ratio, a per-section entry-count table (useful
to the candidate too, as a quantitative summary of their own dossier).

**What does not apply to this genre, stated as rules:**
- **There is no fill target, not even a floor on the last page.** A last page
  that ends short because the next entry didn't fit is correct, not
  under-filled — there is no number here that anything could be measured
  against.
- **Prose-to-list ratio is not a pass/fail check.** It varies legitimately by
  discipline (humanities produce more prose) and by target (a descriptive
  agency CV can be 100% prose) — report it, never fail on it.
- **No section-boundary spacing checks** (the kind of device-quorum or
  whitespace-ceiling checks industry mode runs at section boundaries). This
  genre's atom is the entry, not the section boundary; those checks have no
  matching population here.
- **"Every entry is dated" is not a standalone text-extraction check.** On
  extracted text alone there's no reliable way to tell where one entry ends
  and the next begins. This requirement lives at the data-source level
  instead (the date field is mandatory there) and is verified through
  property A, by count, not by scanning raw text for year-like tokens.

## What else does not apply here

- Fixed page-count targets, a paired 1-page/2-page deliverable.
- Keyword/ATS rules, a profile/summary hook, action-verb bullet conventions.
- Any design system, palette, or visual-boldness dial — a single neutral,
  low-key layout is the goal here, not variety.
- The job-search companion guide — out of scope for this genre.

## Sources (checked September 13, 2026)

- FRQ — CV-FRQ and the end of the CCV bridge (disabled Dec 19, 2025):
  https://frq.gouv.qc.ca/cv-frq/ and
  https://frq.gouv.qc.ca/nouvelle-etape-dans-le-projet-dimplantation-du-cv-frq-fin-de-la-passerelle-vers-le-cvc/
- CIHR — transition to the tri-agency CV: https://cihr-irsc.gc.ca/e/54668.html
- SSHRC — narrative-style CV: https://sshrc-crsh.canada.ca/en/funding/forms-and-online-application-tools/tri-agency-cv.aspx
- NSERC — introducing the tri-agency CV:
  https://nserc-crsng.canada.ca/en/news/nserc-introduce-tri-agency-cv-two-funding-opportunities
- Galaxie / Odyssée — CNU qualification, required pieces and 2026 calendar:
  https://www.galaxie.enseignementsup-recherche.gouv.fr/ensup/cand_qualification_Odyssee.htm
- CNU section 25 (mathematics) — section-specific recommendations:
  https://cnu25.emath.fr/qualif.html
- UPenn Career Services — CV for a faculty job search (section order):
  https://careerservices.upenn.edu/application-materials-for-the-faculty-job-search/cvs-for-faculty-job-applications/
- Dynamic Ecology — non-refereed publications in a separate section:
  https://dynamicecology.wordpress.com/2016/08/25/formatting-a-cv-for-a-faculty-job-application/

Anything above not tied to one of these sources is marked *(assumed)* or
*(confirm before relying on this)* in the body of this file.
