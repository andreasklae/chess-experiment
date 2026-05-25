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

    @model_validator(mode="after")
    def validate_sides(self) -> "CreateGameRequest":
        if self.white.type == "chesscom":
            raise ValueError("chess.com bots can only play as black.")
        if self.black.type == "agent":
            raise ValueError("Agent players can only play as white.")
        return self


class MoveRequest(BaseModel):
    move: Annotated[str, Field(min_length=4, max_length=5, pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")]


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
