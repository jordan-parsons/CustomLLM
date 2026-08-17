#!/usr/bin/env python3
"""ADVERSARY 1 / CHECK 2 -- fully independent exact-arithmetic verification of
data/CNP-SAT/vtx/510.vtx against data/CNP-SAT/edge/510.edge.

Deliberately imports NOTHING from hn.* (no hn.field, hn.point, hn.detect,
hn.mathematica).  No sympy.  No floats decide anything -- floats are used only
to print a human-readable sanity column, never to accept or reject a pair.

Field model
-----------
Every coordinate appearing in 510.vtx lies in K = Q(sqrt3, sqrt5, sqrt11),
a degree-8 extension of Q.  Integral basis used here:

    b[m] = sqrt(product of primes selected by bitmask m)
    bit 0 -> 3,  bit 1 -> 5,  bit 2 -> 11

    m: 0->1  1->sqrt3  2->sqrt5  3->sqrt15
       4->sqrt11  5->sqrt33  6->sqrt55  7->sqrt165

These 8 elements are Q-linearly independent (K has degree 8 over Q because
3, 5, 11 are multiplicatively independent modulo squares), so a field element
has a UNIQUE coefficient vector and equality testing is coefficient-wise.
That is the whole reason this is a proof and not an approximation.

    b[i] * b[j] = (product of primes in i AND j) * b[i XOR j]

Sqrt[11/3] and Sqrt[5/3] and 1/Sqrt[3] are handled symbolically by the parser:
    Sqrt[p/q] = sqrt(p*q)/q,   1/Sqrt[3] = sqrt3/3.
No rational is ever approximated.

Usage:  python3 tests/adv1_exact.py [--vtx PATH] [--edge PATH]
Exit code 0 iff every assertion in the report passes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import os
import re
import sys
import time
from fractions import Fraction

PRIMES = (3, 5, 11)
DIM = 8

# ---------------------------------------------------------------- mult table
# MULT[i][j] = (factor, target_index)
MULT = [[None] * DIM for _ in range(DIM)]
for _i in range(DIM):
    for _j in range(DIM):
        _f = 1
        for _b, _p in enumerate(PRIMES):
            if (_i >> _b) & 1 and (_j >> _b) & 1:
                _f *= _p
        MULT[_i][_j] = (_f, _i ^ _j)

BASIS_NAME = {0: "1", 1: "r3", 2: "r5", 3: "r15", 4: "r11", 5: "r33", 6: "r55", 7: "r165"}


def radicand(m: int) -> int:
    r = 1
    for b, p in enumerate(PRIMES):
        if (m >> b) & 1:
            r *= p
    return r


# ---------------------------------------------------------------- field elem
class FE:
    """Element of K as an 8-vector of Fractions over the basis above."""

    __slots__ = ("c",)

    def __init__(self, coeffs=None):
        self.c = list(coeffs) if coeffs is not None else [Fraction(0)] * DIM

    @staticmethod
    def rat(q) -> "FE":
        e = FE()
        e.c[0] = Fraction(q)
        return e

    @staticmethod
    def basis(m: int, coeff=1) -> "FE":
        e = FE()
        e.c[m] = Fraction(coeff)
        return e

    def __add__(self, o):
        return FE([a + b for a, b in zip(self.c, o.c)])

    def __sub__(self, o):
        return FE([a - b for a, b in zip(self.c, o.c)])

    def __neg__(self):
        return FE([-a for a in self.c])

    def __mul__(self, o):
        out = [Fraction(0)] * DIM
        sc, oc = self.c, o.c
        for i in range(DIM):
            ai = sc[i]
            if ai == 0:
                continue
            row = MULT[i]
            for j in range(DIM):
                bj = oc[j]
                if bj == 0:
                    continue
                f, t = row[j]
                out[t] += ai * bj * f
        return FE(out)

    def is_zero(self) -> bool:
        return all(x == 0 for x in self.c)

    def __eq__(self, o):
        return self.c == o.c

    def __hash__(self):
        return hash(tuple(self.c))

    # ---- inversion by exact 8x8 linear solve:  find x with self*x = 1 ----
    def inverse(self) -> "FE":
        if self.is_zero():
            raise ZeroDivisionError("inverse of 0 in K")
        # column j of M is self * b[j]
        M = [[Fraction(0)] * DIM for _ in range(DIM)]
        for j in range(DIM):
            col = (self * FE.basis(j)).c
            for r in range(DIM):
                M[r][j] = col[r]
        rhs = [Fraction(0)] * DIM
        rhs[0] = Fraction(1)
        # Gaussian elimination with exact rationals
        A = [M[r][:] + [rhs[r]] for r in range(DIM)]
        piv_cols = []
        row = 0
        for col in range(DIM):
            sel = None
            for r in range(row, DIM):
                if A[r][col] != 0:
                    sel = r
                    break
            if sel is None:
                continue
            A[row], A[sel] = A[sel], A[row]
            pv = A[row][col]
            A[row] = [v / pv for v in A[row]]
            for r in range(DIM):
                if r != row and A[r][col] != 0:
                    fac = A[r][col]
                    A[r] = [a - fac * b for a, b in zip(A[r], A[row])]
            piv_cols.append(col)
            row += 1
            if row == DIM:
                break
        if row != DIM:
            raise ArithmeticError("singular multiplication matrix -- basis assumption broken")
        x = [Fraction(0)] * DIM
        for r, col in enumerate(piv_cols):
            x[col] = A[r][DIM]
        res = FE(x)
        chk = self * res
        if chk != FE.rat(1):
            raise ArithmeticError("inversion self-check failed")
        return res

    def __truediv__(self, o):
        return self * o.inverse()

    def to_float(self) -> float:
        import math

        s = 0.0
        for m in range(DIM):
            if self.c[m]:
                s += float(self.c[m]) * math.sqrt(radicand(m))
        return s

    def __repr__(self):
        parts = [f"{self.c[m]}*{BASIS_NAME[m]}" for m in range(DIM) if self.c[m]]
        return "(" + " + ".join(parts) + ")" if parts else "(0)"


def exact_sqrt_of_rational(q: Fraction) -> FE:
    """Sqrt[q] for positive rational q, exactly, as an element of K.
    sqrt(a/b) = sqrt(a*b)/b.  sqrt(integer) = s * sqrt(squarefree part);
    the squarefree part MUST divide 3*5*11 or we abort (field too small)."""
    if q <= 0:
        raise ValueError(f"Sqrt of non-positive rational {q}")
    a, b = q.numerator, q.denominator
    n = a * b  # positive integer
    # extract square part
    sq = 1
    rem = n
    d = 2
    while d * d <= rem:
        while rem % (d * d) == 0:
            rem //= d * d
            sq *= d
        d += 1
    # rem is now squarefree
    mask = 0
    r = rem
    for bit, p in enumerate(PRIMES):
        if r % p == 0:
            r //= p
            mask |= 1 << bit
    if r != 1:
        raise ValueError(
            f"Sqrt[{q}] has squarefree part {rem}, not a product of {PRIMES}: "
            "field Q(sqrt3,sqrt5,sqrt11) is INSUFFICIENT -- abort, do not guess"
        )
    return FE.basis(mask, Fraction(sq, b))


# ---------------------------------------------------------------- parser
TOKEN_RE = re.compile(r"\s*(Sqrt\[|\d+|[()\[\]+\-*/,{}])")


class Parser:
    """Recursive-descent parser for the Mathematica subset in the .vtx files.

    grammar:
        expr   := term (('+'|'-') term)*
        term   := unary (('*'|'/') unary)*
        unary  := ('-' | '+') unary | atom
        atom   := INT | 'Sqrt[' expr ']' | '(' expr ')'
    Sqrt[...] evaluates its argument, which must be a *rational* (coefficient
    vector supported only in slot 0), then takes the exact rational sqrt.
    """

    def __init__(self, s: str):
        self.s = s
        self.i = 0
        self.toks = []
        self._lex()
        self.p = 0

    def _lex(self):
        i = 0
        s = self.s
        n = len(s)
        while i < n:
            if s[i].isspace():
                i += 1
                continue
            if s.startswith("Sqrt[", i):
                self.toks.append("Sqrt[")
                i += 5
                continue
            if s[i].isdigit():
                j = i
                while j < n and s[j].isdigit():
                    j += 1
                self.toks.append(s[i:j])
                i = j
                continue
            if s[i] in "()[]+-*/,{}":
                self.toks.append(s[i])
                i += 1
                continue
            raise SyntaxError(f"unexpected char {s[i]!r} at {i} in {s!r}")

    def peek(self):
        return self.toks[self.p] if self.p < len(self.toks) else None

    def eat(self, t=None):
        cur = self.peek()
        if t is not None and cur != t:
            raise SyntaxError(f"expected {t!r} got {cur!r} (pos {self.p}) in {self.s!r}")
        self.p += 1
        return cur

    def expr(self) -> FE:
        v = self.term()
        while self.peek() in ("+", "-"):
            op = self.eat()
            r = self.term()
            v = v + r if op == "+" else v - r
        return v

    def term(self) -> FE:
        v = self.unary()
        while self.peek() in ("*", "/"):
            op = self.eat()
            r = self.unary()
            v = v * r if op == "*" else v / r
        return v

    def unary(self) -> FE:
        t = self.peek()
        if t == "-":
            self.eat()
            return -self.unary()
        if t == "+":
            self.eat()
            return self.unary()
        return self.atom()

    def atom(self) -> FE:
        t = self.peek()
        if t == "(":
            self.eat("(")
            v = self.expr()
            self.eat(")")
            return v
        if t == "Sqrt[":
            self.eat("Sqrt[")
            arg = self.expr()
            self.eat("]")
            if any(arg.c[m] != 0 for m in range(1, DIM)):
                raise ValueError(f"Sqrt of non-rational argument {arg} -- unsupported, abort")
            return exact_sqrt_of_rational(arg.c[0])
        if t is not None and t.isdigit():
            self.eat()
            return FE.rat(int(t))
        raise SyntaxError(f"unexpected token {t!r} in {self.s!r}")

    def parse_full(self) -> FE:
        v = self.expr()
        if self.p != len(self.toks):
            raise SyntaxError(f"trailing tokens {self.toks[self.p:]} in {self.s!r}")
        return v


def split_top(s: str) -> list:
    """Split on commas at depth 0 of (), []."""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def parse_vtx(path: str):
    pts = []
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            if not (line.startswith("{") and line.endswith("}")):
                raise SyntaxError(f"{path}:{lineno}: not a brace pair: {line!r}")
            inner = line[1:-1]
            fields = split_top(inner)
            if len(fields) != 2:
                raise SyntaxError(f"{path}:{lineno}: expected 2 coords, got {len(fields)}")
            x = Parser(fields[0]).parse_full()
            y = Parser(fields[1]).parse_full()
            pts.append((x, y))
    return pts


def parse_edges(path: str):
    edges = []
    n = m = None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("p "):
                tk = line.split()
                n, m = int(tk[2]), int(tk[3])
            elif line.startswith("e "):
                tk = line.split()
                edges.append((int(tk[1]), int(tk[2])))
            elif line.startswith("c"):
                continue
            else:
                raise SyntaxError(f"unrecognised edge line {line!r}")
    return n, m, edges


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# --------------------------------------------------- fast integer-vector core
def to_intvec(e: FE, D: int):
    """Return sparse [(idx, int)] of D*e; asserts D clears all denominators."""
    out = []
    for m in range(DIM):
        v = e.c[m]
        if v == 0:
            continue
        num = v * D
        if num.denominator != 1:
            raise ArithmeticError("global denominator does not clear coefficient")
        out.append((m, int(num)))
    return out


def sq_add(dx, dy):
    """Exact (dx^2 + dy^2) as a dense length-8 integer list, dx/dy sparse."""
    out = [0] * DIM
    for vec in (dx, dy):
        L = len(vec)
        for a in range(L):
            ia, va = vec[a]
            f, t = MULT[ia][ia]
            out[t] += f * va * va
            for b in range(a + 1, L):
                ib, vb = vec[b]
                f, t = MULT[ia][ib]
                out[t] += 2 * f * va * vb
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--vtx", default=os.path.join(root, "data/CNP-SAT/vtx/510.vtx"))
    ap.add_argument("--edge", default=os.path.join(root, "data/CNP-SAT/edge/510.edge"))
    args = ap.parse_args()

    ok = True
    t0 = time.time()
    print("=" * 74)
    print("ADVERSARY 1 / CHECK 2 -- independent exact unit-distance verification")
    print("=" * 74)
    print(f"vtx  : {args.vtx}\n       sha256 {sha256(args.vtx)}")
    print(f"edge : {args.edge}\n       sha256 {sha256(args.edge)}")

    pts = parse_vtx(args.vtx)
    n_v = len(pts)
    print(f"\n[parse] parsed {n_v} vertices exactly in K=Q(sqrt3,sqrt5,sqrt11)")

    n_hdr, m_hdr, edges = parse_edges(args.edge)
    print(f"[parse] edge header: p edge {n_hdr} {m_hdr}; parsed {len(edges)} 'e' lines")
    if n_hdr != n_v:
        print(f"*** ALARM: header n={n_hdr} != vertices parsed {n_v}")
        ok = False
    if m_hdr != len(edges):
        print(f"*** ALARM: header m={m_hdr} != edge lines {len(edges)}")
        ok = False

    # duplicate / self-loop / range checks on the edge list itself
    seen = set()
    dup = []
    loops = []
    for (a, b) in edges:
        if a == b:
            loops.append((a, b))
        if not (1 <= a <= n_v and 1 <= b <= n_v):
            print(f"*** ALARM: edge index out of range: {a} {b}")
            ok = False
        key = (min(a, b), max(a, b))
        if key in seen:
            dup.append(key)
        seen.add(key)
    print(f"[edgelist] self-loops={len(loops)} duplicate-undirected-pairs={len(dup)} "
          f"distinct-undirected={len(seen)}")
    if loops or dup:
        print(f"*** ALARM: loops={loops[:5]} dups={dup[:5]}")
        ok = False

    # ---- global denominator ----
    D = 1
    for (x, y) in pts:
        for e in (x, y):
            for m in range(DIM):
                d = e.c[m].denominator
                if d != 1:
                    D = D * d // __import__("math").gcd(D, d)
    print(f"\n[algebra] global common denominator D = {D}")
    ivx = [to_intvec(x, D) for (x, y) in pts]
    ivy = [to_intvec(y, D) for (x, y) in pts]
    D2 = D * D
    print(f"[algebra] all coordinates cleared to integer vectors; target D^2 = {D2}")

    # ---- distinctness, exact ----
    canon = {}
    dupv = []
    for i in range(n_v):
        key = (tuple(pts[i][0].c), tuple(pts[i][1].c))
        if key in canon:
            dupv.append((canon[key], i))
        else:
            canon[key] = i
    print(f"\n[distinct] exactly-distinct vertices: {len(canon)} / {n_v}")
    if dupv:
        print(f"*** ALARM: coincident vertices (0-indexed): {dupv[:10]}")
        ok = False
    else:
        print("[distinct] PASS: all 510 vertices are pairwise distinct exactly")

    # ---- (b) ALL pairs, exact ----
    print(f"\n[all-pairs] running ALL C({n_v},2) = {n_v*(n_v-1)//2} pairs in exact arithmetic ...")
    unit_pairs = set()
    ZERO_TAIL = [0] * (DIM - 1)
    checked = 0
    for i in range(n_v):
        xi, yi = ivx[i], ivy[i]
        for j in range(i + 1, n_v):
            # exact difference of sparse integer vectors
            acc = [0] * DIM
            for m, v in xi:
                acc[m] += v
            for m, v in ivx[j]:
                acc[m] -= v
            dx = [(m, acc[m]) for m in range(DIM) if acc[m]]
            acc = [0] * DIM
            for m, v in yi:
                acc[m] += v
            for m, v in ivy[j]:
                acc[m] -= v
            dy = [(m, acc[m]) for m in range(DIM) if acc[m]]
            s = sq_add(dx, dy)
            checked += 1
            if s[0] == D2 and s[1:] == ZERO_TAIL:
                unit_pairs.add((i + 1, j + 1))
    dt = time.time() - t0
    print(f"[all-pairs] pairs examined exactly: {checked}")
    print(f"[all-pairs] EXACT unit pairs found: {len(unit_pairs)}   ({dt:.1f}s elapsed)")

    edge_set = {(min(a, b), max(a, b)) for (a, b) in edges}
    missing = sorted(edge_set - unit_pairs)   # claimed edges that are NOT unit
    extra = sorted(unit_pairs - edge_set)     # unit pairs NOT in the edge list

    print(f"\n[direction a] claimed edges whose squared distance != 1 exactly: {len(missing)}")
    if missing:
        print(f"*** SOUNDNESS ALARM: non-unit claimed edges: {missing[:20]}")
        ok = False
    else:
        print(f"[direction a] PASS: all {len(edge_set)} claimed edges are EXACTLY unit distance")

    print(f"[direction b] exact unit pairs missing from the edge list: {len(extra)}")
    if extra:
        print(f"*** ALARM (edge list INCOMPLETE): {extra[:20]}")
        ok = False
    else:
        print("[direction b] PASS: edge list is COMPLETE -- no unit pair omitted")

    if len(unit_pairs) != 2504:
        print(f"\n*** ALARM: unit-pair count {len(unit_pairs)} != 2504 as reported")
        ok = False
    else:
        print("\n[count] PASS: exact unit-pair count is 2504, matching the report")

    # ---- degree / structural cross-checks (exact-derived, no floats) ----
    deg = [0] * (n_v + 1)
    for (a, b) in unit_pairs:
        deg[a] += 1
        deg[b] += 1
    iso = [v for v in range(1, n_v + 1) if deg[v] == 0]
    print(f"\n[struct] min degree {min(deg[1:])} max degree {max(deg[1:])} "
          f"isolated vertices {len(iso)}")
    if iso:
        print(f"[struct] NOTE isolated vertices (1-indexed): {iso}")

    print("\n" + "=" * 74)
    print("CHECK 2 RESULT:", "ALL EXACT ASSERTIONS PASS" if ok else "FAILURE / ALARM RAISED")
    print("=" * 74)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
