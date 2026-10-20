#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# logify2d.py  --  2D PERIOD ENGINE scalarizer (pairs).
#
# A 2D record is a PAIR of raw positive quantities on the SAME object. This stage
# takes ln(x1), ln(x2) at test time and stores them. Same contract as 1D logify:
#   * NO modulus, NO x0 in the config (asserted at load; keys-not-prose check).
#   * NO sector normalization accepted (Form C guard) unless explicitly allowed.
#   * Field resolution identical to the 1D engine (breadth-first nested, or dotted).
#   * Output carries klghs_lnx1, klghs_lnx2 + provenance. No modulus anywhere.
#
# configs2d_period/logify2d.json maps each PAIR DOMAIN to its two fields:
#   { "domains": { "velocity_luminosity": {
#         "field1": "vT_kms", "field2": "luminosity_lsun",
#         "combine": "identity", "target_pair": [6,8],
#         "description": "..." } } }
# ==============================================================================
import json, math, os, sys
from pathlib import Path

MAX_DEPTH = 6
STRICT = os.environ.get("KLGHS_PERIOD_STRICT", "1") == "1"
ALLOW_NORM = os.environ.get("KLGHS_PERIOD_ALLOW_NORM", "0") == "1"

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs2d_period" / "logify2d.json"
IN_DIR = ROOT / "lakes2d_period" / "inputs_promoted"
OUT_DIR = ROOT / "lakes2d_period" / "logified"

_report = {}
def _note(dom, route): _report.setdefault(dom, {"ok":0,"fail":None}); _report[dom]["ok"]+=1
def _fail(dom, reason, detail): _report.setdefault(dom, {"ok":0,"fail":None}); _report[dom]["fail"]=(reason,detail)


def _dotted(rec, path):
    cur = rec
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def resolve_field(rec, field):
    if not field:
        return None
    if "." in field:
        return _dotted(rec, field)
    frontier = [rec]; depth = 0
    while frontier and depth <= MAX_DEPTH:
        nxt = []
        for obj in frontier:
            if not isinstance(obj, dict):
                continue
            if field in obj and obj[field] is not None and not isinstance(obj[field], dict):
                return obj[field]
            for v in obj.values():
                if isinstance(v, dict):
                    nxt.append(v)
        frontier = nxt; depth += 1
    return None


def load_config():
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    banned = {"k_geo", "modulus", "x0"}
    hit = banned & set(cfg.keys())
    for dom, e in cfg.get("domains", {}).items():
        if isinstance(e, dict):
            hit |= (banned & set(e.keys()))
    if hit:
        raise SystemExit(f"[logify2d] ABORT: banned computational key(s) {sorted(hit)} in "
                         f"config. The period engine carries no modulus/x0. Remove them.")
    return cfg["domains"]


def positive(v):
    try:
        x = float(v)
        return x if (x > 0 and math.isfinite(x)) else None
    except (TypeError, ValueError):
        return None


def logify_record(rec, dom, entry):
    if not ALLOW_NORM:
        meta = rec.get("meta", {}) or {}
        if meta.get("sector_normalized"):
            _fail(dom, "SECTOR_NORMALIZED", "source is sector-normalised (Form C) -- forbidden")
            return None
    v1 = positive(resolve_field(rec, entry["field1"]))
    v2 = positive(resolve_field(rec, entry["field2"]))
    if v1 is None or v2 is None:
        _fail(dom, "NO_PAIR", f"missing/non-positive field(s): "
              f"{entry['field1']}={v1}, {entry['field2']}={v2}")
        return None
    _note(dom, "ok")
    return {
        "entity_id": rec.get("entity_id"),
        "domain": rec.get("domain", dom),
        "klghs_lnx1": math.log(v1),
        "klghs_lnx2": math.log(v2),
        "target_pair": entry.get("target_pair"),
        "provenance": rec.get("meta", {}),
    }


def main():
    domains = load_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_DIR.exists():
        raise SystemExit(f"[logify2d] no input dir {IN_DIR}")
    for src in sorted(IN_DIR.glob("*_promoted.jsonl")):
        out = OUT_DIR / (src.stem.replace("_promoted", "") + "_logified.jsonl")
        n_in = n_out = 0
        with open(src, encoding="utf-8") as fh, open(out, "w", encoding="utf-8") as wf:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                n_in += 1
                rec = json.loads(line)
                dom = rec.get("domain")
                if dom not in domains:
                    continue
                res = logify_record(rec, dom, domains[dom])
                if res:
                    wf.write(json.dumps(res) + "\n"); n_out += 1
        print(f"  logify2d {src.name}: {n_in} -> {n_out}")
    print("\n  DISPATCH REPORT")
    aborted = False
    for dom, info in _report.items():
        if info["fail"]:
            reason, detail = info["fail"]
            print(f"    [{dom}] FAIL {reason}: {detail}")
            if STRICT and reason == "SECTOR_NORMALIZED":
                aborted = True
        else:
            print(f"    [{dom}] ok={info['ok']}")
    if aborted:
        raise SystemExit("[logify2d] ABORT under STRICT: Form C guard fired.")


if __name__ == "__main__":
    main()
