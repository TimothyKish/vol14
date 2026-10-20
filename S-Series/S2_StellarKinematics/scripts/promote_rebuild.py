import json
import os
import sys
import math
import uuid
from datetime import datetime, timezone

# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# ==============================================================================
# promote_rebuild.py  --  Vol 13/14 promotion gate, strict.
#
#   * No local scalarization (scalar_klc banned).
#   * The bouncer asserts the raw physical observable is PRESENT *and VALID* --
#     a null/NaN value is rejected exactly like a missing key. A field that is
#     present-but-null was the exact way a bad value could slip a "field exists"
#     check; it cannot here.
#   * Every count is real. No status line prints PASS without a computed basis.
# ==============================================================================

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
LAKE_DIR = os.path.join(SCRIPTS_DIR, '..', 'lake')
PROMOTED_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, '..', '..', '..', 'lakes', 'inputs_promoted'))

RAW_INPUT = os.path.join(LAKE_DIR, 's2_stellar_kinematics_dr3_raw.jsonl')
PROMOTED_OUTPUT = os.path.join(PROMOTED_DIR, 's2_stellar_kinematics_promoted.jsonl')

REQUIRED_FIELDS = ['vT_kms', 'parallax_corrected', 'pm_total']


def is_valid_number(v):
    """Present is not enough: the value must be a finite number. This is the
    guard that stops a present-but-null field from passing the bouncer."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def promote_lake():
    print("=" * 60)
    print("S2 Stellar Kinematics - Strict Promotion Gate")
    print("=" * 60)

    if not os.path.exists(RAW_INPUT):
        sys.exit(f"[ABORT] Raw lake not found: {RAW_INPUT}. Waiting on Gaia TAP build.")

    os.makedirs(PROMOTED_DIR, exist_ok=True)
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    promoted = 0
    seen = 0
    rejected_missing = 0
    rejected_invalid = 0

    with open(RAW_INPUT, 'r', encoding='utf-8') as fin, \
         open(PROMOTED_OUTPUT, 'w', encoding='utf-8') as fout:

        for line in fin:
            if not line.strip():
                continue
            seen += 1
            rec = json.loads(line.strip())

            # STRICT BOUNCER: present AND valid. A missing key OR a null/NaN
            # value aborts the run -- because a promoted lake must never carry a
            # null in a scored field, and a "field exists" check alone would let
            # one through.
            missing = [f for f in REQUIRED_FIELDS if f not in rec]
            if missing:
                sys.exit(f"[ABORT] record {seen}: missing required fields {missing}. "
                         f"No fallback, no fill. Fix the build.")
            invalid = [f for f in REQUIRED_FIELDS if not is_valid_number(rec[f])]
            if invalid:
                sys.exit(f"[ABORT] record {seen}: fields present but null/non-finite "
                         f"{invalid} (values {[rec[f] for f in invalid]}). A present-but-"
                         f"null value is rejected exactly like a missing one.")

            out_rec = {
                "entity_id": str(uuid.uuid4()),
                "domain": "stellar_kinematic",
                "volume": 14,
                "lake_id": "s2_stellar_kinematics",
                "val_raw": rec['vT_kms'],
                "meta": {
                    "source": "Gaia DR3 astrometry (vT_kms, raw)",
                    "ingest_timestamp": now_ts,
                    "sovereign": True,
                    "audit_status": "vol14_strict_covariance_rebuild",
                    "sector_normalized": False,
                    "parallax_mas": rec['parallax_corrected'],
                    "parallax_zp_applied": rec.get('parallax_zp_applied'),
                    "pm_total_mas_yr": rec['pm_total'],
                    "pm_over_error": rec.get('pm_over_error'),
                    "source_id": rec.get('source_id', 'unknown'),
                    "sample_note": "first 250k by Gaia random_index (unbiased sky sample)"
                },
                "_raw_payload": rec
            }
            fout.write(json.dumps(out_rec, ensure_ascii=False) + '\n')
            promoted += 1

    if promoted == 0:
        sys.exit("[ABORT] zero records promoted. Nothing written that could be scored.")

    print(f"  records seen        : {seen:,}")
    print(f"  promoted            : {promoted:,}")
    print(f"[PASS] {promoted:,} strict records promoted; every val_raw is a finite "
          f"empirical velocity (bouncer verified present AND valid).")
    print(f"Output: {PROMOTED_OUTPUT}")


if __name__ == "__main__":
    promote_lake()