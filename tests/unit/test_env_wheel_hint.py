"""The wheel platform tag behind the offline typst hint: taken from the running interpreter, never a fixed OS/arch."""
import sys
import types

import pytest
import vitae.core.env as verify_env


def _no_packaging(monkeypatch):
    monkeypatch.setitem(sys.modules, "packaging.tags", None)
    monkeypatch.setitem(sys.modules, "pip._vendor.packaging.tags", None)


def test_most_specific_packaging_tag_wins(monkeypatch):
    tags = types.SimpleNamespace(sys_tags=lambda: iter([types.SimpleNamespace(platform="macosx_14_0_arm64"),
                                                        types.SimpleNamespace(platform="macosx_13_0_arm64")]))
    monkeypatch.setitem(sys.modules, "packaging.tags", tags)
    assert verify_env._wheel_platform_tag() == "macosx_14_0_arm64"


def test_falls_back_to_pip_vendored_packaging(monkeypatch):
    tags = types.SimpleNamespace(sys_tags=lambda: iter([types.SimpleNamespace(platform="win_amd64")]))
    monkeypatch.setitem(sys.modules, "packaging.tags", None)
    monkeypatch.setitem(sys.modules, "pip._vendor.packaging.tags", tags)
    assert verify_env._wheel_platform_tag() == "win_amd64"


@pytest.mark.parametrize("platform, tag", [
    ("linux-aarch64.x", "linux_aarch64_x"),     # dashes and dots both become underscores
    ("linux-x86_64", "linux_x86_64"),
    ("win-amd64", "win_amd64"),
    ("macosx-14.0-arm64", "macosx_14_0_arm64"),
    ("already_ok", "already_ok"),
], ids=["dash-and-dot", "linux", "windows", "macos", "unchanged"])
def test_platform_tag_fallback_is_normalised(monkeypatch, platform, tag):
    _no_packaging(monkeypatch)
    monkeypatch.setattr(verify_env.sysconfig, "get_platform", lambda: platform)
    assert verify_env._wheel_platform_tag() == tag
