"""verify.py --selftest: The ink-band detector and the whitespace gate (devices, furniture, quorum)"""

from __future__ import annotations

import os
import tempfile
from typing import Literal, overload

import vitae.fill as measure_fill
from vitae.core.base import Box
from vitae.selftest.gates.fixtures import VERIFY_FILE
from vitae.verify.cv import (
    is_academic,
    is_letter,
)
from vitae.verify.layout import DEVICE_QUORUM, SEPARATION_CEILING, check_whitespace
from vitae.verify.page import FURNITURE_SCALE, furniture_ink
from vitae.verify.pdf import family_from_path


def whitespace() -> None:
    """The ink-band detector and the whitespace gate (devices, furniture, quorum)."""
    # The other piece that can break silently: the ink-band detector. If
    # it stopped seeing devices, every CV would pass the "carries ink"
    # check by accident, which is the exact rule that kept regressing.
    # Two synthetic pages, drawn with PIL so the check needs no Typst.
    from PIL import Image, ImageDraw

    # Synthetic page factory: 1275x1650 px (US Letter 8.5x11 in at 150 ppi), 4 sections of 6 text rows of 16
    # dark blocks (44x8 px words every 60 px, row step 22 px => 14 px median white gap). `rule_luma` draws a
    # hairline AT each of the first `rules` boundaries (None: none), `gap` is the white run left above each
    # section's text, `underline` the number of sections with an underlined link mid-body. Measured with
    # check_whitespace, biggest gap over median: thin (gap 75, 4 rules) 5.62x, bare (gap 90) 7.92x, airy
    # (gap 53) 5.08x, inked (gap 45) 4.46x, tight (gap 25) 1.77x.
    @overload
    def _page(rule_luma: int | None = ..., gap: int = ..., rule_len: int = ...,
              underline: int = ..., rules: int = ..., want_boxes: Literal[False] = ...) -> str: ...
    @overload
    def _page(rule_luma: int | None = ..., gap: int = ..., rule_len: int = ...,
              underline: int = ..., rules: int = ..., *, want_boxes: Literal[True]
              ) -> tuple[str, list[Box]]: ...
    def _page(rule_luma: int | None = None, gap: int = 45, rule_len: int = 975, underline: int = 0,
              rules: int = 4, want_boxes: bool = False) -> str | tuple[str, list[Box]]:
        # `underline` is a COUNT of sections that get an underlined link
        # mid-body; `want_boxes` also returns the word boxes for the body
        # text (never for the underlines — pdftotext does not box a rule),
        # which is what lets furniture_ink see them.
        im = Image.new("L", (1275, 1650), 255)
        d = ImageDraw.Draw(im)
        boxes: list[Box] = []
        y = 200
        for s in range(4):
            if rule_luma is not None and s < rules:  # a hairline AT the boundary
                d.line([(150, y), (150 + rule_len, y)], fill=rule_luma, width=2)
            y += gap                        # …or nothing but empty space
            for i in range(6):              # body text: short dark runs
                for x in range(150, 1100, 60):
                    d.rectangle([x, y, x + 44, y + 8], fill=30)
                    boxes.append((x / FURNITURE_SCALE, y / FURNITURE_SCALE,
                                  (x + 44) / FURNITURE_SCALE,
                                  (y + 8) / FURNITURE_SCALE))
                y += 22
                if s < underline and i == 2:
                    # an underlined link mid-section: a 24%-of-width
                    # unbroken run, wider than any real device on the
                    # roster, but nowhere near a boundary
                    d.line([(150, y - 6), (450, y - 6)], fill=30, width=2)
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        im.save(f.name)
        return (f.name, boxes) if want_boxes else f.name

    # inked: a tight page whose boundaries are pale full-measure hairlines.
    # thin: the same, with a device deliberately SHORTER than the text
    # column (5.5% of page width — `quiet-luxury`'s tick is 5.65%); it must
    # still pass, which is what breaks if RULE_FLOOR is raised back to 0.08.
    # linked: the false positive the old page-wide scan could not see — no
    # device at all, but an underlined link supplying a wide dark run. bare:
    # the same defect without even that.
    inked, bare = _page(rule_luma=180), _page(rule_luma=None, gap=90)
    # gap=75 puts this page's white ratio OVER SEPARATION_CEILING, so it
    # passes only while the short rule is seen: miss the device and the
    # same page is the "empty space is doing the whole job" failure.
    thin = _page(rule_luma=30, rule_len=70, gap=75)
    linked = _page(rule_luma=None, gap=90, underline=1)
    # one rule at the top and nothing below it: the `engraved-card` /
    # `gutter-rail` case, a flourish under the name and bare space after
    lone = _page(rule_luma=30, gap=75, rules=1)
    assert measure_fill.bands(inked)[2], "a pale hairline must read as ink"
    assert not measure_fill.bands(bare)[2], "body text must not read as ink"
    assert measure_fill.bands(linked)[2], \
        "the underline must register as a wide dark run (else the next " \
        "assert passes for the wrong reason)"
    for p in (inked, thin):
        msgs = list(check_whitespace(p))
        assert not any(f for f, _ in msgs), \
            "a page whose boundaries carry a hairline must not FAIL"
        # …and POSITIVELY, that the device was seen. Asserting only "does
        # not FAIL" stopped proving that once SEPARATION_CEILING rose
        # above `thin`'s 5.62x ratio: miss the short rule and the page
        # merely reports "carries no ink" and still passes. This is the
        # assertion RULE_FLOOR = 0.08 has to break (a 5.5%-of-width rule
        # falls under an 8% floor), and the ceiling can no longer stand in
        # for it.
        assert any("boundary devices:" in m for _, m in msgs), \
            "a pale or short hairline AT a boundary must be COUNTED as a " \
            "device, not merely fail to trigger a failure"
    for p in (bare, linked, lone):
        assert any(f and "no ink" in m for f, m in check_whitespace(p)), \
            "empty-space-only separation must FAIL on the ink check, " \
            "whatever ink the page carries away from its boundaries"

    # --- furniture: the blind spot no row-wide scan can see ---
    # A device typeset ON the heading's own text line (a tick, a side
    # bar) never shows up in `all_ink`: the row also carries word ink, so
    # its longest UNBROKEN run is just one word's width — under
    # RULE_FLOOR — same as any ordinary text row. Only a word-box list
    # that does NOT cover the device can tell the two apart.
    def _page_with_tick() -> tuple[str, list[Box]]:
        im = Image.new("L", (1275, 1650), 255)
        d = ImageDraw.Draw(im)
        boxes: list[Box] = []
        y = 200
        for s in range(4):
            first_row = True
            for i in range(6):
                for x in range(150, 1100, 60):
                    d.rectangle([x, y, x + 44, y + 8], fill=30)
                    boxes.append((x / FURNITURE_SCALE, y / FURNITURE_SCALE,
                                  (x + 44) / FURNITURE_SCALE,
                                  (y + 8) / FURNITURE_SCALE))
                if first_row:
                    # the tick: same row as text (never a white gap), and
                    # deliberately left OUT of `boxes` above. 30px of
                    # 1275 = 2.35%, above FURNITURE_FLOOR (2%) and below
                    # RULE_FLOOR (4%) so the old row-wide scan is blind
                    # to it on its own width too.
                    d.rectangle([1130, y, 1160, y + 8], fill=20)
                    first_row = False
                y += 22
            y += 45
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        im.save(f.name)
        return f.name, boxes

    tick_png, tick_boxes = _page_with_tick()
    assert not any("boundary devices:" in m for _, m
                   in check_whitespace(tick_png)), \
        "without word boxes the OLD detector alone must MISS a device " \
        "sitting beside a text line (not in any white gap)"
    assert any("boundary devices:" in m for _, m
               in check_whitespace(tick_png, boxes=tick_boxes)), \
        "furniture_ink must SEE the same tick once word boxes are given " \
        "— ink not covered by any word box, on a line that carries text"
    os.unlink(tick_png)

    # …and the other half of the same coin: furniture is only a device
    # when it sits AT a boundary. A page with NO device anywhere but four
    # underlined links deep inside its sections used to satisfy
    # DEVICE_QUORUM the moment word boxes were available — `linked` above
    # only ever exercised the BOX-LESS path, where the links are caught by
    # boundary_ink instead, so it could not see this. Word boxes cover the
    # body text and not the underlines, so furniture_ink finds all four.
    link_png, link_boxes = _page(rule_luma=None, gap=90, underline=4,
                                 want_boxes=True)
    assert len(furniture_ink(link_png, link_boxes)) >= DEVICE_QUORUM, \
        "the underlines must reach furniture_ink at all, else the next " \
        "assert passes for the wrong reason"
    assert any(f and "no ink" in m for f, m in
               check_whitespace(link_png, boxes=link_boxes)), \
        "link underlines in the MIDDLE of a section must not count " \
        "towards the quorum just because word boxes are available — the " \
        "gate claims the bands are AT a section boundary"
    os.unlink(link_png)

    # --- one device, seen by BOTH detectors, must count ONCE. This is
    # the frame bug: `furniture_ink` scans the whole PNG while
    # `measure_fill.bands` reports rows of a crop that cuts 2% off the
    # top, so the `_overlap` dedupe was comparing two coordinate systems
    # and never fired. A single rule at a boundary therefore scored 2 and
    # cleared DEVICE_QUORUM on its own — which is how the cover letter
    # (one letterhead rule, by design) and engraved-card passed. ---
    one_png, one_boxes = _page(rule_luma=30, rules=1, gap=90,
                               want_boxes=True)
    assert len(furniture_ink(one_png, one_boxes)) >= 1, \
        "the lone rule must reach furniture_ink at all, else the next " \
        "assert passes for the wrong reason"
    assert any(f and "no ink" in m for f, m in
               check_whitespace(one_png, boxes=one_boxes)), \
        "a page carrying ONE device must FAIL the quorum: both scans " \
        "see that same rule, and counting it twice is the mixed-frame " \
        "bug — a boundary SYSTEM is two devices, not one counted twice"
    os.unlink(one_png)

    with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False,
                                     encoding="utf-8") as tf:
        tf.write("// vitae letter template — one letter per posting\n")
        lettre = tf.name
    assert is_letter(lettre), \
        "a cover letter must be recognised by its line-1 marker, or a " \
        "sweep asks a one-rule letter for a section boundary SYSTEM"
    assert not is_letter(VERIFY_FILE), \
        "is_letter must not fire on an ordinary file"
    os.unlink(lettre)

    # --- the gate must actually FAIL now (2026-09-13 fix): a page with
    # no device anywhere used to pass whenever its whitespace ratio sat
    # under SEPARATION_CEILING (6.0) — which the WHOLE corpus does (max
    # measured: 5.14). Quorum failure is now unconditional unless the
    # family is in DEVICELESS. ---
    bare_tight = _page(rule_luma=None, gap=10)  # ratio well under 6.0
    assert any(f for f, _ in check_whitespace(bare_tight)), \
        "zero boundary devices must FAIL the quorum even when the " \
        "whitespace ratio is nowhere near SEPARATION_CEILING — this is " \
        "exactly the case that never failed before"
    assert not any(f for f, _ in
                   check_whitespace(bare_tight, family="humanist-quiet")), \
        "a DEVICELESS-exempt family must not FAIL on zero devices"
    # A missing pdftotext must not masquerade as a design defect: without
    # word boxes the union is the old row scan alone, which scores 0 on
    # real pages whose device sits on the heading's line.
    assert not any(f for f, _ in
                   check_whitespace(bare_tight, degraded=True)), \
        "with no word boxes the quorum must be REPORTED, not failed"
    assert any("NOT MEASURED" in m for _, m in
               check_whitespace(bare_tight, degraded=True)), \
        "degraded mode must say so, not silently pass"
    os.unlink(bare_tight)

    with tempfile.NamedTemporaryFile("w", suffix=".typ", delete=False,
                                     encoding="utf-8") as tf:
        tf.write("// vitae-academic: sections=13 entries=212\n#set page()\n")
        acad = tf.name
    assert is_academic(acad), \
        "an academic CV must be recognised by its line-1 marker, or a " \
        "sweep judges a 13-page CV against a 1-page resume gate"
    assert not is_academic(VERIFY_FILE), \
        "is_academic must not fire on an ordinary file"
    os.unlink(acad)

    assert family_from_path("templates/families/quiet-luxury/resume.typ") \
        == "quiet-luxury"
    assert family_from_path("/home/x/my-own-cv.typ") is None, \
        "a path outside templates/families/ must never carry an exemption"

    # --- the 2026-09-13 recalibration, pinned from both sides ---
    # tight: boundaries carry a hairline but the gap is only 1.77x the
    # median — BELOW the old 2.0 floor, which failed it. The corpus says
    # that ratio does not rank separation (a page with NO section gap at
    # all scores 2.69), so an inked page must pass at any ratio. This is
    # the `engraved-card/resume-pair-b` case, which measured 1.89.
    tight = _page(rule_luma=30, gap=25)
    assert not any(f for f, _ in check_whitespace(tight)), \
        "the white ratio must no longer FAIL a page whose boundaries " \
        "carry ink, however tight the gap"
    # airy: no device anywhere and a ratio of ~5.1 — the top of the real
    # roster (margin-index 5.14). SEPARATION_CEILING still must not fail
    # it on the ratio alone; but the ratio was never what covered a truly
    # device-less family — DEVICELESS does. margin-index itself is not
    # exempt (it measures a union of 14: its "device-less" reputation was
    # an artifact of the old ink-blind scan), so this is a synthetic
    # stand-in and must only pass WITH an exemption.
    airy = _page(rule_luma=None, gap=53)
    assert not any(f for f, _ in
                   check_whitespace(airy, family="humanist-quiet")), \
        "SEPARATION_CEILING must sit above the roster's highest page " \
        f"(5.14x); at {SEPARATION_CEILING} an exempt device-less family " \
        "that compensates with white — which core.md requires of it " \
        "— must not fail on the ratio"
    assert any(f for f, _ in check_whitespace(airy)), \
        "the same page with no family exemption must FAIL the quorum"
    for f in (inked, bare, thin, linked, lone, tight, airy):
        os.unlink(f)
