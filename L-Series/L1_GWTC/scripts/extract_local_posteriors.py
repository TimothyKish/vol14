import os
import h5py
import pandas as pd
import numpy as np

# ==============================================================================
# L1_GWTC EMPIRICAL POSTERIOR EXTRACTOR - ROBUST FUSION
# Strict implementation of Option A: Measured f_220 only.
# Fuses Damped Sinusoid (DS) f_220/tau_220 with Kerr Mf/af.
# ==============================================================================

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lake', 'zenodo_downloads'))
OUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lake', 'lvk_pyring_qnm_source.csv'))

def get_posterior_dataset(hf):
    """Safely locates the posterior samples array across different LVK release schemas."""
    paths = ['PROD1/posterior_samples', 'GWTC3_rerun_PROD1/posterior_samples', 'posterior_samples', 'posterior']
    for p in paths:
        if p in hf:
            return hf[p]
            
    # Recursive fallback
    for key in hf.keys():
        if 'posterior' in key.lower(): 
            return hf[key]
        if isinstance(hf[key], h5py.Group):
            for subk in hf[key].keys():
                if 'posterior' in subk.lower(): 
                    return hf[key][subk]
    return None

def get_median(dataset, possible_keys):
    """Safely attempts to extract the median using a list of known column aliases."""
    names = dataset.dtype.names if dataset.dtype.names else dataset.keys()
    for k in possible_keys:
        if k in names:
            return float(np.median(dataset[k][()]))
    return None

def extract_ds_metrics(filepath):
    """Extracts purely empirical f_220 and tau_220 from a Damped Sinusoid run."""
    try:
        with h5py.File(filepath, 'r') as hf:
            dataset = get_posterior_dataset(hf)
            if dataset is not None:
                f_val = get_median(dataset, ['f_t_0', 'f_220', 'f_ringdown', 'f_0'])
                t_val = get_median(dataset, ['tau_t_0', 'tau_220', 'tau_ringdown', 'tau_0'])
                if f_val is not None and t_val is not None:
                    return {'f_220_hz': f_val, 'tau_220_s': t_val}
    except Exception:
        pass
    return None

def extract_kerr_metrics(filepath):
    """Extracts the Kerr-inferred final mass and spin for the consistency gate."""
    try:
        with h5py.File(filepath, 'r') as hf:
            dataset = get_posterior_dataset(hf)
            if dataset is not None:
                m_val = get_median(dataset, ['Mf', 'final_mass_source', 'final_mass', 'm_f'])
                a_val = get_median(dataset, ['af', 'final_spin', 'a_f', 'spin_final'])
                if m_val is not None and a_val is not None:
                    return {'final_mass_solar': m_val, 'final_spin': a_val}
    except Exception:
        pass
    return None

def main():
    print("--- EXTRACTING AND FUSING EMPIRICAL QNM POSTERIORS ---")
    event_files = {}
    
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.endswith('.h5'):
                parts = file.split('_')
                if len(parts) > 1:
                    event_raw = parts[1]
                    event_name = event_raw.replace('S', 'GW') if event_raw.startswith('S') else event_raw
                    
                    if event_name not in event_files:
                        event_files[event_name] = {'ds': [], 'kerr': []}
                        
                    filepath = os.path.join(root, file)
                    if 'DS_1mode' in file:
                        event_files[event_name]['ds'].append(filepath)
                    elif 'Kerr_220' in file and 'domega' not in file:
                        event_files[event_name]['kerr'].append(filepath)

    records = []
    for event, paths in event_files.items():
        if not paths['ds'] or not paths['kerr']:
            continue 
            
        ds_data = extract_ds_metrics(paths['ds'][0])
        kerr_data = extract_kerr_metrics(paths['kerr'][0])
        
        if ds_data and kerr_data:
            # BBH Gate
            if kerr_data['final_mass_solar'] > 5.0:
                record = {'event': event}
                record.update(ds_data)
                record.update(kerr_data)
                records.append(record)
                print(f"[+] {event}: f_220={record['f_220_hz']:.1f}Hz, Mf={record['final_mass_solar']:.1f}M_sun")

    if not records:
        sys.exit("\n[FAIL] No events contained both complete DS and Kerr posteriors.")
        
    df = pd.DataFrame(records).sort_values(by='event')
    df.to_csv(OUT_FILE, index=False)
    print(f"\n[PASS] Extracted {len(df)} measured QNM events to {OUT_FILE}")
    print("Next: Run 'python build_l1_gwtc_rebuild.py'")

if __name__ == "__main__":
    main()