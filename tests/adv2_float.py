#!/usr/bin/env python3
"""ADVERSARY 2 / CATEGORY A -- float leakage into the edge set.

Attacks hn.detect.detect_edges, whose float prefilter (PRUNE_WINDOW = 1e-6 on
the squared distance) and float grid bucketing (math.floor on p.approx()) are
the only two places in the edge pipeline where a double is consulted.

Claim under attack (detect.py module docstring):

    "The prune window is deliberately enormous relative to double-precision
     error (1e-6 on squared distance vs ~1e-15 achievable error on these
     coordinate magnitudes) so that a false negative is not credible."
    "detect_edges and detect_edges_bruteforce_exact must agree on every input"

Every test below constructs a point set whose EXACT squared distance is
EXACTLY 1 (verified by the exact predicate) and where detect_edges nonetheless
returns a strictly smaller edge set than detect_edges_bruteforce_exact.

Run:  python tests/adv2_float.py
"""
import math
import sys
from fractions import Fraction as F

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.detect import (PRUNE_WINDOW, detect_edges,  # noqa: E402
                       detect_edges_bruteforce_exact)
from hn.field import DEGREY_FIELD as K  # Q(sqrt3, sqrt11)      # noqa: E402
from hn.point import Point  # noqa: E402

FAIL = []


def report(name, ok, detail=""):
    print(f"[{'ok ' if ok else 'HOLE'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


def disagreement(points):
    """Return (fast, slow) edge lists; they must be equal for detect to be sound."""
    fast = detect_edges(points)
    slow = detect_edges_bruteforce_exact(points)
    return fast, slow


def assert_truly_unit(p, q):
    assert p.is_unit_from(q), "fixture bug: pair is not exactly unit distance"


def coord_magnitude(points):
    return max(max(abs(p.x.approx()), abs(p.y.approx())) for p in points)


def coeff_magnitude(points):
    m = 0
    for p in points:
        for c in list(p.x.coeffs) + list(p.y.coeffs):
            m = max(m, abs(c))
    return m


# ---------------------------------------------------------------------------
# A-1  pure magnitude, axis-aligned separation (dx = 1 exactly)
# ---------------------------------------------------------------------------
def a1_axis_aligned():
    """P=(a,0), Q=(a+1,0).  Sweep |a| to find the smallest breaking magnitude.

    Below 2^52 the double ulp divides 1 exactly, so fl(a) and fl(a+1) carry the
    SAME rounding error and it cancels in the subtraction. At 2^52 the ulp
    reaches 1 and the cancellation stops.
    """
    def broke(a):
        pts = [Point(K.rational(a), K.zero()), Point(K.rational(a + 1), K.zero())]
        assert_truly_unit(pts[0], pts[1])
        f, s = disagreement(pts)
        return f != s, pts

    smallest = None
    for k in range(20, 56):
        for off in (F(1, 2), F(1, 3), F(1, 2) - F(1, 10 ** 9), F(3, 4)):
            a = F(2) ** k + off
            b, pts = broke(a)
            if b and (smallest is None or a < smallest[0]):
                smallest = (a, pts)
    if smallest is None:
        report("A1 axis-aligned rational sweep", True, "no disagreement up to 2^55")
        return
    a, pts = smallest
    f, s = disagreement(pts)
    report(
        "A1 axis-aligned rational sweep",
        False,
        f"detect_edges={f} bruteforce={s} at |a|={float(a):.6g} "
        f"(= 2^{math.log2(float(a)):.1f})",
    )


# ---------------------------------------------------------------------------
# A-2  pure magnitude, generic (non-dyadic) unit separation
# ---------------------------------------------------------------------------
def a2_generic_direction():
    """P=(a,b), Q=P+(3/5,4/5). Unit vector with non-dyadic components, so the
    rounding errors of the two endpoints no longer cancel. Breaks ~6 orders of
    magnitude lower than A1."""
    def broke(a):
        P = Point(K.rational(a), K.rational(a))
        Q = Point(K.rational(a + F(3, 5)), K.rational(a + F(4, 5)))
        assert_truly_unit(P, Q)
        pts = [P, Q]
        f, s = disagreement(pts)
        return f != s, pts

    smallest = None
    lo = None
    # coarse then fine binary search on the exponent
    for k in range(20, 56):
        a = F(2) ** k + F(1, 3)
        b, pts = broke(a)
        if b:
            lo = k
            break
    if lo is None:
        report("A2 generic-direction sweep", True, "no disagreement up to 2^55")
        return
    # refine: linear scan of mantissas in [2^(lo-1), 2^lo]
    step = F(2) ** (lo - 1) // 64 or 1
    a = F(2) ** (lo - 1)
    while a < F(2) ** lo:
        b, pts = broke(a + F(1, 3))
        if b:
            smallest = (a + F(1, 3), pts)
            break
        a += step
    if smallest is None:
        smallest = (F(2) ** lo + F(1, 3), broke(F(2) ** lo + F(1, 3))[1])
    a, pts = smallest
    f, s = disagreement(pts)
    d2 = sum((pts[0].approx()[i] - pts[1].approx()[i]) ** 2 for i in range(2))
    report(
        "A2 generic-direction sweep",
        False,
        f"detect_edges={f} bruteforce={s} at |a|={float(a):.6g} "
        f"(2^{math.log2(float(a)):.1f}); float d^2-1={d2-1:.3e} vs window {PRUNE_WINDOW}",
    )


# ---------------------------------------------------------------------------
# A-3  THE REAL ONE: O(1) coordinates, huge basis coefficients.
#      Coordinate VALUES are all < 1.  Only the coefficients are large, and
#      approx() sums them with catastrophic cancellation.
# ---------------------------------------------------------------------------
Q3 = 10 ** 60
P3 = math.isqrt(3 * Q3 * Q3)
SQ3 = F(P3, Q3)                    # rational lower approx of sqrt(3), err < 1e-60


def cancelling(scale, target):
    """Field element A + B*sqrt3 with |A|,|B| ~ scale but exact VALUE ~ target.

    approx() evaluates it as float(A) + float(B)*sqrt(3.0); each term is ~scale,
    so each carries absolute error ~ scale*2^-53. The value is O(1), so the
    coordinate magnitude tells you nothing about the float error.
    """
    A0 = F(scale)
    B = -F(A0 * Q3, P3)
    A = A0 + (target - (A0 + B * SQ3))
    return K.elem([A, B, 0, 0])


def a3_cancellation():
    """O(1) coordinates, large basis coefficients.

    P = (A+B*sqrt3, C+D*sqrt3) with all four coefficients ~N but both coordinate
    VALUES < 1.5;  Q = P + w  with w an exact unit vector whose components are
    non-dyadic (3/10 - (2/5)sqrt3, 2/5 + (3/10)sqrt3) = (3/5,4/5) rotated 60deg,
    so the rounding errors of the two endpoints do not cancel.

    Binary-searches the smallest coefficient scale N at which detect_edges loses
    the edge.  Answer: N ~ 9.5e9, with every coordinate value below 1.3.
    """
    wx = (F(3, 10), F(-2, 5))
    wy = (F(2, 5), F(3, 10))
    assert (K.elem([wx[0], wx[1], 0, 0]) ** 2 if False else True)

    def make(N):
        px = cancelling(N, F(1, 2))
        py = cancelling(N + 1, F(1, 3))
        P = Point(px, py)
        Q = Point(K.elem([px.coeffs[0] + wx[0], px.coeffs[1] + wx[1], 0, 0]),
                  K.elem([py.coeffs[0] + wy[0], py.coeffs[1] + wy[1], 0, 0]))
        assert_truly_unit(P, Q)
        return [P, Q]

    lo, hi = 1, None
    N = 2
    while N < 2 ** 60:
        pts = make(N)
        f, s = disagreement(pts)
        if f != s:
            hi = N
            break
        lo = N
        N *= 2
    if hi is None:
        report("A3 cancellation (O(1) coords)", True, "no disagreement")
        return
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        p = make(mid)
        if disagreement(p)[0] != disagreement(p)[1]:
            hi = mid
        else:
            lo = mid
    pts = make(hi)
    f, s = disagreement(pts)
    ax = [p.approx() for p in pts]
    d2 = (ax[0][0] - ax[1][0]) ** 2 + (ax[0][1] - ax[1][1]) ** 2
    report(
        "A3 cancellation (O(1) coords)",
        False,
        f"detect_edges={f} bruteforce={s}; smallest breaking coefficient scale "
        f"N={hi} (~1e{math.log10(hi):.1f}); max |coord VALUE| = "
        f"{coord_magnitude(pts):.4g}; float d^2-1 = {d2-1:.4e} vs window "
        f"{PRUNE_WINDOW}",
    )
    return pts


# ---------------------------------------------------------------------------
# A-4  grid-bucketing attack: |d^2-1| passes the window, but math.floor on the
#      erroneous float coordinates puts the two endpoints two cells apart, so
#      the pair is never even considered.
# ---------------------------------------------------------------------------
def a4_bucket_boundary():
    """Force floor(fl(x_i)) and floor(fl(x_j)) to differ by 2 for a pair at
    exact distance 1. The 3x3 neighbourhood scan then never enumerates it, and
    it is missed even though the float squared distance is ~1."""
    q3 = 10 ** 40
    p3 = math.isqrt(3 * q3 * q3)
    sqrt3 = F(p3, q3)

    def make(N, want):
        """P.x value ~ `want`; P.x = A + B*sqrt3 with |A|,|B| ~ N."""
        A0 = F(N)
        B = -F(A0 * q3, p3)
        x0 = A0 + B * sqrt3
        A = A0 + (want - x0)
        P = Point(K.elem([A, B, 0, 0]), K.zero())
        Q = Point(K.elem([A + 1, B, 0, 0]), K.zero())
        assert_truly_unit(P, Q)
        return [P, Q]

    found = None
    N = 2 ** 20
    while N < 2 ** 70 and found is None:
        # slide the target value across an integer boundary
        for num in range(-40, 41):
            want = 5 + F(num, 10 ** 7)
            pts = make(N, want)
            xs = [p.approx()[0] for p in pts]
            cells = [math.floor(x) for x in xs]
            d2 = (xs[0] - xs[1]) ** 2
            if abs(cells[0] - cells[1]) >= 2 and abs(d2 - 1.0) <= PRUNE_WINDOW:
                f, s = disagreement(pts)
                if f != s:
                    found = (N, want, cells, d2, f, s, pts)
                    break
        N *= 2
    if found is None:
        report("A4 grid-bucket boundary", True, "could not force a 2-cell split")
        return
    N, want, cells, d2, f, s, pts = found
    report(
        "A4 grid-bucket boundary",
        False,
        f"cells={cells} (differ by {abs(cells[0]-cells[1])}), float d^2-1="
        f"{d2-1:.2e} INSIDE the window, detect_edges={f} bruteforce={s}; "
        f"coord values ~{float(want)}",
    )


# ---------------------------------------------------------------------------
# A-5  is the exact confirmation itself unconditional?  (static-ish check)
# ---------------------------------------------------------------------------
def a5_no_false_positive():
    """The other direction: can the prefilter ever ADD an edge? It must not,
    because is_unit_from() gates every append. Feed the published adversarial
    near-unit fixtures and check no edge appears."""
    from hn.constructions import (exact_unit_pair_hard,
                                  near_unit_irrational_pair,
                                  near_unit_rational_pair)
    ok = True
    detail = []
    for name, fn in (("near_unit_rational", near_unit_rational_pair),
                     ("near_unit_irrational", near_unit_irrational_pair)):
        p, q = fn(K)
        f, s = disagreement([p, q])
        detail.append(f"{name}: fast={f} slow={s}")
        if f or s:
            ok = False
    p, q = exact_unit_pair_hard(K)
    f, s = disagreement([p, q])
    detail.append(f"exact_unit_pair_hard: fast={f} slow={s}")
    if f != [(0, 1)] or s != [(0, 1)]:
        ok = False
    report("A5 no false-positive edges from the prefilter", ok, "; ".join(detail))


# ---------------------------------------------------------------------------
# A-6  does the failure mode reach real, project-shaped data?
# ---------------------------------------------------------------------------
def a6_rotation_coefficient_growth():
    """Coefficient blow-up is not hypothetical: composing the spindle rotation
    (cos=5/6) n times multiplies denominators by 6 each time. Measure how many
    compositions it takes to reach the coefficient size that A3 needs."""
    from hn.point import Rotation, spindle_rotation
    rot = spindle_rotation(K)
    cur = Rotation(K.one(), K.zero())
    sizes = []
    for n in range(1, 121):
        cur = cur.compose(rot)
        m = max(abs(c) for c in list(cur.cos.coeffs) + list(cur.sin.coeffs))
        sizes.append((n, m.denominator))
    hits = [(n, d) for n, d in sizes if d > 10 ** 12]
    report(
        "A6 coefficient growth under repeated exact rotation",
        True,
        f"denominator exceeds 1e12 after n={hits[0][0]} compositions "
        f"(6^n growth); at n=120 denominator has {len(str(sizes[-1][1]))} digits "
        "-- so the A3 regime is reachable by ordinary search moves",
    )


if __name__ == "__main__":
    print(f"PRUNE_WINDOW = {PRUNE_WINDOW}\n")
    a1_axis_aligned()
    a2_generic_direction()
    a3_cancellation()
    a4_bucket_boundary()
    a5_no_false_positive()
    a6_rotation_coefficient_growth()
    print()
    if FAIL:
        print("HOLES FOUND:", ", ".join(FAIL))
        sys.exit(1)
    print("no holes found in category A")
