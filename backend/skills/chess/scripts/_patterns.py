"""Wiki-driven mating-pattern triggers.

Scans the agent's own wiki for pages carrying machine-readable
``template_*`` frontmatter keys, and reports which patterns' *geometric
preconditions* are present on the board. The fairness contract
(knowledge-base ADR 2026-06-11-pattern-triggers, building on the 2026-06-02
rulebook):

- **Hints fire on geometry-present, never on mate-verified.** The test: a
  hint must still fire on a position where the pattern is actually refuted.
  The matcher checks piece inventory and king geometry only — it runs no
  search and draws no conclusion. Recognising, verifying, and executing the
  mate stays the agent's job.
- **Every hint traces to a wiki page.** The pattern knowledge lives in
  ``references/`` (the agent-curated corpus, captured by skill_repo_sha);
  this module implements only a small vocabulary of knowledge-free
  geometric predicates. A pattern with no page produces no hint. New
  pattern = new page, never new code here.

Template vocabulary (all optional except pieces+zone):

    template_pieces: [rook, knight]        # my non-king material must include these
    template_king_zone: corner             # corner | edge | edge-file | back-rank | centre-back | any
    template_min_own_blockers: 2           # enemy-king escape squares occupied by ITS OWN pieces
    template_max_king_moves: 3             # enemy king legal-move count at most this
    template_exposed_king: true            # king off its back rank, or opponent thinned (<=3 non-pawn pieces)
    template_open_file_near_king: true     # a fully open file within one file of the enemy king
    template_rook_on_seventh: true         # one of my rooks already on the enemy's second rank

Not exposed as a tool (underscore prefix); the radar embeds the output.
"""

from __future__ import annotations

import re
from pathlib import Path

import chess

_REFERENCES = Path(__file__).resolve().parent.parent / "references"

_PIECE_TYPES = {
    "pawn": chess.PAWN, "knight": chess.KNIGHT, "bishop": chess.BISHOP,
    "rook": chess.ROOK, "queen": chess.QUEEN,
}

# Cap on hints per position — retrieval pollution is a real cost for a
# fresh-context reader. Most-specific templates (most conditions) win.
_MAX_HINTS = 3


def _parse_templates(references_dir: Path = _REFERENCES) -> list[dict]:
    """Collect template stubs from page frontmatter. Flat key=value lines
    only (no YAML dependency); pages without template_ keys are skipped."""
    templates = []
    for page in references_dir.rglob("*.md"):
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("---", 3)
        if end < 0:
            continue
        fm = text[3:end]
        keys: dict = {}
        for line in fm.splitlines():
            m = re.match(r"^(template_\w+):\s*(.+?)\s*$", line)
            if not m:
                continue
            key, raw = m.group(1), m.group(2)
            if raw.startswith("["):
                keys[key] = [x.strip() for x in raw.strip("[]").split(",") if x.strip()]
            elif raw.isdigit():
                keys[key] = int(raw)
            else:
                keys[key] = raw
        if "template_pieces" not in keys or "template_king_zone" not in keys:
            continue
        desc = re.search(r"^description:\s*(.+?)\s*$", fm, re.M)
        templates.append({
            "path": str(page.relative_to(references_dir)),
            "name": page.stem.replace("-", " "),
            "description": desc.group(1) if desc else "",
            "pieces": keys["template_pieces"],
            "king_zone": keys["template_king_zone"],
            "min_own_blockers": keys.get("template_min_own_blockers", 0),
            "max_king_moves": keys.get("template_max_king_moves"),
            "exposed_king": keys.get("template_exposed_king") == "true",
            "open_file_near_king": keys.get("template_open_file_near_king") == "true",
            "rook_on_seventh": keys.get("template_rook_on_seventh") == "true",
        })
    return templates


def _have_pieces(board: chess.Board, color: bool, wanted: list[str]) -> bool:
    """True when my material includes the wanted multiset (e.g. [rook, rook])."""
    counts: dict[int, int] = {}
    for name in wanted:
        pt = _PIECE_TYPES.get(name)
        if pt is None:
            return False
        counts[pt] = counts.get(pt, 0) + 1
    return all(len(board.pieces(pt, color)) >= n for pt, n in counts.items())


def _king_zone(board: chess.Board, opp: bool) -> set[str]:
    ksq = board.king(opp)
    f, r = chess.square_file(ksq), chess.square_rank(ksq)
    zones = {"any"}
    if f in (0, 7) or r in (0, 7):
        zones.add("edge")
    if f in (0, 7):
        zones.add("edge-file")
    if f in (0, 7) and r in (0, 7):
        zones.add("corner")
    if r == (7 if opp == chess.BLACK else 0):
        zones.add("back-rank")
        if 2 <= f <= 5:
            zones.add("centre-back")
    return zones


def _exposed_king(board: chess.Board, opp: bool, opp_pieces: int) -> bool:
    """King off its back rank, or the opponent thinned to <=3 non-pawn
    pieces — the mechanical proxy for 'this king can actually be reached'."""
    back = 7 if opp == chess.BLACK else 0
    return chess.square_rank(board.king(opp)) != back or opp_pieces <= 3


def _open_file_near_king(board: chess.Board, opp: bool) -> bool:
    """A fully open file (no pawns of either colour) within one file of the
    enemy king — the line an attack pattern needs."""
    kf = chess.square_file(board.king(opp))
    pawns = board.pieces(chess.PAWN, chess.WHITE) | board.pieces(chess.PAWN, chess.BLACK)
    for f in (kf - 1, kf, kf + 1):
        if 0 <= f <= 7 and all(chess.square(f, r) not in pawns for r in range(8)):
            return True
    return False


def _rook_on_seventh(board: chess.Board, own: bool) -> bool:
    """One of my rooks already on the opponent's second rank."""
    seventh = 6 if own == chess.WHITE else 1
    return any(chess.square_rank(sq) == seventh for sq in board.pieces(chess.ROOK, own))


def _own_blockers(board: chess.Board, opp: bool) -> int:
    """How many of the enemy king's adjacent squares hold its OWN pieces."""
    ksq = board.king(opp)
    return sum(
        1 for sq in chess.SQUARES
        if chess.square_distance(sq, ksq) == 1
        and (p := board.piece_at(sq)) is not None and p.color == opp
    )


def _king_moves(board: chess.Board, opp: bool) -> int:
    b = board.copy(stack=False)
    if b.turn != opp:
        b.push(chess.Move.null())
    ksq = b.king(opp)
    return sum(1 for m in b.legal_moves if m.from_square == ksq)


def match_patterns(board: chess.Board, references_dir: Path = _REFERENCES) -> list[str]:
    """Markdown hint lines for every wiki template whose geometry is present."""
    own = board.turn
    opp = not own

    # Exposure gate: an undisturbed opening king trivially satisfies
    # "back-rank + blockers" geometry, which is noise. Hints fire only once
    # the enemy king has left its home square (castled kings count — that is
    # where most of these patterns live) or the opponent is thinned out.
    home = chess.E8 if opp == chess.BLACK else chess.E1
    opp_pieces = sum(
        len(board.pieces(pt, opp))
        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    )
    if board.king(opp) == home and opp_pieces > 3:
        return []

    zones = _king_zone(board, opp)
    blockers = _own_blockers(board, opp)
    king_moves = _king_moves(board, opp)
    exposed = _exposed_king(board, opp, opp_pieces)
    open_file = _open_file_near_king(board, opp)
    pig = _rook_on_seventh(board, own)

    hits = []
    for t in _parse_templates(references_dir):
        if t["king_zone"] not in zones:
            continue
        if not _have_pieces(board, own, t["pieces"]):
            continue
        if blockers < t["min_own_blockers"]:
            continue
        if t["max_king_moves"] is not None and king_moves > t["max_king_moves"]:
            continue
        if t["exposed_king"] and not exposed:
            continue
        if t["open_file_near_king"] and not open_file:
            continue
        if t["rook_on_seventh"] and not pig:
            continue
        specificity = (
            len(t["pieces"]) + (t["king_zone"] != "any")
            + (t["min_own_blockers"] > 0) + (t["max_king_moves"] is not None)
            + t["exposed_king"] + t["open_file_near_king"] + t["rook_on_seventh"]
        )
        hits.append((specificity, t))

    hits.sort(key=lambda x: -x[0])
    lines = []
    for _, t in hits[:_MAX_HINTS]:
        pieces = "+".join(t["pieces"])
        lines.append(
            f"- Pattern trigger (from your wiki): with your {pieces} and the enemy "
            f"king placed like this, **{t['name']}** geometry is on the board — "
            f"read `{t['path']}`. Geometry hint only: the mate may not work; "
            f"verify with `chess__imagine_move`."
        )
    return lines
