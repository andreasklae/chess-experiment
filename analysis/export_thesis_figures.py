#!/usr/bin/env python3
"""Export print-quality PDF figures for the thesis chess chapter.

Reads analysis/data/*.csv (build with build_dataset.py first) and writes PDFs
into ../../thesis/figures/chess/. Design rules: single axis per panel (no
dual-axis), Okabe-Ito colourblind-safe phase colours in fixed order, thin
marks, serif text to match the LaTeX body.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "thesis" / "figures" / "chess"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 9.5,
    "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "figure.dpi": 150, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
    "grid.linewidth": 0.4,
})

PHASES = ["P1-minimal-tools", "P2-visualization", "P3-mating-blunders", "P4-autonomous-loop"]
PHASE_LABEL = {"P1-minimal-tools": "P1 minimal tools", "P2-visualization": "P2 visualization",
               "P3-mating-blunders": "P3 mating \\& blunders", "P4-autonomous-loop": "P4 autonomous loop"}
PHASE_LABEL_PLAIN = {k: v.replace("\\&", "&") for k, v in PHASE_LABEL.items()}
# Okabe-Ito, fixed order
PHASE_COLOR = {"P1-minimal-tools": "#999999", "P2-visualization": "#56B4E9",
               "P3-mating-blunders": "#E69F00", "P4-autonomous-loop": "#009E73"}
INK = "#1a1a1a"

df = pd.read_csv(HERE / "data" / "games.csv", parse_dates=["datetime"])
wiki = pd.read_csv(HERE / "data" / "wiki_growth.csv", parse_dates=["date"])
ranked = df[(df.kind == "ranked") & (~df.aborted)
            & df.result.isin(["1-0", "0-1", "1/2-1/2"])].sort_values("datetime").reset_index(drop=True)
ranked["game_no"] = range(1, len(ranked) + 1)
full = df[(~df.is_puzzle_mode) & (~df.aborted) & df.result.isin(["1-0", "0-1", "1/2-1/2"])]

# ── 1. Elo trajectory ────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.2, 3.2))
for ph in PHASES:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        ax.axvspan(sub.game_no.min() - 0.5, sub.game_no.max() + 0.5,
                   color=PHASE_COLOR[ph], alpha=0.18, lw=0,
                   label=PHASE_LABEL_PLAIN[ph])
ax.plot(ranked.game_no, ranked.elo_after.astype(float), lw=1.2, color=INK)
# phase-end annotations
for ph, val in [("P1-minimal-tools", 684.2), ("P2-visualization", 793.6),
                ("P3-mating-blunders", 968.4), ("P4-autonomous-loop", 1347.9)]:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        ax.annotate(f"{val:.0f}", (sub.game_no.max(), val), fontsize=7.5,
                    xytext=(2, -9), textcoords="offset points", color=INK)
ax.set_xlabel("ranked game")
ax.set_ylabel("agent Elo")
ax.legend(loc="upper left", frameon=False)
fig.tight_layout()
fig.savefig(OUT / "elo-trajectory.pdf")
plt.close(fig)

# ── 2. Fix loop: two stacked panels, shared x (no dual axis) ────────────────
loop = pd.DataFrame([
    ("pre-fix", 7.42, 16), ("iter. 1", 5.35, 7), ("iter. 2", 5.80, 6),
    ("iter. 3", 5.81, 6), ("iter. 4", 4.83, 6), ("iter. 5", 3.59, 5),
], columns=["batch", "blunder_rate", "overrides"])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(5.4, 3.4), sharex=True,
                             gridspec_kw=dict(height_ratios=[1, 1], hspace=0.15))
x = range(len(loop))
a1.bar(x, loop.blunder_rate, width=0.55, color="#0072B2")
a1.set_ylabel("blunder rate (%)")
a2.bar(x, loop.overrides, width=0.55, color="#0072B2")
a2.set_ylabel("blunder-overrides")
a2.set_xticks(list(x))
a2.set_xticklabels(loop.batch)
for a in (a1, a2):
    a.grid(axis="x", visible=False)
fig.align_ylabels()
fig.tight_layout()
fig.savefig(OUT / "fix-loop.pdf")
plt.close(fig)

# ── 3. Loss profile by phase ─────────────────────────────────────────────────
losses = full[(full.result == "0-1") & full.worst_winpct_drop.notna()]
fig, ax = plt.subplots(figsize=(5.2, 2.9))
data = [losses[losses.phase == ph].worst_winpct_drop for ph in PHASES]
bp = ax.boxplot(data, tick_labels=[f"P{i+1}" for i in range(4)], patch_artist=True,
                widths=0.5, medianprops=dict(color=INK))
for patch, ph in zip(bp["boxes"], PHASES):
    patch.set_facecolor(PHASE_COLOR[ph]); patch.set_alpha(0.55); patch.set_edgecolor(INK)
for i, d in enumerate(data, 1):
    ax.annotate(f"n={len(d)}", (i, 2), ha="center", fontsize=7, color="#555")
ax.set_ylabel("worst single-move win% lost")
ax.grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(OUT / "loss-profile.pdf")
plt.close(fig)

# ── 4. Wiki growth + Elo: stacked shared-time panels ────────────────────────
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.2, 3.6), sharex=True,
                             gridspec_kw=dict(hspace=0.15))
a1.plot(wiki.date, wiki.words / 1000, lw=1.4, color="#0072B2")
a1.set_ylabel("wiki size (k words)")
a2.plot(ranked.datetime, ranked.elo_after.astype(float), lw=1.2, color=INK)
a2.set_ylabel("ranked Elo")
for d, lbl in [("2026-05-26", "PR1"), ("2026-06-15", "PR2"), ("2026-06-20", "PR3"),
               ("2026-06-23", "PR4"), ("2026-07-03", "PR5")]:
    for a in (a1, a2):
        a.axvline(pd.Timestamp(d), color="#888", ls=":", lw=0.7)
    a1.annotate(lbl, (pd.Timestamp(d), a1.get_ylim()[1]), fontsize=7,
                ha="center", va="bottom", color="#555")
for a in (a1, a2):
    a.grid(axis="x", visible=False)
fig.align_ylabels()
fig.autofmt_xdate(rotation=0, ha="center")
fig.tight_layout()
fig.savefig(OUT / "wiki-growth-elo.pdf")
plt.close(fig)

print("wrote 4 PDFs ->", OUT)
