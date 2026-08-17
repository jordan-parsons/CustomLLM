# Referee decision

The referee promotes a claim to the leaderboard only if it carries all seven
required items: exact vertex list, exactly-confirmed edge list, CNF, solver
proof, checker verdict on that proof, literature check, and independent
adversary reports naming their artifacts. It may not promote anything lacking a
verified proof artifact.

---

## Claim 1 — the 510-vertex graph is 5-chromatic

**DECISION: PROMOTED to the leaderboard as a verified reproduction.
NOT promoted as a record, and NOT a new result.**

| Required item | Status |
|---|---|
| exact vertex list | YES — 510 points in Q(√3,√5,√11), `artifacts/heule510/vertices.json`, coord_hash `5cc16bb4faf7dcf7…` |
| edge list confirmed by exact arithmetic | YES — 2504 edges; confirmed by our indexed detector, our brute-force all-pairs exact detector, and independently by Adversary 1's from-scratch implementation |
| CNF | YES — `artifacts/heule510/heule510.k4.cnf` |
| solver proof | YES — kissat, DRAT, 7160065 bytes, sha256 `71dc6bcbb371ebb8…` (checked bytes); archived gz 1984991 bytes, sha256 `4c2c07760d195942…` |
| checker verdict on that proof | YES — drat-trim **VERIFIED** |
| literature check | YES — 509 (Parts 2020) stands; 510 is **worse than the record** |
| independent adversary reports | YES — Adversary 1 (3 checks), Adversary 3 (third-party proof cross-validation) |

**Why not a record.** Adversary 1's Check 3 refuted the record framing outright:
the smallest known 5-chromatic planar unit-distance graph is Parts' 509-vertex /
2442-edge graph (Geombinatorics 29/4:137–166, 2020; arXiv:2010.12665), still
standing as of Aug 2026. Our 510 is one vertex worse **and is not even new** — it
is the previously known HeuleGraph510. Promoted as a pipeline-validating
reproduction only.

**Independent confirmations on record.**
- Adversary 1 wrote a genuinely different encoder (colour-major numbering,
  at-most-one clauses *included* where our pipeline omits them, no symmetry
  breaking, edge set re-derived from geometry rather than read from `510.edge`),
  solved with CaDiCaL: `s UNSATISFIABLE` at k=4, 330,646,444-byte DRAT
  (`cf4affe6…`), drat-trim **VERIFIED**. The checker log shows 11,660 of 13,586
  clauses in the core (86%, so no degenerate sub-formula) and **0 RAT lemmas**.
- Adversary 1 implemented Q(√3,√5,√11) independently, cleared all 1,020
  coordinates to integer vectors over a common denominator D=96 so the unit test
  is an **integer equality with no epsilon in the accept path**, and ran all
  **129,795** pairs exactly: 2504 unit pairs, all 2504 claimed edges exactly
  unit, **zero omissions**, all 510 vertices exactly distinct.
- Adversary 3 verified five of Heule's **own published DRAT proofs** with our
  drat-trim build (517, 553, 610, 633, 803 all VERIFIED), with mismatched
  CNF/proof pairings correctly returning NOT VERIFIED as a negative control.
- Max clique is 3 (no K₄), so the k=4 UNSAT is real combinatorial content and
  not forced by a clique.

## Claim 2 — a 510-vertex, 2503-edge 5-chromatic unit-distance graph exists

**DECISION: PROMOTED as a minor new result, clearly labelled as an edge-count
result, not a vertex-count record.**

Adversary 1 found the 510 graph is **not edge-critical**: deleting edge (1,2)
leaves it non-4-colourable — CaDiCaL UNSAT with drat-trim **VERIFIED**, kissat
agreeing. This strictly strengthens Claim 1 rather than threatening it.

Caveat the referee attaches: an edge-deleted unit-distance graph is a *subgraph*
of a unit-distance graph, which is the standard convention, but it is not a
record of the kind Objective A asks for and must never be reported as one.

## Claim 3 — Objective A (a 5-chromatic graph with < 509 vertices)

**DECISION: NOT PROMOTED. No such graph was found.**

Best verified vertex count remains 510. Requires ≤ 508 to be a record. The
search is not merely unlucky; it is provably stuck in the pure-deletion regime:

- The 510 graph's k=4 UNSAT core is the entire vertex set, and all 510
  single-vertex deletions yield 4-colourable graphs (measured twice
  independently — by us and by Adversary 1's own sweep).
- Deletion-MUS to fixpoint on 510, 517, 529 and 553 returns each graph
  unchanged: the whole published corpus is vertex-critical.

So Heule and Parts already ran the minimisation this project's spec assigns to
M3. Nothing below 509 can be reached by deleting from published material.

## Claim 4 — Objective B (a 6-chromatic unit-distance graph)

**DECISION: NOT PROMOTED. Nothing was found, nothing was attempted at scale.**
No 6-chromatic unit-distance graph in the plane is known and this project did not
change that. Recorded caution: adjacent problems (two-distance graphs,
odd-distance graphs, spheres, higher dimensions) *do* attain chromatic number 6,
and must not be conflated with the unit-distance case in the plane.

## Soundness alarms

**None raised.** No adversary found an edge that is not exactly unit distance, and
no proof failed its checker. Two **metadata** defects were found by Adversary 1
and fixed (proof hash naming a different file than it described; proof byte count
retained on a SAT result). Neither could produce an unsound mathematical claim,
but both would have made a claim harder to audit, so the loop was not treated as
clean until they were fixed and the affected verdicts regenerated.
