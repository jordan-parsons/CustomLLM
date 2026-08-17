# Pass 1 report

Wall clock: ~1h50m from cold start (empty repo, no solvers installed).

## What was built
Everything. The repo was empty apart from a one-line README, and the spec's
assumed tooling was entirely absent. Built from source: kissat, CaDiCaL,
drat-trim. Installed: python-flint 0.9.0, pysat, networkx. `pynauty` will not
build on this host, so canonicalization is WL-hash bucketing plus exact VF2
isomorphism confirmation — sound, because a dedup decision is never taken
without an isomorphism proof.

## Candidates generated / deduped / solved / verified
| stage | count | notes |
|---|---|---|
| published graphs acquired | 13 | from github.com/marijnheule/CNP-SAT |
| of those, 5-chromatic (k=4 UNSAT) | 9 | 510,517,529,553,610,633,803,826,874 |
| of those, 4-colourable traps | 4 | S199, L403, G2167 (Q(√3,√11)); T721 (Q(√2,√3)) |
| fully proof-verified (DRAT + drat-trim) | 1 | the 510-vertex graph, both k=4 and k=5 |
| ambient pools built | 1 | union of the 9 = 2306 points / 13569 exact edges |
| MUS descent runs completed | 0 at first attempt | design fault, see "what went wrong" |

## Current best
**510 vertices**, verified. k=4 UNSAT, kissat, 7160065-byte DRAT,
drat-trim **VERIFIED**, proof sha256 `71dc6bcbb371ebb8…`; k=5 SAT with an
independent model check that re-derived all 2504 edges from exact coordinates.
This is **one vertex worse than the record** (509, Parts 2020) — a verified
reproduction, not a new result.

## What was learned about which generators are productive

**Productive.**
- *Published-data acquisition.* Far and away the highest-value move. Turned a
  blocked project (arXiv unreachable) into a working M2 baseline in one step.
- *Exact edge re-derivation as a validator.* Re-deriving edges from coordinates
  and diffing against published edge lists caught nothing — which is the point:
  five graphs matched exactly in both directions (510/2504, 517/2579, 553/2722,
  403/2112, 199/888). That single test validates the parser, the field
  arithmetic, and the detector jointly, and it is far stronger evidence than any
  unit test I could have invented.

**Barren, and why.**
- *Single-vertex deletion from the 510 graph.* Dead on arrival. The graph is
  vertex-critical: the k=4 UNSAT core is all 510 vertices and all 510 deletion
  tests return 4-colourable. **Killed.** Corollary worth keeping: Parts' 509 is
  not a subgraph of Heule's 510, so the two records are structurally different
  graphs, not a nested chain.
- *UNSAT-core reduction on the 510 graph.* The core is the whole graph, so core
  reduction is a no-op here. **Killed** as a standalone move; retained as a cheap
  first step on larger pools where it does bite.
- *Voronov et al. series 1 / series 2 as starting material.* 3877 and 64513
  vertices — an order of magnitude above 510, and their own authors did not beat
  509 from them. **Deprioritised**, not formally killed, since they live in a
  different field and could yield different local minima.
- *Voronov series-2 rotation data.* Genuinely outside the arithmetic layer: it
  uses nested radicals and complex numbers, e.g.
  `Sqrt[5 - 3*Sqrt[2] + Sqrt[3] + 3*Sqrt[6]]`, which no multiquadratic field can
  express. Recorded as a real representational limitation rather than worked
  around.

## What went wrong (and the fix)
The first search driver put a time budget on the batch-descent phase but not on
the single-vertex deletion passes. On the full 2306-vertex encoding each
`is_unsat` call carries ~2300 assumption literals, so one pass ran far past any
useful horizon and **zero runs completed in 28 minutes**. Killed and rewritten
as two stages: coarse descent on the pool, then a *fresh, much smaller* encoding
built on the induced subgraph, plus a hard deadline checked inside the deletion
loop and incremental logging so an unfinished run still reports its best set.

## Reallocation
- Killed: single-deletion and core-reduction on the 510 graph (provably stuck).
- Reallocated to: enlarging the ambient pool, which is the only move that can
  work given criticality. A subset of a vertex-critical graph cannot be smaller
  and still 5-chromatic, so **the ambient set must grow before minimisation can
  win.** Constructor C1 is closing the 510 vertex set under the recovered
  rotation group (θ₀ with cos = √33/6, β with cos = 7/8) and generating
  neighbour-completion points.
- Queued: basin-hopping ("add a points, delete a+d") over the enlarged pools,
  implemented in `src/hn/perturb.py` and waiting on those pools.

## Honest assessment
Objective A is a long shot from here. The only 5-chromatic material available is
one coordinate system whose smallest member is already vertex-critical, the
record holder's graph is not obtainable on this host, and 509 was produced by an
expert doing exactly this minimisation with more compute. Objective B is an open
problem and nothing in this pass moved toward it.
