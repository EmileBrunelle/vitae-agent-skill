"""The doctor reads its install advice from the PEP 723 header of the script being run: one place declares the dependencies."""
import pathlib

from vitae.core import env

SAMPLE = '''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["typst==9.8.7", "pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'"]
# ///
"""Docstring."""
'''
SCRIPTS = pathlib.Path(env.__file__).resolve().parents[2]


def test_parses_the_dependencies_markers_included():
    assert env.pep723_requirements(SAMPLE) == (
        "typst==9.8.7", "pikepdf>=10.8.0; sys_platform != 'darwin' or platform_machine != 'x86_64'")


def test_no_block_means_no_requirements():
    assert env.pep723_requirements("print('x')\n") == ()


def test_requirement_is_read_from_the_running_script_header(monkeypatch):
    monkeypatch.setattr(env, "script_requirements", lambda name: env.pep723_requirements(SAMPLE))
    assert env.requirement("TYPST") == "typst==9.8.7"
    assert env.requirement("nothing") == "nothing"
    assert env._pip("pikepdf").startswith("pip install 'pikepdf>=10.8.0; sys_platform")


def test_the_three_verify_facades_declare_the_same_dependencies():
    deps = {n: env.script_requirements(n) for n in ("verify.py", "verify_letter.py", "verify_academic.py")}
    assert deps["verify.py"] and len(set(deps.values())) == 1


def test_typst_min_is_the_pinned_major_minor():
    (pin,) = [r for r in env.script_requirements("verify.py") if r.startswith("typst==")]
    major, minor = pin.removeprefix("typst==").split(".")[:2]
    assert env.TYPST_MIN == (int(major), int(minor))
    assert env.script_requirements("pick_design.py") == (pin,)
