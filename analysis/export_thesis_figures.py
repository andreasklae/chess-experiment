#!/usr/bin/env python3
"""Export print-quality PDF figures for the thesis chess chapter.

Reads analysis/data/*.csv (build with build_dataset.py first) and writes PDFs
into ../../thesis/figures/chess/. Conventions: configurations are labelled
C1-C4 (each shaded band in the trajectory = ONE ranked calibration batch on
ONE fixed configuration; changes happen only at band boundaries); violin
plots (author preference over box plots); every multi-series plot carries a
legend; Okabe-Ito colourblind-safe palette in fixed order; serif text.
The wiki-size metric counts agent-readable pages only (references/ excluding
the verbatim raw/ source library), sampled at each configuration's merge
commit (the store was frozen during ranked play).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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

# dataset phase names -> configuration display labels (fixed order)
PHASES = ["P1-minimal-tools", "P2-visualization", "P3-mating-blunders", "P4-autonomous-loop"]
CONFIG_LABEL = {
    "P1-minimal-tools": "C1: minimal tools",
    "P2-visualization": "C2: board perception",
    "P3-mating-blunders": "C3: mating & blunder gates",
    "P4-autonomous-loop": "C4: autonomous loop",
}
CONFIG_SHORT = {"P1-minimal-tools": "C1", "P2-visualization": "C2",
                "P3-mating-blunders": "C3", "P4-autonomous-loop": "C4"}
CONFIG_COLOR = {"P1-minimal-tools": "#999999", "P2-visualization": "#56B4E9",
                "P3-mating-blunders": "#E69F00", "P4-autonomous-loop": "#009E73"}
# wiki size (agent-readable pages, k words) at each configuration's merge SHA
CONFIG_WIKI_KWORDS = {"P1-minimal-tools": 0.0, "P2-visualization": 0.0,
                      "P3-mating-blunders": 22.0, "P4-autonomous-loop": 38.6}
INK = "#1a1a1a"
WIKI_C = "#CC79A7"

df = pd.read_csv(HERE / "data" / "games.csv", parse_dates=["datetime"])
ranked = df[(df.kind == "ranked") & (~df.aborted)
            & df.result.isin(["1-0", "0-1", "1/2-1/2"])].sort_values("datetime").reset_index(drop=True)
ranked["game_no"] = range(1, len(ranked) + 1)
full = df[(~df.is_puzzle_mode) & (~df.aborted) & df.result.isin(["1-0", "0-1", "1/2-1/2"])]


def config_legend_handles():
    from matplotlib.patches import Patch
    return [Patch(facecolor=CONFIG_COLOR[ph], alpha=0.6, label=CONFIG_LABEL[ph])
            for ph in PHASES]


# ── 1. Elo trajectory ────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.2, 3.3))
for ph in PHASES:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        ax.axvspan(sub.game_no.min() - 0.5, sub.game_no.max() + 0.5,
                   color=CONFIG_COLOR[ph], alpha=0.18, lw=0)
        ax.axvline(sub.game_no.max() + 0.5, color="#666", lw=0.8)
ax.plot(ranked.game_no, ranked.elo_after.astype(float), lw=1.2, color=INK)
for ph, val in [("P1-minimal-tools", 684.2), ("P2-visualization", 793.6),
                ("P3-mating-blunders", 968.4), ("P4-autonomous-loop", 1347.9)]:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        ax.annotate(f"{val:.0f}", (sub.game_no.max(), val), fontsize=7.5,
                    xytext=(2, -9), textcoords="offset points", color=INK)
ax.set_xlabel("ranked game")
ax.set_ylabel("agent Elo")
leg = ax.legend(handles=config_legend_handles(), loc="upper left", frameon=False,
                title="calibration batches (one fixed configuration each)",
                title_fontsize=7.5)
plt.tight_layout()
fig.savefig(OUT / "elo-trajectory.pdf")
plt.close(fig)

# ── 2. Move quality by configuration (violins) ───────────────────────────────
fq = full.dropna(subset=["accuracy"]).copy()
fq["blunders_per_100"] = 100 * fq.blunders / fq.plies.clip(lower=1) * 2
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, col, title in [(axes[0], "accuracy", "game accuracy (%)"),
                       (axes[1], "blunders_per_100", "blunders per 100 own moves")]:
    data = [fq[fq.phase == ph][col].dropna().to_numpy() for ph in PHASES]
    vp = ax.violinplot(data, showmedians=True, widths=0.75)
    for body, ph in zip(vp["bodies"], PHASES):
        body.set_facecolor(CONFIG_COLOR[ph]); body.set_alpha(0.6)
        body.set_edgecolor(INK); body.set_linewidth(0.5)
    for part in ("cmedians", "cbars", "cmins", "cmaxes"):
        vp[part].set_color(INK); vp[part].set_linewidth(0.8)
    ax.set_xticks(range(1, 5))
    ax.set_xticklabels([CONFIG_SHORT[p] for p in PHASES])
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    for i, d in enumerate(data, 1):
        ax.annotate(f"n={len(d)}", (i, ax.get_ylim()[0]), ha="center",
                    fontsize=7, color="#555", xytext=(0, 2), textcoords="offset points")
fig.legend(handles=config_legend_handles(), ncol=4, loc="upper center",
           frameon=False, bbox_to_anchor=(0.5, 1.02))
plt.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(OUT / "quality-by-config.pdf", bbox_inches="tight")
plt.close(fig)

# ── 3. Loss profile by configuration (violin) ────────────────────────────────
losses = full[(full.result == "0-1") & full.worst_winpct_drop.notna()]
fig, ax = plt.subplots(figsize=(5.6, 3.1))
data = [losses[losses.phase == ph].worst_winpct_drop.to_numpy() for ph in PHASES]
vp = ax.violinplot(data, showmedians=True, widths=0.75)
for body, ph in zip(vp["bodies"], PHASES):
    body.set_facecolor(CONFIG_COLOR[ph]); body.set_alpha(0.6)
    body.set_edgecolor(INK); body.set_linewidth(0.5)
for part in ("cmedians", "cbars", "cmins", "cmaxes"):
    vp[part].set_color(INK); vp[part].set_linewidth(0.8)
ax.set_xticks(range(1, 5))
ax.set_xticklabels([CONFIG_SHORT[p] for p in PHASES])
ax.set_ylabel("worst single-move win% lost")
ax.grid(axis="x", visible=False)
for i, d in enumerate(data, 1):
    ax.annotate(f"n={len(d)}", (i, 0), ha="center", fontsize=7, color="#555")
ax.legend(handles=config_legend_handles(), loc="lower left", frameon=False, fontsize=7)
plt.tight_layout()
fig.savefig(OUT / "loss-profile.pdf")
plt.close(fig)

# ── 4. Wiki size (step, frozen per configuration) + Elo, one graph ───────────
fig, ax = plt.subplots(figsize=(6.2, 3.3))
axw = ax.twinx()
wiki_step = ranked.phase.map(CONFIG_WIKI_KWORDS).to_numpy()
axw.fill_between(ranked.game_no, wiki_step, step="post", color=WIKI_C, alpha=0.14, lw=0)
axw.plot(ranked.game_no, wiki_step, drawstyle="steps-post", color=WIKI_C,
         lw=1.4, label="knowledge store (k words)")
axw.set_ylabel("knowledge-store size (k words)", color=WIKI_C)
axw.tick_params(axis="y", labelcolor=WIKI_C)
axw.grid(visible=False)
axw.spines["right"].set_visible(True)
for ph in PHASES:
    sub = ranked[ranked.phase == ph]
    if len(sub):
        nxt = ranked[ranked.game_no == sub.game_no.max() + 1]
        xs = list(sub.game_no) + list(nxt.game_no)
        ys = list(sub.elo_after.astype(float)) + list(nxt.elo_after.astype(float))
        ax.plot(xs, ys, lw=1.7, color=CONFIG_COLOR[ph], label=CONFIG_LABEL[ph])
ax.set_xlabel("ranked game")
ax.set_ylabel("ranked Elo")
ax.set_zorder(axw.get_zorder() + 1)
ax.patch.set_visible(False)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = axw.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=7.2)
plt.tight_layout()
fig.savefig(OUT / "wiki-growth-elo.pdf")
plt.close(fig)

# ── 5. Fix-loop batches (two stacked single-axis panels) ─────────────────────
loop = pd.DataFrame([
    ("1", 7.42, 16), ("2", 5.35, 7), ("3", 5.80, 6),
    ("4", 5.81, 6), ("5", 4.83, 6), ("6", 3.59, 5),
], columns=["batch", "blunder_rate", "overrides"])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(5.4, 3.4), sharex=True,
                             gridspec_kw=dict(hspace=0.15))
x = range(len(loop))
a1.bar(x, loop.blunder_rate, width=0.55, color="#0072B2", label="all-move blunder rate (%)")
a1.set_ylabel("blunder rate (%)")
a1.legend(frameon=False, fontsize=7.5)
a2.bar(x, loop.overrides, width=0.55, color="#0072B2", label="blunders committed past the safety warning")
a2.set_ylabel("overridden blunders")
a2.legend(frameon=False, fontsize=7.5)
a2.set_xticks(list(x))
a2.set_xticklabels(loop.batch)
a2.set_xlabel("successive validation batches (autonomous period)")
for a in (a1, a2):
    a.grid(axis="x", visible=False)
fig.align_ylabels()
plt.tight_layout()
fig.savefig(OUT / "fix-loop.pdf")
plt.close(fig)

# ── 6. Opening accuracy + opponent strength ──────────────────────────────────
od = pd.read_csv(HERE / "data" / "opening_accuracy.csv", parse_dates=["datetime"])
od = od.sort_values("datetime").reset_index(drop=True)
od["game_no"] = range(1, len(od) + 1)
# join opponent elo from games.csv
opp = df.drop_duplicates("game_id").set_index("game_id").opponent_elo
od["opp_elo"] = od.game_id.map(opp)
FM_COLOR = {"e4": "#D55E00", "d4": "#0072B2"}
fig, ax = plt.subplots(figsize=(6.2, 3.2))
for fm, lbl in [("e4", "opens 1.e4 (the model's unprompted choice)"),
                ("d4", "opens 1.d4 (the London System)")]:
    sub = od[od.first_move == fm]
    ax.scatter(sub.game_no, sub.opening_acc, s=7, color=FM_COLOR[fm], alpha=0.55,
               lw=0, label=lbl)
od["roll"] = od.opening_acc.rolling(15, min_periods=8).mean()
ax.plot(od.game_no, od.roll, color=INK, lw=1.3, label="opening accuracy, 15-game rolling mean")
instr = od[od.first_move == "d4"].game_no.min()
theory_dt = pd.Timestamp("2026-06-30T20:34:00+00:00")
theory = od[od.datetime >= theory_dt].game_no.min()
for xpos, lbl, halign, dx in [(instr, "London instructed\n(no theory)", "right", -4),
                              (theory, "opening book\n+ theory pages", "left", 4)]:
    ax.axvline(xpos - 0.5, color="#555", ls=":", lw=0.9)
    ax.annotate(lbl, (xpos - 0.5, 74), fontsize=7, color="#555",
                ha=halign, va="top", xytext=(dx, 0), textcoords="offset points")
ax.set_xlabel("full game (chronological)")
ax.set_ylabel("opening accuracy (%)")
ax.set_ylim(65, 101)
# opponent strength on a recessive secondary axis
axo = ax.twinx()
axo.plot(od.game_no, od.opp_elo.rolling(15, min_periods=5).mean(),
         color="#888", lw=1.1, ls="--", label="opponent rating, 15-game rolling mean")
axo.set_ylabel("opponent rating", color="#888")
axo.tick_params(axis="y", labelcolor="#888")
axo.grid(visible=False)
axo.spines["right"].set_visible(True)
axo.set_ylim(600, 1500)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = axo.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="lower right", frameon=False, fontsize=6.8, markerscale=1.8)
plt.tight_layout()
fig.savefig(OUT / "opening-accuracy.pdf")
plt.close(fig)

print("wrote 6 PDFs ->", OUT)
