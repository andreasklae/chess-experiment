from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]

SKILLFUL_AGENT_ENV = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    lc0_path: str = "lc0"
    maia_weights_dir: Path = BACKEND_DIR / "engines" / "maia" / "weights"
    games_dir: Path = BACKEND_DIR / "games"

    # chess.com driver settings — used only when a player of type "chesscom"
    # is created. The user-data directory persists the chess.com login.
    chesscom_user_data_dir: Path = BACKEND_DIR / "chesscom-profile"
    chesscom_headless: bool = False
    chesscom_chrome_channel: str = "chrome"

    model_config = SettingsConfigDict(env_prefix="CHESS_", extra="ignore")

    def maia_weight_path(self, elo: int) -> Path:
        return self.maia_weights_dir / f"maia-{elo}.pb.gz"


@lru_cache
def get_settings() -> Settings:
    return Settings()
