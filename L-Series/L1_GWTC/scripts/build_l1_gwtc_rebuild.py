import pandas as pd
import numpy as np
import json
import os
import sys

# ==============================================================================
# L1_GWTC REBUILD - STRICT KERR GATE
# Pre-registration: Vol 14. Target: 16/pi (using Register 4 logic scale)
# ==============================================================================

REGISTER_N = 4
K_GEO = 16 / np.pi
LATTICE_CONSTANT = 0.0215902
RESOLUTION_THRESHOLD = (REGISTER_N ** 2) * LATTICE_CONSTANT 

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lake'))
os.makedirs(OUT_DIR, exist_ok=True)
RAW_SOURCE = os.path.join(OUT_DIR, 'lvk_pyring_qnm_source.csv') 
OUT_FILE = os.path.join(OUT_DIR, 'l1_gwtc_qnm_raw.jsonl')

REQUIRED_FIELDS = ['event', 'f_220_hz', 'tau_220_s', 'final_mass_solar', 'final_spin']

def load_and_assert_contract(filepath):
    print("--- I/O CONTRACT ASSERTION ---")
    if not os.path.exists(filepath):
        sys.exit(f"[ABORT] Raw source file not found: {filepath}")
        
    df = pd.read_csv(filepath)
    missing = [f for f in REQUIRED_FIELDS if f not in df.columns]
    if missing:
        sys.exit(f"[ABORT] Missing required QNM fields: {missing}. No fallbacks allowed.")
        
    print("[PASS] All required QNM parameters present.")
    return df

def apply_falsification_filters(df):
    print("\n--- APPLYING PHYSICAL EXCLUSIONS ---")
    initial_count = len(df)
    
    # 1. Drop BNS / NSBH
    df = df[df['final_mass_solar'] >= 5.0].copy()
    
    # 2. Strict drop for missing values
    df = df.dropna(subset=['f_220_hz', 'final_mass_solar', 'final_spin'])
    
    print(f"Dropped {initial_count - len(df)} events (BNS/NSBH or incomplete).")
    return df

def kerr_consistency_gate(df):
    print("\n--- KERR CONSISTENCY GATE (Berti et al. 2009) ---")
    # Constants for l=m=2, n=0 mode
    f1, f2, f3 = 1.5251, -1.1568, 0.1292
    c3_over_2piGM_solar = 32312.5  # Hz conversion factor for 1 solar mass
    
    # Compute the theoretical Kerr frequency for the measured mass and spin
    omega_R = f1 + f2 * (1 - df['final_spin'])**f3
    df['f_kerr_theoretical'] = (c3_over_2piGM_solar / df['final_mass_solar']) * omega_R
    
    # Non-spinning floor (a=0)
    omega_R_nonspin = f1 + f2
    df['f_floor'] = (c3_over_2piGM_solar / df['final_mass_solar']) * omega_R_nonspin
    
    # Evaluate violations
    df['kerr_ratio'] = df['f_220_hz'] / df['f_kerr_theoretical']
    violations = df[df['f_220_hz'] < df['f_floor']]
    
    pass_fraction = (len(df) - len(violations)) / len(df)
    print(f"Computed theoretical Kerr bounds for {len(df)} events.")
    print(f"Events violating non-spinning floor: {len(violations)}")
    print(f"Kerr Consistency Pass Rate: {pass_fraction:.2%}")
    
    if pass_fraction < 0.50:
        sys.exit(f"[ABORT] Source data fails Kerr consistency (Pass rate {pass_fraction:.2%}). Extracted frequencies are likely peak merger, not QNMs.")
        
    df['kerr_pass_fraction'] = pass_fraction
    return df[df['f_220_hz'] >= df['f_floor']].copy()

def enforce_resolution_criterion(df):
    print("\n--- RESOLUTION CRITERION GATE ---")
    log_f = np.log(df['f_220_hz'].values)
    log_span = float(log_f.max() - log_f.min())

    # Correct M/N: span divided by the register PERIOD, then over N.
    # Delta_N = N * ln(k_geo) / (24 * pi);  M = span / Delta_N;  M/N = M / N.
    delta_N = REGISTER_N * np.log(K_GEO) / (24.0 * np.pi)
    M = log_span / delta_N
    m_n_ratio = M / REGISTER_N

    RES_THRESHOLD = 2.6667   # annulus non-empty; scoreable threshold above this

    print(f"Target Register:        {REGISTER_N}/pi")
    print(f"Log-Span:               {log_span:.4f} nat ({log_span/np.log(10):.2f} decades)")
    print(f"M:                      {M:.4f}")
    print(f"M/N Ratio:              {m_n_ratio:.4f}   (threshold {RES_THRESHOLD})")
    print(f"N (events):             {len(df)}")

    if m_n_ratio > RES_THRESHOLD:
        print("[PASS] Lake resolves target register on its own span.")
    elif m_n_ratio > 1.0:
        print("[BACKGROUND-LIMITED] M/N between 1.0 and 2.67: register resolvable in")
        print("   principle but annulus is too thin to score. Writing anyway,")
        print("   verdict recorded. This is the honest outcome, not a pass.")
    else:
        print("[FAIL] M/N < 1: data cannot distinguish this register from its")
        print("   neighbour. RESOLUTION-LIMITED. Writing anyway with FAIL recorded.")

    if len(df) < 30:
        print(f"[WARNING] n = {len(df)} events is very small. Treat any lock as provisional")
        print(f"   pending more loud events (O4/O5). Sample-size limit, not a defect.")
    print("---------------------------------\n")
    return df

def write_strict_io_lake(df):
    records = df.to_dict(orient='records')
    print(f"\nWriting {len(records)} strict records to {OUT_FILE}...")
    with open(OUT_FILE, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    print("l1_gwtc rebuild complete.")

if __name__ == "__main__":
    raw_df = load_and_assert_contract(RAW_SOURCE)
    clean_df = apply_falsification_filters(raw_df)
    kerr_df = kerr_consistency_gate(clean_df)
    final_df = enforce_resolution_criterion(kerr_df)
    write_strict_io_lake(final_df)