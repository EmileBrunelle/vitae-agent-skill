"""check_whitespace on real PIL-built page rasters: the true measure_fill.bands / furniture_ink path (no typst)."""

import pytest
from PIL import Image, ImageDraw
from vitae.verify.layout import check_whitespace
from vitae.verify.page import FURNITURE_SCALE

W, H = 1275, 1650


def page(tmp_path, rule_luma=None, gap=45, rule_len=975, rules=4, underline=0, tick=False):
    """4 sections of 6 text rows. Returns (png path, word boxes in PDF points).

    rule_luma: hairline AT each of the first `rules` boundaries; gap: white run above each section's text;
    underline: number of sections with a link underline mid-body; tick: a short mark on each heading's text line,
    absent from the word boxes.
    """
    im = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(im)
    boxes = []
    y = 200
    for s in range(4):
        if rule_luma is not None and s < rules:
            d.line([(150, y), (150 + rule_len, y)], fill=rule_luma, width=2)
        y += gap
        for i in range(6):
            for x in range(150, 1100, 60):
                d.rectangle([x, y, x + 44, y + 8], fill=30)
                boxes.append((x / FURNITURE_SCALE, y / FURNITURE_SCALE, (x + 44) / FURNITURE_SCALE,
                              (y + 8) / FURNITURE_SCALE))
            if tick and i == 0:
                d.rectangle([1130, y, 1160, y + 8], fill=20)
            y += 22
            if s < underline and i == 2:
                d.line([(150, y - 6), (450, y - 6)], fill=30, width=2)
        if tick:
            y += gap
    path = str(tmp_path / "p.png")
    im.save(path)
    return path, boxes


def run(tmp_path, boxes=False, **kw):
    gate_kw = {k: kw.pop(k) for k in ("family", "degraded") if k in kw}
    png, bx = page(tmp_path, **kw)
    r = list(check_whitespace(png, boxes=bx if boxes else None, **gate_kw))
    return [f for f, _ in r], [m for _, m in r]


@pytest.mark.parametrize("kw", [
    pytest.param(dict(rule_luma=180), id="pale-full-hairline"),
    pytest.param(dict(rule_luma=30, rule_len=70, gap=75), id="short-5.5pct-rule-RULE_FLOOR"),
    pytest.param(dict(rule_luma=30, gap=25), id="tight-but-inked"),
])
def test_rule_at_boundaries_is_counted_as_device(tmp_path, kw):
    fails, msgs = run(tmp_path, **kw)
    assert not any(fails) and any("boundary devices:" in m for m in msgs)


def test_tick_on_heading_line_is_seen_only_with_word_boxes(tmp_path):
    _, blind = run(tmp_path, tick=True)
    _, seen = run(tmp_path, tick=True, boxes=True)
    assert not any("boundary devices:" in m for m in blind)
    assert any("boundary devices:" in m for m in seen)


@pytest.mark.parametrize("boxes", [False, True], ids=["no-boxes", "boxes"])
def test_mid_section_link_underlines_never_reach_quorum(tmp_path, boxes):
    # with boxes the underlines are found by furniture_ink, but sit mid-section, not at a boundary
    fails, msgs = run(tmp_path, gap=90, underline=4, boxes=boxes)
    assert any(f and "no ink" in m for f, m in zip(fails, msgs))


def test_one_rule_seen_by_both_scans_counts_once(tmp_path):
    fails, msgs = run(tmp_path, rule_luma=30, rules=1, gap=90, boxes=True)
    assert any(f and "no ink" in m for f, m in zip(fails, msgs))


@pytest.mark.parametrize("kw", [dict(gap=10), dict(gap=90), dict(gap=53)], ids=["tight", "bare-7.9x", "airy"])
def test_zero_devices_fail_whatever_the_ratio(tmp_path, kw):
    assert any(run(tmp_path, **kw)[0])


@pytest.mark.parametrize("gap", [10, 53], ids=["tight", "airy-5.1x"])
def test_deviceless_family_is_exempt_below_the_separation_ceiling(tmp_path, gap):
    assert not any(run(tmp_path, gap=gap, family="humanist-quiet")[0])


def test_degraded_is_reported_not_measured_never_failed(tmp_path):
    fails, msgs = run(tmp_path, gap=10, degraded=True)
    assert not any(fails) and any("NOT MEASURED" in m for m in msgs)
