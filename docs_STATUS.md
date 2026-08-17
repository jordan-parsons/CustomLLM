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
