# Pass 7 — a proof, not a sample

## The ladder to a record

A record needs <= 508 vertices, i.e. a net loss of 2 from 510. Enumerating the
moves by how many points they add:

| move | status | basis |
|---|---|---|
| add 0, delete 2 | **IMPOSSIBLE** | vertex-criticality of the 510 (a subset of a 509-subset) |
| add 1, delete 3 | **IMPOSSIBLE** | the corollary below |
| add 2, delete 4 | OPEN | being searched |

## The corollary (proved over this pool)

> **No single added point from the degree>=2 neighbour-completion pool, combined
> with any 2 or more deletions, yields a 5-chromatic graph.** So 509 *and* 508 are
> both unreachable by an add-1 move over this pool.

**Proof.** Let G be the 510, w a pool point outside it, and suppose (G + w) − D is
not 4-colourable with |D| >= 2.

*Case A, w in D.* Then (G+w)−D is a subgraph of G minus at least one vertex, which
is 4-colourable by vertex-criticality of G. Contradiction.

*Case B, w not in D.* So D is a subset of V(G). Pick v1 in D. Then (G+w)−D is a
subgraph of (G−v1)+w, and a supergraph of a non-4-colourable graph is
non-4-colourable, so (G−v1)+w is non-4-colourable — i.e. (w,v1) is one of the
exhaustively enumerated hits. Now pick a second v2 in D. Then (G+w)−D is a subgraph
of H − v2, where H = (G−v1)+w, so H − v2 is non-4-colourable. But every hit graph H
is vertex-critical. Contradiction. **QED**

### The two computational facts it rests on
- **(F1) the 8 hits are ALL the hits.** From the exhaustive substitution search:
  337,142 of 338,130 pairs ruled out by solving, and the remaining candidates —
  2637 of degree 2 and 539 of degree 3 — discarded by the degree>=4 prune lemma,
  which is itself a proof (adding w to a 4-colourable H is non-4-colourable iff
  every proper 4-colouring of H puts all four colours on N(w)∩H, requiring
  |N(w)∩H| >= 4).
- **(F2) every hit graph is vertex-critical.** Re-verified in `verify_corollary.py`
  independently of the earlier MUS runs: for each of the 8 graphs, **all 510 single
  deletions tested, 0 removable.** Output in `catalog/corollary.log`.

### Scope, stated plainly
This is a theorem about the pool, not about the plane. "Over this pool" means the
complete degree>=2 neighbour completion of the 510 (4349 points, of which 3839 lie
outside the 510). A point of the plane outside that pool is not covered. The result
is nonetheless categorically stronger than the sampled negatives that preceded it:
those said "we did not find one", this says "there is none, here".

## Why add-2 must be sampled rather than enumerated
Exhaustive add-2 needs C(663,2) x 510 ~ **112 million** queries, against the 338,130
that add-1 required — three orders of magnitude beyond budget. So `run_add2.py`
randomises over pairs but stays targeted at the frontier: pairs are drawn only from
the 663 candidates surviving the proved degree>=4 prune, weighted by degree into the
incumbent, with incumbent vertices tried for deletion first. It runs from all **nine**
distinct critical 510-vertex graphs (the original plus the 8 new ones), since those
have structurally different add-2 neighbourhoods.

Honest framing: unlike pass 6, a negative result here will be statistical, not a
proof. It will not close the rung, only fail to open it.
