# Tested platforms and models

This page records how the skill behaved on real platforms and models, so you can pick one with realistic expectations. Every row below is a single run (n=1): treat each verdict as an observation, not a benchmark. All rows used the same test facts file and the pre-release 0.7.1 skill (commit `fcb4498`) unless noted.

## Verdict categories

- `Autonomous`: the agent finished alone, the gate passed at the normal fill target, no fact was invented, and the visual and layout passes caught the real defects.
- `Supervised-<what>`: the agent finished, but a human had to catch or supply something. `Supervised-facts` means the facts file ran out and the agent lowered the fill target (an honest WARN) or left open questions. `Supervised-visual` means a visible layout defect got past the agent's own visual pass.
- `Not recommended`: the run did not converge or misused its tools.

Effort is measured in tool calls and tokens, not minutes, because wall-clock depends on the machine. Where a duration is given, the machine is named next to it.

## Results

| Platform | Model | Skill loaded how | Network / sandbox | Verdict | Gate | Calls / tokens |
|---|---|---|---|---|---|---|
| Codex CLI 0.166.0 (ChatGPT Free login) | account default, unconfirmed | copied into `~/.codex/skills/vitae` | open network (icons fetched) | Supervised-facts | PASS 88-90 (fill 89 %, target lowered from 94-96, facts exhausted) | 40 commands; input 2,904,308 tokens (2,795,264 cached), output 26,441 (17,006 reasoning); about 13 min, host machine not recorded |
| claude.ai web chat | Opus 5.5 | zip import (Settings, Capabilities, Skills) | claude.ai sandbox: pip works, `api.iconify.design` blocked | Supervised-facts | PASS 90-92 (fill 91 %, target lowered, facts exhausted) | tool-call limit hit at step 8, 1 relaunch ("continue"); tokens not recorded |
| ChatGPT Free web | unconfirmed | zip attached to the chat, prompt "read SKILL.md" (no skill import on Free) | offline sandbox, no DNS, no pip; typst abi3 wheel uploaded | Supervised-visual | PASS 85-87 (fill about 86 %, target lowered by the agent) | finished without relaunch; calls/tokens not recorded; used 2 attachments of the Free quota |
| opencode in a container, LM Studio (local) model | Devstral Small 2 (`devstral-small-2-2512`, Q3_K_L, ctx 65536) | skill tool, frozen copy in the container | local, container | Not recommended | final gate replayed externally: FAIL group proximity 2/9 | 98 calls; input 2,895,270 tokens, output 19,329; hit the 1 h timeout; never reached steps 5-8 |
| opencode in the same container, LM Studio (local) model | Gemma 4 12B QAT (`gemma-4-12b-qat`, Q4_0, ctx 65536) | skill tool, frozen copy in the container | local, container | Not rated (abandoned) | none | 7 calls, abandoned after about 30 s; model used the wrong tools |
| Google Gemini (web) | n/a | n/a | n/a | Not supported | n/a | upload accepts only CSV/PY/TXT/MD, so the skill cannot be attached |
| Claude Code on the web (cloud routine) | Sonnet 5.5 | repository skill `.claude/skills/vitae`, named explicitly in the prompt (an older copy preinstalled in the cloud environment loads first otherwise) | cloud sandbox: Google Fonts and Iconify blocked, npm and pip open | Supervised-facts | PASS 88-96 (fill 88 %, target lowered, facts exhausted) | 39 turns, about 4 min; tokens not recorded |
| Google Antigravity CLI (`agy`) in a container | Gemini 3.8 Flash, high (`gemini-3.8-flash-high`) | user skill mounted at `~/.gemini/config/skills/vitae` | open network (icons fetched), container | Supervised-visual | PASS 94-96 (fill 94 %, normal target kept) | 84 tool calls; input 323,992 tokens (plus 5,818,561 cached), output 46,169 (36,201 reasoning); about 9 min, host machine not recorded |

Notes on the rows:

- Codex CLI: no fact was invented; the year-only date was kept as year-only; "expected May 2026" was kept and flagged. It used `--tune` (ceiling 91 % at 1.097 em, restored). Its self visual pass found two ugly line endings but declared the contact line PASS although GitHub sat alone on a second line. The text size was raised to fill the page, larger than in the other runs.
- claude.ai: no fact was invented (it fixed "REST APIs" and "QC" on its own); its visual pass found and fixed widows, the banner and double line spacing. The candidate package was correctly refused because of open questions (the B.Sc. "expected May 2026" and missing facts), as the skill requires. Replaying the gate on the delivery gave the same PASS 90-92; the Profile line spacing was still loose and the contact icons were mixed.
- ChatGPT Free: two relevant questions asked before starting; no fact was invented. Its visual pass marked line-spacing checks PASS while the summary and the second line of a bullet were visibly double-spaced. It replaced the display font with Liberation Sans (the drawn font was absent), generated no icon crops, and ran a compact panel without sub-agents. About 14 % blank space at the bottom of the page.
- Devstral Small 2: steps 0-3 were fine (facts sheet, design pick, `cv.typ` compiled), then it looped at step 4 for about 45 min, oscillating between 2 pages and 86-93 % fill by adding and removing content. It never used `--tune` although the exact command was printed in every FAIL.
- Gemma 4 12B: the skill was loaded, but the model ran Python through a JS execute tool, globbed outside `/work`, then asked the user for the skill path. This is not a configuration defect. A second launch (run13b) never started because the model had been unloaded in LM Studio (0 tool calls); it is not a data point.
- Antigravity CLI: the only run in this series that kept the normal fill target, with skill run 0.7.1 (`ad17556`), not `fcb4498`. No fact was invented and the year-only DEC dates were kept and flagged. It used `--tune`. Its self visual pass reported no defect, but the Summary reads double-spaced next to the bullets (leading 0.942em, under the 1.00em WARN), GitHub sits alone on the second contact line, and the Summary repeats the projects and languages listed further down to fill the page. "Expected May 2026" was kept but not raised as an open question.
- Claude Code on the web: skill 0.7.2 (`2c739dd`). The ratio WARN fired (leading 0.96em / bullets 0.45em = 2.13) and the agent widened the bullet spacing; it refused a 1.097em leading and lowered the fill target with the honest WARN instead, naming the missing facts. It fetched the drawn fonts through npm `@fontsource` when Google Fonts was blocked. Left over: the Profile still reads looser than the bullets at a ratio of exactly 2.00, the contact row mixes two hand-drawn icons with three missing harvested ones, and the Profile repeats numbers from the bullets. A first attempt (run19) silently loaded an older vitae preinstalled under `/root/.claude/skills` by the cloud environment (most likely its cached setup script) instead of the repository copy; it is not graded. If a cloud environment ships its own copy, name the repository copy in the prompt or update the environment.
- The test facts file was thin, which capped the fill at about 86-91 %. "Autonomous" was therefore unreachable in this series: every capable run exhausted the facts and had to lower the target. Enrich the facts file before the next series.
- Earlier runs on skill 0.6.6 and 0.7.0 (a Claude Code Web session cut short, a Vibe run that invented facts and dates, a harness that did not discover the skill, a 503 from the provider) are not graded here: the skill has changed since.

## Route 3: the visual checker

Route 3 is the optional visual pass done by a separate vision model through `scripts/look.py`. Recommendation: use a remote model. Three local models were tried as the checker on five test pages (one control, four with a known defect: low contrast, a clipped icon, a word split by a forced break, an extra gap above a heading), all on an AMD RX 9070 with LM Studio (ROCm), n=1 per page and mode.

| Local model | Completed runs | Defects detected | False FAILs | Verdict |
|---|---|---|---|---|
| Gemma 4 12B QAT | single 2 of 5, per-item 0 of 5 (8 of 10 runs truncated at 16384 tokens, reasoning loop; retries are deterministic) | 0 of 4 | 0 (control correctly all PASS) | not usable: truncates, and missed the one defect it finished on (the split word) |
| Bonsai 27B Q1_0 | 10 of 10, no truncation (single about 8-9.5k tokens, 60-90 s; per-item about 65-71k tokens, 10-11 min) | 1 of 8 defect runs | 7 of 10 runs | not usable |
| Devstral Small 2 Q3_K_L (single call only) | 5 of 5 (10-15 s, about 4.8k tokens) | 0 of 4 | 5 of 5 | not usable: 4 of 5 pages got the byte-identical answer, so it does not look at the page |

Durations above come from the RX 9070 machine. The only local detection (Bonsai on the clipped icon) is not trustworthy, since the same finding also appeared as a false FAIL on the control page. The three models' prompts and settings are in the bench logs, not reproduced here.

## Platform notes

- claude.ai: the skill zip must not contain symlinks. The first import of an archive with symlinks is refused ("Zip file contains a symbolic link"). Fixed in 0.7.1.
- ChatGPT Free: there is no skill import. Attach the zip to the chat and say "read SKILL.md".
- Offline sandbox (no DNS, no pip): upload the typst abi3 wheel and install it with `pip install --no-index`; `python3 scripts/verify.py --doctor` prints the exact command.
- Gemini web: the upload only accepts CSV, PY, TXT and MD files, so the skill cannot be attached. Not supported.
- Antigravity: the CLI (`agy`) finds user skills in `~/.gemini/config/skills/<name>/` (or `<workspace>/.agents/skills/<name>/`). Asked to list its skills, it named only its two built-in ones, yet it loaded vitae as soon as the task called for it. The desktop IDE is not needed.
- Networks that block `api.iconify.design` leave the contact icons mixed or missing; the CV still compiles with plain-text contact URLs.
