#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# ==============================================================================
# sidecar_2d_period.py  --  live status monitor for the 2D period pipeline.
# Same design as 1D: polls the heartbeat, renders progress, flags staleness.
# ==============================================================================
import json, time, sys
from pathlib import Path
HEARTBEAT = Path("lakes2d_period/unified/period2d_heartbeat.json")
STALE_AFTER = 20
def fmt(s): s=int(max(0,s)); m,s=divmod(s,60); h,m=divmod(m,60); return f"{h}h {m}m {s}s"
def clear(): sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
def main():
    print("Waiting for 2D Period Engine heartbeat...")
    last=None; changed=time.time(); spin="|/-\\"; tick=0
    while True:
        try:
            if HEARTBEAT.exists():
                d=json.loads(HEARTBEAT.read_text()); pct=float(d.get("progress_pct",0))
                act=d.get("current_action","?"); now=time.time()
                if act!=last: last=act; changed=now
                stale=(now-changed)>STALE_AFTER; tick=(tick+1)%4
                clear(); print("="*62)
                print(" KISHLATTICE 2D PERIOD SIDECAR ".center(62,"~")); print("="*62)
                print(f" Time    : {d.get('timestamp_utc')}")
                bar="#"*int(pct//2)+"."*(50-int(pct//2))
                print(f" Progress: [{bar}] {pct:.1f}%")
                print(f" Lakes   : {d.get('completed')} / {d.get('total')}")
                print(f" ETA     : {fmt(d.get('eta_seconds',0))}")
                if "COMPLETE" in act or pct>=100:
                    print(f" Stage   : [DONE] {act}")
                    print(f"           Run finished -- safe to close (Ctrl+C).")
                elif stale:
                    print(f" Stage   : {act}")
                    print(f"           (no update {int(now-changed)}s -- 529-pair scan with")
                    print(f"            scramble null is heavy; working, not hung)")
                else:
                    print(f" Stage   : {spin[tick]} {act}")
                print("="*62)
        except (json.JSONDecodeError,IOError): pass
        time.sleep(1)
if __name__=="__main__": main()
