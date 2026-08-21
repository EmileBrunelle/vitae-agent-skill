// FAMILY: gutter-rail — the themed developer environment, read in print
// REGISTER: creative (never in the default pool — design.md § The creative
// register: unlocked by a creative target field, by a SOFTWARE field plus an
// explicit request, or by --creative; capped back out by a conservative
// market).
//
// THE CURRENT, and it is a documented one, not a mood: the "coordinated theme"
// practice of developer environments — a code editor's chrome (a gutter with
// its sign column, fold marks, a statusline of segments) and the tiling-desktop
// rice conventions (bar modules as discrete segments, uniform gaps, ONE
// reserved accent for the live state). Harvested from the LIGHT halves of that
// tradition (the light-theme lineage that Solarized Light started and the
// curated palettes after it), from the opinionated-rice practice (flat, square,
// unrounded segments; one hardcoded accent for active modules) and from an
// institutional desktop's design language (a single corner-style token applied
// uniformly to every surface, a first-class light theme whose accent is
// re-derived per surface instead of inverted).
//
// NOT a screenshot of one editor or one distro: the non-recognition bar covers
// products too (design.md § The final bar). No line numbers, no syntax
// colouring, no tab bar, no dark background — those are what make a page
// identifiable as VS Code or as one rice.
// ---------- Shared mechanics (templates/lib.typ) ----------
#import "lib.typ": *
// SUPPORT DE DESTINATION (design.md § The destination support): the PRINT-SAFE
// build below is the CANONICAL one and it is the one that ships — nobody
// controls what a recipient does with a PDF, and a photocopier is the worst
// case that has to survive. `screen: true` emits the screen-first build of the
// SAME source, for a portfolio page or any other controlled context, and it is
// a SUPPLEMENT on explicit request, never the delivered file.
//
// The two builds are the same document with a re-derived palette, not an
// inversion: each hue keeps its hue and gets its lightness recomputed against
// the real background (the institutional-desktop practice the current was
// harvested from does exactly this, in OKLCH, instead of flipping a dark theme
// to light). Measured on rgb("#1b1d23"): hue A 6.86:1, hue B 7.98:1, body
// 13.70:1, metadata 8.37:1 — every role above the sober floor on its ACTUAL
// background. What does NOT transfer is the gate: on a dark page the whole
// sheet is ink, so the fill measurement and the white-run separation scan have
// nothing to measure. The canonical light build carries those two checks; the
// screen build is validated for contrast and for extraction only (verified
// byte-identical — colour emits no text).
#let screen = false
#let paper = if screen { rgb("#1b1d23") } else { white }
#let accent = if screen { rgb("#b49ad8") } else { rgb("#4d2287") }   // hue A — the CHROME: the gutter rails + the crumb marks
#let accent2 = if screen { rgb("#7ac46e") } else { rgb("#2e6b24") }  // hue B — the LIVE STATE: the drawn marks + the dates
// DUOTONE family (design.md § Duotone). The A→B pairs are validated together,
// never mixed across rows. The role split is harvested, not invented: the
// opinionated-rice configs reserve ONE accent, outside the theme system, for
// active/live modules and leave every other surface on the chrome colour.
#let pal = derive(accent)
#let soft = pal.soft
#let ink = if screen { rgb("#afb8c0") } else { pal.ink }
#let muted = ink
#let dark = if screen { rgb("#e5e8eb") } else { pal.dark }
// The theme SURFACE: a 14% wash of hue A, the light-theme equivalent of the
// chrome panel a bar or a gutter is painted on. A surface, not a colour job —
// the accent budget is unaffected (same construction as mono-technical's wash).
#let wash = color.mix((accent, 14%), (paper, 86%))

// SEGMENT SHAPE — the one variant axis of this family, and it is the harvested
// binary of the tradition: the default bar style is a rounded PILL, the
// opinionated dialect resets every module to a flat SQUARE. An institutional
// desktop makes the same thing one global "corner style" token applied to every
// surface at once, which is why it is ONE knob here and not a per-element
// decision. `pick_design.py` draws it.
#let seg-radius = 2.5pt         // 0pt = square (flat dialect) · 2.5pt = pill

#let bodyf = ("Noto Sans", "Public Sans", "Liberation Sans")
#let dispf = ("Instrument Sans", "Onest", "Geist", "Noto Sans")
// THIRD font role: the BUFFER face. Everything the environment would show as
// machine state sits in the mono — the statusline segments, the dates, the
// skills keys — and nothing else does. The chrome (name, section titles) is the
// UI grotesque, exactly as an editor's own chrome is not monospaced. That
// split is what keeps this family off mono-technical's ground, where the
// headings themselves are mono.
#let monof = ("Red Hat Mono", "Geist Mono", "Noto Sans Mono")

// NO generic pin/phone icon: every mark in the statusline is a PLATFORM mark
// (`mk.pin` / `mk.phone` alongside the four channel logos), in hue B with the
// other data marks. That is the family's icon statement and it is a measured
// one, not a purism: the drawn line-style pin and handset, at the 8.5pt of a
// statusline segment, read as a "C" and a "[" — the vector detail of a 0.9pt
// stroked icon collapses at that size, while the solid path-data marks stay
// legible. The line is marked ALL-OR-NOTHING: city and phone included.
#let ic-col = accent2
#let mk = marks(ic-col)

// GABARIT: uniform — 1.5cm on all four sides. The only family whose margins are
// equal all round, and the reason is the source: a tiling desktop's outer gap
// is one number applied to every edge. Fill target derives from the 1.5cm
// bottom margin: (100 − 5.4) − 0..2%.
#set page(paper: "us-letter", fill: paper, margin: (x: 1.5cm, top: 1.5cm, bottom: 1.5cm))
#set text(font: bodyf, size: 10.5pt, lang: "en", fill: dark, hyphenate: false)
#set par(justify: false, leading: 0.770em, spacing: 0.860em)

// DEVICE: a GUTTER RAIL. Each section carries a 0.9pt hue-A rule running down
// the margin beside it, for exactly the height of that section and no further —
// the gutter/buffer relation of an editor window. A hue-A fold mark sits in
// that gutter beside the title, where an editor puts its fold chevrons and its
// diff signs. Both are `place`d or stroked: they emit no text.
//
// Nobody else in the roster runs a vertical rule beside body content:
// keyline-corporate's keyline hugs the TITLE's own height and carries no mark,
// margin-index puts a whole column beside the body and no rule at all. The
// rail's nameable job (§ Anti-AI-slop) is that it marks the section's vertical
// extent: where a rail stops, the section has stopped, so the white between two
// rails is bracketed by ink at both ends. That is what lets this family sit
// near the separation floor instead of buying its boundary in white.
//
// THE RAIL SITS IN THE MARGIN, and that is a MEASURED requirement, not a
// stylistic one. Drawn at the text edge with the text indented past it (the
// obvious construction: `inset: (left: 11pt)`), the rail blinds the gate's own
// separation instrument: it puts ink on EVERY row of the section body, so the
// intra-section white runs the metric compares the boundary against stop
// existing. Measured, first build of this family: 10 white runs on the whole
// page instead of ~60, median 21.5px, tallest 27px, ratio 1.26 — a FAIL on a
// page whose boundaries are in fact bracketed by ink at both ends. `outset`
// moves the same rail 11pt LEFT of the text, into the margin, where a gutter
// belongs anyway: the text column's rhythm is then measured honestly and the
// rail's separation is a bonus the number understates. Precedent for furniture
// in the margin: margin-index puts a whole title column there. This is NOT
// avant-poster's claim — nothing bleeds off the page edge.
#let crumb = polygon(fill: accent, (0pt, 0pt), (3.6pt, 2.1pt), (0pt, 4.2pt))
#let section(t, body, airy: false) = block(width: 100%, breakable: false,
  above: if airy { 21pt } else { 16pt }, below: 0pt)[
  #block(width: 100%, above: 0pt, below: 0pt, outset: (left: 11pt),
    stroke: (left: 0.9pt + accent))[
    #place(left + top, dx: -8pt, dy: 3.6pt, crumb)
    #text(font: dispf, size: 12.5pt, weight: "bold", fill: dark)[#t]
    #v(4.5pt)
    #body
  ]
]

// Dates in the BUFFER face, hue B, right-flushed: the date is the one datum a
// recruiter checks for recency, which is the CV's own "live state".
//
// The descriptor line under the entry is what keeps the date anchored in the
// extraction (ats.md, orphaned-date trap) — and this family MEASURED a
// refinement of that trap, so the descriptor's face is mechanical here, not
// stylistic. With the descriptor in the 9pt body sans, the education entry's
// "2015 – 2019" still floated to the very end of the extraction even though a
// line of text followed it. The bboxes say why: the descriptor ended at
// x=452.7 while the date ran x=493-569, so the following line never reached
// under the date's x-range and the date stayed its own cluster. The same
// descriptor in the 8pt MONO reaches x=532.6, overlaps the date column, and the
// date extracts in place. Widening the date run itself does NOT fix it
// ("Sep 2015 – Jun 2019" still floated) — it is the FOLLOWING line's horizontal
// reach that anchors the date, which is also what makes the trap look
// position-dependent.
#let job(role, org, dates, note) = entry(role, org, dates, note,
  role-st: it => text(font: dispf, size: 11pt, weight: "bold", it),
  date-st: it => text(font: monof, size: 8.5pt, fill: accent2, weight: "medium", it),
  note-st: it => text(font: monof, size: 8pt, fill: muted, it),
  meta-size: 9pt)

// SKILLS: a FOLD ROW. A drawn hue-B fold triangle, then the key in LOWERCASE
// mono, then the items in the body sans. Lowercase is the point and nobody else
// in the roster has it: an editor's own configuration keys are lowercase, and
// after thirteen families of uppercase / bold / italic / numbered labels it is
// the shape left unused. No colon, no `=`, no separator glyph — the face and
// the case do the separating.
//
// Distinct from mono-technical's `KEY = VALUE` row (uppercase mono key, an `=`
// operator in hue B) and from hard-edge's reversed-out tag. The triangle is a
// drawn box, so it emits no text, and the gaps around it are the paragraph's
// own word spaces: an explicit `h()` is only a trap beside a *painted* run
// (ats.md), but a plain word space is never one.
#let fold = box(width: 4.2pt, height: 4.2pt, baseline: -0.4pt,
  polygon(fill: accent2, (0pt, 0pt), (3.4pt, 2.1pt), (0pt, 4.2pt)))
#let skill(cat, items) = srow(
  [#fold #text(font: monof, size: 8.5pt, weight: "medium")[#lower(cat)]], items)
#let sskill(cat, items) = skill(cat, items)

// List marker: a drawn hue-B VERTICAL BAR — the change sign an editor paints in
// its gutter, and the rail's own shape one scale down (the family repeats its
// vocabulary instead of inventing a second one). Emits no text. The roster's
// other drawn markers are a filled square, an outlined square and a circle.
#set list(marker: box(width: 1.5pt, height: 5.4pt, fill: accent2,
    baseline: -0.6pt), indent: 10pt, spacing: 0.45em, body-indent: 7pt)

// HEADER: a STATUSLINE STRIP first, then the identity. The contacts ride the top
// of the page as a run of discrete segments — the bar of a themed desktop, or
// the statusline of an editor: one module per item, each painted on the theme
// surface, gaps between them.
//
// MECHANICALLY this is the ONE construction that makes a segmented bar legal
// (verified, this page, against the unsegmented line: byte-identical
// extraction). Each segment is a PAINTED chip (`highlight`), never a
// `box(fill:)` — a box per item makes every segment its own text cluster and
// the run scatters (ats.md, lib.typ § chip). The gaps between segments are a
// plain SPACE CHARACTER (`sym.space.quad`, wide enough to read as a gap) and
// never an `h()`: explicit spacing beside a painted run tears it exactly as a
// box does. Each mark+value pair goes through `nb`, so the mark can never be
// orphaned from its value at a line end.
//
// The MARK rides in the gap just before its own field, OUTSIDE the tint, and
// the construction is `nb(mk.x, seg[value])` — the mark outside, the `seg` on
// the value only. `highlight` paints behind a text run and not behind an inline
// image box, so there is no construction that puts a vector mark under the
// paint; MEASURED, the version that wrapped the whole pair (`seg[#nb(mk.x)[…]]`)
// therefore started its tint at the first GLYPH and its `extent: 2.2pt` then
// reached 2.2pt BACK into the icon box — the paint edge cut every mark in half.
// Wrapping only the value puts the whole 2.2pt extent inside the pair's own
// non-breaking space (~5.1pt at 8.5pt mono), so the tint clears the mark by
// ~2.9pt and the mark stays grouped with its own value (the gap to the PREVIOUS
// segment is the wider one: `sym.space.quad` less the extent). Extraction is
// unchanged — verified byte-identical against the wrapped-pair version, since
// `nb`'s box is the same box either way and colour emits no text.
#let seg(b) = chip(b, fill: wash, extent: 2.2pt, radius: seg-radius)
#block(above: 0pt, below: 9pt)[
  #text(font: monof, size: 8.5pt, fill: muted)[#{
    (nb(mk.pin, seg[City, Region]),
     nb(mk.phone, seg[#link("tel:+15555550100")[(555) 555-0100]]),
     nb(mk.mail, seg[#link("mailto:me@example.com")[me\@example.com]]),
     nb(mk.li, seg[#link("https://www.linkedin.com/in/handle/")[linkedin.com/in/handle]]),
     nb(mk.gh, seg[#link("https://github.com/handle")[github.com/handle]])).join([#sym.space.quad])
  }]
  #v(5pt)
  #text(font: dispf, size: 24pt, weight: "bold")[Firstname Lastname]
  #v(-4pt)
  #text(size: 10.5pt, weight: "medium")[Backend Software Developer — B.Sc. in Computer Science]
]

// SECTION ORDER (this family's default): skills-forward hybrid — the profile,
// then the stack, then the full reverse chronology. A target market's own
// convention wins over this default (references/regional.md).

// ---------- Profile ----------
#section("Profile")[
Role and degree in one clause, then the strongest verifiable fact (X years
shipping production code at A, B, C). One sentence covering the stack with
2-3 bolded keywords (*Python/Django*, *TypeScript*, #box[*CI/CD*] — box keeps
fragile tokens unbroken). One closing trait sentence, no clichés
("seeking opportunities…" is dead weight).
]

// ---------- Skills: 5-7 linear rows, every keyword defensible ----------
#section("Skills")[
#skill("Languages", "Python, TypeScript, SQL, JavaScript, Bash")
#skill("Backend & data", "Django, PostgreSQL, REST APIs, message queues")
#skill("Frontend", "React, accessibility-minded interface work")
#skill("Tools & DevOps", "Git (version control), Docker, AWS (EC2 and S3), continuous integration")
#skill("Software quality", "unit and integration testing, test plans, code review")
#skill("Methodologies", "Agile / Scrum, technical documentation")
]

// ---------- Experience in the target field FIRST ----------
#section("Software Development Experience")[

#job("Current Role Title", "Employer", "Mar 2024 – present",
  "City · what the employer is, in one clause · full-time, hybrid")
- Current role in the present tense — every tense convention agrees on that.
- Action verb first; one bolded tech (*Python (Django)*); outcome or scope,
  no invented numbers.
- Contribution verbs (collaborated, strengthened, participated) unless the
  candidate truly owned the outcome — inflated verbs die in interviews.

#job("Earlier Role", "Employer 2", "Jul 2021 – Feb 2024",
  "City · descriptor · full-time, on-site")
- Month+year date ranges always — year-only breaks ATS duration math.
- One strong keyword bolded per bullet, two at most — a wall of bold is none.
]

// ---------- Off-target roles: separated, honest, never leading ----------
#section("Other Professional Experience")[
#job("Off-Target Earlier Role", "Employer 3", "Sep 2019 – Jun 2021",
  "City · descriptor · part-time alongside studies")
- Keep 1-2 transferable bullets; the section label does the explaining.
]

// ---------- Education: the SAME entry shape as the jobs (dates right-flush) ----------
#section("Education")[
#job("Degree Name (Abbrev.)", "Institution", "2015 – 2019",
  "City · anchor unproven-but-real skills here · gloss local institutions for foreign readers")
]

// ---------- Soft skills: only with evidence drawn from this CV ----------
#section("Working Style")[
#sskill("Label", "evidence drawn from the CV itself, never a bare adjective")
#sskill("Mentoring", "onboarded two junior developers — only if a bullet above backs it")
]

// ---------- Languages (spell out the boolean-search words: "bilingual") ----------
#section("Languages")[
Bilingual English / French (fluent) #box[#h(2.5pt)#box(width: 2pt, height: 6pt,
  fill: accent2, baseline: -0.9pt)#h(2.5pt)Third] language (native)
]
