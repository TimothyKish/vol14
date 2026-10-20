import json
import os
import sys
import math
import uuid
from datetime import datetime, timezone

# -------------------------------------------------------------------------
# VOL 14 PROMOTION CONTRACT
# - No local scalarization.
# - Strict Bouncer: Fields must be PRESENT AND FINITE.
# -------------------------------------------------------------------------

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
LAKE_DIR = os.path.join(SCRIPTS_DIR, '..', 'lake')
PROMOTED_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, '..', '..', '..', 'lakes', 'inputs_promoted'))

RAW_INPUT = os.path.join(LAKE_DIR, 'l1_gwtc_qnm_raw.jsonl')
PROMOTED_OUTPUT = os.path.join(PROMOTED_DIR, 'l1_gwtc_promoted.jsonl')

REQUIRED_FIELDS = ['f_220_hz', 'tau_220_s', 'final_mass_solar', 'final_spin']

def is_valid_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def promote_lake():
    print("=" * 60)
    print("L1 GWTC (Ringdown) - Strict Promotion Gate")
    print("=" * 60)
    
    if not os.path.exists(RAW_INPUT):
        sys.exit(f"[ABORT] Raw lake not found: {RAW_INPUT}")
        
    os.makedirs(PROMOTED_DIR, exist_ok=True)
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    promoted = 0
    seen = 0
    
    with open(RAW_INPUT, 'r', encoding='utf-8') as fin, \
         open(PROMOTED_OUTPUT, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            if not line.strip():
                continue
            seen += 1
            rec = json.loads(line.strip())
            
            missing = [f for f in REQUIRED_FIELDS if f not in rec]
            if missing:
                sys.exit(f"[ABORT] Record {seen} missing fields: {missing}")
                
            invalid = [f for f in REQUIRED_FIELDS if not is_valid_number(rec[f])]
            if invalid:
                sys.exit(f"[ABORT] Record {seen} contains null/non-finite fields: {invalid}")
                
            out_rec = {
                "entity_id": str(uuid.uuid4()),
                "domain": "gravitational_wave",
                "volume": 14,
                "lake_id": "l1_gwtc_qnm",
                "val_raw": rec['f_220_hz'],
                "meta": {
                    "source": "LVK Testing GR (pyRing) f_220 QNM",
                    "ingest_timestamp": now_ts,
                    "sovereign": True,
                    "audit_status": "vol14_strict_qnm_rebuild",
                    "sector_normalized": False,
                    "mass_final": rec['final_mass_solar'],
                    "spin_final": rec['final_spin'],
                    "tau_220_s": rec['tau_220_s'],
                    "kerr_pass_fraction": rec.get('kerr_pass_fraction', 1.0),
                    "event_name": rec.get('event', 'unknown'),
                    "exclusions": "BNS/NSBH dropped (M_f < 5); non-spinning violators dropped"
                },
                "_raw_payload": rec
            }
            fout.write(json.dumps(out_rec, ensure_ascii=False) + '\n')
            promoted += 1
            
    print(f"  records seen        : {seen}")
    print(f"  promoted            : {promoted}")
    print(f"[PASS] {promoted} strict records promoted; val_raw is a finite empirical frequency.")
    print(f"Output: {PROMOTED_OUTPUT}")

if __name__ == "__main__":
    promote_lake()