"""verify_letter.check_letter finds the employer name regardless of case and sharp s."""
import verify_letter as vl


def _letter(monkeypatch, tmp_path, text, employer, title):
    monkeypatch.setattr(vl, "preflight", lambda: (True, True, "x"))
    monkeypatch.setattr(vl, "ensure_icons", lambda typ: None)
    monkeypatch.setattr(vl, "compile_pdf", lambda typ, pdf, cli: (True, ""))
    monkeypatch.setattr(vl, "count_pages", lambda pdf, backend: "1")
    monkeypatch.setattr(vl, "extract_text", lambda pdf, backend: text)
    monkeypatch.setattr(vl, "check_hidden_text", lambda pdf: [])
    monkeypatch.setattr(vl, "make_context", lambda *a, **k: None)
    monkeypatch.setattr(vl, "_placeholders", lambda ctx: [])
    typ = tmp_path / "letter.typ"
    typ.write_text(text, encoding="utf-8")
    return vl.check_letter(str(typ), employer, title)


def employer_failures(msgs):
    return [m for failed, m in msgs if failed and "employer" in m]


def test_letter_finds_the_employer_across_sharp_s_and_case(monkeypatch, tmp_path):
    ok, msgs = _letter(monkeypatch, tmp_path, "Sehr geehrte Damen und Herren, bei der STRASSENBAU AG als LEITERIN bewerbe ich mich.",
                       "Straßenbau AG", "Leiterin")
    assert ok and employer_failures(msgs) == []


def test_letter_fails_when_the_employer_is_absent(monkeypatch, tmp_path):
    ok, msgs = _letter(monkeypatch, tmp_path, "Dear team, I apply as a developer.", "Acme", "Developer")
    assert not ok and employer_failures(msgs)
