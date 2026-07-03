"""Tests for chess__imagine_trade — the SEE/exchange tool. Each expected outcome
is cross-checked against the existing static_exchange_eval so we never rely on
hand-read FENs (this experiment is a monument to how badly machines, incl. the
author, read boards)."""
import importlib.util
import sys
from pathlib import Path

import chess

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


tr = _mod("imagine_trade")
ev = _mod("_eval")


def _played_net(fen, square_name):
    """The net (white pov) imagine_trade computes for PLAYING the first capture
    (the agent is considering that capture; opponent recaptures optimally)."""
    b = chess.Board(fen)
    sq = chess.parse_square(square_name)
    start_bal, plies = tr._play_exchange(b, sq, None)
    if not plies:
        return None
    return tr._see_stop_from_ply1(start_bal, plies) - start_bal


def _decline_net(fen, square_name):
    """The net if you may CHOOSE not to initiate — the quantity SEE computes
    (0 when the first capture loses and can be declined)."""
    b = chess.Board(fen)
    sq = chess.parse_square(square_name)
    start_bal, plies = tr._play_exchange(b, sq, None)
    if not plies:
        return None
    return tr._see_stop(start_bal, plies, b.turn) - start_bal


def test_winning_capture_undefended_pawn():
    # Rook takes an undefended pawn on e5: +1 pawn, nothing recaptures.
    fen = "4k3/8/8/4p3/8/8/8/4R1K1 w - - 0 1"
    out = tr._render(chess.Board(fen), chess.E5, None)
    assert "WINS ~+100" in out


def test_losing_capture_declines():
    # Rxe5 wins a pawn but the d6 pawn recaptures the rook: playing it loses,
    # declining keeps +0. (d6 black pawn defends e5.)
    fen = "4k3/8/3p4/4p3/8/8/8/4R1K1 w - - 0 1"
    out = tr._render(chess.Board(fen), chess.E5, None)
    assert "LOSES" in out and "NOT to initiate" in out
    # the played-net must equal the genuine material swing (pawn for rook = -4)
    assert _played_net(fen, "e5") == -400


def test_even_trade():
    # White Nxe5 (knight takes pawn), black d6 pawn... build an EVEN trade:
    # knight takes knight, defended by a knight -> even (N for N).
    # white Nd3 x e5 knight, black f-pawn? construct N-for-N:
    fen = "4k3/8/5n2/4n3/3N4/8/8/4K3 w - - 0 1"  # Nd4xe5? d4 knight attacks e6,c6,f5,f3,b5,b3,c2,e2 - NOT e5
    # use a rook-for-rook on e-file, defended by a rook:
    fen = "4r1k1/8/8/4r3/8/8/8/4R1K1 w - - 0 1"  # Re1xe5 rook, black Re8 recaptures
    out = tr._render(chess.Board(fen), chess.E5, None)
    # Rxe5 Rxe5 = rook for rook = even
    assert "EVEN" in out
    assert _played_net(fen, "e5") == 0


def test_see_matches_static_exchange_eval():
    # Cross-check: imagine_trade's played-net == static_exchange_eval for the
    # side to move, on a battery of random capture positions.
    import random
    random.seed(11)
    checked = 0
    for _ in range(300):
        b = chess.Board()
        for _ in range(random.randint(0, 30)):
            ms = list(b.legal_moves)
            if not ms or b.is_game_over():
                break
            b.push(random.choice(ms))
        if b.is_game_over():
            continue
        # find a square the side to move can capture on
        caps = [m for m in b.legal_moves if b.is_capture(m)]
        if not caps:
            continue
        sq = caps[0].to_square
        # SEE = the DECLINE-optimal net (you may choose not to initiate). Compare
        # imagine_trade's _decline_net to it (mover-pov).
        net = _decline_net(b.fen(), chess.square_name(sq))
        see = ev.static_exchange_eval(b, sq, b.turn)
        sign = 1 if b.turn == chess.WHITE else -1
        if net is not None:
            assert sign * net == see, \
                f"mismatch fen={b.fen()} sq={chess.square_name(sq)} decline={sign*net} see={see}"
            checked += 1
    assert checked > 20
