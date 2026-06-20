import chess
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.game_service import GameService
from app.main import app, get_game_service
from app.players import MaiaEngineRunner, PlayerFactory
from app.schemas import CreateGameRequest, GameState, PlayerConfig


class FakeMaiaRunner(MaiaEngineRunner):
    def __init__(self) -> None:
        super().__init__(Settings())

    def validate_available(self, elo: int) -> None:
        return None

    def play(self, board: chess.Board, elo: int) -> chess.Move:
        return next(iter(board.legal_moves))


def build_test_service(tmp_path) -> GameService:
    return GameService(PlayerFactory(Settings(), maia_runner=FakeMaiaRunner()), games_dir=tmp_path)


def client(tmp_path) -> TestClient:
    service = build_test_service(tmp_path)
    app.dependency_overrides[get_game_service] = lambda: service
    return TestClient(app)


def test_player_config_validation_accepts_human_without_elo() -> None:
    config = PlayerConfig(type="human")

    assert config.type == "human"
    assert config.elo is None


def test_player_config_validation_rejects_human_with_elo() -> None:
    try:
        PlayerConfig(type="human", elo=1500)
    except ValueError as exc:
        assert "Human players do not accept an elo" in str(exc)
    else:
        raise AssertionError("Expected validation error")


def test_player_config_validation_requires_maia_elo() -> None:
    try:
        PlayerConfig(type="maia")
    except ValueError as exc:
        assert "Maia players require an elo" in str(exc)
    else:
        raise AssertionError("Expected validation error")


def test_player_config_validation_rejects_unsupported_maia_elo() -> None:
    try:
        PlayerConfig(type="maia", elo=1000)
    except ValueError as exc:
        assert "Maia elo must be one of" in str(exc)
    else:
        raise AssertionError("Expected validation error")


def test_player_types(tmp_path) -> None:
    with client(tmp_path) as test_client:
        response = test_client.get("/api/player-types")

    assert response.status_code == 200
    types = {entry["type"]: entry for entry in response.json()}
    assert set(types) == {"human", "maia", "agent", "chesscom"}
    assert types["human"] == {"type": "human", "elo_required": False, "allowed_elos": []}
    assert types["maia"] == {
        "type": "maia",
        "elo_required": True,
        "allowed_elos": [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
    }
    assert types["agent"]["elo_required"] is False
    assert types["chesscom"]["elo_required"] is True
    assert len(types["chesscom"]["allowed_elos"]) > 0


def test_create_human_vs_human_game(tmp_path) -> None:
    with client(tmp_path) as test_client:
        response = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})

    assert response.status_code == 200
    body = response.json()
    assert body["turn"] == "white"
    assert body["status"] == "active"
    assert body["white"] == {"type": "human", "elo": None}
    assert body["black"] == {"type": "human", "elo": None}
    assert "e2e4" in body["legal_moves"]


def test_get_current_game_returns_backend_owned_game(tmp_path) -> None:
    with client(tmp_path) as test_client:
        created = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        response = test_client.get("/api/game")

    assert response.status_code == 200
    assert response.json()["game_id"] == created["game_id"]


def test_get_current_game_returns_404_before_creation(tmp_path) -> None:
    with client(tmp_path) as test_client:
        response = test_client.get("/api/game")

    assert response.status_code == 404
    assert response.json()["detail"] == "No game has been created."


def test_creating_new_game_while_one_active_is_rejected(tmp_path) -> None:
    # One game at a time: a second create while the first is still in progress
    # is refused (409), so a new game can't tear a running one down mid-move
    # (which starved the shared eX3 server and aborted both, 2026-06-16).
    with client(tmp_path) as test_client:
        first = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})
        assert first.status_code == 200
        second = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})
        assert second.status_code == 409
        # The original game is untouched and still current.
        current = test_client.get("/api/game").json()
        assert current["game_id"] == first.json()["game_id"]


def test_cancelling_active_game_allows_a_new_one(tmp_path) -> None:
    # After deleting the active game, a new game is allowed.
    with client(tmp_path) as test_client:
        first = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        test_client.delete(f"/api/games/{first['game_id']}")
        second = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})
        assert second.status_code == 200
        assert second.json()["game_id"] != first["game_id"]


def test_create_human_vs_maia_game_with_mocked_engine(tmp_path) -> None:
    with client(tmp_path) as test_client:
        response = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "maia", "elo": 1500}})

    assert response.status_code == 200
    assert response.json()["black"] == {"type": "maia", "elo": 1500}


def test_legal_human_move_updates_board(tmp_path) -> None:
    with client(tmp_path) as test_client:
        created = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        response = test_client.post("/api/game/moves", json={"move": "e2e4"})

    assert response.status_code == 200
    body = response.json()
    assert body["game_id"] == created["game_id"]
    assert body["turn"] == "black"
    assert body["uci_moves"] == ["e2e4"]
    assert body["san_moves"] == ["e4"]


def test_illegal_human_move_is_rejected(tmp_path) -> None:
    with client(tmp_path) as test_client:
        created = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        response = test_client.post(f"/api/games/{created['game_id']}/moves", json={"move": "e2e5"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Illegal move: e2e5"


def test_finished_game_rejects_more_moves(tmp_path) -> None:
    with client(tmp_path) as test_client:
        created = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        game_id = created["game_id"]
        for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            response = test_client.post(f"/api/games/{game_id}/moves", json={"move": move})
            assert response.status_code == 200
        response = test_client.post(f"/api/games/{game_id}/moves", json={"move": "e2e4"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Game is already finished."


async def test_sse_subscription_emits_initial_state(tmp_path) -> None:
    service = build_test_service(tmp_path)
    created = await service.create_game(CreateGameRequest(white=PlayerConfig(type="human"), black=PlayerConfig(type="human")))
    queue = await service.subscribe(created.game_id)

    payload = await queue.get()

    assert payload.startswith("event: state\ndata: ")
    state = GameState.model_validate_json(payload.split("data: ", 1)[1].strip())
    assert state.game_id == created.game_id


def test_list_games_returns_all_persisted_games(tmp_path) -> None:
    # One game at a time: the first must FINISH before the second can start
    # (a back-rank mate-in-1 finishes game 1), then both persist to disk.
    mate_fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
    with client(tmp_path) as test_client:
        g1 = test_client.post("/api/games", json={
            "white": {"type": "human"}, "black": {"type": "human"},
            "initial_fen": mate_fen}).json()
        test_client.post(f"/api/games/{g1['game_id']}/moves", json={"move": "a1a8"})
        second = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})
        assert second.status_code == 200
        response = test_client.get("/api/games")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_game_removes_it_from_list(tmp_path) -> None:
    with client(tmp_path) as test_client:
        game = test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}}).json()
        delete_response = test_client.delete(f"/api/games/{game['game_id']}")
        list_response = test_client.get("/api/games")

    assert delete_response.status_code == 204
    assert len(list_response.json()) == 0


def test_load_game_makes_it_current(tmp_path) -> None:
    # Finish the first game (back-rank mate) so the second can start; then
    # loading the first makes it current again.
    mate_fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
    with client(tmp_path) as test_client:
        first = test_client.post("/api/games", json={
            "white": {"type": "human"}, "black": {"type": "human"},
            "initial_fen": mate_fen}).json()
        test_client.post(f"/api/games/{first['game_id']}/moves", json={"move": "a1a8"})
        test_client.post("/api/games", json={"white": {"type": "human"}, "black": {"type": "human"}})
        load_response = test_client.post(f"/api/games/{first['game_id']}/load")
        current = test_client.get("/api/game").json()

    assert load_response.status_code == 200
    assert current["game_id"] == first["game_id"]


# ── Puzzle mode (initial_fen) ─────────────────────────────────────────────


def test_create_game_from_custom_fen(tmp_path) -> None:
    """Puzzle mode: a game can start from any legal position; moves are
    validated against it; the FEN round-trips through persistence/load."""
    fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"  # back-rank mate in 1
    with client(tmp_path) as test_client:
        created = test_client.post("/api/games", json={
            "white": {"type": "human"},
            "black": {"type": "human"},
            "initial_fen": fen,
        })
        assert created.status_code == 200
        state = created.json()
        assert state["fen"] == fen
        game_id = state["game_id"]

        # e2e4 is not legal here; Ra8# is.
        bad = test_client.post(f"/api/games/{game_id}/moves", json={"move": "e2e4"})
        assert bad.status_code == 400
        good = test_client.post(f"/api/games/{game_id}/moves", json={"move": "a1a8"})
        assert good.status_code == 200
        assert good.json()["status"] == "finished"
        assert good.json()["result"] == "1-0"
        assert good.json()["san_moves"] == ["Ra8#"]

        # Reload from disk: board must replay from the custom FEN.
        loaded = test_client.post(f"/api/games/{game_id}/load")
        assert loaded.status_code == 200
        assert loaded.json()["result"] == "1-0"


def test_create_game_rejects_bad_fen(tmp_path) -> None:
    with client(tmp_path) as test_client:
        for fen in ["not a fen", "8/8/8/8/8/8/8/8 w - - 0 1",  # no kings
                    "4k3/8/8/8/8/8/8/4K3 b - - 0 1"[:-1] + "x"]:
            resp = test_client.post("/api/games", json={
                "white": {"type": "human"},
                "black": {"type": "human"},
                "initial_fen": fen,
            })
            assert resp.status_code == 422, fen


def test_create_game_rejects_finished_fen(tmp_path) -> None:
    mated = "R5k1/5ppp/8/8/8/8/8/6K1 b - - 0 1"  # black already mated
    with client(tmp_path) as test_client:
        resp = test_client.post("/api/games", json={
            "white": {"type": "human"},
            "black": {"type": "human"},
            "initial_fen": mated,
        })
        assert resp.status_code == 422
