"""Family-relative leading / list-spacing WARN and the tuner's list-spacing scaling."""
from pathlib import Path

import pytest
from vitae.core.base import LEADING_ABS_RATIO_WARN, LEADING_FAMILY_RATIO_WARN
from vitae.core.env import PdfCheck
from vitae.verify import tune as T
from vitae.verify.cv import LEADING_WARN, _family_default, _leading_warn
from vitae.verify.typst import doc_par_list, scale_list_spacing

pytestmark = pytest.mark.usefixtures("tuner_original_compiles")


def _default(family: str, pages: int) -> tuple[float, float]:
    d = _family_default(family, pages)
    assert d is not None
    return d


_L, _S = _default("color-band", 1)
BAND = _L / _S        # the shipped color-band ratio, read from the template


def cv(tmp_path, lead, lsp, family="color-band"):
    p = tmp_path / "cv.typ"
    banner = f"// FAMILY: {family}\n" if family else ""
    p.write_text(f"{banner}#set par(leading: {lead!r}em, spacing: 1.0em)\n#set list(spacing: {lsp!r}em)\nbody\n",
                 encoding="utf-8")
    return str(p)


class TestFamilyRelative:
    @pytest.mark.parametrize("factor,warns", [
        (1.0, False), (LEADING_FAMILY_RATIO_WARN - 0.005, False),
        (LEADING_FAMILY_RATIO_WARN + 0.005, True), (1.5, True)])   # explicit margin: no float-exact boundary

    def test_threshold_boundary(self, tmp_path, factor, warns):
        out = _leading_warn(cv(tmp_path, _S * BAND * factor, _S))
        assert bool(out) == warns, out

    def test_message_names_the_fix(self, tmp_path):
        # the absolute leading check takes precedence, so keep the leading well under
        # LEADING_WARN whatever the shipped color-band values are: only the ratio is off
        lsp = min(_S, LEADING_WARN / (BAND * 1.5) / 2)
        out = _leading_warn(cv(tmp_path, lsp * BAND * 1.5, lsp))
        assert "list rhythm no longer matches" in out and "--tune" in out and "color-band" in out

    def test_real_run_numbers(self, tmp_path):
        # run26 agy carbon: relative ratio ~1.16 against color-band; absolute ratio is below 1.95
        lead, lsp = 0.83, 0.55
        assert (lead / lsp) / BAND > LEADING_FAMILY_RATIO_WARN
        assert lead / lsp < LEADING_ABS_RATIO_WARN
        assert _leading_warn(cv(tmp_path, lead, lsp)).startswith("WARN")

    def test_two_page_reference_is_the_2page_template(self, tmp_path, monkeypatch):
        # a file at exactly the family's 2-page default: silent against it, fires against resume.typ.
        # Synthetic family: the shipped 1-page and 2-page ratios are no longer far enough apart to pin.
        import vitae.verify.cv as C
        fam = tmp_path / "templates" / "families" / "zz"
        fam.mkdir(parents=True)
        (tmp_path / "scripts" / "vitae" / "verify").mkdir(parents=True)
        (fam / "resume.typ").write_text("#set par(leading: 0.60em)\n#set list(spacing: 0.80em)\nx\n")
        (fam / "resume-2page.typ").write_text("#set par(leading: 0.80em)\n#set list(spacing: 0.80em)\nx\n")
        monkeypatch.setattr(C.os.path, "abspath", lambda _p: str(tmp_path / "scripts" / "vitae" / "verify" / "cv.py"))
        C._family_default.cache_clear()
        try:
            p = cv(tmp_path, 0.80, 0.80, "zz")
            assert _leading_warn(p, 2) == ""
            assert _leading_warn(p, 1).startswith("WARN")
        finally:
            C._family_default.cache_clear()

    def test_unparsable_2page_falls_back_to_resume(self, tmp_path, monkeypatch):
        import vitae.verify.cv as C
        fam = tmp_path / "templates" / "families" / "zz"
        fam.mkdir(parents=True)
        (tmp_path / "scripts" / "vitae" / "verify").mkdir(parents=True)
        (fam / "resume.typ").write_text("#set par(leading: 0.6em)\n#set list(spacing: 0.5em)\nx\n")
        (fam / "resume-2page.typ").write_text("no rules here\n")
        monkeypatch.setattr(C.os.path, "abspath", lambda _p: str(tmp_path / "scripts" / "vitae" / "verify" / "cv.py"))
        C._family_default.cache_clear()
        try:
            assert C._family_default("zz", 2) == (0.6, 0.5)
        finally:
            C._family_default.cache_clear()


class TestFallback:
    @pytest.mark.parametrize("family", [None, "no-such-family"])
    def test_absolute_check_below_and_above(self, tmp_path, family):
        assert _leading_warn(cv(tmp_path, 0.85, 0.45, family)) == ""            # 1.89
        assert _leading_warn(cv(tmp_path, 0.90, 0.45, family)).startswith("WARN")   # 2.00


PAR_LIST = "#set par(leading: 0.60em, spacing: 0.70em)\n#set list(spacing: 0.45em)\nbody\n"


@pytest.fixture
def typ(tmp_path):
    p = tmp_path / "cv.typ"
    p.write_text(PAR_LIST, encoding="utf-8")
    return p


def _install(monkeypatch, lstar=0.90):
    monkeypatch.setattr(T, "preflight", lambda: PdfCheck(True, "pypdf"))

    def probe(path, text, leading, spacing, expected, backend):
        Path(path).write_text(T._with_rhythm(text, leading, spacing), encoding="utf-8")
        return (True, round(leading * 100)) if leading <= lstar else (False, None)
    monkeypatch.setattr(T, "_probe", probe)


class TestTuneScalesList:
    def test_ratio_preserved(self, typ, monkeypatch):
        _install(monkeypatch)
        assert T.tune(str(typ), T.FillTarget(1, 80, 99))[0] == 0
        lead, lsp = doc_par_list(typ.read_text(encoding="utf-8"))
        assert lead is not None and lsp is not None
        assert lead > 0.7 and lead / lsp == pytest.approx(0.60 / 0.45, rel=3e-3)

    def test_no_list_spacing_untouched(self, tmp_path, monkeypatch):
        p = tmp_path / "cv.typ"
        p.write_text("#set par(leading: 0.60em, spacing: 0.70em)\n#set list(indent: 10pt)\nbody\n", encoding="utf-8")
        _install(monkeypatch)
        assert T.tune(str(p), T.FillTarget(1, 80, 99))[0] == 0
        assert "#set list(indent: 10pt)\n" in p.read_text(encoding="utf-8")

    def test_two_par_file_tunes_the_gates_line_and_leaves_an_earlier_list_alone(self):
        src = ("#set par(leading: 0.60em, spacing: 0.70em)\n#set list(spacing: 0.45em)\n"
               "#set par(leading: 0.96em, spacing: 1.0em)\nbody\n")
        out = T._with_rhythm(src, 0.70, 0.80)
        assert doc_par_list(out) == (0.70, 0.45) and out.startswith("#set par(leading: 0.60em, spacing: 0.70em)")

    def test_nested_spacing_untouched(self):
        src = "#set par(leading: 0.6em)\n#set list(marker: box(spacing: 0.1em)[x])\nbody\n"
        assert scale_list_spacing(src, 2.0) == src

    def test_scale_helper_multiplies_and_keeps_unit(self):
        out = scale_list_spacing("#set list(indent: 1pt, spacing: 0.4em)\nbody spacing: 0.4em\n", 1.5)
        assert "spacing: 0.600em)" in out and "body spacing: 0.4em" in out
