"""No broad `except Exception` turns a bug into "nothing found": at every narrowed site the expected
failure is handled as before, and an unexpected bug exception (KeyError) propagates or is reported
with its type, never a silent pass. The guarded calls are replaced by fakes; no network, no PDF."""
import http.client
import subprocess
import types
import urllib.error

import pytest
from vitae import icons
from vitae.core import env
from vitae.verify import layout, text
from vitae.verify.groups import query


def _raiser(exc: BaseException):
    def fn(*_a: object, **_k: object) -> object:
        raise exc
    return fn


class _PyPdfError(Exception):
    """Stands for pypdf.errors.PyPdfError."""


def _fake_pypdf(exc: BaseException) -> types.SimpleNamespace:
    return types.SimpleNamespace(errors=types.SimpleNamespace(PyPdfError=_PyPdfError), PdfReader=_raiser(exc))


class TestIcons:
    @pytest.mark.parametrize("exc", [urllib.error.URLError("dns"), TimeoutError("slow"), ValueError("bad json"),
                                     http.client.BadStatusLine("x")])
    def test_network_and_parse_failures_degrade_with_a_message(self, monkeypatch, capsys, exc):
        monkeypatch.setattr(icons, "fetch", _raiser(exc))
        assert icons.fetch_set("lucide", ["mail"]) == ({}, {})
        assert "WARN  ICONS: lucide unreachable" in capsys.readouterr().err

    def test_deeply_nested_json_degrades_with_a_message(self, monkeypatch, capsys):
        class Reply:
            def __enter__(self) -> "Reply":
                return self

            def __exit__(self, *_a: object) -> None: ...

            def read(self, _n: int) -> bytes:
                return b"[" * 100_000   # nested far past the interpreter's recursion limit

        monkeypatch.setattr(icons.urllib.request, "urlopen", lambda *a, **k: Reply())
        assert icons.fetch_set("lucide", ["mail"]) == ({}, {})
        assert "WARN  ICONS: lucide unreachable" in capsys.readouterr().err

    def test_a_bug_is_not_swallowed(self, monkeypatch):
        monkeypatch.setattr(icons, "fetch", _raiser(KeyError("boom")))
        with pytest.raises(KeyError):
            icons.fetch_set("lucide", ["mail"])


class TestPdfCharFonts:
    @pytest.fixture(autouse=True)
    def _pdfium_present(self, monkeypatch):
        monkeypatch.setattr(layout, "importable", lambda name: True)
        monkeypatch.setattr(layout.importlib, "import_module", lambda name, *a: object())

    @pytest.mark.parametrize("exc", [OSError("gone"), RuntimeError("PdfiumError: bad file"), ImportError("libpdfium")])
    def test_unreadable_pdf_reads_as_cannot_check(self, monkeypatch, exc):
        monkeypatch.setattr(layout, "pdfium_doc", _raiser(exc))
        assert layout.pdf_char_fonts("x.pdf") is None

    def test_a_bug_in_the_scan_raises_instead_of_a_clean_gate(self, monkeypatch):
        monkeypatch.setattr(layout, "pdfium_doc", _raiser(KeyError("boom")))
        with pytest.raises(KeyError):
            layout.pdf_char_fonts("x.pdf")


class TestQueryValuesPy:
    def _mod(self, monkeypatch, *, compiler_exc: BaseException | None = None, query_exc: BaseException | None = None):
        class Compiler:
            def __init__(self, *_a: object, **_k: object) -> None:
                if compiler_exc:
                    raise compiler_exc

            def query(self, *_a: object, **_k: object) -> object:
                raise query_exc or RuntimeError("no")

            def eval(self, *_a: object, **_k: object) -> object:
                return '[1, 2]'
        monkeypatch.setattr(query, "typst_py", lambda: types.SimpleNamespace(Compiler=Compiler))

    def test_failing_first_route_falls_back_to_eval(self, monkeypatch):
        self._mod(monkeypatch, query_exc=RuntimeError("selector matched nothing"))
        assert query._values_py("a.typ", "<x>", None) == [1, 2]

    def test_a_wheel_whose_query_lacks_field_goes_straight_to_eval(self, monkeypatch):
        """The signature fallback is a recorded capability, not a swallowed TypeError: a TypeError would be a bug."""
        self._mod(monkeypatch, query_exc=TypeError("would be a bug if called"))
        monkeypatch.setattr(query, "typst_route", lambda: env.TypstRoute("api", "api", None, env.TypstPyCaps(query_field=False)))
        assert query._values_py("a.typ", "<x>", None) == [1, 2]

    def test_compiler_refusing_the_source_is_not_readable(self, monkeypatch):
        self._mod(monkeypatch, compiler_exc=RuntimeError("syntax error"))
        assert query._values_py("a.typ", "<x>", None) is None

    def test_a_bug_in_a_route_raises(self, monkeypatch):
        self._mod(monkeypatch, query_exc=KeyError("boom"))
        with pytest.raises(KeyError):
            query._values_py("a.typ", "<x>", None)

    def test_a_bug_in_compiler_setup_raises(self, monkeypatch):
        self._mod(monkeypatch, compiler_exc=KeyError("boom"))
        with pytest.raises(KeyError):
            query._values_py("a.typ", "<x>", None)


@pytest.mark.usefixtures("fresh_typst_probes")
class TestEnv:
    def test_platform_tag_falls_back_when_packaging_is_absent(self, monkeypatch):
        monkeypatch.setattr(env.importlib, "import_module", _raiser(ImportError("no packaging")))
        assert env._wheel_platform_tag()   # sysconfig fallback, never empty

    def test_platform_tag_bug_raises(self, monkeypatch):
        monkeypatch.setattr(env.importlib, "import_module", _raiser(KeyError("boom")))
        with pytest.raises(KeyError):
            env._wheel_platform_tag()

    @pytest.mark.parametrize("fake", [_raiser(OSError("exec")), _raiser(subprocess.TimeoutExpired("typst", 1)),
                                      lambda *a, **k: types.SimpleNamespace(stdout="typst")])
    def test_unreadable_cli_version_is_not_fatal(self, monkeypatch, capsys, fake):
        monkeypatch.setattr(env.shutil, "which", lambda n, *a, **k: "/bin/typst" if n == "typst" else None)
        monkeypatch.setattr(env.subprocess, "run", fake)
        env.check_typst()   # prints a verdict line, does not raise
        assert capsys.readouterr().out

    def test_cli_version_bug_raises(self, monkeypatch):
        monkeypatch.setattr(env.shutil, "which", lambda n, *a, **k: "/bin/typst")
        monkeypatch.setattr(env.subprocess, "run", _raiser(KeyError("boom")))
        with pytest.raises(KeyError):
            env.check_typst()

    def _probe(self, monkeypatch, *, eval_exc: BaseException | None = None, fonts_exc: BaseException | None = None,
               has_eval: bool = True):
        class Compiler:
            def __init__(self, *_a: object, **_k: object) -> None: ...

            def compile_with_warnings(self) -> tuple[bytes, list[object]]:
                return b"%PDF-1.7", []

            def query(self) -> None: ...

            def eval(self, *_a: object, **_k: object) -> str:
                if eval_exc:
                    raise eval_exc
                return '"0.15.0"'

        if not has_eval:
            del Compiler.eval   # typst-py 0.13.4-0.14.x
        mod = types.SimpleNamespace(
            Compiler=Compiler, __version__="9.9",
            Fonts=_raiser(fonts_exc) if fonts_exc else lambda **k: types.SimpleNamespace(families=lambda: ["A"]))
        monkeypatch.setattr(env.importlib, "import_module", lambda name, *a: mod)
        env._typst_py_probe.cache_clear()
        try:
            p = env._typst_py_probe()
            return p.module, p.version, p.problem, p.full
        finally:
            env._typst_py_probe.cache_clear()

    def test_probe_ok(self, monkeypatch):
        mod, ver, problem, full = self._probe(monkeypatch)
        assert (mod is not None, ver, problem, full) == (True, "0.15.0", "", True)

    def test_eval_failure_keeps_module_version(self, monkeypatch):
        _, ver, problem, full = self._probe(monkeypatch, eval_exc=RuntimeError("no eval"))
        assert (ver, problem, full) == ("9.9", "", True)

    def test_compiler_without_eval_is_degraded_not_broken(self, monkeypatch, capsys):
        mod, ver, problem, full = self._probe(monkeypatch, has_eval=False)
        assert mod is not None and problem == "" and full is False and ver == "9.9"
        monkeypatch.setattr(env.shutil, "which", lambda n, *a, **k: None)
        monkeypatch.setattr(env, "_typst_py_probe", lambda: env.TypstPyProbe(mod, ver, problem, full))
        assert env.check_typst() is True
        out = capsys.readouterr().out
        assert out.startswith("DEGRADED") and "BROKEN" not in out

    def test_eval_signature_mismatch_keeps_module_version(self, monkeypatch):
        _, ver, problem, full = self._probe(monkeypatch, eval_exc=TypeError("unexpected keyword 'format'"))
        assert (ver, problem, full) == ("9.9", "", True)

    def test_fonts_failure_leaves_compile_only(self, monkeypatch):
        mod, _, problem, full = self._probe(monkeypatch, fonts_exc=RuntimeError("no fonts"))
        assert mod is not None and problem == "" and full is False

    @pytest.mark.parametrize("kw", [{"eval_exc": KeyError("boom")}, {"fonts_exc": KeyError("boom")}])
    def test_probe_bug_is_reported_as_the_problem_not_hidden(self, monkeypatch, kw):
        mod, _, problem, full = self._probe(monkeypatch, **kw)
        assert mod is None and full is False and "KeyError" in problem

    def test_typst_fonts_failure_is_none_and_bug_raises(self, monkeypatch):
        monkeypatch.setattr(env.shutil, "which", lambda n, *a, **k: None)
        monkeypatch.setattr(env, "typst_py", lambda: types.SimpleNamespace(Fonts=_raiser(RuntimeError("x"))))
        assert env.typst_fonts() is None
        monkeypatch.setattr(env, "typst_py", lambda: types.SimpleNamespace(Fonts=_raiser(KeyError("boom"))))
        with pytest.raises(KeyError):
            env.typst_fonts()


class TestTextGates:
    @pytest.fixture(autouse=True)
    def _pypdf_route(self, monkeypatch):
        monkeypatch.setattr(text, "pdf_backend", lambda: None)
        monkeypatch.setattr(text.shutil, "which", lambda n, *a, **k: None)

    def _use(self, monkeypatch, exc: BaseException):
        monkeypatch.setattr(text.importlib, "import_module", lambda name, *a: _fake_pypdf(exc))

    @pytest.mark.parametrize("exc", [OSError("gone"), ValueError("bad"), _PyPdfError("corrupt")])
    def test_unreadable_pdf_gives_no_metadata_finding(self, monkeypatch, exc):
        self._use(monkeypatch, exc)
        assert text.check_pdf_metadata("x.pdf") == []

    @pytest.mark.parametrize("exc", [NotImplementedError("encrypted"), KeyError("boom")])
    def test_metadata_pypdf_crash_is_a_visible_warn(self, monkeypatch, exc):
        self._use(monkeypatch, exc)
        assert text.check_pdf_metadata("x.pdf") == [
            f"metadata pypdf scan failed: {type(exc).__name__} — metadata not checked"]

    def test_missing_pypdf_means_no_metadata_finding_and_runs_not_run(self, monkeypatch):
        monkeypatch.setattr(text.importlib, "import_module", _raiser(ImportError("pypdf")))
        assert text.check_pdf_metadata("x.pdf") == []
        assert text._text_runs("x.pdf") == ([], [], False, "")

    @pytest.mark.parametrize("exc", [OSError("gone"), ValueError("bad"), _PyPdfError("corrupt")])
    def test_unreadable_pdf_still_counts_as_ran_found_nothing(self, monkeypatch, exc):
        self._use(monkeypatch, exc)
        assert text._text_runs("x.pdf") == ([], [], True, "")

    @pytest.mark.parametrize("exc", [NotImplementedError("unsupported"), KeyError("boom")])
    def test_text_runs_pypdf_crash_is_reported_not_a_clean_pass(self, monkeypatch, exc):
        self._use(monkeypatch, exc)
        assert text._text_runs("x.pdf") == ([], [], False, type(exc).__name__)

    def test_pypdf_rejecting_a_readable_pdf_is_reported_not_a_clean_pass(self, monkeypatch):
        monkeypatch.setattr(text, "pdf_unreadable", lambda pdf: False)
        self._use(monkeypatch, _PyPdfError("LZW stream corrupt"))
        assert text._text_runs("x.pdf") == ([], [], False, "_PyPdfError")

    def test_hidden_text_gate_warns_when_the_pypdf_scan_crashed(self, monkeypatch):
        self._use(monkeypatch, NotImplementedError("unsupported"))
        monkeypatch.setattr(text, "boxes_unavailable", lambda pdf: "")
        monkeypatch.setattr(text, "bbox_pages", lambda pdf: [])
        monkeypatch.setattr(text, "render_pages_png", lambda *a, **k: [])
        monkeypatch.setattr(text, "check_pdf_metadata", lambda pdf: [])
        msgs = text.check_hidden_text("x.pdf")
        assert any(lvl is text.Level.WARN and m.startswith("hidden-text pypdf scan failed: NotImplementedError")
                   for lvl, m in msgs)
        assert not any("PASS" in m or "no hidden" in m for _, m in msgs)
