"""check_group_proximity's hierarchy WARN (PROX_HIER = 1.2: the gap between entries must be visibly larger
than the gaps inside one; groups before a section title are left to the section rules) and the org line ->
first bullet figures that measure_groups records. Mutation check, each verified by hand: PROX_HIER = 1.0 makes
test_ratio_1_1_warns fail; dropping `not r["next_sec"]` makes test_group_before_a_section_is_excluded fail;
`n >= 4` -> `n >= 3` (or `gaps[1]` -> `gaps[0]`) makes the org-gap tests fail."""
from collections.abc import Sequence

import pytest
from test_verify_groups import head, line, only_group, sec
from vitae.core.base import GroupRow, Mark
from vitae.core.level import Level
from vitae.verify import groups


def _run(between: float, secs: Sequence[Mark] = (), internal: float = 10.0):
    nxt = 20 + internal + between
    words = [line("Role", 0), line("Detail", 10 + internal), line("Next", nxt)]
    return groups.check_group_proximity("", "", heads=[head("Role", 0), head("Next", nxt)], secs=list(secs),
                                        pages=[words], detail=[])


class TestHierarchy:
    def test_ratio_1_1_warns(self):
        (lv, msg), = _run(11)
        assert lv is Level.WARN and "entries barely separated" in msg and "ratio 1.10" in msg
        assert "`job` wrapper" in msg and "entry(above:)" in msg and "not the content" in msg
        assert "never per entry, never in lib.typ" in msg

    def test_skill_rows_name_the_skill_wrapper(self):
        words = [line("Cat", 0), line("Detail", 20), line("Next", 41)]
        h: Mark = {**head("Cat", 0), "kind": "skill"}
        n: Mark = {**head("Next", 41), "kind": "skill"}
        (lv, msg), = groups.check_group_proximity("", "", heads=[h, n], secs=[], pages=[words], detail=[])
        assert lv is Level.WARN and "skill rows barely separated" in msg and "entries" not in msg.split("\n")[0]
        assert "gap to the next skill row" in msg and "inside a skill row" in msg
        assert "`skill` wrapper" in msg and "srow(above:)" in msg and "entry(above:)" not in msg
        assert "never per row, never in lib.typ" in msg

    def test_entry_only_groups_say_entry(self):
        words = [line("Role", 0), line("Detail", 20), line("Next", 41)]
        (lv, msg), = groups.check_group_proximity("", "", heads=[head("Role", 0), head("Next", 41)], secs=[],
                                                  pages=[words], detail=[])
        assert lv is Level.WARN and "entries barely separated" in msg and "skill row" not in msg
        assert "inside an entry" in msg and "gap to the next entry" in msg

    def test_mixed_groups_say_entries_but_worst_clause_follows_its_own_kind(self):
        # worst group (ratio 1.0) is a skill row; the other flat group (ratio 1.1) is an entry
        words = [line("Cat", 0), line("Detail", 20), line("Role", 40), line("Detail2", 60), line("Next", 81)]
        h1: Mark = {**head("Cat", 0), "kind": "skill"}
        h2, n = head("Role", 40), head("Next", 81)
        (lv, msg), = groups.check_group_proximity("", "", heads=[h1, h2, n], secs=[], pages=[words], detail=[])
        first = msg.split("\n")[0]
        assert lv is Level.WARN and "entries barely separated" in first and "skill rows" not in first
        assert "inside an entry" in first and "gap to the next skill row" in first

    def test_prox_warn_boundary_picks_the_message(self):
        # ratio 0.84 -> the attached-to-next WARN; 0.85 sits on the line (>=, not >): hierarchy WARN only
        (lv, msg), = _run(8.4)
        assert lv is Level.WARN and "barely separated from the next block" in msg
        (lv, msg), = _run(8.5)
        assert lv is Level.WARN and "entries barely separated" in msg and "from the next block" not in msg
        (lv, msg), = _run(8.6)
        assert "entries barely separated" in msg

    def test_ratio_1_3_does_not_warn(self):
        (lv, msg), = _run(13)
        assert lv is Level.OK

    def test_threshold_is_1_2_inclusive(self):
        assert groups.PROX_HIER == 1.2
        assert _run(12)[0][0] is Level.OK and _run(11.9)[0][0] is Level.WARN

    def test_group_before_a_section_is_excluded(self):
        # the next block is a section title: even a 1.1 ratio is the section rules' business
        words = [line("Role", 0), line("Detail", 20), line("EDU", 41), line("Body", 60)]
        out = groups.check_group_proximity("", "", heads=[head("Role", 0)], secs=[sec("EDU", 41)],
                                           pages=[words], detail=[])
        assert [lv for lv, _ in out if "group proximity" in _] == [Level.OK]    # same ratio 1.1 as test_ratio_1_1_warns

    def test_attached_to_next_keeps_its_own_message(self):
        (lv, msg), = _run(8)
        assert lv is Level.WARN and "barely separated from the next block" in msg
        assert _run(5)[0][0] is Level.FAIL


def _entry(gap_head: float, pitch: float, org: str = "Acme") -> GroupRow:
    """Role, org line, then three bullets `pitch` apart (the first `gap_head` after the org line), next head."""
    ys = [0.0, 12.0]
    ys.append(ys[-1] + 10 + gap_head)
    ys += [ys[-1] + 10 + pitch, ys[-1] + 20 + 2 * pitch]
    words = [line(t, y) for t, y in zip(("Role", "Acme", "B1", "B2", "B3"), ys)] + [line("Next", ys[-1] + 60)]
    h: Mark = {**head("Role", 0), "org": org}
    return only_group(groups.measure_groups([h, head("Next", ys[-1] + 60)], [], [words])[0])


class TestOrgToFirstBullet:
    def test_head_gap_and_bullet_pitch_recorded(self):
        r = _entry(2.0, 5.0)
        assert r["head_gap"] == pytest.approx(2.0) and r["pitch"] == pytest.approx(5.0)

    def test_larger_head_gap_is_visible_in_the_figures(self):
        r = _entry(9.0, 3.0)
        assert r["head_gap"] is not None and r["pitch"] is not None
        assert r["head_gap"] > r["pitch"]

    def test_needs_an_org_and_two_bullets(self):
        assert _entry(2.0, 5.0, org="")["head_gap"] is None            # no org line: line 1 would be a bullet
        words = [line("Role", 0), line("Acme", 12), line("B1", 24), line("Next", 80)]
        h: Mark = {**head("Role", 0), "org": "Acme"}
        r = only_group(groups.measure_groups([h, head("Next", 80)], [], [words])[0])
        assert r["head_gap"] is None and r["pitch"] is None             # one bullet: no pitch

    def test_wrapped_org_or_role_is_skipped(self):
        # org wraps onto a second line: line 1 holds only its first words, so gaps[1] is not org -> bullet
        words = [line("Role", 0), line("Acme", 12), line("Corp", 24), line("B1", 36), line("B2", 48), line("Next", 90)]
        h: Mark = {**head("Role", 0), "org": "Acme Corp"}
        r = only_group(groups.measure_groups([h, head("Next", 90)], [], [words])[0])
        assert r["head_gap"] is None
        # role wraps: the org lands on line 2
        words = [line("Role", 0), line("more", 12), line("Acme", 24), line("B1", 36), line("B2", 48), line("Next", 90)]
        h = {**h, "org": "Acme"}
        r = only_group(groups.measure_groups([h, head("Next", 90)], [], [words])[0])
        assert r["head_gap"] is None

    def test_printed_in_detail_but_never_a_finding(self, capsys):
        words = [line("Role", 0), line("Acme", 12), line("B1", 24), line("B2", 36), line("Next", 80)]
        h: Mark = {**head("Role", 0), "org": "Acme"}
        out = groups.check_group_proximity("", "", heads=[h, head("Next", 80)], secs=[], pages=[words], detail=[])
        assert "head-gap=" in capsys.readouterr().out and all(lv is Level.OK for lv, _ in out)
