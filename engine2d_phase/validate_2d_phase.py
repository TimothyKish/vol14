#!/usr/bin/env python3
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# validate_2d_phase.py -- BUILD GATE for the 2D phase engine. Five checks; the
# fifth is what the phase engine uniquely needs: proof the SCRAMBLE catches
# single-axis structure the CHAOS null is fooled by.
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase_lock2d import load_registers_and_kgeo, target_of, score_pair, DEFAULT_FILTERS
def banner(t): print("\n"+"="*66+f"\n  {t}\n"+"="*66)
def nf(**k): f=dict(DEFAULT_FILTERS); f["resolution_gate"]=False; f.update(k); return f
def main():
    regs,C,kg=load_registers_and_kgeo(); rng=np.random.default_rng(20260913); n=20000
    N1,N2=11,13; t1=target_of(N1,kg); t2=target_of(N2,kg); passed=True

    banner("A. NOISE -> both nulls ~0")
    s1=np.exp(rng.uniform(0,10,n)); s2=np.exp(rng.uniform(0,10,n))
    r=score_pair(np.c_[np.log(s1),np.log(s2)],N1,N2,kg,C,filters=nf())
    okA=abs(r["scramble_z"])<5 and abs(r["chaos_z"])<5; passed&=okA
    print(f"  chaos_z={r['chaos_z']:+.1f} scramble_z={r['scramble_z']:+.1f}  {'PASS' if okA else 'FAIL'}")

    banner("B. TRUE JOINT lock -> survives scramble")
    s1=rng.uniform(1,1000,n); s2=rng.uniform(1,1000,n)
    idx=rng.choice(n,int(0.30*n),replace=False)
    s1[idx]=t1*np.round(s1[idx]/t1*C)/C; s2[idx]=t2*np.round(s2[idx]/t2*C)/C
    r=score_pair(np.c_[np.log(s1),np.log(s2)],N1,N2,kg,C,filters=nf())
    okB=r["scramble_z"]>20; passed&=okB
    print(f"  scramble_z={r['scramble_z']:+.1f}  {'PASS' if okB else 'FAIL'} (expect >20)")

    banner("C. FORM B correlation -> scramble ~0")
    s1=rng.uniform(1,1000,n); s2=s1*rng.uniform(0.9,1.1,n)
    r=score_pair(np.c_[np.log(s1),np.log(s2)],N1,N2,kg,C,filters=nf())
    okC=abs(r["scramble_z"])<5; passed&=okC
    print(f"  scramble_z={r['scramble_z']:+.1f}  {'PASS' if okC else 'FAIL'}")

    banner("D. SINGLE-AXIS -> CHAOS fooled, SCRAMBLE catches it (the key phase check)")
    s1=rng.uniform(1,1000,n); s2=rng.uniform(1,1000,n)
    idx=rng.choice(n,int(0.30*n),replace=False); s1[idx]=t1*np.round(s1[idx]/t1*C)/C
    r=score_pair(np.c_[np.log(s1),np.log(s2)],N1,N2,kg,C,filters=nf())
    okD=r["chaos_z"]>10 and abs(r["scramble_z"])<5; passed&=okD
    print(f"  chaos_z={r['chaos_z']:+.1f} (fooled, expect >10)  scramble_z={r['scramble_z']:+.1f} (catches, expect ~0)  {'PASS' if okD else 'FAIL'}")
    print("  -> this is WHY the phase engine needs the scramble: chaos alone would")
    print("     report single-axis structure as a false joint discovery.")

    banner("E. FORM A gate present and OPEN")
    okE = (r.get("flag","").startswith("FORM_A_UNCLEARED")); passed&=okE
    print(f"  form_a flag: {'present (locks not citable)' if okE else 'MISSING'}  {'PASS' if okE else 'FAIL'}")

    banner("BUILD GATE "+("GREEN -- 2D phase engine validated (Form A still open)" if passed else "RED"))
    sys.exit(0 if passed else 1)
if __name__=="__main__": main()
