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

# ── 4. Wiki growth + Elo: one graph, Elo coloured by phase ──────────────────
# (Author's requested form: both lines on the same graph; the twin axis is a
# deliberate exception to the one-axis rule, with the wiki curve kept visually
# recessive so the Elo line reads as the primary series.)
import numpy as np
fig, ax = plt.subplots(figsize=(6.2, 3.2))
axw = ax.twinx()
# interpolate wiki size (words) at each ranked game's timestamp -> game axis
wdates = wiki.date.map(pd.Timestamp.timestamp).to_numpy()
gdates = ranked.datetime.dt.tz_localize(None).map(pd.Timestamp.timestamp).to_numpy()
wiki_at_game = np.interp(gdates, wdates, wiki.words.to_numpy(),
                         left=0.0) / 1000
WIKI_C = "#CC79A7"
axw.fill_between(ranked.game_no, wiki_at_game, color=WIKI_C, alpha=0.12, lw=0)
axw.plot(ranked.game_no, wiki_at_game, color=WIKI_C, lw=1.2, alpha=0.9,
         label="knowledge store")
axw.set_ylabel("knowledge-store size (k words)", color=WIKI_C)
axw.tick_params(axis="y", labelcolor=WIKI_C)
axw.grid(visible=False)
axw.spines["right"].set_visible(True)
for ph in PHASES:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        # extend each segment to the next phase's first game so the line is
        # continuous across phase boundaries
        nxt = ranked[ranked.game_no == sub.game_no.max() + 1]
        xs = list(sub.game_no) + list(nxt.game_no)
        ys = list(sub.elo_after.astype(float)) + list(nxt.elo_after.astype(float))
        ax.plot(xs, ys, lw=1.7, color=PHASE_COLOR[ph], label=PHASE_LABEL_PLAIN[ph])
ax.set_xlabel("ranked game")
ax.set_ylabel("ranked Elo")
ax.set_zorder(axw.get_zorder() + 1)
ax.patch.set_visible(False)
ax.legend(loc="upper left", frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(OUT / "wiki-growth-elo.pdf")
plt.close(fig)

# ── 5. Opening accuracy: the training-prior switch ──────────────────────────
od = pd.read_csv(HERE / "data" / "opening_accuracy.csv", parse_dates=["datetime"])
od = od.sort_values("datetime").reset_index(drop=True)
od["game_no"] = range(1, len(od) + 1)
FM_COLOR = {"e4": "#D55E00", "d4": "#0072B2"}
fig, ax = plt.subplots(figsize=(6.2, 3.0))
for fm, lbl in [("e4", "opens 1.e4 (parametric prior)"), ("d4", "opens 1.d4 (London)")]:
    sub = od[od.first_move == fm]
    ax.scatter(sub.game_no, sub.opening_acc, s=7, color=FM_COLOR[fm], alpha=0.55,
               lw=0, label=lbl)
other = od[~od.first_move.isin(FM_COLOR)]
if len(other):
    ax.scatter(other.game_no, other.opening_acc, s=7, color="#999999", alpha=0.5, lw=0)
# rolling mean over 15 games
od["roll"] = od.opening_acc.rolling(15, min_periods=8).mean()
ax.plot(od.game_no, od.roll, color=INK, lw=1.3)
# markers: instruction-only start; theory (book + wiki) added
instr = od[od.first_move == "d4"].game_no.min()
theory_dt = pd.Timestamp("2026-06-30T20:34:00+00:00")  # commit d923439 (theory ingest)
theory = od[od.datetime >= theory_dt].game_no.min()
for x, lbl, y, halign, dx in [
        (instr, "London instructed\n(no theory)", 74, "right", -4),
        (theory, "opening book\n+ theory pages", 74, "left", 4)]:
    ax.axvline(x - 0.5, color="#555", ls=":", lw=0.9)
    ax.annotate(lbl, (x - 0.5, y), fontsize=7, color="#555",
                ha=halign, va="top", xytext=(dx, 0), textcoords="offset points")
ax.set_xlabel("full game (chronological)")
ax.set_ylabel("opening accuracy (%)")
ax.set_ylim(65, 101)
ax.legend(loc="lower left", frameon=False, fontsize=7.5, markerscale=1.8)
fig.tight_layout()
fig.savefig(OUT / "opening-accuracy.pdf")
plt.close(fig)

print("wrote 4 PDFs ->", OUT)
