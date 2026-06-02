#!/usr/bin/env python3
"""Search the chess knowledge wiki (the skill's references/ tree) by keyword.

This is a DISCOVERY tool, not a content tool. It returns, for each matching
page, only its path and its YAML frontmatter (description, triggers, tags,
status, related_pages) — never the page body — plus the exact read_reference
call to open it. Read the frontmatter to decide which page is worth loading,
then read that one page with read_reference.

The contract is fixed in
knowledge-base/decisions/2026-06-02-chess-agent-wiki-architecture.md §6.

Exposed as the tool chess__search_wiki after use_skill('chess'). Call it with
a generic args list:

    chess__search_wiki(args=["isolated pawn"])
    chess__search_wiki(args=["back rank mate", "--limit", "5"])

Matching is a case-insensitive keyword scan over each page's frontmatter
(description, triggers, tags) and its path. All whitespace-separated terms in
the query are scored; pages matching more terms rank higher. Index pages
(index.md) and log.md are skipped — navigate those directly.

Output is markdown: one block per matched page, frontmatter plus a ready-to-run
read_reference call.
"""

import re
import sys
from pathlib import Path

# references/ is the sibling of scripts/ inside the skill directory.
_REFERENCES = Path(__file__).resolve().parent.parent / "references"

_SKIP_NAMES = {"index.md", "log.md"}


def _parse_frontmatter(text: str) -> tuple[dict[str, str], bool]:
    """Return (frontmatter dict, found). Only the raw --- ... --- block is read.

    Values are kept as raw strings (lists like ``[a, b]`` are not parsed into
    Python lists — the agent reads them as-is). No YAML dependency.
    """
    if not text.startswith("---"):
        return {}, False
    end = text.find("\n---", 3)
    if end == -1:
        return {}, False
    block = text[3:end].strip("\n")
    meta: dict[str, str] = {}
    for line in block.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, True


def _haystack(path: Path, meta: dict[str, str]) -> str:
    """The text a query is scored against: path + searchable frontmatter fields."""
    parts = [str(path.relative_to(_REFERENCES))]
    for field in ("description", "triggers", "tags"):
        if field in meta:
            parts.append(meta[field])
    return " ".join(parts).lower()


def _render(path: Path, meta: dict[str, str]) -> str:
    rel = path.relative_to(_REFERENCES)
    lines = [f"### {rel}"]
    for field in ("description", "status", "triggers", "tags", "related_pages"):
        if field in meta:
            lines.append(f"- **{field}:** {meta[field]}")
    lines.append(f'- **read with:** `read_reference(skill_name="chess", path="{rel}")`')
    return "\n".join(lines)


def main() -> None:
    args = [a for a in sys.argv[1:]]
    limit = 8
    if "--limit" in args:
        i = args.index("--limit")
        try:
            limit = int(args[i + 1])
            del args[i : i + 2]
        except (IndexError, ValueError):
            print("error: --limit needs an integer", file=sys.stderr)
            sys.exit(1)

    query = " ".join(args).strip()
    if not query:
        print("error: provide a search query, e.g. \"isolated pawn\"", file=sys.stderr)
        sys.exit(1)

    if not _REFERENCES.is_dir():
        print(f"error: no references/ directory at {_REFERENCES}", file=sys.stderr)
        sys.exit(1)

    terms = [t for t in re.split(r"\s+", query.lower()) if t]

    scored: list[tuple[int, Path, dict[str, str]]] = []
    for path in sorted(_REFERENCES.rglob("*.md")):
        if path.name in _SKIP_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, found = _parse_frontmatter(text)
        if not found:
            continue
        hay = _haystack(path, meta)
        score = sum(1 for t in terms if t in hay)
        if score:
            scored.append((score, path, meta))

    if not scored:
        print(f"_No wiki pages matched **{query}**._")
        print()
        print(
            'Navigate from the index instead — '
            '`read_reference(skill_name="chess", path="index.md")` — or broaden the query. '
            "Remember search only matches frontmatter (description, triggers, tags), not page bodies."
        )
        return

    # Higher score first; stable path order within a score.
    scored.sort(key=lambda r: (-r[0], str(r[1])))

    print(f"_{min(len(scored), limit)} match(es) for **{query}** (frontmatter only — use the read_reference call shown to read a page):_")
    print()
    for _score, path, meta in scored[:limit]:
        print(_render(path, meta))
        print()


if __name__ == "__main__":
    main()
