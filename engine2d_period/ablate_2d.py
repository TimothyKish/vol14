#!/usr/bin/env python3
r"""
KishLattice 2D Filter Ablation Harness  --  ablate_2d.py
=========================================================
Measures the empirical contribution of each tunable form filter in the 2D
period / phase engine by running the FULL 2^3 factorial over the three
toggles and tabulating the census verdict for every lake the pipeline scores.

    toggle (default ON; --no-X turns it OFF)   Form
    ----------------------------------------   ----
    common_support                             Form D  (null-support / floor mismatch)
    scale_flag                                 Form C  (scale degeneracy / preprocessing)
    resolution_gate                            the  M/N > 2.67  resolution criterion

The SCRAMBLE NULL is the spine: ALWAYS ON, never a toggle. Form B is read in
every cell as the real-vs-scramble ratio itself. Form A is the open gate
(FORM_A_UNCLEARED) and is not a filter. So the factorial is 2^3 = 8 runs.

HOW TO USE
----------
Drop this file into the SAME folder as run_pipeline_2d_period.py, and a copy
into the engine2d_phase folder next to run_pipeline_2d_phase.py. It auto-detects
which pipeline it sits beside. From the vol14 root, run:

    python .\engine2d_period\ablate_2d.py
    python .\engine2d_phase\ablate_2d.py

It drives the REAL pipeline as a subprocess under each of the 8 flag
combinations -- exactly the same code path as a normal run, no internal calls --
parses the census block from stdout, saves each combo's raw log, and emits:

    filter_ablation_<engine>.csv      (one row per combo x lake; full detail)
    ablation_logs_<engine>\...        (raw stdout per combo, for the receipt)
    a console pivot: ratio per lake per combo, with deltas vs the all-on baseline

SOVEREIGN INTEGRITY: this harness computes nothing but bookkeeping. The engine
does all the math natively under each flag set, just as in a normal run.
"""

import os, sys, glob, re, csv, subprocess, itertools, datetime

# --- locate the pipeline this harness sits beside -------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)        # vol14 root (where you normally run from)
_cands = glob.glob(os.path.join(SCRIPT_DIR, "run_pipeline_2d_*.py"))
if not _cands:
    sys.exit(f"[ablate] no run_pipeline_2d_*.py found beside this script in {SCRIPT_DIR}")
PIPELINE = _cands[0]
ENGINE   = "phase" if "phase" in os.path.basename(PIPELINE).lower() else "period"

# --- the three toggles, in fixed order ------------------------------------
TOGGLES = ["common_support", "scale_flag", "resolution_gate"]
FLAG    = {"common_support":  "--no-common-support",
           "scale_flag":      "--no-scale-flag",
           "resolution_gate": "--no-resolution-gate"}
FORM    = {"common_support": "D", "scale_flag": "C", "resolution_gate": "gate"}

# Your lakes are already logified from the Oct-6 runs, so scan is the fast path.
# For a from-scratch reproduction, set FIRST_FROM = "logify" to prepare once.
FIRST_FROM = "scan"
REST_FROM  = "scan"

LOGDIR = os.path.join(PROJECT_ROOT, f"ablation_logs_{ENGINE}")
os.makedirs(LOGDIR, exist_ok=True)

# --- regexes over the census stdout ---------------------------------------
RE_LAKE   = re.compile(r"\[STAGE\]\s+scan\s+--\s+(\S+)")
RE_SCORED = re.compile(r"scored\s+(\d+)\s*/\s*(\d+)\s+pairs")
RE_BEST   = re.compile(
    r"best-of-grid pair:\s*\(([^)]+)\)\s*real=([0-9.eE+\-]+)\s*"
    r"scramble=([0-9.eE+\-]+)\s*ratio=([0-9.eE+\-]+)\s*->\s*(\S+)")


def run_combo(state, stage_from):
    """state: dict toggle->bool (True = filter ON). Returns (results, raw, rc)."""
    flags = [FLAG[t] for t in TOGGLES if not state[t]]
    cmd = [sys.executable, PIPELINE, "--from", stage_from, "--skip-figures"] + flags
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    results, cur = {}, None
    for line in out.splitlines():
        m = RE_LAKE.search(line)
        if m:
            cur = m.group(1)
            results.setdefault(cur, {"pair": "", "real": "", "scramble": "",
                                     "ratio": "", "verdict": "", "scored": "", "total": ""})
            continue
        if cur:
            ms = RE_SCORED.search(line)
            if ms:
                results[cur]["scored"], results[cur]["total"] = ms.group(1), ms.group(2)
            mb = RE_BEST.search(line)
            if mb:
                results[cur].update(pair=mb.group(1), real=mb.group(2),
                                    scramble=mb.group(3), ratio=mb.group(4),
                                    verdict=mb.group(5))
    return results, out, proc.returncode


def label_of(state):
    return "".join("1" if state[t] else "0" for t in TOGGLES)


def main():
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print("=" * 74)
    print(f" KishLattice 2D FILTER ABLATION  --  {ENGINE.upper()} engine")
    print(f" pipeline : {os.path.basename(PIPELINE)}")
    print(f" toggles  : " + ", ".join(f"{t} (Form {FORM[t]})" for t in TOGGLES))
    print(f" scramble : ALWAYS ON (the spine; not a toggle)")
    print("=" * 74)

    # all 8 combos, baseline (all-ON) first, then by number of filters removed
    combos = [dict(zip(TOGGLES, bits)) for bits in itertools.product([True, False], repeat=3)]
    combos.sort(key=lambda s: sum(not v for v in s.values()))

    rows, table, lakes_seen = [], {}, []
    for i, state in enumerate(combos):
        stage = FIRST_FROM if i == 0 else REST_FROM
        lab = label_of(state)
        offs = [FORM[t] for t in TOGGLES if not state[t]] or ["baseline (all on)"]
        print(f"\n[{i+1}/8] combo {lab}  (off: {', '.join(offs)})  --from {stage}")
        res, raw, rc = run_combo(state, stage)
        with open(os.path.join(LOGDIR, f"combo_{lab}_{stamp}.log"), "w", encoding="utf-8") as f:
            f.write(raw)
        if rc != 0:
            print(f"    [warn] pipeline exit code {rc} -- see log; parsed what was available")
        if not res:
            print("    [warn] no scan lines parsed -- check the log for this combo")
        for lake, d in sorted(res.items()):
            if lake not in lakes_seen:
                lakes_seen.append(lake)
            table.setdefault(lab, {})[lake] = d.get("ratio", "")
            rows.append({"engine": ENGINE, "combo": lab,
                         "common_support": state["common_support"],
                         "scale_flag": state["scale_flag"],
                         "resolution_gate": state["resolution_gate"],
                         "lake": lake, **d})
            sc = f"{d.get('scored','?')}/{d.get('total','?')}"
            print(f"      {lake:30s} ratio={d.get('ratio',''):>8}  "
                  f"scored={sc:>9}  {d.get('verdict','')}")

    # --- CSV (full detail) ---
    csvpath = os.path.join(PROJECT_ROOT, f"filter_ablation_{ENGINE}.csv")
    with open(csvpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["engine", "combo", "common_support", "scale_flag",
            "resolution_gate", "lake", "pair", "real", "scramble", "ratio", "verdict",
            "scored", "total"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # --- console pivot: ratio per lake per combo, delta vs all-on baseline ---
    print("\n" + "=" * 74)
    print(f" SUMMARY  --  best-of-grid real/scramble ratio    ({ENGINE} engine)")
    print(" delta vs baseline 111 in parentheses;  CS/SF/RG: Y=on, -=off")
    print("=" * 74)
    base = table.get("111", {})
    print("combo CS SF RG " + "".join(f"{l[:18]:>20}" for l in lakes_seen))
    for lab in sorted(table, key=lambda s: (s != "111", s)):
        st = dict(zip(TOGGLES, [c == "1" for c in lab]))
        cells = ""
        for l in lakes_seen:
            v = table[lab].get(l, "")
            try:
                txt = f"{float(v):.2f}"
                if lab != "111" and base.get(l):
                    txt += f" ({float(v) - float(base[l]):+.2f})"
            except (ValueError, TypeError):
                txt = str(v)
            cells += f"{txt:>20}"
        flags = f"{'Y' if st['common_support'] else '-'}  " \
                f"{'Y' if st['scale_flag'] else '-'}  " \
                f"{'Y' if st['resolution_gate'] else '-'}"
        print(f"{lab}  {flags} {cells}")

    print(f"\n[ablate] CSV  -> {csvpath}")
    print(f"[ablate] logs -> {LOGDIR}")
    print(f"[ablate] done. Send me filter_ablation_{ENGINE}.csv (or paste the SUMMARY table).")


if __name__ == "__main__":
    main()