"""Stage 1 — discover which board representation the model is most fluent in.

Two sterile prompt conditions (NO format suggestions, NO examples, NO shots —
anything we show biases the attractor we are trying to find):

  Condition A (unconstrained): "generate a chess position."
      No FEN. Reveals the model's NATIVE attractor with zero anchoring.
      Scored only for FORM (which representation), not correctness.

  Condition B (anchored): "generate this position: <FEN>".
      Ground truth exists, so we get (1) the preferred form when rendering a
      KNOWN position and (2) fidelity — does the produced board match the FEN?

Output: results/stage1_calls.jsonl   (complete audit trail, one row per call)
Classification of forms is done in analyze_stage1.py (separate, re-runnable).

Determinism: positions and prompts fixed; only model sampling varies. Each
(condition x position) cell is sampled N times. We deliberately spend MORE
samples on Condition A (highest variance; the 'what is it fluent in' insight
lives there).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from positions import load_positions          # noqa: E402
from model import Client, gemma_spec          # noqa: E402

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
OUT = RESULTS / "stage1_calls.jsonl"

# Sampling. Condition A is position-independent (no FEN), so we sample it many
# times against a single neutral prompt. Condition B is sampled per position.
N_A = 40              # unconstrained samples (high — native-attractor variance)
N_B_PER_POS = 4       # anchored samples per position
TEMPERATURE = 0.8     # we WANT variety here to surface the attractor distribution
# Condition A only needs the FORM (appears early); B must render a full board,
# so it needs room for a ~25-line boxed grid plus the FEN echo.
MAX_TOKENS_A = 400
MAX_TOKENS_B = 700

PROMPT_A = "Generate a chess position."
def prompt_b(fen: str) -> str:
    return f"Generate this position: {fen}"


def main():
    spec = gemma_spec()
    client = Client(spec)
    positions = load_positions()

    rows = []
    run_meta = {
        "stage": 1, "model": spec.id, "model_name": spec.model_name,
        "base_url": spec.base_url, "temperature": TEMPERATURE,
        "max_tokens_a": MAX_TOKENS_A, "max_tokens_b": MAX_TOKENS_B,
        "n_a": N_A, "n_b_per_pos": N_B_PER_POS,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "prompt_a": PROMPT_A, "prompt_b_template": "Generate this position: <FEN>",
    }

    # Condition A
    print(f"Condition A (unconstrained): {N_A} samples ...", flush=True)
    for i in range(N_A):
        res = client.chat(PROMPT_A, temperature=TEMPERATURE, max_tokens=MAX_TOKENS_A)
        rows.append({
            "condition": "A", "sample": i, "position_id": None, "fen": None,
            "prompt": PROMPT_A, "text": res.text, "ok": res.ok,
            "error": res.error, "latency_s": res.latency_s,
            "finish_reason": res.finish_reason,
        })
        if (i + 1) % 10 == 0:
            print(f"  A {i+1}/{N_A}", flush=True)

    # Condition B
    print(f"Condition B (anchored): {len(positions)} positions x {N_B_PER_POS} ...", flush=True)
    for pos in positions:
        for i in range(N_B_PER_POS):
            p = prompt_b(pos.fen)
            res = client.chat(p, temperature=TEMPERATURE, max_tokens=MAX_TOKENS_B)
            rows.append({
                "condition": "B", "sample": i, "position_id": pos.id, "fen": pos.fen,
                "phase": pos.phase, "prompt": p, "text": res.text, "ok": res.ok,
                "error": res.error, "latency_s": res.latency_s,
                "finish_reason": res.finish_reason,
            })
        print(f"  B {pos.id} done", flush=True)

    run_meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_meta["n_calls"] = len(rows)

    with OUT.open("w") as f:
        f.write(json.dumps({"_meta": run_meta}) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(rows)} calls -> {OUT}")
    n_ok = sum(1 for r in rows if r["ok"])
    print(f"  ok: {n_ok}/{len(rows)}")


if __name__ == "__main__":
    main()
