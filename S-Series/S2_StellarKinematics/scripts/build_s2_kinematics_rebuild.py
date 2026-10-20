import os
import sys
import json
import math
import pandas as pd
import numpy as np
from astroquery.gaia import Gaia
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# ==============================================================================
# build_s2_kinematics_rebuild.py  --  Vol 14 S2 rebuild, strict.
#
# PRE-REGISTERED (Vol 13 Ch 14): raw velocity only, no sector normalisation,
# full astrometry retained INCLUDING pmra_pmdec_corr, a 5-sigma PARALLAX gate
# AND a 5-sigma proper-motion gate on the COVARIANCE-PROPAGATED PM error, DR3
# zero-point handled explicitly, and the resolution gate COMPUTED from the data
# it built -- never a printed constant.
#
# Every gate in this script computes a number and can FAIL. There are no status
# lines that cannot fail. That is the point.
# ==============================================================================

K_GEO = 16.0 / math.pi
CONTAINER = 24
TARGET_REGISTER = 2                      # s2's pre-registered target
RES_THRESHOLD = 2.6667                   # annulus non-empty (Vol 12 Ch 12)
DR3_ZP_MICROARCSEC = -17.0               # DR3 global parallax zero-point (Lindegren+ 2021)
APPLY_ZP = True                          # explicit choice, recorded in output

LAKE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lake'))
os.makedirs(LAKE_DIR, exist_ok=True)
RAW_FILE = os.path.join(LAKE_DIR, 's2_stellar_kinematics_dr3_raw.jsonl')


def apply_strict_validity_cuts(df):
    print("\n--- APPLYING PHYSICAL FILTERS (pre-registered) ---")
    initial_len = len(df)

    # 1. Strict 5-sigma parallax gate
    df = df[df['parallax_over_error'] >= 5.0].copy()

    # 2. Parallax positive, proper motion present
    df = df[(df['parallax'] > 0) & (df['pmra'].notna()) & (df['pmdec'].notna())].copy()

    # 3. DR3 parallax zero-point: applied explicitly, or declined explicitly.
    #    Never silently copied under a name that claims a correction.
    if APPLY_ZP:
        df['parallax_corrected'] = df['parallax'] + (DR3_ZP_MICROARCSEC / 1000.0)  # uas -> mas
        df = df[df['parallax_corrected'] > 0].copy()   # a few near-zero can flip sign
    else:
        df['parallax_corrected'] = df['parallax']
    df['parallax_zp_applied'] = bool(APPLY_ZP)

    # 4. Total proper motion and its COVARIANCE-PROPAGATED error (pre-registered).
    #    sigma_mu = (1/mu) * sqrt( pmra^2 s_a^2 + pmdec^2 s_d^2 + 2 pmra pmdec rho s_a s_d )
    df['pm_total'] = np.sqrt(df['pmra']**2 + df['pmdec']**2)
    rho = df['pmra_pmdec_corr'] if 'pmra_pmdec_corr' in df.columns else 0.0
    if 'pmra_pmdec_corr' not in df.columns:
        # Do NOT silently assume rho=0 -- that would weaken the pre-registered cut.
        sys.exit("[ABORT] pmra_pmdec_corr not returned by the query. The covariance "
                 "propagation is pre-registered; add it to the SELECT or amend the "
                 "pre-registration. Refusing to build a weaker lake than filed.")
    sa, sd = df['pmra_error'], df['pmdec_error']
    var = (df['pmra']**2 * sa**2 + df['pmdec']**2 * sd**2
           + 2.0 * df['pmra'] * df['pmdec'] * rho * sa * sd)
    df['pm_total_error'] = np.sqrt(np.abs(var)) / df['pm_total']
    df['pm_over_error'] = df['pm_total'] / df['pm_total_error']

    # 5. Strict 5-sigma PROPER-MOTION gate (this is the pre-registered floor)
    df = df[df['pm_over_error'] >= 5.0].copy()

    # 6. Transverse velocity from sovereign astrometry
    df['vT_kms'] = 4.74047 * (df['pm_total'] / df['parallax_corrected'])

    # 7. Drop non-finite / non-physical (these are exclusions, not fills)
    df = df[np.isfinite(df['vT_kms']) & (df['vT_kms'] > 0) & (df['vT_kms'] < 1000)].copy()

    dropped = initial_len - len(df)
    print(f"  parallax S/N >= 5, pm S/N >= 5 (covariance-propagated), ZP "
          f"{'applied' if APPLY_ZP else 'declined'}")
    print(f"  dropped {dropped:,} records failing strict gates; {len(df):,} remain")
    return df


def resolution_gate(vT):
    """COMPUTE M/N from the built data. This can FAIL. It is not a print."""
    lnx = np.log(vT[vT > 0])
    span = float(lnx.max() - lnx.min())
    delta = TARGET_REGISTER * math.log(K_GEO) / (CONTAINER * math.pi)
    M = span / delta
    mn = M / TARGET_REGISTER
    return span, M, mn


def fetch_gaia_in_batches():
    print("Fetching raw astrometry from Gaia DR3 TAP server in batches...")
    chunk_size = 50_000_000
    max_index = 1_800_000_000
    all_records = []
    for start_idx in range(0, max_index, chunk_size):
        end_idx = start_idx + chunk_size - 1
        print(f"  -> random_index BETWEEN {start_idx} AND {end_idx} ...")
        query = f"""
        SELECT source_id, ra, dec, parallax, parallax_error, parallax_over_error,
               pmra, pmdec, pmra_error, pmdec_error, pmra_pmdec_corr, ruwe
        FROM gaiadr3.gaia_source
        WHERE random_index BETWEEN {start_idx} AND {end_idx}
          AND parallax > 5
          AND parallax_over_error > 5
        """
        try:
            job = Gaia.launch_job(query)
            df_chunk = job.get_results().to_pandas()
            print(f"     received {len(df_chunk):,} records")
            all_records.append(df_chunk)
            if sum(len(c) for c in all_records) > 250_000:
                print("\n[!] Harvested >250,000 records (first-by-random_index, an unbiased "
                      "sky sample). Early stop.")
                break
        except Exception as e:
            print(f"     [!] chunk failed: {e}")
            print("     [!] network/server issue; saving accumulated data (no fabrication)")
            break
    if not all_records:
        sys.exit("\n[ABORT] No data retrieved.")
    raw_df = pd.concat(all_records, ignore_index=True)
    print(f"\nTotal raw payload: {len(raw_df):,} records")
    return raw_df


if __name__ == "__main__":
    raw_df = fetch_gaia_in_batches()
    clean_df = apply_strict_validity_cuts(raw_df)

    if len(clean_df) < 100:
        sys.exit(f"\n[ABORT] only {len(clean_df)} records survived the strict gates; "
                 f"too few to build a lake. Nothing written.")

    # --- RESOLUTION GATE, COMPUTED (can fail) ---
    span, M, mn = resolution_gate(clean_df['vT_kms'].values)
    print("\n--- RESOLUTION CRITERION GATE (computed from built data) ---")
    print(f"  target register : {TARGET_REGISTER}/pi")
    print(f"  log-span        : {span:.4f} nat ({span/math.log(10):.2f} decades)")
    print(f"  M               : {M:.4f}")
    print(f"  M/N             : {mn:.4f}   (threshold {RES_THRESHOLD})")
    if mn > RES_THRESHOLD:
        print(f"  [PASS] data resolves {TARGET_REGISTER}/pi on its own span.")
    else:
        print(f"  [FAIL] data does NOT resolve {TARGET_REGISTER}/pi "
              f"(M/N {mn:.3f} <= {RES_THRESHOLD}). Lake is BACKGROUND-LIMITED.")
        print(f"         Writing anyway with the FAIL recorded -- the honest result is that")
        print(f"         transverse velocity spans too few decades, as Vol 13 predicted.")

    print(f"\nWriting {len(clean_df):,} strict records to {RAW_FILE} ...")
    written = 0
    with open(RAW_FILE, 'w', encoding='utf-8') as f:
        for rec in clean_df.to_dict('records'):
            # Exclude any record whose scored value went non-finite. Drop, do not None-fill.
            v = rec.get('vT_kms')
            if v is None or not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
                continue
            f.write(json.dumps(rec) + '\n')
            written += 1
    print(f"S2 rebuild complete: {written:,} records written "
          f"(resolution verdict recorded: {'PASS' if mn>RES_THRESHOLD else 'FAIL/background-limited'}).")