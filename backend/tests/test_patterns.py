"""Tests for the wiki-driven pattern trigger matcher (_patterns.py).

The fairness contract under test: hints fire on geometry-present (including
positions where the mate is refuted — that's the point), never on
mate-verified; every hint names a wiki page; patterns without pages
produce nothing.
"""

import sys
from pathlib import Path

import chess

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _patterns import _parse_templates, match_patterns  # noqa: E402
from _radar import render_radar  # noqa: E402


class TestTemplateParsing:
    def test_templates_found_in_wiki(self):
        templates = _parse_templates()
        names = {t["path"] for t in templates}
        assert any("arabian" in n for n in names)
        assert any("smothered" in n for n in names)
        assert any("ladder" in n for n in names)

    def test_every_template_names_an_existing_page(self):
        refs = Path(__file__).resolve().parents[1] / "skills" / "chess" / "references"
        for t in _parse_templates():
            assert (refs / t["path"]).exists()


class TestMatching:
    def test_arabian_geometry_fires(self):
        # R+N, enemy king in corner — geometry present, mate NOT yet there.
        out = match_patterns(chess.Board("7k/8/5N2/8/8/8/8/R6K w - - 0 1"))
        assert any("arabian" in line for line in out)

    def test_hint_fires_even_when_refuted(self):
        # Same inventory/zone but black has a defender that refutes any
        # quick mate — the hint must STILL fire (geometry, not verification).
        out = match_patterns(chess.Board("6qk/8/5N2/8/8/8/8/R6K w - - 0 1"))
        assert any("arabian" in line for line in out)

    def test_no_knight_no_arabian(self):
        out = match_patterns(chess.Board("7k/8/8/8/8/8/8/R6K w - - 0 1"))
        assert not any("arabian" in line for line in out)

    def test_smothered_needs_own_blockers(self):
        # Corner king but no own pieces boxing it: smothered must not fire.
        out = match_patterns(chess.Board("7k/8/5N2/8/8/8/8/Q6K w - - 0 1"))
        assert not any("smothered" in line for line in out)
        # Boxed corner king (own rook g8, pawns g7/h7): fires.
        out = match_patterns(chess.Board("6rk/6pp/5N2/8/8/8/8/Q6K w - - 0 1"))
        assert any("smothered" in line for line in out)

    def test_blind_swine_needs_pig_on_seventh(self):
        # One rook already on the 7th + a second rook: fires.
        out = match_patterns(chess.Board("6k1/R4ppp/8/8/8/8/8/1R4K1 w - - 0 1"))
        assert any("blind swine" in line for line in out)
        # Two rooks still at home: gate keeps it quiet.
        out = match_patterns(chess.Board("6k1/5ppp/8/8/8/8/8/RR4K1 w - - 0 1"))
        assert not any("blind swine" in line for line in out)
        # Only one rook: never fires.
        out = match_patterns(chess.Board("6k1/R4ppp/8/8/8/8/8/6K1 w - - 0 1"))
        assert not any("blind swine" in line for line in out)

    def test_quiet_opening_produces_no_pattern_hints(self):
        out = match_patterns(chess.Board())
        assert out == []

    def test_hint_cap(self):
        # A position satisfying many templates still yields at most 3 hints.
        out = match_patterns(chess.Board("6rk/6pp/5N2/7Q/2B5/8/8/RR5K w - - 0 1"))
        assert len(out) <= 3

    def test_every_hint_traces_to_a_page(self):
        out = match_patterns(chess.Board("6rk/6pp/5N2/7Q/2B5/8/8/RR5K w - - 0 1"))
        for line in out:
            assert ".md" in line and "read" in line


class TestRadarIntegration:
    def test_radar_carries_pattern_triggers(self):
        radar = render_radar(chess.Board("7k/8/5N2/8/8/8/8/R6K w - - 0 1"))
        assert "Pattern trigger" in radar

    def test_radar_survives_matcher_problems(self):
        # Even with no references dir reachable the radar must not crash —
        # simulated indirectly: a position with no triggers still renders
        # other sections fine.
        radar = render_radar(chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1"))
        assert "forced mate" in radar
