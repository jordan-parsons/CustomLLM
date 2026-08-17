# Hadwiger-Nelson toolchain - build status

## Environment deltas from spec
| Spec assumes | Reality | Resolution |
|---|---|---|
| kissat / cadical / drat-trim installed | absent | built from source in `vendor/` |
| `nauty`/`pynauty` for canonical labeling | pynauty wheel fails to build | WL-hash bucketing + exact VF2 confirmation (never dedups without proof of isomorphism) |
| arXiv:1804.02385 readable | arxiv.org egress-BLOCKED | M1 blocked; de Grey generators NOT reconstructed from memory |
| Published graph data reachable | cs.cmu.edu, zenodo, mathworld BLOCKED | obtained equivalent data from GitHub (marijnheule/CNP-SAT) |
| python-flint | installable | installed 0.9.0 (Fraction used for the reference layer) |
| Jenkins matrix orchestration | single 4-core container | multiprocessing pool, 4 workers |

## Milestones
- **M0 PASSED.** Exact multiquadratic arithmetic; detector validated against
  brute-force exact all-pairs on every fixture; Moser spindle and Golomb graph
  k=3 UNSAT (drat-trim VERIFIED) and k=4 SAT (independent model check).
  Adversarial near-unit pairs (|d^2-1| ~ 1e-10, 3e-11) correctly rejected.
- **M1 BLOCKED.** Cannot read arXiv:1804.02385. Spec explicitly warns against
  reconstructing de Grey's generators; not attempted. See "M1 substitute".
- **M1 substitute (partial credit, honestly labelled).** The pipeline reproduces
  the *published* Heule graphs, which are themselves derived from de Grey's
  construction, and the independently re-derived exact edge sets match the
  published edge lists exactly (510/2504, 517/2579, 553/2722, 403/2112, 199/888;
  zero discrepancies in either direction). This validates arithmetic + parser +
  detector jointly but is NOT the M1 the spec asked for.
- **M2 PASSED (at 510, not 509).** Parts' 509 coordinates are not publicly
  available on any reachable host. The smallest available published graph is
  Heule's 510. Verified chi = 5: k=4 UNSAT, 7.16MB DRAT, drat-trim VERIFIED,
  sha256 71dc6bcbb371ebb8...; k=5 SAT with independent model check.

## Corpus (all verified k=4 UNSAT via pysat search solve; 510 fully proof-verified)
510, 517, 529, 553, 610, 633, 803, 826, 874 - all in Q(sqrt3,sqrt5,sqrt11),
all sharing one coordinate system (union = 2306 distinct points, 13569 edges).
4-colourable building blocks (NOT 5-chromatic): L403, S199, G2167 in
Q(sqrt3,sqrt11); T721 in Q(sqrt2,sqrt3).

## Key negative results
1. **The 510-vertex graph is vertex-critical.** Its k=4 UNSAT core is all 510
   vertices and all 510 single-vertex deletion tests return 4-colourable.
   Therefore Parts' 509 is not a subgraph of it and no single deletion helps.
2. The Voronov et al. `series 2` rotation data uses **nested radicals and
   complex numbers** (e.g. Sqrt[5 - 3*Sqrt[2] + Sqrt[3] + 3*Sqrt[6]]), which the
   multiquadratic representation genuinely cannot express. Those constructions
   are outside the current arithmetic layer - a real limitation, not a bug.
3. Voronov series 1 = 3877v/26814e, series 2 = 64513v - both far larger than 510.

## Record target
Current world record: 509 (Parts 2020), confirmed still standing as of Aug 2026.
**A record requires <= 508.** 509 would only tie.

## Rotation generators of the published point set (recovered empirically)
All exact in Q(sqrt3,sqrt5,sqrt11); each satisfies cos^2+sin^2 == 1 exactly, and
`Rotation.__init__` asserts that, so a wrong value raises rather than corrupts.

| name | angle | cos | sin | role |
|---|---|---|---|---|
| theta0 | arcsin(1/(2 sqrt3)) ~ 16.7787 deg | sqrt33/6 | sqrt3/6 | **atomic** rotation; maps far more points back into the published sets than alpha |
| alpha | 2*theta0 | 5/6 | sqrt11/6 | the classical Moser/de Grey spindle angle |
| beta | 2*arcsin(1/4) | 7/8 | sqrt15/8 | **where sqrt5 enters**; maps 94/510 of the 510-graph but only 1/199 of S199 |
| hex | k*60 deg | +-1, +-1/2 | 0, +-sqrt3/2 | triangular-lattice symmetry |

Interpretation: beta is the generator the *small record* graphs use and de Grey's
originals do not, which is why the 510-family needs a degree-8 field while
de Grey's S199/L403/G2167 live in the degree-4 field Q(sqrt3,sqrt11).

## M1 reconstruction status (why it is genuinely blocked, not skipped)
- **H CONFIRMED**: hexagon of side 1 plus centre, 7 vertices, 12 edges.
- **J CONFIRMED** with an exact closed form, checked in integer arithmetic:
  J = {(a,b) in Z^2 : a^2 + ab + b^2 <= 7} in Eisenstein coordinates.
  31 points, 72 unit edges; contains exactly 13 copies of H and their union is J.
- **K, L: counts only.** |K| = 31+31-1 = 61 and |L| = 61+61-1 = 121 are consistent
  with spindling about a shared vertex, but those counts do NOT pin the rotation
  angles - any generic rotation reproduces 61/121. Exact angles NOT FOUND.
- **W, M, N: NOT FOUND.** Without W's definition, M (1345) and N (20425) cannot be
  reconstructed, and therefore neither can the 1581-vertex reduction.
Conclusion: M1 as specified is not achievable on this host. Reconstructing the
missing angles by guesswork is exactly the silent-failure mode the spec warns
about, so it was not attempted.

## Literature check (Objective A gate)
- Smallest known 5-chromatic planar unit-distance graph: **509 vertices, 2442
  edges (Parts 2020)**. Still the record as of Aug 2026.
- Corroborated independently by MathWorld and by the Aug 2026 Haugland paper
  (2131-vertex Moser-spindle-free graph), which explicitly states it does not
  improve the unrestricted record.
- Nothing at or below 509 found. No 6-chromatic unit-distance graph is known.
- CAUTION recorded: adjacent problems (two-distance, odd-distance graphs) do
  reach chromatic number 6 and must not be conflated with the unit-distance case.

## Vertex-criticality of the whole published corpus (measured, not assumed)
Randomised deletion-MUS to fixpoint on each published 5-chromatic graph returns
the graph itself:

| start | result | conclusion |
|---|---|---|
| 510 | 510 | vertex-critical |
| 517 | 517 | vertex-critical |
| 529 | 529 | vertex-critical |
| 553 | 553 | vertex-critical |

Plus the exhaustive per-vertex scan on 510: all 510 single-deletion tests return
4-colourable, and the k=4 UNSAT core is the entire vertex set.

**Consequence.** Every published starting graph is already a local minimum under
vertex deletion. Heule and Parts already did this minimisation, so no amount of
deletion-only search can improve on them. The ONLY route to <= 508 from this
corpus is to first ENLARGE the vertex set with ambient points and then delete
more than we added (basin hopping). That reframes Objective A from a
minimisation problem into a *construction* problem, contradicting the spec's
section 7 claim that "beating 509 is a minimization problem, not a construction
problem" - at least when starting from already-minimised published graphs.
