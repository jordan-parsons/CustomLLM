#!/usr/bin/env python3
"""ADVERSARY 3 - provenance/record audit of a DERIVED artifact.

data/auxiliary_4colorable/G2167.edge and data/derived/G2167.edge have NO upstream
counterpart: marijnheule/CNP-SAT ships vtx/G2167.vtx but no edge/G2167.edge.
So that edge list was produced by us and is unaudited. Re-derive it from the
exact coordinates with O(n^2) exact arithmetic and compare.
"""
import sys

sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.mathematica import load_vtx, load_edge_file  # noqa: E402
from hn.detect import detect_edges_bruteforce_exact, detect_edges  # noqa: E402
from hn.field import MultiQuadField  # noqa: E402

VTX = "/home/user/CustomLLM/data/CNP-SAT/vtx/G2167.vtx"
pts, f = load_vtx(VTX, MultiQuadField((3, 5, 11)))
print(f"G2167.vtx: {len(pts)} lines, {len({p.key() for p in pts})} distinct exact points, field {f}")

E = set(detect_edges_bruteforce_exact(pts))
Eg = set(detect_edges(pts))
print(f"exact brute force edges = {len(E)};  grid detector = {len(Eg)};  agree = {E == Eg}")
if E != Eg:
    print("  ALARM grid missed:", sorted(E - Eg)[:10], " grid spurious:", sorted(Eg - E)[:10])

for path in [
    "/home/user/CustomLLM/data/auxiliary_4colorable/G2167.edge",
    "/home/user/CustomLLM/data/derived/G2167.edge",
]:
    n, Ef = load_edge_file(path)
    Ef = set(Ef)
    print(f"{path}: header n={n}, m={len(Ef)}, matches_exact={Ef == E}")
    bad = sorted(Ef - E)
    miss = sorted(E - Ef)
    if bad:
        print(f"  SOUNDNESS ALARM: {len(bad)} claimed edges are NOT exactly unit distance:")
        for u, v in bad[:10]:
            print(f"    ({u+1},{v+1}) d^2 = {pts[u].sqdist(pts[v])!r}")
    if miss:
        print(f"  {len(miss)} exactly-unit pairs are MISSING from the file, e.g. "
              f"{[(u+1, v+1) for u, v in miss[:10]]}")
