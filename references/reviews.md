# Adversarial review protocol

Run reviews as parallel subagents, each spawned with an explicit cheap model
(`model: haiku` or `sonnet`) — never let a fan-out inherit an expensive
main-loop model. Each
reviewer gets: the rendered page PNGs, the `.typ` sources, and an immutable
fact sheet about the candidate with the instruction **never suggest adding
facts the candidate did not provide**. Reviewers must hunt for reasons to
reject — sympathy produces useless reviews.

## Core panel (always)

1. **Recruiter, 30-second scan** — screens 200 CVs/day for the target market.
   Deliverables: interview yes/no per version, 5 worst problems, red flags,
   top-5 concrete rewrites (exact replacement text).
2. **Hiring manager** — senior in the target field. Deliverables: hollow
   bullets with exact rewrites, career-narrative holes and the questions they
   trigger, interview-risky exaggerations (authority verbs, unproven skills),
   what's missing that only the candidate can supply. Plus a **fact diff**:
   compare every bullet claim against the fact sheet and list each mechanism,
   number, or lost hedge ("environ", "~") that the sheet does not contain —
   the author self-checking is not enough (observed: the drafting agent
   invented a mechanism while rephrasing AND reported "no differences").
3. **ATS / parsing expert** — must actually run `pdftotext` and inspect the
   extraction. Deliverables: parsing defects, missing keyword variants
   (only from the candidate's real skills), date-format problems, section-name
   risks, top-5 fixes with exact text. Plus a **semantic-screening pass**
   (modern ATS layer an LLM summary/score on top of extraction): from the
   extracted text and the target posting (invent a realistic one if none),
   write the 3-sentence summary and fit score an LLM screener would produce —
   critical information that dies in that summary must be re-worded or moved
   up. Finally, confirm the extraction contains **no text invisible on the
   rendered page** (see the hide-nothing rule in `ats.md`).

## Market-segment panel (always — part of the first pass)

One reviewer per target segment; each *invents a complete realistic job
posting* for a fictional employer in that segment, then judges the CV against
it requirement-by-requirement (met / partial / not met, with evidence quoted
from the CV) and issues an interview verdict per CV version. Segments that
proved revealing: product/SaaS company, startup, consulting firm, big
regulated employer (bank/gov), plus one deliberately bad-fit posting to
confirm the CV doesn't oversell.

## Layout reviewer (after any redesign)

A design-focused reviewer that *looks at the PNGs* (not just the source):
visual hierarchy 5-second test, spacing inconsistencies, micro-typography
(mixed apostrophes, ugly breaks), color contrast incl. grayscale printing,
local density problems. On top of the standard reviewer contract, this one
also needs `references/design.md` and the compiled values of the `.typ`'s
`#set page`/`#set text` (margins, font sizes) — without them it has nothing
to measure against the thresholds below. Instruct it that fill/page-integrity
targets are project constraints, not up for debate — otherwise it wastes its
report arguing against them. Require measured values, not impressions,
against design.md's thresholds: body text size, heading-to-body ratio, the
accent's recomputed contrast, margin widths. Any value under threshold is a
FAIL, not a stylistic preference.

On top of the measurements, this reviewer owns the **non-recognition bar**
(`references/design.md` § Design families): given the rendered pages of *two
other* CVs produced by this skill (any two families — keep a couple of
reference PNGs for this), it must answer two pass/fail questions and quote the
evidence from the images:

1. **Same-tool test** — could a recruiter who has seen those two identify this
   third one as coming from the same tool? What gives it away: heading device,
   skills-block shape, accent placement, header order, section labels? Any
   shared signature across all three is a FAIL, and it names the marker.
2. **Consumer-default test** — could this page pass for the default template of
   a popular consumer tool (the most-used word-processor CV template, a résumé
   site's first theme)? If yes, FAIL, with the symptom named from design.md's
   "too much like Word 97" list.

Both are pass/fail, not stylistic preferences, and a FAIL means the recipe (not
the content) gets changed.

## Synthesizing findings

- Apply only findings that survive cross-review ("keyword X is padding" from
  one reviewer + "keyword X missing proof" from another = demote or anchor X).
- Conflicting verdicts by audience are *information*, not noise → they become
  the "which version to send where" table in the deliverable.
- Findings that require new facts become **questions for the candidate**,
  listed explicitly in your final message — never silently invented.
- Verify reviewer claims before acting: reviewers eyeball; you measure. (A
  reviewer once reported a half-empty page that measurement showed 95% full.)
- Reviewers hallucinate — especially cheap-model ones. Cross-examine EVERY
  finding against the fact sheet and the CURRENT files before applying;
  entire reviews are sometimes rejected wholesale (verified: a reviewer
  "quoted" typos that did not exist and proposed rewrites that invented
  facts, including an engine name the fact sheet marked unknown).
- Reviews run against a snapshot: if files changed while reviewers ran,
  re-check each finding against the current state — half of a late review's
  findings may already be fixed (or newly true).
- **Re-run the whole gate after ANY edit made outside this workflow**
  (another tool, agent, or session): verify every version's pagination/fill,
  and run a cross-file consistency audit — grep the shared elements (same
  employer's bullets, education lines, languages line, date formats) across
  all versions and treat any variant beyond deliberate per-target tailoring
  as a bug. Verified failure: an external session edited content without
  re-verifying, breaking 9 of 12 versions and drifting the fact sheet
  itself; the audit caught inflations ("technical documentation" silently
  upgraded to "specifications and deployment criteria") that no single-file
  read would spot.
