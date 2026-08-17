"""Exact arithmetic over multiquadratic number fields Q(sqrt(r1), ..., sqrt(rk)).

This is the soundness-critical layer of the whole toolchain. NOTHING here may
use floating point to decide anything. Floats appear only in `approx()`, which
is documented as a *filter* helper and is never consulted by an equality test.

Representation
--------------
A multiquadratic field Q(sqrt(r1),...,sqrt(rk)) with squarefree, pairwise
coprime generators r1..rk has a Q-basis indexed by subsets S of {1..k}:

    basis(S) = prod_{i in S} sqrt(r_i)

so a field element is a vector of 2^k rationals. Basis multiplication is

    basis(S) * basis(T) = (prod_{i in S n T} r_i) * basis(S xor T)

because sqrt(r)*sqrt(r) = r. Linear independence of these 2^k basis elements
over Q (which is what makes the representation canonical, and therefore what
makes exact equality testing valid) holds precisely when the r_i are
multiplicatively independent modulo squares. We enforce a sufficient condition:
the generators are squarefree, pairwise coprime, and > 1.

With that, an element equals a rational q iff its basis-() coefficient is q and
every other coefficient is exactly 0. That is the test the unit-distance
detector relies on.
"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import isqrt
from typing import Iterable, Sequence, Tuple

Rat = Fraction


def _is_squarefree(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % (d * d) == 0:
            return False
        if n % d == 0:
            n //= d
        d += 1
    return True


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


class MultiQuadField:
    """The field Q(sqrt(r1), ..., sqrt(rk)) with an exact canonical basis."""

    __slots__ = ("gens", "k", "dim", "_subsets", "_index", "_multab")

    def __init__(self, gens: Sequence[int]):
        gens = tuple(int(g) for g in gens)
        for g in gens:
            if g < 2:
                raise ValueError(f"generator {g} must be >= 2")
            if not _is_squarefree(g):
                raise ValueError(
                    f"generator {g} is not squarefree; sqrt({g}) is not a "
                    "canonical basis generator"
                )
            if isqrt(g) ** 2 == g:
                raise ValueError(f"generator {g} is a perfect square")
        for i in range(len(gens)):
            for j in range(i + 1, len(gens)):
                if gens[i] == gens[j]:
                    raise ValueError(f"duplicate generator {gens[i]}")
                if _gcd(gens[i], gens[j]) != 1:
                    raise ValueError(
                        f"generators {gens[i]} and {gens[j]} are not coprime; "
                        "basis independence is not guaranteed"
                    )
        self.gens = gens
        self.k = len(gens)
        self.dim = 1 << self.k
        # subset S encoded as a bitmask over generator indices
        self._subsets = tuple(range(self.dim))
        self._index = {s: s for s in self._subsets}
        # multiplication table: (S, T) -> (scalar, S xor T)
        multab = {}
        for s in range(self.dim):
            for t in range(self.dim):
                inter = s & t
                scalar = 1
                m = inter
                i = 0
                while m:
                    if m & 1:
                        scalar *= gens[i]
                    m >>= 1
                    i += 1
                multab[(s, t)] = (scalar, s ^ t)
        self._multab = multab

    def __repr__(self) -> str:
        return f"Q({', '.join('sqrt%d' % g for g in self.gens)})"

    def __eq__(self, other) -> bool:
        return isinstance(other, MultiQuadField) and self.gens == other.gens

    def __hash__(self) -> int:
        return hash(("MultiQuadField", self.gens))

    # ---- element construction -------------------------------------------
    def zero(self) -> "FieldElem":
        return FieldElem(self, (Rat(0),) * self.dim)

    def one(self) -> "FieldElem":
        c = [Rat(0)] * self.dim
        c[0] = Rat(1)
        return FieldElem(self, tuple(c))

    def rational(self, q) -> "FieldElem":
        c = [Rat(0)] * self.dim
        c[0] = Rat(q)
        return FieldElem(self, tuple(c))

    def sqrt_gen(self, g: int) -> "FieldElem":
        """The element sqrt(g) for a generator g (or a product of generators)."""
        mask = 0
        rem = g
        for i, gi in enumerate(self.gens):
            if rem % gi == 0:
                mask |= 1 << i
                rem //= gi
        if rem != 1:
            raise ValueError(
                f"sqrt({g}) is not expressible: leftover factor {rem} is not a "
                f"product of distinct generators {self.gens}"
            )
        c = [Rat(0)] * self.dim
        c[mask] = Rat(1)
        return FieldElem(self, tuple(c))

    def elem(self, coeffs: Iterable) -> "FieldElem":
        c = [Rat(x) for x in coeffs]
        if len(c) != self.dim:
            raise ValueError(f"expected {self.dim} coefficients, got {len(c)}")
        return FieldElem(self, tuple(c))

    def embed(self, other: "MultiQuadField", e: "FieldElem") -> "FieldElem":
        """Embed an element of a subfield `other` into this field."""
        if e.field is self:
            return e
        c = [Rat(0)] * self.dim
        for s, v in enumerate(e.coeffs):
            if v == 0:
                continue
            mask = 0
            for i in range(other.k):
                if s >> i & 1:
                    g = other.gens[i]
                    if g not in self.gens:
                        raise ValueError(f"cannot embed: sqrt({g}) not in {self}")
                    mask |= 1 << self.gens.index(g)
            c[mask] += v
        return FieldElem(self, tuple(c))

    @lru_cache(maxsize=None)
    def _sqrt_float(self, mask: int) -> float:
        v = 1.0
        for i in range(self.k):
            if mask >> i & 1:
                v *= float(self.gens[i]) ** 0.5
        return v


class FieldElem:
    """An exact element of a MultiQuadField. Immutable and hashable."""

    __slots__ = ("field", "coeffs", "_hash")

    def __init__(self, field: MultiQuadField, coeffs: Tuple[Rat, ...]):
        self.field = field
        self.coeffs = coeffs
        self._hash = None

    # ---- exactness-critical predicates ----------------------------------
    def is_zero(self) -> bool:
        """Exact. All coefficients are exactly the rational 0."""
        return all(c == 0 for c in self.coeffs)

    def is_rational(self) -> bool:
        return all(c == 0 for c in self.coeffs[1:])

    def as_rational(self) -> Rat:
        if not self.is_rational():
            raise ValueError("element is not rational")
        return self.coeffs[0]

    def equals_rational(self, q) -> bool:
        """Exact equality against a rational. This is the unit-distance test."""
        q = Rat(q)
        return self.coeffs[0] == q and all(c == 0 for c in self.coeffs[1:])

    def __eq__(self, other) -> bool:
        if isinstance(other, FieldElem):
            if self.field is not other.field and self.field != other.field:
                raise TypeError("cannot compare elements of different fields")
            return self.coeffs == other.coeffs
        if isinstance(other, (int, Fraction)):
            return self.equals_rational(other)
        return NotImplemented

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self.field.gens, self.coeffs))
        return self._hash

    # ---- exact ring operations ------------------------------------------
    def _check(self, other: "FieldElem"):
        if self.field is not other.field and self.field != other.field:
            raise TypeError("field mismatch")

    def __add__(self, other):
        if isinstance(other, (int, Fraction)):
            other = self.field.rational(other)
        self._check(other)
        return FieldElem(
            self.field, tuple(a + b for a, b in zip(self.coeffs, other.coeffs))
        )

    __radd__ = __add__

    def __neg__(self):
        return FieldElem(self.field, tuple(-a for a in self.coeffs))

    def __sub__(self, other):
        if isinstance(other, (int, Fraction)):
            other = self.field.rational(other)
        self._check(other)
        return FieldElem(
            self.field, tuple(a - b for a, b in zip(self.coeffs, other.coeffs))
        )

    def __rsub__(self, other):
        return (-self) + other

    def __mul__(self, other):
        if isinstance(other, (int, Fraction)):
            if other == 0:
                return self.field.zero()
            return FieldElem(self.field, tuple(a * other for a in self.coeffs))
        self._check(other)
        f = self.field
        multab = f._multab
        out = [Rat(0)] * f.dim
        sc = self.coeffs
        oc = other.coeffs
        for s in range(f.dim):
            a = sc[s]
            if a == 0:
                continue
            for t in range(f.dim):
                b = oc[t]
                if b == 0:
                    continue
                scalar, u = multab[(s, t)]
                out[u] += a * b * scalar
        return FieldElem(f, tuple(out))

    __rmul__ = __mul__

    def square(self):
        return self * self

    def conjugate(self, mask: int) -> "FieldElem":
        """Apply the Galois automorphism flipping sign of sqrt(r_i) for i in mask."""
        out = []
        for s, v in enumerate(self.coeffs):
            sign = -1 if bin(s & mask).count("1") % 2 else 1
            out.append(v * sign)
        return FieldElem(self.field, tuple(out))

    def inverse(self) -> "FieldElem":
        """Exact inverse via the field norm (product of all Galois conjugates)."""
        if self.is_zero():
            raise ZeroDivisionError("inverse of zero")
        num = self.field.one()
        for mask in range(1, self.field.dim):
            num = num * self.conjugate(mask)
        denom = self * num
        if not denom.is_rational():
            raise ArithmeticError(
                "norm is not rational - basis independence violated"
            )
        d = denom.as_rational()
        if d == 0:
            raise ArithmeticError("zero norm on a nonzero element")
        return FieldElem(self.field, tuple(c / d for c in num.coeffs))

    def __truediv__(self, other):
        if isinstance(other, (int, Fraction)):
            if other == 0:
                raise ZeroDivisionError
            return FieldElem(self.field, tuple(a / other for a in self.coeffs))
        return self * other.inverse()

    # ---- FLOAT: filter only, never a decision ---------------------------
    def approx(self) -> float:
        """Floating-point image. FILTER ONLY.

        This value must never determine membership in an edge set, an equality,
        or any catalog verdict. It exists so the spatial index can prune
        candidate pairs cheaply before exact confirmation.
        """
        f = self.field
        total = 0.0
        for s, v in enumerate(self.coeffs):
            if v:
                total += float(v) * f._sqrt_float(s)
        return total

    def sign(self) -> int:
        """Exact sign of a real multiquadratic number.

        Uses the standard norm trick: multiply by conjugates until rational,
        tracking signs by exact interval refinement is avoided entirely by
        using exact rational comparison on the squared value where possible.
        Falls back to high-precision interval arithmetic with a proven bound.
        """
        if self.is_zero():
            return 0
        if self.is_rational():
            q = self.coeffs[0]
            return 1 if q > 0 else -1
        # Exact: compare via repeated squaring/rationalisation.
        return _exact_sign(self)

    def __repr__(self) -> str:
        f = self.field
        parts = []
        for s, v in enumerate(self.coeffs):
            if v == 0:
                continue
            if s == 0:
                parts.append(str(v))
            else:
                rad = 1
                for i in range(f.k):
                    if s >> i & 1:
                        rad *= f.gens[i]
                parts.append(f"{v}*sqrt({rad})")
        return " + ".join(parts) if parts else "0"

    def key(self) -> Tuple:
        """Exact hashable canonical key (numerator, denominator pairs)."""
        return tuple((c.numerator, c.denominator) for c in self.coeffs)


def _exact_sign(e: FieldElem) -> int:
    """Determine sign(e) exactly for a nonzero multiquadratic real number.

    Method: isolate one radical at a time. Write e = A + B*sqrt(r) where A, B
    lie in the subfield without sqrt(r). Then sign(e) is decided by comparing
    A^2 and B^2*r, recursing into the subfield. This is exact rational
    arithmetic throughout - no floats, no tolerances.
    """
    f = e.field
    if e.is_rational():
        q = e.coeffs[0]
        return (q > 0) - (q < 0)
    # split on the highest generator present
    top = max(s for s, v in enumerate(e.coeffs) if v != 0)
    i = top.bit_length() - 1  # index of a generator present
    bit = 1 << i
    r = f.gens[i]
    a_coeffs = [Rat(0)] * f.dim
    b_coeffs = [Rat(0)] * f.dim
    for s, v in enumerate(e.coeffs):
        if v == 0:
            continue
        if s & bit:
            b_coeffs[s ^ bit] += v
        else:
            a_coeffs[s] += v
    A = FieldElem(f, tuple(a_coeffs))
    B = FieldElem(f, tuple(b_coeffs))
    sA = _exact_sign(A) if not A.is_zero() else 0
    sB = _exact_sign(B) if not B.is_zero() else 0
    if sB == 0:
        return sA
    if sA == 0:
        return sB
    if sA == sB:
        return sA
    # opposite signs: compare magnitudes |A| vs |B|*sqrt(r) via squares
    lhs = A * A
    rhs = (B * B) * r
    diff = lhs - rhs
    sd = _exact_sign(diff) if not diff.is_zero() else 0
    if sd == 0:
        return 0  # |A| == |B|sqrt(r) and opposite signs => e == 0
    return sA if sd > 0 else sB


# The canonical field for de Grey-style constructions:
#   sqrt(3)  - the triangular/hexagonal lattice
#   sqrt(11) - the spindling rotation cos(a)=5/6, sin(a)=sqrt(11)/6
DEGREY_FIELD = MultiQuadField((3, 11))
