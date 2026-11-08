"""verify.py --selftest: Rule 5: no section may split across a page break"""

from __future__ import annotations

from vitae.verify.source import check_no_split


def no_split() -> None:
    """Rule 5: no section may split across a page break."""
    # --- rule 5, "no section may split across a page break": the
    # headline rule of the whole skill, and until 2026-09-13 NOTHING on
    # the industry side measured it (the academic gate measured its own
    # entry-level analogue; lib.typ only sets `breakable: false`, which
    # says what the template INTENDS, not what the PDF did).
    ns_src = ('#section("Profile")[a]\n#section("Selected Projects")[b]\n'
              '#section("Certifications & Professional Development")[c]\n')
    one = ["NAME\nProfile\ntext"]
    assert not any(f for f, _ in check_no_split(ns_src, one)), \
        "a single-page deliverable has no break and must never fail"
    good = ["NAME\nPROFILE\ntext", "SELECTED PROJECTS\nProject Name\n2024"]
    assert not any(f for f, _ in check_no_split(ns_src, good)), \
        "a page opening on a declared heading is a clean break"
    split = ["NAME\nPROFILE\ntext", "kept the API under 200 ms\n2024"]
    assert any(f for f, _ in check_no_split(ns_src, split)), \
        "page 2 opening mid-section is the SPLIT this check exists for"
    # the running head must not be mistaken for the split it hides:
    # lib.typ's runhead extracts as name and `n / total`, over one line or
    # two, in either order.
    # Only the order the device actually produces: pdftotext reads left
    # to right, so `name #h(1fr) n / total` extracts as the name first —
    # measured on swiss-grid/resume-2page, the corpus's only 2-pager.
    # Pagination-first is not handled and is not a case that occurs.
    for band in ("Firstname Lastname\n2 / 2",
                 "Firstname Lastname — Backend Developer 2 / 2"):
        rh = ["NAME\nPROFILE\ntext", band + "\nSELECTED PROJECTS\nProject"]
        assert not any(f for f, _ in check_no_split(ns_src, rh)), \
            f"the running head band ({band!r}) must be skipped, not judged"
        bad_rh = ["NAME\nPROFILE\ntext", band + "\nkept the API under 200 ms"]
        assert any(f for f, _ in check_no_split(ns_src, bad_rh)), \
            "skipping the running head must not swallow the line AFTER it"
    # a heading long enough to wrap still opens its page
    wrapped = ["NAME\nPROFILE\ntext", "CERTIFICATIONS &\nPROFESSIONAL DEVELOPMENT"]
    assert not any(f for f, _ in check_no_split(ns_src, wrapped)), \
        "a wrapped heading must match on its first line, not fail"
    # the pdftotext terminator: a trailing empty chunk is not a page
    assert not any(f for f, _ in check_no_split(ns_src, one + [""])), \
        "pdftotext's trailing \\f must not read as an empty second page"
    assert any(f for f, _ in check_no_split(ns_src, split + [""])), \
        "dropping the terminator must not drop a real trailing page"
    # and a source with no #section() call is reported, never guessed at
    assert not any(f for f, _ in check_no_split("#let x = 1\n", split)), \
        "no declared heading list means NOT CHECKED, not a free pass fail"
