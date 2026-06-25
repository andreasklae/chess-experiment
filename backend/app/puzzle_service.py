"""Puzzle-solving benchmark: the agent solves Lichess puzzles, scored strictly.

A puzzle is run as a real GameService game so the agent uses its full normal
machinery — perception scripts (show_position/imagine_move), the make_move commit
path, and the per-move reasoning logging — exactly as in a live game. The
OPPONENT is a ``PuzzlePlayer`` that (a) replays the puzzle's scripted replies and
(b) checks each agent move against the expected solution move, ending the game
the instant the agent deviates (strict scoring).

Lichess convention: the puzzle's DB ``FEN`` is the position BEFORE the setup
move; ``moves[0]`` is the opponent's setup; then solver(agent)/opponent alternate.
We start the GameService game from the position AFTER the setup move (so the
agent is immediately to move) and feed the PuzzlePlayer the remaining replies.

Scoring:
  - The agent must play each expected solver move in order.
  - At a step whose expected move is checkmate, ANY mating move is accepted
    (Lichess's alternative-mate rule); otherwise the move must match exactly.
  - First wrong move => FAILED; we record solved_plies / total and the deviation.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import chess

from app.players import Player, PlayerError


class PuzzleFailed(PlayerError):
    """Raised by PuzzlePlayer when the agent deviated from the solution. Carries
    the scoring detail so the runner can record exactly where it went wrong."""
    def __init__(self, message: str, *, ply: int, expected: str, played: str | None):
        super().__init__(message)
        self.ply = ply
        self.expected = expected
        self.played = played


@dataclass
class PuzzleSpec:
    id: str
    fen: str                 # position BEFORE the setup move (Lichess convention)
    moves: list[str]         # full solution UCI; moves[0] = opponent setup
    rating: int = 0
    themes: list[str] = field(default_factory=list)
    topic: str = ""
    band: str = ""
    title: str = ""
    difficulty: str = ""
    lichess_url: str = ""

    @property
    def start_fen(self) -> str:
        """The position the agent actually faces (after the setup move)."""
        b = chess.Board(self.fen)
        b.push(chess.Move.from_uci(self.moves[0]))
        return b.fen()

    @property
    def agent_color(self) -> bool:
        return chess.Board(self.start_fen).turn

    @property
    def solver_line(self) -> list[chess.Move]:
        """Moves after the setup: index 0,2,4.. = agent; 1,3.. = opponent."""
        return [chess.Move.from_uci(u) for u in self.moves[1:]]

    @property
    def total_solver_plies(self) -> int:
        return len(self.solver_line[0::2])


class PuzzlePlayer(Player):
    """Scripted opponent that also scores the agent. Plays the puzzle's reply
    moves; before each reply, verifies the agent's just-played move matched the
    expected solver move (the board it receives already has the agent's move on
    it via the move stack). Deviation -> PuzzleFailed (ends the game).

    Tracks progress with an internal index because get_move receives a stackless
    board; we count solver/opponent plies as they are consumed.
    """

    is_human = False

    def __init__(self, spec: PuzzleSpec):
        self._spec = spec
        self._line = spec.solver_line
        self._idx = 0                  # next index into _line we expect to consume
        self.solved_plies = 0          # agent moves verified correct so far
        self.attempts: list[dict] = [] # per-agent-move record
        self.done = False
        self.solved = False
        # The position we expect the agent to be moving FROM this turn. Tracked
        # internally because the bot loop passes get_move a STACKLESS board copy,
        # so we can't read the agent's move from board.move_stack — we derive it
        # by diffing this `before` against the received post-move board.
        self._before = chess.Board(spec.start_fen)

    def _record_agent_move(self, board: chess.Board) -> bool:
        """Score the agent's just-played move (the one that produced `board`)
        against the expected solver move at self._idx, append the attempt, and
        advance internal state past it. Returns True if correct.

        Raises PuzzleFailed on a wrong move (terminal for the puzzle). Shared by
        get_move (mid-line) and finalize (the agent's move ended the game, so
        get_move is never called again to score it). Does NOT raise
        PuzzleComplete — the caller decides whether the line is complete."""
        if self._idx % 2 != 0:
            raise PlayerError(f"puzzle desync at idx {self._idx}")
        expected_solver = self._line[self._idx]
        before = self._before.copy()
        played = _derive_move(before, board)
        expected_san = before.san(expected_solver)
        correct, accepted = self._score(before, played, expected_solver)
        ply = self._idx // 2
        self.attempts.append({
            "ply": ply,
            "fen_before": before.fen(),
            "expected_uci": expected_solver.uci(),
            "expected_san": expected_san,
            "played_uci": played.uci() if played else None,
            "played_san": (before.san(played) if played and played in before.legal_moves else None),
            "correct": correct,
            "accepted_as": accepted,
        })
        if not correct:
            self.done = True
            raise PuzzleFailed(
                f"agent played {played.uci() if played else 'None'}, expected {expected_solver.uci()}",
                ply=ply, expected=expected_solver.uci(),
                played=played.uci() if played else None)
        self.solved_plies += 1
        # Advance our tracked position past the agent's (accepted) move. Use the
        # move the agent actually played (may differ from `expected_solver` on an
        # accepted alt-mate) so internal state matches the real board.
        self._before.push(played if played is not None else expected_solver)
        self._idx += 1  # consume the solver ply
        return True

    async def get_move(self, board: chess.Board, last_san: str | None = None) -> chess.Move:
        # The board passed here is the position AFTER the agent's move. Score
        # that move, then either play the scripted reply or finish the puzzle.
        self._record_agent_move(board)

        # Is there an opponent reply? If the agent's move ended the game, none.
        if self._before.is_game_over() or self._idx >= len(self._line):
            self.done = True
            self.solved = (self.solved_plies == self._spec.total_solver_plies)
            raise PuzzleComplete(self.solved)

        reply = self._line[self._idx]
        self._before.push(reply)   # advance past the opponent's scripted reply
        self._idx += 1
        return reply

    def finalize(self, board: chess.Board) -> bool:
        """Score the agent's FINAL move when it ended the game (checkmate,
        stalemate, etc.), so the bot loop never calls get_move again. `board` is
        the terminal position after the agent's move. Idempotent and safe to call
        even if the puzzle already finished mid-line. Returns self.solved.

        This closes the false-negative where a puzzle whose last solver move is
        mate was scored as failed because the scoring call (get_move) is skipped
        when the game is already over."""
        if self.done:
            return self.solved
        # Only score if it's the agent's turn to be scored (even idx) and there
        # is still an expected solver move pending.
        if self._idx % 2 == 0 and self._idx < len(self._line):
            try:
                self._record_agent_move(board)
            except PuzzleFailed:
                # A wrong terminal move: _record_agent_move already set done and
                # recorded the attempt. Mark unsolved and swallow (finalize never
                # raises — the game is already ending).
                self.done = True
                self.solved = False
                return False
        self.done = True
        self.solved = (self.solved_plies == self._spec.total_solver_plies)
        return self.solved

    def _score(self, before: chess.Board, played: chess.Move | None,
               expected: chess.Move) -> tuple[bool, str | None]:
        if played is None or played not in before.legal_moves:
            return False, None
        if played == expected:
            return True, "exact"
        # alternative mate: if the expected move is mate and the played move is
        # also mate, accept it (Lichess rule).
        if _is_mate(before, expected) and _is_mate(before, played):
            return True, "alt-mate"
        return False, None


class PuzzleComplete(PlayerError):
    """Raised when the agent has played the full (successful) solution line."""
    def __init__(self, solved: bool):
        super().__init__("puzzle complete")
        self.solved = solved


def _is_mate(board: chess.Board, move: chess.Move) -> bool:
    b = board.copy(); b.push(move); return b.is_checkmate()


def _derive_move(before: chess.Board, after: chess.Board) -> chess.Move | None:
    """The single legal move from `before` that produces `after`'s position.
    Used because the bot loop hands get_move a stackless board copy, so we
    can't read board.move_stack. Compares by board placement (piece map)."""
    target = after.board_fen()
    for mv in before.legal_moves:
        b = before.copy(); b.push(mv)
        if b.board_fen() == target:
            return mv
    return None


# ---- puzzle set loading ----

def load_puzzle_set(path: str | Path) -> list[PuzzleSpec]:
    data = json.loads(Path(path).read_text())
    return [PuzzleSpec(id=p["id"], fen=p["fen"], moves=p["moves"],
                       rating=p.get("rating", 0), themes=p.get("themes", []),
                       topic=p.get("topic", ""), band=p.get("band", ""),
                       title=p.get("title", ""), difficulty=p.get("difficulty", ""),
                       lichess_url=p.get("lichess_url", "")) for p in data]
