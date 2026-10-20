#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# make_synthetic_lakes.py  --  generate the 2D standing synthetic control lakes.
#
# These are the 2D analogue of the phase engine's lotto / finance / pure-noise
# nulls: permanent, version-controlled negative (and one positive) controls that
# prove the instrument does what it must on known data. They live on disk at
# lakes2d_period/synthetic/ and are regenerable from a FIXED SEED so anyone can
# reproduce them byte-identically and verify they are what they claim.
#
# FOUR control lakes, each a named, falsifiable expectation:
#   synth_noise     : uniform random pairs    -> MUST come back noise-floor
#   synth_jointlock : 25% planted joint lock  -> MUST survive the scramble
#   synth_formB     : linear correlation      -> MUST be killed by the scramble
#   synth_oneaxis   : lock on one axis only   -> MUST NOT register as joint
#
# Every record is stamped synthetic=True and carries its control role, so it can
# never be mistaken for real empirical data in a run or a review.
#
# Run:  python engine2d_period/make_synthetic_lakes.py
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from periodogram2d import load_registers_and_kgeo, delta_N

ROOT = _here.parent
OUT = ROOT / "lakes2d_period" / "synthetic"
SEED = 42          # fixed: regenerable byte-for-byte
N = 20000

CONTROLS = {
    "synth_noise":     "NEGATIVE CONTROL: uniform random pairs. Expect noise-floor (ratio ~1).",
    "synth_jointlock": "POSITIVE CONTROL: 25% planted joint lock at (11,13). Expect SURVIVES (ratio >> 1).",
    "synth_formB":     "NEGATIVE CONTROL: linear correlation (Hertzsprung-Russell analogue). Expect killed by scramble (ratio ~1).",
    "synth_oneaxis":   "NEGATIVE CONTROL: lock on axis 1 only. Expect NOT joint (ratio ~1).",
}


def write_lake(name, x1_log, x2_log, role):
    """Store as a PROMOTED pair-lake: two raw positive fields on the same object."""
    path = OUT / f"L_{name}_promoted.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for a, b in zip(x1_log, x2_log):
            f.write(json.dumps({
                "entity_id": None,
                "domain": "velocity_luminosity",   # maps via logify2d.json
                "vT_kms": float(math.exp(a)),
                "luminosity_lsun": float(math.exp(b)),
                "meta": {
                    "source": "SYNTHETIC CONTROL LAKE (generated)",
                    "synthetic": True,
                    "control_role": role,
                    "generator": "make_synthetic_lakes.py",
                    "seed": SEED,
                    "sector_normalized": False,
                },
            }) + "\n")
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    regs, C, kg = load_registers_and_kgeo()
    rng = np.random.default_rng(SEED)
    d1 = delta_N(11, kg, C)
    d2 = delta_N(13, kg, C)

    print(f"Generating 2D synthetic control lakes (seed {SEED}, n={N}) -> {OUT}\n")

    # 1. pure noise
    p = write_lake("synth_noise", rng.uniform(0, 20, N), rng.uniform(0, 20, N),
                   CONTROLS["synth_noise"])
    print(f"  [noise]     {p.name}")

    # 2. true joint lock
    a1 = rng.uniform(0, 20, N); a2 = rng.uniform(0, 20, N)
    idx = rng.choice(N, int(0.25 * N), replace=False)
    a1[idx] = np.round(a1[idx] / d1) * d1
    a2[idx] = np.round(a2[idx] / d2) * d2
    p = write_lake("synth_jointlock", a1, a2, CONTROLS["synth_jointlock"])
    print(f"  [jointlock] {p.name}")

    # 3. Form B correlation
    b1 = rng.uniform(0, 20, N); b2 = 0.7 * b1 + rng.normal(0, 0.5, N)
    b2 = b2 - b2.min() + 0.5
    p = write_lake("synth_formB", b1, b2, CONTROLS["synth_formB"])
    print(f"  [formB]     {p.name}")

    # 4. single-axis lock
    c1 = rng.uniform(0, 20, N); c2 = rng.uniform(0, 20, N)
    idx = rng.choice(N, int(0.25 * N), replace=False)
    c1[idx] = np.round(c1[idx] / d1) * d1
    p = write_lake("synth_oneaxis", c1, c2, CONTROLS["synth_oneaxis"])
    print(f"  [oneaxis]   {p.name}")

    # a manifest so the expectations are on disk, not just in a run
    manifest = OUT / "synthetic_manifest.json"
    manifest.write_text(json.dumps({
        "generated_by": "make_synthetic_lakes.py",
        "seed": SEED, "n_per_lake": N,
        "planted_registers": {"jointlock": [11, 13], "oneaxis": [11]},
        "controls": CONTROLS,
        "note": "Regenerate byte-identically with the same seed. These are standing "
                "negative/positive controls, the 2D analogue of the phase engine's "
                "lotto/finance/noise nulls. A run that does not reproduce these "
                "expectations indicates an engine regression.",
    }, indent=2))
    print(f"\n  manifest:   {manifest.name}")
    print("\nTo validate expectations, run the pipeline pointing inputs at this folder,")
    print("or copy these into lakes2d_period/inputs_promoted/ for a first-light run.")


if __name__ == "__main__":
    main()
