"""--tune robustness: the rule's comments survive, line endings and the original survive every exit,
rhythm edge values, and which `#let rhythm` line is edited. The probe is injected (fake page height
`50 * rhythm + 50 * leading`)."""
import os
import re
import signal

import pytest
from vitae.verify import pdf as pdf_module
from vitae.verify import tune as T
from vitae.verify.typst import _read_par, _read_rhythm, _rhythm_unparsed, _write_par, _write_rhythm

pytestmark = pytest.mark.usefixtures("tuner_original_compiles")

BODY = "#set par(leading: 0.500em, spacing: 0.600em)\n#set list(spacing: 0.400em)\nbody\n"
BASE = "#let rhythm = 1.000\n" + BODY


def install(monkeypatch, *, breakat=1000.0, raise_at=None, log=None, raise_if=None):
    monkeypatch.setattr(T, "preflight", lambda: (True, "pypdf"))
    n = [0]

    def probe(typ, candidate, expected, backend):
        T._write(typ, candidate)
        n[0] += 1
        if log is not None:
            log.append(candidate)
        if (raise_at is not None and n[0] == raise_at) or (raise_if and raise_if(candidate)):
            raise KeyboardInterrupt
        r = _read_rhythm(candidate) or 1.0
        par = _read_par(candidate)
        assert par is not None
        h = 50 * r + 50 * par[0]
        return (True, round(h)) if h <= breakat else (False, None)
    monkeypatch.setattr(T, "_probe_text", probe)


def put(tmp_path, text):
    p = tmp_path / "cv.typ"
    p.write_bytes(text.encode())
    return p


def test_write_par_keeps_comment_inside_rule():
    src = "#set par(leading: 0.500em, // tight\n  spacing: 0.600em)\nx\n"
    out = _write_par(src, 0.7, 0.8)
    assert out == "#set par(leading: 0.700em, // tight\n  spacing: 0.800em)\nx\n"


def test_tune_keeps_comment_in_par_rule(tmp_path, monkeypatch):
    p = put(tmp_path, "#set par(leading: 0.500em, // tight\n  spacing: 0.600em)\n" + BODY.split("\n", 1)[1])
    install(monkeypatch)
    code, _ = T.tune(str(p), 1, 74, 76)
    assert code == 0 and "// tight\n" in p.read_text()


def test_crlf_preserved_on_success_and_failure(tmp_path, monkeypatch):
    crlf = BASE.replace("\n", "\r\n")
    p = put(tmp_path, crlf)
    install(monkeypatch)
    assert T.tune(str(p), 1, 74, 76)[0] == 0
    out = p.read_bytes()
    assert b"\r\n" in out and out.replace(b"\r\n", b"").count(b"\n") == 0
    assert _read_rhythm(out.decode()) is not None
    p2 = put(tmp_path, crlf)
    install(monkeypatch, breakat=97)
    assert T.tune(str(p2), 1, 99, 100)[0] == 1
    assert p2.read_bytes() == crlf.encode()


@pytest.mark.parametrize("zero", ["0", "0.000"])
def test_rhythm_zero_is_a_user_error(tmp_path, monkeypatch, capsys, zero):
    text = BASE.replace("1.000", zero)
    p = put(tmp_path, text)
    install(monkeypatch)
    code, _ = T.tune(str(p), 1, 90, 96)
    out = capsys.readouterr().out
    assert code == 2 and "rhythm" in out and "Traceback" not in out
    assert p.read_bytes() == text.encode()


def test_current_rhythm_below_floor_is_the_lower_bound(tmp_path, monkeypatch):
    log = []
    p = put(tmp_path, BASE.replace("1.000", "0.800"))
    install(monkeypatch, log=log)
    T.tune(str(p), 1, 60, 62)
    assert min(_read_rhythm(c) or 9 for c in log) <= 0.8 + 1e-9
    assert _read_rhythm(log[0]) == pytest.approx(0.8)


def test_floor_failure_keeps_original_as_candidate(tmp_path, monkeypatch):
    # pages hold only for rhythm >= 0.88 (a too-short floor): the original at 0.9 is the fallback
    monkeypatch.setattr(T, "preflight", lambda: (True, "pypdf"))

    def probe(typ, candidate, expected, backend):
        T._write(typ, candidate)
        r = _read_rhythm(candidate) or 1.0
        return (r >= 0.88, round(50 * r + 25) if r >= 0.88 else None)
    monkeypatch.setattr(T, "_probe_text", probe)
    p = put(tmp_path, BASE.replace("1.000", "0.900"))
    code, _ = T.tune(str(p), 1, 69, 71)
    r = _read_rhythm(p.read_text())
    assert code == 0 and r is not None and 0.88 <= r <= 0.93


def test_last_rhythm_line_is_the_edited_one(tmp_path, monkeypatch):
    text = "#let rhythm = 2.000\n" + BASE
    assert _write_rhythm(text, 0.9) == "#let rhythm = 2.000\n#let rhythm = 0.900\n" + BODY
    assert _read_rhythm(text) == 1.0


@pytest.mark.parametrize("line", ["#let rhythm = 1", "#let rhythm = 1.000;", "#let rhythm = 1.000 // base",
                                  "#let rhythm = 1.000;\r"])
def test_rhythm_line_forms_are_read(line):
    assert _read_rhythm(line + "\n" + BODY) == 1.0 and not _rhythm_unparsed(line + "\n" + BODY)


def test_unparsable_rhythm_gets_a_note_not_silence(tmp_path, monkeypatch, capsys):
    text = "#let rhythm = 1.0pt * 2\n" + BODY
    assert _rhythm_unparsed(text) and _read_rhythm(text) is None
    p = put(tmp_path, text)
    install(monkeypatch)
    T.tune(str(p), 1, 74, 76)
    assert "NOTE" in capsys.readouterr().out


@pytest.mark.parametrize("at", [2, 5])
def test_interrupt_in_phase_one_restores_original(tmp_path, monkeypatch, at):
    p = put(tmp_path, BASE.replace("\n", "\r\n"))
    orig = p.read_bytes()
    install(monkeypatch, raise_at=at, breakat=105)
    with pytest.raises(KeyboardInterrupt):
        T.tune(str(p), 1, 106, 108)
    assert p.read_bytes() == orig


def test_interrupt_between_the_phases_restores_original(tmp_path, monkeypatch):
    # the old code opened its try only at phase 2's first probe: an interrupt in the gap (here, at the
    # message printed once phase 1 ends) left the last phase-1 probe in the file
    p = put(tmp_path, BASE)
    orig = p.read_bytes()
    install(monkeypatch)

    def boom(*args: object) -> None:
        if str(args[0]).startswith("tuning "):
            raise KeyboardInterrupt
    monkeypatch.setattr(T, "print", boom, raising=False)
    with pytest.raises(KeyboardInterrupt):
        T.tune(str(p), 1, 106, 108)
    assert p.read_bytes() == orig


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP])
def test_termination_signal_mid_probe_restores_original(tmp_path, monkeypatch, sig):
    p = put(tmp_path, BASE.replace("\n", "\r\n"))
    orig = p.read_bytes()
    before = signal.getsignal(sig)
    calls = [0]

    def kill_on_third(_candidate):
        calls[0] += 1
        if calls[0] == 3:
            os.kill(os.getpid(), sig)       # the handler raises right here, with a probe on disk
        return False
    install(monkeypatch, raise_if=kill_on_third, breakat=105)
    with pytest.raises(BaseException) as ei:
        T.tune(str(p), 1, 74, 76)
    assert not isinstance(ei.value, Exception) and calls[0] == 3
    assert p.read_bytes() == orig                   # no probe left in the CV
    assert signal.getsignal(sig) == before          # handler restored afterwards


def test_a_longer_identifier_is_not_the_rhythm_line():
    """`#let rhythm-big = 2` is another binding (Typst identifiers allow `-`), not the rhythm."""
    text = "#let rhythm = 1.000\n#let rhythm-big = 2\n" + BODY
    assert not _rhythm_unparsed(text) and _read_rhythm(text) == 1.0
    assert _read_rhythm("#let rhythm-big = 2\n" + BODY) is None
    assert not _rhythm_unparsed("#let rhythm-big = 2\n" + BODY)


# ---- the CV must compile before it is tuned: a refusal is reported as such, not as "page count off"

def test_a_cv_that_does_not_compile_is_reported_and_never_probed(tmp_path, monkeypatch, capsys):
    p = put(tmp_path, BASE)
    log = []
    install(monkeypatch, log=log)
    refusal = pdf_module.standard_failure_advice("error: PDF/UA-1 error: missing document title\n")
    monkeypatch.setattr(T, "compile_or_messages", lambda typ, out: ("", pdf_module.compile_failure_messages(
        f"{refusal}\nerror: PDF/UA-1 error: missing document title\n")))

    code, footer = T.tune(str(p), 1, 74, 76)

    out = capsys.readouterr().out
    assert code == 1 and footer is None
    assert re.search(r"^FAIL  vitae:.*title", out, flags=re.M) and "missing document title" in out
    assert "page count off" not in out
    assert log == [] and p.read_text() == BASE        # no probe was compiled, the file is untouched


def test_a_cv_that_compiles_is_tuned(tmp_path, monkeypatch, capsys):
    """Control of the test above: the same file with a compile that succeeds is tuned."""
    p = put(tmp_path, BASE)
    install(monkeypatch)
    assert T.tune(str(p), 1, 74, 76)[0] == 0
    assert "nothing was tuned" not in capsys.readouterr().out


def test_a_real_cv_without_a_title_never_prints_page_count_off(tmp_path, monkeypatch, capsys):
    """End to end (real Typst, real probes): the refusal comes from the first compile and names the title."""
    from vitae.core import env
    if not env.check_typst() or not env.preflight()[0]:
        pytest.skip("no Typst or no PDF reader available")
    monkeypatch.setattr(T, "compile_or_messages", pdf_module.compile_or_messages)     # the real one, not the conftest stub
    p = put(tmp_path, '#set page(width: 200pt, height: 100pt)\n' + BODY)
    code, _ = T.tune(str(p), 1, 74, 76)
    out = capsys.readouterr().out
    assert code == 1 and "page count off" not in out
    assert re.search(r"^FAIL  vitae:.*title", out, flags=re.M)
