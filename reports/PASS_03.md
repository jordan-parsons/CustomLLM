# Pass 3 report — first full round on the hardened stack

## Configuration
Two-tier basin hop, gate removed, over the four highest-ranked ambient pools.
Pool edges detected once by the CERTIFIED (float-free) detector; candidate subsets
obtained by restriction, which is an identity rather than a measurement.

| worker | pool | full passes | cores beating 510 | solver calls | wall |
|---|---|---|---|---|---|
| 400000 | P3_nc510_deg3 (1712 pts) | 11 | 0 | 11582 | 1585 s |
| 400001 | P3_ncD6_deg3 (2953 pts) | 11 | 0 | 11575 | 1602 s |
| 400002 | P5a_super_510 (4279 pts) | 11 | 0 | 11523 | 1550 s |
| 400003 | P1d_510_rot_L2 (5224 pts) | 11 | 0 | 11513 | 1547 s |
| **total** | | **44** | **0** | **46,193** | ~26 min |

## Result
**No improvement. Best verified remains 510.** Zero perturbations produced a
5-chromatic subgraph below the incumbent, on any of the four pools.

## Distribution of local minima (58 full passes, cumulative)
```
510  ################################ (32)
511  ########                          (8)
512  ######                            (6)
513  ########                          (8)
514  #                                 (1)
515  #                                 (1)
516  #                                 (1)
517  #                                 (1)
```
**510 is the floor, not the median.** 55% of passes land exactly on it and the rest
land strictly above. Not one pass out of 58 finished below 510. A search whose best
local minimum is also its modal one, with a one-sided tail, is a search sitting at
the bottom of its basin — not one that is merely unlucky.

## What this rules out, and what it does not
**Rules out:** that a sub-510 graph is reachable from the 510 vertex set by adding
neighbour-completion or rotation-closure points and re-minimising, at the
perturbation sizes sampled (3–45 added points). Four structurally different pools,
including the provably complete degree-3 neighbour completion, all behave alike.

**Does not rule out:** that such a graph exists in these pools. 58 samples of a
combinatorial space this size is a thin slice, and the perturbation sizes explored
are small. The result is evidence about the *search*, not a theorem about the pools.

## The core-filter negative result
Cumulative: **0 cores beat 510 in 44 triages.** CaDiCaL's assumption core returns
nearly all assumptions it is given (518 from 510+8, 537 from 510+38), so it never
signalled a promising candidate. The 1-in-12 gate built on that signal was
discarding 11 of every 12 informative samples for nothing, and was removed. Retained
only as a cheap colourability reject.

Honest note on a metric I got wrong earlier: I described the gated search as ~1000
perturbations/hour. Triages are not the informative unit — full deletion passes are,
and gated the rate was ~16/hour. Ungated it is ~100/hour (44 passes per 26 min).

## Strategies killed
- **UNSAT-core triage as a promise signal.** Measured useless here. Killed as a
  filter, kept as a free reject.
- **Nothing else killed this pass.** The four pools all performed identically, which
  is itself informative: pool *choice* is not the variable, so reallocating between
  them is not the lever. The lever is either much larger perturbations, a symmetric
  (orbit) move that criticality does not already forbid, or a genuinely different
  ambient field.

## Reallocation for the next passes
Rounds 1–11 continue on the same four pools with fresh seeds, since the sample is
still thin. If the distribution is unchanged after several hundred passes, the
honest conclusion is a plateau and the remaining untried lever is the C3-orbit move
(the 510 is nearly C3-symmetric: R120 maps 482 of 510 vertices back, and
510 = 3 x 170).
