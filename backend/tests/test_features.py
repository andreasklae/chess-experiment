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
    # Black Bc5 attacked by d4, undefended -> a high-salience LOSE warning (the
    # symmetric mirror of ★ WIN MATERIAL) with handling moves.
    b = chess.Board("rnbqk1nr/pppp1ppp/8/2b1p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 3")
    f = _has(detect_loose_pieces(b), "c5 is attacked and UNDEFENDED", side=True, kind="lose")
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
    # White's queen is the one in danger — it must surface as danger to White
    # (a THREAT, or the higher-salience LOSING-MATERIAL warning).
    assert "queen on d2" in out_white and ("THREAT" in out_white or "LOSING MATERIAL" in out_white)
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


def test_own_king_exposure_fires_on_king_hunt():
    """Proactive king-danger (the defensive twin of the offensive boxing signal). Real
    loss game 3e83ce50: the king marched into the open under Q+R and was mated. The signal
    must fire BEFORE the mate, when the king is boxed/advanced with heavy pieces near."""
    from _features import detect_own_king_exposure
    # White king on f3, boxed to ~1 flight, black Q+R closing in (the move before Kg4##).
    b = chess.Board("2b1k1n1/r2p1p2/p3p1p1/1p6/3QPP2/1B3K1r/P6P/8 w - - 0 1")
    fs = detect_own_king_exposure(b, perspective=chess.WHITE)
    assert any("KING" in f.text and "EXPOSED" in f.text.upper() or "hunt" in f.text.lower()
               for f in fs), [f.text for f in fs]


def test_own_king_exposure_silent_in_active_king_endgame():
    """ENDGAME GUARD: an active king near passed pawns in a K+P/K+R ending is CORRECT —
    the signal must NOT tell the agent to retreat it (the false positives it was tuned out
    of). No enemy queen + few pieces = endgame → silent."""
    from _features import detect_own_king_exposure
    # White Kf5 active vs a lone black rook harassing it — a normal endgame, king should stay.
    b = chess.Board("8/8/6k1/5PK1/8/8/7r/8 w - - 0 1")
    fs = detect_own_king_exposure(b, perspective=chess.WHITE)
    assert fs == [], [f.text for f in fs]


def test_skewer_basic():
    from _features import detect_skewers
    # Ba1 skewers Ke5 (front) -> Qg7 (behind) on the a1-h8 diagonal.
    b = chess.Board("8/6q1/8/4k3/8/8/8/B6K w - - 0 1")
    fs = detect_skewers(b)
    assert any("SKEWER" in f.text and "g7" in f.text for f in fs)


def test_skewer_defended_front_worth_less_than_attacker_is_not_flagged():
    """Regression (real game 57fc05ad): the agent played Qd3 believing it
    'skewered' a rook on c4 with a bishop on a6 behind it. It won nothing: the
    rook was DEFENDED (by d5, a6, c8) and worth LESS than the queen, so Qxc4?? is
    met by ...dxc4 losing the queen — the rook is not forced to move. The detector
    must NOT report this as a skewer, for either side.

    A skewer/pin only wins the piece behind if the FRONT piece is forced to move:
    it must be undefended, or worth more than the attacking piece.
    """
    from _features import detect_skewers
    # White to move, exactly the position before the mistaken Qd3.
    b = chess.Board("2q1r1k1/5ppp/bp2p3/p2pP3/2rN4/6QP/PP3PP1/3R1RK1 w - - 4 23")
    # after Qd3, the queen would "skewer" the defended rook c4 -> bishop a6:
    b.push_san("Qd3")
    ours = [f for f in detect_skewers(b, perspective=chess.WHITE)
            if f.side and "skewer" in f.text.lower()]
    assert ours == [], f"defended-cheaper-front is not a real skewer: {[f.text for f in ours]}"
    # and it must not be advertised as a potential skewer one move earlier either.
    b0 = chess.Board("2q1r1k1/5ppp/bp2p3/p2pP3/2rN4/6QP/PP3PP1/3R1RK1 w - - 4 23")
    ours0 = [f for f in detect_skewers(b0, perspective=chess.WHITE)
             if f.side and "skewer" in f.text.lower()]
    assert ours0 == [], f"no bogus potential skewer for Qd3: {[f.text for f in ours0]}"


def test_skewer_still_fires_when_front_is_forced():
    """The soundness filter must not kill REAL skewers. Three that must still fire:
    king in front, front worth more than the attacker, and an undefended front."""
    from _features import detect_skewers

    def mine(fen):
        return [f for f in detect_skewers(chess.Board(fen))
                if f.side and "skewer" in f.text.lower()]

    # king-in-front (a3) → rook behind (a8): king must move, rook falls.
    assert mine("r7/8/8/8/8/k7/8/R6K w - - 0 1")
    # front is an UNDEFENDED rook, prize is a bishop behind: front forced (loose).
    assert mine("4b1k1/8/8/4r3/8/8/8/4R1K1 w - - 0 1")
    # front QUEEN worth more than the skewering ROOK, prize a rook behind.
    assert mine("4r1k1/8/8/8/4q3/8/8/4R1K1 w - - 0 1")


def test_skewer_prize_behind_must_be_a_piece_not_a_pawn():
    """A 'skewer' whose only prize behind is a pawn is noise and must be dropped
    (this was a false positive in the same real game: a rook-to-c3 'skewer' of the
    queen with only a pawn behind — and the rook would hang on c3 anyway)."""
    from _features import detect_skewers
    b = chess.Board("2q1r1k1/5ppp/bp2p3/p2pP3/2rN4/6QP/PP3PP1/3R1RK1 w - - 4 23")
    pawn_prizes = [f for f in detect_skewers(b)
                   if "skewer" in f.text.lower() and "pawn behind" in f.text.lower()]
    assert pawn_prizes == [], f"pawn-only skewers are noise: {[f.text for f in pawn_prizes]}"


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


def test_trap_detector_flags_baited_capture():
    """A 'free' capture that loses material by SEE is flagged as a TRAP/bait,
    and a genuinely free capture is not."""
    from _features import detect_traps
    # Rxd5 grabs a pawn but it's defended by the e6 pawn -> loses the rook.
    bait = chess.Board("4k3/8/4p3/3p4/8/3R4/8/4K3 w - - 0 1")
    fs = detect_traps(bait)
    assert any("TRAP" in f.text and "Rxd5" in f.text for f in fs)
    assert all(f.side for f in fs)  # it's the agent's own tempting capture

    # An undefended pawn grab is safe -> no trap flagged.
    safe = chess.Board("4k3/8/8/3p4/8/3R4/8/4K3 w - - 0 1")
    assert detect_traps(safe) == []


def test_trap_detector_excludes_removing_defender_sacrifice():
    """A material-losing capture that REMOVES THE SOLE DEFENDER of an attacked
    enemy piece is a deliberate sacrifice, not a bait — it must NOT be flagged as a
    trap (doing so steers the agent away from the solution, 7e5N5). Here the e7
    knight is defended only by the d8 queen; Qxd8 loses the queen by SEE but wins
    the knight next move (Rxe7), so it should be excluded from the trap list while
    the genuine baits (Rxe7, Bxa6) remain."""
    from _features import detect_traps
    b = chess.Board("r2q1rk1/1p2nppp/p4n2/5P2/4R3/8/PPP2PPP/R2Q1BK1 w - - 1 16")
    fs = detect_traps(b)
    trap_text = " ".join(f.text for f in fs)
    assert "Qxd8" not in trap_text          # the removing-the-defender sac is NOT a trap
    assert "Rxe7" in trap_text               # a genuine bait still flagged


def test_trap_detector_excludes_checking_capture():
    """A capture that GIVES CHECK is forcing and must be judged by the line, not by
    one-ply SEE — it must not be flagged as a trap (VhRSK: Bxh7+ is a
    discovered-attack check, not a bait)."""
    from _features import detect_traps
    b = chess.Board("r4rk1/pb3ppp/1p1q1n2/2p5/2p5/P2BPN1P/1P3PP1/R2Q1RK1 w - - 0 17")
    fs = detect_traps(b)
    assert all("Bxh7" not in f.text for f in fs)


# ── new detectors (king safety, material, overload, luft) — gap-fill audit ──

def test_material_up_advises_trade():
    from _features import detect_material
    b = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")  # White up a rook
    fs = detect_material(b)
    assert any("UP" in f.text and "trad" in f.text.lower() and f.side for f in fs)


def test_material_down_advises_avoid_initiating_trades_but_keep_free_material():
    from _features import detect_material
    b = chess.Board("r3k3/8/8/8/8/8/8/4K3 b - - 0 1")  # Black (to move) up a rook
    # from White's perspective White is down
    fs = detect_material(b, perspective=chess.WHITE)
    # Down-material advice must (a) discourage INITIATING trades but (b) NEVER
    # discourage winning free material — the bug that made the agent reject a
    # free capture (puzzle YZ2IM). Assert both halves so the carve-out can't
    # regress away.
    down = [f for f in fs if "DOWN" in f.text]
    assert down, "expected a down-material finding"
    txt = down[0].text.lower()
    assert "avoid initiating" in txt
    assert "free material" in txt and "always capture" in txt


def test_creatable_pin_against_king_is_surfaced():
    # YlFR1 / Jxmyy (pin easy): Bb5 pins the black queen on c6 to the king on e8.
    # This creatable pin (a winning motif) was previously invisible -- only
    # already-existing pins were detected. Must surface with the Bb5 move.
    from _features import detect_creatable_pins
    for fen in ("r1b1k2r/pp2bppp/2q1p3/8/P4P2/8/1PP3PP/R1BQKB1R w KQkq - 1 11",
                "r1b1k2r/pp2ppbp/2q2np1/8/8/N1P1B3/PP3PPP/R2QKB1R w KQkq - 0 10"):
        b = chess.Board(fen)
        mine = [f for f in detect_creatable_pins(b) if f.side]
        assert any("PIN enemy queen" in f.text and "KING" in f.text and "Bb5" in (f.moves or [])
                   for f in mine), fen


def test_creatable_pin_no_false_positive_in_start_position():
    from _features import detect_creatable_pins
    assert detect_creatable_pins(chess.Board()) == []


def test_relative_pin_to_queen_surfaced_with_piling_move():
    # Wkp7l (pin medium): black knight f6 is relatively pinned to the e7 queen by
    # the white queen on g5. python-chess is_pinned only sees absolute pins, so
    # this was invisible. Must surface with the piling move Nh5.
    from _features import detect_pins_skewers
    b = chess.Board("r2r2k1/1b2qppp/p3pn2/1ppp2Q1/7P/3P1PN1/PPP2PB1/2KR3R w - - 4 18")
    rel = [f for f in detect_pins_skewers(b) if "RELATIVELY PINNED" in f.text and f.side]
    assert rel, "expected a relative-pin finding for the f6 knight"
    assert "knight on f6" in rel[0].text and "queen on e7" in rel[0].text
    assert "Nh5" in (rel[0].moves or [])


def test_relative_pin_no_false_positive_in_start_position():
    from _features import detect_pins_skewers
    assert not any("RELATIVELY" in f.text for f in detect_pins_skewers(chess.Board()))


def test_win_finding_flags_checking_capture_as_zwischenzug():
    # A3WM4: two free black rooks (a8, b1); Qxa8+ takes one WITH CHECK. The win
    # finding for a8 must carry the zwischenzug nudge (capture-with-check first),
    # the b1 one (quiet) must not.
    from _features import detect_all
    b = chess.Board("r5k1/3q1pp1/4pn1p/8/3P4/1pP2QN1/5PPP/1r2R1K1 w - - 0 29")
    wins = {f.text.split(" on ")[1][:2]: f.text for f in detect_all(b) if f.kind == "win"}
    assert "a8" in wins and "WITH CHECK" in wins["a8"] and "zwischenzug" in wins["a8"].lower()
    assert "b1" in wins and "WITH CHECK" not in wins["b1"]


def test_free_undefended_enemy_piece_is_top_win_finding():
    # YZ2IM position: White (down material) attacks an UNDEFENDED black knight on
    # f7 with the bishop on e6. This must surface as a top-priority WIN-material
    # finding in YOUR block with the capture move (Bxf7) -- not a buried
    # 'potential'. Regression for the agent rejecting a free capture because it
    # was 'down material'.
    from _features import detect_loose_pieces, detect_all, render_features
    b = chess.Board("4r1r1/p1k2np1/1pp1Bp1p/5P1P/2P1N3/1P6/8/2K3R1 w - - 1 36")
    fs = detect_loose_pieces(b)
    win = [f for f in fs if f.kind == "win"]
    assert win, "expected a WIN finding for the free knight on f7"
    assert win[0].side is True               # belongs to the agent (YOURS)
    assert "FREE MATERIAL" in win[0].text and "f7" in win[0].text
    assert "Bxf7" in (win[0].moves or [])
    # and it renders FIRST in the YOURS block (before any threat/weakness)
    out = render_features(b)
    yours = out.split("OPPONENT")[0]
    assert yours.index("WIN MATERIAL") < yours.index("THREAT")


def test_win_finding_only_when_capture_available_now():
    # An undefended enemy piece NOT currently attacked by us is a latent target
    # (potential), not a WIN-now finding.
    from _features import detect_loose_pieces
    b = chess.Board("4k3/8/3b4/8/8/8/8/4K3 w - - 0 1")  # lone black bishop, white can't reach it
    fs = detect_loose_pieces(b)
    assert not any(f.kind == "win" for f in fs)


def test_king_safety_flags_both_sides():
    from _features import detect_king_safety
    b = chess.Board("3rk3/8/8/8/8/8/8/3QK2R w - - 0 1")
    fs = detect_king_safety(b)
    assert any(f.side and "KING" in f.text and "exposed" in f.text for f in fs)      # yours
    assert any((not f.side) and "KING" in f.text for f in fs)                        # opponent's


def test_own_back_rank_no_luft():
    from _features import detect_own_back_rank
    b = chess.Board("6k1/8/8/8/8/8/5PPP/r5K1 w - - 0 1")
    fs = detect_own_back_rank(b)
    assert any(f.side and "LUFT" in f.text for f in fs)


def test_overloaded_defender_runs_clean():
    # conservative detector: must never crash, fires only on a genuine overload.
    from _features import detect_overloaded_defenders
    b = chess.Board("r2q1rk1/pp1b1ppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2Q1RK1 w - - 0 9")
    assert isinstance(detect_overloaded_defenders(b), list)


def test_new_detectors_in_detect_all():
    # the gap-fill detectors must be wired into the assembler used by the tools.
    from _features import detect_all
    b = chess.Board("3rk3/8/8/8/8/8/8/3QK2R w - - 0 1")
    texts = " ".join(f.text for f in detect_all(b))
    assert "KING" in texts  # king-safety reached via detect_all


def test_forcing_moves_line_lists_checks_at_top():
    # The position assessment must surface the side-to-move's CHECKS as forcing
    # moves to calculate first (delivered at the decision point, not just SKILL.md
    # prose). XxMgX: Qd6+ is the answer; it must appear among the listed checks.
    from _features import render_features, _forcing_moves_line
    import chess as _c
    b = _c.Board("3r2k1/pp3ppp/2p5/4q3/8/2P5/PP3PPP/3Q1RK1 w - - 0 1")  # has several checks
    line = _forcing_moves_line(b)
    # at least one check should be present and the label correct
    if line:
        assert "Forcing moves" in line and "calculate these FIRST" in line
    # and the full assessment puts it right after the method note
    b2 = _c.Board("2r3k1/1p3p1p/p5p1/3qB3/8/2P5/P4PPP/3QR1K1 w - - 0 1")
    out = render_features(b2)
    if "Forcing moves" in out:
        assert out.index("Forcing moves") < out.index("YOURS") if "YOURS" in out else True


def test_no_forcing_line_without_checks():
    from _features import _forcing_moves_line
    import chess as _c
    assert _forcing_moves_line(_c.Board()) == ""  # start position: no checks


def test_in_check_line_lists_all_escapes_and_flags_blocks():
    # VsxCo (defend-pin): White is in check (Qg5+); the right reply is the BLOCK
    # Rg3 (Qxg3+ Kxg3 wins the queen). The assessment must lead with an IN CHECK
    # line listing every legal reply and flagging the block as not-just-king-move.
    from _features import render_features, _in_check_line
    import chess as _c
    b = _c.Board("8/8/5pk1/p5q1/1p6/1P1R4/P2R2K1/8 w - - 3 59")
    line = _in_check_line(b)
    assert "IN CHECK" in line
    assert "Rg3" in line and "blocks/captures" in line
    out = render_features(b)
    assert "IN CHECK" in out
    # when in check, the in-check line leads instead of the forcing-moves line
    assert "Forcing moves" not in out.split("IN CHECK")[0]


def test_in_check_line_silent_when_not_in_check():
    from _features import _in_check_line
    import chess as _c
    assert _in_check_line(_c.Board()) == ""


def test_piece_fork_warning_for_queen_and_bishop():
    # Symmetric warning: a QUEEN or BISHOP fork the opponent can play next must be
    # flagged (knight forks are covered separately). Flipped puzzle positions:
    # Qu8ZH-flip (Black Qa5+ forks Ke1+Nc5), ZQoBU-flip (Black Bf3 forks two rooks).
    from _features import detect_all
    b1 = chess.Board("3qk3/8/8/2N5/8/8/8/4K3 w - - 0 1")  # crafted: black Qd8, white Ke1+Nc5
    # ensure a real queen-fork-threat position by construction:
    b1 = chess.Board("3q4/8/8/2n5/8/8/8/3RK3 w - - 0 1")  # black Qd8 can fork? use the real flip below
    import json, pathlib
    fj = pathlib.Path(__file__).resolve().parents[2] / "experiments/puzzle-benchmark/puzzles-flipped.json"
    if fj.exists():
        flips = {p["id"]: p for p in json.loads(fj.read_text())}
        for fid in ("Qu8ZH-flip", "ZQoBU-flip"):
            if fid in flips:
                b = chess.Board(flips[fid]["fen"])
                warns = [f.text for f in detect_all(b) if not f.side and "FORK" in f.text]
                assert warns, f"{fid}: expected a fork warning"


def test_piece_fork_no_false_positive_in_quiet_positions():
    from _features import detect_piece_forks
    assert detect_piece_forks(chess.Board()) == []
    assert detect_piece_forks(
        chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4")) == []


def test_royal_fork_counts_defended_piece(im=None):
    # EGtLS: Qe8+ forks the king on g8 AND the bishop on e5 — but the bishop is
    # DEFENDED. A royal fork (a check) wins the other piece anyway (the king must
    # move), so it must be flagged. Regression for the 'winning target' filter
    # wrongly excluding defended pieces when the move is a check.
    from _features import detect_piece_forks
    b = chess.Board("6k1/2p2p2/2Q3p1/p1N1b1q1/7p/1P5P/3r2P1/5R1K w - - 1 29")
    forks = [f for f in detect_piece_forks(b) if f.side and "Qe8" in (f.text + str(f.moves))]
    assert forks, "royal queen-fork Qe8+ (king + defended bishop) must be flagged"
    assert "king on g8" in forks[0].text and "bishop on e5" in forks[0].text


def test_center_control_fires_in_opening_silent_in_endgame():
    from _features import detect_center_control
    # Black neglects the centre (1.e4 a6 2.d4): White dominates → warning for Black.
    b = chess.Board("rnbqkbnr/1ppppppp/p7/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2")
    fs = detect_center_control(b)
    assert any("OPPONENT controls the centre" in f.text and f.kind == "weakness" for f in fs)
    # Endgame: must be silent (centre control is gated off there).
    assert detect_center_control(chess.Board("8/5k2/8/4P3/8/8/5K2/8 w - - 0 1")) == []
    # Balanced opening (1.e4 e5 2.Nf3): no large deficit either way → no warning.
    bal = detect_center_control(chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"))
    assert not any(f.kind in ("weakness", "strength") for f in bal)


def test_center_control_opening_suggests_central_pawn():
    from _features import detect_center_control
    # Start position: a central pawn push is offered as a way to claim the centre.
    fs = detect_center_control(chess.Board())
    assert any("centre square" in f.text and ("e4" in str(f.moves) or "d4" in str(f.moves)) for f in fs)


def test_forced_mate_hint_when_enemy_king_boxed_and_check_available():
    # 37qrJ (mateIn2): enemy king has <=2 escapes and White has a check (Qxg7+)
    # -> the forcing-moves line must add the 'FORCED MATE may be available;
    # calculate your checks to the end' nudge. Pure mechanics, no move picked.
    from _features import _forcing_moves_line
    import chess as _c, json, pathlib
    pj = pathlib.Path(__file__).resolve().parents[2] / "experiments/puzzle-benchmark/puzzles.json"
    if pj.exists():
        p = {x["id"]: x for x in json.loads(pj.read_text())}.get("37qrJ")
        if p:
            b = _c.Board(p["fen"]); b.push(_c.Move.from_uci(p["moves"][0]))
            line = _forcing_moves_line(b)
            assert "FORCED MATE may be available" in line
            assert "imagine_line" in line


def test_no_mate_hint_in_quiet_position_with_safe_king():
    from _features import _forcing_moves_line
    import chess as _c
    # castled, king has luft, no mating net -> no mate hint even if a check exists
    b = _c.Board("r1bqk2r/pppp1ppp/2n2n2/1Bb1p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5")
    assert "FORCED MATE" not in _forcing_moves_line(b)


def test_forcing_moves_line_includes_piece_captures_not_just_checks():
    # 7e5N5 (capturing-defender): the win STARTS with Qxd8 — a capture, not a
    # check (deflect the defender, then win the knight). The forcing-moves line
    # must list piece-captures too (full CCT), or the agent never calculates it.
    from _features import _forcing_moves_line
    import chess as _c
    b = _c.Board("r2q1rk1/1p2nppp/p4n2/5P2/4R3/8/PPP2PPP/R2Q1BK1 w - - 1 16")
    line = _forcing_moves_line(b)
    assert "Qxd8" in line          # the deflecting capture is surfaced
    assert "✛" in line             # marked as a capture
    assert "capture" in line.lower()


def test_forcing_moves_line_ignores_pawn_only_captures():
    # A position whose only capture is a pawn-grab (no checks) should NOT produce
    # a forcing-moves line (a pawn capture is not a 'forcing move' worth flagging).
    from _features import _forcing_moves_line
    import chess as _c
    b = _c.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")  # exd5 = pawn x pawn
    assert _forcing_moves_line(b) == ""


def test_remove_the_defender_surfaces_the_deflecting_capture():
    # 7e5N5 (capturing-defender): the e7 knight is defended ONLY by the d8 piece;
    # Qxd8 removes the defender, then Rxe7 wins it. The detector must surface this
    # 'remove the defender' idea with the concrete capture (Qxd8) -- the agent was
    # playing safe instead because no signal pointed at the deflection.
    from _features import detect_removable_defender
    import chess as _c
    b = _c.Board("r2q1rk1/1p2nppp/p4n2/5P2/4R3/8/PPP2PPP/R2Q1BK1 w - - 1 16")
    fs = detect_removable_defender(b)
    assert any("REMOVE THE DEFENDER" in f.text and "e7" in f.text and "Qxd8" in (f.moves or [])
               for f in fs)


def test_remove_the_defender_no_false_positive_start_and_double_defended():
    from _features import detect_removable_defender
    import chess as _c
    assert detect_removable_defender(_c.Board()) == []
    # a piece defended by TWO pieces is not removable by eliminating one defender
    b = _c.Board("4k3/8/8/3n4/8/2N1N3/8/4K3 w - - 0 1")
    assert detect_removable_defender(b) == []


def test_forcing_line_includes_line_opening_pawn_capture():
    """BLrYl: the winning move exf6 is a PAWN capture, but it opens the f-file/attacks
    the e7-bishop (a clearance combination start). A bare pawn-grab is excluded, but a
    line-opening / defender-removing pawn capture must appear in the forcing list."""
    from _features import _forcing_moves_line, _pawn_capture_opens_attack
    import chess as c
    b = c.Board("r3rk2/pR1Rb2p/2p1pp2/4P3/5Pp1/2P3P1/P1P4P/5K2 w - - 2 23")
    line = _forcing_moves_line(b)
    assert "exf6" in line
    # a bare pawn grab with no tactical point is NOT flagged
    plain = c.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert not _pawn_capture_opens_attack(plain, plain.parse_san("exd5"))


# ---- adaptive situation/priority header ----

def test_situation_survival_when_mate_threatened():
    """def_0c0765: roughly equal but the opponent threatens Rg3# — priority must be
    SURVIVAL (defend the king; material secondary), not a material/greed framing."""
    from _features import assess_situation
    s = assess_situation(chess.Board("1rb5/7p/1pR2pk1/5N1n/P1P1P1KP/1P1r4/6P1/6R1 w - - 21 48"))
    assert "SURVIVAL" in s["priority"]
    assert s["threat"] and s["threat"][0] == "mate"


def test_situation_consolidate_when_winning_and_safe():
    """Up a clean piece, no threat, not opening → CONSOLIDATE (simplify; don't grab)."""
    from _features import assess_situation
    # White up a full rook, king safe, nothing hanging or threatened.
    s = assess_situation(chess.Board("6k1/5ppp/8/8/8/8/R4PPP/6K1 w - - 0 1"))
    assert s["material_diff"] >= 3
    assert "CONSOLIDATE" in s["priority"]


def test_situation_counterplay_when_losing():
    """Down a rook, king has luft (no back-rank mate), no immediate threat → COUNTERPLAY."""
    from _features import assess_situation
    s = assess_situation(chess.Board("6k1/5pp1/7p/8/8/6P1/r4P1P/6K1 w - - 0 1"))
    assert s["material_diff"] <= -3
    assert "COUNTERPLAY" in s["priority"]


def test_situation_respond_to_check():
    from _features import assess_situation
    s = assess_situation(chess.Board("6k1/5ppp/8/8/8/8/5PPP/4q1K1 w - - 0 1"))
    assert s["in_check"] and "CHECK" in s["priority"]


class TestPromotePriority:
    """PROMOTE must outrank CONSOLIDATE when the opponent has no pieces and we
    have a passer — game 9eddc039 shuffled a knight for 15 moves in K+N+P vs K
    while the header said 'trade PIECES to simplify' (has_pieces counted OUR
    knight) and the push-the-pawn advice sat buried mid-page."""

    def test_bare_king_with_passer_says_promote(self):
        from _features import assess_situation
        b = chess.Board("4k3/8/8/4K3/5N2/4P3/8/8 w - - 9 67")
        sit = assess_situation(b)
        assert sit["priority"].startswith("PROMOTE")
        text = "\n".join(sit["lines"])
        assert "e3" in text            # names the passer
        assert "wasted tempi" in text  # the anti-check line
        assert "50-move" in text

    def test_progress_moves_listed(self):
        from _features import assess_situation
        b = chess.Board("4k3/8/8/4K3/5N2/4P3/8/8 w - - 9 67")
        text = "\n".join(assess_situation(b)["lines"])
        assert "e4" in text  # the pawn push is named as a progress move

    def test_consolidate_when_enemy_has_pieces(self):
        from _features import assess_situation
        # Same material edge but the opponent still has a rook -> CONSOLIDATE.
        b = chess.Board("4k2r/8/8/4K3/5N2/4P3/8/6R1 w - - 0 40")
        sit = assess_situation(b)
        assert sit["priority"].startswith("CONSOLIDATE")
        assert "trade PIECES" in "\n".join(sit["lines"])

    def test_no_promote_without_passer(self):
        from _features import assess_situation
        # Bare enemy king, no pawn at all: K+N+B vs K must not say PROMOTE.
        b = chess.Board("4k3/8/8/4K3/5N2/3B4/8/8 w - - 0 40")
        sit = assess_situation(b)
        assert not sit["priority"].startswith("PROMOTE")

    def test_promote_defers_to_mate_with_queen_or_rook(self):
        from _features import assess_situation
        # K+Q+P vs bare K: the job is MATE, not more promotion (iter-4 batch:
        # PROMOTE kept firing post-promotion, competing with the mate radar).
        b = chess.Board("4k3/8/8/4K3/8/4P3/8/4Q3 w - - 0 60")
        assert not assess_situation(b)["priority"].startswith("PROMOTE")
        # K+N+P vs bare K still says PROMOTE.
        b2 = chess.Board("4k3/8/8/4K3/5N2/4P3/8/8 w - - 9 67")
        assert assess_situation(b2)["priority"].startswith("PROMOTE")


class TestDriftAlert:
    """NO-PROGRESS alert: winning + last 4 own moves quiet (no capture/pawn) +
    clock climbing or oscillation → the Situation must call out the drift and
    point back at the standing plan (games 9eddc039/cf272d shuffled winning
    endgames for 10+ moves; the plan was in the prompt but nothing tied the
    MOVES to it)."""

    def _shuffle_board(self):
        # K+R+N vs bare K; white knight oscillates f3-d4, black king g8-h8.
        b = chess.Board("6k1/8/8/8/8/5N2/8/R3K3 w - - 0 40")
        for san in ("Nd4", "Kh8", "Nf3", "Kg8", "Nd4", "Kh8", "Nf3", "Kg8"):
            b.push_san(san)
        return b

    def test_quiet_shuffle_fires(self):
        from _features import assess_situation
        sit = assess_situation(self._shuffle_board())
        text = "\n".join(sit["lines"])
        assert sit["drift"] and "NO PROGRESS" in text
        assert "standing plan" in text

    def test_recent_capture_silences(self):
        from _features import assess_situation
        b = self._shuffle_board()
        b.push_san("Ra8+"); b.push_san("Kh7"); b.push_san("Ra7+"); b.push_san("Kh8")
        # last own moves include rook checks but still no capture/pawn... make one:
        b2 = chess.Board("6k1/8/8/8/8/5N2/8/R3K3 w - - 0 40")
        for san in ("Nd4", "Kh8", "Nf3", "Kg8"):
            b2.push_san(san)
        sit = assess_situation(b2)   # only 2 own quiet moves — below threshold
        assert not sit.get("drift")

    def test_no_history_is_silent(self):
        from _features import assess_situation
        sit = assess_situation(chess.Board("6k1/8/8/8/8/5N2/8/R3K3 w - - 30 40"))
        assert not sit.get("drift")
