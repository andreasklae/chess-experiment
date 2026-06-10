"""Per-game JSON state persistence.

Games are organised into per-PR subfolders under ``games_dir``. Writes
explicitly name the subfolder; reads scan recursively because callers
typically only know the ``game_id`` and not which folder it lives in.

Aggregate files (``ranked.csv``, ``experimental.csv``, ``agent_elo.json``)
stay at the top level of ``games_dir`` and are excluded from the scan.
"""

import json
import os
import re
from pathlib import Path

# Sequence-prefix pattern used by ``logging_service._write_agent_log``.
# Re-used here so the per-PR ``NNN_<game_id>.json`` filenames can still be
# looked up by bare game_id.
_SEQ_PREFIX_RE = re.compile(r"^\d{3}_")


def ensure_dir(games_dir: Path) -> None:
    games_dir.mkdir(parents=True, exist_ok=True)


def _game_path(games_dir: Path, game_id: str, subfolder: str = "") -> Path:
    """Return the on-disk path for ``<game_id>.json``.

    When ``subfolder`` is provided the path lives under
    ``games_dir/<subfolder>/<game_id>.json``. The directory is not created
    here — callers writing the file are responsible for ensuring it exists.
    """
    if subfolder:
        return games_dir / subfolder / f"{game_id}.json"
    return games_dir / f"{game_id}.json"


def _find_existing_game_path(games_dir: Path, game_id: str) -> Path | None:
    """Locate this game's state JSON anywhere under games_dir.

    Returns the first match. Used by readers / deleters that don't know
    which subfolder or sequence prefix the game lives under. Top-level bare
    matches are preferred over nested ones (legacy layout), followed by
    bare-UUID files in any subfolder, followed by sequence-prefixed files
    (``NNN_<game_id>.json``).
    """
    top = games_dir / f"{game_id}.json"
    if top.exists():
        return top
    # First pass: exact ``<game_id>.json`` match anywhere under the tree.
    for p in games_dir.rglob(f"{game_id}.json"):
        return p
    # Second pass: ``NNN_<game_id>.json`` for renamed files in per-PR folders.
    for p in games_dir.rglob(f"*_{game_id}.json"):
        if _SEQ_PREFIX_RE.match(p.name):
            return p
    return None


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
    subfolder: str = "",
    initial_fen: str | None = None,
) -> None:
    """Write the per-game JSON. Optional ``agent_elo_before`` and
    ``agent_elo_after`` capture the agent's ELO snapshot for this game (only
    meaningful when one of the players is an agent). They live as a separate
    top-level ``agent_elo`` dict because PlayerConfig schema deliberately
    rejects an ``elo`` field on agent players — putting them inside ``white``
    or ``black`` would re-introduce that ambiguity.

    ``subfolder`` selects the destination directory under ``games_dir``. When
    empty, writes go to the top level (legacy / migration behaviour).
    """
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
    # Custom starting position (puzzle mode). Omitted for standard games so
    # historical game files keep their exact shape.
    if initial_fen:
        data["initial_fen"] = initial_fen
    if agent_elo_before or agent_elo_after:
        data["agent_elo"] = {
            "before": agent_elo_before or None,
            "after": agent_elo_after or None,
        }
    path = _game_path(games_dir, game_id, subfolder)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_game_file(games_dir: Path, game_id: str) -> dict:
    path = _find_existing_game_path(games_dir, game_id)
    if path is None:
        raise FileNotFoundError(game_id)
    return json.loads(path.read_text(encoding="utf-8"))


def existing_subfolder(games_dir: Path, game_id: str) -> str:
    """Return the subfolder ``<game_id>.json`` lives in, or ``""`` if at top level.

    Used when restoring a game from disk so subsequent writes land back in
    the same folder rather than at the top level.
    """
    path = _find_existing_game_path(games_dir, game_id)
    if path is None:
        return ""
    try:
        rel = path.parent.relative_to(games_dir)
    except ValueError:
        return ""
    return "" if str(rel) == "." else str(rel)


# Files in games_dir that look like ``*.json`` but are not per-game state
# (and should be excluded from listings). The CSV header would never parse
# as JSON, but ``agent_elo.json`` and the ``*_agent.json`` event logs would.
_NON_GAME_JSON_NAMES = frozenset({"agent_elo.json"})


def _is_game_file(path: Path) -> bool:
    name = path.name
    if name in _NON_GAME_JSON_NAMES:
        return False
    if name.endswith("_agent.json"):
        return False
    return True


def list_game_files(games_dir: Path) -> list[dict]:
    """Return every per-game JSON anywhere under ``games_dir``.

    Scans recursively so games in per-PR subfolders are included. Agent
    event logs (``*_agent.json``) and aggregate state files
    (``agent_elo.json``) are excluded.
    """
    results = []
    if not games_dir.exists():
        return results
    for p in games_dir.rglob("*.json"):
        if not _is_game_file(p):
            continue
        try:
            results.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    results.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return results


def delete_game_file(games_dir: Path, game_id: str) -> None:
    path = _find_existing_game_path(games_dir, game_id)
    if path is None:
        raise FileNotFoundError(game_id)
    path.unlink()


def most_recent_game_id(games_dir: Path) -> str | None:
    files = list_game_files(games_dir)
    return files[0]["game_id"] if files else None
