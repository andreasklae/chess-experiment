"""Orchestrates a batch of agent games on top of GameService.

Only one batch is active at a time (matches the single-game architecture of
GameService). A running batch:

1. Creates the next game in the batch (agent white vs Maia/chesscom black).
2. Waits for the game to finish (via the GameService.on_game_finished hook).
3. Updates the persistent agent ELO with the result.
4. Repeats until `total_games` games have completed, the batch is paused,
   or the user stops it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.batch_service import Batch, BatchService, GameRecord, normalize_result
from app.elo import update_elo
from app.game_service import Game, GameService


logger = logging.getLogger(__name__)


class BatchRunner:
    def __init__(self, batch_service: BatchService, game_service: GameService):
        self._batches = batch_service
        self._games = game_service
        self._active_batch_id: str | None = None
        self._next_game_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        # GameService fires this when a game ends naturally. We use it to
        # advance the batch.
        game_service.set_on_game_finished(self._handle_game_finished)

    # ── Public API ───────────────────────────────────────────────────────

    def active_batch_id(self) -> str | None:
        return self._active_batch_id

    def get(self, batch_id: str) -> Batch | None:
        return self._batches.load(batch_id)

    def list_all(self) -> list[Batch]:
        return self._batches.list_all()

    def get_active(self) -> Batch | None:
        if self._active_batch_id is None:
            return None
        return self._batches.load(self._active_batch_id)

    async def start(self, batch_id: str) -> Batch:
        """Begin or resume a batch. Idempotent."""
        if self._active_batch_id is not None and self._active_batch_id != batch_id:
            raise RuntimeError(
                f"Batch {self._active_batch_id} is already running; stop it before starting another."
            )
        batch = self._batches.load(batch_id)
        if batch is None:
            raise ValueError(f"Unknown batch: {batch_id}")
        if batch.is_terminal:
            raise ValueError(f"Batch {batch_id} is in terminal state {batch.status!r}.")

        self._active_batch_id = batch_id
        batch.status = "running"
        batch.last_error = ""
        self._batches.save(batch)
        logger.info("batch start · %s '%s' pool=%s games=%d/%d",
                    batch_id[:8], batch.label, batch.pool, batch.completed_count, batch.total_games)

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
        # Wake the loop in case it's idling on the event.
        self._next_game_event.set()
        return batch

    async def pause(self, batch_id: str) -> Batch:
        batch = self._batches.load(batch_id)
        if batch is None:
            raise ValueError(f"Unknown batch: {batch_id}")
        if batch.is_terminal:
            return batch
        batch.status = "paused"
        self._batches.save(batch)
        logger.info("batch pause · %s (in-flight game will complete first)", batch_id[:8])
        return batch

    async def stop(self, batch_id: str) -> Batch:
        batch = self._batches.load(batch_id)
        if batch is None:
            raise ValueError(f"Unknown batch: {batch_id}")
        batch.status = "stopped"
        self._batches.save(batch)
        logger.info("batch stop · %s", batch_id[:8])
        if self._active_batch_id == batch_id:
            self._active_batch_id = None
            self._next_game_event.set()
            # Also tear down the live game so the bot loop doesn't keep
            # playing after the user clicked Stop. Detach its batch_id so
            # the on-game-finished callback sees it as a non-batch game
            # and just sets the event without trying to advance the batch.
            current = self._games._game  # type: ignore[attr-defined]
            if current is not None and current.batch_id == batch_id:
                current.batch_id = ""
                await self._games.cancel_current_game()
        return batch

    async def delete(self, batch_id: str) -> None:
        """Stop (if active) and delete a batch's persistence file."""
        logger.info("batch delete · %s", batch_id[:8])
        if self._active_batch_id == batch_id:
            await self.stop(batch_id)
        self._batches.delete(batch_id)

    # ── Internal: the runner loop ────────────────────────────────────────

    async def _run_loop(self) -> None:
        """Drive games one at a time until the batch is done or paused.

        Each iteration:
        - Re-loads the batch from disk (in case it was paused/stopped).
        - If terminal or no longer the active batch, exits.
        - If a game is in progress, waits on `_next_game_event`.
        - Otherwise creates the next game.
        """
        try:
            while True:
                if self._active_batch_id is None:
                    return
                batch = self._batches.load(self._active_batch_id)
                if batch is None or batch.is_terminal:
                    self._active_batch_id = None
                    return

                if batch.status == "paused":
                    # Wait until someone calls start() again.
                    self._next_game_event.clear()
                    await self._next_game_event.wait()
                    continue

                if batch.completed_count >= batch.total_games:
                    batch.status = "completed"
                    self._batches.save(batch)
                    self._active_batch_id = None
                    return

                # Is there a game currently being played for this batch?
                current = self._games._game  # type: ignore[attr-defined]
                if current is not None and current.batch_id == batch.batch_id and not current.is_over():
                    # Wait for it to finish.
                    self._next_game_event.clear()
                    await self._next_game_event.wait()
                    continue

                # No current game (or current is from a different batch) — start the next one.
                await self._create_next_game(batch)
                # And wait for it to finish.
                self._next_game_event.clear()
                await self._next_game_event.wait()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Batch runner crashed: %s", exc)
            if self._active_batch_id is not None:
                batch = self._batches.load(self._active_batch_id)
                if batch is not None:
                    batch.status = "failed"
                    batch.last_error = str(exc)
                    self._batches.save(batch)
                self._active_batch_id = None

    async def _create_next_game(self, batch: Batch) -> None:
        agent_state = self._batches.load_agent_elo()
        request, opp_elo = self._batches.next_create_request(
            batch, agent_state.elo, agent_state.streak
        )
        elo_before = agent_state.elo

        logger.info(
            "batch %s · next game (%d/%d) · agent ELO %.0f (streak %+d) vs %s %d",
            batch.batch_id[:8],
            batch.completed_count + 1,
            batch.total_games,
            elo_before,
            agent_state.streak,
            batch.pool,
            opp_elo,
        )

        try:
            state = await self._games.create_game(request)
        except Exception as exc:
            logger.exception("batch %s · create_game failed: %s", batch.batch_id[:8], exc)
            batch.status = "failed"
            batch.last_error = str(exc)
            self._batches.save(batch)
            self._active_batch_id = None
            raise

        # Stamp the new in-memory Game with batch metadata.
        game = self._games._game  # type: ignore[attr-defined]
        if game is not None and game.game_id == state.game_id:
            game.batch_id = batch.batch_id
            game.batch_name = batch.label
            game.agent_elo_before = f"{elo_before:.1f}"

        batch.current_game_id = state.game_id
        self._batches.save(batch)

    def _handle_game_finished(self, game: Game) -> None:
        """Sync callback from GameService bot loop. Updates batch + ELO."""
        if not game.batch_id or game.batch_id != self._active_batch_id:
            # Not a batch game (or batch was stopped) — nothing to advance.
            logger.debug("on_game_finished · non-batch game %s (active=%s, game.batch=%s)",
                         game.game_id[:8], self._active_batch_id, game.batch_id or "—")
            self._next_game_event.set()
            return

        try:
            batch = self._batches.load(game.batch_id)
            if batch is None:
                self._next_game_event.set()
                return

            # Determine the result from agent's perspective.
            result_string = game.result()
            normalized = normalize_result(result_string, agent_color="white")
            aborted_reason = getattr(game, "aborted_reason", "")

            agent_state = self._batches.load_agent_elo()
            elo_before = agent_state.elo
            if normalized is not None:
                opp_elo = int(game.black_config.elo) if game.black_config.elo is not None else int(elo_before)
                agent_state.apply_result(opp_elo, normalized)
                self._batches.save_agent_elo(agent_state)
            elif aborted_reason:
                logger.warning(
                    "batch %s · game %s ABORTED · ELO unchanged · reason=%s",
                    batch.batch_id[:8],
                    game.game_id[:8],
                    aborted_reason[:120],
                )

            # Record game outcome in batch + persist before stamping the
            # finished Game so logging picks it up too (race-free because
            # _record_game_end ran inside the bot loop *before* this callback).
            game_record = GameRecord(
                game_id=game.game_id,
                opponent_elo=int(game.black_config.elo) if game.black_config.elo is not None else 0,
                result=normalized,
                agent_elo_before=elo_before,
                agent_elo_after=agent_state.elo,
            )
            batch.games.append(game_record)
            batch.current_game_id = None
            if batch.completed_count >= batch.total_games:
                batch.status = "completed"
                logger.info("batch %s · COMPLETED (%d/%d games)",
                            batch.batch_id[:8], batch.completed_count, batch.total_games)
            self._batches.save(batch)
            result_label = normalized or (f"aborted ({aborted_reason[:60]})" if aborted_reason else "aborted")
            logger.info(
                "batch %s · game %d done · result=%s · ELO %.0f → %.0f (vs opp %d) · streak %+d",
                batch.batch_id[:8],
                batch.completed_count,
                result_label,
                elo_before,
                agent_state.elo,
                game_record.opponent_elo,
                agent_state.streak,
            )

            # Also stamp elo_after on the (already-recorded) Game for any
            # later use — not used by the CSV, which is written before this
            # callback runs. The CSV's elo_before is correct; elo_after will
            # be one step behind by design (it's the *outgoing* ELO from
            # this game, which we now know).
            game.agent_elo_after = f"{agent_state.elo:.1f}"

        finally:
            self._next_game_event.set()
