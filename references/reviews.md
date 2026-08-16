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

## Market-segment panel (when positioning matters)

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
local density problems. Instruct it that fill/page-integrity targets are
project constraints, not up for debate — otherwise it wastes its report
arguing against them.

## Synthesizing findings

- Apply only findings that survive cross-review ("keyword X is padding" from
  one reviewer + "keyword X missing proof" from another = demote or anchor X).
- Conflicting verdicts by audience are *information*, not noise → they become
  the "which version to send where" table in the deliverable.
- Findings that require new facts become **questions for the candidate**,
  listed explicitly in your final message — never silently invented.
- Verify reviewer claims before acting: reviewers eyeball; you measure. (A
  reviewer once reported a half-empty page that measurement showed 95% full.)
