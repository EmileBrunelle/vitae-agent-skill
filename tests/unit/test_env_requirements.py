"""The doctor reads its install advice from the PEP 723 header of the script being run: one place declares the dependencies."""
import pathlib
import re

from vitae.core import env

SAMPLE = '''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["typst==9.8.7", "pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'"]
# ///
"""Docstring."""
'''
SCRIPTS = pathlib.Path(env.__file__).resolve().parents[2]
ROOT = SCRIPTS.parent


def test_parses_the_dependencies_markers_included():
    assert env.pep723_requirements(SAMPLE) == (
        "typst==9.8.7", "pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'")


def test_no_block_means_no_requirements():
    assert env.pep723_requirements("print('x')\n") == ()


def test_requirement_is_read_from_the_running_script_header(monkeypatch):
    monkeypatch.setattr(env, "script_requirements", lambda name: env.pep723_requirements(SAMPLE))
    assert env.requirement("TYPST") == "typst==9.8.7"
    assert env.requirement("nothing") == "nothing"
    assert env._pip("pikepdf").startswith('pip install "pikepdf>=10.8.0; sys_platform')


def test_the_three_verify_facades_declare_the_same_dependencies():
    deps = {n: env.script_requirements(n) for n in ("verify.py", "verify_letter.py", "verify_academic.py")}
    assert deps["verify.py"] and len(set(deps.values())) == 1


def _typst_range() -> tuple[str, str]:
    """(lower, upper) bounds of the `typst>=X,<Y` range declared in verify.py's header."""
    (req,) = [r for r in env.script_requirements("verify.py") if r.startswith("typst")]
    m = re.fullmatch(r"typst>=(\d+\.\d+\.\d+),<(\d+\.\d+)", req)
    assert m, f"typst must be a compatible range `typst>=X.Y.Z,<X.(Y+1)`, got {req!r}"
    return m.group(1), m.group(2)


def test_typst_min_is_the_range_lower_bound_and_the_upper_is_the_next_minor():
    lower, upper = _typst_range()
    major, minor = (int(x) for x in lower.split(".")[:2])
    assert env.TYPST_MIN == (major, minor)
    assert upper == f"{major}.{minor + 1}"
    (req,) = [r for r in env.script_requirements("verify.py") if r.startswith("typst")]
    assert env.script_requirements("pick_design.py") == (req,)


def test_doctor_advice_quotes_the_typst_range(monkeypatch):
    monkeypatch.setattr(env, "_running_script", lambda: "verify.py")
    lower, upper = _typst_range()
    assert env._pip("typst") == f'pip install "typst>={lower},<{upper}"'


_DOC_FILES = [ROOT / "README.md", ROOT / "README.fr.md", *sorted((ROOT / "references").rglob("*.md"))]
_PIP_TYPST = re.compile(r"pip (install|download)\b([^`\n]*)")


def _typst_pip_specs() -> list[tuple[str, str, str]]:
    """(file, verb, typst specifier) for every `pip install|download ... typst...` command in the docs."""
    found = []
    for path in _DOC_FILES:
        for m in _PIP_TYPST.finditer(path.read_text(encoding="utf-8")):
            found.extend((path.name, m.group(1), tok) for tok in re.findall(r"\"?(typst[^\s\"]*)\"?", m.group(2)))
    return found


def test_documented_pip_commands_use_the_header_typst_range():
    lower, upper = _typst_range()
    specs = _typst_pip_specs()
    assert specs, "no `pip install typst` command found in the docs: the regex is stale"
    bad = []
    for name, verb, spec in specs:
        if verb == "download":
            ok = spec.startswith("typst==") and _in_range(spec.removeprefix("typst=="), lower, upper)
        else:
            ok = spec == f"typst>={lower},<{upper}"
        if not ok:
            bad.append(f"{name}: pip {verb} {spec}")
    assert not bad, "docs disagree with the verify.py header range:\n" + "\n".join(bad)


def _in_range(version: str, lower: str, upper: str) -> bool:
    def key(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))
    return key(lower) <= key(version) < key(upper)


def test_uv_line_names_the_script_by_absolute_path(monkeypatch):
    """The doctor runs from the user's project dir: a relative `scripts/...` path would not exist there."""
    monkeypatch.setattr(env, "_running_script", lambda: "verify.py")
    line = env._uv_line()
    assert str(SCRIPTS / "verify.py") in line
    assert "uv run scripts/" not in line and "..." not in line.split("#")[0]


def test_pip_requirement_with_markers_is_double_quoted(monkeypatch):
    monkeypatch.setattr(env, "script_requirements", lambda name: env.pep723_requirements(SAMPLE))
    assert env._pip("pikepdf") == (
        "pip install \"pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'\"")


def test_pip_requirement_with_a_shell_special_falls_back_to_shlex(monkeypatch):
    monkeypatch.setattr(env, "script_requirements", lambda name: ("foo>=1; extra == \"$x\"",))
    assert env._pip("foo") == "pip install " + env.shlex.quote('foo>=1; extra == "$x"')


def test_invalid_toml_in_the_header_means_no_requirements():
    bad = "# /// script\n# dependencies = [\n# ///\n"
    assert env.pep723_requirements(bad) == ()


def test_a_non_utf8_script_means_no_requirements(monkeypatch, tmp_path):
    (tmp_path / "bad.py").write_bytes(b"# \xff\xfe\n")
    monkeypatch.setattr(env, "_SCRIPTS_DIR", tmp_path)
    env.script_requirements.cache_clear()
    try:
        assert env.script_requirements("bad.py") == ()
    finally:
        env.script_requirements.cache_clear()
