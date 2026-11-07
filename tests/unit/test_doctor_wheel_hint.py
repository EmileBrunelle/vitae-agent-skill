"""The offline typst-wheel hint names the running platform tag and Python version, never a fixed OS/arch."""
import sys

import verify_env


def test_hint_uses_detected_platform_and_python(monkeypatch, capsys):
    monkeypatch.setattr(verify_env, "_wheel_platform_tag", lambda: "macosx_14_0_arm64")
    monkeypatch.setattr(verify_env, "_typst_py_probe", lambda: (None, "", "", False))
    monkeypatch.setattr(verify_env.shutil, "which", lambda _n: None)
    verify_env.check_typst()
    out = capsys.readouterr().out
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert f"--platform macosx_14_0_arm64 --python-version {pyver}" in out
    assert "x86_64" not in out and "manylinux" not in out
    assert "pip debug --verbose" in out


def test_platform_tag_fallback_is_normalised(monkeypatch):
    monkeypatch.setitem(sys.modules, "packaging.tags", None)
    monkeypatch.setitem(sys.modules, "pip._vendor.packaging.tags", None)
    monkeypatch.setattr(verify_env.sysconfig, "get_platform", lambda: "linux-aarch64.x")
    assert verify_env._wheel_platform_tag() == "linux_aarch64_x"
