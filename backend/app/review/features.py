"""Bridge to the chess skill's mechanical detector stack (`_features.py`).

The review engine's distinctive value over a plain chess.com clone is the **mechanical
"why"**: instead of only "you lost 2.3 pawns", it attaches the same explicit, fair
facts the agent itself sees — the situation/priority, the active threats, what a
blunder allowed the opponent to do. That comes from the detector stack the rest of
this experiment already built. This module makes those functions importable from the
`app.review` package (the scripts dir is not on the normal import path) and exposes a
couple of compact extractors tuned for review output (plain data, not the agent-facing
prose blocks)."""

from __future__ import annotations

import sys
from pathlib import Path

import chess

_SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "chess" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    import _features as _F  # noqa: E402
    AVAILABLE = True
except Exception:  # pragma: no cover - skill stack must be present in this repo
    _F = None
    AVAILABLE = False


def situation(board: chess.Board) -> dict | None:
    """Compact situation/priority summary for the side to move (see
    `_features.assess_situation`). Returns the machine-readable fields only."""
    if not AVAILABLE:
        return None
    try:
        s = _F.assess_situation(board)
    except Exception:
        return None
    return {
        "priority": s.get("priority"),
        "material": s.get("material"),
        "material_diff_pawns": s.get("material_diff"),
        "phase": s.get("phase"),
        "in_check": s.get("in_check"),
        "threat_against_mover": (
            {"kind": s["threat"][0], "move": s["threat"][1]} if s.get("threat") else None
        ),
        "has_forcing_move": s.get("have_forcing"),
        "mate_savers": s.get("mate_savers") or [],
    }


def key_features(board: chess.Board, *, limit: int = 8) -> list[dict]:
    """The salient mechanical findings at this position, from the side-to-move's seat
    (strengths/weaknesses/threats/tactics). Compact dicts, ranked by salience."""
    if not AVAILABLE:
        return []
    try:
        findings = _F.detect_all(board)
    except Exception:
        return []
    # order: opponent threats & our losing/winning material first, then the rest
    order = {"lose": 0, "win": 1, "threat": 2, "weakness": 3, "strength": 4,
             "potential": 5, "fundamental": 6}
    findings = sorted(findings, key=lambda f: order.get(f.kind, 9))
    out = []
    for f in findings[:limit]:
        out.append({
            "kind": f.kind,
            "side": "mover" if f.side else "opponent",
            "text": f.text,
            "moves": list(getattr(f, "moves", []) or [])[:4],
            "wiki": getattr(f, "wiki", None),
        })
    return out


def opponent_reply_threats(board_after: chess.Board, *, limit: int = 5) -> list[dict]:
    """After a move, what the opponent can now do TO the mover — the concrete
    consequence of a blunder. Findings from the opponent's seat that are threats /
    winning-material against the mover."""
    if not AVAILABLE:
        return []
    try:
        findings = _F.detect_all(board_after)  # board_after: opponent to move
    except Exception:
        return []
    out = []
    for f in findings:
        # from the opponent-to-move seat, THEIR strengths/wins/threats are the danger
        if f.kind in ("win", "threat") and f.side:
            out.append({"kind": f.kind, "text": f.text,
                        "moves": list(getattr(f, "moves", []) or [])[:4]})
        if len(out) >= limit:
            break
    return out
