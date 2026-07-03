"""CLI for the game-review engine.

Examples (run from backend/, with the chess venv):

    # one PGN file
    python -m app.review.cli --pgn game.pgn

    # one of our game-log JSONs (uses its uci_moves)
    python -m app.review.cli --game-json games/baseline/<id>.json

    # a whole folder of game logs -> one review per game + an aggregate weakness report
    python -m app.review.cli --games-dir games/<folder> --player white

    # ad-hoc move list
    python -m app.review.cli --moves e2e4 e7e5 g1f3 ...

Reviews are written to games/reviews/ (or --out-dir). The aggregate weakness report is
games/reviews/_aggregate.json. Stockfish path/depth come from CHESS_STOCKFISH_PATH /
--depth.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from app.config import get_settings
from app.review import review_game, write_review, load_reviews, write_aggregate


def _review_game_json(path: Path, depth: int, sf: str, out_dir: Path | None) -> dict:
    d = json.loads(path.read_text())
    moves = d.get("uci_moves")
    if not moves:
        raise ValueError(f"{path} has no uci_moves")
    r = review_game(
        moves=moves, stockfish_path=sf, depth=depth,
        game_id=d.get("game_id") or path.stem,
        headers={"White": str(d.get("white")), "Black": str(d.get("black")),
                 "Result": d.get("result", "*")},
    )
    write_review(r, out_dir=out_dir)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chess game-review engine.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pgn", help="path to a .pgn file")
    src.add_argument("--moves", nargs="+", help="UCI or SAN moves")
    src.add_argument("--game-json", help="one of our game-log JSON files (uses uci_moves)")
    src.add_argument("--games-dir", help="a folder of game-log JSONs to review in bulk")
    ap.add_argument("--start-fen", default=None, help="start FEN for --moves")
    ap.add_argument("--depth", type=int, default=18)
    ap.add_argument("--multipv", type=int, default=3)
    ap.add_argument("--out-dir", default=None, help="where to write reviews (default games/reviews)")
    ap.add_argument("--player", default="white", choices=["white", "black"],
                    help="which player the aggregate weakness report is for")
    args = ap.parse_args(argv)

    sf = os.environ.get("CHESS_STOCKFISH_PATH") or get_settings().stockfish_path
    out_dir = Path(args.out_dir) if args.out_dir else None

    if args.games_dir:
        files = [Path(p) for p in sorted(glob.glob(str(Path(args.games_dir) / "*.json")))
                 if not p.endswith("_agent.json") and "elo" not in os.path.basename(p)]
        if not files:
            print(f"no game JSONs in {args.games_dir}", file=sys.stderr); return 2
        print(f"reviewing {len(files)} games at depth {args.depth} …")
        for i, f in enumerate(files, 1):
            try:
                r = _review_game_json(f, args.depth, sf, out_dir)
                s = r["summary"]
                print(f"  [{i}/{len(files)}] {f.stem[:12]}  "
                      f"W acc {s['white']['accuracy_pct']}  B acc {s['black']['accuracy_pct']}")
            except Exception as e:  # noqa: BLE001
                print(f"  [{i}/{len(files)}] {f.stem[:12]}  ERROR: {e}", file=sys.stderr)
        agg_path = write_aggregate(load_reviews(out_dir), out_dir=out_dir)
        print(f"aggregate weakness report -> {agg_path}")
        agg = json.loads(agg_path.read_text())[args.player]
        print(f"\n== {args.player.upper()} weakness report ({agg['n_games']} games) ==")
        print(f"mean accuracy: {agg['mean_accuracy_pct']}  mean avg-CPL: {agg['mean_avg_centipawn_loss']}")
        print("top weakness tags (by mistake rate):")
        for tag, v in list(agg["weakness_tags"].items())[:10]:
            print(f"  {tag:28s} mistakes {v['n_mistakes']}/{v['n_total']}  rate {v['mistake_rate']}")
        return 0

    if args.pgn:
        r = review_game(pgn=Path(args.pgn).read_text(), stockfish_path=sf,
                        depth=args.depth, multipv=args.multipv)
    elif args.game_json:
        r = _review_game_json(Path(args.game_json), args.depth, sf, out_dir)
        _print_one(r); return 0
    else:
        r = review_game(moves=args.moves, start_fen=args.start_fen, stockfish_path=sf,
                        depth=args.depth, multipv=args.multipv)
    path = write_review(r, out_dir=out_dir)
    _print_one(r)
    print(f"\nwritten -> {path}")
    return 0


def _print_one(r: dict) -> None:
    s = r["summary"]
    print(f"result {r.get('result')}  |  White accuracy {s['white']['accuracy_pct']}  "
          f"Black accuracy {s['black']['accuracy_pct']}")
    for color in ("white", "black"):
        wm = s[color]["worst_moments"]
        if wm:
            print(f"  {color} worst:")
            for w in wm[:3]:
                print(f"    ply {w['ply']} {w['move']} ({w['classification']}, "
                      f"-{w['win_pct_lost']}% win) better: {w['better_move']}")


if __name__ == "__main__":
    raise SystemExit(main())
