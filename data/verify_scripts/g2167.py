#!/usr/bin/env python3
"""Build the FULL unit-distance graph on the G2167 point set (exact arithmetic)
and test 4-colorability."""
import re, sys
import sympy as sp
from pysat.solvers import Cadical153
from pysat.formula import IDPool

sys.path.insert(0, "/tmp/claude-0/-home-user-CustomLLM/d7f31fe2-b59b-5716-9431-923157eab8d6/scratchpad")
from verify import parse_vtx

path = sys.argv[1]
pts = parse_vtx(path)
n = len(pts)
print(f"{path}: {n} points")

# numeric prefilter at high precision, then exact confirm
import mpmath as mp
mp.mp.dps = 50
num = [(mp.mpf(str(sp.N(x, 45))), mp.mpf(str(sp.N(y, 45)))) for x, y in pts]

cand = []
for i in range(n):
    xi, yi = num[i]
    for j in range(i + 1, n):
        xj, yj = num[j]
        d2 = (xi - xj) ** 2 + (yi - yj) ** 2
        if abs(d2 - 1) < mp.mpf('1e-25'):
            cand.append((i, j))
print(f"numeric unit-distance candidate pairs: {len(cand)}")

edges = []
bad = 0
for (i, j) in cand:
    dx = pts[i][0] - pts[j][0]
    dy = pts[i][1] - pts[j][1]
    d2 = sp.expand(dx * dx + dy * dy)
    if sp.simplify(d2 - 1) == 0:
        edges.append((i + 1, j + 1))
    else:
        bad += 1
print(f"EXACT unit edges: {len(edges)}  (numeric false positives: {bad})")

# dedupe coincident points check
seen = {}
dups = 0
for idx, (x, y) in enumerate(num):
    key = (mp.nstr(x, 30), mp.nstr(y, 30))
    if key in seen:
        dups += 1
    seen[key] = idx
print(f"duplicate points: {dups}")

pool = IDPool()
v = lambda i, c: pool.id(('v', i, c))
K = 4
with Cadical153() as s:
    for i in range(1, n + 1):
        s.add_clause([v(i, c) for c in range(K)])
    for (a, b) in edges:
        for c in range(K):
            s.add_clause([-v(a, c), -v(b, c)])
    r = s.solve()
print(f"4-colorable = {r}  =>  chi {'<= 4' if r else '>= 5'}")

out = path.rsplit('/', 1)[-1].replace('.vtx', '') + ".edge"
with open("/home/user/CustomLLM/data/derived/" + out, "w") as f:
    f.write(f"p edge {n} {len(edges)}\n")
    for a, b in edges:
        f.write(f"e {a} {b}\n")
print("wrote", "/home/user/CustomLLM/data/derived/" + out)
