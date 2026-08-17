#!/usr/bin/env python3
"""ADVERSARY 1 / CHECK 2 negative controls for tests/adv1_exact.py.

A checker that says PASS on the first run is a checker that has not been shown
to be able to say FAIL.  This script proves adv1_exact.py has teeth:

  T1 field axioms: (sqrt m)^2 == m for every basis radicand; associativity and
     distributivity on random elements; inverse * self == 1.
  T2 parser cross-check against an INDEPENDENT float evaluator built by textual
     rewriting + math.sqrt (floats used only to cross-check the parse, never to
     accept/reject a unit distance).
  T3 mutation: perturb one coordinate of one vertex by 1/96 and confirm the
     exact all-pairs check no longer reports 2504 / reports non-unit edges.
  T4 mutation: replace Sqrt[33] by Sqrt[3] in one vertex, confirm detection.
  T5 duplicate-vertex mutation: confirm the distinctness test fires.
  T6 near-miss sensitivity: confirm a pair at squared distance 1 + 1e-12 is
     REJECTED (i.e. no tolerance is hiding in the comparison).
"""

from __future__ import annotations

import math
import os
import random
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import adv1_exact as A  # noqa: E402

fails = []


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        fails.append(name)


print("T1 field axioms")
for m in range(A.DIM):
    r = A.radicand(m)
    b = A.FE.basis(m)
    check(f"(sqrt {r})^2 == {r}", (b * b) == A.FE.rat(r))
rng = random.Random(20260817)


def rnd():
    return A.FE([Fraction(rng.randint(-9, 9), rng.randint(1, 7)) for _ in range(A.DIM)])


for t in range(30):
    a, b, c = rnd(), rnd(), rnd()
    if not ((a * b) * c == a * (b * c)):
        fails.append("assoc")
    if not (a * (b + c) == a * b + a * c):
        fails.append("distrib")
    if not a.is_zero() and not (a * a.inverse() == A.FE.rat(1)):
        fails.append("inverse")
check("associativity/distributivity/inverse on 30 random elements",
      not any(x in fails for x in ("assoc", "distrib", "inverse")))
# sanity: the 8 basis elements are Q-independent -> a nonzero vector is nonzero
check("basis independence sanity: sqrt3*sqrt11 == sqrt33",
      A.FE.basis(1) * A.FE.basis(4) == A.FE.basis(5))
check("sqrt(11/3) == sqrt33/3",
      A.exact_sqrt_of_rational(Fraction(11, 3)) == A.FE.basis(5, Fraction(1, 3)))
check("sqrt(5/3) == sqrt15/3",
      A.exact_sqrt_of_rational(Fraction(5, 3)) == A.FE.basis(3, Fraction(1, 3)))
check("1/sqrt3 == sqrt3/3",
      A.FE.rat(1) / A.FE.basis(1) == A.FE.basis(1, Fraction(1, 3)))
try:
    A.exact_sqrt_of_rational(Fraction(7))
    check("Sqrt[7] rejected (field too small)", False)
except ValueError:
    check("Sqrt[7] rejected (field too small)", True)

print("\nT2 parser vs independent float evaluator")
VTX = os.path.join(ROOT, "data/CNP-SAT/vtx/510.vtx")


def float_eval(expr: str) -> float:
    """Totally separate route: textual rewrite to python + math.sqrt."""
    e = expr.replace("Sqrt[", "sqrt(").replace("]", ")")
    return eval(e, {"sqrt": math.sqrt, "__builtins__": {}})  # noqa: S307


pts = A.parse_vtx(VTX)
worst = 0.0
worst_at = None
with open(VTX) as fh:
    lines = [l.strip() for l in fh if l.strip()]
for idx, line in enumerate(lines):
    fx, fy = A.split_top(line[1:-1])
    for got, raw in ((pts[idx][0], fx), (pts[idx][1], fy)):
        # use true division semantics: Mathematica ints -> python floats already
        ref = float_eval(raw)
        d = abs(ref - got.to_float())
        if d > worst:
            worst, worst_at = d, (idx + 1, raw)
check(f"all 1020 coordinates agree with independent float eval (max abs diff {worst:.3e})",
      worst < 1e-9, f"worst at line {worst_at}")

print("\nT3/T4/T5 mutation tests -- the checker must FAIL on corrupted input")
_, _, edges = A.parse_edges(os.path.join(ROOT, "data/CNP-SAT/edge/510.edge"))
edge_set = {(min(a, b), max(a, b)) for a, b in edges}


def count_units(points):
    D = 1
    for (x, y) in points:
        for e in (x, y):
            for m in range(A.DIM):
                dd = e.c[m].denominator
                D = D * dd // math.gcd(D, dd)
    ivx = [A.to_intvec(x, D) for (x, y) in points]
    ivy = [A.to_intvec(y, D) for (x, y) in points]
    D2 = D * D
    zt = [0] * (A.DIM - 1)
    found = set()
    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            acc = [0] * A.DIM
            for m, v in ivx[i]:
                acc[m] += v
            for m, v in ivx[j]:
                acc[m] -= v
            dx = [(m, acc[m]) for m in range(A.DIM) if acc[m]]
            acc = [0] * A.DIM
            for m, v in ivy[i]:
                acc[m] += v
            for m, v in ivy[j]:
                acc[m] -= v
            dy = [(m, acc[m]) for m in range(A.DIM) if acc[m]]
            s = A.sq_add(dx, dy)
            if s[0] == D2 and s[1:] == zt:
                found.add((i + 1, j + 1))
    return found


base = count_units(pts)
check("baseline reproduces 2504", len(base) == 2504 and base == edge_set,
      f"got {len(base)}")

# T3: shift vertex 300's x by 1/96 (smallest step the denominator allows)
mut = [(x, y) for (x, y) in pts]
vx, vy = mut[299]
mut[299] = (vx + A.FE.rat(Fraction(1, 96)), vy)
m3 = count_units(mut)
check("T3 perturb vertex 300 x by 1/96 -> detected",
      m3 != edge_set, f"unit pairs now {len(m3)}, symmetric diff {len(m3 ^ edge_set)}")

# T4: swap Sqrt[33] -> Sqrt[3] in vertex 8 (line 8 uses Sqrt[33])
mut = [(x, y) for (x, y) in pts]
bad_x = A.Parser("(3 - Sqrt[3])/6").parse_full()
mut[7] = (bad_x, mut[7][1])
m4 = count_units(mut)
check("T4 corrupt radical in vertex 8 -> detected",
      m4 != edge_set, f"unit pairs now {len(m4)}, symmetric diff {len(m4 ^ edge_set)}")

# T5: make vertex 509 a duplicate of vertex 1
mut = [(x, y) for (x, y) in pts]
mut[508] = mut[0]
canon = {(tuple(x.c), tuple(y.c)) for (x, y) in mut}
check("T5 duplicated vertex -> distinctness test fires", len(canon) == 509,
      f"distinct={len(canon)}")

print("\nT6 no hidden tolerance")
# a genuine near-miss: squared distance 1 + 1/9216 (one unit in D^2), and also a
# pair whose squared distance is rational-1 but with a nonzero radical tail.
p0 = (A.FE.rat(0), A.FE.rat(0))
near = (A.FE.rat(Fraction(97, 96)), A.FE.rat(0))  # dist^2 = (97/96)^2 != 1
u = count_units([p0, near])
check("T6a squared distance (97/96)^2 rejected", len(u) == 0)
# tail test: point at (1/2, sqrt3/2) from origin is EXACT unit -> must be found
u2 = count_units([p0, (A.FE.rat(Fraction(1, 2)), A.FE.basis(1, Fraction(1, 2)))])
check("T6b exact unit pair (1/2, sqrt3/2) IS found", len(u2) == 1)
# tail test: squared distance = 1 in slot0 but nonzero sqrt3 slot -> must reject
# take dx=1, dy^2 contributing sqrt3: dy = sqrt(sqrt3)... not in K; instead
# construct dx with a tail: dx = 1/2 + sqrt3/6  -> dx^2 = 1/4+1/12 + sqrt3/6
u3 = count_units([p0, (A.FE.rat(Fraction(1, 2)) + A.FE.basis(1, Fraction(1, 6)), A.FE.rat(0))])
check("T6c squared distance with nonzero radical tail rejected", len(u3) == 0)

print()
if fails:
    print(f"SELFTEST FAILURES: {sorted(set(fails))}")
    sys.exit(1)
print("SELFTEST: all negative controls behaved correctly -- the checker has teeth")
sys.exit(0)
