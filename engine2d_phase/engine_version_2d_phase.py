#!/usr/bin/env python3
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
import hashlib, sys, argparse
from pathlib import Path
SLOTS=[("phase_lock2d_py","engine2d_phase","phase_lock2d.py"),
       ("logify2d_py","engine2d_phase","logify2d.py"),
       ("kish_phase2d_io_py","engine2d_phase","kish_phase2d_io.py"),
       ("logify2d_json","configs2d_phase","logify2d.json"),
       ("harmonic_targets","configs2d_phase","harmonic_targets.json")]
def _md5(p):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(8192),b""): h.update(c)
    return h.hexdigest()
def compute(base=None):
    b=Path(base) if base else Path(__file__).resolve().parent.parent
    segs=[]
    for n,sub,fn in SLOTS:
        p=b/sub/fn
        if not p.exists(): raise FileNotFoundError(f"fingerprint needs {p}")
        segs.append(_md5(p))
    return "".join(segs)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base"); a=ap.parse_args()
    v=compute(a.base); print(v); print()
    for i,(n,sub,fn) in enumerate(SLOTS):
        print(f"  {n:<22} {v[i*32:(i+1)*32]}   ({sub}/{fn})")
if __name__=="__main__": main()
