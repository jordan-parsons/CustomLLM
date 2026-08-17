#!/usr/bin/env python3
"""ADVERSARY 3 - CHECK C support: structural provenance of Heule's 510.vtx.

Question: where does the 510-vertex graph in marijnheule/CNP-SAT come from?
Structural evidence available offline:
  * is its exact coordinate set a SUBSET of 517 / 529 / 553 / G2167 / L403 / T721?
  * does its .edge file agree with our exact-arithmetic unit-distance edges?
  * is it isomorphic to an induced subgraph relationship with 517?
  * how many exact coordinates does it share with each other file?
All comparisons are on EXACT field elements (canonical keys), never floats.
"""
import json
import sys

sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.mathematica import load_vtx, load_edge_file  # noqa: E402
from hn.detect import detect_edges_bruteforce_exact  # noqa: E402
from hn.field import MultiQuadField  # noqa: E402

ROOT = "/home/user/CustomLLM/data/CNP-SAT"
FIELD = MultiQuadField((3, 5, 11))
OTHERS = ["517", "529", "553", "610", "633", "803", "826", "874", "G2167", "L403", "T721", "S199"]

out = {}
pts510, _ = load_vtx(f"{ROOT}/vtx/510.vtx", FIELD)
k510 = [p.key() for p in pts510]
s510 = set(k510)
out["n_510"] = len(pts510)
out["distinct_510"] = len(s510)
print(f"510.vtx: {len(pts510)} lines, {len(s510)} distinct exact points")

E = set(detect_edges_bruteforce_exact(pts510))
n_e, E_file = load_edge_file(f"{ROOT}/edge/510.edge")
E_file = set(E_file)
out["our_exact_edges_510"] = len(E)
out["their_edge_file_510"] = len(E_file)
out["edges_agree"] = E == E_file
print(f"510: our exact edges = {len(E)}, their edge file = {len(E_file)}, agree = {E == E_file}")
if E != E_file:
    bad = sorted(E_file - E)
    out["their_edges_not_unit"] = [
        {"u1": u + 1, "v1": v + 1, "sqdist": repr(pts510[u].sqdist(pts510[v]))}
        for u, v in bad[:20]
    ]
    out["our_edges_missing_from_theirs"] = [[u + 1, v + 1] for u, v in sorted(E - E_file)[:20]]

# degree-1 / isolated vertices would be a red flag for a "minimal" graph
deg = [0] * len(pts510)
for u, v in E:
    deg[u] += 1
    deg[v] += 1
out["min_degree_510"] = min(deg)
out["n_deg_lt_4_510"] = sum(1 for d in deg if d < 4)
print(f"510: min degree {min(deg)}, vertices with degree < 4: {out['n_deg_lt_4_510']}")

out["overlap"] = {}
for nm in OTHERS:
    try:
        pts, _ = load_vtx(f"{ROOT}/vtx/{nm}.vtx", FIELD)
    except Exception as e:
        out["overlap"][nm] = {"error": str(e)}
        print(f"  {nm}: parse error {e}")
        continue
    ks = {p.key() for p in pts}
    inter = len(s510 & ks)
    rec = {
        "n": len(pts),
        "shared_exact_points": inter,
        "510_is_subset": s510 <= ks,
    }
    out["overlap"][nm] = rec
    print(f"  vs {nm:6s} n={len(pts):5d} shared={inter:5d} 510_subset_of_it={s510 <= ks}")

with open("/home/user/CustomLLM/artifacts/adv3/prov510.json", "w") as fh:
    json.dump(out, fh, indent=2)
print("wrote artifacts/adv3/prov510.json")
