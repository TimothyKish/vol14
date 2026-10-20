import os
import h5py

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lake', 'zenodo_downloads'))

def inspect_rosetta_stone():
    # We will use GW150914 as our Rosetta Stone to read the LVK schema
    targets = ["rin_S150914_pyring_DS_1mode_10M.h5", "rin_S150914_pyring_Kerr_220_10M.h5"]
    
    found = 0
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file in targets:
                found += 1
                print(f"\n=== Inspecting: {file} ===")
                try:
                    with h5py.File(os.path.join(root, file), 'r') as hf:
                        def print_keys(name, obj):
                            if isinstance(obj, h5py.Dataset):
                                print(f"Dataset: {name}")
                                if obj.dtype.names:
                                    print(f"  Columns: {obj.dtype.names}")
                        hf.visititems(print_keys)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
                    
    if found == 0:
        print(f"Could not find the target files in {DOWNLOAD_DIR}")

if __name__ == "__main__":
    inspect_rosetta_stone()