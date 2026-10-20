#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# phase_lock2d.py  --  THE 2D PHASE ENGINE statistic (near-node CELL).
#
# Lifted faithfully from the 1D phase engine (build_pinch_table.py):
#   1D:  r_p = (scalar / target) * container ;  residual = |r_p - round(r_p)|
#        a record LOCKS when residual < lock_threshold (near an integer node).
#
# 2D:  a PAIR locks when BOTH coordinates sit near their nodes SIMULTANEOUSLY.
#      The node is now a CELL on the (register1, register2) grid, and agreement
#      is reported as the FRACTION OF RECORDS IN THE NEAR-NODE CELL -- Mondy's
#      ruling: "in 2D the node is a cell; agreement is a fraction of cell area,
#      never a fraction of values."
#
#        res1 = |r_p1 - nearest1| ,  res2 = |r_p2 - nearest2|
#        joint lock = res1 < tau AND res2 < tau   (inside the 2D node cell)
#        lock_rate  = (# pairs in cell) / (# pairs on common support)
#
# NULLS (phase engine has the full stack, unlike the period engine):
#   * CHAOS null  -- uniform random scalars on each axis, same support. The
#                    phase engine's canonical null (reproduces below-floor mass).
#   * SCRAMBLE null -- shuffle x2 against x1: kills joint pairing, keeps marginals.
#                    THE SPINE. Always on. Distinguishes joint lock from Form B.
#
# TUNABLE FILTERS (dict; on/off, as in the period engine):
#   common_support  : exclude r_p < 0.5 in EITHER coordinate (anti-node cut).
#   resolution_gate : require M/N > 2.67 in both coordinates.
#   scale_flag      : report x0/unit degeneracy -- FOUR freedoms in 2D phase.
# The scramble null is NOT in this dict.
#
# NOTE (Form A, OPEN GATE): the 1D transform theorem that certain distribution
# shapes manufacture phase structure has NOT been re-derived for the surface.
# Until it is, a 2D phase lock is reported but flagged FORM_A_UNCLEARED and is
# NOT citable as a result. See validate / pipeline. This is a pre-registered gate.
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from kish_phase2d_io import to_compute, to_host

ROOT = _here.parent
TARGETS = ROOT / "configs2d_phase" / "harmonic_targets.json"

RES_THRESHOLD = 2.6667
SUPPORT_FLOOR = 0.5                    # r_p < 0.5 is the anti-node (1D Erratum remedy)
FORM_A_CLEARED = False                 # OPEN GATE -- flip only when re-derived on a surface

DEFAULT_FILTERS = {"common_support": True, "resolution_gate": True, "scale_flag": True}


def load_registers_and_kgeo():
    t = json.load(open(TARGETS, encoding="utf-8"))
    return t["registers"], t.get("container", 24), float(t.get("k_geo", 16.0/math.pi))


def target_of(N, kg):
    return float(N) / math.pi            # N/pi, the harmonic target (phase convention)


def residuals(scalar, target, container):
    """1D near-node residual, lifted verbatim from build_pinch_table."""
    rp = (scalar / target) * container
    nearest = np.maximum(1, np.round(rp))
    return rp, np.abs(rp - nearest)


def mn_ratio(lnx, N, kg, container):
    span = float(lnx.max() - lnx.min())
    d = N * math.log(kg) / (container * math.pi)
    return (span / d) / N


def joint_lock_rate(s1, s2, N1, N2, kg, container, tau, filters):
    """Fraction of pairs inside the 2D near-node cell (res1<tau AND res2<tau),
    on common support. Returns (lock_rate, n_support) or (None, reason)."""
    t1 = target_of(N1, kg); t2 = target_of(N2, kg)
    rp1, res1 = residuals(s1, t1, container)
    rp2, res2 = residuals(s2, t2, container)

    if filters.get("common_support", True):
        on = (rp1 >= SUPPORT_FLOOR) & (rp2 >= SUPPORT_FLOOR)
    else:
        on = np.ones(len(s1), dtype=bool)
    n_sup = int(on.sum())
    if n_sup < 20:
        return None, "floored-out"

    in_cell = (res1[on] < tau) & (res2[on] < tau)
    return float(in_cell.mean()), n_sup


def score_pair(pairs, N1, N2, kg, container, tau=0.05, filters=None, rng=None):
    """Score one register pair: real joint lock rate vs CHAOS and SCRAMBLE nulls."""
    filters = filters or DEFAULT_FILTERS
    s1 = np.exp(pairs[:, 0]); s2 = np.exp(pairs[:, 1])   # phase works on the scalar, not ln
    # NOTE: phase convention scores the scalar directly; lnx stored in the lake,
    # scalar recovered here. (The 1D phase engine scores scalar_kls directly.)

    if filters.get("resolution_gate", True):
        mn1 = mn_ratio(pairs[:, 0], N1, kg, container)
        mn2 = mn_ratio(pairs[:, 1], N2, kg, container)
        if mn1 <= RES_THRESHOLD or mn2 <= RES_THRESHOLD:
            return {"N1": N1, "N2": N2, "status": "UNRESOLVED", "MN1": mn1, "MN2": mn2}

    real_rate, n_sup = joint_lock_rate(s1, s2, N1, N2, kg, container, tau, filters)
    if real_rate is None:
        return {"N1": N1, "N2": N2, "status": "FLOORED-OUT"}

    rng = rng or np.random.default_rng(20260913)
    # CHAOS null: uniform random scalars on each axis over the SAME range
    n_null = 16
    def chaos_once():
        c1 = np.exp(rng.uniform(pairs[:,0].min(), pairs[:,0].max(), len(s1)))
        c2 = np.exp(rng.uniform(pairs[:,1].min(), pairs[:,1].max(), len(s2)))
        r,_ = joint_lock_rate(c1, c2, N1, N2, kg, container, tau, filters)
        return r if r is not None else 0.0
    chaos = np.array([chaos_once() for _ in range(n_null)])

    # SCRAMBLE null: shuffle x2 against x1 (spine) -- kills joint, keeps marginals
    def scramble_once():
        perm = rng.permutation(len(s2))
        r,_ = joint_lock_rate(s1, s2[perm], N1, N2, kg, container, tau, filters)
        return r if r is not None else 0.0
    scr = np.array([scramble_once() for _ in range(n_null)])

    def z(null):
        m, sd = float(null.mean()), float(null.std())
        return (real_rate - m)/sd if sd > 0 else 0.0

    out = {"N1": N1, "N2": N2, "status": "SCORED",
           "real_lock_rate": real_rate, "n_support": n_sup,
           "chaos_z": z(chaos), "scramble_z": z(scr),
           "form_a_cleared": FORM_A_CLEARED}
    if not FORM_A_CLEARED:
        out["flag"] = "FORM_A_UNCLEARED -- not citable until surface transform theorem re-derived"
    return out


def census_null(pairs, kg, container, registers, tau=0.05, filters=None, heartbeat=None):
    """Honest 2D census: best-of-grid real lock rate vs SCRAMBLE best-of-grid.
    Same look-elsewhere correction proven in the period engine."""
    filters = filters or DEFAULT_FILTERS
    s1 = np.exp(pairs[:, 0]); s2 = np.exp(pairs[:, 1])
    rng = np.random.default_rng(20260913)
    def best_grid(a2):
        best = -1.0; bp = None
        for N1 in registers:
            for N2 in registers:
                r, _ = joint_lock_rate(s1, a2, N1, N2, kg, container, tau, filters)
                if r is not None and r > best:
                    best = r; bp = (N1, N2)
        return best, bp
    real_best, real_pair = best_grid(s2)
    if heartbeat: heartbeat("census: scramble best-of-grid")
    scr = [best_grid(s2[rng.permutation(len(s2))])[0] for _ in range(5)]
    scr_med = float(np.median(scr))
    ratio = real_best/scr_med if scr_med > 0 else float("inf")
    return {"real_best": real_best, "real_pair": real_pair,
            "scramble_best_median": scr_med, "ratio": ratio,
            "verdict": "SURVIVES" if ratio > 1.5 else "noise-floor",
            "form_a_cleared": FORM_A_CLEARED}


if __name__ == "__main__":
    regs, C, kg = load_registers_and_kgeo()
    from kish_phase2d_io import resource_banner
    print(resource_banner())
    print(f"registers {regs[0]}..{regs[-1]}  container={C}  k_geo={kg:.8f}")
    print(f"pairs: {len(regs)**2}  FORM_A_CLEARED={FORM_A_CLEARED} (OPEN GATE)")
    print(f"nulls: CHAOS + SCRAMBLE (scramble always on)")
