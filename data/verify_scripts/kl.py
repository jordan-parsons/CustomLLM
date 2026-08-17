#!/usr/bin/env python3
"""Test K = J u rot(J) and L = K u rot(K); and look for the sqrt(15) rotation
(2*asin(1/4), cos=7/8) in the graphs whose coordinates involve sqrt(5)."""
import itertools, os, sys
import mpmath as mp
mp.mp.dps = 40
import sympy as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify import parse_vtx

R3 = mp.sqrt(3)
w = mp.exp(1j * mp.pi / 3)

def norm(a, b):
    return a * a + a * b + b * b

J_lat = [(a, b) for a in range(-4, 5) for b in range(-4, 5) if norm(a, b) <= 7]
J = [a + b * w for (a, b) in J_lat]
assert len(J) == 31

def kk(z, dps=24):
    return (mp.nstr(mp.re(z) + 0, dps), mp.nstr(mp.im(z) + 0, dps))

def uniq(P):
    d = {}
    for p in P:
        d.setdefault(kk(p), p)
    return list(d.values())

def upairs(P):
    return sum(1 for a, b in itertools.combinations(range(len(P)), 2)
               if abs(abs(P[a] - P[b]) - 1) < mp.mpf('1e-25'))

def rot(P, th):
    e = mp.exp(1j * th)
    return [p * e for p in P]

alpha = mp.acos(mp.mpf(5) / 6)          # = 2*asin(1/(2 sqrt3)) ~ 33.5573 deg
theta0 = mp.asin(1 / (2 * R3))          # ~ 16.7786 deg
beta = 2 * mp.asin(mp.mpf(1) / 4)       # cos=7/8, sin=sqrt15/8 ~ 28.955 deg

print("|J| =", len(J), " unit pairs in J =", upairs(J))
for nm, th in [("alpha=acos(5/6) ~33.5573", alpha),
               ("theta0=asin(1/(2sqrt3)) ~16.7786", theta0),
               ("beta=2asin(1/4) ~28.955", beta)]:
    K = uniq(J + rot(J, th))
    print(f"K = J u rot(J,{nm:34s}) -> |K|={len(K):4d} unitpairs={upairs(K)}")
    if len(K) == 61:
        for nm2, th2 in [("alpha", alpha), ("theta0", theta0), ("beta", beta),
                         ("-alpha", -alpha), ("-theta0", -theta0)]:
            L = uniq(K + rot(K, th2))
            print(f"      L = K u rot(K,{nm2:8s}) -> |L|={len(L):4d} unitpairs={upairs(L)}")

# ---- rotation spectrum restricted to interesting angles, for 510 / 517 / 553
ROOT = "/home/user/CustomLLM/data/CNP-SAT/vtx"
targets = {"theta0 asin(1/(2sqrt3))": theta0, "alpha acos(5/6)": alpha,
           "beta 2asin(1/4) cos7/8": beta, "asin(1/4)": mp.asin(mp.mpf(1)/4),
           "60deg": mp.pi/3}
for nm in ['510', '517', '553', 'S199']:
    pts = parse_vtx(os.path.join(ROOT, nm + '.vtx'))
    num = [mp.mpc(mp.mpf(str(sp.N(x, 40))), mp.mpf(str(sp.N(y, 40)))) for x, y in pts]
    ks = set(kk(z, 22) for z in num)
    print(f"\n{nm} (n={len(num)}): points mapped back into the set by rotation about origin")
    for lbl, th in targets.items():
        for sgn in (1, -1):
            c = sum(1 for z in num if kk(z * mp.exp(1j * sgn * th), 22) in ks)
            print(f"   {lbl:26s} sign={sgn:+d}  {c:4d}/{len(num)}")
