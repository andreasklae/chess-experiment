"""Stage 1 analysis — classify the FORM of each generated position, and for
Condition B check FIDELITY against the target FEN.

Re-runnable: reads results/stage1_calls.jsonl, writes results/stage1_summary.json
and prints a human-readable report. No model calls.

Form taxonomy (detected by regex/structural heuristics, most-specific first):
  fen            — a bare/inline FEN string present
  piece_list     — coordinate piece listing ("King: e1", "Ke1", "White: ... Black: ...")
  boxed_grid     — ASCII grid with +---+ cell borders
  letter_grid    — 8-row grid of letters/dots WITHOUT box borders
  unicode_grid   — grid containing unicode chess glyphs
  prose_only     — none of the above (narrative description with no usable layout)

A single response can contain MULTIPLE forms (the model often gives FEN + a
visual). We record the SET of forms present and also the "primary visual" (the
non-FEN rendering it leads with), since FEN is nearly always included.

Fidelity (Condition B only): extract the model's rendering, parse it back to a
piece placement, compare to the target FEN's placement (piece+square set,
ignoring side-to-move/castling/clocks). Scored per extractable form.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CALLS = RESULTS / "stage1_calls.jsonl"

FEN_RE = re.compile(r"\b([rnbqkpRNBQKP1-8]+(?:/[rnbqkpRNBQKP1-8]+){7})\b")
UNICODE_GLYPHS = set("♔♕♖♗♘♙♚♛♜♝♞♟")
BOX_RE = re.compile(r"\+\s*-{2,}\s*\+")


def load_calls():
    meta = None
    rows = []
    for line in CALLS.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "_meta" in obj:
            meta = obj["_meta"]
        else:
            rows.append(obj)
    return meta, rows


def detect_forms(text: str) -> set[str]:
    forms = set()
    if FEN_RE.search(text):
        forms.add("fen")
    if any(g in text for g in UNICODE_GLYPHS):
        forms.add("unicode_grid")
    if BOX_RE.search(text):
        forms.add("boxed_grid")
    # piece-list: coordinate references like "King: e1", "Ke1", or "White:" headers
    if re.search(r"\b[KQRBN]?[a-h][1-8]\b", text) and (
        re.search(r"(King|Queen|Rook|Bishop|Knight|Pawn)s?\s*[:(]", text)
        or re.search(r"\b(White|Black)\s*:", text)
        or len(re.findall(r"\b[KQRBN][a-h][1-8]\b", text)) >= 4
    ):
        forms.add("piece_list")
    # letter-grid without boxes: >=6 lines that look like 8 cells of letters/dots
    grid_lines = 0
    for ln in text.splitlines():
        cells = re.findall(r"[rnbqkpRNBQKP.·_]", ln)
        if len(cells) >= 6 and "+" not in ln and not UNICODE_GLYPHS & set(ln):
            grid_lines += 1
    if grid_lines >= 6 and "boxed_grid" not in forms:
        forms.add("letter_grid")
    if not forms:
        forms.add("prose_only")
    return forms


def primary_visual(forms: set[str]) -> str:
    """The non-FEN rendering the response relies on, in priority order."""
    for f in ("boxed_grid", "letter_grid", "unicode_grid", "piece_list"):
        if f in forms:
            return f
    if forms == {"fen"}:
        return "fen_only"
    return "prose_only"


# ---- fidelity for Condition B ----

def _placement_set(board: chess.Board) -> set[tuple[int, str]]:
    return {(sq, board.piece_at(sq).symbol()) for sq in chess.SQUARES if board.piece_at(sq)}


def extract_fen_placement(text: str) -> set[tuple[int, str]] | None:
    m = FEN_RE.search(text)
    if not m:
        return None
    try:
        b = chess.Board(m.group(1) + " w - - 0 1")
        return _placement_set(b)
    except Exception:
        return None


def fidelity_vs_target(text: str, target_fen: str) -> dict:
    """Compare the model's FEN echo (if any) to the target placement.
    We score FEN-echo fidelity: did it reproduce the placement it was given?
    (Grids are checked qualitatively in the report; FEN echo is the crisp metric.)"""
    target = _placement_set(chess.Board(target_fen))
    got = extract_fen_placement(text)
    if got is None:
        return {"fen_echo_present": False, "fen_exact": None}
    return {"fen_echo_present": True, "fen_exact": (got == target)}


def main():
    meta, rows = load_calls()
    a_rows = [r for r in rows if r["condition"] == "A" and r["ok"]]
    b_rows = [r for r in rows if r["condition"] == "B" and r["ok"]]

    # Condition A: form distribution
    a_form_sets = Counter()
    a_primary = Counter()
    a_form_any = Counter()
    for r in a_rows:
        forms = detect_forms(r["text"])
        a_form_sets[tuple(sorted(forms))] += 1
        a_primary[primary_visual(forms)] += 1
        for f in forms:
            a_form_any[f] += 1

    # Condition B: form distribution + FEN-echo fidelity
    b_primary = Counter()
    b_form_any = Counter()
    fen_echo_present = 0
    fen_exact = 0
    fen_echo_total = 0
    b_fidelity_by_phase = defaultdict(lambda: [0, 0])  # phase -> [exact, present]
    for r in b_rows:
        forms = detect_forms(r["text"])
        b_primary[primary_visual(forms)] += 1
        for f in forms:
            b_form_any[f] += 1
        fid = fidelity_vs_target(r["text"], r["fen"])
        if fid["fen_echo_present"]:
            fen_echo_present += 1
            fen_echo_total += 1
            if fid["fen_exact"]:
                fen_exact += 1
                b_fidelity_by_phase[r["phase"]][0] += 1
            b_fidelity_by_phase[r["phase"]][1] += 1

    summary = {
        "meta": meta,
        "condition_A": {
            "n_ok": len(a_rows),
            "primary_visual": dict(a_primary.most_common()),
            "form_present_any": dict(a_form_any.most_common()),
            "exact_form_sets": {", ".join(k): v for k, v in a_form_sets.most_common()},
        },
        "condition_B": {
            "n_ok": len(b_rows),
            "primary_visual": dict(b_primary.most_common()),
            "form_present_any": dict(b_form_any.most_common()),
            "fen_echo_present": fen_echo_present,
            "fen_echo_exact": fen_exact,
            "fen_echo_fidelity_rate": round(fen_exact / fen_echo_total, 3) if fen_echo_total else None,
            "fen_fidelity_by_phase": {
                ph: {"exact": v[0], "present": v[1],
                     "rate": round(v[0] / v[1], 3) if v[1] else None}
                for ph, v in b_fidelity_by_phase.items()
            },
        },
    }
    (RESULTS / "stage1_summary.json").write_text(json.dumps(summary, indent=2))

    # report
    print("=" * 70)
    print("STAGE 1 SUMMARY — what representation is the model fluent in?")
    print("=" * 70)
    print(f"\nCondition A (unconstrained, n={len(a_rows)} ok):")
    print("  Primary visual rendering it leads with:")
    for k, v in a_primary.most_common():
        print(f"    {k:14} {v:3}  ({100*v/len(a_rows):.0f}%)")
    print("  Any form present (responses often include FEN + a visual):")
    for k, v in a_form_any.most_common():
        print(f"    {k:14} {v:3}")
    print(f"\nCondition B (anchored, n={len(b_rows)} ok):")
    print("  Primary visual:")
    for k, v in b_primary.most_common():
        print(f"    {k:14} {v:3}  ({100*v/len(b_rows):.0f}%)")
    print(f"  FEN-echo fidelity: {fen_exact}/{fen_echo_total} exact "
          f"({summary['condition_B']['fen_echo_fidelity_rate']})")
    for ph, d in summary["condition_B"]["fen_fidelity_by_phase"].items():
        print(f"    {ph:11} {d['exact']}/{d['present']} ({d['rate']})")
    print(f"\nWrote {RESULTS / 'stage1_summary.json'}")


if __name__ == "__main__":
    main()
