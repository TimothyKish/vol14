#!/usr/bin/env python3
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# make_synthetic_lakes.py -- 2D PHASE standing controls. Plant on NODES (phase).
import json, math, sys
from pathlib import Path
import numpy as np
_here=Path(__file__).resolve().parent; sys.path.insert(0,str(_here))
from phase_lock2d import load_registers_and_kgeo, target_of
ROOT=_here.parent; OUT=ROOT/"lakes2d_phase"/"synthetic"; SEED=42; N=20000
def write(name,s1,s2,role):
    p=OUT/f"L_{name}_promoted.jsonl"
    with open(p,"w") as f:
        for a,b in zip(s1,s2):
            f.write(json.dumps({"entity_id":None,"domain":"velocity_luminosity",
                "vT_kms":float(a),"luminosity_lsun":float(b),
                "meta":{"source":"SYNTHETIC CONTROL","synthetic":True,"control_role":role,
                        "generator":"make_synthetic_lakes.py","seed":SEED,"sector_normalized":False}})+"\n")
    return p
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    regs,C,kg=load_registers_and_kgeo(); rng=np.random.default_rng(SEED)
    t1=target_of(11,kg); t2=target_of(13,kg)
    print(f"Generating 2D PHASE synthetic controls (seed {SEED}) -> {OUT}\n")
    # noise
    write("synth_noise",np.exp(rng.uniform(0,10,N)),np.exp(rng.uniform(0,10,N)),"NEG: noise-floor")
    print("  [noise]")
    # joint lock: 30% on BOTH nodes
    s1=rng.uniform(1,1000,N); s2=rng.uniform(1,1000,N); idx=rng.choice(N,int(0.30*N),replace=False)
    s1[idx]=t1*np.round(s1[idx]/t1*C)/C; s2[idx]=t2*np.round(s2[idx]/t2*C)/C
    write("synth_jointlock",s1,s2,"POS: SURVIVES at (11,13)"); print("  [jointlock]")
    # Form B
    s1=rng.uniform(1,1000,N); s2=s1*rng.uniform(0.9,1.1,N)
    write("synth_formB",s1,s2,"NEG: scramble kills correlation"); print("  [formB]")
    # single axis
    s1=rng.uniform(1,1000,N); s2=rng.uniform(1,1000,N); idx=rng.choice(N,int(0.30*N),replace=False)
    s1[idx]=t1*np.round(s1[idx]/t1*C)/C
    write("synth_oneaxis",s1,s2,"NEG: chaos fooled, scramble catches"); print("  [oneaxis]")
    (OUT/"synthetic_manifest.json").write_text(json.dumps({"generated_by":"make_synthetic_lakes.py",
        "seed":SEED,"n":N,"planted":{"jointlock":[11,13],"oneaxis":[11]},
        "note":"2D PHASE controls. single-axis is the KEY: chaos_z high (fooled), scramble_z ~0 (caught)."},indent=2))
    print("\n  manifest written")
if __name__=="__main__": main()
