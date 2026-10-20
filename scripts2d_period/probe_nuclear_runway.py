#!/usr/bin/env python3
# ==============================================================================
# probe_nuclear_runway.py
#
# AM-15-01 Nuclear Go/No-Go Probe (Lyra's Assignment)
# Measures the dual-axis dynamic range (M/N ratio) for the only remaining 
# feasible 2D pair: Nuclear Half-life x Q-value/Binding Energy.
# 
# STRICT RULE: Measures span and join count only. Does NOT score registers.
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
Q4_FILE = IN_DIR / "q4_nuclear_promoted.jsonl"
Q5_FILE = IN_DIR / "q5_decay_promoted.jsonl"

def compute_mn_ratio(log_values, N=15, container=24, k_geo=16.0/math.pi):
    """Computes the M/N dynamic range resolution metric."""
    if not log_values: return 0.0
    span = max(log_values) - min(log_values)
    d = (N * math.log(k_geo)) / (container * math.pi)
    return (span / d) / N

def load_lake(filepath, key_to_extract):
    data = {}
    if not filepath.exists():
        print(f"[!] Warning: Could not find {filepath.name}")
        return data
        
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                
                Z = rec.get("Z")
                A = rec.get("A")
                if Z is None or A is None:
                    continue
                    
                join_key = f"{Z}_{A}"
                val = rec.get(key_to_extract)
                    
                if val is not None:
                    try:
                        f_val = float(val)
                        if f_val > 0 and math.isfinite(f_val):
                            data[join_key] = f_val
                    except ValueError:
                        pass
            except json.JSONDecodeError:
                continue
    return data

def main():
    print("================================================================")
    print(" NUCLEAR GO/NO-GO FEASIBILITY PROBE")
    print("================================================================")
    
    print("[*] Loading Q5 Decay Lake (Axis 1: Half-life)...")
    half_lives = load_lake(Q5_FILE, "half_life_seconds")
    
    print("[*] Loading Q4 Nuclear Lake (Axis 2: Energy)...")
    energies = load_lake(Q4_FILE, "binding_energy_mev_per_A")
    
    # Perform strict same-object inner join
    joint_entities = set(half_lives.keys()).intersection(set(energies.keys()))
    
    if not joint_entities:
        print("\n[!] FATAL: No intersecting nuclides found between Q4 and Q5 lakes.")
        print("[*] Verdict: Door Closed. Fold closure into Vol 14.")
        return

    hl_logs = []
    e_logs = []
    
    for entity in joint_entities:
        hl_logs.append(math.log(half_lives[entity]))
        e_logs.append(math.log(energies[entity]))

    hl_span = max(hl_logs) - min(hl_logs)
    e_span = max(e_logs) - min(e_logs)
    
    mn_hl = compute_mn_ratio(hl_logs, N=15)
    mn_e = compute_mn_ratio(e_logs, N=15)

    print(f"\n[*] STRICT JOIN COMPLETE: {len(joint_entities):,} matched nuclides.")
    print("\n[SPAN AND RESOLUTION METRICS - REGISTER 15]")
    print(f"  Axis 1 (Half-life):  Span = {hl_span:.2f} nat  |  M/N = {mn_hl:.4f}  [{'PASS' if mn_hl > 2.67 else 'FAIL'}]")
    print(f"  Axis 2 (Energy):     Span = {e_span:.2f} nat  |  M/N = {mn_e:.4f}  [{'PASS' if mn_e > 2.67 else 'FAIL'}]")
    
    print("\n[DECISION GATE]")
    if mn_hl > 2.67 and mn_e > 2.67:
        print("  => DOOR OPEN: Both axes resolve mid-registers. Proceed to Vol 15: The Second Doorway.")
    else:
        print("  => DOOR CLOSED: Dual-wide collapse. Fold the exhaustive proof into Vol 14.")

if __name__ == "__main__":
    main()