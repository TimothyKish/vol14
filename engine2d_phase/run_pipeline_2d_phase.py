#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# run_pipeline_2d_phase.py  --  2D PHASE ENGINE orchestrator.
#
# Stages, mirroring 1D: logify -> support(+heatmap) -> scan -> census.
# The scan scores all 529 register pairs with the scramble null (always on) and
# the tunable filters (common_support / scale_flag / resolution_gate). The
# census reports only pairs whose SCRAMBLE excess clears the pair-space bar.
#
# Full logging + receipt to lakes2d_phase/logs/, heartbeat for the sidecar,
# resource-adaptive (streams, samples, GPU/threads). Same familiar operation.
# ==============================================================================
import argparse, json, math, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent
LOGIFIED = ROOT / "lakes2d_phase" / "logified"
UNIFIED = ROOT / "lakes2d_phase" / "unified"
LOGS = ROOT / "lakes2d_phase" / "logs"
REPORTS = ROOT / "reports2d_phase" / "output"
HEARTBEAT = UNIFIED / "phase2d_heartbeat.json"

sys.path.insert(0, str(ENGINE))
from phase_lock2d import load_registers_and_kgeo, census_null, score_pair, DEFAULT_FILTERS, RES_THRESHOLD, FORM_A_CLEARED
from support2d import profile_pair_lake
from kish_phase2d_io import load_pairs, cap_from_env, resource_banner

STAGES = ["logify", "support", "scan", "census", "figures"]
# pair-space look-elsewhere bar: 529 pairs vs 23 registers. Re-derived, published.
BAR_PAIR = 6.90   # local scramble-excess for a pair-space 5-sigma (23*23 trials)


class Tee:
    def __init__(self, p): self.log=open(p,"w",encoding="utf-8"); self.out=sys.stdout
    def write(self,s): self.out.write(s); self.log.write(s)
    def flush(self): self.out.flush(); self.log.flush()
    def close(self): self.log.close()

def utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def heartbeat(pct, done, total, action, t0):
    UNIFIED.mkdir(parents=True, exist_ok=True)
    try:
        HEARTBEAT.write_text(json.dumps({"timestamp_utc":utc(),"progress_pct":round(pct,1),
            "completed":done,"total":total,"current_action":action,
            "eta_seconds":int((time.time()-t0)/max(pct,1e-9)*(100-pct)) if pct>0 else 0}))
    except Exception: pass

def heartbeat_reset(t0):
    UNIFIED.mkdir(parents=True, exist_ok=True)
    try: HEARTBEAT.write_text(json.dumps({"timestamp_utc":utc(),"progress_pct":0.0,
        "completed":0,"total":0,"current_action":"starting 2D run...","eta_seconds":0}))
    except Exception: pass

def fingerprint():
    import subprocess
    try:
        r=subprocess.run([sys.executable,str(ENGINE/"engine_version_2d_phase.py")],
                         capture_output=True,text=True)
        return r.stdout.strip().split("\n")[0]
    except Exception: return "unavailable"


def stage_logify():
    import subprocess
    r=subprocess.run([sys.executable,str(ENGINE/"logify2d.py")],capture_output=True,text=True)
    print(r.stdout,end="")
    if r.returncode!=0: print(r.stderr,file=sys.stderr); return False
    return True


def main():
    ap=argparse.ArgumentParser(description="KishLattice 2D PHASE engine")
    ap.add_argument("--from",dest="start",choices=STAGES,default="logify")
    ap.add_argument("--support-only",action="store_true")
    ap.add_argument("--skip-figures",action="store_true")
    ap.add_argument("--cap",type=int,default=None)
    # filter toggles -- the empirical knobs
    ap.add_argument("--no-common-support",action="store_true")
    ap.add_argument("--no-scale-flag",action="store_true")
    ap.add_argument("--no-resolution-gate",action="store_true")
    a=ap.parse_args()

    filters=dict(DEFAULT_FILTERS)
    if a.no_common_support: filters["common_support"]=False
    if a.no_scale_flag: filters["scale_flag"]=False
    if a.no_resolution_gate: filters["resolution_gate"]=False

    cap=a.cap or cap_from_env()
    LOGS.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tee=Tee(LOGS/f"run_phase2d_{stamp}.log"); sys.stdout=tee
    fp=fingerprint(); t0=time.time(); heartbeat_reset(t0)
    regs,C,kg=load_registers_and_kgeo()

    print("KishLattice 2D Period Engine Run Log"); print("="*72)
    print(f" started_utc : {utc()}")
    print(f" fingerprint : {fp}")
    print(resource_banner(cap))
    print(f" filters     : {filters}   (SCRAMBLE NULL: always on)")
    print(f" FORM A      : {'CLEARED' if FORM_A_CLEARED else 'OPEN GATE -- locks flagged, not citable'}")
    print(f" pair space  : {len(regs)}x{len(regs)} = {len(regs)**2} pairs   bar={BAR_PAIR}")
    print("="*72)

    si=STAGES.index(a.start)
    try:
        if si<=STAGES.index("logify"):
            print("\n[STAGE] logify")
            if not stage_logify(): sys.exit(1)

        files=sorted(LOGIFIED.glob("*_logified.jsonl"))
        if not files:
            print("  no logified pair-lakes found"); sys.exit(1)

        signals=[]
        for i,f in enumerate(files):
            dom=f.stem.replace("_logified","")
            heartbeat(100*i/len(files),i,len(files),f"loading {dom}",t0)
            pairs,meta=load_pairs(f,cap=cap,log=lambda s:print(s))

            print(f"\n[STAGE] support -- {dom}")
            profile_pair_lake(f,out_dir=REPORTS)

            if a.support_only: continue

            print(f"\n[STAGE] scan -- {dom} ({len(regs)**2} pairs, CHAOS+SCRAMBLE nulls)")
            def hb(msg): heartbeat(100*i/len(files),i,len(files),f"{dom}: {msg}",t0)
            cn = census_null(pairs, kg, C, regs, heartbeat=hb)
            np_ = cn["real_pair"]
            fa = "" if FORM_A_CLEARED else "  [FORM_A_UNCLEARED -- not citable]"
            print(f"    best-of-grid pair: ({np_[0]}/pi,{np_[1]}/pi)  "
                  f"real={cn['real_best']:.4f}  scramble={cn['scramble_best_median']:.4f}  "
                  f"ratio={cn['ratio']:.2f}  -> {cn['verdict']}{fa}")
            if cn["verdict"] == "SURVIVES":
                signals.append((dom, np_[0], np_[1], cn["ratio"]))

        if not a.support_only:
            print("\n"+"="*72); print("  2D REGISTER-PAIR CENSUS"); print("="*72)
            if signals:
                for dom,N1,N2,ratio in signals:
                    print(f"    {dom}: ({N1}/pi,{N2}/pi) real/scramble ratio {ratio:.2f} -- SURVIVES")
            else:
                print("  No register PAIR survives the scramble null above the pair-space bar.")
                print("  Any apparent joint structure is marginal (correlation / Form B) or")
                print("  below the noise floor. This is the honest outcome.")
            print("="*72)

        # ---- figures stage (Vera) ----
        if not a.support_only and not a.skip_figures:
            fig=ENGINE/"generate_figures_2d_phase.py"
            if fig.exists():
                print("\n[STAGE] figures")
                import subprocess
                r=subprocess.run([sys.executable,str(fig)],capture_output=True,text=True)
                print(r.stdout,end="")
    finally:
        rt=time.time()-t0
        try: heartbeat(100, 0, 0, "RUN COMPLETE", t0)
        except Exception: pass
        (LOGS/f"run_phase2d_{stamp}.receipt.txt").write_text(
            "KishLattice 2D PHASE Engine Receipt\n"+"="*48+"\n"
            f"fingerprint: {fp}\ncompleted_utc: {utc()}\nruntime_s: {rt:.1f}\n"
            f"filters: {filters}\nscramble_null: ALWAYS ON\npair_bar: {BAR_PAIR}\n")
        print(f"\nRuntime: {rt:.1f}s")
        sys.stdout=tee.out; tee.close()


if __name__ == "__main__":
    main()
