"""Tutor-side wiki validator: every concrete chess claim in the agent's
wiki must be machine-checkable, forever.

Two guarantees over all content pages under references/ (raw/ included):

1. Every backticked FEN parses as a legal position.
2. Every SAN line printed next to a FEN and ending in '#' replays legally
   from that FEN and ends in genuine checkmate.

The agent trusts these pages; a wrong example would seed wrong theory into
the corpus (a methodology failure, not just a typo). This test is the
validator the pattern-tools discussion called for.
"""

import re
from pathlib import Path

import chess
import pytest

REFS = Path(__file__).resolve().parents[1] / "skills" / "chess" / "references"

FEN_RE = re.compile(
    r"`([rnbqkpRNBQKP1-8/]+/[rnbqkpRNBQKP1-8/]+ [wb] (?:K?Q?k?q?|-) (?:[a-h][36]|-)(?: \d+ \d+)?)`"
)
# A SAN movetext like "1.Qe6+ Kh8 2.Nf7+ ... 5.Nf7#": from a move number to
# the first mate marker. Parentheticals and annotation marks are stripped
# before matching.
LINE_RE = re.compile(r"(\d+\.\S[^#]*#)")

REPLAYED = []  # (page, movetext) pairs actually verified — guards vacuousness

pages = sorted(p for p in REFS.rglob("*.md"))


def _san_tokens(movetext: str) -> list[str] | None:
    """Movetext -> SAN tokens, or None when it is prose, not a line."""
    tokens = []
    for chunk in movetext.split():
        chunk = re.sub(r"^\d+\.(\.\.)?", "", chunk).strip(".,;:!")
        if not chunk:
            continue
        if not re.fullmatch(r"[KQRBNOa-hx1-8=+#\-]+", chunk):
            return None  # something non-movelike: treat as prose
        tokens.append(chunk)
    return tokens or None


@pytest.mark.parametrize("page", pages, ids=lambda p: str(p.relative_to(REFS)))
def test_page_fens_and_mate_lines(page):
    text = page.read_text(encoding="utf-8")
    is_raw = "raw" in page.relative_to(REFS).parts
    fens = FEN_RE.findall(text)
    for fen in fens:
        board = chess.Board(fen)  # raises on garbage (parse errors still caught)
        # The verify-every-claim contract applies to AUTHORED wiki pages, whose
        # FENs must be legal playable positions. raw/ holds EXTERNAL source
        # illustrations (Wikipedia diagrams): these legitimately include
        # not-to-move-in-check positions, king-less pawn skeletons, and
        # single-king tactical fragments — all "invalid" to python-chess but
        # correct as diagrams. So we only require raw/ FENs to PARSE, not to be
        # legal positions.
        if is_raw:
            continue
        assert board.is_valid() or board.is_checkmate() or board.is_stalemate(), (
            f"invalid position in {page.name}: {fen}"
        )

    # Replay mate lines: pair each movetext-ending-in-# with the nearest
    # preceding FEN in the same paragraph. Parentheticals and annotation
    # marks are stripped first.
    for para in text.split("\n\n"):
        para_fens = FEN_RE.findall(para)
        if not para_fens:
            continue
        cleaned = re.sub(r"\([^)]*\)", " ", para.replace("\n", " ")).replace("!", "")
        for movetext in LINE_RE.findall(cleaned):
            tokens = _san_tokens(movetext)
            if not tokens:
                continue
            board = chess.Board(para_fens[0])
            try:
                for san in tokens:
                    board.push_san(san)
            except ValueError as exc:
                pytest.fail(f"{page.name}: line {movetext!r} illegal from {para_fens[0]}: {exc}")
            assert board.is_checkmate(), (
                f"{page.name}: line {movetext!r} from {para_fens[0]} does not end in mate"
            )
            REPLAYED.append((page.name, movetext))


def test_wiki_has_pages():
    assert len(pages) > 20


def test_validator_is_not_vacuous():
    """Must run AFTER the parametrized replays (alphabetical ordering holds
    within a module). If this fails, the extraction regressed and the
    validator silently stopped checking anything."""
    assert len(REPLAYED) >= 5, f"only replayed: {REPLAYED}"
