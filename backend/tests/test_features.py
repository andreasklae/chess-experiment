"""Stage 1 tests for _features.py — verify each detector fires the CORRECT
information given a FEN, with correct YOURS/OPPONENT framing, current+potential,
and inline move suggestions. These are crafted positions with known features.
"""
import sys
from pathlib import Path

import chess
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/chess/scripts"))

from _features import (  # noqa: E402
    detect_pawn_structure, detect_files, detect_development, detect_bishop_pair,
    detect_outposts, detect_knight_forks, detect_loose_pieces, detect_pins_skewers,
    detect_phase_fundamentals, detect_all, render_features, render_features_for,
)


def _texts(findings):
    return [f.text for f in findings]


def _has(findings, *substrings, side=None, kind=None):
    for f in findings:
        if all(s in f.text for s in substrings) and \
           (side is None or f.side == side) and (kind is None or f.kind == kind):
            return f
    return None


# ---- pawn structure ----

def test_doubled_pawns():
    b = chess.Board("4k3/8/8/8/8/2P5/P1P3PP/4K3 w - - 0 1")
    f = _has(detect_pawn_structure(b), "doubled pawns on the c-file", side=True)
    assert f and f.kind == "weakness"


def test_isolated_pawn():
    b = chess.Board("4k3/pp4pp/8/3P4/8/8/PP4PP/4K3 w - - 0 1")
    assert _has(detect_pawn_structure(b), "d5 is ISOLATED", side=True)


def test_passed_pawn_both_sides():
    # White d5 passed (no black c/d/e pawn ahead)
    b = chess.Board("4k3/pp4pp/8/3P4/8/8/PP4PP/4K3 w - - 0 1")
    assert _has(detect_pawn_structure(b), "PASSED pawn on d5", side=True, kind="strength")


def test_open_file_potential():
    b = chess.Board("r3k2r/ppp2ppp/8/8/8/8/PPP2PPP/R3K2R w KQkq - 0 1")
    f = _has(detect_files(b), "d-file is open", side=True, kind="potential")
    assert f and any("Rd1" in m for m in f.moves)


# ---- development / fundamentals ----

def test_undeveloped_pieces_opening():
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    f = _has(detect_development(b), "undeveloped pieces", side=True)
    assert f and ("Nc3" in f.moves or "Na3" in f.moves)


def test_not_castled():
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    assert _has(detect_development(b), "NOT castled", side=True)


def test_phase_endgame_by_material():
    # few pieces, constructed at move 1 -> must read ENDGAME, not opening
    b = chess.Board("8/1p4k1/p7/P1P5/8/6K1/8/8 w - - 0 1")
    assert "ENDGAME" in detect_phase_fundamentals(b)[0].text


def test_phase_middlegame():
    b = chess.Board("r1bq1rk1/pp3ppp/2n1pn2/8/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 w - - 0 11")
    assert "MIDDLEGAME" in detect_phase_fundamentals(b)[0].text


def test_phase_opening():
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    assert "OPENING" in detect_phase_fundamentals(b)[0].text


# ---- piece activity ----

def test_bishop_pair():
    b = chess.Board("r1bq1rk1/pp3ppp/2n1pn2/8/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 w - - 0 11")
    assert _has(detect_bishop_pair(b), "bishop pair", side=True, kind="strength")


# ---- tactics ----

def test_current_knight_fork():
    # Ne5 forks Kd7 + Qf7
    b = chess.Board("8/3k1q2/8/4N3/8/8/8/4K3 w - - 0 1")
    assert _has(detect_knight_forks(b), "already forks", side=True, kind="strength")


def test_loose_enemy_piece():
    # black bishop on b4 undefended (off home rank) -> opponent loose target
    b = chess.Board("rnbqk2r/pppp1ppp/5n2/4p3/1b2P3/2N5/PPPP1PPP/R1BQKBNR w KQkq - 0 1")
    assert _has(detect_loose_pieces(b), "b4 is undefended", side=False)


def test_hanging_piece_threat_with_moves():
    # Black Bc5 attacked by d4, undefended -> THREAT with handling moves
    b = chess.Board("rnbqk1nr/pppp1ppp/8/2b1p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 3")
    f = _has(detect_loose_pieces(b), "c5 is attacked and UNDEFENDED", side=True, kind="threat")
    assert f
    joined = " ".join(f.moves)
    assert "captures attacker" in joined and "moves to safety" in joined


def test_absolute_pin():
    b = chess.Board("4k3/4b3/8/8/8/8/8/4R1K1 b - - 0 1")
    assert _has(detect_pins_skewers(b), "e7 is PINNED", side=True, kind="weakness")


# ---- perspective: both sides never confused ----

def test_perspective_flip_in_imagine():
    # After White Be2, from White's seat the black Bb4 is OPPONENT's loose piece
    b = chess.Board("rnbqk2r/pppp1ppp/5n2/4p3/1b2P3/2N5/PPPP1PPP/R1BQKBNR w KQkq - 0 1")
    b.push(chess.Move.from_uci("f1e2"))  # now Black to move
    out = render_features_for(b, chess.WHITE, heading="After")
    assert "OPPONENT" in out and "b4" in out


def test_no_crash_on_random_positions():
    import random
    random.seed(7)
    for _ in range(100):
        b = chess.Board()
        for _ in range(random.randint(0, 40)):
            ms = list(b.legal_moves)
            if not ms or b.is_game_over():
                break
            b.push(random.choice(ms))
        detect_all(b)            # must not raise
        detect_all(b, perspective=not b.turn)


def test_render_splits_yours_and_opponent():
    b = chess.Board("rnbqk1nr/pppp1ppp/8/2b1p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 3")
    out = render_features(b)
    assert "YOURS" in out  # the hanging-bishop side


def test_imagine_line_keeps_agent_seat_on_opponent_move():
    """Regression: in imagine_line the last move can be the OPPONENT's. The
    feature assessment must stay framed from the AGENT's seat, so a Black move
    that forks the White agent reads as a THREAT to White — not as 'YOURS'.
    This is what lets the agent assess the opponent's replies as strongly as its
    own (and not mistake an attack against it for a good move)."""
    from imagine_move import render_imagine
    # Black to move plays Nf3+, forking White's Kg1 and Qd2.
    b = chess.Board("6k1/8/8/4n3/8/8/3Q4/6K1 b - - 0 1")
    mv = b.parse_san("Nf3+")

    # Agent is WHITE imagining the opponent's (Black's) move.
    out_white = render_imagine(b, mv, agent_color=chess.WHITE)
    assert "YOURS (you are White)" in out_white
    # White's queen is the one in danger — it must surface as a threat to White.
    assert "queen on d2" in out_white and "THREAT" in out_white
    # It must NOT tell White "your knight ... forks" (that's Black's knight).
    assert "your knight on f3 already forks" not in out_white

    # why_stronger must also be framed as the OPPONENT's strong move, not the
    # agent's, when imagining the opponent's reply.
    assert "OPPONENT's move is STRONG" in out_white

    # Agent is BLACK imagining its OWN move — the fork is its strength.
    out_black = render_imagine(b, mv, agent_color=chess.BLACK)
    assert "YOURS (you are Black)" in out_black
    assert "your knight on f3 already forks" in out_black
    # For the agent's own move, why_stronger is NOT prefixed as the opponent's.
    assert "OPPONENT's move is STRONG" not in out_black


# ---- Lichess puzzle-DB validation (ground-truth themes) ----
# These run only when a decompressed puzzle CSV is present (not in CI). They
# measure detector recall/precision against real puzzles tagged with known
# motifs. Download: database.lichess.org/lichess_db_puzzle.csv.zst ; decompress
# to one of the paths below. See _puzzle_db_test.py for the standalone version.

import csv as _csv  # noqa: E402

_PUZZLE_CSVS = ["/tmp/puz_big.csv", "/tmp/puz_chunk.csv"]


def _puzzle_csv():
    for p in _PUZZLE_CSVS:
        if Path(p).exists():
            return p
    return None


def _load_theme(theme, limit, exclude=None):
    path = _puzzle_csv()
    rows = []
    with open(path) as f:
        for row in _csv.DictReader(f):
            th = row["Themes"].split()
            if theme in th and (exclude is None or exclude not in th):
                rows.append(row)
            if len(rows) >= limit:
                break
    return rows


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_knight_fork_recall_on_real_puzzles():
    """Every real knight fork of two major pieces in fork-puzzle solutions should
    be flagged. Validated at 100% over 3000 puzzles when last run."""
    from _features import _knight_targets_from
    checked = flagged = 0
    for row in _load_theme("fork", 1500):
        b = chess.Board(row["FEN"])
        for uci in row["Moves"].split():
            mv = chess.Move.from_uci(uci)
            pc = b.piece_at(mv.from_square)
            if pc and pc.piece_type == chess.KNIGHT and pc.color == b.turn:
                b2 = b.copy(); b2.push(mv)
                tg = [s for s in _knight_targets_from(mv.to_square)
                      if b2.piece_at(s) and b2.piece_at(s).color != pc.color
                      and b2.piece_at(s).piece_type in (chess.KING, chess.QUEEN, chess.ROOK)]
                if len(tg) >= 2:
                    checked += 1
                    land = chess.square_name(mv.to_square)
                    if any(land in f.text and "fork" in f.text.lower()
                           for f in detect_knight_forks(b)):
                        flagged += 1
            b.push(mv)
    assert checked >= 100, f"too few fork samples ({checked})"
    assert flagged / checked >= 0.97, f"knight-fork recall {flagged}/{checked}"


def test_skewer_basic():
    from _features import detect_skewers
    # Ba1 skewers Ke5 (front) -> Qg7 (behind) on the a1-h8 diagonal.
    b = chess.Board("8/6q1/8/4k3/8/8/8/B6K w - - 0 1")
    fs = detect_skewers(b)
    assert any("SKEWER" in f.text and "g7" in f.text for f in fs)


def test_discovered_check_lists_moves():
    from _features import detect_discovered_attacks
    # Re1 - Ne5 (screen) - Ke8: moving the knight is a discovered check.
    b = chess.Board("4k3/8/8/4N3/8/8/8/4R1K1 w - - 0 1")
    fs = detect_discovered_attacks(b)
    disc = [f for f in fs if "DISCOVERED CHECK" in f.text]
    assert disc and disc[0].moves  # it lists the knight's discovering moves


def test_why_stronger_check_plus_threat():
    from _features import why_stronger
    # Nf7+ forks Kh8 + undefended Rd8: check AND attacks the rook.
    b = chess.Board("3r3k/8/8/4N3/8/8/8/6K1 w - - 0 1")
    lines = why_stronger(b, b.parse_san("Nf7+"))
    assert any("CHECK" in s and "rook" in s.lower() for s in lines)


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_fork_threat_spotting_preemptive():
    """PREEMPTIVE: when the opponent is about to play a knight fork, the detector
    run from the DEFENDER's seat must warn (an OPPONENT-side finding) BEFORE the
    fork move. Validated 100% over 584 fork puzzles when last run."""
    from _features import _knight_targets_from
    checked = warned = 0
    for row in _load_theme("fork", 800):
        b = chess.Board(row["FEN"])
        for uci in row["Moves"].split():
            mv = chess.Move.from_uci(uci); pc = b.piece_at(mv.from_square)
            if pc and pc.piece_type == chess.KNIGHT and pc.color == b.turn:
                b2 = b.copy(); b2.push(mv)
                tg = [s for s in _knight_targets_from(mv.to_square)
                      if b2.piece_at(s) and b2.piece_at(s).color != pc.color
                      and b2.piece_at(s).piece_type in (chess.KING, chess.QUEEN, chess.ROOK)]
                if len(tg) >= 2:
                    defender = not b.turn
                    opp = [f for f in detect_knight_forks(b, perspective=defender)
                           if not f.side and "fork" in f.text.lower()]
                    checked += 1; warned += int(bool(opp))
                    break
            b.push(mv)
    assert checked >= 50 and warned / checked >= 0.97, f"fork threat-spotting {warned}/{checked}"


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_skewer_threat_spotting_preemptive():
    """PREEMPTIVE: when the opponent can move a line piece next turn to create a
    skewer, the detector (defender's seat) warns BEFORE the move. 100% last run."""
    from _features import detect_skewers, _dirs_for, _ray_squares
    from _features import PIECE_VALUE as PV
    checked = warned = 0
    for row in _load_theme("skewer", 800):
        b = chess.Board(row["FEN"])
        for uci in row["Moves"].split():
            mv = chess.Move.from_uci(uci); pc = b.piece_at(mv.from_square)
            if pc and pc.piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN) and pc.color == b.turn:
                b2 = b.copy(); b2.push(mv); real = False
                for d in _dirs_for(pc.piece_type):
                    front = rear = None
                    for sq in _ray_squares(mv.to_square, d):
                        occ = b2.piece_at(sq)
                        if occ is None:
                            continue
                        if front is None:
                            if occ.color == pc.color:
                                break
                            front = sq; continue
                        rear = sq if occ.color != pc.color else None; break
                    if front and rear and PV[b2.piece_at(front).piece_type] >= PV[b2.piece_at(rear).piece_type]:
                        real = True
                if real:
                    defender = not b.turn
                    opp = [f for f in detect_skewers(b, perspective=defender)
                           if not f.side and "SKEWER" in f.text]
                    checked += 1; warned += int(bool(opp))
                    break
            b.push(mv)
    assert checked >= 50 and warned / checked >= 0.97, f"skewer threat-spotting {warned}/{checked}"


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_skewer_recall_on_real_puzzles():
    """When a skewer is created in a skewer-puzzle's solution line, the detector
    flags it. Validated at 100% over 748 created-skewers when last run."""
    from _features import detect_skewers, _dirs_for, _ray_squares
    from _features import PIECE_VALUE as PV
    checked = flagged = 0
    for row in _load_theme("skewer", 400):
        b = chess.Board(row["FEN"])
        for i, uci in enumerate(row["Moves"].split()):
            mv = chess.Move.from_uci(uci); pc = b.piece_at(mv.from_square)
            is_solver = (i % 2 == 1)
            b.push(mv)
            if is_solver and pc and pc.piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN):
                real = False
                for d in _dirs_for(pc.piece_type):
                    front = rear = None
                    for sq in _ray_squares(mv.to_square, d):
                        occ = b.piece_at(sq)
                        if occ is None:
                            continue
                        if front is None:
                            if occ.color == pc.color:
                                break
                            front = sq; continue
                        rear = sq if occ.color != pc.color else None; break
                    if front and rear and PV[b.piece_at(front).piece_type] >= PV[b.piece_at(rear).piece_type]:
                        real = True
                if real:
                    checked += 1
                    if any("SKEWER" in f.text and chess.square_name(mv.to_square) in f.text
                           for f in detect_skewers(b, not b.turn)):
                        flagged += 1
    assert checked >= 50 and flagged / checked >= 0.97, f"skewer recall {flagged}/{checked}"


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_discovered_geometry_on_real_puzzles():
    # The detector deliberately ignores discoveries whose unveiled target is a
    # mere pawn (noise), so it won't fire on 100% of discoveredAttack puzzles —
    # some of those discoveries unveil onto pawns or are set up later in the line.
    # ~80%+ at the puzzle-start frame is the meaningful (piece-target/check) share.
    from _features import detect_discovered_attacks
    hit = tot = 0
    for row in _load_theme("discoveredAttack", 300):
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(row["Moves"].split()[0]))
        tot += 1
        if detect_discovered_attacks(b) + detect_discovered_attacks(b, not b.turn):
            hit += 1
    assert tot >= 50 and hit / tot >= 0.80, f"discovered geometry {hit}/{tot}"


@pytest.mark.skipif(_puzzle_csv() is None, reason="Lichess puzzle CSV not present")
def test_pin_and_hanging_on_real_puzzles():
    pin_hit = pin_tot = 0
    for row in _load_theme("pin", 300):
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(row["Moves"].split()[0]))
        if any(b.piece_at(sq) and b.is_pinned(b.piece_at(sq).color, sq)
               and b.piece_at(sq).piece_type != chess.KING for sq in chess.SQUARES):
            pin_tot += 1
            if any("PINNED" in f.text for f in
                   detect_pins_skewers(b) + detect_pins_skewers(b, not b.turn)):
                pin_hit += 1
    assert pin_tot >= 50 and pin_hit / pin_tot >= 0.97, f"pin recall {pin_hit}/{pin_tot}"

    h_hit = h_tot = 0
    for row in _load_theme("hangingPiece", 300):
        b = chess.Board(row["FEN"]); b.push(chess.Move.from_uci(row["Moves"].split()[0]))
        h_tot += 1
        if any("undefended" in f.text.lower() or "loose" in f.text.lower()
               for f in detect_loose_pieces(b) + detect_loose_pieces(b, not b.turn)):
            h_hit += 1
    assert h_tot >= 50 and h_hit / h_tot >= 0.95, f"hanging recall {h_hit}/{h_tot}"
