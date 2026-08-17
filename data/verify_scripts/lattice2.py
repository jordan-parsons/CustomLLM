#!/usr/bin/env python3
"""Exact verification of de Grey's H, J via Eisenstein integers, and
empirical extraction of the rotation angles present in the real data."""
import itertools
from fractions import Fraction as F
import mpmath as mp
mp.mp.dps = 40

# ---------- Part 1: exact lattice verification ----------
# lattice point (a,b) = a + b*w, w = exp(i pi/3);  |a+bw|^2 = a^2+ab+b^2
def norm(a, b):
    return a * a + a * b + b * b

R = 12
lat = [(a, b) for a in range(-R, R + 1) for b in range(-R, R + 1)]

H = [(0, 0), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
print("H =", H)
print("  |H| =", len(H), " norms:", sorted(set(norm(*p) for p in H)))
print("  unit pairs in H:",
      sum(1 for p, q in itertools.combinations(H, 2) if norm(p[0]-q[0], p[1]-q[1]) == 1))

J = [(a, b) for (a, b) in lat if norm(a, b) <= 7]
Js = set(J)
print("\nJ = {(a,b): a^2+ab+b^2 <= 7}")
print("  |J| =", len(J), "  <-- expect 31")
from collections import Counter
print("  norm distribution:", dict(sorted(Counter(norm(*p) for p in J).items())))
print("  unit pairs in J:",
      sum(1 for p, q in itertools.combinations(J, 2) if norm(p[0]-q[0], p[1]-q[1]) == 1))
cops = [c for c in lat if all((c[0]+h[0], c[1]+h[1]) in Js for h in H)]
print("  copies of H fully contained in J:", len(cops))
print("  centre norms of those copies:", dict(sorted(Counter(norm(*c) for c in cops).items())))
union = set()
for c in cops:
    for h in H:
        union.add((c[0]+h[0], c[1]+h[1]))
print("  union of those 13 copies has", len(union), "points; equals J?", union == Js)

# ---------- Part 2: rotation spectrum in the real data ----------
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sympy as sp
from verify import parse_vtx

def spectrum(path, label):
    pts = parse_vtx(path)
    n = len(pts)
    num = [mp.mpc(mp.mpf(str(sp.N(x, 40))), mp.mpf(str(sp.N(y, 40)))) for x, y in pts]
    keys = {}
    for z in num:
        keys[(mp.nstr(mp.re(z)+0, 22), mp.nstr(mp.im(z)+0, 22))] = True
    def inset(z):
        return (mp.nstr(mp.re(z)+0, 22), mp.nstr(mp.im(z)+0, 22)) in keys
    # candidate rotations about the origin: angle(q)-angle(p) for |p|==|q|
    byr = {}
    for z in num:
        r = mp.nstr(abs(z), 20)
        byr.setdefault(r, []).append(z)
    cand = {}
    for r, group in byr.items():
        if float(r) < 1e-15 or len(group) < 2:
            continue
        for p, q in itertools.permutations(group, 2):
            th = mp.arg(q) - mp.arg(p)
            th = mp.fmod(th + 2*mp.pi, 2*mp.pi)
            cand[mp.nstr(th, 16)] = th
    scored = []
    for ks, th in cand.items():
        e = mp.exp(1j * th)
        c = sum(1 for z in num if inset(z * e))
        scored.append((c, th))
    scored.sort(reverse=True, key=lambda t: t[0])
    print(f"\n{label}: n={n}. Top rotations about origin mapping many points back into the set:")
    seen = []
    for c, th in scored:
        d = float(th * 180 / mp.pi)
        if any(abs(d - x) < 1e-6 for x in seen):
            continue
        seen.append(d)
        if len(seen) > 14:
            break
        cosv = mp.cos(th); sinv = mp.sin(th)
        # try to identify cos as a simple rational
        idc = ""
        for q in range(1, 200):
            for p in range(-q, q+1):
                if abs(cosv - mp.mpf(p)/q) < mp.mpf('1e-25'):
                    idc = f"cos={p}/{q}"
                    break
            if idc:
                break
        s2 = sinv**2
        ids = ""
        for q in range(1, 400):
            for p in range(0, 4*q+1):
                if abs(s2 - mp.mpf(p)/q) < mp.mpf('1e-25'):
                    ids = f"sin^2={p}/{q}"
                    break
            if ids:
                break
        print(f"   {d:10.5f} deg  maps {c:4d}/{n} pts into set   {idc:12s} {ids}")

ROOT = "/home/user/CustomLLM/data/CNP-SAT/vtx"
for nm in ['S199', 'L403', 'G2167', '553', '510']:
    try:
        spectrum(os.path.join(ROOT, nm + '.vtx'), nm)
    except Exception as ex:
        print(nm, "ERROR", ex)
