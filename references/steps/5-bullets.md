# Step 5 — Write bullets

5. **Write bullets.** Action verb first (mood/tense per region; current role in
   present tense in every tense-based convention), one strong keyword bolded
   per bullet (max two), no authority inflation: *led / owned / guaranteed*
   only where the candidate truly had final responsibility — otherwise
   *contributed / collaborated / strengthened*. Contribution verbs survive
   interviews; inflated ones die there. Before moving on, diff every bullet
   against the fact sheet: any number, technology, mechanism, or hedge
   ("environ", "~") that differs from what the candidate said gets reverted
   or flagged — embellishing while rephrasing is the most common rule-1
   violation, and it survives every mechanical check. **Aim each bullet at one
   line** wherever the honest content allows it — that is what the 30-second
   scan reads; two lines are fine for a bullet that earns them, three means
   the bullet is two bullets. Never force a line break (`\ `) inside a bullet
   to fix spacing or fill — `verify.py` FAILs it (`check_forced_linebreak`). A section title and a row label never share a name (spoken "Languages" vs programming "Languages") — `check_duplicate_names` FAILs it.
   Prose (the Profile) wraps freely: that is its job. The Profile carries what
   Skills can't (level, domain, outcome) and never re-lists technologies the
   Skills section already names. The hard half of this rule — structured lines never wrap — is checked
   on the render in step 6 (design.md § Line integrity).
