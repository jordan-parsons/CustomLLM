# Pass 2 report

## Candidates generated / deduped / solved / verified
| stage | count |
|---|---|
| ambient pool (union of the 9 published 5-chromatic graphs) | 2306 points / 13569 exact unit edges, k=4 UNSAT |
| deletion-MUS fixpoint runs from published starts | 8 (510, 517, 529, 553 × 2 seed families) |
| distinct local minima found | **0 new** — every run returned its own start |
| basin-hop perturbation iterations | small (single digits per worker per round; see "the real constraint") |
| improvements below 510 | **0** |

## Current best
Unchanged: **510 vertices**, verified (k=4 UNSAT, drat-trim VERIFIED, checked
proof sha256 `71dc6bcbb371ebb8…` / 7160065 B; archived gz `4c2c07760d195942…` /
1984991 B). Record is 509. Still not a record.

## What was learned

### 1. The corpus is uniformly vertex-critical (the load-bearing finding)
Deletion-MUS to fixpoint returns the input unchanged for 510, 517, 529 and 553,
and the exhaustive per-vertex sweep on 510 (run independently twice — by us and
by Adversary 1) shows all 510 deletions give 4-colourable graphs, with the k=4
UNSAT core equal to the whole vertex set.

This is not bad luck, it is a structural fact, and it **falsifies the spec's
§7 premise** that "beating 509 is a minimization problem, not a construction
problem." That premise silently assumes un-minimised starting material. Heule and
Parts already ran this minimisation to fixpoint, so from published graphs the
minimiser has nothing left to remove. Reaching ≤508 requires *constructing* new
ambient points and then deleting more than were added.

### 2. Two search-design faults found by measurement, not intuition
- **Encoding size.** Solving the 2306-vertex pool encoding under ~2300 assumption
  literals is ~50× slower per call than the 510-vertex encoding (0.09 s/call).
  The first two drivers completed **zero** runs in 28 minutes. Fix: never encode
  the pool; build a fresh induced graph per candidate set.
- **Deletion order.** With a uniform order over B ∪ A, the few added points get
  tried and deleted early and the pass collapses straight back to the critical
  incumbent. Fix: try B's own vertices first so the added constraints stay in
  play. This is the difference between a search that cannot possibly succeed and
  one that merely probably won't.

### 3. The real constraint is sampling rate, not algorithm quality
One basin-hop iteration = one full deletion pass over ~540 vertices × 2–4 passes
= roughly 3–15 minutes on this host, and the 4 cores are shared with three
adversary/constructor agents. That buys single-digit perturbation samples per
worker per round. Parts reached 509 with far more compute and expert-guided
construction. **Honest read: the sampling rate is several orders of magnitude
short of what this approach needs**, and no amount of tuning within a 4-core
container closes that gap.

## Strategies killed this pass, and why
- **Deletion-only minimisation from any published graph.** Provably stuck
  (criticality). Killed, permanently, with a proof rather than a hunch.
- **UNSAT-core reduction as a standalone move on minimised graphs.** The core is
  the entire vertex set, so it is a no-op. Retained only as a cheap first step on
  genuinely redundant pools.
- **MUS descent over the 2306-point pool encoding.** Killed on measured cost
  grounds (~50× per-call penalty). Superseded by small induced encodings.
- **Uniform-order basin hopping.** Killed as structurally incapable of escaping a
  vertex-critical incumbent.
- **Voronov series 1 / series 2 (3877 and 64513 vertices) as starting material.**
  Deprioritised: an order of magnitude larger, and their own authors did not beat
  509 from them.

## Positive results this pass
- **510 vertices / 2503 edges is 5-chromatic** (Adversary 1): edge (1,2) is
  redundant, CaDiCaL UNSAT with drat-trim VERIFIED. A genuine, if minor, new
  result — an edge-count improvement, explicitly *not* a vertex-count record.
- **Our drat-trim verifies a third party's proofs.** Five of Heule's published
  DRAT proofs (517, 553, 610, 633, 803) VERIFIED with matched CNFs, and NOT
  VERIFIED on every deliberately mismatched pairing. That negative control is
  what makes the positive verdicts meaningful.
- **Two metadata defects found and fixed** (proof hash describing a different
  file than `proof_path` named; proof byte count retained on a SAT result).
  Neither could produce an unsound mathematical claim, but both would have made a
  claim unauditable by a referee re-hashing the artifact.

## Soundness alarms
None. No adversary found a non-unit edge; no proof failed its checker.
