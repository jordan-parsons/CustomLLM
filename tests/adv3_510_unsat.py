#!/usr/bin/env python3
"""ADVERSARY 3 - CHECK C support: the repo ships NO CNF and NO DRAT proof for 510.

Heule's CNP-SAT repo contains vtx/510.vtx and edge/510.edge but, unlike
517/529/553/610/633/803, no cnf/510-4*.cnf, no proof/510-4*.drat and no
check/510.singular. So the "510-vertex 5-chromatic graph" is UNCERTIFIED inside
the artifact set we inherited. This script closes that specific hole with a
machine-checked certificate: encode from OUR exactly-derived edge set, solve,
and verify the refutation with drat-trim.

(Adversary 1 attacks the same claim with an independent encoder; this run exists
to record that the third party's own repo has no proof for it, and to produce
one, not to duplicate that encoder.)
"""
import subprocess
import sys
import time

sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.mathematica import load_vtx  # noqa: E402
from hn.detect import detect_edges_bruteforce_exact  # noqa: E402
from hn.field import MultiQuadField  # noqa: E402
from hn.cnf import encode_coloring  # noqa: E402

OUT = "/home/user/CustomLLM/artifacts/adv3"
pts, _ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", MultiQuadField((3, 5, 11)))
edges = sorted(set(detect_edges_bruteforce_exact(pts)))
print(f"510: {len(pts)} exact points, {len(edges)} exactly-unit edges")

for k, tag in ((4, "k4"), (5, "k5")):
    enc = encode_coloring(len(pts), edges, k, adj=None, break_symmetry=False)
    cnf = f"{OUT}/adv3_510_{tag}.cnf"
    enc.write(cnf)
    drat = f"{OUT}/adv3_510_{tag}.drat"
    t = time.time()
    r = subprocess.run(
        ["nice", "-n", "19", "/home/user/CustomLLM/vendor/kissat/build/kissat", cnf, drat],
        capture_output=True, text=True,
    )
    wall = time.time() - t
    st = "UNSAT" if r.returncode == 20 else ("SAT" if r.returncode == 10 else f"rc={r.returncode}")
    print(f"  k={k}: kissat -> {st} in {wall:.2f}s")
    if r.returncode == 20:
        t = time.time()
        v = subprocess.run(
            ["nice", "-n", "19", "/home/user/CustomLLM/vendor/drat-trim/drat-trim", cnf, drat, "-t", "3600"],
            capture_output=True, text=True,
        )
        vw = time.time() - t
        verdict = [l for l in v.stdout.splitlines() if l.startswith("s ")]
        print(f"  k={k}: drat-trim -> {verdict} in {vw:.2f}s")
