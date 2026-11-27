# Field pack: academic CV

Loaded on demand when the document is an academic CV: a faculty job search, a tenure/promotion file, a qualification dossier, or an academic appointment — never for an industry résumé, even from a candidate with a PhD.

Read together with [`academic-mode.md`](../academic-mode.md), which holds the workflow, the data file, the correctness properties and the gate (`scripts/verify_academic.py`); this file is the genre knowledge.

This file does not layer on top of the industry conventions elsewhere in this skill — it **replaces** them for this genre. The reasons live in the "Why this genre is different" note below; the rules follow.

**Labels used throughout:** a sourced fact carries its S### id; *(LOW, unsourced)* means a reasonable inference from the one real specimen and general practice, not independently confirmed; *(not checked)* flags something genuinely unclear that must be checked before it goes in a candidate's document. Do not upgrade a LOW, unsourced convention to sourced without checking a current source — a made-up regional convention costs more than admitting it isn't checked.

## Why this genre is different

An academic CV is exhaustive and cumulative, not curated: a career-spanning list of publications, talks, grants, and supervision, often 10+ pages. The unit that matters is the **entry** (one publication, one talk, one grant), not the section or the page. Page count is an output of the career, not a target; a section is not split across a "device budget" the way an industry résumé's whitespace is — there is no equivalent industry-mode check to run here (page totals, fill ratio, section-boundary spacing). Whatever verification this genre eventually gets must be built around counting and ordering entries, not around page geometry.

## Canonical sections

Order below is the research-track default; the market file overrides. Mandatory = **M**, optional = **o**.

| # | Section | | Notes |
|---|---|---|---|
| 1 | Contact / general information | M | Name, title + affiliation, professional address, email, website, ORCID, and the **CV's own revision date**. |
| 2 | Education | M | Degree, institution, year, thesis title, advisor. |
| 3 | Appointments / positions | M | Include postdocs, visiting positions, sabbaticals. |
| 4 | Honors and awards | o | |
| 5 | **Publications**, split by type | M | Sub-list order is the main disciplinary variable — see Discipline differences below. |
| 6 | **Talks** | M | Invited plenaries → invited talks → conference talks → seminars → posters, in that descending order of prestige. |
| 7 | **Funding / grants** | M where agencies count it | Agency, program, role (PI / co-PI), amount, period. |
| 8 | **Supervision and mentoring** | M where agencies count it | PhD, master's, postdoc, internships; dates, thesis title, trainee's current position if known. |
| 9 | Teaching | M | Course code, title, level, term, enrollment; course/program development. |
| 10 | Service | M | Peer review (name the journals), agency review panels, thesis committees, editorial boards, departmental/faculty committees, conference organizing, learned societies. |
| 11 | Knowledge mobilization / outreach | o | Growing weight — funding agencies' descriptive CVs now value this explicitly. |
| 12 | Affiliations, languages | o | Two lines, never more. |
| 13 | References | o | Convention varies by market — see Regional differences. |

**Never on an academic CV:** a summary/profile hook, photo, date of birth, marital status, a keyword-style "skills" list, skill-level bars or dots, or any graphic device that isn't a dated list. The specimen this file was built from has a 5-line header — that is the norm, not an economy measure.

### Two invariants that hold across every section

1. **Every entry carries a date.** An undated entry is one a committee cannot place in a trajectory.
2. **Strict reverse chronology inside each section**, no exceptions by grouping — except a leading block of "submitted" / "accepted, forthcoming" entries at the top of the publication list, which precedes the dated ones.

## Regional differences

Market conventions (section scrutiny, institution-type order, references, agency formats, ranks) live in the target market's academic file, listed in [`regional.md`](../regional.md) § Market files and named in [`steps/2-region.md`](../steps/2-region.md). Read only that file.

**Not covered:** markets without an academic file. Do not invent; the same rule [`regional.md`](../regional.md) already states applies here: if the market has no file, verify with a current source or ask, and label the assumption in the deliverable.

## Funding agency formats: firm recommendation — do not target them

National agency formats (dated, as of September 2026): in the market's academic file.

Do not target any agency format (a common CV, a descriptive or narrative agency CV, a biosketch, or any other portal form):

1. **They are not documents, they are portal forms** — a set of online fields with character limits and closed dropdown lists, not a composed PDF. There is nothing for a document template to produce.
2. **They are actively changing right now**, rollout by rollout. Anything hard-coded here would be stale within one cycle.
3. The shift toward **narrative / descriptive** formats runs opposite to a countable, enumerated list — these are two different genres, not two templates of the same one.

What this field pack does instead, which has real, lasting value: **structure the candidate's data so it pours into these forms.** Every entry in the candidate's data source (see [`academic-mode.md`](../academic-mode.md), "Data source") should carry the fields agencies ask for — role, amount, currency, period, peer-review status, author order, DOI. Feed the form; do not imitate it.

## Discipline differences

What actually changes the **order** or **weight** of sections. Anything not listed here is minor and should be asked about, not invented.

**Mathematics / theoretical computer science:**
- **Refereed conference proceedings are primary publications, not talks.** Filing them under "talks" is a costly misreading in CS — they belong in their own sub-list alongside journal articles. This is the single most consequential discipline difference in this file.
- **Author order is alphabetical** in mathematics: position carries no information. Never mark "first author," never bold the candidate's name as if it signals a leading contribution *(LOW, unsourced: a very well-established disciplinary convention)*.
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

Sources for market facts: in the market academic files. Anything not tied to a source is marked *(LOW, unsourced)* or *(not checked)* in the body of this file.
