# Field pack: software development

Load this file when the candidate targets software roles. It layers dev-market
depth on top of the generic method — every rule here was validated through
simulated adversarial hiring reviews on a real junior-developer dossier.

## Positioning

- Map internship months + shipped-code time honestly: recruiters read "3
  internships" as junior no matter how it is phrased. Target postings that say
  "junior", "1-3 years", or "intermediate (min. 1 year)"; postings demanding
  3-5+ years reject stage-heavy profiles at triage.
- Header title: "Software Developer" / « Développeur logiciel » (+ full stack /
  backend / frontend qualifier). Never "Engineer" as a job title unless the
  candidate holds the license where required (see regional.md) — the degree in
  the header carries the engineering signal legally.
- If the current role is not a dev role, split sections: the target-field
  experience block leads, the off-track job goes under "Other professional
  experience" with 1-2 transferable bullets. Every month out of code is an
  interview question — prepare the candidate for "why, and why come back?".

## The portfolio lever

- A public GitHub link is the single highest-leverage addition for junior and
  intermediate profiles — unanimous across every simulated reviewer, and
  startups treat its absence as a near-eliminatory signal ("does this person
  code because they like it?").
- Link it in the header only if there is at least one presentable repo:
  README with a screenshot, CI badge, deployed link, honest "technical
  decisions" section. An empty profile linked is worse than no link.
- Curate projects per target version: pick the few genuinely relevant ones,
  each as its own entry with its own link — a lumped "school projects" line
  buries the best work, and an algorithm project that sells a
  scientific-computing version can be dead weight on a game version.
- Link each project entry to its EXACT repo (clickable title or visible URL),
  not just the profile — reviewers unanimously prefer one-click access, and
  the original CV's copy-pasted-wrong repo link is a classic bug to check.
- **Verify claimed implementation details in the candidate's public repos**:
  clone and grep. A claim like "quaternion interpolation (SLERP)" confirmed
  in the actual source is the strongest anchor that exists — and repos often
  reveal bonus anchors (unit test files anchor "automated testing" with
  public proof). Conversely, never let a plausible-sounding technical detail
  onto the CV unverified when the code is one clone away.
- Minimum viable showcase: one small product with real business logic (not a
  todo/clone), tests on the logic, a CI pipeline, a free deployment. 30-40 h.

## Keyword families (each listed item must survive an interview)

- Spell both forms: "continuous integration (CI/CD)", "version control (Git)",
  acronyms AND words — boolean searches hit either.
- Group skills in 5-7 rows: Languages / Frontend / Backend & data /
  Software quality / Tools & DevOps / Methodologies. The quality row
  (unit & integration testing, code review, test plans) is an
  underused differentiator — most juniors cannot prove it; anchor it in
  experience bullets.
- Watch the era gaps: TypeScript-first postings, cloud platforms named
  (Azure/AWS/GCP), container keywords. Never add them unproven — flag the gap
  to the user with the project-based way to close it instead.
- Employers verify LinkedIn *and* GitHub. Stack claims must match in all three
  places.

## Market segments (verdict patterns from simulation)

| Segment | Version to send | What decides |
|---|---|---|
| Product/SaaS company | 2-page | Highlights block + proof density |
| Startup / scale-up | 1-page only | GitHub, shipping speed signals; 2 pages for a junior reads as padding |
| Consulting firm | 2-page | CV is resold to clients: transparency on internships, no overclaimed skills, availability date |
| Bank/gov/regulated | match posting stack exactly | A skills-list-only language ("Java" with no bullets) fails triage as keyword stuffing |

Use these four segments as the reviewer personas in the adversarial step, plus
one deliberately bad-fit posting to confirm the CV does not oversell.

## AI-assisted development (2026 reality)

- "How do you use AI tools?" is a near-systematic interview question — the
  companion guide should prep it. Winning angle for a junior: judgment and
  verification (review, tests, git hygiene), never tool loyalty; the
  interviewer is testing "can you debug code you didn't write".
- If the companion recommends tools, web-verify free tiers at writing time
  and label them "as of <date>, revalidate" — free tiers of AI coding tools
  get cut with little notice.

## Dev-specific title notes

- Default job title on the CV: developer, not engineer (see regional.md for
  the legal map). Engineering-degree holders in Canada may add the registered
  pathway once enrolled (e.g. Québec's « CPI ») — a real asset only when
  targeting engineering-culture employers (aerospace, defence, industrial),
  noise for SaaS/startups.
- Interview-fatal verbs to soften for interns/juniors: "led architecture",
  "owned", "guaranteed" → "contributed to design discussions", "strengthened",
  unless literally true and defensible with a story.
- Deriving an EN version from a FR file (or vice versa): the skill-row helper
  and dates carry language conventions — check the colon style (`~:` French
  non-breaking space vs plain `:`), month abbreviations, and quote styles
  survive the translation. Verified failure mode: EN CVs shipping with French
  spaced colons.
- Local course codes are opaque outside the school — translating
  them into their actual content (object-oriented design, GoF patterns, unit
  testing/JUnit, UML) is a legitimate ATS improvement IF the syllabus backs
  it; ask for the course plan when available, it is a goldmine of defensible
  anchors. Watch the GRASP-vs-GoF confusion: candidates (and users) routinely
  answer a GRASP question with GoF patterns — if both are claimed, the
  interview-prep companion must spell out the difference.
