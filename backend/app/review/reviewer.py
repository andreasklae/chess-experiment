"""Game review orchestration — the chess.com-style "game review" for this experiment.

Input: a game's moves (UCI or SAN, or a PGN). Output: a single rich JSON object with,
for EVERY move:
  - the position before, the move played, the engine's best move + principal variation
  - eval before/after (cp + win%), centipawn loss, win% lost, per-move accuracy
  - a quality label (brilliant/great/best/excellent/good/inaccuracy/mistake/blunder/forced)
  - the mechanical "why": the side-to-move's situation/priority, the salient features,
    and — for a mistake/blunder — what the move ALLOWED the opponent to do, plus the
    better move and the line that refutes what was played
and per-player + per-game summaries (accuracy, average CPL, label counts, the worst
moments, and weakness tags) designed to be easy to mine and learn from.

The "why" comes from this repo's own fair detector stack (see review/features.py), so a
review is engine-accurate AND carries the same explicit mechanical facts the agent
sees — no third-party service, no natural-language model required (an LLM layer can be
added on top of this structured output if desired).
"""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from typing import Iterable

import chess
import chess.pgn

from app.review import classify as C
from app.review import features as FEAT
from app.review.engine import ReviewEngine, ScoredMove


# ── input parsing ───────────────────────────────────────────────────────────────

def _moves_from_pgn(pgn: str) -> tuple[chess.Board, list[chess.Move], dict]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("could not parse PGN")
    board = game.board()
    moves = list(game.mainline_moves())
    headers = {k: v for k, v in game.headers.items()}
    return board, moves, headers


def _moves_from_list(moves: Iterable[str], start_fen: str | None) -> tuple[chess.Board, list[chess.Move], dict]:
    board = chess.Board(start_fen) if start_fen else chess.Board()
    parsed: list[chess.Move] = []
    probe = board.copy()
    for m in moves:
        try:
            mv = probe.parse_uci(m)
        except Exception:
            mv = probe.parse_san(m)   # tolerate SAN input too
        parsed.append(mv)
        probe.push(mv)
    return board, parsed, {}


# ── per-move record ─────────────────────────────────────────────────────────────

def _mover_cp(white_cp: int | None, white_mate: int | None, white_to_move: bool) -> int:
    """Fold a White-POV score to a single cp number from the MOVER's POV."""
    folded = C.cp_from_score(white_cp, white_mate)
    return folded if white_to_move else -folded


def _best_for_mover(cands: list[ScoredMove], white_to_move: bool) -> int | None:
    """Mover-POV cp of the engine's best move (cands[0]). None if no candidates."""
    if not cands:
        return None
    return _mover_cp(cands[0].cp, cands[0].mate, white_to_move)


def _is_sound_sacrifice(board: chess.Board, move: chess.Move) -> bool:
    """A move is a 'sacrifice' for brilliancy purposes if it gives up material on the
    move (a capture netting negative by SEE, or moving a piece onto an attacked,
    under-defended square) — judged mechanically. Combined with 'is_best' upstream,
    that is a sound sacrifice. Best-effort via the skill's SEE if available."""
    try:
        from _eval import static_exchange_eval, MATERIAL
    except Exception:
        return False
    after = board.copy(); after.push(move)
    mover = board.turn
    # captured into a square the opponent can win back, OR left the moved piece hanging
    if board.is_capture(move):
        try:
            if static_exchange_eval(after, move.to_square, not mover) >= 200:
                return True
        except Exception:
            return False
    # moved a >= minor piece to a square where it is now hanging
    pc = board.piece_at(move.from_square)
    if pc and pc.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        if after.attackers(not mover, move.to_square) and not after.attackers(mover, move.to_square):
            return True
    return False


def _review_one_move(
    eng: ReviewEngine, board: chess.Board, move: chess.Move, ply: int, depth: int,
) -> dict:
    white_to_move = board.turn == chess.WHITE
    mover = "white" if white_to_move else "black"
    san = board.san(move)
    legal = list(board.legal_moves)
    forced = len(legal) == 1

    cands = eng.best_moves(board, depth=depth)
    best = cands[0] if cands else None
    played_in_top = next((c for c in cands if c.move == move), None)

    # eval of the position assuming BEST play (mover POV)
    win_best = best_cp_mover = None
    if best is not None:
        best_cp_mover = _best_for_mover(cands, white_to_move)
        win_best = C.win_percent(best_cp_mover)

    # eval after the move actually played (mover POV): reuse the multipv result if the
    # played move was among the candidates, else evaluate the resulting position once.
    board_after = board.copy(); board_after.push(move)
    if played_in_top is not None:
        played_cp_mover = _mover_cp(played_in_top.cp, played_in_top.mate, white_to_move)
    else:
        after_cands = eng.best_moves(board_after, depth=depth, multipv=1)
        if after_cands:
            # after_cands is from the OPPONENT's seat (board_after); flip back to the
            # position eval, which is still White-POV, then to the mover's POV.
            wc, wm = after_cands[0].cp, after_cands[0].mate
            played_cp_mover = _mover_cp(wc, wm, white_to_move)
        else:
            played_cp_mover = best_cp_mover if best_cp_mover is not None else 0

    win_played = C.win_percent(played_cp_mover) if played_cp_mover is not None else None

    # classification
    is_best = best is not None and (move == best.move)
    cpl = max(0, (best_cp_mover - played_cp_mover)) if (best_cp_mover is not None) else 0
    only_good = False
    if is_best and len(cands) >= 2 and cands[1].cp is not None and best.cp is not None:
        # 'great': best move, and the second-best is much worse (the move was the only
        # way to hold/win) — measured in win% from the mover's POV
        second_mover = _mover_cp(cands[1].cp, cands[1].mate, white_to_move)
        only_good = (C.win_percent(best_cp_mover) - C.win_percent(second_mover)) >= 10.0
    sac = is_best and _is_sound_sacrifice(board, move)

    if win_best is not None and win_played is not None:
        q = C.classify(win_best, win_played, cpl, is_best=is_best,
                       only_good_move=only_good, is_sound_sacrifice=sac, forced=forced)
    else:
        q = C.MoveQuality("forced" if forced else "best", 0.0, 0, is_best)

    rec: dict = {
        "ply": ply,
        "move_number": ply // 2 + 1,
        "mover": mover,
        "fen_before": board.fen(),
        "played": {"san": san, "uci": move.uci()},
        "eval_best_cp_mover": best_cp_mover,
        "eval_played_cp_mover": played_cp_mover,
        "win_before_pct": round(win_best, 1) if win_best is not None else None,
        "win_after_pct": round(win_played, 1) if win_played is not None else None,
        "centipawn_loss": cpl,
        "win_pct_lost": round(q.win_loss, 1),
        "accuracy_pct": round(C.accuracy_percent(win_best, win_played), 1)
                        if (win_best is not None and win_played is not None) else None,
        "classification": q.label,
        "is_best_move": is_best,
        "best_move": ({"san": best.san, "uci": best.move.uci(),
                       "pv": best.pv} if best else None),
        # the mechanical "why" for the side that just moved (seen from BEFORE the move)
        "situation": FEAT.situation(board),
    }

    # for sub-par moves, attach the actionable explanation: the better move's line and
    # what the played move ALLOWED the opponent to do.
    if q.label in C.MISTAKE_LABELS and not is_best:
        rec["why_suboptimal"] = {
            "better_move": best.san if best else None,
            "better_line": best.pv if best else [],
            "allowed_opponent": FEAT.opponent_reply_threats(board_after),
            "key_features_before": FEAT.key_features(board),
        }
    return rec


# ── summary ──────────────────────────────────────────────────────────────────────

def _summary(moves: list[dict]) -> dict:
    out: dict = {}
    for color in ("white", "black"):
        rows = [m for m in moves if m["mover"] == color]
        accs = [m["accuracy_pct"] for m in rows if m["accuracy_pct"] is not None]
        cpls = [m["centipawn_loss"] for m in rows]
        counts = {lbl: sum(1 for m in rows if m["classification"] == lbl) for lbl in C.LABELS}
        worst = sorted([m for m in rows if m["classification"] in C.MISTAKE_LABELS],
                       key=lambda m: -m["win_pct_lost"])[:5]
        out[color] = {
            "accuracy_pct": C.game_accuracy(accs),
            "avg_centipawn_loss": round(sum(cpls) / len(cpls), 1) if cpls else None,
            "move_counts": counts,
            "n_moves": len(rows),
            "worst_moments": [
                {"ply": m["ply"], "move": m["played"]["san"],
                 "classification": m["classification"], "win_pct_lost": m["win_pct_lost"],
                 "better_move": (m.get("why_suboptimal") or {}).get("better_move")}
                for m in worst
            ],
            "weakness_tags": _weakness_tags(rows),
        }
    return out


def _weakness_tags(rows: list[dict]) -> dict:
    """Slice this player's mistakes/blunders by position-type, so a batch can surface
    *where* the player is weak (phase, in-check, under-threat, has-forcing-move). Each
    tag carries n_mistakes / n_total / mistake_rate — the learning signal."""
    buckets: dict[str, dict] = {}

    def bump(tag: str, is_mistake: bool):
        b = buckets.setdefault(tag, {"n_total": 0, "n_mistakes": 0})
        b["n_total"] += 1
        if is_mistake:
            b["n_mistakes"] += 1

    for m in rows:
        sit = m.get("situation") or {}
        is_mistake = m["classification"] in C.MISTAKE_LABELS
        bump(f"phase:{sit.get('phase', 'unknown')}", is_mistake)
        if sit.get("in_check"):
            bump("in_check", is_mistake)
        if sit.get("threat_against_mover"):
            bump(f"under_threat:{sit['threat_against_mover']['kind']}", is_mistake)
        if sit.get("has_forcing_move"):
            bump("had_forcing_move", is_mistake)
        if sit.get("priority"):
            bump(f"priority:{sit['priority'].split(' ')[0]}", is_mistake)
    for b in buckets.values():
        b["mistake_rate"] = round(b["n_mistakes"] / b["n_total"], 3) if b["n_total"] else 0.0
    # only keep buckets with at least one mistake or a few samples, mistake-rate desc
    return dict(sorted(
        ((k, v) for k, v in buckets.items() if v["n_mistakes"] > 0 or v["n_total"] >= 3),
        key=lambda kv: -kv[1]["mistake_rate"]))


# ── public API ───────────────────────────────────────────────────────────────────

def review_game(
    moves: Iterable[str] | None = None,
    *,
    pgn: str | None = None,
    start_fen: str | None = None,
    stockfish_path: str = "stockfish",
    depth: int = 18,
    multipv: int = 3,
    game_id: str | None = None,
    headers: dict | None = None,
) -> dict:
    """Review a game. Provide either `moves` (UCI or SAN list) or `pgn`.

    Returns the full analysis dict (also see `review.io.write_review` to persist it).
    Deterministic: single-threaded Stockfish at fixed depth.
    """
    if pgn is not None:
        board, mv_list, pgn_headers = _moves_from_pgn(pgn)
        headers = {**pgn_headers, **(headers or {})}
    elif moves is not None:
        board, mv_list, _ = _moves_from_list(moves, start_fen)
    else:
        raise ValueError("provide either `moves` or `pgn`")

    result: dict = {
        "game_id": game_id,
        "headers": headers or {},
        "start_fen": board.fen(),
        "engine": {"name": "stockfish", "depth": depth, "multipv": multipv},
        "schema_version": 1,
        "moves": [],
    }

    with ReviewEngine(stockfish_path, depth=depth, multipv=multipv) as eng:
        result["engine_available"] = eng.available
        play = board.copy()
        for ply, mv in enumerate(mv_list):
            rec = _review_one_move(eng, play, mv, ply, depth)
            result["moves"].append(rec)
            play.push(mv)
        result["final_fen"] = play.fen()
        result["result"] = play.result(claim_draw=True) if play.is_game_over(claim_draw=True) \
            else (headers or {}).get("Result", "*")

    result["summary"] = _summary(result["moves"])
    return result
