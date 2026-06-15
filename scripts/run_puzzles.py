#!/usr/bin/env python3
"""Run the agent against a suite of mating/conversion puzzle positions.

Each puzzle starts a game from a custom FEN (puzzle mode, initial_fen on
POST /api/games) with the agent as white and Maia as black, waits for it to
finish, and reports how the agent did: result, plies used, and whether it
delivered checkmate.

Usage (backend must be running, eX3 tunnel up):
    python3 scripts/run_puzzles.py                  # full suite vs maia-1100
    python3 scripts/run_puzzles.py --only kq-basic ladder
    python3 scripts/run_puzzles.py --elo 1500
    python3 scripts/run_puzzles.py --base http://localhost:8000

Puzzle games are ordinary agent games on a non-main git state: they land in
games/experimental.csv with ELO frozen. This script is a measurement aid,
not part of the calibration pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

PUZZLES = [
    {
        "id": "backrank-m1",
        "max_plies": 8,
        "name": "Back-rank mate in 1",
        "fen": "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1",
        "expect": "1-0 immediately (Ra8#). Tests mate-spotting + radar.",
    },
    {
        "id": "kq-basic",
        "max_plies": 40,
        "name": "K+Q vs K basic mate",
        "fen": "8/8/4k3/8/8/8/8/3QK3 w - - 0 1",
        "expect": "1-0 in under ~20 plies. Tests king-queen-mate technique.",
    },
    {
        "id": "kr-basic",
        "max_plies": 60,
        "name": "K+R vs K basic mate",
        "fen": "8/8/4k3/8/8/8/8/R3K3 w - - 0 1",
        "expect": "1-0 in under ~32 plies. Tests king-rook-mate technique.",
    },
    {
        "id": "ladder",
        "max_plies": 30,
        "name": "Two-rook ladder mate",
        "fen": "8/8/3k4/8/8/8/R7/1R4K1 w - - 0 1",
        "expect": "1-0 in under ~12 plies. Tests ladder-mate page.",
    },
    {
        "id": "promote-convert",
        "max_plies": 60,
        "name": "K+P escort, promote, then mate",
        "fen": "8/8/5k2/8/5K2/8/4P3/8 w - - 0 1",
        "expect": "1-0. Capablanca Ex.6: king in front, opposition, promote, mate.",
    },
    {
        "id": "philidor",
        "max_plies": 14,
        "name": "Smothered mate setup (Philidor's legacy, forced in 5)",
        "fen": "5rk1/6pp/8/6N1/8/8/8/4Q1K1 w - - 0 1",
        "expect": "1-0 in 9 plies: Qe6+ Kh8 Nf7+ Kg8 Nh6+ Kh8 Qg8+ Rxg8 Nf7#. Tests trigger -> page -> forced sequence.",
    },
    {
        "id": "arabian-net",
        "max_plies": 60,
        "name": "R+N vs cornered king (Arabian geometry)",
        "fen": "7k/8/8/8/4N3/8/8/R5K1 w - - 0 1",
        "expect": "1-0. Arabian trigger fires; K+R drill also wins ignoring the knight.",
    },
    {
        "id": "r2b-convert",
        "max_plies": 40,
        "name": "R+2B conversion (drawn in ranked game 72aa5cfc)",
        "fen": "8/3B4/8/k3B3/8/2R2P2/1P4PK/8 w - - 0 1",
        "expect": "1-0. The exact final position of the 150-ply draw vs chesscom-1000.",
    },
]


def _post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _get(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=30) as resp:
        return json.loads(resp.read().decode())


def run_puzzle(base: str, puzzle: dict, elo: int, poll_s: float, timeout_s: float) -> dict:
    state = _post(base, "/api/games", {
        "white": {"type": "agent"},
        "black": {"type": "maia", "elo": elo},
        "initial_fen": puzzle["fen"],
        "max_half_moves": puzzle.get("max_plies"),
    })
    game_id = state["game_id"]
    print(f"  game {game_id[:8]} started", flush=True)

    deadline = time.monotonic() + timeout_s
    last_plies = -1
    while time.monotonic() < deadline:
        time.sleep(poll_s)
        state = _get(base, f"/api/games/{game_id}")
        plies = len(state["uci_moves"])
        if plies != last_plies:
            last_san = state["san_moves"][-1] if state["san_moves"] else "-"
            print(f"    ply {plies:3d}  last {last_san}", flush=True)
            last_plies = plies
        if state.get("aborted_reason"):
            return {"id": puzzle["id"], "game_id": game_id, "result": "ABORTED",
                    "termination": state["aborted_reason"][:120],
                    "plies": len(state["uci_moves"]), "mate": False}
        if state["status"] == "finished":
            break
    else:
        return {"id": puzzle["id"], "game_id": game_id, "result": "TIMEOUT",
                "plies": len(state["uci_moves"]), "mate": False}

    import re
    mate = bool(state["san_moves"]) and state["san_moves"][-1].endswith("#")
    result = state["result"]
    if result != "1-0":
        # Within a tight per-puzzle cap, anything but a win is a fail.
        result = f"FAIL({result})"
    return {
        "id": puzzle["id"],
        "game_id": game_id,
        "result": result,
        "termination": state.get("termination"),
        "plies": len(state["uci_moves"]),
        "mate": mate,
        "moves": " ".join(state["san_moves"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--elo", type=int, default=1100, help="Maia elo for black")
    ap.add_argument("--only", nargs="*", default=None, help="Puzzle ids to run")
    ap.add_argument("--poll", type=float, default=5.0)
    ap.add_argument("--timeout", type=float, default=3600.0, help="Per-puzzle wall-clock cap (s)")
    ap.add_argument("--report", default=None, help="Write JSON report to this path")
    args = ap.parse_args()

    suite = [p for p in PUZZLES if args.only is None or p["id"] in args.only]
    if not suite:
        print(f"No puzzles match {args.only}. Available: {[p['id'] for p in PUZZLES]}")
        sys.exit(1)

    # Puzzles run strictly one at a time: each run_puzzle call blocks until
    # its game finishes before the next POST /api/games happens (and the
    # backend's single-game slot would close a still-running game anyway).
    # Infra aborts stop the whole suite — when the eX3 tunnel drops, every
    # subsequent game would just burn its attempts and record a bogus 0-1
    # (observed 2026-06-12: games 037-039 all "agent_resigned_no_move"
    # within 30 seconds of a tunnel failure in 036).
    _INFRA_MARKERS = (
        "peer closed", "incomplete chunked read", "tunnel", "connection",
        "game_vanished", "context_overflow", "timed out",
    )
    results = []
    for puzzle in suite:
        print(f"\n=== {puzzle['id']}: {puzzle['name']}")
        print(f"  FEN    {puzzle['fen']}")
        print(f"  expect {puzzle['expect']}")
        try:
            res = run_puzzle(args.base, puzzle, args.elo, args.poll, args.timeout)
            results.append(res)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            results.append({"id": puzzle["id"], "result": "ERROR", "error": str(exc)})
            print("  Backend unreachable — stopping the suite.")
            break
        term = str(res.get("termination") or "").lower()
        if res["result"] == "ABORTED" and any(m in term for m in _INFRA_MARKERS):
            print(f"  Infrastructure abort ({res['termination']}) — stopping "
                  f"the suite. Fix the tunnel/backend and re-run with --only "
                  f"for the remaining puzzles.")
            break

    print("\n===== Summary =====")
    print(f"{'puzzle':18} {'result':8} {'plies':>5}  mate  game")
    for r in results:
        print(f"{r['id']:18} {str(r.get('result')):8} {r.get('plies', '-'):>5}  "
              f"{'yes' if r.get('mate') else 'no ':4}  {r.get('game_id', '')[:8]}")

    if args.report:
        with open(args.report, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nreport written to {args.report}")


if __name__ == "__main__":
    main()
