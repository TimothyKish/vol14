# Referee Briefing — S2 and L1_GWTC Rebuilds Complete

**To:** Mondy Aurora Kish  (cc: Lyra)
**From:** Atlas
**Date:** Vol 14 rebuild campaign
**Subject:** Both Vol 13 pre-registered lake rebuilds built, audited, and closed. Neither locks. Both honest.

---

## Summary

The two lakes filed for rebuild in Volume 13 are complete. Both were built under the strict
I/O contract, both passed the fallback audit (no synthetic can wear the mask of empirical),
both had at least one real gate bug caught and corrected before promotion, and both returned
honest below-bar results. The defects the rebuilds existed to fix are fixed. Neither lake
locks a register — and that is the correct, publishable outcome.

---

## S2 — Stellar Kinematics (Gaia DR3)

**The thread being closed:** Vol 11 reported s2 locking at 15/pi (+98). Vol 12 diagnosed it as
Form C — a sector-normalization artifact. Vol 13 pre-registered a raw-velocity rebuild.

**Built:**
- Raw transverse velocity only. Sector normalization permanently absent (Erratum 4a honored).
- 5-sigma parallax gate AND 5-sigma proper-motion gate on the **covariance-propagated** PM
  error (using pmra_pmdec_corr, per the pre-registration — not naive quadrature). The build
  aborts if pmra_pmdec_corr is absent rather than silently assuming rho=0.
- DR3 parallax zero-point (-17 uas) applied explicitly and flagged; the field is no longer a
  no-op rename.
- 72,000 raw (36 chunks x 2k, server-capped during the DR4 transition) -> 69,078 after strict
  gates (4% dropped, believable).

**Gate bug caught and fixed:** the original build printed a hardcoded `M/N = 1.1082 [PASS]` —
a status line that could not fail, the same pattern as the Vol 1 Listing 14.1 erratum. Replaced
with a gate that COMPUTES M/N from the built data and can return FAIL. On the real data it
computes M/N = 86.9 at register 2/pi — resolves cleanly (register 2 has a tiny period; 3.26
decades is ample).

**Bouncer hardened:** promote rejects present-but-null values (None/NaN/inf/bool), not just
missing keys — closing the hole where a null val_raw could pass a "field exists" check.

**Result:** shape FILLED (a clean unimodal stellar velocity distribution, no placeholder spike),
best resolvable 6/pi at excess 3.7 — **below bar**. The old 15/pi "signal" is disproven: on raw
velocities, one honest population, there is no register above noise. The artifact is gone and
nothing real replaces it.

---

## L1_GWTC — Black Hole Ringdown (LVK measured QNM)

**The thread being closed:** Vol 13 found the old lake's f_ring_hz gave 81/83 events below the
physically-impossible non-spinning Kerr floor — the wrong frequency observable entirely.

**Built:**
- Source changed to measured fundamental quasi-normal mode f_220 from LVK / pyRing posteriors —
  not the merger-catalog peak frequency, not a GR-predicted value.
- 22 events with genuine measured f_220 extracted, named, with remnant mass and final spin.
- BNS/NSBH excluded by construction (mass floor). Bouncer present-AND-valid.

**Gate bug caught and fixed:** the original resolution gate divided log-span by the
decades-required quantity (N^2 x 0.0216) instead of the register period, and checked against 1.0
instead of the 2.67 annulus threshold — printing PASS at a real M/N of 1.21 (which is
background-limited). Corrected to compute true M/N against the right threshold.

**Kerr gate did real work — one exclusion, named:** of 22 events, **GW190512at** fell below the
non-spinning floor (f_220 = 220 Hz vs floor 268 Hz, ratio 0.82) and was excluded. This is a
low-SNR event with a broad, prior-influenced ringdown posterior — a marginal measurement, not a
Kerr violation. One outlier from a known-faint event is categorically different from the old
lake's systemic 81/83; it confirms the new observable is correct and the gate discriminates.
21 events promoted.

**Result:** shape CLUMPED (11 empty interior bins — this is n=21 sparsity, not composite
banding; inflation 1.02 confirms the span is honest), best resolvable 4/pi at excess 0.2 —
**below bar, essentially zero.** The lake is resolution-limited by sample size.

**Honest standing:** the strong-field ringdown test now runs on the CORRECT observable and
passes the Kerr-consistency gate (21/22). It cannot resolve a register because 21 events across
~1 decade is too few. Deferred to O4/O5, which will supply the loud events required. The old
defective lake could never have reached even this honest limit.

---

## What both rebuilds demonstrate

1. **The defects are fixed.** Form C gone from s2; wrong-observable gone from l1_gwtc.
2. **The gates compute and can fail.** Two hardcoded/miscoded PASS statements were caught and
   replaced before promotion. Neither lake carries a status line that cannot fail.
3. **Nothing locked.** s2 below bar, l1_gwtc below bar. We followed the data.
4. **The rebuilds succeeded at their actual purpose** — not to make the tests lock, but to make
   them runnable on honest, correct observables. Both now are. Both say no. That is a result.

---

## For the referee's ruling

- Both lakes are proposed as **closed** for Vol 14: s2 as a disproven-artifact null, l1_gwtc as
  a corrected-observable resolution-limited null.
- The GW190512at exclusion is proposed for the lake provenance metadata, named with its ratio
  and cause, so the 22->21 drop is documented rather than silent.
- Recommend both results carry forward into Vol 14 exactly as measured, with no softening.

The dream said these might lock. The data says they do not. We are filing the data.
