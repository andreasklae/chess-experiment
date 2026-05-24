# chesscom-driver

Play chess.com's Engine bots from Python by driving a real Chrome browser
with Playwright. Designed as a drop-in `Player` for the chess experiment's
backend; usable standalone as a thin Python API.

The agent always plays **white**; this driver always plays **black**.
That's an experiment-design choice, not a v1 limitation — see [Why
white-only](#why-white-only).

---

## Table of contents

1. [Why this exists](#why-this-exists)
2. [What it does](#what-it-does)
3. [What it doesn't do](#what-it-doesnt-do)
4. [Install](#install)
5. [First-time setup: log in once](#first-time-setup-log-in-once)
6. [Quickstart: standalone usage](#quickstart-standalone-usage)
7. [Integration: plugging into a Player ABC](#integration-plugging-into-a-player-abc)
8. [How it works under the hood](#how-it-works-under-the-hood)
9. [ELO coverage and the slider mapping](#elo-coverage-and-the-slider-mapping)
10. [Configuration reference](#configuration-reference)
11. [Error handling](#error-handling)
12. [Troubleshooting](#troubleshooting)
13. [Limitations and known gaps](#limitations-and-known-gaps)
14. [Layout](#layout)
15. [Maintenance notes (when chess.com breaks the DOM)](#maintenance-notes-when-chesscom-breaks-the-dom)

---

## Why this exists

The chess experiment evaluates an agent at multiple ELOs. Maia covers
1100-1900, but the agent plays in the sub-1100 range during calibration,
so the experiment needs sub-1100 opponents. Lichess has bots in that
range but imposes time controls, which break the experiment's
no-time-pressure design. Chess.com has Engine bots from 250 to 3200 ELO
with no time pressure — and no public API. Hence Playwright.

A real Chrome (Playwright's `channel="chrome"`) with a persistent
user-data directory keeps the chess.com login cookie and behaves like a
normal logged-in user, so Cloudflare doesn't gate the page.

## What it does

- Launches Chrome with a persistent profile so login survives across runs.
- Navigates to `chess.com/play/computer`.
- Picks an Engine bot at (or nearest to) a target ELO.
- Starts a game.
- Lets you submit white moves (`chess.Move`) and reads back black moves
  (`chess.Move`).
- Reports game-over status and result.
- Exposes a `Player`-compatible adapter (`ChessComPlayer`) with the
  signature `async def get_move(board, last_san) -> chess.Move`.

## What it doesn't do

- Bypass CAPTCHAs (if chess.com challenges you, solve it in the spawned
  window).
- Play character bots (Polly, Martin, etc.) — only the **Engine** bot
  group. Engine bots are Stockfish with skill caps and cover the full
  ELO range we need.
- Play timed games — uses the "No Timer" default.
- Underpromote — `autoPromote: true` always queens. UCI promotion
  suffixes on submitted moves are accepted and ignored.
- Play black. The agent always plays white per the experiment design.

---

## Install

```bash
# from the chess-driver directory
pip install -e .

# install Chrome under Playwright's control (only if not already done)
playwright install chrome
```

Requirements:
- Python 3.11+
- Chrome installed system-wide (the driver uses `channel="chrome"` to
  reuse it)
- `python-chess` and `playwright` (declared in `pyproject.toml`)

If you don't want to install the package globally, the integrated path
inside the chess experiment is `pip install -e experiments/chess/chesscom-driver`
from the chess project root.

## First-time setup: log in once

The driver uses a **persistent user-data directory** to remember your
chess.com session. You pick the directory; the driver writes to it.

```bash
python examples/basic_usage.py --user-data-dir ~/.config/chesscom-driver-profile --elo 400
```

What happens on first run:

1. Chrome opens with a fresh profile.
2. The script navigates to `/play/computer`.
3. Chess.com prompts you to log in or sign up.
4. **Pause the script** (Ctrl-C is fine), log in interactively, then
   re-run. Or, if the script is fast enough to keep the page alive, log
   in in the spawned window and let the script proceed.
5. The cookie is now saved in the user-data directory.

Subsequent runs reuse the profile and skip login entirely. You can pick
any path you like for the profile; just keep using the same one.

**Important:** don't reuse a directory another Chrome instance is
already using — Chrome refuses to open two windows on the same profile.
Make a dedicated directory for this driver.

---

## Quickstart: standalone usage

```python
import asyncio
import chess
from chesscom_driver import ChessComDriver

async def play_a_game():
    async with ChessComDriver(user_data_dir="~/.config/chesscom-driver-profile") as driver:
        # Pick a bot at (or near) the target ELO and click Play.
        start = await driver.start_game(target_elo=400)
        print(f"Playing rating {start.actual_rating} "
              f"(slider position {start.slider_position})")

        board = chess.Board()

        # Submit a white move.
        move = chess.Move.from_uci("e2e4")
        await driver.submit_move(move)
        board.push(move)

        # Wait for the bot's reply.
        bot_move = await driver.wait_for_bot_move()
        board.push(bot_move)
        print(f"Bot replied: {board.peek().uci()}")

        # Check game state.
        if await driver.is_game_over():
            result = await driver.get_result()  # "1-0" | "0-1" | "1/2-1/2"
            print(f"Result: {result}")

asyncio.run(play_a_game())
```

That's the whole API. `start_game` once, then alternate `submit_move` and
`wait_for_bot_move` until `is_game_over()` is true.

---

## Integration: plugging into a Player ABC

If your host project has a `Player` ABC with:

```python
class Player(ABC):
    @abstractmethod
    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move: ...
```

then `ChessComPlayer` already conforms. Plug it in like this:

```python
# in your players.py
from chesscom_driver import ChessComPlayer as _DriverPlayer

class ChessComPlayer(_DriverPlayer, Player):
    """Subclassed so isinstance(p, Player) checks pass elsewhere."""
    pass

# in your factory:
def create(self, config):
    if config.type == "chesscom":
        return ChessComPlayer(
            target_elo=config.elo,
            user_data_dir=settings.chesscom_user_data_dir,
        )
```

Lifecycle:
- `ChessComPlayer(target_elo=...)` **does not** open the browser.
- The first call to `get_move` lazily launches Chrome, picks the bot,
  and starts a game.
- Subsequent `get_move` calls submit the agent's last move and wait for
  the bot's reply.
- Call `await player.close()` when the game is over to shut down Chrome.

Why lazy launch? Player factories typically construct synchronously, but
launching Playwright requires `await`. Lazy launch on the first
`get_move` call avoids an awkward `async def setup()` step in the host.

### The `get_move` contract

`ChessComPlayer.get_move(board, last_san)` expects `last_san` to be the
agent's last move (the white move just played). The adapter:

1. Parses `last_san` on its internal `chess.Board` to a `chess.Move`.
2. Submits that move to chess.com via simulated pointer events.
3. Polls `board.game.getLastMove()` until chess.com's bot has replied.
4. Returns the bot's move as a `chess.Move`.

The `board` argument is used only to validate the bot's move is legal
in the host's view of the position. The adapter maintains its own
internal board because the host passes a `stack=False` copy that has no
move history (so `board.peek()` won't work).

---

## How it works under the hood

Three things to know if you ever need to debug or extend this.

### 1. The page exposes a JS API

The custom element `wc-chess-board.board` owns an instance member
`board.game` with verified methods:

- `getFEN()`, `getLastMove()`, `getHistorySANs()`, `getTurn()`,
  `getPlayingAs()`, `isGameOver()`, `getCalculatedResult()`.
- `setOptions({autoPromote: true})` — enables auto-queening.
- `move({from, to})` — updates the board state but does **NOT** trigger
  the bot's reply. We don't use this.
- `onAll(cb)` — fires events like `{type: "Move", data: {move: {san,
  from, to, color, userGenerated}}}`. We don't use it; polling is
  simpler.

### 2. Moves must be submitted as pointer events

`board.game.move({from, to})` updates internal state but the bot won't
reply. Only genuine pointer/mouse events on board pixels trigger the
bot. The driver dispatches `pointerdown` + `mousedown` + `pointerup` +
`mouseup` at the source and destination square centers.

Coordinates: square *a1* is at the bottom-left when the board is not
flipped. The driver doesn't flip because the agent always plays white,
but the `flipped` branch is in place if you ever invert.

### 3. The Engine slider needs React-compatible writes

The slider is a controlled React `<input type=range>`. Setting `.value`
directly is ignored. The driver uses the HTMLInputElement prototype's
native setter, then dispatches `input` and `change` events:

```javascript
const setter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(input), 'value'
).set;
setter.call(input, String(position));
input.dispatchEvent(new Event('input', {bubbles: true}));
input.dispatchEvent(new Event('change', {bubbles: true}));
```

The React state takes ~400 ms to settle. Reading
`.selected-bot-introduction-rating` faster than that returns stale data.

---

## ELO coverage and the slider mapping

The Engine slider has 25 discrete positions:

| Pos | Rating | | Pos | Rating | | Pos | Rating |
|---:|---:|---|---:|---:|---|---:|---:|
|  1 |  250 | |  10 | 1400 | |  19 | 2300 |
|  2 |  400 | |  11 | 1500 | |  20 | 2400 |
|  3 |  550 | |  12 | 1600 | |  21 | 2500 |
|  4 |  700 | |  13 | 1700 | |  22 | 2600 |
|  5 |  850 | |  14 | 1800 | |  23 | 2800 |
|  6 | 1000 | |  15 | 1900 | |  24 | 3000 |
|  7 | 1100 | |  16 | 2000 | |  25 | 3200 |
|  8 | 1200 | |  17 | 2100 | |
|  9 | 1300 | |  18 | 2200 | |

Step sizes: 150 (pos 1-5), 100 (pos 5-15), 100 (pos 15-20), then
100/200/200/200/200 (pos 20-25).

`closest_position(target_elo)` rounds to the nearest available rating;
ties go to the lower rating (more forgiving opponent).

```python
from chesscom_driver import closest_position, POSITION_TO_RATING, available_ratings

closest_position(420)       # -> (3, 400)  — closer to 400 than 550
closest_position(2_700)     # -> (23, 2800)
available_ratings()         # -> [250, 400, 550, ..., 3000, 3200]
POSITION_TO_RATING[7]       # -> 1100
```

---

## Configuration reference

### `ChessComDriver`

```python
ChessComDriver(
    user_data_dir: str | Path,            # required
    headless: bool = False,                # True is risky (Cloudflare)
    chrome_channel: str = "chrome",        # or "chromium", "chrome-beta"
    poll_interval: float = 0.25,           # seconds between state polls
    bot_move_timeout: float = 60.0,        # raise if bot doesn't move
    slider_settle_delay: float = 0.45,     # wait after slider change
)
```

### `ChessComPlayer`

```python
ChessComPlayer(
    target_elo: int,                       # 250-3200
    *,
    user_data_dir: str | Path,
    headless: bool = False,
    chrome_channel: str = "chrome",
    bot_move_timeout: float = 60.0,
)
```

After the first move, `player.actual_rating` is set to the rating
actually chosen (closest available).

---

## Error handling

The driver raises typed exceptions, all subclasses of
`ChessComDriverError`:

| Exception | Means |
|---|---|
| `ChessComSetupError` | Browser couldn't reach a playable state (login, Cloudflare, DOM changed). |
| `ChessComIllegalMove` | chess.com refused a move we submitted. Move didn't register within 5 s. |
| `ChessComMoveTimeout` | Bot didn't move within `bot_move_timeout`. |
| `ChessComGameError` | Other in-game inconsistency (e.g. game ended unexpectedly). |

A typical retry pattern:

```python
from chesscom_driver import ChessComMoveTimeout

try:
    bot_move = await driver.wait_for_bot_move(timeout=30.0)
except ChessComMoveTimeout:
    # Bot is taking too long — could be a thinking spike at high ELO.
    bot_move = await driver.wait_for_bot_move(timeout=60.0)
```

---

## Troubleshooting

**"wc-chess-board not ready" on launch.** Cloudflare or the login wall
is in the way. Run interactively with `headless=False` and resolve in
the browser. After that, the cookie is in your profile and runs go
through.

**Slider shows the wrong rating after `start_game`.** The page might
still be settling. Bump `slider_settle_delay` to 0.7 or 1.0. Check
warnings in the log: the driver compares the rating shown on the page
against the expected rating from the mapping and warns on mismatch.

**Bot never replies.** Most likely the move click missed the board.
Check `state = await driver.get_state()` and look at `lastMove` and
`historySANs`. If the move never registered, the source square pixel
calculation may be off (e.g. zoom level isn't 100%, viewport is
different).

**`ChessComIllegalMove` on a move you believe is legal.** Almost always
a click-coordinate issue. Take a screenshot via Playwright before
submitting and compare to where the driver thought the squares were.

**"Could not find the Engine bot group".** chess.com may have changed
the `data-cy="bot-group-Engine"` selector. See [Maintenance
notes](#maintenance-notes-when-chesscom-breaks-the-dom).

**Playwright complains the user-data-dir is in use.** Another Chrome
instance is already on that profile. Close it, or pick a different
directory.

---

## Limitations and known gaps

- **Time control assumed "No Timer".** The driver doesn't currently
  enforce this; if chess.com starts you on a timed game it will play
  one. The /play/computer Engine group defaults to "No Timer", so this
  hasn't bitten in practice.
- **Side selector not enforced.** The driver assumes you play white. If
  the page remembers a previous black-side game, you'll start as black
  and everything will be off by one. A defensive reset to white before
  clicking Play is a planned improvement.
- **Resignation / new-game flow not exercised.** `get_result()` returns
  `None` while the game is in progress and `"1-0"`/`"0-1"`/`"1/2-1/2"`
  once chess.com decides the game is over. There's no `resign()` method.
- **Underpromotion not supported.** `autoPromote: true` always queens.
  This is fine for the experiment but a real limitation for general use.
- **No CAPTCHA bypass.** If you trigger one, solve it manually.

---

## Why white-only

The host experiment fixes the agent at white across both phases of the
trajectory experiment, because white-advantage cancels across
configurations when they all play the same colour against a shared
opponent pool. What's preserved is the relative ranking across
configs. Coding the driver to play either side would have added
complexity (board flipping, side selector clicks) for an outcome the
experiment doesn't measure.

The `flipped` code path in `_js.py:SUBMIT_MOVE` is implemented but not
exercised; if you ever need to play black, that branch is what you
flip on.

---

## Layout

```
chesscom-driver/
├── README.md
├── pyproject.toml
├── chesscom_driver/
│   ├── __init__.py         # re-exports the public API
│   ├── driver.py           # ChessComDriver: browser control
│   ├── player.py           # ChessComPlayer: Player ABC adapter
│   ├── mapping.py          # 25-position ELO table + closest_position()
│   ├── exceptions.py       # typed errors
│   └── _js.py              # JS snippets evaluated in the page
└── examples/
    └── basic_usage.py      # standalone demo
```

The package has zero runtime dependency on the host chess experiment —
it imports `chess` (python-chess) and `playwright` only. The host
experiment depends on this package, not the other way around.

---

## Maintenance notes (when chess.com breaks the DOM)

The driver is glued to chess.com's frontend. The four hooks it relies on:

| What | Selector / JS | What changes mean |
|---|---|---|
| Board element | `wc-chess-board.board` | Total DOM redesign — likely catastrophic. |
| Game API | `board.game.*` | API rename — update `_js.py`. |
| Engine group | `[data-cy="bot-group-Engine"]` | Selector change — search for "Engine" string in DOM. |
| Slider | `input.slider-input` (with min=1, max=25) | If max changes, re-derive `POSITION_TO_RATING`. |
| Selected bot rating | `.selected-bot-introduction-rating` | Used to sanity-check the slider; non-fatal if it breaks. |

To re-derive the slider mapping after a chess.com change:

```python
# Run interactively against the page, step the slider through all positions,
# read .selected-bot-introduction-rating after each (with ~500ms settle).
import json
mapping = {}
for pos in range(1, 26):
    await driver._set_slider_position(pos)
    await asyncio.sleep(0.5)
    shown = await driver._page.evaluate(_js.GET_SELECTED_RATING)
    mapping[pos] = int(re.search(r'\d+', shown).group())
print(json.dumps(mapping, indent=2))
```

Paste the result into `mapping.py`.

If `board.game` is renamed: look for `document.querySelector('wc-chess-board')`
in chess.com's bundled JS, find the analogous accessor (chess.com uses
the same plumbing for live games, so the API rarely fully disappears),
and update `_js.py`. Everything else in the driver is just a thin
wrapper over those JS calls.
