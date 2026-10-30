# Step 7 — Adversarial review

7. **Adversarial review.** Never deliver without this pass — a mechanical
   PASS is not a review. Run `references/reviews.md`: 3 core reviewers plus
   one per target market segment (recruiter 30-second scan, hiring manager of
   the field, ATS expert, plus one per segment with an invented but realistic
   posting) — the market-segment reviewers are part of this FIRST pass, not
   an optional later round. Spawn every reviewer on the cheapest model your
   runtime offers — a fan-out inheriting an expensive main-loop model burns
   budget fast. If your runtime has no subagents, run the personas one at a
   time in the main session, clearing between them: the review is mandatory,
   the parallelism is not. **Compact path** (no parallel subagents, tight budget
   or small model): skip the full panel; run, sequentially in ONE pass yourself,
   only the ATS/fact-diff check and the hiring-manager read from
   `references/reviews.md`, each ≤5 findings; fix, then re-run step 6. Never
   shrink the default path for a capable runtime. Give them rendered PNGs *and* sources. Apply only
   findings that survive cross-examination; findings demanding invented
   facts become questions for the user. After applying findings, go back
   through step 6 before delivering. Once that final PASS holds, write the
   manifest: `sha256sum *.typ > .vitae-manifest` — the trigger for the
   external-edit trap in `references/steps/0-env.md`.
