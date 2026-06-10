from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


MAIA_ELOS = (1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900)
# chess.com Engine bot ratings selectable in this experiment. The chess.com
# slider physically supports 25 positions (250–3200); we exclude the three
# lowest (250, 400, 550) because games at those ratings converge on time-cap
# draws regardless of the agent's true skill (the bots play moves erratic
# enough that neither side reliably converts within the 150-half-move cap).
# See knowledge-base/decisions/2026-05-25-chesscom-pool-floor.md.
# The chesscom_driver package's mapping.py keeps the full 25-position table
# unchanged — only the experiment's selectable pool is trimmed.
CHESSCOM_ELOS = (
    700, 850, 1000, 1100, 1200, 1300, 1400, 1500, 1600,
    1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2800, 3000, 3200,
)


class PlayerConfig(BaseModel):
    type: Literal["human", "maia", "agent", "chesscom"]
    elo: Annotated[int | None, Field(default=None)] = None

    @model_validator(mode="after")
    def validate_player_options(self) -> "PlayerConfig":
        if self.type in ("human", "agent") and self.elo is not None:
            raise ValueError(f"{self.type.capitalize()} players do not accept an elo.")
        if self.type == "maia":
            if self.elo is None:
                raise ValueError("Maia players require an elo.")
            if self.elo not in MAIA_ELOS:
                raise ValueError(f"Maia elo must be one of: {', '.join(map(str, MAIA_ELOS))}.")
        if self.type == "chesscom":
            if self.elo is None:
                raise ValueError("chess.com players require an elo.")
            if self.elo not in CHESSCOM_ELOS:
                raise ValueError(
                    f"chess.com elo must be one of: {', '.join(map(str, CHESSCOM_ELOS))}."
                )
        return self


class CreateGameRequest(BaseModel):
    white: PlayerConfig
    black: PlayerConfig
    # Optional custom starting position ("puzzle mode"). Used to drop the
    # agent into specific positions (mating exercises, conversion endgames)
    # without playing a full game to reach them. Such games land in
    # experimental.csv like any non-main game; they are never ranked.
    initial_fen: Annotated[str | None, Field(default=None)] = None

    @model_validator(mode="after")
    def validate_sides(self) -> "CreateGameRequest":
        if self.white.type == "chesscom":
            raise ValueError("chess.com bots can only play as black.")
        if self.black.type == "agent":
            raise ValueError("Agent players can only play as white.")
        if self.initial_fen is not None:
            if self.white.type == "chesscom" or self.black.type == "chesscom":
                raise ValueError(
                    "chess.com games cannot start from a custom position — "
                    "the browser board always begins at the standard setup."
                )
            import chess
            try:
                board = chess.Board(self.initial_fen)
            except ValueError as exc:
                raise ValueError(f"Invalid initial_fen: {exc}") from exc
            if not board.is_valid():
                raise ValueError(
                    f"Invalid initial_fen: position fails validity check "
                    f"({board.status()!r})."
                )
            if board.is_game_over():
                raise ValueError("Invalid initial_fen: position is already game over.")
        return self


class MoveRequest(BaseModel):
    """Human-side move submission. Strict UCI shape — chessground drag/drop
    produces from-square + to-square (+ promotion piece), never SAN."""
    move: Annotated[str, Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")]


class AgentCommitRequest(BaseModel):
    """Agent-side commit-intent submission.

    The endpoint that consumes this (``POST /api/games/{id}/agent-commit``)
    validates the move against the live board but **does not push it** —
    pushing is the bot loop's exclusive job. The recorded commit is read
    back by ``AgentPlayer.get_move`` once the LLM stream ends, and the
    returned ``chess.Move`` is what the bot loop pushes.

    Accepts UCI (``e2e4``, ``e1g1``, ``e7e8q``) or SAN (``e4``, ``Nf3``,
    ``O-O``, ``e8=Q``, ``Nxc6+``). The validator at the service layer
    tries UCI first and falls back to SAN. Trailing ``+`` / ``#`` is
    tolerated."""
    move: Annotated[str, Field(min_length=2, max_length=12)]
    reasoning: Annotated[str, Field(min_length=1, max_length=4000)]


class PlayerTypeInfo(BaseModel):
    type: Literal["human", "maia", "agent", "chesscom"]
    elo_required: bool
    allowed_elos: list[int] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    lc0_path: str
    lc0_found: bool
    maia_weights_dir: str


class GameState(BaseModel):
    game_id: str
    fen: str
    turn: Literal["white", "black"]
    white: PlayerConfig
    black: PlayerConfig
    legal_moves: list[str]
    uci_moves: list[str]
    san_moves: list[str]
    status: Literal["active", "finished"]
    result: str | None
    termination: str | None = None
    # Stockfish evaluation from White's perspective. `eval_cp` is centipawns
    # (positive = White better). `eval_mate` is +N for White mating in N,
    # -N for Black mating in N. Exactly one is non-null when an eval is
    # available; both null means the eval is pending or unavailable.
    eval_cp: int | None = None
    eval_mate: int | None = None
    # Paused state — see GameService.set_paused. Pause is honoured between
    # turns: an in-flight bot turn finishes, then the loop stops.
    paused: bool = False
    # Forced-draw ply cap (Game.max_half_moves). Exposed so the chess skill's
    # radar can warn the agent when the budget to convert a win is running out.
    move_cap: int = 150


class GameSummary(BaseModel):
    game_id: str
    white: PlayerConfig
    black: PlayerConfig
    status: Literal["active", "finished"]
    result: str | None
    turn: Literal["white", "black"]
    move_count: int
    last_move_san: str | None
    created_at: str
