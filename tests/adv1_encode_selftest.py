#!/usr/bin/env python3
"""ADVERSARY 1 / CHECK 1 negative controls for tests/adv1_encode.py.

The 510-graph k=4 UNSAT is only meaningful if this encoder is capable of
(a) reporting SAT when a colouring exists and (b) reporting UNSAT only when one
genuinely does not.  Controls:

  C1 K_m for m=3..6 at every k: encoder must give SAT iff k >= m.
  C2 Moser spindle (chi = 4): k=3 UNSAT, k=4 SAT.
  C3 Golomb graph (chi = 4): k=3 UNSAT, k=4 SAT.
  C4 bipartite / odd cycle sanity: C5 needs 3, C6 needs 2.
  C5 edge-criticality probe on the 510 graph: delete a single edge and re-solve
     at k=4.  If the encoder were structurally biased toward UNSAT this would
     stay UNSAT; a genuine encoder should flip to SAT for a critical edge.
  C6 clause-count and variable-collision audit of the colour-major numbering.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import adv1_encode as E  # noqa: E402

SCRATCH = os.environ.get("ADV1_SCRATCH", "/tmp")
fails = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        fails.append(name)


def solve(n, edges, k, tag, want_model=False):
    nvars, clauses = E.encode(n, edges, k)
    path = os.path.join(SCRATCH, f"adv1_ctl_{tag}_k{k}.cnf")
    E.write_dimacs(path, nvars, clauses)
    cmd = [E.CADICAL, "-q", path] if want_model else [E.CADICAL, "-q", "-n", path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=100000)
    v = None
    for line in r.stdout.splitlines():
        if line.startswith("s "):
            v = line[2:].strip()
    return v, r.stdout, n, edges


print("C6 numbering audit")
n_probe, k_probe = 510, 4
seen = {}
coll = 0
for v in range(n_probe):
    for c in range(k_probe):
        x = E.var(v, c, n_probe)
        if x in seen:
            coll += 1
        seen[x] = (v, c)
check("colour-major var(v,c)=c*n+v+1 is injective over 510x4", coll == 0)
check("variable range is exactly 1..n*k", min(seen) == 1 and max(seen) == n_probe * k_probe)
check("differs from vertex-major: var(1,0)=2 here, vertex-major gives 5",
      E.var(1, 0, n_probe) == 2)

print("\nC1 complete graphs K_m: SAT iff k >= m")
for m in range(3, 7):
    ed = [(a + 1, b + 1) for a, b in itertools.combinations(range(m), 2)]
    for k in range(2, 7):
        v, _, _, _ = solve(m, ed, k, f"K{m}")
        want = "SATISFIABLE" if k >= m else "UNSATISFIABLE"
        if v != want:
            fails.append(f"K{m} k={k}")
    print(f"  K{m}: ok")
check("K3..K6 across k=2..6 all as predicted",
      not any(f.startswith("K") for f in fails))

print("\nC2 Moser spindle (chi = 4)")
moser = [(1, 2), (1, 3), (2, 3), (2, 4), (3, 4),
         (1, 5), (1, 6), (5, 6), (5, 7), (6, 7), (4, 7)]
v3, _, _, _ = solve(7, moser, 3, "moser")
v4, out4, _, _ = solve(7, moser, 4, "moser", want_model=True)
check("Moser spindle k=3 UNSAT", v3 == "UNSATISFIABLE", f"got {v3}")
check("Moser spindle k=4 SAT", v4 == "SATISFIABLE", f"got {v4}")
if v4 == "SATISFIABLE":
    ok, msgs, _ = E.check_model(E.parse_model(out4), 7, 4, moser)
    check("Moser spindle 4-colouring passes my own model checker", ok, str(msgs))

print("\nC3 Golomb graph (chi = 4)")
# hub 1; inner triangle 2,3,4; outer triangle 5,6,7; spokes 8,9,10 -> 10 vertices
golomb = [(1, 2), (1, 3), (1, 4), (2, 3), (3, 4), (2, 4),
          (5, 6), (6, 7), (5, 7),
          (5, 8), (6, 9), (7, 10),
          (8, 9), (9, 10), (8, 10),
          (2, 8), (3, 9), (4, 10)]
g3, _, _, _ = solve(10, golomb, 3, "golomb")
g4, _, _, _ = solve(10, golomb, 4, "golomb")
check("Golomb-like graph k=3 UNSAT", g3 == "UNSATISFIABLE", f"got {g3}")
check("Golomb-like graph k=4 SAT", g4 == "SATISFIABLE", f"got {g4}")

print("\nC4 cycles")
c5 = [(i + 1, (i + 1) % 5 + 1) for i in range(5)]
c6 = [(i + 1, (i + 1) % 6 + 1) for i in range(6)]
a, _, _, _ = solve(5, c5, 2, "c5")
b, _, _, _ = solve(5, c5, 3, "c5")
c, _, _, _ = solve(6, c6, 2, "c6")
check("C5 k=2 UNSAT", a == "UNSATISFIABLE", f"got {a}")
check("C5 k=3 SAT", b == "SATISFIABLE", f"got {b}")
check("C6 k=2 SAT", c == "SATISFIABLE", f"got {c}")

print("\nC5 edge-criticality probe on the 510 graph at k=4")
n510, edges510 = E.unit_pairs_from_geometry(E.VTX)
check("geometry gives 510 / 2504", n510 == 510 and len(edges510) == 2504,
      f"got {n510}/{len(edges510)}")
probe = [edges510[0], edges510[len(edges510) // 2], edges510[-1]]
flipped = 0
redundant = []
for e in probe:
    red = [x for x in edges510 if x != e]
    v, _, _, _ = solve(510, red, 4, f"del{e[0]}_{e[1]}")
    print(f"  delete edge {e}: m={len(red)} -> k=4 {v}")
    if v == "SATISFIABLE":
        flipped += 1
    elif v == "UNSATISFIABLE":
        redundant.append(e)
# The control we actually need: the encoder MUST be able to flip to SAT on a
# minimally weakened 510-graph.  If every deletion stayed UNSAT the encoder
# would be structurally UNSAT-biased and the headline result meaningless.
check("at least one single-edge deletion flips 510 to 4-COLOURABLE "
      "(encoder is NOT structurally UNSAT-biased)",
      flipped >= 1, f"{flipped}/{len(probe)} flipped")
# FINDING, not a failure: the 510 graph turns out NOT to be edge-critical.
if redundant:
    print(f"  FINDING: these edges are REDUNDANT -- the graph stays 5-chromatic "
          f"without them, so 510.edge is not edge-minimal: {redundant}")
check("recorded edge-criticality status of the probed edges", True,
      f"critical={len(probe)-len(redundant)} redundant={len(redundant)}")

print()
if fails:
    print(f"CHECK-1 SELFTEST FAILURES: {sorted(set(fails))}")
    sys.exit(1)
print("CHECK-1 SELFTEST: encoder proven able to report SAT and UNSAT correctly")
sys.exit(0)
