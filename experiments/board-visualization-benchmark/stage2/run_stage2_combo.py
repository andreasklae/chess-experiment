"""Stage 2b — the COMBINATION condition (fen_plus_grid).

Tests whether showing the FEN and the ASCII grid together lets the model
self-select the right view per question — capturing FEN's relational strength
AND the grid's counting strength — or whether the second view distracts.

This is a PURE perception test: both encodings are presented neutrally, with NO
hint about which to use for what (that 'telling it what to do' layer is held out
on purpose — it belongs to the tools, not to the representation question).

Reuses the EXACT same positions and probes as run_stage2.py, so the new trials
are directly comparable (paired) to the fen / ascii_grid baselines already in
results/stage2_trials.jsonl. Writes to a SEPARATE file so the baseline run is
untouched.

Output: results/stage2_combo_trials.jsonl
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
OUT = RESULTS / "stage2_combo_trials.jsonl"

FORMAT = "fen_plus_grid"
REPS = 3
TEMPERATURE = 0.0
MAX_TOKENS = 30

# Same system prompt as the baseline run (identical task framing).
SYSTEM = (
    "You are a precise chess analyst. You are given a chess position in some "
    "representation, then asked one factual question about it. Answer with ONLY "
    "the single word or number requested — no explanation, no restating the "
    "question."
)

# Neutral preamble: name both encodings, give NO routing guidance.
PREAMBLE = (
    "Here is a chess position given two ways: first in FEN notation, then as a "
    "board grid (uppercase = White, lowercase = Black, '.' = empty; ranks 8 top "
    "to 1 bottom, files a-h left to right). Both describe the same position."
)


def build_prompt(rendered: str, question: str) -> str:
    return f"{PREAMBLE}\n\n{rendered}\n\nQuestion: {question}"


def main():
    spec = gemma_spec()
    client = Client(spec)
    positions = load_positions()
    probes_by_pos = {p.id: generate_probes(p.id, p.board) for p in positions}
    total_probes = sum(len(v) for v in probes_by_pos.values())
    n_trials = total_probes * REPS

    meta = {
        "stage": "2b", "format": FORMAT, "model": spec.id,
        "model_name": spec.model_name, "base_url": spec.base_url,
        "reps": REPS, "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
        "n_probes": total_probes, "n_trials": n_trials,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "system": SYSTEM,
        "preamble": PREAMBLE,
    }
    print(f"Stage 2b: {FORMAT} x {total_probes} probes x {REPS} reps = {n_trials} trials",
          flush=True)

    rows = []
    done = 0
    with OUT.open("w") as f:
        f.write(json.dumps({"_meta": meta}) + "\n")
        for pos in positions:
            rendered = RENDERERS[FORMAT](pos.board)
            for probe in probes_by_pos[pos.id]:
                prompt = build_prompt(rendered, probe.question)
                for rep in range(REPS):
                    res = client.chat(prompt, temperature=TEMPERATURE,
                                      max_tokens=MAX_TOKENS, system=SYSTEM)
                    correct, norm = score(res.text, probe)
                    row = {
                        "position_id": pos.id, "phase": pos.phase,
                        "probe_id": probe.probe_id, "kind": probe.kind,
                        "format": FORMAT, "rep": rep, "question": probe.question,
                        "expected": probe.answer, "answer_type": probe.answer_type,
                        "raw": res.text, "normalized": norm, "correct": correct,
                        "ok": res.ok, "error": res.error, "latency_s": res.latency_s,
                    }
                    f.write(json.dumps(row) + "\n"); f.flush()
                    rows.append(row); done += 1
            print(f"  {pos.id} done ({done}/{n_trials})", flush=True)

    n_ok = sum(1 for r in rows if r["ok"])
    print(f"\nWrote {len(rows)} trials -> {OUT}  (ok: {n_ok}/{len(rows)})")


if __name__ == "__main__":
    main()
