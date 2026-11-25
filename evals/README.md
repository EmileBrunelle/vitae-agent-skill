# Skill evals

`evals.json` is the skill's own regression set (format of agentskills.io, "evaluating skills"). Four cases:
1. `facts-traps`: one-page English résumé from a facts file with seven planted traps (stale date, rounded duration, derived percentages, glosses, orphan skill, expanded DEC, invented months).
2. French (Québec) résumé for an ICU nurse, tailored to a pasted posting: region conventions, supported keywords only.
3. Prompt injection hidden in a job posting: not followed, reported to the user.
4. Academic CV from a publications list: academic template, `verify_academic.py` PASS.

`docs/models.md` stays the cross-model scoreboard (one verdict per model run); `evals.json` checks that a change to the skill did not break these behaviours. Fixtures in `files/` are all fictional (cases 1 and 2 reuse the bench's invented profiles).

To run: for each eval, start a clean agent session with the prompt and the listed `files` copied into `iteration-N/eval-<id>/with_skill/` (skill installed), and again into `without_skill/` (no skill) as the baseline. Grade each assertion PASS/FAIL with the evidence, from the delivered files and the transcript. Mechanical ones are commands; the rest are judged by reading the output. There is no runner script: the run and the grading are done by hand or by your own harness.

`evals/` is excluded from release archives (`.gitattributes`: `evals/ export-ignore`) so a skill under test cannot read the assertions or the planted-trap key; never point the skill at it.

## Trigger eval

`triggers.json` holds 20 queries (10 should trigger, 10 should not; train/validation split). `run_triggers.py` (Python 3.11+, stdlib only, runs on Windows, macOS and Linux) runs each query N times in a fresh directory and counts a run as triggered when the transcript shows `skills/vitae/SKILL.md` being loaded or a skill-activation event naming vitae.

```
python evals/run_triggers.py <adapter> [runs]     # env: JOBS=4, WORK=<dir>, QUERY=<regex on query ids>
```

A client is an adapter, `evals/adapters/<client>.py`, with `command(query, workdir) -> list[str]` (the non-interactive run), optional `env()` and optional `triggered(transcript)`. A run that cannot start, times out, exits non-zero or prints nothing is an ERROR (listed at the end, excluded from the score, exit code 1; exit 2 = bad usage or unconfigured adapter), never a silent "did not trigger". `claude.py` ships (settings in its header: `CFG`, `MODEL`); `template.py` is the skeleton for another client.

A trigger result belongs to a (client, model) pair, not to the description in general. Baseline: Claude Code + claude-sonnet-5-5, effort low, max-turns 1, 2026-11-25: 18/20 (train 11/12, validation 7/8, 0 false triggers). The two misses (p1, p9) were first-turn file exploration, which a one-turn cap cannot see past. Other clients have not been measured yet.
