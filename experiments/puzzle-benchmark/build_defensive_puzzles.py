#!/usr/bin/env python3
"""Build the DEFENSIVE puzzle set by mining the agent's own lost games.

Item P (king safety / not getting mated) has no fitting Lichess theme — every Lichess
puzzle theme is framed from the solver's *offensive* seat (see the lichess2026api KB
page). So we source defensive positions from our own games: each agent game JSON
(`backend/games/**/*_agent.json`) logs, per turn, `evals.stockfish_cp_before/after`
(the needle, White's POV) and the FEN in the turn `prompt`. A blunder is a turn where
the eval falls from non-losing to clearly lost; the pre-blunder FEN is a defensive
puzzle — *find a move that holds*.

Pipeline (all here, idempotent):
  1. MINE   — scan agent-lost-by-mate games for pre-blunder positions (no engine).
  2. VERIFY — Stockfish (depth 16) classifies every legal move; a position is a FAIR
              puzzle iff a holding move exists, the agent's actual move lost, and not
              every move holds (a real test). The set of holding moves = `acceptable_uci`.
  3. EXPORT — write puzzles_defensive.json in the benchmark schema (+ acceptable_uci),
              keeping the Lichess fen convention (fen = position BEFORE moves[0] setup).

Run from experiments/chess/:  .venv/bin/python experiments/puzzle-benchmark/build_defensive_puzzles.py
Requires Stockfish on PATH (or set STOCKFISH).
"""
from __future__ import annotations
import glob, hashlib, json, os, re, sys
from pathlib import Path

import chess
import chess.engine

HERE = Path(__file__).resolve().parent
CHESS_ROOT = HERE.parents[1]                       # experiments/chess
GAMES = CHESS_ROOT / "backend" / "games"
OUT = HERE / "puzzles_defensive.json"
STOCKFISH = os.environ.get("STOCKFISH", "/opt/homebrew/bin/stockfish")

# eval thresholds (centipawns, White POV)
OK_BEFORE = -200    # agent was not already lost before the blunder
LOST_AFTER = -350   # the blunder dropped it to clearly lost
MIN_DROP = 250      # and the swing was real
HOLD_MIN = -150     # a FAIR puzzle's best move keeps eval >= this
LOST_MAX = -300     # the agent's actual move must be at least this bad
ACCEPT_MIN = -150   # a played move PASSES if eval stays >= this
DEPTH = 16

_FEN_RE = re.compile(
    r"([rnbqkpRNBQKP1-8]+(?:/[rnbqkpRNBQKP1-8]+){7} [wb] (?:-|[KQkq]+) (?:-|[a-h][36]) \d+ \d+)"
)


def _fen_in(prompt: str | None) -> str | None:
    m = _FEN_RE.search(prompt or "")
    return m.group(1) if m else None


def _full_games() -> dict[str, dict]:
    out = {}
    for f in glob.glob(str(GAMES / "**" / "*.json"), recursive=True):
        # filter on the BASENAME, not the full path — an absolute path can contain
        # "elo" incidentally (e.g. ".../Developer/...") and silently drop everything.
        base = os.path.basename(f)
        if base.endswith("_agent.json") or "elo" in base:
            continue
        try:
            g = json.load(open(f))
        except Exception:
            continue
        if "uci_moves" in g:
            out[g.get("game_id")] = g
    return out


def mine(fulls: dict[str, dict]) -> list[dict]:
    """Pre-blunder positions from games the agent (White) lost by checkmate."""
    seen, cands = set(), []
    for af in glob.glob(str(GAMES / "**" / "*_agent.json"), recursive=True):
        try:
            a = json.load(open(af))
        except Exception:
            continue
        g = fulls.get(a.get("game_id"))
        if not g or g.get("status") != "finished" or g.get("result") != "0-1":
            continue
        b = chess.Board(); ok = True
        for u in g.get("uci_moves", []):
            try:
                b.push(chess.Move.from_uci(u))
            except Exception:
                ok = False; break
        if not (ok and b.is_checkmate() and b.turn == chess.WHITE):
            continue
        best = None
        for t in a.get("turns", []):
            ev = t.get("evals") or {}
            cb, ca = ev.get("stockfish_cp_before"), ev.get("stockfish_cp_after")
            if cb is None or ca is None:
                continue
            if cb >= OK_BEFORE and ca <= LOST_AFTER and (cb - ca) >= MIN_DROP:
                fen = _fen_in(t.get("prompt"))
                if not fen:
                    continue
                try:
                    board = chess.Board(fen)
                except Exception:
                    continue
                if board.turn != chess.WHITE or len(board.piece_map()) < 7:
                    continue
                drop = cb - ca
                if best is None or drop > best["drop"]:
                    best = dict(gid=a["game_id"], cb=cb, ca=ca, drop=drop,
                                mv=t.get("move_chosen"), fen=fen)
        if best and best["fen"] not in seen:
            seen.add(best["fen"]); cands.append(best)
    return cands


def verify(cands: list[dict]) -> list[dict]:
    """Stockfish fairness pass; attach best move, acceptable holding moves, fairness."""
    eng = chess.engine.SimpleEngine.popen_uci(STOCKFISH)
    # Single thread + fixed hash → DETERMINISTIC eval at a given depth, so the set
    # regenerates identically (multi-threaded search is non-deterministic and flips
    # borderline ±150cp puzzles in/out of the fair set).
    eng.configure({"Threads": 1, "Hash": 64})

    def cp(board: chess.Board) -> int:
        s = eng.analyse(board, chess.engine.Limit(depth=DEPTH))["score"].white()
        if s.is_mate():
            return 10000 if s.mate() > 0 else -10000
        return s.score()

    out = []
    try:
        for c in cands:
            b = chess.Board(c["fen"])
            scored = []
            for mv in b.legal_moves:
                bb = b.copy(); bb.push(mv)
                scored.append((mv, cp(bb)))
            if not scored:
                continue
            scored.sort(key=lambda x: -x[1])
            best_mv, best_cp = scored[0]
            acc = [mv for mv, e in scored if e >= ACCEPT_MIN]
            try:
                bl = chess.Move.from_uci(c["mv"]); bb = b.copy(); bb.push(bl)
                bl_cp = cp(bb)
            except Exception:
                bl_cp = None
            fair = (best_cp >= HOLD_MIN and bl_cp is not None and bl_cp <= LOST_MAX
                    and 0 < len(acc) < len(scored))
            out.append(dict(c, best_uci=best_mv.uci(), best_cp=best_cp,
                            acc_uci=[m.uci() for m in acc], blunder_cp=bl_cp,
                            n_holding=len(acc), n_legal=len(scored), fair=fair))
    finally:
        eng.quit()
    return out


def export(verified: list[dict], fulls: dict[str, dict]) -> list[dict]:
    """Find the opponent setup move (so fen = position BEFORE it) and write the set."""
    def setup_for(gid: str, target_fen: str):
        g = fulls.get(gid)
        if not g:
            return None
        b = chess.Board(); tgt = chess.Board(target_fen).board_fen()
        for u in g["uci_moves"]:
            before = b.fen()
            try:
                b.push(chess.Move.from_uci(u))
            except Exception:
                break
            if b.board_fen() == tgt and b.turn == chess.WHITE:
                return before, u
        return None

    out = []
    for v in verified:
        if not v["fair"]:
            continue
        su = setup_for(v["gid"], v["fen"])
        if not su:
            continue
        fen_before, setup_uci = su
        b = chess.Board(v["fen"])
        pid = "def_" + hashlib.sha1((v["gid"] + v["fen"]).encode()).hexdigest()[:6]
        blunder_san = b.san(chess.Move.from_uci(v["mv"])) if v.get("mv") else "?"
        rec = dict(
            id=pid, fen=fen_before, moves=[setup_uci, v["best_uci"]],
            acceptable_uci=sorted(set(v["acc_uci"])),
            rating=0, difficulty="defensive",
            title=f"Defensive · hold the position (lost to {blunder_san})",
            themes=["defensiveMove", "kingSafety"], topic="defensive-king-safety",
            band="mined", kind="defensive",
            source_game=v["gid"], blunder_played=blunder_san,
            blunder_cp=v["blunder_cp"], best_cp=v["best_cp"],
            n_holding=v["n_holding"], n_legal=v["n_legal"],
        )
        # sanity: after setup it's White to move and acceptable moves are legal
        bb = chess.Board(rec["fen"]); bb.push(chess.Move.from_uci(rec["moves"][0]))
        if bb.turn == chess.WHITE and all(
                chess.Move.from_uci(m) in bb.legal_moves for m in rec["acceptable_uci"]):
            out.append(rec)
    return out


def main() -> None:
    fulls = _full_games()
    cands = mine(fulls)
    print(f"mined {len(cands)} pre-blunder positions (agent lost by mate)")
    verified = verify(cands)
    fair = [v for v in verified if v["fair"]]
    print(f"verified {len(fair)}/{len(verified)} as FAIR (a holding move exists; "
          f"the agent's move lost; not all moves hold)")
    puzzles = export(verified, fulls)
    OUT.write_text(json.dumps(puzzles, indent=1))
    print(f"exported {len(puzzles)} defensive puzzles -> {OUT.relative_to(CHESS_ROOT)}")


if __name__ == "__main__":
    main()
