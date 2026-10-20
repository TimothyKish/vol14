#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# periodogram2d.py  --  THE 2D PERIOD ENGINE statistic.
#
# The 1D engine asks: does ln(x) repeat with period Delta_N?  (one phase)
# The 2D engine asks: does the PAIR (ln x1, ln x2) repeat JOINTLY with periods
# (Delta_N1, Delta_N2)?  -- a resultant on the TORUS, both phases together.
#
#   theta1_j = 2*pi * ln(x1_j) / Delta_N1
#   theta2_j = 2*pi * ln(x2_j) / Delta_N2
#   R_joint  = | mean_j exp( i (theta1_j + theta2_j) ) |     (the +1,+1 diagonal)
#   P_joint  = n R_joint^2
#
# Scanned over register PAIRS (N1, N2) -- 23x23 = 529 pairs. The look-elsewhere
# bar is far higher than 1D and is re-derived for the pair space.
#
# THE SCRAMBLE NULL IS THE SPINE AND IS NOT TUNABLE OFF. Shuffling x2 against x1
# destroys the pairing while preserving both marginals exactly. A joint lock that
# does NOT survive the scramble is marginal structure (Form B / Hertzsprung-
# Russell), not joint lattice structure. Every scored pair reports the scramble
# comparison. This is the whole reason 2D is worth building.
#
# TUNABLE FILTERS (via a filters dict; each may be turned on or off empirically):
#   common_support  : drop records below the clamp floor in EITHER coordinate
#                     (Form D compounds per-coordinate). default ON.
#   scale_flag      : report the scale-degeneracy of x2,x10,x10^3 per axis.
#                     default ON (report only; never silently rescales).
#   resolution_gate : require M/N > 2.67 in BOTH coordinates. default ON.
# The scramble null is deliberately NOT in this dict.
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from kish_period2d_io import to_compute, to_host, HAVE_GPU, n_workers

ROOT = _here.parent
TARGETS = ROOT / "configs2d_period" / "harmonic_targets.json"

ANNULUS_INNER = 1.6
ANNULUS_OUTER = 0.60
RES_THRESHOLD = ANNULUS_INNER / ANNULUS_OUTER   # 2.6667

DEFAULT_FILTERS = {"common_support": True, "scale_flag": True, "resolution_gate": True}


def load_registers_and_kgeo():
    with open(TARGETS, "r", encoding="utf-8") as f:
        t = json.load(f)
    return t["registers"], t.get("container", 24), float(t.get("k_geo", 16.0/math.pi))


def delta_N(N, kg, container):
    return N * math.log(kg) / (container * math.pi)


def _joint_power(ln1_b, ln2_b, xp, d1, d2):
    """Joint resultant power on the +1,+1 torus diagonal."""
    phase = (2.0*math.pi) * (ln1_b / d1 + ln2_b / d2)
    z = xp.mean(xp.exp(1j * phase))
    R = abs(z)
    return len(ln1_b) * R * R, R


def joint_power(ln1, ln2, d1, d2):
    b, xp = to_compute(np.ascontiguousarray(np.asarray(ln1, np.float64)))
    b2 = xp.asarray(ln2) if HAVE_GPU and hasattr(xp, "asarray") else np.asarray(ln2, np.float64)
    P, R = _joint_power(b, b2, xp, d1, d2)
    return to_host(P), to_host(R)


def floor_mask(ln, N, kg, container):
    """Common-support: True where the record is ABOVE the clamp floor at N."""
    d = delta_N(N, kg, container)
    rp = ln / d
    return rp >= 0.5


def mn_ratio(ln, N, kg, container):
    span = float(ln.max() - ln.min())
    return (span / delta_N(N, kg, container)) / N


def scale_degeneracy(N1, N2, kg, container):
    """Report whether common rescalings (x2, x10, x1000) are phase-neutral on the
    joint diagonal -- i.e. could manufacture a joint lock. Report only."""
    flags = {}
    for lab, c in (("x2", 2.0), ("x10", 10.0), ("x1000", 1000.0)):
        d1 = delta_N(N1, kg, container); d2 = delta_N(N2, kg, container)
        shift1 = (math.log(c)/d1) % 1.0
        shift2 = (math.log(c)/d2) % 1.0
        # near-neutral if either axis shift lands near an integer period
        flags[lab] = (min(shift1, 1-shift1) < 0.02) or (min(shift2, 1-shift2) < 0.02)
    return flags


def score_pair(pairs, N1, N2, kg, container, filters=None, rng=None):
    """Score one register pair. Returns dict with joint excess AND scramble excess."""
    filters = filters or DEFAULT_FILTERS
    ln1 = pairs[:, 0].copy()
    ln2 = pairs[:, 1].copy()

    # --- resolution gate (both coordinates), tunable ---
    if filters.get("resolution_gate", True):
        mn1 = mn_ratio(ln1, N1, kg, container)
        mn2 = mn_ratio(ln2, N2, kg, container)
        if mn1 <= RES_THRESHOLD or mn2 <= RES_THRESHOLD:
            return {"N1": N1, "N2": N2, "status": "UNRESOLVED",
                    "MN1": mn1, "MN2": mn2}

    # --- common support (both coordinates), tunable ---
    if filters.get("common_support", True):
        m = floor_mask(ln1, N1, kg, container) & floor_mask(ln2, N2, kg, container)
        ln1, ln2 = ln1[m], ln2[m]
        if len(ln1) < 20:
            return {"N1": N1, "N2": N2, "status": "FLOORED-OUT", "n_kept": int(len(ln1))}

    d1 = delta_N(N1, kg, container)
    d2 = delta_N(N2, kg, container)
    P_real, R_real = joint_power(ln1, ln2, d1, d2)

    # --- THE SCRAMBLE NULL (spine; not tunable) ---
    rng = rng or np.random.default_rng(20260913)
    n_scr = 24
    scr_P = np.empty(n_scr)
    for i in range(n_scr):
        perm = rng.permutation(len(ln2))
        scr_P[i], _ = joint_power(ln1, ln2[perm], d1, d2)
    scr_med = float(np.median(scr_P))
    scr_mad = float(np.median(np.abs(scr_P - scr_med))) * 1.4826
    scramble_excess = (P_real - scr_med) / scr_mad if scr_mad > 0 else float("nan")

    out = {"N1": N1, "N2": N2, "status": "SCORED",
           "P_real": P_real, "R_real": R_real,
           "scramble_median": scr_med,
           "scramble_excess": float(scramble_excess),
           "n_scored": int(len(ln1))}
    if filters.get("scale_flag", True):
        out["scale_degeneracy"] = scale_degeneracy(N1, N2, kg, container)
    return out


def scan_pairs(pairs, kg, container, registers, filters=None, heartbeat=None):
    """Scan all 529 register pairs. Returns the full grid + the best SCRAMBLE-SURVIVING pair."""
    filters = filters or DEFAULT_FILTERS
    rng = np.random.default_rng(20260913)
    rows = []
    total = len(registers)**2
    done = 0
    for N1 in registers:
        for N2 in registers:
            r = score_pair(pairs, N1, N2, kg, container, filters, rng)
            rows.append(r)
            done += 1
            if heartbeat and done % 25 == 0:
                heartbeat(f"pair scan {done}/{total}  ({N1}/pi, {N2}/pi)")
    scored = [r for r in rows if r.get("status") == "SCORED"]
    # the ONLY meaningful 'best' is the one that survives the scramble
    best = max(scored, key=lambda r: r["scramble_excess"]) if scored else None
    return rows, best


if __name__ == "__main__":
    regs, C, kg = load_registers_and_kgeo()
    from kish_period2d_io import resource_banner
    print(resource_banner())
    print(f"registers {regs[0]}..{regs[-1]}  container={C}  k_geo={kg:.8f}")
    print(f"pairs to scan: {len(regs)**2}   RES_THRESHOLD={RES_THRESHOLD}")
    print(f"default filters: {DEFAULT_FILTERS}  (scramble null is ALWAYS on)")


def census_null(pairs, kg, container, registers, n_scramble=5, heartbeat=None):
    """The honest 2D census verdict: does the real best-of-grid joint power exceed
    the SCRAMBLE best-of-grid? Noise gives ratio ~1 (both are look-elsewhere
    maxima over 529 pairs); a true joint lock gives ratio >> 1. This corrects the
    529-fold multiple-comparisons problem that a fixed per-pair bar cannot."""
    ln1 = pairs[:, 0]; ln2 = pairs[:, 1]
    deltas = {N: delta_N(N, kg, container) for N in registers}
    def best_of_grid(a, b):
        best = -9.0; bestpair = None
        for N1 in registers:
            for N2 in registers:
                P, _ = joint_power(a, b, deltas[N1], deltas[N2])
                if P > best:
                    best = P; bestpair = (N1, N2)
        return best, bestpair
    real_best, real_pair = best_of_grid(ln1, ln2)
    if heartbeat: heartbeat("census: scramble best-of-grid")
    rng = np.random.default_rng(20260913)
    scr = [best_of_grid(ln1, ln2[rng.permutation(len(ln2))])[0] for _ in range(n_scramble)]
    scr_med = float(np.median(scr))
    ratio = real_best / scr_med if scr_med > 0 else float("inf")
    return {"real_best": real_best, "real_pair": real_pair,
            "scramble_best_median": scr_med, "ratio": ratio,
            "verdict": "SURVIVES" if ratio > 1.5 else "noise-floor"}
