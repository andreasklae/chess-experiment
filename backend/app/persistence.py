import json
import os
from pathlib import Path


def ensure_dir(games_dir: Path) -> None:
    games_dir.mkdir(parents=True, exist_ok=True)


def _game_path(games_dir: Path, game_id: str) -> Path:
    return games_dir / f"{game_id}.json"


def save_game(
    games_dir: Path,
    game_id: str,
    white: dict,
    black: dict,
    uci_moves: list[str],
    san_moves: list[str],
    status: str,
    result: str | None,
    created_at: str,
    agent_elo_before: str | None = None,
    agent_elo_after: str | None = None,
) -> None:
    """Write the per-game JSON. Optional ``agent_elo_before`` and
    ``agent_elo_after`` capture the agent's ELO snapshot for this game (only
    meaningful when one of the players is an agent). They live as a separate
    top-level ``agent_elo`` dict because PlayerConfig schema deliberately
    rejects an ``elo`` field on agent players — putting them inside ``white``
    or ``black`` would re-introduce that ambiguity."""
    data: dict = {
        "game_id": game_id,
        "white": white,
        "black": black,
        "uci_moves": uci_moves,
        "san_moves": san_moves,
        "status": status,
        "result": result,
        "created_at": created_at,
    }
    if agent_elo_before or agent_elo_after:
        data["agent_elo"] = {
            "before": agent_elo_before or None,
            "after": agent_elo_after or None,
        }
    path = _game_path(games_dir, game_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_game_file(games_dir: Path, game_id: str) -> dict:
    path = _game_path(games_dir, game_id)
    if not path.exists():
        raise FileNotFoundError(game_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_game_files(games_dir: Path) -> list[dict]:
    results = []
    for p in games_dir.glob("*.json"):
        try:
            results.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    results.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return results


def delete_game_file(games_dir: Path, game_id: str) -> None:
    path = _game_path(games_dir, game_id)
    if not path.exists():
        raise FileNotFoundError(game_id)
    path.unlink()


def most_recent_game_id(games_dir: Path) -> str | None:
    files = list_game_files(games_dir)
    return files[0]["game_id"] if files else None
