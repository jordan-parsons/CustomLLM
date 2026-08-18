# Hadwiger–Nelson attack — final report

**Bottom line: Objective A was not achieved. Objective B was not achieved.**
No 5-chromatic unit-distance graph below 509 vertices was found, and no
6-chromatic unit-distance graph was found. The record stands where it stood:
509 vertices (Parts, 2020).

What exists instead is a working, adversarially-tested pipeline; a verified
reproduction at 510; one minor new result; several substantive negative results
that constrain where the record can live; and a documented list of seven barren
strategies with the measurements that killed each.

---

## 1. The seven required items, for the one promoted claim

The claim: **the 510-vertex graph is a unit-distance graph in the plane with
χ = 5 exactly.**

| # | Required | Status | Artifact |
|---|---|---|---|
| 1 | Vertex list in exact coordinates | present | `artifacts/heule510/` + `data/CNP-SAT/vtx/510.vtx`, 510 points in ℚ(√3,√5,√11), coord hash `5cc16bb4faf7dcf7…` |
| 2 | Edge list confirmed by exact arithmetic | present | 2504 edges; certified detector, brute-force all-pairs, and Adversary 1's independent implementation all agree |
| 3 | CNF | present | `artifacts/heule510/heule510.k4.cnf` (2040 vars / 10019 clauses) |
| 4 | Solver proof | present | kissat DRAT, 7,160,065 B, sha256 `71dc6bcbb371ebb8…`; archived gz 1,984,991 B, sha256 `4c2c07760d195942…` |
| 5 | Checker verdict on that proof | present | drat-trim **VERIFIED** |
| 6 | Literature check | present, **with a stated weakness** | 509 (Parts 2020) confirmed at *secondary-source strength only* — every primary source is egress-blocked |
| 7 | Three independent adversary reports | present | `reports/ADVERSARY_{1,2,3}.md`, hashes in `reports/MANIFEST.txt` |

k = 5 is SAT with an independent model check that re-derived all 2504 edges from
exact coordinates. So χ = 5 exactly, not merely ≥ 5.

**This is a reproduction, not a result.** It is one vertex worse than the record
and it is not new — it is the already-known HeuleGraph510. The referee promoted it
to the leaderboard as a pipeline validation and explicitly refused it as a record.

---

## 2. Milestones

| | Target | Outcome |
|---|---|---|
| **M0** | Exact arithmetic + detection | **PASSED.** Moser spindle and Golomb: k=3 UNSAT drat-trim VERIFIED, k=4 SAT independently model-checked. Certified detector agrees with brute-force exact on every fixture. Adversarial near-unit pairs (\|d²−1\| ≈ 1e-10, 3e-11, which a 1e-9 tolerance accepts) correctly rejected. |
| **M1** | Reproduce de Grey's 1581 | **BLOCKED, not skipped.** arXiv:1804.02385 is egress-blocked. H confirmed (hexagon side 1 + centre, 7v/12e) and J confirmed with an exact closed form (`{(a,b) ∈ ℤ² : a²+ab+b² ≤ 7}` in Eisenstein coordinates, 31 pts / 72 unit edges, verified in integer arithmetic). K/L rotation angles and W/M/N **not found**. The spec warns that guessing the generators is the single most likely silent failure; they were not guessed. |
| **M2** | Reproduce the record | **PASSED at 510, not 509.** Parts' coordinates are not obtainable on any reachable host. |
| **M3** | Beat 509 | **NOT ACHIEVED.** 187 full deletion passes + 64 orbit minimisations, 180,038 search solver calls, nothing below 510. |
| **M4** | χ ≥ 6 | **NOT ATTEMPTED at scale.** Open problem; nothing found; no claim made. |

**M1 substitute, honestly labelled.** The pipeline reproduces the *published*
Heule graphs, which are themselves derived from de Grey's construction, and the
independently re-derived exact edge sets match the published edge lists exactly —
510/2504, 517/2579, 553/2722, 403/2112, 199/888, zero discrepancies in either
direction. That validates arithmetic, parser and detector jointly. It is not the
M1 the spec asked for.

---

## 3. Corpus and leaderboard

**Leaderboard (verified proofs only, by construction of the SQL query):**
one row — 510 vertices, drat-trim VERIFIED.

**5-chromatic (k=4 UNSAT):** 510, 517, 529, 553, 610, 633, 803, 826, 874 — all in
ℚ(√3,√5,√11), all sharing one coordinate system (union = 2306 distinct points /
13569 exact unit edges).

**4-colourable traps, identified so others don't waste time:** L403, S199, G2167
(ℚ(√3,√11)); T721 (ℚ(√2,√3)). These sit in the same repository as the 5-chromatic
graphs and are *not* witnesses.

**Ambient pools built:** 32, all exact, all round-trip verified, largest 14,189
points. Every pool containing the 510 reproduces exactly 2504 induced edges on
reload.

**Proofs we produced that upstream does not ship:** verified refutations for
**510, 826 and 874**. Upstream ships DRAT only for 517, 529, 553, 610, 633, 803.

---

## 4. New results (both minor, both labelled)

1. **A 510-vertex, 2503-edge 5-chromatic unit-distance graph exists.** Adversary 1
   showed the graph is *not edge-critical*: edge (1,2) is redundant, CaDiCaL UNSAT
   with drat-trim VERIFIED. An edge-count improvement, explicitly not a
   vertex-count record.
2. **The published corpus is uniformly vertex-critical.** Deletion-MUS to fixpoint
   returns 510, 517, 529 and 553 unchanged, and all 510 single-vertex deletions of
   the 510 yield 4-colourable graphs (measured twice, independently). Corollary:
   **Parts' 509 is not a subgraph of Heule's 510** — the two records are
   structurally different graphs, not a nested chain.

---

## 5. Negative results that actually constrain the problem

These are the most useful output of the project.

**(a) Deletion cannot win from published material.** Every published starting
graph is already a deletion fixpoint. Heule and Parts ran this minimisation first.
This **falsifies the spec's §7 premise** that "beating 509 is a minimization
problem, not a construction problem" — that premise silently assumes un-minimised
starting material. From published graphs it is a construction problem.

**(b) The vertex-search basin is deep and one-sided.** 187 full deletion passes
over four structurally different ambient pools:

```
510  ##################################################  (98)
511  ################                                    (32)
512  #########                                           (17)
513  ##########                                          (19)
514  #####                                                (9)
515–519 ######                                           (12)
```

510 is both the **floor and the mode** (52%), with a strictly one-sided tail and
not one pass below it. All four pools behaved identically, so **pool choice is not
the variable** — reallocating between pools is not a lever.

**(c) Symmetry costs vertices here rather than saving them.** The C3-orbit move was
the one move vertex-criticality does not forbid, and it is arithmetically
all-or-nothing (a graph of whole orbits plus the fixed origin has 1+3(k−1)
vertices, so 509 and 510 are unreachable — it either misses or beats). Measured:
64 orbit minimisations, **floor 517**, seven worse than the asymmetric 510. Modes A
(minimise the 550-point closure) and B (complete the 510's partial orbits, then
delete whole orbits) **converge on 517 from opposite directions**, which is
evidence about the object rather than about one search order. The record's shape is
probably not C3-symmetric — this rules out a family, not a point.

**(d) The ambient set is far more rigid than its size suggests.** Only 148 distinct
unit vectors exist across the entire 2306-point pool, and only 21.8% of
sub-diameter vertex pairs of the 510 have their unit-circle intersections inside
the field. This is why the complete 2-neighbour completion is finite and small
(3839 points): it bounds the whole single-vertex substitution search space.

---

## 6. Barren strategies, with the measurement that killed each

| # | Strategy | Why it was killed |
|---|---|---|
| 1 | Single-vertex deletion from any published graph | Provably stuck: k=4 UNSAT core is the entire vertex set; 510/510 deletions 4-colourable |
| 2 | UNSAT-core reduction on already-minimised graphs | The core *is* the whole graph — a no-op |
| 3 | MUS descent over the 2306-point pool encoding | ~50× per-call penalty vs a 510-vertex encoding; **zero runs completed in 28 min** |
| 4 | Uniform-order basin hopping | Structurally cannot escape a critical incumbent: the few added points get deleted first and the pass collapses back |
| 5 | UNSAT-core triage as a promise signal | **0 of 44 cores ever beat the incumbent**; CaDiCaL's assumption core returns nearly all assumptions (518 of 510+8) |
| 6 | Minkowski sums of 4-colourable blocks with H/J | Still k=4 SAT at 5167 points and mean degree 15.7 |
| 7 | C3-orbit minimisation | Floor 517 over 64 samples, both modes agreeing — worse than the asymmetric 510 |
| 8 | Orbit search on the 985-orbit pool | One pass consumed the entire 1200 s budget to reach 1804 vertices; cost grows with pool size, signal does not |
| — | Voronov series 1 / 2 (3877 / 64513 vertices) | Deprioritised, not killed: an order of magnitude larger, and their own authors did not beat 509 from them |

---

## 7. Soundness: what the adversaries broke, and what was fixed

**No soundness alarm in the mathematical sense ever fired.** No adversary found an
edge that is not exactly unit distance, and no proof failed its checker. But
Adversary 2 found two genuinely reachable holes in the *toolchain*, and the loop
was halted to fix them.

**CRITICAL — the proof checker could be fooled.** `check_proof` returned VERIFIED
for a *satisfiable* formula with a 0-byte proof. drat-trim has a parse-time path
printing `c trivial UNSAT` / `s VERIFIED` **before examining the proof at all**, and
ordinary CNF malformations drive it there — a comment after the header, an inflated
clause count, a missing trailing `0`. Reproduced end to end. My own `--relaxed` flag
on kissat was suppressing the header-mismatch report that would have caught it. So
ground rule 2 was silently degrading to "the solver said UNSAT."
*Fixed:* strict DIMACS validation before the checker runs; 0-byte proofs refused;
`trivial UNSAT` mapped to `REJECTED_TRIVIAL_UNSAT`, never VERIFIED; verdict lines
matched anchored at line start (drat-trim echoes file paths into stdout, so an
unanchored grep was forgeable); checker exit code must agree.

**MAJOR — float was deciding the edge set.** The float prefilter could *miss* an
exactly-unit edge at coefficient scale ~9.5e9 with all coordinates inside |x| < 1.26,
and grid bucketing broke at scale 2²⁵ because `math.floor` ran on a float. Reachable
by ordinary moves: composing the spindle rotation grows denominators like 6ⁿ.
*Fixed:* `detect_edges_certified` is float-free — certified rational enclosures from
integer square roots, exact rational floor for bucketing, a ±2 neighbourhood
provably safe for any enclosure width ≤ 1, and a pair discarded only when the
certified interval provably excludes 1. Precision affects speed, never correctness.
It is also faster than brute force (3.8 s vs 12.2 s on 510 points).

**Also fixed:** `UDGraph`'s `edges=` parameter (an arbitrary edge list gave m=0 with
an identical `coord_hash`, the catalog's primary key); the minimizer never validated
its symmetry-breaking clique; and two proof-metadata defects from Adversary 1 (the
hash described a different file than `proof_path` named; a SAT result carried a
phantom `proof_bytes`).

**Re-verified after all fixes:** M0 ALL PASS; the 510 re-derives to the same 2504
edges under the certified detector; k=4 UNSAT with the **identical** proof hash
`71dc6bcb…`. No prior result was invalidated.

**Independent cross-validation.** Our drat-trim verifies *Heule's own* published
proofs — 517, 553, 610, 633, 803 all VERIFIED with matched CNFs — while every
deliberately mismatched pairing returns NOT VERIFIED. All six were re-verified
through `lrat-check`, a different checking algorithm, and four negative controls
(corrupted, truncated, cross-graph, corrupted-hint) were all correctly rejected.
That negative control is what makes the positive verdicts mean anything.

---

## 8. Limitations and open uncertainties, stated as uncertainties

1. **The literature check rests on zero primary sources.** arxiv.org, mathworld,
   cs.cmu.edu, researchgate, zenodo, michaelnielsen.org and semanticscholar are all
   egress-blocked. "509 is the record" and "no 6-chromatic unit-distance graph is
   known" are **inferred from corroborating secondary summaries**, not
   primary-verified. Since no record is being claimed, this is disclosed rather than
   disqualifying — but it would need re-checking before any headline claim.
2. **Unresolved edge-count discrepancy.** Secondary sources quote the 510 graph at
   2508 edges and 553 at 2720; our exact arithmetic gives 2504 and 2722. Ours is
   authoritative for *these* point sets, derived from coordinates alone. The
   bookkeeping question cannot be closed without primary sources. Labelled
   unresolved, not resolved.
3. **The 510's attribution is inconclusive.** It has no citable publication: git
   commit `a65ee28`, 2019-08-08. MathWorld exposes `GraphData["HeuleGraph510"]` but
   its Heule-spindle page places 510 in the *Parts* family. Cite it as a git commit,
   never as a literature record.
4. **Nested-radical constructions are outside the arithmetic layer.** Voronov et
   al.'s series-2 rotation data uses complex numbers and nested radicals such as
   `Sqrt[5 − 3·Sqrt[2] + Sqrt[3] + 3·Sqrt[6]]`, which no multiquadratic field can
   express. A real representational limitation, not a bug.
5. **The searches are evidence about the search, not theorems about the pools.**
   187 + 64 samples of a combinatorial space this size is a thin slice. "Not
   reachable by these moves at these perturbation sizes" is the honest claim; "does
   not exist" is not.

---

## 9. What I would try next, in order

1. **Get primary sources.** The single highest-value unblock. Parts' 509
   coordinates would give a second, structurally different starting graph — and
   since 509 is not a subgraph of 510, it is a genuinely different basin.
2. **Extend the arithmetic layer beyond multiquadratic fields** to handle nested
   radicals, opening the Voronov constructions.
3. **Much larger perturbations.** Everything sampled here added 3–45 points. The
   basin may simply be wider than that.
4. **Cube-and-conquer for k=5** if Objective B is ever attempted seriously; nothing
   in this project moved toward χ ≥ 6.

---

## 10. Reproducing everything here

```
python3 tests/test_m0.py                 # M0 end to end
python3 verify_candidate.py <tag> <idx>  # full 7-step evidence chain
python3 build_dashboard.py               # regenerate the dashboard
python3 run_search6.py                   # vertex basin hop
python3 run_orbit2.py                    # C3-orbit search
```

Catalog: `catalog/hn.sqlite` — the leaderboard query reads only rows with
`verdict='UNSAT' AND checker_verdict='VERIFIED'`, so an unverified solver answer
cannot reach it by construction.
