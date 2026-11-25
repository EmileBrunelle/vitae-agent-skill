"""Adapter template: copy to evals/adapters/<client>.py, then
`python evals/run_triggers.py <client> [runs]`.

Document here the env vars the adapter reads (config dir, model, ...). The skill must be
installed where the client loads skills from, in an isolated config so no other skill
competes, and the run must be non-interactive.
"""

from pathlib import Path


def command(query: str, workdir: Path) -> list[str]:
    """argv that runs the client once, non-interactively, with `query` as the prompt.

    It runs with `workdir` (a fresh directory) as cwd; stdout and stderr are captured as the
    transcript. Fill in your client's non-interactive command (ideally one that logs tool
    calls or file reads) and, if it allows, a turn cap. argv[0] must be resolvable on PATH (it
    is looked up with shutil.which, so Windows .cmd shims work). A non-zero exit, a timeout or
    empty stdout makes the run an ERROR (excluded from the score, exit code 1), not "no trigger".
    """
    raise NotImplementedError("fill in your client's non-interactive command")


def env() -> dict[str, str | None]:
    """Optional: overrides for the child environment (None unsets a variable). Read required
    settings with os.environ[...]: a KeyError aborts the eval up front with a clear message."""
    return {}


def triggered(transcript: str) -> bool:
    """Optional: custom detection. Without it the core looks for skills/vitae/SKILL.md
    (either path separator) or a skill-activation event naming vitae."""
    raise NotImplementedError
