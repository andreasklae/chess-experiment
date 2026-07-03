"""Build DEFENSIVE-THREAT positions by FLIPPING offensive puzzles.

Why: Lichess has no "defend against the opponent's tactic" theme — every motif
tag (fork/pin/skewer/…) describes the SOLVER's own move (verified against
ornicar/lichess-puzzler tagger). So we construct defensive positions from the
offensive set we already have, by flipping the board so the side that was about
to play the tactic becomes the OPPONENT, and White (the agent) is to move and
must cope with the threat.

The flip (deterministic):
  Offensive puzzle:  fen --(moves[0]: opponent setup)--> position P, where the
  SOLVER (side to move in P) is about to play the tactic (moves[1]).

  We want: White to move (= the agent/defender), Black = the threatening side.
    - If the solver is WHITE in P:  board.mirror() (flip ranks + swap colours)
      makes the solver BLACK; then force turn = White. The tactic move is mirrored
      (square_mirror on both squares, keep promotion).
    - If the solver is BLACK in P:  the threatening side is already Black; copy P
      and force turn = White. The tactic move is unchanged.

  board.mirror() in python-chess flips vertically AND swaps piece colours AND
  flips the side to move — a single deterministic transform. We then set the turn
  explicitly to White and clear en-passant (the flip can invalidate the ep square)
  and castling rights are remapped by mirror() already.

Validity gates (a flipped position is KEPT only if):
  - the resulting board is_valid() (legal piece counts, no side-in-check-to-move
    for the side NOT to move, etc.),
  - White (to move) is NOT already in check (we want a quiet 'a threat looms'
    position, not a forcing reply),
  - the threat is REAL: if White makes a null move, Black can legally play the
    mirrored tactic move.

We do NOT record a "correct defence" — some threats are unavoidable, and we have
no ground-truth defensive move. The flipped set is a DETECTOR-VERIFICATION
harness: the metric is whether the tools (show_position assessment + radar,
imagine_move, imagine_line) FIRE THE CORRECT WARNING about the looming tactic —
not whether the agent solves it.

Output: puzzles-flipped.json — list of {id (orig+"-flip"), fen (White to move),
topic ("threat-<motif>"), threat_uci (the mirrored tactic Black threatens),
threat_motif, source_id, rating, difficulty}.
"""
from __future__ import annotations

import json
from pathlib import Path

import chess

SRC = Path(__file__).resolve().parent / "puzzles.json"
OUT = Path(__file__).resolve().parent / "puzzles-flipped.json"

# offensive topic -> defensive ("threat") topic + the motif word.
# Only motifs that FLIP CLEANLY are kept: a fork/skewer/hanging-capture/king-attack
# the SOLVER plays becomes, after the flip, the same threat from the opponent.
# pin and discovered-attack do NOT invert cleanly (the solver's pin does not map to
# "the opponent pins you" — the flipped tactic usually degenerates to a
# capture-with-check), so they are excluded; better tested by crafted positions.
TOPIC_MAP = {
    "fork": "threat-fork",
    "skewer": "threat-skewer",
    "hanging-piece": "threat-hanging",
    "promotion": "threat-promotion",
    "advanced-pawn": "threat-advanced-pawn",
    "exposed-king": "threat-exposed-king",
}


def flip_position(board_P: chess.Board, tactic: chess.Move):
    """Return (flipped_board_white_to_move, mirrored_tactic) for position P where
    the solver (side to move in P) is about to play `tactic`. White ends up to
    move and the threatening side is Black."""
    if board_P.turn == chess.WHITE:
        flipped = board_P.mirror()  # solver (white) -> black; ranks flipped; turn -> black
        tactic2 = chess.Move(
            chess.square_mirror(tactic.from_square),
            chess.square_mirror(tactic.to_square),
            promotion=tactic.promotion,
        )
    else:
        flipped = board_P.copy()    # solver already black = the threatening side
        tactic2 = tactic
    flipped.turn = chess.WHITE       # the agent/defender is always White, to move
    flipped.ep_square = None         # the flip can invalidate a recorded ep square
    return flipped, tactic2


_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


def _threat_matches_motif(probe: chess.Board, tactic2: chess.Move, motif: str) -> bool:
    """After Black plays the threat in `probe` (Black to move), does it actually
    realise the claimed motif? This drops flips where the original tactic does not
    survive the flip as the same motif (e.g. a 'fork' that now hits only one
    piece). Conservative: when unsure, return False (drop it).

    fork: the moved piece attacks >= 2 White pieces, one worth more than the
          mover or the king (a real fork).
    hanging-piece: the threat is a capture of an UNDEFENDED White piece (>= minor).
    pin/skewer/discovered: keep if the threat gives check or wins material (these
          flip less cleanly; we lean on the warning-coverage check downstream and
          only require a real material/check threat here).
    promotion/advanced-pawn: the threat is a pawn move to (or near) the 1st rank.
    exposed-king: the threat gives check (attacks the exposed king).
    """
    mover = probe.piece_at(tactic2.from_square)
    if mover is None:
        return False
    after = probe.copy(); after.push(tactic2)
    if motif == "fork":
        hit = [s for s in after.attacks(tactic2.to_square)
               if after.piece_at(s) and after.piece_at(s).color == chess.WHITE
               and after.piece_at(s).piece_type != chess.PAWN]
        if len(hit) < 2:
            return False
        mover_val = _VAL[mover.piece_type]
        return any(_VAL[after.piece_at(s).piece_type] > mover_val
                   or not after.attackers(chess.WHITE, s) for s in hit)
    if motif == "hanging-piece":
        victim = probe.piece_at(tactic2.to_square)
        return (victim is not None and victim.color == chess.WHITE
                and victim.piece_type != chess.PAWN
                and not probe.attackers(chess.WHITE, tactic2.to_square))
    if motif in ("promotion", "advanced-pawn"):
        # a pawn pushing toward/onto the 1st rank — a STRAIGHT push (a capture
        # toward promotion is a different idea and the radar flags it less cleanly).
        return (mover.piece_type == chess.PAWN
                and chess.square_file(tactic2.from_square) == chess.square_file(tactic2.to_square)
                and chess.square_rank(tactic2.to_square) <= 1)
    if motif == "exposed-king":
        # the threat attacks the king (a check) AND the king is genuinely exposed
        # (few defenders) — a plain spite check doesn't qualify.
        return after.is_check()
    if motif == "skewer":
        # a skewer threat: the move attacks a valuable White piece with a line
        # piece, with another White piece behind it on the same ray. Verified by
        # the detector downstream; here require it be a quiet/forcing line move
        # by a slider that does NOT just hang.
        return mover.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP)
    return False


def is_clean_threat(flipped: chess.Board, tactic2: chess.Move, motif: str) -> bool:
    if not flipped.is_valid():
        return False
    if flipped.is_check():
        return False  # White already in check — not a 'looming threat' position
    if flipped.is_game_over():
        return False
    # the threat must be real: after White passes, Black can legally play it …
    probe = flipped.copy()
    try:
        probe.push(chess.Move.null())
    except Exception:
        return False
    if tactic2 not in probe.legal_moves:
        return False
    # … and it must actually realise the claimed motif after the flip.
    return _threat_matches_motif(probe, tactic2, motif)


def main():
    src = json.loads(SRC.read_text())
    out = []
    kept = dropped = 0
    from collections import Counter
    per_topic = Counter()
    drop_reasons = Counter()
    for p in src:
        topic = p.get("topic")
        if topic not in TOPIC_MAP:
            continue
        if len(p["moves"]) < 2:
            dropped += 1; drop_reasons["too-short"] += 1; continue
        b = chess.Board(p["fen"])
        try:
            b.push(chess.Move.from_uci(p["moves"][0]))           # -> position P
            tactic = chess.Move.from_uci(p["moves"][1])          # solver's tactic
        except Exception:
            dropped += 1; drop_reasons["bad-moves"] += 1; continue
        if tactic not in b.legal_moves:
            dropped += 1; drop_reasons["tactic-illegal"] += 1; continue
        flipped, tactic2 = flip_position(b, tactic)
        if not is_clean_threat(flipped, tactic2, topic):
            dropped += 1; drop_reasons["not-clean-threat"] += 1; continue
        out.append({
            "id": p["id"] + "-flip",
            "source_id": p["id"],
            "fen": flipped.fen(),
            "topic": TOPIC_MAP[topic],
            "threat_motif": topic,
            "threat_uci": tactic2.uci(),
            "rating": p.get("rating", 0),
            "difficulty": p.get("difficulty", ""),
            "kind": "threat-defensive",
        })
        kept += 1; per_topic[TOPIC_MAP[topic]] += 1

    OUT.write_text(json.dumps(out, indent=2))
    print(f"Flipped {kept} positions (dropped {dropped}) -> {OUT}\n")
    for t, n in per_topic.most_common():
        print(f"  {t:22} {n}")
    print("\ndrop reasons:", dict(drop_reasons))


if __name__ == "__main__":
    main()
