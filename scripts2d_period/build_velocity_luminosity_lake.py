#!/usr/bin/env python3
# ==============================================================================
# build_velocity_luminosity_lake.py
#
# Constructs the first real 2D pair-lake: velocity x luminosity.
# Strictly enforces the same-object pairing constraint and applies the identical
# 5-sigma covariance gates from the S2 rebuild. 
#
# Input:  Gaia DR3 CSV from the ADQL query.
# Output: Promoted JSONL ready for both 2D engines.
# ==============================================================================
import csv
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Assuming the raw CSV is saved here after you run the ADQL query
IN_FILE = ROOT / "lakes2d_period" / "inputs_raw" / "gaia_velocity_luminosity_raw.csv"
OUT_DIR = ROOT / "lakes2d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_velocity_luminosity_promoted.jsonl"

def compute_mn_ratio(log_values, N=15, container=24, k_geo=16.0/math.pi):
    """Computes the M/N dynamic range resolution metric."""
    if not log_values: return 0.0
    span = max(log_values) - min(log_values)
    d = (N * math.log(k_geo)) / (container * math.pi)
    return (span / d) / N

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_FILE.exists():
        print(f"[!] Raw input not found: {IN_FILE}")
        print("    Please run the ADQL query and save the CSV to this location.")
        return

    print("================================================================")
    print(" BUILDING 2D LAKE: VELOCITY x LUMINOSITY")
    print("================================================================")
    
    total_in = 0
    total_out = 0
    
    vT_logs = []
    L_logs = []

    with open(IN_FILE, "r", encoding="utf-8") as f_in, \
         open(OUT_FILE, "w", encoding="utf-8") as f_out:
        
        reader = csv.DictReader(f_in)
        for row in reader:
            total_in += 1
            try:
                # 1. Parallax Gate (with DR3 zero-point shift)
                parallax_raw = float(row["parallax"])
                parallax_err = float(row["parallax_error"])
                p = parallax_raw - (-0.017)
                
                if p <= 0 or p < 5 * parallax_err:
                    continue
                
                # 2. Proper Motion Covariance Gate
                pmra = float(row["pmra"])
                pmdec = float(row["pmdec"])
                pmra_err = float(row["pmra_error"])
                pmdec_err = float(row["pmdec_error"])
                corr = float(row["pmra_pmdec_corr"])
                
                mu_sq = pmra**2 + pmdec**2
                if mu_sq <= 0: continue
                mu = math.sqrt(mu_sq)
                
                variance = ( (pmra**2 * pmra_err**2) + 
                             (pmdec**2 * pmdec_err**2) + 
                             (2 * pmra * pmdec * corr * pmra_err * pmdec_err) ) / mu_sq
                
                if variance <= 0: continue
                sigma_mu = math.sqrt(variance)
                
                if mu < 5 * sigma_mu:
                    continue
                    
                # 3. Compute Transverse Velocity
                vT = 4.74047 * (mu / p)
                if vT <= 0 or not math.isfinite(vT): continue

                # 4. Compute Luminosity (G-band absolute proxy)
                # Distance modulus M = m + 5*log10(p_mas) - 10
                phot_g = float(row["phot_g_mean_mag"])
                M_G = phot_g + 5 * math.log10(p) - 10.0
                
                # Convert to Solar Luminosities (assuming M_sun_G ~ 4.66)
                L_lsun = 10 ** (-0.4 * (M_G - 4.66))
                if L_lsun <= 0 or not math.isfinite(L_lsun): continue

                # 5. Build the strict same-object record
                master_rec = {
                    "entity_id": row["source_id"],
                    "domain": "velocity_luminosity",
                    "vT_kms": vT,
                    "luminosity_lsun": L_lsun,
                    "meta": {
                        "source": "Gaia DR3",
                        "synthetic": False,
                        "sector_normalized": False,
                        "bolometric_correction": "none (raw G-band absolute proxy)"
                    }
                }
                
                f_out.write(json.dumps(master_rec) + "\n")
                
                vT_logs.append(math.log(vT))
                L_logs.append(math.log(L_lsun))
                total_out += 1
                
            except (ValueError, TypeError, KeyError):
                continue

    print(f"[*] Processed {total_in:,} raw records.")
    print(f"[*] Promoted {total_out:,} valid pairs passing all strict gates.")
    
    if total_out > 0:
        # Pre-flight the promotion gates (M/N > 2.67) for register 15
        mn_vT = compute_mn_ratio(vT_logs, N=15)
        mn_L = compute_mn_ratio(L_logs, N=15)
        
        print("\n  [PROMOTION GATE PRE-FLIGHT (15/pi)]")
        print(f"    vT_kms          M/N = {mn_vT:.4f}  [{'PASS' if mn_vT > 2.67 else 'FAIL'}]")
        print(f"    luminosity_lsun M/N = {mn_L:.4f}  [{'PASS' if mn_L > 2.67 else 'FAIL'}]")
        
        if mn_vT > 2.67 and mn_L > 2.67:
            print("\n[*] BOTH coordinates clear the 2D resolution criterion. Ready for engine ingestion.")
        else:
            print("\n[!] WARNING: One or both coordinates fail the M/N > 2.67 resolution gate at 15/pi.")
            
        print(f"\n[*] Saved to: {OUT_FILE}")

if __name__ == "__main__":
    main()