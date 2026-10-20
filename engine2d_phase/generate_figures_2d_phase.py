#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# ==============================================================================
# generate_figures_2d_phase.py -- 2D report executor (Vera). Auto-discovers
# report_*.py in reports2d_phase/, runs each generate(context), writes an index.
# No-op if the reports folder is empty. Mirrors the 1D generator.
# ==============================================================================
import importlib.util, json, sys
from datetime import datetime, timezone
from pathlib import Path
ENGINE=Path(__file__).resolve().parent; ROOT=ENGINE.parent
REPORTS=ROOT/"reports2d_phase"; LOGIFIED=ROOT/"lakes2d_phase"/"logified"
sys.path.insert(0,str(ENGINE))
from phase_lock2d import load_registers_and_kgeo
from kish_phase2d_io import load_pairs, cap_from_env

def main():
    plugins=sorted(p for p in REPORTS.glob("report_*.py")) if REPORTS.exists() else []
    if not plugins:
        print("  [figures] no report_*.py in reports2d_phase/ -- nothing to do."); return
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out=REPORTS/"output"/f"run_{stamp}"; out.mkdir(parents=True,exist_ok=True)
    regs,C,kg=load_registers_and_kgeo()
    ctx={"logified_dir":LOGIFIED,"output_dir":out,"registers":regs,"kg":kg,
         "container":C,"run_timestamp":stamp}
    print(f"  [figures] {len(plugins)} plugin(s) -> {out}")
    index={}
    for p in plugins:
        try:
            spec=importlib.util.spec_from_file_location(p.stem,p)
            m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            files=[str(x) for x in (m.generate(ctx) or [])]
            index[p.stem]=files; print(f"    [{p.stem}] {len(files)} file(s)")
        except Exception as e:
            index[p.stem]={"error":str(e)}; print(f"    [{p.stem}] FAILED: {e}")
    (out/"figures_index.json").write_text(json.dumps(index,indent=2))
    print(f"  [figures] index -> {out/'figures_index.json'}")

if __name__=="__main__": main()
