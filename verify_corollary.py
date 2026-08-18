"""Verify the corollary: no single added point can beat 510 over this pool.

CLAIM. Let P be the degree>=2 neighbour-completion pool, G the 510, and w any
point of P outside G. Then for every D with |D| >= 2, the graph (G + w) - D is
4-colourable. Hence no single-point augmentation reaches 509 or 508.

PROOF.
  Suppose (G + w) - D is NOT 4-colourable, with |D| >= 2.
  Case A, w in D: then (G+w)-D is a subgraph of G minus at least one vertex,
    which is 4-colourable by vertex-criticality of G. Contradiction.
  Case B, w not in D: so D is a subset of V(G). Pick v1 in D. Then (G+w)-D is a
    subgraph of (G - v1) + w, and a supergraph of a non-4-colourable graph is
    non-4-colourable, so (G - v1) + w is non-4-colourable - i.e. (w,v1) is one of
    the exhaustively enumerated hits. Now pick v2 in D, v2 != v1. Then (G+w)-D is
    a subgraph of H - v2 where H = (G - v1) + w, so H - v2 is non-4-colourable.
    But every hit graph H is vertex-critical. Contradiction. QED

The proof leans on exactly two computational facts, and this script re-checks the
second one exhaustively rather than trusting the earlier MUS runs:
  (F1) the 8 hits are ALL the hits          - exhaustive search + degree prune lemma
  (F2) every hit graph is vertex-critical   - re-verified here, all 510 deletions
"""
import json, sys
from fractions import Fraction
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer, restrict
from hn.point import Point

d = json.load(open("data/pools/P3_nc510_deg2.json"))
F = MultiQuadField(tuple(d["field"]))
pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
             F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
pool = UDGraph(pts, lineage={"op":"pool"})
adj = pool.adj
key2i = {p.key(): i for i,p in enumerate(pool.points)}
spts,_ = load_vtx("data/CNP-SAT/vtx/510.vtx", field=F)
B = sorted(key2i[p.key()] for p in spts); bs=set(B)
hits = json.load(open("catalog/substitute_result.json"))["hits"]
print(f"pool n={pool.n} m={pool.m}; 510 present; {len(hits)} exhaustive hits\n")

allok = True
for i,h in enumerate(hits):
    S = sorted((bs - {h['v']}) | {h['w']})
    sub = restrict(adj, S); pos = {v:j for j,v in enumerate(sub.index)}
    R = MUSReducer(sub, 4)
    try:
        assert R.is_unsat(list(range(sub.n))), "hit graph is not UNSAT!"
        removable = []
        for v in S:
            if R.is_unsat([pos[u] for u in S if u != v]):
                removable.append(v)
    finally:
        R.close()
    ok = (len(removable) == 0)
    allok &= ok
    print(f"hit{i} w={h['w']:5d} v={h['v']:4d}: all {len(S)} single deletions tested, "
          f"removable={len(removable)} -> {'VERTEX-CRITICAL' if ok else 'REDUCIBLE!'}",
          flush=True)

print()
print("F2 (all 8 hit graphs vertex-critical):", "CONFIRMED" if allok else "REFUTED")
print()
print("COROLLARY:", "PROVED over this pool" if allok else "NOT proved")
print("  No single added point from the deg>=2 completion pool, combined with any")
print("  2 or more deletions, yields a 5-chromatic graph. So 509 and 508 are both")
print("  unreachable by an add-1 move over this pool.")
json.dump({"F2_all_critical": bool(allok), "hits": len(hits)},
          open("catalog/corollary.json","w"), indent=1)
