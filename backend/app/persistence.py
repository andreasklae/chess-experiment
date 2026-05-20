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
) -> None:
    data = {
        "game_id": game_id,
        "white": white,
        "black": black,
        "uci_moves": uci_moves,
        "san_moves": san_moves,
        "status": status,
        "result": result,
        "created_at": created_at,
    }
    path = _game_path(games_dir, game_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
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
