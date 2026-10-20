#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# report_01_phase_heatmap_panel.py  --  2D PHASE ENGINE report (Vera).
#
# The 2D PHASE first-light figure: for every pair-lake, the REAL-vs-SCRAMBLED
# joint NODE-density heatmap. This is the verification instrument Mondy ruled for
# -- a Form B diagonal ridge survives the scramble (visible), a true joint node
# lock vanishes under it (visible). The eye catches what the chaos z-score alone
# would misreport (single-axis structure fools chaos; the scramble catches it).
#
# OUTPUT: phase_heatmap_panel.png  (prefixed 'phase_' so it never collides with
# the PERIOD engine's heatmap_panel.png -- the two engines write to separate
# report folders, but the distinct filename keeps figures unambiguous if copied
# together into a volume's figure directory).
#
# Plugin contract: generate(context) -> [Path,...]. The figures stage
# (generate_figures_2d_phase.py) auto-discovers any report_*.py in
# reports2d_phase/, so this file is picked up automatically under this name.
# ==============================================================================
import json, math
from pathlib import Path

def generate(context):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        p = Path(context["output_dir"]) / "phase_heatmap_FALLBACK.txt"
        p.write_text(f"matplotlib unavailable ({e})\n"); return [p]

    logified = Path(context["logified_dir"])
    out_dir = Path(context["output_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(logified.glob("*_logified.jsonl"))
    if not files:
        p = out_dir / "phase_heatmap_EMPTY.txt"; p.write_text("no pair-lakes\n"); return [p]

    rng = np.random.default_rng(20260913)
    created = []
    ncol = 2
    nrow = len(files)
    fig, axes = plt.subplots(nrow, ncol, figsize=(9, 3.6*nrow))
    axes = np.array(axes).reshape(nrow, ncol)

    for r, f in enumerate(files):
        name = f.stem.replace("_logified","")
        pairs = np.array([(json.loads(l)["klghs_lnx1"], json.loads(l)["klghs_lnx2"])
                          for l in open(f, encoding="utf-8") if l.strip()])
        if len(pairs) < 20:
            for c in range(2): axes[r,c].set_visible(False)
            continue
        ln1, ln2 = pairs[:,0], pairs[:,1]
        ln2s = ln2[rng.permutation(len(ln2))]
        corr = abs(float(np.corrcoef(ln1,ln2)[0,1]))
        for c,(y,lab) in enumerate([(ln2,"REAL"),(ln2s,"SCRAMBLED")]):
            ax=axes[r,c]
            ax.hexbin(ln1,y,gridsize=30,cmap="inferno",mincnt=1)
            ax.set_title(f"{name} -- {lab}", fontsize=8)
            ax.tick_params(labelsize=5)
        axes[r,0].set_ylabel(f"|corr|={corr:.2f}", fontsize=7)

    fig.suptitle("KishLattice 2D PHASE Support -- REAL vs SCRAMBLED joint node density\n"
                 "ridge surviving scramble = Form B correlation; node grid vanishing "
                 "under scramble = true joint phase lock", fontsize=9)
    fig.tight_layout(rect=[0,0,1,0.96])
    png = out_dir / "phase_heatmap_panel.png"
    fig.savefig(png, dpi=115); plt.close(fig)
    created.append(png)
    return created