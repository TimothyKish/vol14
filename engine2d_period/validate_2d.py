#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# ==============================================================================
# validate_2d.py -- THE BUILD GATE for the 2D period engine.
# Four pre-registered checks; the engine is not trusted until all pass:
#   A. PURE NOISE pairs -> scramble excess ~ 0 (no false joint lock)
#   B. TRUE JOINT lock -> survives the scramble (large excess)
#   C. FORM B correlation -> KILLED by the scramble (the Hertzsprung-Russell guard)
#   D. EXPECTED FAIL -- a planted lock on ONE axis only must NOT survive, because
#      a single-axis lock is marginal, not joint. This is the pre-registered
#      expected-fail: a panel that only passes proves self-agreement, not disagreement.
# ==============================================================================
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from periodogram2d import load_registers_and_kgeo, delta_N, score_pair, DEFAULT_FILTERS

def banner(t): print("\n"+"="*66+f"\n  {t}\n"+"="*66)
def nf(**kw): f=dict(DEFAULT_FILTERS); f["resolution_gate"]=False; f.update(kw); return f

def main():
    regs,C,kg=load_registers_and_kgeo(); rng=np.random.default_rng(20260913); n=20000
    N1,N2=11,13; d1=delta_N(N1,kg,C); d2=delta_N(N2,kg,C)
    passed=True

    banner("A. PURE NOISE pairs -> no joint lock")
    p=np.c_[rng.uniform(0,20,n),rng.uniform(0,20,n)]
    exA=score_pair(p,N1,N2,kg,C,nf())["scramble_excess"]
    okA=abs(exA)<5; passed&=okA
    print(f"  scramble_excess={exA:+.2f}  {'PASS' if okA else 'FAIL'} (expect |x|<5)")

    banner("B. TRUE JOINT lock -> survives scramble")
    a1=rng.uniform(0,20,n); a2=rng.uniform(0,20,n)
    idx=rng.choice(n,int(0.25*n),replace=False)
    a1[idx]=np.round(a1[idx]/d1)*d1; a2[idx]=np.round(a2[idx]/d2)*d2
    exB=score_pair(np.c_[a1,a2],N1,N2,kg,C,nf())["scramble_excess"]
    okB=exB>20; passed&=okB
    print(f"  scramble_excess={exB:+.1f}  {'PASS' if okB else 'FAIL'} (expect >20)")

    banner("C. FORM B correlation -> KILLED by scramble (H-R guard)")
    b1=rng.uniform(0,20,n); b2=0.7*b1+rng.normal(0,0.5,n)
    exC=score_pair(np.c_[b1,b2],N1,N2,kg,C,nf())["scramble_excess"]
    okC=abs(exC)<5; passed&=okC
    print(f"  scramble_excess={exC:+.2f}  {'PASS' if okC else 'FAIL'} (expect |x|<5: scramble kills it)")

    banner("D. EXPECTED FAIL -- single-axis lock must NOT survive as joint")
    c1=rng.uniform(0,20,n); c2=rng.uniform(0,20,n)
    idx=rng.choice(n,int(0.25*n),replace=False)
    c1[idx]=np.round(c1[idx]/d1)*d1   # ONLY axis 1 locked; axis 2 random
    exD=score_pair(np.c_[c1,c2],N1,N2,kg,C,nf())["scramble_excess"]
    okD=abs(exD)<5; passed&=okD
    print(f"  scramble_excess={exD:+.2f}  {'PASS' if okD else 'FAIL'} (expect |x|<5: 1 axis != joint)")

    banner("BUILD GATE "+("GREEN -- 2D period engine may be built out" if passed
                           else "RED -- do not proceed"))
    sys.exit(0 if passed else 1)

if __name__=="__main__": main()
