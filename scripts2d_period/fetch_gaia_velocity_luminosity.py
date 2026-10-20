#!/usr/bin/env python3
# ==============================================================================
# fetch_gaia_velocity_luminosity.py
#
# Connects to the Gaia DR3 archive via TAP/ADQL and downloads a sample 
# containing the exact astrometric and photometric columns required for 2D.
#
# UPDATED: Bypasses ESA server timeouts using a "Pencil Beam" spatial scan. 
# Instead of expensive global table scans, it throws random 3-degree darts 
# at the sky and uses highly-optimized spatial cone searches.
# ==============================================================================
import os
import sys
import time
import math
import random
import socket
from pathlib import Path

# Prevent zombie connections
socket.setdefaulttimeout(30)

try:
    import pandas as pd
    from astroquery.gaia import Gaia
except ImportError:
    print("[!] Missing dependencies. Please run: pip install astroquery pandas")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "lakes2d_period" / "inputs_raw"
OUT_FILE = OUT_DIR / "gaia_velocity_luminosity_raw.csv"

# Configuration
TARGET_TOTAL = 250_000   # 250k is massive for a 2D pair lake (S2 was 69k)
CONE_RADIUS_DEG = 3.0    # A 3-degree radius captures a rich but fast chunk

def get_random_coord():
    """Generates a random RA (0-360) and Dec (-90 to 90) for our pencil beam."""
    ra = random.uniform(0, 360)
    # Correct spherical point picking so we don't oversample the poles
    dec = math.degrees(math.asin(random.uniform(-1, 1)))
    return ra, dec

def build_cone_query(ra, dec, radius):
    # Spatial CONTAINS queries use HEALPix indexing and resolve in milliseconds
    return f"""
    SELECT source_id,
           parallax, parallax_error,
           pmra, pmra_error, pmdec, pmdec_error, pmra_pmdec_corr,
           phot_g_mean_mag, phot_g_mean_flux_over_error
    FROM gaiadr3.gaia_source
    WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {radius}))
      AND parallax > 0 
      AND parallax_error > 0
      AND pmra IS NOT NULL
      AND pmdec IS NOT NULL
      AND pmra_pmdec_corr IS NOT NULL
      AND phot_g_mean_mag IS NOT NULL
      AND phot_g_mean_flux_over_error > 20
    """

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if OUT_FILE.exists():
        OUT_FILE.unlink()
        
    print("================================================================")
    print(" FETCHING GAIA DR3 (PENCIL BEAM): VELOCITY x LUMINOSITY")
    print("================================================================")

    total_fetched = 0
    patch_count = 1

    while total_fetched < TARGET_TOTAL:
        ra, dec = get_random_coord()
        query = build_cone_query(ra, dec, CONE_RADIUS_DEG)
        
        print(f"\n[*] Scanning Patch {patch_count}: RA={ra:.2f}, Dec={dec:.2f} (Radius {CONE_RADIUS_DEG} deg)")
        
        try:
            # Synchronous query is perfect for lightning-fast spatial indices
            job = Gaia.launch_job(query, dump_to_file=False)
            results = job.get_results()
            df = results.to_pandas()
            
            if df.empty:
                print("    -> Sky patch empty or highly obscured. Moving to next.")
            else:
                write_header = (total_fetched == 0)
                df.to_csv(OUT_FILE, mode='a', index=False, header=write_header)
                
                rows_returned = len(df)
                total_fetched += rows_returned
                print(f"    -> Success! Retrieved {rows_returned:,} stars. (Total so far: {total_fetched:,})")
            
            patch_count += 1
            time.sleep(1) # Be polite between darts
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"    [!] Error encountered: {str(e).strip()}")
            # If a patch fails, we just throw another dart at a different part of the sky
            print("    [*] Skipping this patch and picking a new coordinate...")
            time.sleep(2)

    print("\n[*] SUCCESS! Raw Gaia dataset compiled and ready.")
    print(f"[*] Total records downloaded: {total_fetched:,}")
    print(f"[*] File saved to: {OUT_FILE}")

if __name__ == "__main__":
    main()