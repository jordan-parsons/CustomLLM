"""How many degree>=4 substitution candidates exist beyond the completion pool?

The proved prune says only points with deg_510(w) >= 4 can ever make
(510 - v) + w non-4-colourable. The exhaustive substitution search drew its 663
candidates from P3_nc510_deg2, which is by construction built from points near the
510. If the larger pools contain deg>=4 points OUTSIDE that set, the exhaustive
search can be re-run against a genuinely larger candidate set and the corollary's
scope widens with it. If they contain none, the pool is saturated and the
corollary already covers everything reachable by these constructions.

Reports, per pool: total points, points outside the 510, how many have
deg_510 >= 4, and critically how many of those are NEW relative to the 663.
"""
import json, os, sys, glob
from fractions import Fraction
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.point import Point

F510 = MultiQuadField((3, 5, 11))
spts, _ = load_vtx("data/CNP-SAT/vtx/510.vtx", field=F510)
KEY510 = {p.key() for p in spts}

# the 663 already covered by the exhaustive search
d = json.load(open("data/pools/P3_nc510_deg2.json"))
Fb = MultiQuadField(tuple(d["field"]))
bpts = [Point(Fb.elem([Fraction(a,b) for a,b in p["x"]]),
              Fb.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
bpool = UDGraph(bpts, lineage={"op":"pool"})
bidx = {p.key(): i for i, p in enumerate(bpool.points)}
b510 = {bidx[k] for k in KEY510 if k in bidx}
COVERED = set()
for v in range(bpool.n):
    if v in b510: continue
    if sum(1 for u in bpool.adj[v] if u in b510) >= 4:
        COVERED.add(bpool.points[v].key())
print(f"baseline P3_nc510_deg2: {len(COVERED)} candidates already exhaustively tested\n")

rows = []
targets = sys.argv[1:] or [
    "P1e_union_rot_L1", "P2g_union_plus_H", "P1f_union_D6", "P2b_510_plus_J",
    "P5b_super_510_wide", "P1d_510_rot_L2", "P1h_510_multi_centre",
    "P1g_510_beta_at4centres", "P5a_super_510", "P3_ncD6_deg4", "P3_nc510_deg4",
]
for name in targets:
    path = f"data/pools/{name}.json"
    if not os.path.exists(path):
        print(f"{name}: MISSING"); continue
    d = json.load(open(path))
    F = MultiQuadField(tuple(d["field"]))
    pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
                 F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
    g = UDGraph(pts, lineage={"op":"pool"})
    idx = {p.key(): i for i, p in enumerate(g.points)}
    have = {idx[k] for k in KEY510 if k in idx}
    if len(have) != 510:
        print(f"{name}: only {len(have)}/510 of the 510 present - SKIP")
        continue
    deg4 = []
    for v in range(g.n):
        if v in have: continue
        if sum(1 for u in g.adj[v] if u in have) >= 4:
            deg4.append(g.points[v].key())
    new = [k for k in deg4 if k not in COVERED]
    rows.append((name, g.n, g.n - 510, len(deg4), len(new)))
    print(f"{name:28s} n={g.n:6d} outside={g.n-510:6d} deg>=4={len(deg4):5d} "
          f"NEW={len(new):5d}", flush=True)

print()
allnew = set()
for name, *_ in rows: pass
print("summary (sorted by NEW candidates):")
for r in sorted(rows, key=lambda x: -x[4]):
    print(f"  {r[0]:28s} deg>=4={r[3]:5d}  new-vs-baseline={r[4]:5d}")
json.dump([{"pool":r[0],"n":r[1],"outside":r[2],"deg4":r[3],"new":r[4]} for r in rows],
          open("catalog/deg4_counts.json","w"), indent=1)
