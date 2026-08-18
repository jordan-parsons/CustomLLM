# Pass 6 — the exhaustive substitution search

## What was asked
Criticality closed every route that ends in "delete vertices from published
material" (all nine published graphs are deletion fixpoints, measured). Progress
therefore requires points that are *not* in the published sets. The smallest such
move is a single substitution:

        (510 - v) + w       v in the 510, w outside it.

Unlike everything before it, this was run **exhaustively, not sampled**.

## Two proofs that made it tractable

**The prune.** Adding one vertex w to a 4-colourable graph H yields a
non-4-colourable graph **iff** every proper 4-colouring of H assigns all four
colours to N(w) n H — which requires |N(w) n H| >= 4. Since 510 - v is
4-colourable by criticality, deg_510(w) >= 4 is necessary, and >= 5 when v is
itself a neighbour of w. Candidates below that are discarded **with a proof**.

Measured effect over the deg>=2 neighbour-completion pool (4349 points):

| deg into the 510 | count | status |
|---|---|---|
| 2 | 2637 | discarded with proof |
| 3 | 539 | discarded with proof |
| 4–10 | **663** | must be tested |

**The batching.** For fixed v, adding ALL surviving candidates at once: if
(510 - v) + W is 4-colourable then so is (510 - v) + w for every w in W, since the
latter is a subgraph and 4-colourability is inherited. One SAT answer clears 663
candidates.

Honest note: this helped far less than predicted. Only 39,780 pairs were cleared
by batch SAT, because adding all 663 candidates is almost always UNSAT — the full
pool is UNSAT, so of course it is. The drill-down path carried the search, which is
why it took ~10,000 s per worker rather than the ~15 min estimated.

## Result

**337,142 of 338,130 substitutions ruled out. Eight survive.**

| # | w | v | deg_w | edges | isomorphic to the 510? |
|---|---|---|---|---|---|
| 0 | 997 | 364 | 7 | 2505 | **no** |
| 1 | 4145 | 504 | 5 | 2504 | **no** |
| 2 | 525 | 357 | 8 | 2506 | **no** |
| 3 | 971 | 373 | 7 | 2505 | **no** |
| 4 | 4047 | 487 | 7 | 2504 | **no** |
| 5 | 645 | 354 | 7 | 2505 | **no** |
| 6 | 553 | 370 | 7 | 2505 | **no** |
| 7 | 677 | 374 | 8 | 2506 | **no** |

**Eight new 510-vertex 5-chromatic unit-distance graphs.** Non-isomorphism was
confirmed by exact VF2 against the original, not by the WL invariant — they differ
in degree sequence and in edge count (2504, 2505, 2506). A substitution changes the
vertex set by construction, but that alone would not make it a different *graph*;
the VF2 check is what licenses the claim.

## But: all eight are themselves vertex-critical

24 runs (8 graphs x 3 random deletion orders): **zero vertices removed anywhere.**

So the substitution neighbourhood of the 510 is *entirely* critical. Reaching 509
is not blocked by one stubborn graph — it is blocked by a whole neighbourhood of
them. This is the strongest negative result the project has produced, because it is
exhaustive over the pool rather than statistical:

> **No single-point substitution of the 510, over the complete degree>=2
> neighbour-completion pool, yields a 5-chromatic graph that reduces below 510.**

## Engineering fault found and fixed
The first run of the reduction job died after 4 of 24 runs: each of 4 workers
independently rebuilt the 4349-point pool with the certified detector, and four
concurrent copies of the exact-arithmetic geometry exhausted memory. Workers never
needed the geometry — an induced subgraph's edges are determined by the pool's
already-certified integer adjacency. Pool now built once in the parent; only the
adjacency is passed. Same lesson as the in-loop detection fix, applied to process
startup.

## Standing barren list (10)
1. Single-vertex deletion from any published graph — all nine are fixpoints
2. UNSAT-core reduction on minimised graphs — core is the whole vertex set
3. MUS descent over the 2306-point pool encoding — ~50x per-call penalty
4. Uniform-order basin hopping — cannot escape a critical incumbent
5. UNSAT-core triage as a promise signal — 0 of 44 cores beat the incumbent
6. Minkowski sums of 4-colourable blocks with H/J — still 4-colourable
7. C3-orbit minimisation — floor 517, both modes converging
8. Orbit search on the 985-orbit pool — cost grows, signal does not
9. Large perturbations (62–299 points) — monotonically worse, 0/98 reached 510
10. **Single-point substitution — exhaustive over the pool; 8 new graphs, all critical**

## What the eight graphs are worth
They do not advance Objective A. They are, as far as the (egress-limited)
literature check can tell, previously unrecorded 510-vertex 5-chromatic
unit-distance graphs, and they are catalogued with exact coordinates. Any claim of
novelty is weak — it rests on secondary sources — so they are recorded as "not
found in reachable literature", not as new discoveries.
