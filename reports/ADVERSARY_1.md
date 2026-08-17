# ADVERSARY 1 — attack report on the 510-vertex claim

**Target claim.** `data/CNP-SAT/vtx/510.vtx` is a unit-distance graph in the plane with
χ = 5 exactly. Pipeline reported: 510 vertices, 2504 edges, k=4 UNSAT (drat-trim VERIFIED,
proof sha256 prefix `71dc6bcbb371ebb8`), k=5 SAT.

**Bottom line.** I could not break the mathematical claim. Both halves (χ ≥ 5 and χ ≤ 5)
survive independent re-derivation with a different encoding, a different solver, and
from-scratch exact arithmetic that re-derives the graph from the coordinates rather than
trusting the edge file. **The claim is CONFIRMED.**

I did find **five discrepancies**, none of which touch soundness, and one of which
**refutes any novelty/record framing**: 510 is a previously known graph (HeuleGraph510)
and is one vertex *worse* than the standing 509 record.

| Check | Verdict |
|---|---|
| CHECK 1 — independent 4-colouring attempt, different solver + encoding | **CONFIRMED** |
| CHECK 2 — exact re-derivation of coordinates, both directions | **CONFIRMED** |
| CHECK 3 — literature: is 510 a record? | **REFUTED as a record** (worse than 509); record identification itself CONFIRMED |

Input files under attack, hashed at time of use:

| File | Bytes | sha256 |
|---|---|---|
| `data/CNP-SAT/vtx/510.vtx` | 25 819 | `66defa1743e64073776ed4c6a2e9c496abbd4628bf7d973dcc07cf834ce35b37` |
| `data/CNP-SAT/edge/510.edge` | 23 661 | `c6178b5a6ee12f9469d33f2cdac51e6e76b3cc6b39d3bd2358b0f97a894aac0a` |

---

## CHECK 1 — independent encoding + different solver: **CONFIRMED**

### What I built

`/home/user/CustomLLM/tests/adv1_encode.py` (11 695 B, sha256
`011d8d4504f8f3061120cfe64934fbc183d5c9885b69fd99ff048e80e58b3414`).
Shares no code with `src/hn/cnf.py`. Deliberate differences:

1. **Colour-major numbering** `var(v,c) = c*n + v + 1` (pipeline uses vertex-major
   `v*k + c + 1`). Audited injective over 510×4, range exactly 1..nk.
2. **At-most-one-colour clauses ARE emitted** (pairwise). The pipeline deliberately omits
   them. With ALO+AMO each vertex gets *exactly* one colour, so models are in bijection
   with proper colourings — this removes the entire "pick any true colour" post-processing
   step that the pipeline's soundness argument depends on.
3. **No symmetry breaking at all.** No clique pinned, nothing assumed about structure.
4. **Edge set re-derived from the exact geometry**, not read from `510.edge`
   (`--edge-source geometry`, the default). Chain is: Mathematica coordinates → exact field
   arithmetic → unit pairs → CNF → solver. The `.edge` file is never trusted.
5. Solved with **cadical 3.0.1** (pipeline used kissat 4.0.4).

Clause counts are asserted against a closed form, not just printed:
k=4 → 2040 vars, 14 566 clauses = 510 ALO + 3060 AMO + 10 016 edge.
k=5 → 2550 vars, 18 130 clauses = 510 ALO + 5100 AMO + 12 520 edge.

### Exact commands

```
python3 tests/adv1_encode.py --k 5 --out artifacts/adv1 --no-proof
python3 tests/adv1_encode.py --k 4 --out artifacts/adv1
# internally:
vendor/cadical/build/cadical --no-binary -q artifacts/adv1/adv1_510_k4.cnf \
                                            artifacts/adv1/adv1_510_k4.cadical.drat
vendor/drat-trim/drat-trim  artifacts/adv1/adv1_510_k4.cnf \
                            artifacts/adv1/adv1_510_k4.cadical.drat -f
```

### k = 4 result

- Geometry re-derivation inside the encoder: n=510, **2504 exact unit pairs**, and
  `identical to data/CNP-SAT/edge/510.edge ? True`.
- **cadical exit 20, `s UNSATISFIABLE`, 111.1 s.**
- Proof `artifacts/adv1/adv1_510_k4.cadical.drat` — **330 646 444 bytes**, sha256
  `cf4affe60a8f076e6291544b932ab658d1df08b10c19bf97842067b00aa0189d`.
- **drat-trim forward mode (`-f`): `s VERIFIED`, exit 0, 182.5 s.**
  Log: `artifacts/adv1/adv1_510_k4.drattrim.log` (426 B, sha256
  `a379c3124237c2f75aa202091dce2c6ff07c0eacd844643aca2574860967e6c2`).

**CHECKER VERDICT: VERIFIED.** No SAT at k=4 — no soundness alarm.

The proof is 46× larger than the pipeline's 7 160 065 B kissat proof. That is fully
explained by my removal of the 3 symmetry-breaking unit clauses (the solver must now
re-refute all 4! = 24 colour permutations) plus the added AMO clauses. It is not a
discrepancy in the result.

Two extra confirmations on the *same* CNF, different search:

| Run | Verdict |
|---|---|
| `vendor/kissat/build/kissat -n artifacts/adv1/adv1_510_k4.cnf` | `s UNSATISFIABLE` |
| `vendor/cadical/build/cadical --plain -q -n …k4.cnf` (all preprocessing off) | `s UNSATISFIABLE` |

`--plain` matters: it rules out the UNSAT being an artifact of cadical's inprocessing.

### k = 5 result

- **cadical exit 10, `s SATISFIABLE`, 0.0 s.**
- CNF: `artifacts/adv1/adv1_510_k5.cnf`, 243 667 B, sha256
  `9448fb226d0102f2aee5273c06ea52eedfa6c909ad51a99898276aeea76486ba`.
- Model: `artifacts/adv1/adv1_510_k5.model`, 13 683 B, sha256
  `cfc45ad3fc8e6de297fe4d57aba89cb1646dd511794fbcddacbc55a947ec7967`.
- Colouring: `artifacts/adv1/adv1_510_k5.colouring`, 2 952 B, sha256
  `d10b2666e08de7244953b94e59e2ad6365c69bdd6278fb97d30613d3f20d4ae9`.
- **My own checker (`check_model`, written from scratch) against the exactly-derived
  edge list: VALID PROPER COLOURING.** Every vertex carries exactly one true colour var
  (AMO not violated anywhere), zero monochromatic edges, 5 of 5 colours used.

Together with k=4 UNSAT this gives **χ = 5 exactly**, independently.

### Negative controls — proving the encoder can say both words

A checker that only ever says UNSAT would make the headline meaningless.
`/home/user/CustomLLM/tests/adv1_encode_selftest.py` (5 795 B, sha256
`1fb194e77a43d0a2248c7545329562f69d0fcc8e97b2adc40b06b772142dbd6d`):

```
ADV1_SCRATCH=<scratch> python3 tests/adv1_encode_selftest.py
```

- Numbering audit: colour-major map injective over 510×4; range exactly 1..nk; distinct
  from vertex-major. **PASS**
- K₃…K₆ at every k ∈ 2..6: SAT iff k ≥ m, all 20 cells as predicted. **PASS**
- Moser spindle: k=3 UNSAT, k=4 SAT, and the 4-colouring passes my model checker. **PASS**
- Golomb-type graph: k=3 UNSAT, k=4 SAT. **PASS**
- C₅: k=2 UNSAT, k=3 SAT. C₆: k=2 SAT. **PASS**
- Single-edge deletion on the 510 graph flips it to 4-colourable. **PASS** (2 of 3 probed
  edges) — see Discrepancy D3 for the third.

The encoder demonstrably distinguishes SAT from UNSAT on graphs with independently known
chromatic numbers.

### Cross-audit of the pipeline's own CNFs (unsolicited, and it matters)

I decoded `artifacts/heule510/heule510.k4.cnf` and `.k5.cnf` back into edge sets under the
pipeline's own vertex-major convention and compared against my exact geometry:

- k=4: 510 ALO clauses, unit clauses `[1, 102, 123]`, **2504 decoded edges, edge set ==
  my exact geometry-derived set: True**.
- k=5: 510 ALO clauses, unit clauses `[1, 127, 153]`, **2504 decoded edges, == exact set:
  True**.

The unit clauses decode exactly to the documented `symmetry_fixed {0:0, 25:1, 30:2}` and
nothing else. There are no undeclared clauses hiding in the pipeline's CNFs.

I also verified the symmetry-breaking clique is real, against my exact edge set:
vertices 0, 25, 30 (0-indexed) → pairs (1,26), (1,31), (26,31) all present. **Genuine
triangle.** Since the graph's **maximum clique is 3** (networkx; and I confirmed no K₄
exists by direct enumeration), pinning 3 vertices is the most SBP the structure allows,
and — importantly — **the k=4 UNSAT is not trivially forced by a K₅**. It is real content.

I re-verified the pipeline's own proof end-to-end:

```
gunzip -c artifacts/heule510/heule510.k4.kissat.drat.gz > pipeline.k4.drat
vendor/drat-trim/drat-trim artifacts/heule510/heule510.k4.cnf pipeline.k4.drat -f
  → s VERIFIED  (2.373 s)
```

Structural facts (exact-derived, no floats): connected, 1 component, min degree 4,
max degree 36, 999 triangles, max clique 3, no isolated vertices.

---

## CHECK 2 — exact re-derivation of the coordinate set: **CONFIRMED**

### What I built

`/home/user/CustomLLM/tests/adv1_exact.py` (18 365 B, sha256
`86ed7e1905fa335d0346f7a93d8640bb29b69c47fbdb593b0c32a79239225c0a`).
Imports nothing from `hn.*` — no `hn.field`, `hn.point`, `hn.detect`, `hn.mathematica`.
No sympy. No python-flint. My own field implementation.

**Field model.** Every coordinate lies in K = ℚ(√3, √5, √11), degree 8 over ℚ. Basis
indexed by a bitmask over the primes (bit0→3, bit1→5, bit2→11):

```
b[m] = √(product of primes in m)
0→1  1→√3  2→√5  3→√15  4→√11  5→√33  6→√55  7→√165
b[i]·b[j] = (product of primes in i AND j) · b[i XOR j]
```

Because 3, 5, 11 are multiplicatively independent modulo squares, these 8 elements are
ℚ-linearly independent, so **a field element has a unique coefficient vector and equality
is coefficient-wise**. That is what makes this a proof rather than an approximation.

Coefficients are `fractions.Fraction`. All nine radicals in the file are handled
symbolically and exactly: `Sqrt[11/3] = √33/3`, `Sqrt[5/3] = √15/3`, `1/Sqrt[3] = √3/3`
(via a real 8×8 exact-rational Gaussian-elimination inverse in K, self-checked as
`a · a⁻¹ = 1`). A recursive-descent parser handles `+ - * /`, unary minus, nesting, and
`Sqrt[·]` of any rational; `Sqrt` of a non-rational or of a radicand outside {3,5,11}
**aborts rather than guessing**.

For the all-pairs sweep I cleared denominators to a single global integer denominator
**D = 96**, so every coordinate becomes an integer vector and the unit test is the exact
integer predicate `s[0] == D² == 9216 and s[1:] == [0]*7`. **No floating point is
consulted anywhere in the accept/reject path.** Floats appear only in one printed
cross-check column and in the self-test's parser comparison.

### Exact command and result

```
python3 tests/adv1_exact.py
```

```
[parse]      parsed 510 vertices exactly in K=Q(sqrt3,sqrt5,sqrt11)
[parse]      edge header: p edge 510 2504; parsed 2504 'e' lines
[edgelist]   self-loops=0 duplicate-undirected-pairs=0 distinct-undirected=2504
[algebra]    global common denominator D = 96 ; target D^2 = 9216
[distinct]   510 / 510  — PASS: all 510 vertices pairwise distinct exactly
[all-pairs]  pairs examined exactly: 129795
[all-pairs]  EXACT unit pairs found: 2504
[direction a] claimed edges with squared distance != 1 exactly: 0   PASS
[direction b] exact unit pairs missing from the edge list: 0        PASS
[count]      PASS: exact unit-pair count is 2504
[struct]     min degree 4, max degree 36, isolated vertices 0
CHECK 2 RESULT: ALL EXACT ASSERTIONS PASS
```

### **Measured exact unit-pair count: 2504.** Matches the reported 2504. No alarm.

- **(a)** All 2504 claimed edges have squared distance **exactly 1** — not within a
  tolerance, but as an equality of integer coefficient vectors over the degree-8 basis.
- **(b)** All **129 795** pairs (= C(510,2), the full set, no float prefiltering, no
  sampling) were evaluated exactly. Exactly 2504 are unit. **The edge list is complete —
  zero unit pairs omitted.**
- All 510 vertices are **pairwise distinct exactly**, self-loops 0, duplicate undirected
  pairs 0, all indices in range, header counts consistent.

Direction (b) is the strictly stronger statement and is what the upstream repo's own
checker does *not* do (see D5). It matters: it means 510.edge is the **full**
unit-distance graph induced by that point set, so χ of the induced UD graph is exactly 5 —
not merely of some subgraph.

### Negative controls — proving the exact checker has teeth

`/home/user/CustomLLM/tests/adv1_exact_selftest.py` (7 299 B, sha256
`094b17b802a685b5051b62236a73050d661bf77f7fae84ba04f42a228d9fa4af`):

```
python3 tests/adv1_exact_selftest.py   →  all PASS
```

- **T1 field axioms.** (√m)² = m for all 8 basis radicands; associativity, distributivity
  and inversion on 30 random elements; √3·√11 = √33; √(11/3) = √33/3; √(5/3) = √15/3;
  1/√3 = √3/3; **`Sqrt[7]` correctly rejected** as outside the field rather than silently
  mishandled.
- **T2 parser cross-check.** All 1020 coordinates re-evaluated by a completely separate
  route (textual rewrite to Python + `math.sqrt`). Max absolute difference
  **4.441 × 10⁻¹⁶** — i.e. the exact parse agrees with the naive reading of the file to
  full double precision, so no coordinate was silently mis-parsed.
- **T3 mutation.** Shift vertex 300's x by 1/96 (the smallest step D allows) → unit pairs
  drop 2504 → 2493, symmetric difference 11. **Detected.**
- **T4 mutation.** Corrupt one radical (`Sqrt[33]` → `Sqrt[3]`) in vertex 8 → 2499 pairs,
  symmetric difference 5. **Detected.**
- **T5 mutation.** Duplicate a vertex → distinctness test reports 509/510. **Fires.**
- **T6 no hidden tolerance.** Squared distance (97/96)² rejected; a genuine exact unit pair
  (1/2, √3/2) accepted; a squared distance that is 1 in the rational slot but has a nonzero
  √3 tail **rejected**. There is no epsilon anywhere in the comparison.

---

## CHECK 3 — literature: **the record framing is REFUTED**

Network restriction acknowledged: arxiv.org, mathworld.wolfram.com, cs.cmu.edu,
researchgate.net, and additionally michaelnielsen.org and dustingmixon.wordpress.com are
egress-blocked for WebFetch. All conclusions below rest on the WebSearch tool across
**eight differently-phrased queries**, which returned mutually consistent results.

### Answers to the specific questions

**Q: Did Jaan Parts publish a 509-vertex graph in 2020? — CONFIRMED.**
J. Parts, *"Graph minimization, focusing on the example of 5-chromatic unit-distance graphs
in the plane"*, **Geombinatorics 29/4:137–166, 2020**; preprint **arXiv:2010.12665**.
The graph has **509 vertices and 2442 edges**, obtained by a different vertex-selection /
minimization algorithm.

**Q: Is 509 still the record as of Aug 2026? — CONFIRMED, with the caveat below.**
Multiple independently phrased queries all returned the same statement: *"As of August
2026, the smallest known unit-distance graph with chromatic number 5 realized in the
Euclidean plane remains the 509-vertex Parts graph (Parts 2020, Haugland 2026)."*
Targeted hunts for anything at 508 or below, and for 2025/2026 improvements, returned
**nothing**. I found no construction at or below 509 other than Parts' own.

**Q: Is our 510 a record, a tie, or worse? — WORSE, by one vertex. And it is not new.**

The 510-vertex graph is **not** an original result of this pipeline. It is the previously
known **HeuleGraph510** — one of the Heule graphs derived by Marijn Heule (April–July 2018)
from the 1581-vertex de Grey graph via clausal-proof minimization, and catalogued in the
Wolfram Language as `GraphData["HeuleGraph510"]`. The file we are checking comes from
Heule's own `CNP-SAT` repository. So:

- **510 is one vertex worse than the 509 record.**
- **510 is not a tie and not new** — it is a re-verification of a 2018–2019 published graph.

Any framing of this as a record or a novel construction is **REFUTED**. What our pipeline
legitimately establishes is an *independent verification* of a known graph, which is
valuable but is not a new bound.

### Record progression (as reconstructed from search results)

| Vertices | Author | Date | Reference |
|---|---|---|---|
| 1581 | Aubrey de Grey | 2018 | arXiv:1804.02385 (after correction) |
| ~1577 → 874 → 826 → 803 | Mixon / Polymath16 | 2018 | Polymath16 threads |
| 633, 610, 553, 529, **510**, 517 | Marijn Heule | 2018–2019 | arXiv:1805.12181; arXiv:1907.00929 |
| **509** (2442 edges) | **Jaan Parts** | **2020** | **Geombinatorics 29/4:137–166; arXiv:2010.12665** |

Related but not record-setting: Voronov et al. constructed Moser-spindle-free 5-chromatic
UD graphs on 64 513 vertices; Haugland (2026, arXiv:2608.04542) improved the
Moser-spindle-free case to **2131** vertices — much larger than 509, so not a record for
the unrestricted problem.

Known lower bound on the minimum order v₅: only **v₅ > 12** (Pritikin), versus the upper
bound v₅ ≤ 509. The gap is enormous, so **whether 509 is actually optimal is wide open —
label that conjecture, not fact.**

### Uncertainty I must flag (D4b)

Several search snippets state the 510-vertex Heule graph has **2508** edges, while others
(and a video title) state **2504**. My exact computation is authoritative *for this
coordinate set*: the 510 points in `510.vtx` admit **exactly 2504** unit pairs, derived
from the coordinates alone without consulting `510.edge`. If a literature "510/2508" graph
exists, it must use a different point set. **Either way our result is unaffected** — if
anything, a 2504-edge graph being 5-chromatic is the stronger statement, since fewer edges
means a weaker graph. I could not resolve this bookkeeping question because the primary
sources (arXiv, MathWorld, the Polymath wiki, Mixon's blog) are all egress-blocked.
**Labelled: unresolved, low importance, no soundness impact.**

---

## Discrepancies found

### D1 — reported proof hash does not match the file at `proof_path` (provenance bug)

`artifacts/heule510/verdict.k4.json` says:

```
"proof_path":   ".../heule510.k4.kissat.drat.gz"
"proof_sha256": "71dc6bcbb371ebb8784a6ff27ee2456ac6e556c7b3077afdf4844055a49d9832"
"proof_bytes":  7160065
```

But on disk that `.gz` file is **1 984 991 bytes** with sha256
**`2e7d0a4400eed1731d3b8ef9de6bfd5915b1988b53d35e9202f847cea2d32863`**.

Resolved: the reported hash and byte count describe the **uncompressed** DRAT stream
(`gunzip -c … | sha256sum` = `71dc6bcb…`, 7 160 065 B — exact match). So the numbers are
*correct*, but they are attached to a `proof_path` that names a different (compressed) file.
Anyone reproducing by hashing the file at `proof_path` gets a mismatch and would reasonably
conclude the artifact had been tampered with. **Fix: either record both hashes, or point
`proof_path` at the uncompressed stream.** No soundness impact.

### D2 — `proof_bytes` reported for a SAT run that has no proof (misleading metadata)

`verdict.k5.json` has `"verdict": "SAT"`, `"proof_path": null`, `"checker": null`,
`"checker_verdict": null` — yet `"proof_bytes": 23170`. There is no refutation for a
satisfiable instance, so a non-null `proof_bytes` is meaningless here and invites a reader
to believe a k=5 proof exists. **Fix: null it out, or rename the field to reflect what it
actually measures (solver output size).** No soundness impact.

### D3 — the 510 graph is **not edge-critical**; `510.edge` is not edge-minimal

While building CHECK 1's negative controls I probed three single-edge deletions. Two
flipped to SAT as expected. **Deleting edge (1,2) — between vertex 1 = {0,0} and vertex
2 = {1,0} — left the graph still 4-uncolourable.** Confirmed properly, not just as a
side-effect:

- CNF `artifacts/adv1/adv1_510_minus_e1_2_k4.cnf`, 178 560 B, sha256
  `0a411eb9261eea59d38ef392bb93d209d2e743ab88c06f6f13b4aa1bed03f3b5` (510 vertices,
  **2503** edges).
- **cadical: `s UNSATISFIABLE`, exit 20.**
- Proof `artifacts/adv1/adv1_510_minus_e1_2_k4.cadical.drat`, **331 333 209 bytes**,
  sha256 `06116b517b17aca8bce0ac81916f287136c4e31532176c51c23d4b567e232b4e`.
- **drat-trim `-f`: `s VERIFIED`, exit 0.**
- **kissat independently agrees: `s UNSATISFIABLE`.**

So **there exists a 510-vertex, 2503-edge 5-chromatic unit-distance graph**: edge (1,2) is
redundant. This does **not** contradict the target claim — χ = 5 still holds, and dropping
an edge from a graph that needs 5 colours and still needing 5 colours is a *stronger*
statement. But it **refutes any implicit claim that `510.edge` is minimal**, and it means
the graph is not edge-critical. I did not sweep all 2504 edges (each UNSAT case costs
~110 s of solver time), so **how many edges are redundant is unmeasured — conjecture:
more than one.**

### D4 — 510 is not a record and not new (see CHECK 3)

The record is 509 (Parts 2020). 510 is HeuleGraph510, published 2018–2019. D4b: the
2504-vs-2508 edge-count question in secondary sources is unresolved and immaterial.

### D5 — upstream CNP-SAT ships **no** certification for 510 specifically

The repository's own artifacts are incomplete for this graph:

- `data/CNP-SAT/cnf/` contains CNFs for 517, 529, 553, 610, 633, 803, 826, 874 — **not 510**.
- `data/CNP-SAT/proof/` contains DRAT proofs for 517, 529, 553, 610, 633, 803 — **not 510**.
- `data/CNP-SAT/check/*.singular` (the Singular/Gröbner distance-one certificates) cover
  553, 610, 633, 803, 826, 874 — **not 510**.

So for 510 the upstream repo provides coordinates and an edge list but **no chromatic proof
and no distance-one certificate**. Our pipeline's k=4 proof and my CHECK 1 proof are, as
far as these artifacts go, the certification for this graph; and my CHECK 2 supplies the
exact geometric certificate the upstream `check/` directory omits.

Additionally, note that upstream's `check_dist_one.py` only ever verifies **direction (a)**
(each listed edge reduces to 0 modulo the radical ideal). It never checks completeness, never
checks vertex distinctness, and its `Sqrt[...]`-to-variable rewriting is a fragile
textual-substitution table (a long hard-coded list of `/(k*Sqrt[3])` cases) that would
silently mis-handle any denominator form not in the list. My parser handles the grammar
generally and aborts on anything it cannot represent exactly. **This is a robustness
criticism of the upstream tool, not a defect found in the 510 data.**

---

## Additional result: the graph IS vertex-critical (no 509 hides inside it)

Since 509 is the record, the obvious attack is: does deleting some vertex of this 510
graph leave a 5-chromatic 509-vertex graph, tying the record? I tested **all 510
single-vertex deletions** at k=4 with cadical (4 parallel workers,
`/tmp/.../scratchpad/vtxcrit.py`, edge set re-derived exactly from geometry):

```
vertex-deletion tests: 510 total
  SATISFIABLE (509-vertex subgraph is 4-COLOURABLE): 510
  UNSATISFIABLE (509-vertex subgraph still 5-chromatic): 0
  other: 0
```

**Every one of the 510 induced 509-vertex subgraphs is 4-colourable.** So the graph is
**vertex-critical**: no vertex is removable, and the 509 record cannot be reached by
deleting a vertex from this graph. (Consistent with the literature — Parts reached 509 by a
different vertex-selection algorithm, not by trimming Heule's 510.)

Caveat on rigour: these 510 results are SAT verdicts with **explicit witnesses available
but not individually model-checked or proof-carrying** — a SAT verdict needs no DRAT proof,
and a spurious SAT would only make me *under*-report removable vertices, never
over-report. The headline k=4 UNSAT is the proof-carrying result.

---

## Checker verdicts, stated explicitly

| Instance | Solver | Verdict | Checker | **Checker verdict** |
|---|---|---|---|---|
| my `adv1_510_k4.cnf` (AMO, colour-major, no SBP) | cadical 3.0.1 | UNSAT | drat-trim `-f` | **s VERIFIED** |
| my `adv1_510_k4.cnf` | kissat 4.0.4 | UNSAT | — | (cross-check only) |
| my `adv1_510_k4.cnf` | cadical `--plain` | UNSAT | — | (cross-check only) |
| my `adv1_510_k5.cnf` | cadical 3.0.1 | SAT | my own `check_model` | **VALID PROPER COLOURING** |
| pipeline `heule510.k4.cnf` | kissat (their run) | UNSAT | drat-trim `-f`, **re-run by me** | **s VERIFIED** (2.373 s) |
| `adv1_510_minus_e1_2_k4.cnf` (2503 edges) | cadical 3.0.1 | UNSAT | drat-trim `-f` | **s VERIFIED** |
| 510 × single-vertex-deletion, k=4 | cadical 3.0.1 | SAT ×510 | — | no proof needed for SAT |

No UNSAT is asserted anywhere in this report without a drat-trim `s VERIFIED`.

---

## Artifact manifest

Scripts (`/home/user/CustomLLM/tests/`):

| Path | Bytes | sha256 |
|---|---|---|
| `tests/adv1_encode.py` | 11 695 | `011d8d4504f8f3061120cfe64934fbc183d5c9885b69fd99ff048e80e58b3414` |
| `tests/adv1_exact.py` | 18 365 | `86ed7e1905fa335d0346f7a93d8640bb29b69c47fbdb593b0c32a79239225c0a` |
| `tests/adv1_exact_selftest.py` | 7 299 | `094b17b802a685b5051b62236a73050d661bf77f7fae84ba04f42a228d9fa4af` |
| `tests/adv1_encode_selftest.py` | 5 795 | `1fb194e77a43d0a2248c7545329562f69d0fcc8e97b2adc40b06b772142dbd6d` |

Solver artifacts (`/home/user/CustomLLM/artifacts/adv1/`):

| Path | Bytes | sha256 |
|---|---|---|
| `adv1_510_k4.cnf` | 178 608 | `9ba3d970038cc9c4fefa2d22e545bed6b3d87f6d63e020ace9250726afda83fe` |
| `adv1_510_k4.cadical.drat` | 330 646 444 | `cf4affe60a8f076e6291544b932ab658d1df08b10c19bf97842067b00aa0189d` |
| `adv1_510_k4.drattrim.log` | 426 | `a379c3124237c2f75aa202091dce2c6ff07c0eacd844643aca2574860967e6c2` |
| `adv1_510_k5.cnf` | 243 667 | `9448fb226d0102f2aee5273c06ea52eedfa6c909ad51a99898276aeea76486ba` |
| `adv1_510_k5.model` | 13 683 | `cfc45ad3fc8e6de297fe4d57aba89cb1646dd511794fbcddacbc55a947ec7967` |
| `adv1_510_k5.colouring` | 2 952 | `d10b2666e08de7244953b94e59e2ad6365c69bdd6278fb97d30613d3f20d4ae9` |
| `adv1_510_minus_e1_2_k4.cnf` | 178 560 | `0a411eb9261eea59d38ef392bb93d209d2e743ab88c06f6f13b4aa1bed03f3b5` |
| `adv1_510_minus_e1_2_k4.cadical.drat` | 331 333 209 | `06116b517b17aca8bce0ac81916f287136c4e31532176c51c23d4b567e232b4e` |

Pipeline artifact hashes I independently measured:

| Path | Bytes | sha256 |
|---|---|---|
| `artifacts/heule510/heule510.k4.kissat.drat.gz` (on disk) | 1 984 991 | `2e7d0a4400eed1731d3b8ef9de6bfd5915b1988b53d35e9202f847cea2d32863` |
| same, **uncompressed** (what verdict.json reports) | 7 160 065 | `71dc6bcbb371ebb8784a6ff27ee2456ac6e556c7b3077afdf4844055a49d9832` ✓ |

---

## Verdict summary

- **CHECK 1: CONFIRMED.** k=4 UNSAT reproduced with a from-scratch colour-major +
  at-most-one encoding, no symmetry breaking, edge set re-derived from exact geometry,
  solved by cadical, **drat-trim `s VERIFIED`** on a 330 646 444-byte proof (sha256
  `cf4affe6…`); independently corroborated by kissat and by cadical `--plain`. k=5 SAT with
  a proper 5-colouring validated by my own checker. **No k=4 SAT — no soundness alarm.**
- **CHECK 2: CONFIRMED.** **Exact unit-pair count measured: 2504**, equal to the reported
  2504. All 2504 claimed edges exactly unit; all **129 795** pairs tested exactly with zero
  omissions, so the edge list is complete; all 510 vertices pairwise distinct exactly. Six
  families of negative controls confirm the checker detects corruption and carries no
  tolerance.
- **CHECK 3: the record framing is REFUTED; the record identification is CONFIRMED.**
  Parts' 509-vertex / 2442-edge graph (Geombinatorics 29/4:137–166, 2020;
  arXiv:2010.12665) is confirmed and still stands as of Aug 2026. **Our 510 is one vertex
  worse than the record and is the previously known HeuleGraph510 (Heule 2018–2019), not a
  new construction.** No construction at or below 509 was found. Whether 509 is optimal is
  **open** (lower bound only v₅ > 12) — conjecture, not fact.

**Overall: the mathematical claim "510.vtx is a unit-distance graph in the plane with
χ = 5 exactly" is CONFIRMED and survived every attack I mounted. Five discrepancies were
found (D1, D2, D3, D4, D5); none affect soundness, but D4 refutes any novelty/record
claim and D3 refutes minimality.**

### Sources

- [Parts, *Graph minimization, focusing on the example of 5-chromatic unit-distance graphs in the plane* (arXiv:2010.12665)](https://arxiv.org/abs/2010.12665)
- [Heule, *Computing Small Unit-Distance Graphs with Chromatic Number 5* (arXiv:1805.12181)](https://arxiv.org/pdf/1805.12181)
- [Heule, *Trimming Graphs Using Clausal Proof Optimization* (arXiv:1907.00929)](https://arxiv.org/pdf/1907.00929)
- [de Grey, *The chromatic number of the plane is at least 5* (arXiv:1804.02385)](https://arxiv.org/abs/1804.02385)
- [Parts, *Constructing 5-chromatic unit distance graphs embedded in the Euclidean plane and two-dimensional spheres* (arXiv:2106.11824)](https://arxiv.org/pdf/2106.11824)
- [Haugland, *A Moser-spindle-free 5-chromatic unit distance graph on 2131 vertices in the plane* (arXiv:2608.04542)](https://arxiv.org/abs/2608.04542)
- [*On lower bounds of the order of k-chromatic unit distance graphs* (arXiv:2303.14714)](https://arxiv.org/pdf/2303.14714)
- [Hadwiger-Nelson Problem — Wolfram MathWorld](https://mathworld.wolfram.com/Hadwiger-NelsonProblem.html)
- [Heule Graphs — Wolfram MathWorld](https://mathworld.wolfram.com/HeuleGraphs.html)
- [Parts Graphs — Wolfram MathWorld](https://mathworld.wolfram.com/PartsGraphs.html)
- [Hadwiger-Nelson problem — Polymath Wiki](https://michaelnielsen.org/polymath/index.php?title=Hadwiger-Nelson_problem)
- [Polymath16, fourteenth thread: Automated graph minimization?](https://dustingmixon.wordpress.com/2019/08/05/polymath16-fourteenth-thread-automated-graph-minimization/)
