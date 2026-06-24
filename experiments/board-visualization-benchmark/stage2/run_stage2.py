"""Stage 2 — score COMPREHENSION of each board representation.

For each (format x position x probe), render the board in that format, ask the
relational probe, and score the model's answer against the python-chess oracle.
The FORMAT is the only variable: identical positions, identical probes across
all formats (paired design — enables McNemar on the deciding head-to-head).

We sample each probe REPS times (the model is stochastic). Accuracy per format
is computed over all (probe x rep) trials. Low temperature: we measure reading
accuracy, not policy sampling.

Output: results/stage2_trials.jsonl  (one row per format x probe x rep — full
audit trail with the exact prompt, raw answer, normalized answer, correctness).

Candidate formats are fixed here (controls + Stage-1-confirmed candidates):
  fen, ascii_grid (the live tool's grid), unicode_grid, piece_list.
Stage 1 confirmed FEN + piece_list as native attractors and showed the model
renders an anchored boxed grid; ascii_grid/unicode_grid/piece_list cover the
drawn-board space, FEN is the control to beat.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from positions import load_positions          # noqa: E402
from probes import generate_probes, score     # noqa: E402
from renderers import RENDERERS               # noqa: E402
from model import Client, gemma_spec          # noqa: E402

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
OUT = RESULTS / "stage2_trials.jsonl"

FORMATS = ["fen", "ascii_grid", "unicode_grid", "piece_list"]
REPS = 3              # repeats per probe per format (stochasticity control)
TEMPERATURE = 0.0     # measure reading accuracy, not sampling
MAX_TOKENS = 30       # answers are a single token/word/integer

SYSTEM = (
    "You are a precise chess analyst. You are given a chess position in some "
    "representation, then asked one factual question about it. Answer with ONLY "
    "the single word or number requested — no explanation, no restating the "
    "question."
)

# How each format is introduced, so the model knows what it's reading.
FORMAT_PREAMBLE = {
    "fen": "Here is a chess position in FEN notation:",
    "ascii_grid": ("Here is a chess position as a board grid. Uppercase letters "
                   "are White pieces, lowercase are Black, '.' is an empty square. "
                   "Ranks 8 (top) to 1 (bottom), files a-h left to right:"),
    "unicode_grid": ("Here is a chess position as a board grid using chess symbols "
                     "(outline = White, filled = Black, '·' = empty). Ranks 8 (top) "
                     "to 1 (bottom), files a-h left to right:"),
    "piece_list": "Here is a chess position given as a list of pieces and their squares:",
}


def build_prompt(fmt: str, rendered: str, question: str) -> str:
    return f"{FORMAT_PREAMBLE[fmt]}\n\n{rendered}\n\nQuestion: {question}"


def main():
    spec = gemma_spec()
    client = Client(spec)
    positions = load_positions()

    # Precompute probes per position (deterministic; identical across formats).
    probes_by_pos = {p.id: generate_probes(p.id, p.board) for p in positions}
    total_probes = sum(len(v) for v in probes_by_pos.values())
    n_trials = total_probes * len(FORMATS) * REPS

    meta = {
        "stage": 2, "model": spec.id, "model_name": spec.model_name,
        "base_url": spec.base_url, "formats": FORMATS, "reps": REPS,
        "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
        "n_positions": len(positions), "n_probes": total_probes,
        "n_trials": n_trials, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "system": SYSTEM,
    }
    print(f"Stage 2: {len(FORMATS)} formats x {total_probes} probes x {REPS} reps "
          f"= {n_trials} trials", flush=True)

    rows = []
    done = 0
    with OUT.open("w") as f:
        f.write(json.dumps({"_meta": meta}) + "\n")
        for pos in positions:
            for probe in probes_by_pos[pos.id]:
                for fmt in FORMATS:
                    rendered = RENDERERS[fmt](pos.board)
                    prompt = build_prompt(fmt, rendered, probe.question)
                    for rep in range(REPS):
                        res = client.chat(prompt, temperature=TEMPERATURE,
                                          max_tokens=MAX_TOKENS, system=SYSTEM)
                        correct, norm = score(res.text, probe)
                        row = {
                            "position_id": pos.id, "phase": pos.phase,
                            "probe_id": probe.probe_id, "kind": probe.kind,
                            "format": fmt, "rep": rep,
                            "question": probe.question,
                            "expected": probe.answer, "answer_type": probe.answer_type,
                            "raw": res.text, "normalized": norm,
                            "correct": correct, "ok": res.ok, "error": res.error,
                            "latency_s": res.latency_s,
                        }
                        f.write(json.dumps(row) + "\n")
                        f.flush()
                        rows.append(row)
                        done += 1
            print(f"  {pos.id} done ({done}/{n_trials})", flush=True)

    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    n_ok = sum(1 for r in rows if r["ok"])
    print(f"\nWrote {len(rows)} trials -> {OUT}  (ok: {n_ok}/{len(rows)})")


if __name__ == "__main__":
    main()
