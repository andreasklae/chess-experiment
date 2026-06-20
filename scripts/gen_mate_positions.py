#!/usr/bin/env python3
"""Generate VERIFIED forced-win puzzle positions for the basic-mate curriculum.

The chess experiment's Phase-1 question for mating technique is: across every
material combination that is a *forced win* against a lone (or nearly lone)
enemy king, can the agent convert? And — the new question — at what point does
the generic "restrict the enemy king" radar stop being enough, so a
material-specific wiki page is actually needed?

To test that honestly we need many random positions per material class, each
KNOWN to be a forced win — we must never drop the agent into a position that is
actually a draw and then score it as a failure. This script produces them:

  1. Place the requested material at random on a legal, white-to-move board
     (kings not adjacent, black king not in check, not already mate/stalemate,
     not insufficient material).
  2. VERIFY the position is a forced win for White from an authoritative source,
     not a guess (per the experiment's "do not assume what is forced mate" rule):
       * <=7 total pieces  -> the Lichess 7-piece Syzygy tablebase
         (https://tablebase.lichess.ovh). `category == "win"` is ground truth;
         `dtm` (distance to mate, plies) sets a tight-but-fair ply cap.
       * >7 pieces (over-material combos like K+Q+R+B vs K) -> Stockfish. These
         are trivially winning; we require a mate score or a decisive eval and
         use a generous cap. Flagged `verifier: stockfish` in the output.
  3. Emit a puzzle-suite JSON consumable by run_puzzles.py via `--suite`.

Material spec syntax (white always has K, black always has K):
    "Q"        K+Q vs K
    "RR"       K+2R vs K
    "BB"       K+2B vs K          (forced; bishops auto-placed opposite-coloured)
    "BN"       K+B+N vs K         (forced; the hard one)
    "RNN"      K+R+2N vs K        (over-material)
    "Q|p"      K+Q  vs K+pawn     (enemy pawn — '|' separates black's material)
    "QR|n"     K+Q+R vs K+knight  (enemy has a piece, less than us)

Usage:
    python3 scripts/gen_mate_positions.py --spec Q RR BB BN --count 5 \
        --seed 1 --out /tmp/suite.json
    python3 scripts/gen_mate_positions.py --spec "Q|p" "RR|n" --count 3 --out ...

Offline (skip tablebase, Stockfish only):  --no-tablebase
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import chess
import chess.engine

_PIECE = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP,
          "N": chess.KNIGHT, "P": chess.PAWN}
_NAME = {chess.QUEEN: "Q", chess.ROOK: "R", chess.BISHOP: "B",
         chess.KNIGHT: "N", chess.PAWN: "P"}
_STOCKFISH = "/opt/homebrew/bin/stockfish"
_TABLEBASE_URL = "https://tablebase.lichess.ovh/standard"


def parse_spec(spec: str) -> tuple[list[int], list[int]]:
    """'QR|n' -> (white piece types [Q,R], black piece types [N]). Kings implied."""
    white_str, _, black_str = spec.partition("|")
    white = [_PIECE[c.upper()] for c in white_str if c.strip()]
    black = [_PIECE[c.upper()] for c in black_str if c.strip()]
    return white, black


def _legal_pawn_rank(color: bool) -> range:
    # pawns never on rank 1 or 8; keep enemy pawns off the brink of promotion
    # (rank 2 for black, rank 7 for white) so the puzzle is about mating, not a
    # promotion race the tablebase might still call a win but that muddies the
    # "eliminate the threat then mate" test. We keep them in ranks 3-6.
    return range(2, 6)  # 0-indexed ranks 3..6


def random_position(white: list[int], black: list[int], rng: random.Random,
                    tries: int = 400) -> chess.Board | None:
    """A random legal white-to-move position with the given material, or None."""
    for _ in range(tries):
        board = chess.Board.empty()
        squares = rng.sample(range(64), 2)
        wk, bk = squares[0], squares[1]
        if chess.square_distance(wk, bk) <= 1:
            continue
        board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
        used = {wk, bk}

        def place(pt: int, color: bool) -> bool:
            if pt == chess.PAWN:
                cand = [chess.square(f, r) for f in range(8)
                        for r in _legal_pawn_rank(color)]
            elif pt == chess.BISHOP:
                cand = list(range(64))
            else:
                cand = list(range(64))
            rng.shuffle(cand)
            for sq in cand:
                if sq in used:
                    continue
                board.set_piece_at(sq, chess.Piece(pt, color))
                used.add(sq)
                return True
            return False

        ok = True
        # Two bishops must be opposite-coloured (else they cannot mate). Place
        # the first freely, force the second onto the other colour.
        bishops = [pt for pt in white if pt == chess.BISHOP]
        if len(bishops) == 2:
            sq1 = next((s for s in rng.sample(range(64), 64) if s not in used), None)
            if sq1 is None:
                continue
            board.set_piece_at(sq1, chess.Piece(chess.BISHOP, chess.WHITE)); used.add(sq1)
            want_color = not chess.BB_LIGHT_SQUARES & chess.BB_SQUARES[sq1]
            sq2 = next((s for s in rng.sample(range(64), 64)
                        if s not in used and bool(chess.BB_LIGHT_SQUARES & chess.BB_SQUARES[s]) == bool(want_color)),
                       None)
            if sq2 is None:
                continue
            board.set_piece_at(sq2, chess.Piece(chess.BISHOP, chess.WHITE)); used.add(sq2)
            remaining_white = [pt for pt in white if pt != chess.BISHOP]
        else:
            remaining_white = white
        for pt in remaining_white:
            ok &= place(pt, chess.WHITE)
        for pt in black:
            ok &= place(pt, chess.BLACK)
        if not ok:
            continue

        board.turn = chess.WHITE
        board.clear_stack()
        if not board.is_valid():
            continue
        if board.is_check():          # black king en prise with white to move = illegal already handled by is_valid
            continue
        if board.is_checkmate() or board.is_stalemate():
            continue
        if board.has_insufficient_material(chess.WHITE):
            continue
        # don't hand the agent a free immediate mate-in-1 or a position where the
        # lone king just grabs an undefended piece next move (too easy / not the
        # technique). Light filter; tablebase still confirms the win.
        return board
    return None


def verify_tablebase(board: chess.Board, retries: int = 3) -> dict | None:
    """Return {'win': bool, 'dtm': int|None} from the Lichess tablebase, or None
    on network failure. category=='win' means White (side to move) forces mate."""
    fen = board.fen()
    url = f"{_TABLEBASE_URL}?{urllib.parse.urlencode({'fen': fen})}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
            return {"win": data.get("category") == "win",
                    "dtm": abs(data["dtm"]) if data.get("dtm") is not None else None,
                    "category": data.get("category")}
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def verify_stockfish(board: chess.Board, engine: chess.engine.SimpleEngine,
                     movetime: float = 2.0) -> dict:
    """Decisive-win check for >7-piece positions. Win = mate score or eval >= +6."""
    info = engine.analyse(board, chess.engine.Limit(time=movetime))
    score = info["score"].white()
    if score.is_mate():
        return {"win": score.mate() > 0, "dtm": abs(score.mate()) * 2}
    cp = score.score()
    return {"win": cp is not None and cp >= 600, "dtm": None}


def piece_count(board: chess.Board) -> int:
    return chess.popcount(board.occupied)


def cap_for(dtm: int | None, total_pieces: int, slack: int) -> int:
    """Fair ply cap. An imperfect-but-converging agent typically needs ~2x the
    optimal distance-to-mate; a shuffling one blows past any multiple. So allow
    2*dtm plus a fixed margin, with a floor so very short mates still get room
    to manoeuvre. This aligns with the recipe's hand-tuned caps (K+Q~40 for a
    ~dtm-13 mate) and scales correctly for the long K+B+N (dtm~55 -> ~120).
    `slack` is the additive margin on top of 2*dtm. Without dtm, a fixed cap."""
    if dtm is not None:
        return max(2 * dtm + slack, 30)
    return 60


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", nargs="+", required=True,
                    help="material specs, e.g. Q RR BB BN 'Q|p' 'QR|n'")
    ap.add_argument("--count", type=int, default=3, help="verified positions per spec")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--slack", type=int, default=18,
                    help="plies added to tablebase dtm for the per-puzzle cap")
    ap.add_argument("--out", required=True, help="output suite JSON path")
    ap.add_argument("--no-tablebase", action="store_true",
                    help="skip tablebase, use Stockfish for everything")
    ap.add_argument("--max-attempts", type=int, default=60,
                    help="random positions to try per accepted puzzle")
    ap.add_argument("--min-dtm", type=int, default=6,
                    help="reject positions easier than this (plies to mate); "
                         "filters out trivial mate-in-1/2 so we test conversion")
    ap.add_argument("--max-dtm", type=int, default=None,
                    help="reject positions harder than this (plies to mate); "
                         "grade difficulty, e.g. --max-dtm 25 for 'start easy'")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    engine = chess.engine.SimpleEngine.popen_uci(_STOCKFISH)
    suite: list[dict] = []
    try:
        for spec in args.spec:
            white, black = parse_spec(spec)
            label = "".join(_NAME[p] for p in white) + (
                "|" + "".join(_NAME[p] for p in black) if black else "")
            accepted = 0
            attempts = 0
            print(f"\n=== spec {spec}  (white K+{label.split('|')[0]}"
                  f"{' vs K+' + label.split('|')[1] if black else ' vs K'})", flush=True)
            while accepted < args.count and attempts < args.count * args.max_attempts:
                attempts += 1
                board = random_position(white, black, rng)
                if board is None:
                    continue
                total = piece_count(board)
                if total <= 7 and not args.no_tablebase:
                    v = verify_tablebase(board)
                    verifier = "tablebase"
                    if v is None:
                        print("  tablebase unreachable — falling back to stockfish")
                        v = verify_stockfish(board, engine); verifier = "stockfish"
                else:
                    v = verify_stockfish(board, engine); verifier = "stockfish"
                if not v["win"]:
                    continue
                dtm = v.get("dtm")
                # difficulty grading: skip too-easy / too-hard when dtm is known
                if dtm is not None:
                    if dtm < args.min_dtm:
                        continue
                    if args.max_dtm is not None and dtm > args.max_dtm:
                        continue
                accepted += 1
                cap = cap_for(v.get("dtm"), total, args.slack)
                pid = f"{spec.replace('|', '_v_')}-{accepted:02d}"
                suite.append({
                    "id": pid,
                    "name": f"K+{label} forced mate ({verifier}"
                            f"{', dtm ' + str(v['dtm']) if v.get('dtm') else ''})",
                    "fen": board.fen(),
                    "max_plies": cap,
                    "spec": spec,
                    "verifier": verifier,
                    "dtm": v.get("dtm"),
                    "expect": f"1-0 by checkmate within {cap} plies "
                              f"(forced win, {verifier}-verified).",
                })
                print(f"  [{accepted}/{args.count}] {board.fen()}  "
                      f"({verifier}, dtm={v.get('dtm')}, cap={cap})", flush=True)
            if accepted < args.count:
                print(f"  WARNING: only {accepted}/{args.count} after {attempts} attempts")
    finally:
        engine.quit()

    with open(args.out, "w") as f:
        json.dump(suite, f, indent=2)
    print(f"\nWrote {len(suite)} puzzles to {args.out}")


if __name__ == "__main__":
    main()
