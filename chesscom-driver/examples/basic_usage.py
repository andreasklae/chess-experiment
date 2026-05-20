"""Minimal end-to-end demo: play a few moves against a chess.com Engine bot.

Run from the package root::

    pip install -e .
    playwright install chrome   # if you haven't already
    python examples/basic_usage.py --user-data-dir ~/.config/chesscom-driver-profile

You will need to log in to chess.com once in the spawned browser; the
persistent profile keeps you logged in for subsequent runs.
"""

from __future__ import annotations

import argparse
import asyncio

import chess

from chesscom_driver import ChessComDriver


async def main(user_data_dir: str, target_elo: int) -> None:
    async with ChessComDriver(user_data_dir=user_data_dir) as driver:
        start = await driver.start_game(target_elo=target_elo)
        print(
            f"Started game vs Engine bot at rating {start.actual_rating} "
            f"(slider position {start.slider_position}, requested {start.target_elo})"
        )

        # Toy "agent": play a fixed opening sequence as white, then resign.
        opening = ["e2e4", "g1f3", "f1c4", "d2d3"]
        board = chess.Board()

        for uci in opening:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                print(f"Skipping {uci}: illegal in current position")
                break

            print(f"White: {board.san(move)}")
            await driver.submit_move(move)
            board.push(move)

            if await driver.is_game_over():
                break

            bot_move = await driver.wait_for_bot_move()
            print(f"Black: {board.san(bot_move)}")
            board.push(bot_move)

            if await driver.is_game_over():
                break

        result = await driver.get_result()
        print(f"Final FEN: {board.fen()}")
        print(f"Result so far: {result or 'ongoing'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-data-dir", required=True)
    parser.add_argument("--elo", type=int, default=400)
    args = parser.parse_args()
    asyncio.run(main(args.user_data_dir, args.elo))
