"""JavaScript snippets injected into the chess.com /play/computer page.

All snippets are wrapped as single-argument (or zero-argument) IIFEs so they
can be passed straight to Playwright's ``page.evaluate``.

The DOM/JS API contract these rely on was verified empirically:

- ``wc-chess-board.board`` is the custom element that owns ``board.game``.
- ``board.game`` exposes a stable-ish API: ``getFEN``, ``getLastMove``,
  ``getHistorySANs``, ``getTurn``, ``getPlayingAs``, ``isGameOver``,
  ``getCalculatedResult``, ``setOptions``.
- ``board.classList`` contains ``flipped`` when the user plays black.
- ``board.game.move({from, to})`` updates internal state but does NOT
  trigger the bot's reply. The bot only replies to genuine pointer/mouse
  events on the board element, which is why ``SUBMIT_MOVE`` simulates
  pointerdown+mousedown+pointerup+mouseup at the source and destination
  square pixel centers.
- The Engine bot slider is a controlled React ``<input type=range>``;
  setting ``.value`` directly is ignored. ``SET_RANGE_VALUE`` uses the
  HTMLInputElement prototype's native setter so React's onChange fires.
"""

from __future__ import annotations


# ---- Engine bot selection ----

SET_RANGE_VALUE = """
([selector, value]) => {
    const input = document.querySelector(selector);
    if (!input) return false;
    const proto = Object.getPrototypeOf(input);
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(input, String(value));
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
}
"""

GET_SELECTED_RATING = """
() => {
    const el = document.querySelector('.selected-bot-introduction-rating');
    return el ? el.textContent.trim() : null;
}
"""


# ---- Game state ----

GET_GAME_STATE = """
() => {
    const board = document.querySelector('wc-chess-board.board');
    if (!board || !board.game) return null;
    const g = board.game;
    let last = null;
    try { last = g.getLastMove(); } catch (e) { last = null; }
    return {
        fen: g.getFEN(),
        turn: g.getTurn(),
        playingAs: g.getPlayingAs(),
        isGameOver: g.isGameOver(),
        result: g.getCalculatedResult(),
        historySANs: typeof g.getHistorySANs === 'function' ? g.getHistorySANs() : [],
        lastMove: last ? {
            from: last.from,
            to: last.to,
            san: last.san,
            color: last.color,
            userGenerated: last.userGenerated || false,
            promotion: last.promotion || null,
        } : null,
        flipped: board.classList.contains('flipped'),
    };
}
"""

SET_AUTO_PROMOTE = """
() => {
    const board = document.querySelector('wc-chess-board.board');
    if (!board || !board.game) return false;
    try { board.game.setOptions({autoPromote: true}); return true; }
    catch (e) { return false; }
}
"""


# ---- Move submission ----
#
# Note: ``uci`` here is the source+destination encoded as e.g. "e2e4". We
# ignore the promotion suffix because we've already enabled autoPromote.
SUBMIT_MOVE = """
(uci) => {
    const board = document.querySelector('wc-chess-board.board');
    if (!board) throw new Error('No board element');
    const rect = board.getBoundingClientRect();
    const size = rect.width / 8;
    const fileMap = {a:1, b:2, c:3, d:4, e:5, f:6, g:7, h:8};
    const flipped = board.classList.contains('flipped');
    const fromSq = uci.slice(0, 2);
    const toSq = uci.slice(2, 4);
    const squareCenter = (sq) => {
        const file = fileMap[sq[0]];
        const rank = parseInt(sq[1], 10);
        let cx, cy;
        if (!flipped) {
            cx = rect.left + (file - 0.5) * size;
            cy = rect.top + (8 - rank + 0.5) * size;
        } else {
            cx = rect.left + (8 - file + 0.5) * size;
            cy = rect.top + (rank - 0.5) * size;
        }
        return {x: cx, y: cy};
    };
    const fire = (x, y) => {
        const opts = {bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0};
        board.dispatchEvent(new PointerEvent('pointerdown', opts));
        board.dispatchEvent(new MouseEvent('mousedown', opts));
        board.dispatchEvent(new PointerEvent('pointerup', opts));
        board.dispatchEvent(new MouseEvent('mouseup', opts));
    };
    const src = squareCenter(fromSq);
    const dst = squareCenter(toSq);
    fire(src.x, src.y);
    fire(dst.x, dst.y);
    return true;
}
"""


# ---- Misc helpers ----

BOARD_READY = """
() => {
    const board = document.querySelector('wc-chess-board.board');
    return !!(board && board.game && typeof board.game.getFEN === 'function');
}
"""
