#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# histogram_stage.py  --  PHASE ENGINE support-shape stage.
#
# Mirrors the period engine's histogram_view: for every scalarized lake it prints
# the support-shape verdict (FILLED / TAIL-INFLATED / SPARSE-TAIL / SPIKED) and
# the 25-bin distribution of the scalar, so a reader SEES the data shape before
# the chaos/pinch stages score it. The verdict is the summary; the histogram is
# the evidence, and both go into the run log the pipeline tees.
#
# This stage reads the phase engine's scalar field (scalar_kls / scalar_klc) from
# lakes/unified/*_scalarized.jsonl. It scores nothing and gates nothing -- it is a
# visibility stage, exactly like the period engine's. It never fails the pipeline:
# an unreadable lake is reported and skipped, not fatal.
#
# Writes: lakes/unified/phase_support_profile.json  (machine-readable summary)
# Prints: per-lake verdict + histogram  (captured by the pipeline log)
# ==============================================================================
import json
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCALARIZED_DIR = ROOT / "lakes" / "unified"
OUT_JSON = SCALARIZED_DIR / "phase_support_profile.json"

# scalar field priority in a scalarized phase record
SCALAR_KEYS = ("scalar_kls", "scalar_klc", "scalar", "scalar_raw")
Q = 0.005   # 99% central band for effective span


def extract_scalar(rec):
    for k in SCALAR_KEYS:
        v = rec.get(k)
        if isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
            return float(v)
    return None


def stream_lnx(path, cap=2_000_000):
    """Stream ln(scalar) from a scalarized lake. Reservoir-sample above cap so a
    giant lake never blows memory -- same discipline as the period engine."""
    vals = []
    rng = np.random.default_rng(20260913)
    n_total = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        s = extract_scalar(rec)
        if s is None:
            continue
        x = math.log(s)
        n_total += 1
        if len(vals) < cap:
            vals.append(x)
        else:
            j = rng.integers(0, n_total)
            if j < cap:
                vals[j] = x
    return np.array(vals), n_total


def profile(lnx, q=Q):
    lnx = np.asarray(lnx, float)
    lnx = lnx[np.isfinite(lnx)]
    if len(lnx) < 2 or float(lnx.max() - lnx.min()) <= 0.0:
        return {"n": int(len(lnx)), "raw_span": 0.0, "eff_span": 0.0,
                "tail_fraction": 0.0, "inflation": float("inf"),
                "verdict": "EMPTY-OR-DEGENERATE"}
    lo, hi = np.quantile(lnx, [q, 1 - q])
    raw = float(lnx.max() - lnx.min())
    eff = float(hi - lo)
    tail = float(np.mean((lnx < lo) | (lnx > hi)))
    infl = raw / eff if eff > 0 else float("inf")
    return {"n": int(len(lnx)), "raw_span": raw, "eff_span": eff,
            "tail_fraction": tail, "inflation": infl, "verdict": None}


def shape_verdict(counts, densest_frac, empty_interior, tail_frac, inflation):
    if densest_frac >= 0.25:
        return "SPIKED", "one bin holds >=25% of mass -- likely a single value or placeholder"
    if empty_interior >= 3:
        return "CLUMPED", f"{empty_interior} empty interior bins -- banded support with gaps"
    if inflation >= 3.0:
        return "SPARSE-TAIL-ARTIFACT", f"inflation {inflation:.1f}x -- span dominated by sparse tail"
    if inflation >= 1.5 or tail_frac >= 0.05:
        return "TAIL-INFLATED", f"inflation {inflation:.1f}x -- effective span below raw"
    return "FILLED", "mass spread across the span -- honest support"


def main():
    if not SCALARIZED_DIR.exists():
        print("  [histogram] no unified dir found -- nothing to profile.")
        return 0
    files = sorted(SCALARIZED_DIR.glob("*_scalarized.jsonl"))
    if not files:
        print("  [histogram] no *_scalarized.jsonl lakes found -- run scalarize first.")
        return 0

    print(f"  [histogram] profiling {len(files)} scalarized lake(s)")
    summary = {}
    for f in files:
        dom = f.stem.replace("_scalarized", "")
        lnx, n_total = stream_lnx(f)
        if len(lnx) < 20:
            print(f"\n  [{dom}] SKIPPED -- only {len(lnx)} usable scalar values")
            summary[dom] = {"skipped": True, "n_usable": int(len(lnx))}
            continue

        p = profile(lnx)
        if p["verdict"] == "EMPTY-OR-DEGENERATE":
            print(f"\n  [{dom}] SKIPPED -- degenerate support (zero span)")
            summary[dom] = {"skipped": True, "degenerate": True}
            continue

        h, edges = np.histogram(lnx, 25)
        densest = h.max() / len(lnx)
        empty_interior = int(np.sum(h[1:-1] == 0))
        sv, why = shape_verdict(h, densest, empty_interior, p["tail_fraction"], p["inflation"])

        sampled = " [sampled]" if n_total > len(lnx) else ""
        print(f"\n  [{dom}] n={n_total:,}{sampled}")
        print(f"    support: raw {p['raw_span']:.2f} eff {p['eff_span']:.2f} "
              f"infl {p['inflation']:.2f} -> {p['verdict'] or sv}")
        print(f"    shape:   {sv} -- {why}")
        print(f"    distribution (ln scalar, 25 bins, densest={densest*100:.0f}% of mass):")
        hmax = max(1, int(h.max()))
        for bi in range(25):
            bar = "#" * int(40 * h[bi] / hmax)
            print(f"      {edges[bi]:8.2f}..{edges[bi+1]:8.2f} {int(h[bi]):>9}  {bar}")

        summary[dom] = {"n": n_total, "raw_span": p["raw_span"],
                        "eff_span": p["eff_span"], "inflation": p["inflation"],
                        "shape": sv, "densest_frac": densest}

    try:
        OUT_JSON.write_text(json.dumps(summary, indent=2, default=float))
        print(f"\n  [histogram] support profile written: {OUT_JSON.name}")
    except Exception as e:
        print(f"\n  [histogram] (could not write summary json: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())