"""Are the 8 substitution graphs actually NEW, or isomorphic to the original 510?

A substitution (510 - v) + w is a different VERTEX SET by construction, but that
does not make it a different GRAPH. If it is isomorphic to the original 510 then
it is the same combinatorial object in a different embedding, and calling it new
would be overclaiming. Checked with exact VF2, not an invariant.
"""
import json, sys
from fractions import Fraction
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph, isomorphic
from hn.mathematica import load_vtx
from hn.point import Point

d = json.load(open("data/pools/P3_nc510_deg2.json"))
F = MultiQuadField(tuple(d["field"]))
pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
             F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
pool = UDGraph(pts, lineage={"op":"pool"})
key2i = {p.key(): i for i,p in enumerate(pool.points)}
spts,_ = load_vtx("data/CNP-SAT/vtx/510.vtx", field=F)
B = sorted(key2i[p.key()] for p in spts)
orig = UDGraph([pool.points[i] for i in B], lineage={"op":"heule510"})
print(f"original 510: n={orig.n} m={orig.m} graph_hash={orig.graph_hash()[:16]}")
hits = json.load(open("catalog/substitute_result.json"))["hits"]
out = []
for i,h in enumerate(hits):
    S = sorted((set(B) - {h['v']}) | {h['w']})
    g = UDGraph([pool.points[j] for j in S],
                lineage={"op":"substitute","w":h['w'],"v":h['v'],"parent":"heule510"})
    same_hash = g.graph_hash() == orig.graph_hash()
    iso = isomorphic(g, orig) if same_hash or g.m == orig.m else False
    print(f"hit{i} w={h['w']:5d} v={h['v']:4d}: n={g.n} m={g.m} "
          f"deg_seq_same={g.degree_sequence()==orig.degree_sequence()} "
          f"wl_same={same_hash} ISOMORPHIC={iso}", flush=True)
    out.append({"hit":i,"w":h['w'],"v":h['v'],"n":g.n,"m":g.m,
                "isomorphic_to_orig":bool(iso),
                "coord_hash":g.coord_hash(),"graph_hash":g.graph_hash()})
json.dump(out, open("catalog/hits_iso.json","w"), indent=1)
print()
print("NEW (non-isomorphic) graphs:", sum(1 for o in out if not o["isomorphic_to_orig"]), "of", len(out))
