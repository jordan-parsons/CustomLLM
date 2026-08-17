# CONSTRUCTOR C1 — Ambient point pools for a sub-509 5-chromatic unit-distance graph

Agent: CONSTRUCTOR C1. Deliverable: **candidate ambient point pools**, not colourability
verdicts. 32 pools saved to `/home/user/CustomLLM/data/pools/`.

All pools live in `Q(sqrt3, sqrt5, sqrt11)` (dim 8 over Q). Every coordinate is an exact
`FieldElem`; every unit edge in every count below was decided by exact arithmetic in the
number field. Floats appear only as a candidate-pair prefilter, never as a decision.

---

## 1. Soundness statement

| Requirement | How it is met |
| --- | --- |
| No float decides anything | Every edge count comes from `hn.detect.detect_edges` (float grid prefilter, then **mandatory** `Point.is_unit_from` exact confirmation). New helpers in `hn/pools.py` follow the identical contract and re-verify every point they emit with `is_unit_from`. |
| Every point exact in a MultiQuadField | All construction is `+`, `-`, exact scalar `*`, exact `Rotation.apply`, and exact field square roots. No coordinate is ever introduced that cannot be represented. |
| Exact dedup | `point.dedup_points` / `Point.key()` throughout; `pools.save_pool` **refuses** to write a pool that is not exactly deduplicated. |
| Rotations are real isometries | `Rotation.__init__` asserts `cos^2 + sin^2 == 1` exactly and raises otherwise. All four generators below passed. |
| Round-trip fidelity | All 32 pool files reload exactly, reproduce their recorded edge count, and re-pass the 510 sanity check. **0 failures.** |

Two new routines were needed and are worth flagging because they are the only genuinely
new mathematics in this deliverable:

- **`pools.field_sqrt(e)`** — exact square root inside a multiquadratic field, by descent on
  the highest radical (`e = A + B*sqrt(r)` forces `sqrt(A^2 - r*B^2)` to lie in the subfield
  omitting `sqrt(r)`, so the recursion runs on a strictly shrinking allowed-generator mask).
  It is **self-certifying**: at every recursion level the candidate root is re-verified by
  exact multiplication, so a bug can only ever produce `None`, never a wrong root. Callers
  never have to trust it. Validated: recovers 300/300 random squares, returns `None` on
  every non-square, never returned an unverified value.
- **`pools.circle_intersections(a,b)`** — the (at most 2) points at exact distance 1 from
  both `a` and `b`, which exist in the field iff `q*(4-q)/4` is a square there
  (`q = |a-b|^2`). Every returned point is re-verified with `is_unit_from` against both
  centres.

### Completeness cross-check (the strongest validation here)

`P3_nc510_deg2` claims to be **every** field point at unit distance from >= 2 vertices of
the 510. If that enumeration is complete, then for *any* other pool, every point of it with
exact 510-degree >= 2 must already be in `P3_nc510_deg2`. Tested on four independently
generated pools:

| Probe pool | n | its points with deg_510 >= 2 | not found in `P3_nc510_deg2` |
| --- | --- | --- | --- |
| `P1e_union_rot_L1` | 14189 | 1884 | **0** |
| `P2b_510_plus_J` | 9168 | 1526 | **0** |
| `P1f_union_D6` | 10657 | 1609 | **0** |
| `P0_heule_union` | 2306 | 1064 | **0** |

Zero misses across 6082 independently-constructed high-degree points. `field_sqrt` is
complete, not merely sound, on the geometry that actually occurs here.

---

## 2. The rotation generators (coordinator's data, independently confirmed)

Built with `Rotation.from_cos_sin`; the constructor's exact `cos^2+sin^2==1` assertion
passed for all four.

| Name | cos | sin | angle | check |
| --- | --- | --- | --- | --- |
| `theta0` | `sqrt33/6` | `sqrt3/6` | 16.778655 deg | 33/36 + 3/36 = 1 |
| `alpha` (spindle) | `5/6` | `sqrt11/6` | 33.557310 deg | 25/36 + 11/36 = 1 |
| `beta` | `7/8` | `sqrt15/8` | 28.955024 deg | 49/64 + 15/64 = 1 |
| `R60^k` | `1/2` | `sqrt3/2` | 60k deg | lattice symmetry |

**`theta0^2 == alpha` holds exactly** (coefficient-for-coefficient), so `theta0` really is
the atomic half-spindle rotation.

Points of each published set mapped **back into that set** by each rotation about the origin:

| set | n | theta0 | alpha | beta | R60 | R120 | R180 | mirror x->-x | mirror y->-y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 510 | 510 | **152** | 67 | **94** | 346 | **482** | 343 | 355 | 232 |
| S199 | 199 | 55 | 25 | **1** | 199 | 199 | 199 | 199 | 199 |
| L403 | 403 | 154 | 49 | **1** | 235 | 403 | 235 | 403 | 235 |
| union 2306 | 2306 | 713 | 386 | 294 | 1108 | 1111 | 1721 | 701 | 665 |

Both of the coordinator's claims reproduce exactly: `theta0` beats `alpha` more than 2:1 on
the 510 (152 vs 67), and `beta` maps 94 of the 510 but only 1 of S199 and 1 of L403 — `beta`
is specifically the small-record-graph generator, absent from de Grey's originals.

**New finding: the 510 is nearly C3-symmetric.** R120 maps 482 of its 510 vertices back into
itself; the full C3 closure adds only **40** points (`P1b_510_C3`, 550 points). Mirror
`x->-x` maps 355 back. See the ranking notes — this has search-strategy consequences.

### Productive rotation centres (exactly derived, exactly verified)

Since `|p - R(p)| = 2*d*sin(angle/2)` with `d = |p - c|`, a rotation about a non-origin
centre `c` creates *new unit edges* only at one specific radius:

| rotation | `2 sin(angle/2)` | radius d giving a unit edge | verified exactly |
| --- | --- | --- | --- |
| `R60` | 1 | `d = 1` | yes |
| `R120` | `sqrt3` | `d = 1/sqrt3` | yes |
| `alpha` | `1/sqrt3` | `d = sqrt3` (classic spindling) | yes |
| `beta` | `1/2` | `d = 2` | yes |
| `theta0` | — | `d^2 = 6 + sqrt33` | (rare in the pool) |

So a good `alpha`-centre has many pool points at squared distance 3, a good `beta`-centre at
squared distance 4, a good `R60`-centre at squared distance 1. Within the 510 there are 1204
pairs at squared distance 3, 596 at squared distance 4, and 2504 at squared distance 1;
centres were chosen by that exact count.

### Building blocks confirmed

- **H** = hexagon of side 1 plus centre: **7 points, 12 unit edges** — matches.
- **J** = `{(a,b) in Z^2 : a^2+ab+b^2 <= 7}` in Eisenstein coordinates: **31 points, 72 unit
  edges** — matches de Grey's J exactly. Saved as `PJ31_degrey`.
- **Only 148 distinct exact unit vectors** are realised as differences of unit-distance pairs
  across the whole 2306-point pool (all 148 confirmed to be exact unit vectors). The ambient
  algebraic structure is far more rigid than the point count suggests.

---

## 3. Pool table

`510?` = contains the 510 vertex set as an exact subset. `e510` = unit edges induced on
those 510 vertices (**must be 2504** — this is the sanity check required in (c); it passed
for every pool that contains the set, both at generation time and again on reload).
`k=4` from Cadical153 on the `hn.cnf` encoding with a verified symmetry-breaking clique.

All files are `/home/user/CustomLLM/data/pools/<name>.json`.

| pool | strategy + exact parameters | n | m | max deg | mean deg | 510? | e510 | k=4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PJ31_degrey` | de Grey's J: `{a^2+ab+b^2 <= 7}`, basis `(1,0)`, `omega=(1/2,sqrt3/2)` | 31 | 72 | 6 | 4.65 | no | – | SAT |
| `P4a_unitvec_star` | S4 depth-1: origin + all 148 realised unit vectors | 149 | 294 | 148 | 3.95 | no | – | SAT |
| `P510` | seed: published 510-vertex graph | 510 | 2504 | 36 | 9.82 | **yes** | **2504** | UNSAT |
| `P1b_510_C3` | S1: 510 closed under `C3 = <R120>` about origin (fixpoint) | 550 | 2775 | 36 | 10.09 | **yes** | **2504** | UNSAT |
| `P4b_ring2_deg6` | S4 depth-2: 510 + `{u+v : u,v in U}` with deg_510 >= 6 (`\|U\|=148`, `\|U+U\|=10953`) | 562 | 2883 | 43 | 10.26 | **yes** | **2504** | UNSAT |
| `P4b_ring2_deg4` | same, deg_510 >= 4 | 673 | 3555 | 46 | 10.57 | **yes** | **2504** | UNSAT |
| `P4b_ring2_deg3` | same, deg_510 >= 3 | 724 | 3792 | 47 | 10.48 | **yes** | **2504** | UNSAT |
| `P2f_S199_plus_H` | S2 Minkowski: `S199 (+) H` | 847 | 5058 | 30 | 11.94 | no (241) | – | **SAT** |
| `P1a_510_D6` | S1: 510 closed under dihedral `D6` = `<R60, mx, my>` about origin (fixpoint) | 907 | 4902 | 54 | 10.81 | **yes** | **2504** | UNSAT |
| `P3_nc510_deg5` | S3 completion: 510 + all field points at exact unit distance from >= 5 of the 510 | 908 | 5331 | 44 | 11.74 | **yes** | **2504** | UNSAT |
| `P3_nc510_deg4` | S3 completion, >= 4 | 1173 | 7284 | 46 | 12.42 | **yes** | **2504** | UNSAT |
| `P2c_510_plus_TRI` | S2 Minkowski: `510 (+)` unit triangle (3 pts) | 1189 | 6995 | 38 | 11.77 | **yes** | **2504** | UNSAT |
| `P3_nc510_deg3` | S3 completion, >= 3 (1202 new pts) | 1712 | 11374 | 47 | 13.29 | **yes** | **2504** | UNSAT |
| `P1g_510_R60_at4centres` | S1 non-origin: 510 + `R60^{+-1}` about the 4 best `d=1` centres (510[0,90,93,96], sqdist-1 degrees 36/24/24/24) | 1854 | 10849 | 42 | 11.70 | **yes** | **2504** | UNSAT |
| `P1c_510_rot_L1` | S1: 510 + all word-length-1 images of `theta0^{+-1}, beta^{+-1}, R60^{k=1..5}, mx, my` about origin | 2149 | 12083 | 102 | 11.25 | **yes** | **2504** | UNSAT |
| `P3_ncD6_deg4` | S3 completion of the 907-pt `D6` closure, >= 4 | 2155 | 14478 | 66 | 13.44 | **yes** | **2504** | UNSAT |
| `P0_heule_union` | baseline: exact union of the 9 Heule sets (510,517,529,553,610,633,803,826,874) | 2306 | 13569 | 64 | 11.77 | **yes** | **2504** | UNSAT |
| `P2a_510_plus_H` | S2 Minkowski: `510 (+) H` | 2378 | 15605 | 42 | 13.12 | **yes** | **2504** | UNSAT |
| `P3_ncD6_deg3` | S3 completion of the 907-pt `D6` closure, >= 3 (2046 new pts; 254886 pairs < 2, 40491 realised) | 2953 | 20796 | 66 | **14.09** | **yes** | **2504** | UNSAT |
| `P2d_S199_plus_J` | S2 Minkowski: `S199 (+) J` | 3115 | 20838 | 30 | 13.38 | no (245) | – | **SAT** |
| `P1g_510_alpha_at4centres` | S1 non-origin: 510 + `alpha^{+-1}` about the 4 best `d=sqrt3` centres (510[0,1,2,3], sqdist-3 degrees 30/10/10/10) | 3313 | 20157 | 72 | 12.17 | **yes** | **2504** | UNSAT |
| `P5a_super_510` | **S1+S2+S3+S4 union**: `P3_nc510_deg3 + P1c_510_rot_L1 + P1a_510_D6 + P4b_ring2_deg3 + P2a_510_plus_H` | 4279 | 27948 | 102 | 13.06 | **yes** | **2504** | UNSAT |
| `P3_nc510_deg2` | S3 completion, >= 2 — **the complete 2-neighbour completion** (3839 new pts; 86490 pairs < 2, 18852 realised) | 4349 | 25647 | 56 | 11.79 | **yes** | **2504** | UNSAT |
| `P1g_510_beta_at4centres` | S1 non-origin: 510 + `beta^{+-1}` about the 4 best `d=2` centres (510[0,217,211,220], sqdist-4 degrees 24/6/6/6) | 4393 | 22987 | 84 | 10.47 | **yes** | **2504** | UNSAT |
| `P1h_510_multi_centre` | S1 non-origin: 510 + `alpha`,`beta`,`R60` (both signs) about the 2 best centres of each | 4572 | 25219 | 120 | 11.03 | **yes** | **2504** | UNSAT |
| `P2e_L403_plus_J` | S2 Minkowski: `L403 (+) J` | 5167 | 40548 | 30 | 15.70 | no (375) | – | **SAT** |
| `P1d_510_rot_L2` | S1: 510 under words of length <= 2 in the same 11 generators (levels 510 -> 2149 -> 5224) | 5224 | 31401 | **192** | 12.02 | **yes** | **2504** | UNSAT |
| `P5b_super_510_wide` | **S1+S2+S3+S4 union, wide**: as `P5a` but with the full deg>=2 completion, plus `(+)TRI` and deg>=4 | 6368 | 38789 | 102 | 12.18 | **yes** | **2504** | UNSAT |
| `P2b_510_plus_J` | S2 Minkowski: `510 (+) J` | 9168 | 66635 | 42 | 14.54 | **yes** | **2504** | UNSAT |
| `P1f_union_D6` | S1: 2306 union closed under `D6` about origin (fixpoint) | 10657 | 74070 | 96 | 13.90 | **yes** | **2504** | UNSAT |
| `P2g_union_plus_H` | S2 Minkowski: `2306 union (+) H` | 11588 | 90296 | 70 | **15.58** | **yes** | **2504** | UNSAT |
| `P1e_union_rot_L1` | S1: 2306 union + all word-length-1 images (same 11 generators) | 14189 | 95925 | 138 | 13.52 | **yes** | **2504** | UNSAT |

Edges were detected exactly for **all 32 pools** — none exceeded the budget (largest:
14189 points / 95925 edges, 24 s). Total on disk: 12.98 MB.

### On the k=4 column

Every pool containing the 510 is k=4 UNSAT *necessarily*, because it contains a 5-chromatic
subgraph. Those UNSATs are therefore a **pipeline-integrity check**, not evidence of a
smaller graph: a SAT there would have proved a coordinate got corrupted during rotation /
Minkowski / completion. None did.

The genuinely informative results are the negative ones: `P2f_S199_plus_H`,
`P2d_S199_plus_J` and `P2e_L403_plus_J` are all **k=4 SAT**. Minkowski-summing the
4-colourable building blocks with H or J does **not** create 5-chromaticity, even at 5167
points and mean degree 15.7. That branch of strategy 2 is a dead end and should not be
minimised.

---

## 4. Substitutability metric

A 510 vertex can only be traded away if the pool offers alternative points of comparable
degree (the 510 itself has mean degree 9.82). Count of **new** (non-510) points by degree
*within the pool*:

| pool | n | new pts | deg>=10 | deg>=15 | deg>=20 | % of new with deg>=10 |
| --- | --- | --- | --- | --- | --- | --- |
| `P1b_510_C3` | 550 | 40 | 2 | 0 | 0 | 5.0 |
| `P4b_ring2_deg3` | 724 | 214 | 49 | 6 | 0 | 22.9 |
| `P1a_510_D6` | 907 | 397 | 169 | 24 | 0 | 42.6 |
| `P3_nc510_deg5` | 908 | 398 | 108 | 0 | 0 | 27.1 |
| `P3_nc510_deg4` | 1173 | 663 | 330 | 6 | 0 | 49.8 |
| `P3_nc510_deg3` | 1712 | 1202 | 743 | 140 | 2 | 61.8 |
| `P1c_510_rot_L1` | 2149 | 1639 | 848 | 169 | 33 | 51.7 |
| `P3_ncD6_deg4` | 2155 | 1645 | 1165 | 292 | 100 | 70.8 |
| `P0_heule_union` (baseline) | 2306 | 1796 | 1038 | 316 | 67 | 57.8 |
| `P2a_510_plus_H` | 2378 | 1868 | 1380 | 362 | 16 | 73.9 |
| `P3_ncD6_deg3` | 2953 | 2443 | 1807 | 716 | 184 | 74.0 |
| `P1g_510_alpha_at4centres` | 3313 | 2803 | 1817 | 653 | 158 | 64.8 |
| `P5a_super_510` | 4279 | 3769 | 2563 | 758 | 109 | 68.0 |
| `P3_nc510_deg2` | 4349 | 3839 | 1715 | 573 | 145 | 44.7 |
| `P1h_510_multi_centre` | 4572 | 4062 | 2190 | 502 | 87 | 53.9 |
| `P1d_510_rot_L2` | 5224 | 4714 | 2764 | 949 | 331 | 58.6 |
| `P5b_super_510_wide` | 6368 | 5858 | 3178 | 1095 | 244 | 54.3 |
| `P2b_510_plus_J` | 9168 | 8658 | 7726 | 3632 | 1028 | 89.2 |
| `P1f_union_D6` | 10657 | 10147 | 8089 | 3641 | 1303 | 79.7 |
| `P2g_union_plus_H` | 11588 | 11078 | 10033 | 5388 | 1953 | 90.6 |
| `P1e_union_rot_L1` | 14189 | 13679 | 10214 | 4525 | 1556 | 74.7 |

---

## 5. Ranking — most promising for a 5-chromatic subgraph below 509 vertices

**Tier 1 — minimise these first.**

1. **`P3_nc510_deg3`** (1712 pts, 11374 edges). The best promise-per-vertex. It is
   *mathematically canonical*: it contains **every** field point with >= 3 unit neighbours in
   the 510, so it is provably closed with respect to single-vertex substitution at that
   threshold — if any point of the plane can replace a 510 vertex and keep >= 3 of its
   attachments, that point is in this pool. Only 1202 new points, 62% of them degree >= 10,
   and mean degree 13.29 already exceeds the 2306 baseline's 11.77 at three-quarters the
   size. Small enough for a real MUS run.
2. **`P3_ncD6_deg3`** (2953 pts, 20796 edges, mean degree **14.09**). Same completion idea
   but seeded on the `D6`-symmetrised 510 so the pool is genuinely symmetric. 1807
   substitutable new points, 184 of degree >= 20. Highest density of any pool under 3000
   points. This is my single best bet: symmetry lets a minimiser delete whole orbits, and
   orbit-deletion is exactly the move a vertex-critical graph forbids one vertex at a time.
3. **`P5a_super_510`** (4279 pts, 27948 edges, max degree 102). All four strategies unioned;
   2563 substitutable new points. The right pool if the minimiser can afford ~4300
   presence literals — it dominates each of its five constituents.

**Tier 2 — strong, larger.**

4. **`P1d_510_rot_L2`** (5224 pts, max degree **192**, 331 new points of degree >= 20). The
   depth-2 `theta0`/`beta` rotation closure. Highest-degree points anywhere in the
   collection. Rotation closure produces points that sit on *many* unit circles at once,
   which is what breaks the vertex-critical trap.
5. **`P2b_510_plus_J`** (9168 pts, 66635 edges, 89.2% of new points at degree >= 10). `J` is
   the summand de Grey's own construction uses, so this is the most "natural" enlargement.
6. **`P5b_super_510_wide`** (6368 pts) — `P5a` plus the complete deg>=2 completion.
7. **`P1c_510_rot_L1`** (2149 pts, max degree 102) — cheapest way to get degree-100 points.

**Tier 3 — large ambient sets, for a scalable minimiser.**

8. **`P2g_union_plus_H`** (11588 pts, mean degree **15.58**, 90.6% substitutable) — densest
   pool built.
9. **`P1e_union_rot_L1`** (14189 pts) — the biggest, and the one whose 5-chromatic content is
   least likely to be a re-run of the 510.
10. **`P1f_union_D6`** (10657 pts) — symmetric version of the same.

**Do not minimise.** `P2d_S199_plus_J`, `P2e_L403_plus_J`, `P2f_S199_plus_H` — all
**k=4 SAT**, hence 4-colourable and incapable of containing a 5-chromatic subgraph.
`PJ31_degrey` and `P4a_unitvec_star` are 4-colourable primitives kept only as summands.

### Two structural findings that should change the search strategy

- **The 510 is nearly C3-symmetric** (R120 maps 482 of 510 vertices back; the C3 closure adds
  only 40 points). Its vertex-criticality is a statement about deleting *one* vertex. A
  C3-orbit-restricted search over `P1b_510_C3` (550 pts) or `P3_ncD6_deg3` treats vertices in
  orbits of 3, deletes 3 at a time, and never asks the question criticality already answered.
  Given that 509 is only 1 below 510, and 510 = 3 x 170 exactly, a symmetric graph on
  3k <= 507 vertices is a very plausible shape for the record.
- **Only 148 distinct unit vectors** exist in the whole 2306-point pool, and only 18852 of
  the 86490 sub-diameter vertex pairs of the 510 have their unit-circle intersections inside
  the field (21.8%). The ambient set is much more rigid than its size suggests — which is why
  the complete 2-neighbour completion is finite and small (3839 points). It also means edge
  detection on these pools can be done by exact hash lookup on the 148 difference vectors,
  with **zero** floating point, if a future step wants that.

---

## 6. Loader

Format: `{"field": [3,5,11], "n": N, "points": [{"x": [[num,den] x 8], "y": [...]}, ...],
"meta": {...}}`. This is deliberately the same `field`/`points` shape `UDGraph.to_dict()`
emits, so either loader reads either file. Verified: all 32 files round-trip exactly.

```python
import sys
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.pools import load_pool, pool_stats
from hn.detect import detect_edges
from hn.graph import UDGraph

# (a) as an exact point pool
points, field = load_pool("/home/user/CustomLLM/data/pools/P3_ncD6_deg3.json")
print(len(points), field)                       # 2953 Q(sqrt3, sqrt5, sqrt11)
print(len(detect_edges(points)))                # 20796  (re-derived exactly)

# (b) as a UDGraph -- edges are re-detected exactly, never read from the file
g = UDGraph.from_dict({**__import__("json").load(
        open("/home/user/CustomLLM/data/pools/P3_ncD6_deg3.json")), "edges": []})
print(g)                                        # UDGraph(n=2953, m=20796, ...)

# (c) the 510 sanity check, on any pool
p510, _ = load_pool("/home/user/CustomLLM/data/pools/P510.json")
K = {p.key() for p in p510}
sub = [p for p in points if p.key() in K]
assert len(sub) == 510 and len(detect_edges(sub)) == 2504
```

Reusable code added: `/home/user/CustomLLM/src/hn/pools.py` (`save_pool`, `load_pool`,
`pool_stats`, `field_sqrt`, `circle_intersections`, `neighbour_completion`,
`detect_pairs_at_sqdist`, `embed_points`). No existing audited module was modified.
