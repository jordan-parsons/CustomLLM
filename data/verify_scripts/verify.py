#!/usr/bin/env python3
"""Verify Heule CNP-SAT unit-distance graphs:
   (a) every declared edge has EXACT squared distance 1 (symbolic, sympy)
   (b) the graph is not 4-colorable (pysat)
"""
import re, sys, os
import sympy as sp
from pysat.solvers import Cadical153
from pysat.formula import IDPool

ROOT = "/home/user/CustomLLM/data/CNP-SAT"


def parse_vtx(path):
    pts = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\{(.*)\}$', line)
        assert m, (path, line)
        body = m.group(1)
        # split on top-level comma
        depth = 0
        for i, ch in enumerate(body):
            if ch in '[(':
                depth += 1
            elif ch in '])':
                depth -= 1
            elif ch == ',' and depth == 0:
                cut = i
                break
        else:
            raise AssertionError("no comma: " + line)
        xs, ys = body[:cut], body[cut + 1:]
        conv = lambda s: sp.sympify(s.replace('Sqrt[', 'sqrt(').replace(']', ')'),
                                    rational=True)
        pts.append((conv(xs), conv(ys)))
    return pts


def parse_edge(path):
    edges, decl = [], None
    for line in open(path):
        t = line.split()
        if not t:
            continue
        if t[0] == 'p':
            decl = (int(t[2]), int(t[3]))
        elif t[0] == 'e':
            edges.append((int(t[1]), int(t[2])))
    return decl, edges


def check_unit(pts, edges):
    bad = []
    for (a, b) in edges:
        dx = pts[a - 1][0] - pts[b - 1][0]
        dy = pts[a - 1][1] - pts[b - 1][1]
        d2 = sp.expand(dx * dx + dy * dy)
        if sp.simplify(sp.nsimplify(d2) - 1) != 0:
            bad.append((a, b, d2))
    return bad


def four_colorable(n, edges, k=4):
    pool = IDPool()
    v = lambda i, c: pool.id(('v', i, c))
    with Cadical153() as s:
        for i in range(1, n + 1):
            s.add_clause([v(i, c) for c in range(k)])
        for (a, b) in edges:
            for c in range(k):
                s.add_clause([-v(a, c), -v(b, c)])
        # symmetry break on first edge
        if edges:
            a, b = edges[0]
            s.add_clause([v(a, 0)])
            s.add_clause([v(b, 1)])
        return s.solve()


names = sys.argv[1:] or ['510', '517', '529', '553', '610', '633', '803', '826', '874',
                         'L403', 'S199', 'T721']
for nm in names:
    ep = os.path.join(ROOT, 'edge', nm + '.edge')
    vp = os.path.join(ROOT, 'vtx', nm + '.vtx')
    if not os.path.exists(ep):
        print(f"{nm}: NO .edge file"); continue
    decl, edges = parse_edge(ep)
    nv = decl[0]
    have_v = os.path.exists(vp)
    line = f"{nm}: declared p edge {decl[0]} {decl[1]} | actual edges={len(edges)}"
    maxv = max(max(e) for e in edges)
    line += f" | max vertex index={maxv}"
    if have_v:
        pts = parse_vtx(vp)
        line += f" | vtx points={len(pts)}"
        bad = check_unit(pts, edges)
        line += f" | NON-UNIT EDGES={len(bad)}"
        if bad:
            line += f" e.g. {bad[:3]}"
    else:
        line += " | no .vtx"
    c4 = four_colorable(nv, edges)
    line += f" | 4-colorable={c4}  => chi{'<=4' if c4 else '>=5'}"
    print(line, flush=True)
