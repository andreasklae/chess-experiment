"""Playwright-backed driver for chess.com /play/computer Engine bots.

The driver opens a real Chrome (via Playwright's ``channel="chrome"``) with a
persistent user-data directory so the existing chess.com login session is
reused. It then:

1. Navigates to ``/play/computer``.
2. Expands the Engine bot group and sets the slider to the position whose
   ELO is closest to the requested target.
3. Clicks Play.
4. Exposes ``submit_move`` / ``wait_for_bot_move`` / ``get_result`` for
   playing a game move-by-move from Python.

Internally everything goes through ``board.game`` (chess.com's custom
``<wc-chess-board>`` element), with one important exception: submitting a
move uses simulated pointer events on square pixels, because
``board.game.move()`` updates internal state but does not trigger the bot's
reply.

The driver assumes:

- The agent always plays white (so chess.com plays black). This is the
  experiment's documented methodology, not a v1 shortcut.
- Time control is "No Timer" (the default the page lands on when the Engine
  bot group is selected).
- ``autoPromote`` is enabled before any move is submitted, so under-promotion
  is not currently supported. python-chess's UCI promotion suffix is
  ignored by the click handler.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chess

from . import _js
from .exceptions import (
    ChessComGameError,
    ChessComIllegalMove,
    ChessComMoveTimeout,
    ChessComSetupError,
)
from .mapping import POSITION_TO_RATING, closest_position


logger = logging.getLogger(__name__)


PLAY_URL = "https://www.chess.com/play/computer"

# Color codes used by board.game.getLastMove(). Verified empirically: 1=white, 2=black.
_COLOR_WHITE = 1
_COLOR_BLACK = 2


@dataclass(frozen=True)
class GameStart:
    """Returned by :meth:`ChessComDriver.start_game` to describe what got picked.

    Attributes:
        slider_position: 1-25, position of the Engine bot slider.
        actual_rating: The rating shown next to the selected bot. May differ
            from the target ELO if no bot has an exact match.
        target_elo: The ELO the caller asked for.
    """

    slider_position: int
    actual_rating: int
    target_elo: int


class ChessComDriver:
    """Low-level browser driver.

    Lifecycle:

    .. code-block:: python

        driver = ChessComDriver(user_data_dir="/path/to/chrome-profile")
        await driver.launch()
        await driver.start_game(target_elo=400)
        while not await driver.is_game_over():
            await driver.submit_move(my_move)
            bot_move = await driver.wait_for_bot_move()
            ...
        await driver.close()

    All methods are coroutine-safe but not coroutine-concurrent on the same
    instance. Don't call ``submit_move`` and ``wait_for_bot_move``
    concurrently from different tasks.
    """

    def __init__(
        self,
        *,
        user_data_dir: str | Path,
        headless: bool = False,
        chrome_channel: str = "chrome",
        poll_interval: float = 0.25,
        bot_move_timeout: float = 60.0,
        slider_settle_delay: float = 0.45,
    ) -> None:
        self._user_data_dir = Path(user_data_dir)
        self._headless = headless
        self._chrome_channel = chrome_channel
        self._poll_interval = poll_interval
        self._bot_move_timeout = bot_move_timeout
        self._slider_settle_delay = slider_settle_delay

        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None
        self._last_seen_move_signature: tuple[str, str, int] | None = None

    # ----- lifecycle -----

    async def launch(self) -> None:
        """Start Playwright, open the persistent Chrome profile, navigate."""
        if self._page is not None:
            return

        # Import here so the package can be imported without Playwright
        # installed (e.g. for code that only needs the mapping table).
        from playwright.async_api import async_playwright

        self._user_data_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._user_data_dir),
            headless=self._headless,
            channel=self._chrome_channel,
            viewport={"width": 1280, "height": 900},
        )
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        # chess.com page load is occasionally slow after a previous game in
        # the same batch (network warm-up, ad-loader, etc.). Retry the goto
        # once with a longer timeout before giving up.
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                await self._page.goto(PLAY_URL, wait_until="domcontentloaded", timeout=60_000)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    "chess.com goto failed (attempt %d): %s", attempt, exc
                )
                await asyncio.sleep(2.0)
        if last_exc is not None:
            raise ChessComSetupError(
                f"Failed to load {PLAY_URL} after 2 attempts: {last_exc}"
            ) from last_exc
        await self._dismiss_first_run_modal()
        try:
            await self._page.wait_for_function(_js.BOARD_READY, timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            raise ChessComSetupError(
                "wc-chess-board not ready after navigating to /play/computer. "
                "Most likely Cloudflare or login is gating the page."
            ) from exc

    async def _dismiss_first_run_modal(self) -> None:
        """Dismiss any first-run overlays that block clicks on the bot picker.

        On a fresh user-data dir (we use one per game) two overlays appear:

        1. The chess.com intro modal (``dialog[data-cy="intro-modal"]``).
           This sits on top and intercepts everything. We try clicking the
           Start button first; if that doesn't work within a short window we
           force-hide it via JS so subsequent clicks always land correctly.
        2. The OneTrust cookie banner (``#onetrust-consent-sdk``). Hidden via
           JS — clicking it is unreliable across locales.

        Because we use an ephemeral temp dir for every game, the intro modal
        appears on every single launch and must be reliably dismissed.
        """
        assert self._page is not None

        # Intro modal — try clicking Start, then force-hide as fallback.
        try:
            start_btn = self._page.get_by_role("button", name=re.compile(r"^Start$", re.I))
            await start_btn.first.click(timeout=4_000)
            # Wait for the modal to actually leave the DOM before continuing.
            await self._page.locator('dialog[data-cy="intro-modal"]').wait_for(
                state="hidden", timeout=4_000
            )
        except Exception:
            # Force-hide as fallback (covers timing races and DOM changes).
            try:
                await self._page.evaluate(
                    "() => { const el = document.querySelector('dialog[data-cy=\"intro-modal\"]');"
                    " if (el) el.style.display = 'none'; }"
                )
            except Exception:
                pass

        # OneTrust cookie banner — hide via JS.
        try:
            await self._page.evaluate(
                "() => { const el = document.getElementById('onetrust-consent-sdk');"
                " if (el) el.style.display = 'none'; }"
            )
        except Exception:
            pass

    async def close(self) -> None:
        """Tear down Playwright. Idempotent."""
        if self._context is not None:
            try:
                await self._context.close()
            finally:
                self._context = None
                self._page = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            finally:
                self._playwright = None

    async def __aenter__(self) -> "ChessComDriver":
        await self.launch()
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.close()

    # ----- bot selection / game start -----

    async def start_game(self, target_elo: int) -> GameStart:
        """Select the closest Engine bot to ``target_elo`` and click Play.

        Returns a :class:`GameStart` describing the actual rating used.
        """
        if self._page is None:
            raise ChessComSetupError("launch() must be called before start_game()")

        position, expected_rating = closest_position(target_elo)

        await self._ensure_engine_group_open()
        await self._set_slider_position(position)
        await asyncio.sleep(self._slider_settle_delay)

        shown = await self._page.evaluate(_js.GET_SELECTED_RATING)
        if shown is not None:
            digits = re.search(r"\d+", shown)
            if digits and int(digits.group()) != expected_rating:
                logger.warning(
                    "Slider position %d shows rating %s but mapping expected %d",
                    position,
                    shown,
                    expected_rating,
                )

        await self._click_play()

        # Settle and enable auto-promote on the running game.
        await self._page.wait_for_function(_js.BOARD_READY, timeout=15_000)
        await self._page.evaluate(_js.SET_AUTO_PROMOTE)
        self._last_seen_move_signature = None

        return GameStart(
            slider_position=position,
            actual_rating=expected_rating,
            target_elo=target_elo,
        )

    async def _ensure_engine_group_open(self) -> None:
        """Expand the Engine bot accordion if it is collapsed.

        The Engine group is at the bottom of a long scrollable bot-group
        list, so we must scroll it into view before clicking — otherwise
        Playwright clicks register on an offscreen element and silently
        no-op.
        """
        assert self._page is not None

        # Belt-and-suspenders: force-hide the intro modal in case it is still
        # present (e.g. dismiss timing race between launch() and start_game()).
        try:
            await self._page.evaluate(
                "() => { const el = document.querySelector('dialog[data-cy=\"intro-modal\"]');"
                " if (el) el.style.display = 'none'; }"
            )
        except Exception:
            pass

        engine_group = self._page.locator('[data-cy="bot-group-Engine"]')
        toggle = engine_group.locator('[data-cy="bot-group-Engine-toggle"]')

        try:
            await toggle.wait_for(state="attached", timeout=10_000)
        except Exception as exc:  # noqa: BLE001
            raise ChessComSetupError(
                "Could not find the Engine bot group on /play/computer"
            ) from exc

        # If the slider is already visible inside the Engine group, it's open.
        if await engine_group.locator('input.slider-input').count() > 0:
            return

        await toggle.scroll_into_view_if_needed(timeout=5_000)
        await toggle.click(timeout=5_000)

        try:
            await engine_group.locator('input.slider-input').wait_for(
                state="visible", timeout=5_000
            )
        except Exception as exc:  # noqa: BLE001
            raise ChessComSetupError(
                "Engine slider didn't appear after clicking the Engine group toggle"
            ) from exc

    async def _set_slider_position(self, position: int) -> None:
        assert self._page is not None
        if position not in POSITION_TO_RATING:
            raise ValueError(f"Slider position out of range: {position}")
        ok = await self._page.evaluate(
            _js.SET_RANGE_VALUE,
            ['[data-cy="bot-group-Engine"] input.slider-input', position],
        )
        if not ok:
            raise ChessComSetupError("Failed to find slider input element")

    async def _click_play(self) -> None:
        assert self._page is not None
        # Multiple possible labels - the Play button is the most reliable.
        play = self._page.get_by_role("button", name=re.compile(r"^Play$", re.I))
        try:
            await play.first.click(timeout=5_000)
        except Exception as exc:  # noqa: BLE001
            raise ChessComSetupError("Could not click the Play button") from exc

    # ----- game state -----

    async def get_state(self) -> dict[str, Any]:
        """Return the current game state as reported by ``board.game``."""
        assert self._page is not None
        state = await self._page.evaluate(_js.GET_GAME_STATE)
        if state is None:
            raise ChessComGameError("board.game is not available on the page")
        return state

    async def get_fen(self) -> str:
        state = await self.get_state()
        return state["fen"]

    async def is_game_over(self) -> bool:
        state = await self.get_state()
        return bool(state["isGameOver"])

    async def get_result(self) -> str | None:
        """Return ``"1-0"``, ``"0-1"``, ``"1/2-1/2"``, or ``None`` if ongoing.

        The chess.com API returns ``"*"`` while the game is still in progress;
        we normalize that to ``None``.
        """
        state = await self.get_state()
        result = state.get("result")
        if not result or result == "*":
            return None
        return result

    # ----- move submission -----

    async def submit_move(self, move: chess.Move) -> None:
        """Play ``move`` on the board as white.

        Raises :class:`ChessComIllegalMove` if chess.com rejects it.
        """
        assert self._page is not None
        uci = move.uci()
        # Capture the last move signature *before* submitting so we can
        # detect that chess.com actually applied the move (and not silently
        # ignored it).
        state_before = await self.get_state()
        sig_before = _move_signature(state_before.get("lastMove"))

        await self._page.evaluate(_js.SUBMIT_MOVE, uci)

        # Wait briefly for our own move to register.
        deadline = asyncio.get_event_loop().time() + 5.0
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(self._poll_interval)
            state = await self.get_state()
            last = state.get("lastMove")
            sig = _move_signature(last)
            if sig != sig_before and last and last["color"] == _COLOR_WHITE:
                self._last_seen_move_signature = sig
                return

        raise ChessComIllegalMove(
            f"chess.com did not register move {uci}; the click may have missed "
            "the board or the move is illegal in the current position."
        )

    async def wait_for_bot_move(self, timeout: float | None = None) -> chess.Move:
        """Block until chess.com plays a black move, then return it.

        The returned ``chess.Move`` is reconstructed from the SAN reported by
        ``board.game.getLastMove()``, so it carries the correct promotion
        piece (if any) when chess.com underpromotes.
        """
        assert self._page is not None
        timeout = timeout if timeout is not None else self._bot_move_timeout
        deadline = asyncio.get_event_loop().time() + timeout

        sig_to_beat = self._last_seen_move_signature

        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(self._poll_interval)
            state = await self.get_state()
            last = state.get("lastMove")
            if last is None:
                continue
            sig = _move_signature(last)
            if last["color"] == _COLOR_BLACK and sig != sig_to_beat:
                self._last_seen_move_signature = sig
                return _last_move_to_chess_move(last, state)
            # If the game ended before the bot moved (e.g. checkmate by us),
            # signal that explicitly.
            if state["isGameOver"]:
                raise ChessComGameError(
                    f"Game ended before the bot moved: result={state['result']}"
                )

        raise ChessComMoveTimeout(f"chess.com bot did not move within {timeout:.1f}s")


def _move_signature(last_move: dict[str, Any] | None) -> tuple[str, str, int] | None:
    if not last_move:
        return None
    return (last_move.get("from", ""), last_move.get("to", ""), int(last_move.get("color", 0)))


def _last_move_to_chess_move(last_move: dict[str, Any], state: dict[str, Any]) -> chess.Move:
    """Convert the JS ``lastMove`` object to a ``chess.Move``.

    Prefers SAN reconstruction (uses the full game history to disambiguate
    promotion piece etc.). Falls back to UCI-from-coords if SAN parsing fails.
    """
    san = last_move.get("san")
    history_sans: list[str] = state.get("historySANs") or []
    if san and history_sans:
        # Replay the full history on a fresh board, then look up the move
        # generated by parsing the final SAN.
        board = chess.Board()
        try:
            for past in history_sans[:-1]:
                board.push_san(past)
            return board.parse_san(history_sans[-1])
        except (ValueError, chess.IllegalMoveError):
            pass

    from_sq = last_move.get("from")
    to_sq = last_move.get("to")
    promo = (last_move.get("promotion") or "").lower()
    if not from_sq or not to_sq:
        raise ChessComGameError(f"Cannot parse bot move from chess.com: {last_move!r}")
    return chess.Move.from_uci(f"{from_sq}{to_sq}{promo}")
