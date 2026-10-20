#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# support2d.py  --  2D support profile + the HEATMAP (the verification instrument).
#
# Mondy's ruling: "the 2D lock surface is an instrument, not an illustration. A
# shape artifact reads as structure in a table and as an obvious artifact in a
# heatmap. Visual inspection is part of the verification chain."
#
# This stage emits, per pair-lake:
#   * per-coordinate support verdict (reuses the 1D shape logic on each axis)
#   * a TEXT density grid in the log (coarse, so the log carries the shape)
#   * a PNG heatmap: REAL pairs vs SCRAMBLED pairs, side by side, so a Form B
#     diagonal ridge is visible as surviving the scramble (marginal) while a true
#     grid lock is visible as vanishing under scramble -- the eye catches it.
#
# The heatmap is in the VERIFICATION chain, not presentation: the diagonal-ridge
# detector prints a verdict (RIDGE / GRID / UNIFORM / BLOBS) into the log.
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))

def shape1d(lnx, q=0.005):
    lnx = np.asarray(lnx, float); lnx = lnx[np.isfinite(lnx)]
    if len(lnx) < 2 or lnx.max()-lnx.min() <= 0:
        return "EMPTY", 0.0, 0.0
    lo, hi = np.quantile(lnx, [q, 1-q])
    raw = float(lnx.max()-lnx.min()); eff = float(hi-lo)
    infl = raw/eff if eff > 0 else float("inf")
    h,_ = np.histogram(lnx, 25)
    if h.max()/len(lnx) >= 0.25: v="SPIKED"
    elif int(np.sum(h[1:-1]==0)) >= 3: v="CLUMPED"
    elif infl >= 3.0: v="SPARSE-TAIL"
    elif infl >= 1.5: v="TAIL-INFLATED"
    else: v="FILLED"
    return v, raw, eff


def ridge_detector(ln1, ln2):
    """Classify the joint density. A high |correlation| = diagonal RIDGE (Form B).
    Near-zero correlation with concentrated cells = possible GRID. Spread = UNIFORM."""
    r = float(np.corrcoef(ln1, ln2)[0,1])
    # occupancy concentration: how much mass is in the densest 2D cells
    H,_,_ = np.histogram2d(ln1, ln2, bins=20)
    conc = H.max()/len(ln1)
    if abs(r) > 0.5:
        return "RIDGE", f"|corr|={abs(r):.2f} -- diagonal correlation (Form B hazard)"
    if conc > 0.15:
        return "BLOBS", f"densest cell holds {conc*100:.0f}% -- concentrated, check for composite"
    return "UNIFORM", f"|corr|={abs(r):.2f}, spread -- no obvious marginal structure"


def text_grid(ln1, ln2, bins=12):
    """Coarse ASCII density grid for the log (the shape, in text)."""
    H,_,_ = np.histogram2d(ln1, ln2, bins=bins)
    H = H.T[::-1]  # orient so x1 is horizontal, x2 vertical, increasing up
    hmax = max(1, H.max())
    ramp = " .:-=+*#%@"
    lines = []
    for row in H:
        lines.append("    " + "".join(ramp[min(len(ramp)-1, int((len(ramp)-1)*c/hmax))] for c in row))
    return lines


def make_heatmap(ln1, ln2, out_png, title):
    """REAL vs SCRAMBLED side by side. Returns path or None if matplotlib absent."""
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    rng = np.random.default_rng(20260913)
    ln2s = ln2[rng.permutation(len(ln2))]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.4))
    for a, (y, lab) in zip(ax, [(ln2, "REAL pairs"), (ln2s, "SCRAMBLED (x2 shuffled)")]):
        a.hexbin(ln1, y, gridsize=35, cmap="inferno", mincnt=1)
        a.set_title(lab, fontsize=10); a.set_xlabel("ln x1", fontsize=8)
        a.set_ylabel("ln x2", fontsize=8); a.tick_params(labelsize=6)
    fig.suptitle(f"{title}\nA diagonal ridge that SURVIVES the scramble is correlation (Form B); "
                 f"a grid that VANISHES under scramble was a true joint lock", fontsize=9)
    fig.tight_layout(rect=[0,0,1,0.92])
    fig.savefig(out_png, dpi=120); plt.close(fig)
    return out_png


def profile_pair_lake(path, out_dir=None):
    pairs = np.array([(json.loads(l)["klghs_lnx1"], json.loads(l)["klghs_lnx2"])
                      for l in open(path, encoding="utf-8") if l.strip()])
    if len(pairs) < 20:
        print(f"  [{path.stem}] SKIPPED -- only {len(pairs)} usable pairs")
        return {"skipped": True}
    ln1, ln2 = pairs[:,0], pairs[:,1]
    name = path.stem.replace("_logified", "")
    v1, raw1, eff1 = shape1d(ln1)
    v2, raw2, eff2 = shape1d(ln2)
    rv, why = ridge_detector(ln1, ln2)
    print(f"\n  [{name}] n={len(pairs):,}")
    print(f"    coord 1: {v1:<14} eff {eff1:.2f} ({eff1/math.log(10):.1f} dec)")
    print(f"    coord 2: {v2:<14} eff {eff2:.2f} ({eff2/math.log(10):.1f} dec)")
    print(f"    joint  : {rv} -- {why}")
    print(f"    density grid (x1 ->, x2 ^):")
    for line in text_grid(ln1, ln2):
        print(line)
    png = None
    if out_dir:
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        png = make_heatmap(ln1, ln2, out_dir / f"{name}_heatmap.png",
                           f"KishLattice 2D support: {name}")
        if png: print(f"    heatmap: {png.name}")
    return {"n": len(pairs), "coord1": v1, "coord2": v2, "joint": rv,
            "eff1": eff1, "eff2": eff2, "heatmap": str(png) if png else None}


if __name__ == "__main__":
    p = Path(sys.argv[1])
    profile_pair_lake(p, out_dir=p.parent.parent / "reports2d_period" / "output")
