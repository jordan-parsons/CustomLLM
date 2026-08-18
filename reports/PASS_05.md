# Pass 5 report — large perturbations, and the Voronov field

## Lever 3 from the final report: "much larger perturbations". REFUTED.

Every earlier pass sampled perturbations of 3–45 added points. The stated
hypothesis was that the basin might simply be wider than that. It is not — larger
perturbations are **monotonically worse**, and decisively so.

98 full deletion passes with 62–299 added points, over three pools:

| perturbation regime | passes | best result | fraction landing on 510 |
|---|---|---|---|
| small (3–45 added) | 187 | **510** | 98/187 = 52% |
| large (62–299 added) | 98 | **514** | **0/98 = 0%** |

Large-perturbation result distribution: minimum 514, spread continuously up to
619, median ≈ 551. **Not one pass in 98 recovered even to 510.**

### Why this happens, and why it matters
Greedy deletion cannot undo a large perturbation. Adding ~200 points and then
deleting greedily strands the search at a worse local minimum: the MUS descent is
not powerful enough to walk back out. So the perturbation size is not an
under-explored dimension with a payoff hiding at the far end — it is a
**monotone-degradation** dimension, and 3–45 was already the good regime.

This closes lever 3 from the final report as barren, with the measurement.

## Voronov `Q(√2,√3)` construction — a genuinely different field
Motivation: after the plateau, a different algebraic field is a genuinely
different basin, which is what the diagnosis called for. The Voronov et al.
building blocks parse exactly in ℚ(√2,√3):

| graph | points | edges | k=4 |
|---|---|---|---|
| s2_M1 | 73 | 144 | **SAT** (4-colourable) |
| s2_M2 | 865 | 3000 | **SAT** (4-colourable) |
| s2_M3 | 32257 | — | **not determined — job died** |

s2_M1 and s2_M2 are 4-colourable building blocks, like L403/S199/T721 in the
other family. s2_M3 (32257 points) OOM-killed during certified detection: a dense
point set makes the ±2-cell candidate-pair list explode, and it took the
concurrently running search parent down with it.

**Honest status: s2_M3 is UNDETERMINED, not negative.** It is a real robustness
bug in the detector (unbounded candidate-pair materialisation), not a mathematical
result. Recorded as an open item rather than a finding.

Prior expectation, for calibration: Voronov et al.'s published planar graphs are
3877 and 64513 vertices, both far above 509, and their own paper does not improve
the record. So even a successful s2_M3 run has low expected value for Objective A.

## Gap being closed this pass
510, 517, 529 and 553 were confirmed deletion fixpoints. **610, 633, 803, 826 and
874 were never tested** — they were assumed minimised because Heule published
them. But 826 and 874 ship with **no DRAT proof upstream**, which hints at less
attention. A graph that is not already a fixpoint could reduce somewhere other
than 510. Running now.

## Running total of barren strategies
1. Single-vertex deletion from any published graph — provably stuck (criticality)
2. UNSAT-core reduction on minimised graphs — core is the whole vertex set
3. MUS descent over the 2306-point pool encoding — ~50× per-call penalty
4. Uniform-order basin hopping — cannot escape a critical incumbent
5. UNSAT-core triage as a promise signal — 0 of 44 cores ever beat the incumbent
6. Minkowski sums of 4-colourable blocks with H/J — still 4-colourable at 5167 pts
7. C3-orbit minimisation — floor 517, both modes converging
8. Orbit search on the 985-orbit pool — cost grows, signal does not
9. **Large perturbations (62–299 points) — monotonically worse, 0/98 reached 510**

## Fixpoint gap closed: the ENTIRE published corpus is a deletion fixpoint

| graph | seeds | reduction | solver calls each |
|---|---|---|---|
| 610 | 3 | **0** | 612 |
| 633 | 3 | **0** | 635 |
| 803 | 3 | **0** | 805 |
| 826 | 3 | **0** | 828 |
| 874 | 3 | **0** | 876 |

Combined with the earlier results for 510, 517, 529 and 553: **all nine published
5-chromatic graphs are deletion fixpoints**, over 15 independent runs with three
random deletion orders each and not one vertex removed anywhere.

This matters because 826 and 874 ship with **no DRAT proof upstream**, which was
the reason to suspect they had received less attention and might still be
reducible. They are not. The assumption that Heule's corpus is fully minimised is
now measured rather than inherited.

Consequence: **every route that ends in "delete vertices from published material"
is closed.** Any further progress must introduce points that are not in the
published sets. That is precisely what the exhaustive substitution search tests.
