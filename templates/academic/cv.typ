// vitae-academic: sections=13 entries=42
//
// vitae-academic template — academic/research CV, math & CS discipline
// variant (design note §2: conference proceedings are primary publications,
// author order is alphabetical, no first-author marking, seminars listed in
// full). Swap the discipline conventions in §1-2 of the design note for a
// different field; the mechanics below (lib-academic.typ) do not change.
//
// Design is an explicit ANTI-GOAL for this genre: one neutral gabarit, no
// family draw, no palette generation, no photo, no icons, no profile/summary
// hook, no keyword-skills list, no level bars. See academic-mode.md §1.1 for
// the full ban list. Data is TOML, not FAITS.md prose, because the ~200-plus
// enumerated entries need a format Typst AND Python read without a new
// dependency (`toml()` here, `tomllib` stdlib on the gate side) — the TOML,
// not this file, is the declared source of truth for section counts and
// order (see the schema header in faits-academique.example.toml).
//
// Verify with: typst compile --root . templates/academic/cv.typ out.pdf
// then pdftotext -layout out.pdf - | less  (checks A-E are manual until the
// academic gate is built; see academic-mode.md §3.2).
#import "lib-academic.typ": *

#let data = toml("faits-academique.example.toml")
#let m = data.meta

#set page(paper: "us-letter", margin: (x: 1.6cm, top: 1.4cm, bottom: 1.4cm),
  header: arunning-header(m.name.split(" ").last()),
  footer: arunning-footer())
#set text(font: ("Carlito", "Noto Sans", "Liberation Sans"), size: 10pt,
  lang: m.lang, hyphenate: false)
#set par(justify: false, leading: 0.6em)

#aheader(m.name, m.title, m.affiliation, m.address, m.email, m.cv_date,
  website: m.at("website", default: none), orcid: m.at("orcid", default: none))

// ---------------------------------------------------------------- 2. Education
#asection("Education", data.education.map(e => aentry(e.date, [
  #strong(e.degree), #e.institution
  #if e.at("thesis", default: none) != none [\ Thesis: #emph(e.thesis)]
  #if e.at("supervisor", default: none) != none [ (supervisor: #e.supervisor)]
])))

// ------------------------------------------------------------ 3. Appointments
#asection("Appointments", data.appointments.map(e => aentry(e.date, [
  #strong(e.role), #e.institution
])))

// -------------------------------------------------------------- 4. Honours
#asection("Honours and Awards", data.honours.map(e => aentry(e.date, [
  #e.title, #e.awarding_body
])))

// ----------------------------------------------------------- 5. Publications
#let pub-list(entries) = {
  let n = entries.len()
  entries.enumerate().map(((i, e)) => apub(n - i, e.date, [
    #e.authors. #emph(e.title) #e.venue.
    #if e.at("doi", default: none) != none [DOI: #e.doi.]
  ]))
}
#asection("Publications: Journal Articles", pub-list(data.publications.journal))
#asection("Publications: Peer-Reviewed Conference Proceedings",
  pub-list(data.publications.conference))
#asection("Publications: Preprints", pub-list(data.publications.preprint))

// ---------------------------------------------------------------- 6. Talks
#asection("Invited Plenary Talks", data.talks.plenary.map(e => aentry(e.date, [
  #e.title, #e.event, #e.location
])))
#asection("Invited Talks", data.talks.invited.map(e => aentry(e.date, [
  #e.title, #e.event, #e.location
])))
#asection("Conference Talks", data.talks.conference.map(e => aentry(e.date, [
  #e.title, #e.event, #e.location
])))
#asection("Seminar Talks", data.talks.seminar.map(e => aentry(e.date, [
  #e.title, #e.event, #e.location
])))
#asection("Posters", data.talks.poster.map(e => aentry(e.date, [
  #e.title, #e.event, #e.location
])))

// -------------------------------------------------------------- 7. Funding
#asection("Funding", data.funding.map(e => aentry(e.date, [
  #e.agency -- #e.program (#e.role), #e.amount #e.currency, #e.period
])))

// --------------------------------------------------------- 8. Supervision
#asection("Supervision and Training", data.supervision.map(e => aentry(e.date, [
  #e.student (#e.level): #emph(e.thesis_title)
  #if e.at("current_position", default: none) != none [\ Now: #e.current_position]
])))

// ------------------------------------------------------------- 9. Teaching
#asection("Teaching", data.teaching.map(e => aentry(e.date, [
  #e.code -- #e.title (#e.level), #e.term, enrolment #e.enrolment
])))

// -------------------------------------------------------- 10. Service
#asection("Service and Evaluation", data.service.map(e => aentry(e.date, [
  #e.description
])))

// --------------------------------------------- 11. Knowledge mobilization
#asection("Knowledge Mobilization", data.knowledge_mobilization.map(e => aentry(e.date, [
  #e.description
])))

// -------------------------------------------------- 12. Affiliations/languages
#block(above: 12pt)[
  #text(size: 12pt, weight: "bold")[AFFILIATIONS AND LANGUAGES]
  #v(2pt)
  #line(length: 100%, stroke: 0.6pt + luma(150))
  #v(4pt)
  #data.affiliations_languages.affiliations \
  #data.affiliations_languages.languages
]

// -------------------------------------------------------------- 13. References
#asection("References", data.references.map(e => block(breakable: false)[
  #e.name, #e.affiliation -- #e.email
]))
