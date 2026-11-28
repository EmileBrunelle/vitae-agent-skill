"""verify.layout.check_text_clip (a fill that cuts or hides a word) on synthetic rasters, and the page-level
verify.source.check_no_split rules on pdftotext-style page texts (headings in other scripts: test_source_headings)."""
import pytest
from PIL import Image
from vitae.verify.layout import check_text_clip
from vitae.verify.page import FURNITURE_SCALE
from vitae.verify.source import check_no_split

S = FURNITURE_SCALE
WHITE, DARK, RED = (255, 255, 255), (0, 0, 0), (200, 30, 30)


def _word(y: float, x0: float = 40, x1: float = 200):
    return [((x0 / S, y / S, x1 / S, (y + 14) / S), "linkedin.com")]


def _raster(tmp_path, glyph_y: int, glyph_col=WHITE, rules: int = 0) -> str:
    """400x200 white page with a grey band down to y=100, fake glyphs at glyph_y, optional flanking hairline rules."""
    im = Image.new("RGB", (400, 200), WHITE)
    im.paste((60, 60, 60), (0, 0, 400, 100))
    for x in range(60, 180, 6):
        im.paste(glyph_col, (x, glyph_y + 3, x + 3, glyph_y + 11))
    if rules:
        im.paste(DARK, (0, 108, 37, 108 + rules))
        im.paste(DARK, (203, 108, 400, 108 + rules))
    path = tmp_path / "t.png"
    im.save(path)
    return str(path)


@pytest.mark.parametrize("y, col, fires", [
    (92, RED, True),         # straddles the band's bottom edge
    (70, WHITE, False),      # wholly inside the band
    (120, DARK, False),      # wholly on paper
    (120, WHITE, True),      # white glyphs past the band: colour matches the paper
], ids=["cut-by-edge", "inside-band", "on-paper", "hidden-white-on-white"])
def test_text_clip_fires_or_stays_quiet(tmp_path, y, col, fires):
    assert bool(check_text_clip(_raster(tmp_path, y, col), _word(y))) is fires


def test_hidden_message_names_the_colour_match(tmp_path):
    assert any("indistinguishable" in m for m in check_text_clip(_raster(tmp_path, 120), _word(120)))


@pytest.mark.parametrize("thick", [1, 2])
def test_word_flanked_by_hairline_rules_is_not_cut(tmp_path, thick):
    assert check_text_clip(_raster(tmp_path, 105, DARK, rules=thick), _word(100)) == []


SRC = '#section("Profile")[a]\n#section("Selected Projects")[b]\n#section("Certifications & Professional Development")[c]\n'
P1 = "NAME\nPROFILE\ntext"
RUN_HEADS = ["Firstname Lastname\n2 / 2", "Firstname Lastname — Backend Developer 2 / 2"]


def _fails(pages: list[str], src: str = SRC) -> bool:
    return any(fail for fail, _ in check_no_split(src, pages))


@pytest.mark.parametrize("pages, fails", [
    ([P1], False),                                                       # one page: no break
    ([P1, "SELECTED PROJECTS\nProject Name\n2024"], False),              # page opens on a declared heading
    ([P1, "kept the API under 200 ms\n2024"], True),                     # page opens mid-section
    ([P1, "CERTIFICATIONS &\nPROFESSIONAL DEVELOPMENT"], False),         # wrapped heading matches on its first line
    ([P1, ""], False),                                                   # pdftotext's trailing form feed is not a page
    ([P1, "kept the API under 200 ms", ""], True),                       # ...and does not drop a real trailing page
    ([P1, RUN_HEADS[0] + "\nSELECTED PROJECTS\nProject"], False),        # running head skipped, not judged
    ([P1, RUN_HEADS[1] + "\nSELECTED PROJECTS\nProject"], False),
    ([P1, RUN_HEADS[0] + "\nkept the API under 200 ms"], True),         # ...but not the line after it
    ([P1, RUN_HEADS[1] + "\nkept the API under 200 ms"], True),
], ids=["one-page", "clean-break", "split", "wrapped", "terminator", "terminator-split",
        "runhead-1", "runhead-2", "runhead-split-1", "runhead-split-2"])
def test_no_split_page_texts(pages, fails):
    assert _fails(pages) is fails


@pytest.mark.parametrize("pages", [[P1, "kept the API under 200 ms"], [P1, "x", "y"]], ids=["two-pages", "three-pages"])
def test_no_section_call_is_unmeasurable_so_it_fails_over_several_pages(pages):
    assert _fails(pages, src="#let x = 1\nplain body\n")


def test_hidden_word_starting_above_the_page_top_is_still_detected(tmp_path):
    im = Image.new("RGB", (400, 200), WHITE)                 # white glyphs on white paper, box starts 6 px above the page
    for x in range(60, 180, 6):
        im.paste(WHITE, (x, 0, x + 3, 8))
    path = tmp_path / "top.png"
    im.save(path)

    out = check_text_clip(str(path), _word(-6))

    assert any("indistinguishable" in m for m in out)
