"""Convert a Wikipedia chess article to Markdown with position diagrams INLINE
as FEN + ASCII grid, working directly from the WIKITEXT (regular, order-exact).

Two diagram forms in wikitext, both handled in document order:
  - {{Chess diagram}} templates  -> parsed to a python-chess board -> FEN + ASCII
    grid (the representation chess__show_position uses). Verified in python-chess.
  - [[File:Foo.png|...]] image links (composed position images / photos) -> the
    image is downloaded locally and referenced inline ![](images/Foo.png).

Wikipedia text is CC BY-SA; stored verbatim with diagrams reconstructed losslessly
from the same source. Images are Commons (CC/PD) — provenance kept in SOURCES.md.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import chess

HDR = {"User-Agent": "thesis-chess-wiki/1.0 (academic; andreasklaeboe@gmail.com)"}
API = "https://en.wikipedia.org/w/api.php"


def get_wikitext(title: str) -> str:
    p = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext",
                                "format": "json", "formatversion": "2"})
    raw = urllib.request.urlopen(urllib.request.Request(f"{API}?{p}", headers=HDR), timeout=30).read()
    return json.loads(raw)["parse"]["wikitext"]


def commons_url(filename: str) -> str | None:
    """Resolve a File: name to its actual upload URL via the API."""
    p = urllib.parse.urlencode({"action": "query", "titles": f"File:{filename}",
                                "prop": "imageinfo", "iiprop": "url", "format": "json",
                                "formatversion": "2"})
    try:
        raw = urllib.request.urlopen(urllib.request.Request(f"{API}?{p}", headers=HDR), timeout=25).read()
        pages = json.loads(raw)["query"]["pages"]
        return pages[0]["imageinfo"][0]["url"]
    except Exception:
        return None


def _code(c: str) -> str | None:
    c = (c or "").strip()
    if len(c) == 2 and c[0] in "pnbrqk" and c[1] in "ld":
        return c[0].upper() if c[1] == "l" else c[0]
    return None


def _ascii(board: chess.Board) -> str:
    rows = str(board).split("\n")
    out = [f"{8 - i}  {r}" for i, r in enumerate(rows)]
    out.append("   a b c d e f g h")
    return "\n".join(out)


def _diagram_block_to_md(block: str, n: int) -> str:
    lines = block.split("\n")
    board_rows, text_lines = [], []
    for ln in lines:
        cells = ln.split("|")
        # A board row: a leading '|' then >=8 cells each a piece-code or 0-2 blanks.
        # Do NOT require a piece on the row (empty ranks are valid board rows).
        valid_cells = [c for c in cells if re.fullmatch(r"\s*([pnbrqk][ld])?\s*", c)]
        is_board = (ln.lstrip().startswith("|") and ln.count("|") >= 8 and
                    len(valid_cells) >= 8)
        if is_board:
            board_rows.append(valid_cells[:8])
        else:
            text_lines.append(ln)
    # The template has exactly 8 board rows; if more lines qualified (rare), take
    # the first 8 contiguous-looking ones.
    if len(board_rows) < 8:
        return ""  # not a board diagram (layout-only template)
    board_rows = board_rows[:8]
    b = chess.Board(None)
    for ri, row in enumerate(board_rows):
        for fi, c in enumerate(row):
            s = _code(c)
            if s:
                try:
                    b.set_piece_at(chess.square(fi, 7 - ri), chess.Piece.from_symbol(s))
                except Exception:
                    pass
    cap = ""
    for ln in reversed(text_lines):
        t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", ln)
        t = re.sub(r"'''?|<[^>]+>|\{\{[^}]*\}\}", "", t).strip()
        if t and "|" not in t and not re.search(r"[pnbrqk][ld]", t) and len(t) > 3:
            cap = t
            break
    fen = b.board_fen()
    ok = b.king(chess.WHITE) is not None and b.king(chess.BLACK) is not None
    flag = "" if ok else "  (reconstructed; may be a partial/illustrative position)"
    capline = f"\n*{cap}*\n" if cap else "\n"
    return (f"\n**Diagram {n}** — FEN `{fen} w - - 0 1`{flag}{capline}\n"
            f"```\n{_ascii(b)}\n```\n")


def _strip_wikimarkup(text: str) -> str:
    """Lightweight wikitext -> markdown for prose between diagrams."""
    t = text
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)   # drop footnotes
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"\{\{[Ss]hort description\|[^}]*\}\}", "", t)
    t = re.sub(r"\{\{[Mm]ain\|([^}]*)\}\}", r"(Main article: \1)", t)
    t = re.sub(r"\{\{[^}]*\}\}", "", t)                      # other templates
    t = re.sub(r"'''''(.+?)'''''", r"***\1***", t)
    t = re.sub(r"'''(.+?)'''", r"**\1**", t)
    t = re.sub(r"''(.+?)''", r"*\1*", t)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", t)  # wikilinks -> text
    t = re.sub(r"^==+\s*(.+?)\s*==+\s*$", lambda m: "## " + m.group(1), t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def article_to_md(title: str, image_dir: Path, image_rel: str) -> tuple[str, int, int]:
    """Return (markdown, n_diagrams, n_images). Downloads File: images into
    image_dir; references them as <image_rel>/<file>."""
    wt = get_wikitext(title)
    image_dir.mkdir(parents=True, exist_ok=True)

    out = []
    diag_n = img_n = 0
    pos = 0
    # Tokenize on {{Chess diagram ...}} and [[File:...]] in document order.
    pattern = re.compile(r"(\{\{[Cc]hess diagram.*?\n\}\})|(\[\[File:[^\]]*\]\])", re.S)
    for m in pattern.finditer(wt):
        prose = wt[pos:m.start()]
        if prose.strip():
            out.append(_strip_wikimarkup(prose))
        if m.group(1):  # chess diagram template
            block = re.sub(r"^\{\{[Cc]hess diagram[^\n]*\n", "", m.group(1))
            block = re.sub(r"\n\}\}$", "", block)
            md = _diagram_block_to_md(block, diag_n + 1)
            if md:
                diag_n += 1
                out.append(md)
        else:  # File: image
            inner = m.group(2)[2:-2]
            fname = inner.split("|")[0].replace("File:", "").strip().replace(" ", "_")
            cap = ""
            parts = inner.split("|")[1:]
            for p in parts:
                p = p.strip()
                if p and p not in ("thumb", "right", "left", "center", "frameless", "border") \
                   and not re.match(r"\d+px", p) and "upright" not in p:
                    cap = _strip_wikimarkup(p)
            url = commons_url(fname)
            if url:
                ext = Path(fname).suffix or ".png"
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", fname)
                try:
                    data = urllib.request.urlopen(
                        urllib.request.Request("https:" + url if url.startswith("//") else url,
                                               headers=HDR), timeout=30).read()
                    (image_dir / safe).write_bytes(data)
                    img_n += 1
                    out.append(f"\n![{cap}]({image_rel}/{safe})\n" + (f"*{cap}*\n" if cap else ""))
                except Exception:
                    out.append(f"\n*(image: {fname} — download failed; "
                               f"https:{url} )*\n")
        pos = m.end()
    tail = wt[pos:]
    if tail.strip():
        out.append(_strip_wikimarkup(tail))
    md = re.sub(r"\n{3,}", "\n\n", "\n\n".join(out))
    return md, diag_n, img_n


if __name__ == "__main__":
    import sys
    title = sys.argv[1] if len(sys.argv) > 1 else "Skewer (chess)"
    d = Path("/tmp/test_images")
    md, n, im = article_to_md(title, d, "images")
    print(f"# {title}: {n} diagrams, {im} images\n")
    print(md[:2500])
