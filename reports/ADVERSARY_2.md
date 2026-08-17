# ADVERSARY 2 — toolchain soundness audit

Target: `src/hn/{field,point,detect,graph,constructions,mathematica,cnf,modelcheck,oracle,minimizer,pipeline,search,perturb,catalog,pools}.py`,
plus `run_search3.py` and `verify_candidate.py`.
Scope deliberately disjoint from Adversary 1 (no work on `data/`, no re-attack of the
510-vertex claim). This audit attacks the *tools*, not a graph.

Executable demonstrations, all re-runnable:

```
python tests/adv2_float.py       # A  float leakage into the edge set
python tests/adv2_field.py       # B  exact field arithmetic
python tests/adv2_encoding.py    # C  CNF / MUS encoding
python tests/adv2_proof.py       # D  proof checking and verdict integrity
```

Each exits non-zero if any hole is present, and prints one `[HOLE]`/`[ok ]` line per
check with the measured numbers. Verbatim output of all four is quoted below.

---

## Findings, worst first

| # | Finding | Severity |
|---|---|---|
| D1b / D1c | `check_proof` returns **VERIFIED** for a **satisfiable** formula with a **0-byte proof** whenever the CNF is malformed; `solve_and_verify(...).is_verified_unsat` is `True` end-to-end | **CRITICAL** (latent — no current CNF is malformed) |
| A1–A4 | Float **decides** the edge set: four constructions where `detect_edges` misses a genuinely exact unit edge that `detect_edges_bruteforce_exact` finds. Two independent mechanisms (prune window, grid bucketing) | **MAJOR** |
| D2 | `check_proof` decides VERIFIED by substring-grepping combined stdout+stderr; ignores the exit code, is not line-anchored, and drat-trim has two code paths that echo *external strings* into stdout | **MAJOR** |
| A8 | `UDGraph(points, edges=...)` accepts an arbitrary **subset** of the true edge set; `verify_edges_exact` only checks supplied edges are unit, never that unit pairs were supplied. Same `coord_hash`, different graph | **MAJOR** (latent — no caller uses it) |
| C2b | `encode_coloring` trusts a caller-supplied `adj`; a lying `adj` **manufactures an UNSAT** from a 3-colourable graph. `pipeline.assess` guards it with `verify_clique`; `minimizer.build_mus_encoding` never calls `verify_clique` at all | **MAJOR** (latent) |
| A7 | `audit_prune_margin` — the project's own safety instrument — measures only the prune window and is structurally blind to the bucketing failure mode (A4) | MINOR (measurement gap) |
| B5b | `field.rational(0.1)` / `field.elem([0.1, …])` silently accept floats via `Fraction(float)` | MINOR |
| B6 | `FieldElem.key()` omits the field, so `Point.key()` collides across different fields and `dedup_points` merges unrelated points | MINOR |
| B7 | `_is_squarefree` is trial division to √n; a 30-digit generator hangs the constructor | MINOR (availability) |
| C1, C2, C3, C3b, C4 | at-most-one omission, clique pin, presence literals, variable convention | **NO HOLE FOUND** |
| B1–B4, B5 | generator guard, basis independence, `_exact_sign`, `inverse`/norm, `equals_rational` | **NO HOLE FOUND** |
| D1, D3, D3b, D4, D5 | forged proofs vs satisfiable formula, exit codes, `is_verified_unsat`, model-check downgrade, leaderboard | **NO HOLE FOUND** |

**No current result is invalidated.** `tests/adv2_proof.py::d1d` audits all 14 CNFs under
`artifacts/` (header counts exact, zero comment lines, every clause `0`-terminated), and
`tests/adv2_float.py::a7` measures the real margin on `510.vtx` (worst float `|d²−1|` on a
true edge = `6.66e-16`, i.e. **1.5 × 10⁹×** inside the window; largest coordinate
coefficient `3/2`). The holes are in the tools, waiting for the first input that reaches
them.

---

## A. FLOAT LEAKAGE INTO THE EDGE SET — **MAJOR** (4 demonstrated holes)

### A.0 Static audit

Every float in the repo, from
`grep -rn "float(\|\.approx()\|math\.\|abs(\|1e-" src/hn/*.py run_search3.py verify_candidate.py`:

| site | role | verdict |
|---|---|---|
| `field.FieldElem.approx()`, `field.MultiQuadField._sqrt_float` | the only float producers | filter-only by construction |
| `point.Point.approx()` | wrapper | filter-only |
| `detect.detect_edges` L39 `math.floor(x), math.floor(y)` | grid bucket keys | **decides which pairs are ever considered** |
| `detect.detect_edges` L55 `abs(d2 - 1.0) > window` | prune | filter, followed by exact confirmation |
| `detect.detect_edges` L61 `points[i].is_unit_from(points[j])` | exact | **unconditional** — confirmed by reading; no branch appends an edge without it |
| `detect.audit_prune_margin` | measurement only | no edge effect |
| `pools.detect_pairs_at_sqdist` L290 | prune for rotation-centre search | same shape, exact confirmation at L308; not on the edge path |
| `run_search3.py:133 float(os.environ…)` | a time budget | harmless |

So the *positive* direction is safe: `is_unit_from` gates every `edges.append`, and A5
confirms empirically that the two published near-unit adversarial fixtures
(`near_unit_rational_pair` at `1+1.7e-10`, `near_unit_irrational_pair` with a nonzero
√33 component) produce **zero** edges from both detectors while `exact_unit_pair_hard`
produces exactly one. **No false edge can be created.**

The *negative* direction is where the contract fails. `detect.py` claims:

> "The prune window is deliberately enormous relative to double-precision error (1e-6 on
> squared distance vs ~1e-15 achievable error on these coordinate magnitudes) so that a
> false negative is not credible." … "`detect_edges` and
> `detect_edges_bruteforce_exact` must agree on every input; the test suite enforces that."

Both sentences are false. The second is not enforced anywhere in `src/` — only
`verify_candidate.py` diffs the two detectors, and it does so *after* `UDGraph` has
already used the fast one.

### A.1 Coordinate magnitude alone (axis-aligned, `dx = 1` exactly)

`P=(a,0)`, `Q=(a+1,0)`. Breaks first at **|a| = 2^52 ≈ 4.50e15**.
Below 2^52 the double ulp divides 1 exactly, so `fl(a)` and `fl(a+1)` carry the *same*
rounding error and it cancels in the subtraction — the reason a naive magnitude sweep
finds nothing until the ulp reaches 1.

### A.2 Coordinate magnitude, generic (non-dyadic) unit separation

`P=(a,a)`, `Q=P+(3/5,4/5)`. The shift is not a dyadic multiple of the ulp, so the errors
no longer cancel. Breaks at **|a| = 8.59e9 (2^33)**, float `d²−1 = −3.05e-06` versus a
window of `1e-06` — 6 orders of magnitude below A1.

### A.3 The real attack: **O(1) coordinates, large coefficients**

Magnitude is the wrong variable. `approx()` evaluates `Σ float(v_s)·√r_s` term by term, so
the absolute error scales with the size of the *individual coefficients*, not with the
value of the sum. Build `A + B√3` with `|A|,|B| ~ N` chosen so the exact **value** is
`1/2`; add the exact unit vector `(3/10 − (2/5)√3, 2/5 + (3/10)√3)` (which is `(3/5,4/5)`
rotated 60°, asserted to satisfy `w_x²+w_y² == 1` exactly, and non-dyadic so the endpoint
errors do not cancel).

Binary search over N gives the smallest breaking coefficient scale:

```
[HOLE] A3 cancellation (O(1) coords) detect_edges=[] bruteforce=[(0, 1)];
  smallest breaking coefficient scale N=9507113946 (~1e10.0);
  max |coord VALUE| = 1.253; float d^2-1 = 2.7074e-06 vs window 1e-06
```

**Answer to "smallest coordinate magnitude": there is no such threshold.** Every
coordinate lies inside `|x| < 1.26` — the unit square — and the detector still loses a real
edge. The threshold is on the *coefficient numerators* (~10 digits), which the absolute
`1e-6` window knows nothing about.

This regime is reachable by ordinary project moves, not just by an adversary (A6):
composing the exact spindle rotation (`cos = 5/6`) multiplies denominators by 6 per step,
so coefficient denominators pass `1e12` after **25 compositions** and have 58 digits at
n=120. Any search that iterates rotations, Minkowski sums, or `pools.circle_intersections`
walks straight into it.

### A.4 The grid-bucketing hole — a second, independent mechanism

`detect_edges` buckets on `(math.floor(fl(x)), math.floor(fl(y)))` with cell size 1 and
scans only the 3×3 neighbourhood. That is correct only if the float coordinates are
accurate enough that a true-distance-1 pair never lands two cells apart. Using the exact
half-angle parametrisation `C=(1−u²)/(1+u²)`, `S=2u/(1+u²)` with `u` a *cancelling*
element — so `C²+S² == 1` is asserted exactly while `C,S` carry large coefficients
uncorrelated with `P`'s, which decorrelates the two endpoints' rounding:

```
[HOLE] A4 grid-bucket boundary detect_edges=[] bruteforce=[(0, 1)];
  fl(P.x)=4.99999999627471 -> cell 4, fl(Q.x)=6.0 -> cell 6 (differ by 2,
  so the 3x3 scan never enumerates the pair);
  float d^2-1 = 7.8505e-09 which is INSIDE the window 1e-06
  -- the window would have accepted it;
  coefficient scale 2^25; max |coord VALUE| = 6
```

This is worse than A1–A3 in one specific way: the float squared distance is within
**7.9e-9** of 1, so **widening or tightening `PRUNE_WINDOW` cannot fix it** and
`audit_prune_margin` — the project's own instrument — reports a perfectly healthy margin
while the edge is silently gone. The measurement is blind to the failure mode. Coefficient
scale needed is only **2^25 ≈ 3.4e7**, an order of magnitude *below* A3.

### A.5–A.8 supporting results

- **A5 (ok)** — no false positives; exact confirmation is unconditional.
- **A6 (ok)** — coefficient growth of 6^n under repeated exact rotation, i.e. A3/A4 are reachable.
- **A7 (ok, calibration)** — `510.vtx` sits 1.5e9× inside the window; largest coefficient `3/2`.
- **A8 (HOLE, MAJOR)** — `graph.py` says *"There is deliberately no constructor that accepts a hand-supplied edge list … letting a caller assert edges is exactly how an unsound edge slips in."* There is: `UDGraph(points, lineage, edges=…)`. `verify_edges_exact` only checks that every *supplied* edge is unit, never that every unit pair was supplied, so `UDGraph(pts, edges=[])` builds happily:

```
[HOLE] A8 the same 7 points give m=11 when edges are derived, but
  UDGraph(points, edges=[]) constructs fine with m=0 and edges=first_3 with m=3;
  graph_hash differs (2aee94a7 vs e0925c16) while coord_hash is IDENTICAL (04948f24)
```

Two different graphs share one `coord_hash`, which is the catalog's `graphs` PRIMARY KEY —
`register_graph` would silently keep whichever arrived first.

### Impact analysis for A (why MAJOR and not CRITICAL)

Missing edges is the *weakening* direction, so it cannot manufacture a false 5-chromatic
claim on its own: if `G' ⊆ G` is not 4-colourable then neither is `G`, and the k=5 side is
protected because `modelcheck.check_coloring_against_points` re-derives the edge set by
brute-force exact arithmetic with no filter. What A *does* break:

1. the documented invariant `detect_edges == detect_edges_bruteforce_exact`;
2. `m`, `graph_hash`, degree sequences, and every isomorphism/dedup decision;
3. **every SAT-side conclusion**: "this candidate is 4-colourable", "vertex v is critical",
   "`G[S]` is colourable so don't delete" — the entire minimiser steering signal;
4. `UDGraph.induced()` and `run_search3.minimise_small`, which rebuild a `UDGraph` per
   candidate and would drop edges the parent had.

### Recommended fixes for A

- Compute a **rigorous** per-coordinate error bound `E = Σ|v_s|·√r_s·2^-52` from the actual
  coefficients, and *assert* `PRUNE_WINDOW > 8·(E_i+E_j)` — turning a silent false negative
  into a loud failure. `audit_prune_margin` should report this bound, not just the observed
  slack.
- Bucket over an **interval**: insert each point into every cell its `[x−E, x+E]` box
  touches, or simply widen the neighbourhood scan while asserting `E ≪ 1`.
- Move `verify_candidate.py`'s two-detector diff into `UDGraph.__init__` (or make
  `detect_edges` fall back to brute force when the bound fails). It is currently checked
  only at the very end, long after the edge set has driven the search.
- Delete the `edges=` parameter, or make it assert `sorted(edges) == detect_edges(points)`.

---

## B. FIELD ARITHMETIC — **NO HOLE FOUND** in the soundness core; two MINOR issues

The reference oracle is **rigorous exact-integer interval arithmetic**: `√r` is bracketed
by `isqrt(r·10^{2P})/10^P` and that `+ 10^-P`, so an element's value is enclosed by two
`Fraction`s with a proven bound. `tests/adv2_field.py` contains **no floats at all**, so it
cannot be fooled by the rounding it is testing for.

### What I ran and what it printed

- **B1 generator guard (ok).** 15 degenerate generator sets, all rejected with `ValueError`:
  `(1,)`, `(0,)`, `(-3,)`, `(4,)`, `(9,)`, `(12,)`, `(18,)`, `(75,)`, `(2,2)`, `(6,10)`,
  `(10,15)`, `(3,33)`, `(2,3,6)`, `(6,15,10)`, and — the one that matters —
  **`(6,10,15)`**, the classic collapse `√6·√10·√15 = √900 = 30` which *would* make the 2^k
  basis Q-dependent and `equals_rational` invalid. Pairwise coprimality catches it.
  7 legitimate sets accepted, including `(6,35)` and `(2,15)` (squarefree and coprime but
  composite, i.e. not just primes).
  **I could not construct squarefree pairwise-coprime generators whose product-square-roots
  collapse, and there are none:** for pairwise coprime squarefree `r_i`, every nonempty
  subset product is squarefree and `> 1`, hence not a perfect square, which is exactly the
  Kummer criterion for the 2^k basis to be independent. The guard is genuinely *sufficient*,
  not merely plausible.
- **B1b `_is_squarefree` (ok).** Differentially tested against an independent reference over
  `n ∈ [-5, 20000)`: **0 mismatches**. (The implementation mutates `n` inside the loop bound,
  which looked like a bug; it is not.)
- **B2 basis independence (ok).** 766 random elements over 6 fields — `(3,11)`, `(3,5,11)`,
  `(2,3,5,7)`, `(6,35)`, `(2,15)`, `(5,7,11,13)` — every nonzero coefficient vector
  **proven** to have nonzero real value by interval refinement to 6000 digits; every basis
  element proven irrational. A dependent basis would have shown up as an element the oracle
  could not separate from 0.
- **B3 `_exact_sign` (ok).** Agreed with the proven sign on: 5 exact zeros written as
  differences of equal irrationals (`√15 − √3·√5`, `√165 − √3·√55`, `√33·√5 − √165`,
  `(√3±√5)² − (8±2√15)`) — all `is_zero()` true and `sign() == 0`; 15 near-zero convergents
  `√3 − p/q` down to `708158/408815`; **400** random degree-8 elements; and 3 deliberately
  cancelling elements with `|value| < 1e-40` built from coefficient scales `1e6`, `1e12`,
  `1e20`. **Zero disagreements.** The `sd == 0 ⇒ return 0` branch in `_exact_sign` is
  unreachable for an independent basis (it would require `r` to be a square in the subfield);
  it silently returns 0 rather than alarming, which is a latent nit only.
  Note: `sign()`'s docstring describes an interval-arithmetic fallback that does not exist —
  the implementation is purely the `A² vs B²r` recursion. Doc inaccuracy, not a bug.
- **B4 `inverse()` / norm / conjugation (ok).** 240 random inverses over 3 fields:
  `e·e⁻¹` and `e⁻¹·e` both `equals_rational(1)` exactly; the full Galois product is rational
  and nonzero for every nonzero element; `conjugate` verified additive, multiplicative and an
  involution for all 8 masks; `inverse(0)` raises `ZeroDivisionError`. The construction
  (product over the 2^k−1 non-identity automorphisms, then divide by the rational norm) is
  correct.
- **B5 `equals_rational(1)` cannot be fooled (ok).** 5 obscure exactly-1 forms all
  recognised (`√3²/3`, `(5/6)²+(√11/6)²`, `(1/2)²+(√3/2)²`, `√15/(√3·√5)`, `(2+√3)(2−√3)`);
  5 elements within `1e-120 … 1e-400` of 1 all correctly rejected, including
  `1 + (√3 − p/q)` with a 120-digit convergent and `1 + √165/10^400`.
- **B7 `sqrt_gen` (ok).** Rejects `9, 12, 99, 6, 0, 2, 5, 132` — it never silently swallows a
  square factor — and squares correctly for `3, 11, 33, 1`.

### B5b — float ingestion — **MINOR**

```
MultiQuadField.rational(0.1) silently returned 3602879701896397/36028797018963968
```
`Rat(x)` accepts a `float`, so `field.rational(1/3)` and `field.elem([0.1, …])` succeed and
produce a *dyadic* approximation. Nothing downstream is unsound — the resulting point is
exact, and every verdict is a true statement about *that* point — but it is not the point
the caller asked for, and it is the one remaining way a float can enter the coordinate
pipeline. Fix: reject non-`int`/`Fraction`/`str` inputs in `rational()`/`elem()`.

### B6 — `key()` ignores the field — **MINOR**

```
key(a) == key(b) across DIFFERENT fields: True; hash equal: False;
dedup_points([p_from_Q(3,11), p_from_Q(5,7)]) kept 1 of 2 points
```
`FieldElem.key()` returns only the coefficient numerators/denominators, so `Point.key()`
collides across fields while `__hash__` (which includes `field.gens`) does not — the two
identity notions disagree. `dedup_points`, `pools.save_pool`'s dedup check, and
`run_search3.py`'s `key2i = {p.key(): i}` all use `key()`. Currently harmless because every
pool is single-field, but `Point.__eq__` *raises `TypeError`* rather than returning `False`
for cross-field comparison, so the failure would be a crash or a silent merge, not a clean
error. Fix: prefix `key()` with `field.gens`.

### B7 note — DoS — **MINOR**

`_is_squarefree(1000006000009)` took **0.15 s** (trial division to √n). A 30-digit
generator, e.g. from a future parser that reads `Sqrt[<big>]`, hangs the constructor.
Availability only.

---

## C. ENCODING SOUNDNESS — **NO HOLE FOUND** in the live paths; one MAJOR latent hole

Ground truth throughout is **brute-force enumeration of all k^n colourings**, never another
SAT encoding, so a shared bug between encoder and checker cannot hide.

### C1 — is omitting at-most-one really sound in both directions? **Yes — proved and exhaustively verified.**

The argument: the edge clauses `(¬x_uc ∨ ¬x_vc)` for every colour `c` say that the *sets* of
true colours at adjacent `u` and `v` are **disjoint**; the ALO clause says each set is
nonempty. So picking any element of each set (`decode_model` picks the least) gives a total
proper colouring. Conversely a proper colouring gives a satisfying assignment directly. No
graph can break it — the property is per-edge and per-colour.

Verified rather than assumed:

```
[ok ] C1 248 encodings (ALL 64 graphs on 4 vertices + 60 sampled graphs on 5 vertices,
      k=2 and 3); 23508 satisfying assignments individually decoded: every one yields a
      proper TOTAL colouring, and SAT agreed with brute-force k-colourability on every graph
```

Every satisfying assignment was enumerated by brute force over all `2^{nk}` assignments and
decoded through the *real* `modelcheck.decode_model` — not sampled, not solver-generated.

### C2 / C3 / C3b — presence literals vs real vertex deletion

```
[ok ] C2  1200 random encodings (846 with a pin) agreed with brute-force colourability;
      every pinned set verified to be a real clique with distinct colours
[ok ] C3  11200 (graph, subset) pairs at k=4, with and without conditional symmetry
      breaking; 1707 of them genuinely non-4-colourable; 4202 deleted at least one pinned
      clique member: presence-literal UNSAT agreed with brute-force non-colourability in
      every single case
[ok ] C3b 2800 subsets that delete 1..all pinned clique members: no fake UNSAT was produced
```

C3 is the test the task asked for, done three ways per case: `MUSReducer`-style
`solve(assumptions={p_v : v ∈ S})`, a **from-scratch `encode_coloring` of the induced
subgraph**, and brute-force χ(G[S]) ≤ 4. Graphs `n ∈ [5,10]` at densities 0.55–0.95 so that
a meaningful fraction (1707 / 11200) are genuinely non-4-colourable; subsets uniformly random
including `∅` and the full set. **Zero disagreements in 11200 cases.**

C3b targets the specific worry — "can the conditional clique pin make a 4-colourable induced
subgraph look UNSAT?" — with subsets that drop 1, 2, …, all pinned clique members, on graphs
seeded to contain a k-clique so a pin is always emitted. **No fake UNSAT.** The reason it
holds: any subset of a clique is still a clique in the induced subgraph, distinct pinned
colours are always realisable by a colour permutation because colour classes are
interchangeable, and `(¬p_v ∨ x[v][i])` is vacuous when `p_v` is false. Deleted vertices'
colour variables stay free but the solver can set them all false, which satisfies every
incident edge clause vacuously — so satisfying assignments of the relaxed encoding under
assumptions are in exact correspondence with colourings of `G[S]`.

### C4 — variable convention (ok)

`var(v,c,k) == v*k+c+1` confirmed identical to `modelcheck`'s independently restated
formula, and no emitted literal exceeds the declared `n_vars` for `n ∈ {1,3,7,510}`,
`k ∈ {2,4,5}` — so the DIMACS header can never under-declare.

### C2b — `encode_coloring` trusts an unvalidated `adj` — **MAJOR (latent)**

```
[HOLE] C2b lying adj claims triangle {0,1,2} -> pins {0: 0, 1: 1, 2: 2};
  encoding SAT=False but the graph IS 3-colourable (True)
  -> the encoder MANUFACTURED an UNSAT. verify_clique on the pinned set = False
```

The witness is `K_{2,3}` plus the edge 3–4: vertices 0,1,2 are each adjacent to both 3 and 4,
and 3–4 is an edge. It is 3-colourable, but 3 and 4 consume two colours so 0,1,2 must *all*
take the third — they can never be pairwise distinct. An `adj` that falsely claims
`{0,1,2}` is a triangle pins them to three distinct colours and the encoding becomes UNSAT.

`encode_coloring` performs no consistency check between `adj` and `edges`, even though
`verify_clique` exists in the same module. `pipeline.assess` does call it and would raise
`SOUNDNESS ALARM`, so nothing in the pipeline is currently exposed.
`minimizer.build_mus_encoding` **never calls `verify_clique` at all** — it is safe only
because it derives `adj` from `g.adj`, which `UDGraph` derives from `g.edges`. Combined with
A8 (`edges=` accepting an arbitrary subset), the two latent holes are one careless call
apart from each other. Fix: `encode_coloring` and `build_mus_encoding` should both assert
`verify_clique(clique, edges)` before emitting a pin, and `encode_coloring` should derive
`adj` from `edges` itself rather than accepting it.

---

## D. PROOF-CHECKING HOLES — **CRITICAL** (one demonstrated false VERIFIED) + **MAJOR**

### D1 — can a forged proof verify a satisfiable formula? **No.** (ok)

The right experiment is against a **satisfiable** formula: damaging the proof of a genuinely
UNSAT formula and still getting VERIFIED is *not* unsoundness, because drat-trim certifies
the *formula* and will re-derive a conflict from whatever lemmas remain. Against a
well-formed satisfiable CNF, 14 forgeries were all rejected:

```
empty proof -> NOT_VERIFIED; whitespace only -> NOT_VERIFIED;
bare empty clause, no derivation -> NOT_VERIFIED;
comment claiming success -> NOT_VERIFIED;
comment claiming success then empty clause -> NOT_VERIFIED;
garbage text -> NOT_VERIFIED;
delete every original clause then claim the empty clause -> NOT_VERIFIED;
assert a non-RUP unit then the empty clause -> NOT_VERIFIED;
assert every literal false then the empty clause -> NOT_VERIFIED;
a valid proof of a DIFFERENT, unsatisfiable formula -> NOT_VERIFIED;
p-line injection inside the proof -> NOT_VERIFIED;
random bytes -> NOT_VERIFIED;
nonexistent proof path -> CHECKER_INCONCLUSIVE;
nonexistent CNF path -> CHECKER_INCONCLUSIVE
```

The `-U` flag was checked in the source (`vendor/drat-trim/drat-trim.c:1421` →
`S.rupOnly = 1`, used at L659 to *refuse* the RAT fallback when RUP fails). It makes
checking **stricter**, not weaker — a good choice, at the cost of rejecting legitimate
RAT-using proofs. `s TIMEOUT` (L905) and `s DERIVATION` (L1482) both land in
`CHECKER_INCONCLUSIVE`, i.e. the safe direction. `"s VERIFIED"` is not a substring of
`"s NOT VERIFIED"`, so the `if/elif` order is not exploitable.

### D1b — malformed CNF ⇒ VERIFIED **without reading the proof** — **CRITICAL**

`drat-trim` has a `parse`-time path that prints `c trivial UNSAT` / `s VERIFIED`
(`drat-trim.c:1480`) *before* the proof is ever examined. Several ordinary malformations
drive the parser into it. Every case below uses a **satisfiable** formula and an **empty**
proof file, with the real binaries:

```
well-formed satisfiable CNF (control)                       -> NOT_VERIFIED
one short comment line BETWEEN clauses                      -> VERIFIED   <== FALSE
comment line before the header (control)                    -> NOT_VERIFIED
header clause count too HIGH (3 declared, 2 present)        -> VERIFIED   <== FALSE
header clause count too LOW (control)                       -> NOT_VERIFIED
missing trailing 0 on the last clause                       -> VERIFIED   <== FALSE
duplicated p line                                           -> VERIFIED   <== FALSE
comment longer than drat-trim's 64KiB line buffer           -> VERIFIED   <== FALSE
```

A **single stray `c` comment line between two clauses** is enough. `header count too high` is
particularly pointed: `oracle.run_solver` passes kissat `--relaxed`, commented
*"tolerate header/clause-count slack"* — deliberately disabling the one check that would
otherwise have caught exactly this malformation before drat-trim rubber-stamped it.

### D1c — end to end: `is_verified_unsat == True` for a satisfiable formula — **CRITICAL**

```
[HOLE] D1c solve_and_verify -> verdict=UNSAT, checker_verdict=VERIFIED,
  is_verified_unsat=True, proof_bytes=0
  -- the formula is SATISFIABLE, the proof file is 0 bytes,
     and drat-trim never examined it
```

Only kissat is stubbed, and only to supply the exit code 20 that the real solver supplies for
the formula the project actually intends to solve; drat-trim, `check_proof` and
`solve_and_verify` are the real code paths. Nothing between the checker and the catalog
asserts that the proof was non-empty or that the checker consumed it. Ground rule 2 — *"an
UNSAT is not a result until a proof checker says VERIFIED"* — degrades silently to *"kissat
said UNSAT"*, and `proof_bytes = 0` sits right there in the record, unchecked.

Reachability: **not currently reachable.** `EncodingResult.to_dimacs()` emits
`p cnf {n_vars} {len(clauses)}` followed by exactly that many `0`-terminated lines and no
comments, and D1d audits all 14 CNFs in `artifacts/` as well-formed. The exposure is any
future change that adds a provenance comment header, dedups clauses after counting, or
processes an externally supplied CNF.

### D2 — `check_proof` has no integrity check on the checker — **MAJOR**

`check_proof` decides by `if "s VERIFIED" in proc.stdout + proc.stderr`. It ignores the exit
code, is not line-anchored, and includes stderr. Four ways to get VERIFIED with nothing
verified:

```
prints 's VERIFIED' but exits 1 (crash after the verdict)          -> VERIFIED
prints 's VERIFIED' inside a COMMENT line and then NOT VERIFIED    -> VERIFIED
echoes an attacker-controlled path containing the magic string     -> VERIFIED
prints the string on stderr only                                   -> VERIFIED
```

These are not hypothetical output shapes: drat-trim has **two** code paths that echo external
strings into stdout — `printf("\rc error opening \"%s\".\n", argv[i])` (L1427/1432/1461,
echoes a **file path**) and `printf("c ERROR: comment longer than %zu characters: %s\n", …)`
(L1143, echoes a **line from either input file**). `verify_candidate.py` takes its `tag`
straight from `sys.argv[1]` and that tag becomes the proof filename. Also note the
`elif "s TRIVIALLY UNSAT" in text: verdict = "VERIFIED"` branch is dead — this drat-trim
prints `c trivial UNSAT` + `s VERIFIED`, and D1b shows that path should be treated as
**suspicious**, not as a pass.

### D3 / D3b — exit-code mapping and `is_verified_unsat` (ok)

```
exit 0 with no output                              -> TIMEOUT
exit 20 (UNSAT) but writes NO proof file           -> UNSAT   (then UNSAT_UNVERIFIED)
exit 20 and writes an EMPTY proof file             -> UNSAT
exit 10 (SAT) but prints no model                  -> SAT     (model=[] -> caught by D4)
exit 10 and prints a model                         -> SAT
exit 1 (crash)                                     -> ERROR
exit 42 (unknown)                                  -> ERROR
claims UNSATISFIABLE in stdout but exits 10        -> SAT      (exit code wins, correct)
```

`is_verified_unsat` was probed over all 35 `verdict × checker_verdict` combinations and is
`True` for exactly `("UNSAT", "VERIFIED")` — not for `"verified"`, `"s VERIFIED"`, or
`"UNSAT_UNVERIFIED" + "VERIFIED"`. `solve_and_verify(..., want_proof=False)` on a real UNSAT
correctly returns `UNSAT_UNVERIFIED` with `is_verified_unsat == False`; with a proof it
returns `UNSAT/VERIFIED`. The **one gap** is `exit 20 + empty proof file`, which reaches
`check_proof` because the code tests `os.path.exists(proof_path)` and not
`os.path.getsize(proof_path) > 0` — that is the door D1c walks through.

### D4 — SAT with a failing model check is downgraded (ok)

```
[ok ] D4 honest k=4 Moser spindle -> SAT with model_check ok (11 edges re-derived exactly);
  a monochromatic model and an empty model both produced verdict SAT_MODELCHECK_FAILED;
  both model checkers rejected them
```

`pipeline.assess` was driven with `solve_and_verify` mocked to return (a) a model colouring
every vertex colour 0 and (b) an empty model. Both produced `SAT_MODELCHECK_FAILED`, and both
`check_coloring_against_points` (brute-force exact, no filter) and
`check_coloring_against_edges` rejected them independently. The empty-model case matters
because `run_solver` parses only lines starting with `v ` — a solver that prints no witness
yields `model=[]`, and that is caught here rather than recorded as a colouring.

### D5 — can an unverified row reach the leaderboard? **No.** (ok)

```
[ok ] D5 14 rows inserted covering every verdict x checker_verdict combination incl. case
  and substring variants of 'VERIFIED': only the (UNSAT, VERIFIED) row surfaced, in the
  leaderboard and in already_refuted; k filtering is exact
```

Rows inserted into a temp catalog: `UNSAT × {NULL, NOT_VERIFIED, CHECKER_TIMEOUT,
CHECKER_INCONCLUSIVE, 'verified', 's VERIFIED', ' VERIFIED'}`, `UNSAT_UNVERIFIED × VERIFIED`,
`SAT × VERIFIED`, `SAT_MODELCHECK_FAILED × VERIFIED`, `TIMEOUT × VERIFIED`,
`ERROR × VERIFIED`, and one genuine `UNSAT × VERIFIED` at n=100. Only n=100 surfaced from
`leaderboard()` and only its `graph_hash` satisfied `already_refuted()`; `k=5` returned
nothing for rows recorded at `k=4`. SQL string equality is exact, so the substring and case
variants that fool `check_proof` do **not** fool the catalog query.

### Recommended fixes for D

1. `check_proof`: require `proc.returncode == 0` **and** a line that is exactly `s VERIFIED`
   (`any(l.strip() == "s VERIFIED" for l in proc.stdout.splitlines())`), and drop stderr from
   the decision.
2. Treat `c trivial UNSAT` as `CHECKER_TRIVIAL` and refuse it unless the CNF genuinely
   contains an empty clause. Delete the dead `s TRIVIALLY UNSAT` branch.
3. `solve_and_verify`: require `os.path.getsize(proof_path) > 0`, and record/assert the number
   of lemmas drat-trim actually checked (its stdout reports them) so a vacuous verification
   cannot masquerade as a real one.
4. Validate the CNF before handing it to any solver: header counts, no comment lines, every
   clause `0`-terminated. `tests/adv2_proof.py::d1d` is a ready-made version of this check.
5. Drop `--relaxed` from the kissat invocation. It suppresses the mismatch report on exactly
   the malformation that makes drat-trim unsound, and the encoder's header is always exact
   anyway.
6. Cross-check with a second, independently written checker on any record claim.

---

## Reproduction

```
cd /home/user/CustomLLM
python tests/adv2_float.py      # exits 1: A1 A2 A3 A4 A8
python tests/adv2_field.py      # exits 1: B5b B6   (B1-B5, B7 pass)
python tests/adv2_encoding.py   # exits 1: C2b      (C1, C2, C3, C3b, C4 pass)
python tests/adv2_proof.py      # exits 1: D1b D1c D2 (D1, D1d, D3, D3b, D4, D5 pass)
```

Runtime: A ≈ 4 min (binary searches over coefficient scales), B ≈ 2 min, C ≈ 6 min
(11200 SAT calls plus exhaustive assignment enumeration), D ≈ 1 min.
