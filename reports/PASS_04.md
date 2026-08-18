# Pass 4 report — the C3-orbit move

## Hypothesis under test
Constructor C1's conjecture: since the 510 is nearly C3-symmetric (R120 maps 482 of
510 vertices back) and 510 = 3 x 170, "a symmetric graph on 3k <= 507 is a very
plausible shape for the record." The move is attractive because vertex-criticality
does not forbid it: criticality kills orbit deletion *from the 510 itself*
(G-{p,Rp,R2p} is a subgraph of G-p, hence 4-colourable), but says nothing about a
larger symmetric graph where added points can compensate for a removed one.

It is also arithmetically all-or-nothing. A graph of whole C3 orbits plus the fixed
origin has exactly 1+3(k-1) vertices, so the reachable sizes are 517, 514, 511,
**508**, 505, 502 — and 509 and 510 are unreachable. The move cannot tie the record;
it either misses or beats it.

## Result: HYPOTHESIS REFUTED

| mode | pool | minimisations | distribution |
|---|---|---|---|
| A (minimise whole pool) | P1b_510_C3 (550 pts, 184 orbits) | 18 | 517 x11, 520 x5, 550 x1 |
| B (complete 510's orbits, then orbit-delete) | both | 35 | 517 x28, 520 x5, 550 x2 |
| A | P3_ncD6_deg3 (2953 pts, 985 orbits) | 1 | 1804 (too slow: 481 calls in 1200 s) |

**53 orbit minimisations, floor 517, zero below 510.** The C3-orbit basin bottoms
out at 517 — seven vertices *worse* than our asymmetric 510 and nine above the 508
a record would need.

## What this actually tells us
**Symmetry costs vertices here rather than saving them.** The 510 is not symmetric
(only 482 of 510 vertices map back under R120). Forcing full C3 symmetry — either by
minimising the closure, or by completing the 510's partial orbits and then deleting
whole orbits — lands on 517 every time. The asymmetric graph beats the symmetric
optimum reachable from this closure. That is a clean refutation of the conjecture,
and it is more informative than another barren vertex-search round: it says the
record's shape is probably *not* symmetric, which rules out a whole family.

Both modes agree on the same floor from different directions, which is the useful
part. Mode B starts from the 510 and adds only the 40 completion points; mode A
starts from all 550. Converging on 517 from both sides is evidence about the object,
not about one search order.

## Killed this pass
- **C3-orbit minimisation over the 510's closure.** 53 samples, floor 517, both
  modes agreeing. Killed as a route to <= 508.
- **Orbit search on P3_ncD6_deg3 (985 orbits).** Not productive at this scale: one
  pass consumed the entire 1200 s budget and reached only 1804 vertices. An orbit
  pass costs |orbits| solver calls on a |pool|-vertex encoding, so cost grows with
  the pool while the useful signal does not. Killed.

## Standing count of barren strategies
1. Single-vertex deletion from any published graph — provably stuck (criticality).
2. UNSAT-core reduction on minimised graphs — core is the whole vertex set.
3. MUS descent over the 2306-point pool encoding — ~50x per-call cost penalty.
4. Uniform-order basin hopping — structurally cannot escape a critical incumbent.
5. UNSAT-core triage as a promise signal — 0 of 44 cores ever beat the incumbent.
6. Minkowski sums of 4-colourable blocks with H/J — still 4-colourable at 5167 pts.
7. **C3-orbit minimisation — floor 517, worse than the asymmetric 510.**

## Assessment
This is a plateau. Two structurally different searches have now each bottomed out:
the vertex search at 510 over 66 full passes (510 both floor and mode, one-sided
tail), and the orbit search at 517 over 53 minimisations. No generator has produced
anything below 510.
