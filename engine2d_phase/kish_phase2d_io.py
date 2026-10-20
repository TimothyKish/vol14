#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# kish_phase2d_io.py  --  shared I/O + resource adaptation for the 2D period engine.
#
# Mirrors the 1D kish_period_io, but a 2D record is a PAIR (x1, x2) on the SAME
# object. The lake stores two raw positive quantities per record; the modulus
# enters only at test time. Same core principle: identical numbers on a potato
# and a beast, turtle to rabbit, streaming + reservoir sampling + optional GPU.
#
# A 2D logified record carries: klghs_lnx1, klghs_lnx2 (natural logs of the two
# raw coordinates, same object). load_pairs returns an (n,2) array.
# ==============================================================================
import json, os, sys, math
import numpy as np

DEFAULT_CAP = 2_000_000
SAMPLE_SEED = 20260913

try:
    import cupy as _cp
    _cp.zeros(1)
    HAVE_GPU = True
    _GPU_NAME = _cp.cuda.runtime.getDeviceProperties(0)["name"].decode()
except Exception:
    _cp = None
    HAVE_GPU = False
    _GPU_NAME = None

GPU_MIN_N = 500_000


def n_workers(cap=None):
    env = os.environ.get("KLGHS_WORKERS")
    if env:
        try: return max(1, int(env))
        except ValueError: pass
    c = os.cpu_count() or 1
    w = max(1, c - 1)
    return min(w, cap) if cap else w


def resource_banner(cap=DEFAULT_CAP):
    cores = os.cpu_count() or 1
    gpu = f"GPU: {_GPU_NAME}" if HAVE_GPU else "GPU: none (CPU only)"
    mode = "rabbit" if (cores >= 8 or HAVE_GPU) else ("hare" if cores >= 4 else "turtle")
    return (f"  resources: {cores} core(s), {n_workers()} worker(s), {gpu}   "
            f"[{mode}]   sample cap: {cap:,}")


def iter_pairs(path):
    """Yield (lnx1, lnx2) from a 2D logified lake, one pair at a time."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            a = rec.get("klghs_lnx1")
            b = rec.get("klghs_lnx2")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
               and math.isfinite(a) and math.isfinite(b):
                yield (float(a), float(b))


def count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def load_pairs(path, cap=DEFAULT_CAP, log=None):
    """Return (pairs (n,2) ndarray, meta). Reservoir-samples above cap, logged."""
    n_total = count_lines(path)
    meta = {"n_total": n_total, "n_used": n_total, "sampled": False, "cap": cap}
    if n_total <= cap:
        arr = np.array(list(iter_pairs(path)), dtype=np.float64)
        meta["n_used"] = len(arr)
        return arr, meta
    rng = np.random.default_rng(SAMPLE_SEED)
    res = np.empty((cap, 2), dtype=np.float64)
    i = 0
    for pr in iter_pairs(path):
        if i < cap:
            res[i] = pr
        else:
            j = rng.integers(0, i + 1)
            if j < cap:
                res[j] = pr
        i += 1
    meta["n_used"] = cap; meta["sampled"] = True
    if log:
        log(f"    [sample] {getattr(path,'name',path)}: {n_total:,} > cap {cap:,} "
            f"-> reservoir-sampled to {cap:,} (seed {SAMPLE_SEED}). Deterministic.")
    return res, meta


def cap_from_env(default=DEFAULT_CAP):
    env = os.environ.get("KLGHS_CAP")
    if env:
        try: return max(1000, int(env))
        except ValueError: pass
    return default


def to_compute(arr):
    if HAVE_GPU and len(arr) >= GPU_MIN_N:
        return _cp.asarray(arr), _cp
    return arr, np

def to_host(x):
    if HAVE_GPU and _cp is not None and isinstance(x, _cp.ndarray):
        return float(x.get())
    return float(x)


if __name__ == "__main__":
    print(resource_banner())
