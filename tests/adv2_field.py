#!/usr/bin/env python3
"""ADVERSARY 2 / CATEGORY B -- soundness of the exact field layer.

Everything downstream (every edge, every CNF, every verdict) rests on two
claims made by src/hn/field.py:

  (i)  the 2^k products of square roots of the generators are Q-linearly
       independent, so a FieldElem's coefficient vector is CANONICAL and
       `equals_rational(1)` is a valid unit-distance test;
  (ii) the guard in MultiQuadField.__init__ (squarefree, pairwise coprime, >= 2)
       is sufficient for (i).

The reference oracle here is RIGOROUS interval arithmetic in exact integers:
sqrt(r) is bracketed by isqrt(r*10^(2P))/10^P and that + 10^-P, so a field
element's value is bracketed by two Fractions with a proven error bound. No
floats are used anywhere in this file, so the test cannot be fooled by the same
rounding it is testing for.

Run:  python tests/adv2_field.py
"""
import itertools
import random
import sys
from fractions import Fraction as F

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.field import (DEGREY_FIELD, FieldElem, MultiQuadField, Rat,  # noqa: E402
                      _exact_sign, _is_squarefree)

FAIL = []


def report(name, ok, detail=""):
    print(f"[{'ok ' if ok else 'HOLE'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------------------
# rigorous exact-integer interval oracle
# ---------------------------------------------------------------------------
def isqrt_frac(n: int, P: int):
    """(lo, hi) Fractions with lo <= sqrt(n) <= hi and hi-lo <= 10^-P."""
    import math
    scale = 10 ** P
    r = math.isqrt(n * scale * scale)
    return F(r, scale), F(r + 1, scale)


def radicand(field, mask):
    r = 1
    for i in range(field.k):
        if mask >> i & 1:
            r *= field.gens[i]
    return r


def interval(e: FieldElem, P: int = 200):
    """Rigorous (lo, hi) enclosure of e's real value, in exact Fractions."""
    lo = hi = F(0)
    for s, v in enumerate(e.coeffs):
        if v == 0:
            continue
        if s == 0:
            lo += v
            hi += v
            continue
        a, b = isqrt_frac(radicand(e.field, s), P)
        if v > 0:
            lo += v * a
            hi += v * b
        else:
            lo += v * b
            hi += v * a
    return lo, hi


def proven_sign(e: FieldElem, P0: int = 60, Pmax: int = 6000):
    """Sign of e proven by interval refinement, or None if it looks like 0."""
    P = P0
    while P <= Pmax:
        lo, hi = interval(e, P)
        if lo > 0:
            return 1
        if hi < 0:
            return -1
        P *= 4
    return None


# ---------------------------------------------------------------------------
# B1  the generator guard
# ---------------------------------------------------------------------------
def b1_generator_guard():
    cases = [
        ((1,), "generator 1 (< 2)"),
        ((0,), "generator 0"),
        ((-3,), "negative generator"),
        ((4,), "perfect square 4"),
        ((9,), "perfect square 9"),
        ((12,), "non-squarefree 12 = 4*3"),
        ((18,), "non-squarefree 18 = 9*2"),
        ((75,), "non-squarefree 75 = 25*3"),
        ((2, 2), "duplicate generators"),
        ((6, 10), "not coprime (gcd 2)"),
        ((6, 10, 15), "THE classic dependence: sqrt6*sqrt10*sqrt15 = 30"),
        ((10, 15), "not coprime (gcd 5)"),
        ((3, 33), "not coprime: sqrt33 = sqrt3*sqrt11 already"),
        ((2, 3, 6), "6 = 2*3, product of the others"),
        ((2 * 3, 3 * 5, 5 * 2), "pairwise non-coprime cycle, product a square"),
    ]
    bad = []
    for gens, why in cases:
        try:
            MultiQuadField(gens)
            bad.append(f"ACCEPTED {gens} ({why})")
        except ValueError:
            pass
        except Exception as ex:  # wrong exception type is still a rejection
            if not isinstance(ex, ValueError):
                bad.append(f"{gens} rejected with {type(ex).__name__}: {ex}")
    # and the legitimate ones must be accepted
    for gens in [(2,), (3,), (3, 11), (3, 5, 11), (6, 35), (2, 15), (5, 7, 11, 13)]:
        try:
            MultiQuadField(gens)
        except Exception as ex:
            bad.append(f"REJECTED legitimate {gens}: {ex}")
    report("B1 generator guard", not bad, "; ".join(bad) or
           f"all {len(cases)} degenerate generator sets rejected, 7 legitimate "
           "ones accepted (incl. the sqrt6*sqrt10*sqrt15=30 collapse)")


def b1b_squarefree_helper():
    """Independently re-derive squarefreeness and diff against _is_squarefree."""
    def ref(n):
        if n < 2:
            return False
        d = 2
        m = n
        while d * d <= m:
            if m % (d * d) == 0:
                return False
            d += 1
        return True
    bad = [n for n in range(-5, 20000) if _is_squarefree(n) != ref(n)]
    report("B1b _is_squarefree vs independent reference on [-5, 20000)",
           not bad, f"mismatches: {bad[:10]}" if bad else "0 mismatches")


# ---------------------------------------------------------------------------
# B2  basis independence: can a nonzero coefficient vector be the number 0?
# ---------------------------------------------------------------------------
def b2_independence():
    rnd = random.Random(20260817)
    fields = [MultiQuadField(g) for g in
              [(3, 11), (3, 5, 11), (2, 3, 5, 7), (6, 35), (2, 15), (5, 7, 11, 13)]]
    problems = []
    tested = 0
    for f in fields:
        for _ in range(120):
            coeffs = [Rat(rnd.randint(-40, 40), rnd.randint(1, 40))
                      for _ in range(f.dim)]
            if all(c == 0 for c in coeffs):
                continue
            e = f.elem(coeffs)
            tested += 1
            if e.is_zero():
                problems.append(f"{f}: is_zero() true on nonzero coeffs")
                continue
            if proven_sign(e) is None:
                problems.append(f"{f}: nonzero coeff vector {coeffs} could not be "
                                "proven != 0 at 6000 digits -- DEPENDENT BASIS")
        # every basis element must be irrational and distinct
        for s in range(1, f.dim):
            b = f.elem([1 if i == s else 0 for i in range(f.dim)])
            if b.is_rational():
                problems.append(f"{f}: basis {s} claims to be rational")
            tested += 1
    report("B2 basis independence (random elements proven nonzero)",
           not problems, "; ".join(problems[:4]) or
           f"{tested} elements over 6 fields: every nonzero coefficient vector "
           "was PROVEN to have nonzero real value by interval refinement")


# ---------------------------------------------------------------------------
# B3  _exact_sign against the interval oracle, including nasty inputs
# ---------------------------------------------------------------------------
def b3_exact_sign():
    K = MultiQuadField((3, 5, 11))
    r3, r5, r11 = K.sqrt_gen(3), K.sqrt_gen(5), K.sqrt_gen(11)
    r15, r33, r55, r165 = K.sqrt_gen(15), K.sqrt_gen(33), K.sqrt_gen(55), K.sqrt_gen(165)
    problems = []

    # (a) exact zeros written as differences of equal irrationals
    zeros = [
        ("sqrt15 - sqrt3*sqrt5", r15 - r3 * r5),
        ("sqrt165 - sqrt3*sqrt55", r165 - r3 * r55),
        ("sqrt33*sqrt5 - sqrt165", r33 * r5 - r165),
        ("(sqrt3+sqrt5)^2 - (8+2sqrt15)", (r3 + r5) * (r3 + r5) - (r15 * 2 + 8)),
        ("nested: ((sqrt3-sqrt5)^2 - (8-2sqrt15))", (r3 - r5) * (r3 - r5) - (8 - r15 * 2)),
    ]
    for name, z in zeros:
        if not z.is_zero():
            problems.append(f"{name}: is_zero() FALSE (coeffs {z.coeffs})")
        if z.sign() != 0:
            problems.append(f"{name}: sign() = {z.sign()}, expected 0")

    # (b) deliberately tiny nonzero values: rational convergents to irrationals
    tiny = []
    # p/q -> sqrt3 convergents: 1,2,5/3,7/4,19/11,26/15,71/41,97/56,265/153...
    conv = [(1, 1), (2, 1), (5, 3), (7, 4), (19, 11), (26, 15), (71, 41),
            (97, 56), (265, 153), (362, 209), (989, 571), (1351, 780),
            (18817, 10864), (708158, 408815)]
    for p, q in conv:
        tiny.append((f"sqrt3 - {p}/{q}", r3 - Rat(p, q)))
    # and a nested cancellation that is ~1e-30
    big = 10 ** 15
    tiny.append(("(sqrt3*10^15 - 1732050807568877/10^0)/10^15 scale",
                 r3 * big - Rat(1732050807568877293, 10 ** 3)))
    for name, e in tiny:
        want = proven_sign(e)
        got = e.sign()
        if want is None:
            problems.append(f"{name}: oracle could not prove a sign")
        elif got != want:
            lo, hi = interval(e, 60)
            problems.append(f"{name}: sign()={got} but proven sign is {want} "
                            f"(value in [{float(lo):.3e},{float(hi):.3e}])")

    # (c) random elements, many of them, in the degree-8 field
    rnd = random.Random(4242)
    for _ in range(400):
        coeffs = [Rat(rnd.randint(-9, 9), rnd.randint(1, 9)) for _ in range(K.dim)]
        e = K.elem(coeffs)
        if e.is_zero():
            if e.sign() != 0:
                problems.append("zero element got nonzero sign")
            continue
        want = proven_sign(e)
        got = e.sign()
        if want != got:
            problems.append(f"random {coeffs}: sign()={got} proven={want}")

    # (d) adversarial near-zero: A + B*sqrt3 with |value| ~ 1e-40
    Q3 = 10 ** 80
    import math as _m
    P3 = _m.isqrt(3 * Q3 * Q3)
    for scale in (10 ** 6, 10 ** 12, 10 ** 20):
        A = F(scale)
        B = -F(A * Q3, P3)
        e = MultiQuadField((3,)).elem([A, B])
        want = proven_sign(e)
        got = e.sign()
        if want != got:
            problems.append(f"cancelling scale {scale}: sign()={got} proven={want}")

    report("B3 _exact_sign vs rigorous interval oracle",
           not problems, "; ".join(problems[:4]) or
           f"{len(zeros)} exact-zero identities, {len(tiny)} near-zero "
           "convergents, 400 random degree-8 elements, 3 cancelling elements "
           "with |value| < 1e-40: sign() agreed with the proven sign every time")


# ---------------------------------------------------------------------------
# B4  inverse() and the norm
# ---------------------------------------------------------------------------
def b4_inverse():
    problems = []
    rnd = random.Random(99)
    for gens in [(3, 11), (3, 5, 11), (2, 15)]:
        f = MultiQuadField(gens)
        for _ in range(80):
            coeffs = [Rat(rnd.randint(-6, 6), rnd.randint(1, 6)) for _ in range(f.dim)]
            e = f.elem(coeffs)
            if e.is_zero():
                continue
            inv = e.inverse()
            if not (e * inv).equals_rational(1):
                problems.append(f"{f}: e*e^-1 != 1 for {coeffs}")
            if not (inv * e).equals_rational(1):
                problems.append(f"{f}: e^-1*e != 1 for {coeffs}")
            # norm must be rational and its sign consistent
            num = f.one()
            for mask in range(1, f.dim):
                num = num * e.conjugate(mask)
            nrm = e * num
            if not nrm.is_rational():
                problems.append(f"{f}: norm not rational for {coeffs}")
            elif nrm.as_rational() == 0:
                problems.append(f"{f}: ZERO norm on nonzero element {coeffs}")
        # zero must raise
        try:
            f.zero().inverse()
            problems.append(f"{f}: inverse of zero did not raise")
        except ZeroDivisionError:
            pass
    # conjugation is a ring homomorphism and flips exactly the right radicals
    K = MultiQuadField((3, 5, 11))
    for mask in range(K.dim):
        a = K.elem([Rat(rnd.randint(-5, 5)) for _ in range(K.dim)])
        b = K.elem([Rat(rnd.randint(-5, 5)) for _ in range(K.dim)])
        if (a * b).conjugate(mask) != a.conjugate(mask) * b.conjugate(mask):
            problems.append(f"conjugate not multiplicative at mask {mask}")
        if (a + b).conjugate(mask) != a.conjugate(mask) + b.conjugate(mask):
            problems.append(f"conjugate not additive at mask {mask}")
        if a.conjugate(mask).conjugate(mask) != a:
            problems.append(f"conjugate not an involution at mask {mask}")
    report("B4 inverse() / norm / conjugation", not problems,
           "; ".join(problems[:4]) or
           "240 random inverses over 3 fields verified exactly; norms rational "
           "and nonzero; conjugation is an additive+multiplicative involution "
           "for all 8 masks; inverse(0) raises ZeroDivisionError")


# ---------------------------------------------------------------------------
# B5  can equals_rational(1) be fooled?
# ---------------------------------------------------------------------------
def b5_equals_rational():
    K = MultiQuadField((3, 5, 11))
    problems = []
    # (a) things that ARE exactly 1, written obscurely
    r3, r5, r11 = K.sqrt_gen(3), K.sqrt_gen(5), K.sqrt_gen(11)
    ones = [
        ("sqrt3^2/3", (r3 * r3) * Rat(1, 3)),
        ("(5/6)^2 + (sqrt11/6)^2", K.rational(Rat(5, 6)) ** 2 if False else
         K.rational(Rat(5, 6)) * K.rational(Rat(5, 6)) + (r11 * Rat(1, 6)) * (r11 * Rat(1, 6))),
        ("(1/2)^2+(sqrt3/2)^2", K.rational(Rat(1, 2)) * K.rational(Rat(1, 2))
         + (r3 * Rat(1, 2)) * (r3 * Rat(1, 2))),
        ("sqrt15/(sqrt3*sqrt5)", K.sqrt_gen(15) * (r3 * r5).inverse()),
        ("norm-form (2+sqrt3)(2-sqrt3)", (r3 + 2) * (2 - r3)),
    ]
    for name, e in ones:
        if not e.equals_rational(1):
            problems.append(f"{name}: equals_rational(1) FALSE (coeffs {e.coeffs})")
    # (b) things that are astronomically close to 1 but not 1
    Q = 10 ** 120
    import math as _m
    P = _m.isqrt(3 * Q * Q)
    nears = [
        ("1 + 1/10^300", K.rational(1 + Rat(1, 10 ** 300))),
        ("1 - 1/10^300", K.rational(1 - Rat(1, 10 ** 300))),
        ("1 + (sqrt3 - p/q)  [|d| < 1e-120]", K.one() + (r3 - Rat(P, Q))),
        ("1 + sqrt165/10^400", K.one() + K.sqrt_gen(165) * Rat(1, 10 ** 400)),
        ("1 + (sqrt3*10^100 - a/10^..)", K.one()
         + (r3 * (10 ** 100) - Rat(P * 10 ** 100, Q))),
    ]
    for name, e in nears:
        if e.equals_rational(1):
            problems.append(f"{name}: equals_rational(1) TRUE -- FOOLED")
        lo, hi = interval(e, 400)
        if not (lo <= 1 <= hi or abs(float(hi - 1)) < 1e-100):
            pass  # only a sanity note; the point is equals_rational must be False
    # (c) float ingestion: does the constructor silently accept a float?
    float_accepted = None
    try:
        e = K.rational(0.1)
        float_accepted = e.coeffs[0]
    except (TypeError, ValueError):
        float_accepted = None
    ok = not problems
    detail = "; ".join(problems[:4]) or (
        f"{len(ones)} obscure exact-1 forms all recognised; {len(nears)} "
        "elements within 1e-120..1e-400 of 1 all correctly rejected")
    report("B5 equals_rational(1) cannot be fooled", ok, detail)

    # reported separately: this is a different (input-hygiene) issue
    if float_accepted is not None:
        report("B5b float ingestion into exact coefficients", False,
               f"MultiQuadField.rational(0.1) silently returned the dyadic "
               f"Fraction {float_accepted} instead of raising; elem([...]) does "
               "the same via Fraction(float). Exactness is preserved but the "
               "point is NOT the point the caller asked for -- there is no "
               "guard against a float entering the coordinate pipeline.")
    else:
        report("B5b float ingestion into exact coefficients", True,
               "floats are rejected by the constructors")


# ---------------------------------------------------------------------------
# B6  key()/hash() consistency across fields (dedup correctness)
# ---------------------------------------------------------------------------
def b6_key_collisions():
    A = MultiQuadField((3, 11))
    B = MultiQuadField((5, 7))
    a = A.elem([1, 2, 3, 4])
    b = B.elem([1, 2, 3, 4])
    same_key = a.key() == b.key()
    same_hash = hash(a) == hash(b)
    from hn.point import Point, dedup_points
    pa = Point(a, A.zero())
    pb = Point(b, B.zero())
    dd = dedup_points([pa, pb])
    report("B6 FieldElem.key() ignores the field", not same_key,
           f"key(a)==key(b) across DIFFERENT fields: {same_key}; hash equal: "
           f"{same_hash}; dedup_points([p_from_Q(3,11), p_from_Q(5,7)]) kept "
           f"{len(dd)} of 2 points -- points from different fields collapse, "
           "and Point.__eq__ raises TypeError rather than returning False"
           if same_key else "keys are field-tagged")


def b7_sqrt_gen_and_dos():
    """sqrt_gen must never silently swallow a square factor, and the squarefree
    guard's cost must not be a denial of service on a large generator."""
    import time
    K = MultiQuadField((3, 11))
    problems = []
    for bad in (9, 12, 99, 6, 0, 2, 5, 33 * 4):
        try:
            e = K.sqrt_gen(bad)
            if bad == 33 * 4:
                problems.append(f"sqrt_gen({bad}) accepted -> {e!r} (4 swallowed)")
            elif bad in (9, 12, 99, 6, 0, 2, 5):
                problems.append(f"sqrt_gen({bad}) accepted -> {e!r}")
        except ValueError:
            pass
    for good, want in ((3, 3), (11, 11), (33, 33), (1, 1)):
        e = K.sqrt_gen(good)
        if not (e * e).equals_rational(want):
            problems.append(f"sqrt_gen({good})^2 != {want}")
    # cost of the squarefree guard
    p = 1000003 ** 2          # 12 digits, one big square factor
    t0 = time.time()
    try:
        MultiQuadField((p,))
    except ValueError:
        pass
    slow = time.time() - t0
    report("B7 sqrt_gen rejects square factors", not problems,
           "; ".join(problems[:4]) or
           "sqrt_gen rejects 9,12,99,6,0,2,5,132 and squares correctly for "
           f"3,11,33,1. Guard cost note: _is_squarefree({p}) took {slow:.2f}s "
           "(trial division to sqrt(n)); a 30-digit generator would hang the "
           "constructor -- availability only, not soundness")


if __name__ == "__main__":
    b1_generator_guard()
    b1b_squarefree_helper()
    b2_independence()
    b3_exact_sign()
    b4_inverse()
    b5_equals_rational()
    b6_key_collisions()
    b7_sqrt_gen_and_dos()
    print()
    if FAIL:
        print("HOLES FOUND:", ", ".join(FAIL))
        sys.exit(1)
    print("no holes found in category B")
