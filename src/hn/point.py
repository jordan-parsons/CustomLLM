"""Exact planar points over a multiquadratic field, plus exact rigid motions."""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable, List, Tuple

from .field import FieldElem, MultiQuadField, Rat


class Point:
    """A point of the plane with exact coordinates in a MultiQuadField."""

    __slots__ = ("x", "y", "_hash")

    def __init__(self, x: FieldElem, y: FieldElem):
        if x.field != y.field:
            raise TypeError("coordinates live in different fields")
        self.x = x
        self.y = y
        self._hash = None

    @property
    def field(self) -> MultiQuadField:
        return self.x.field

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def __neg__(self) -> "Point":
        return Point(-self.x, -self.y)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self.x, self.y))
        return self._hash

    def key(self) -> Tuple:
        """Exact canonical hashable key. Used for dedup and content addressing."""
        return (self.x.key(), self.y.key())

    def sqdist(self, other: "Point") -> FieldElem:
        """Exact squared distance. Never takes a square root."""
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def is_unit_from(self, other: "Point") -> bool:
        """EXACT unit-distance predicate. The single most important test here."""
        return self.sqdist(other).equals_rational(1)

    def approx(self) -> Tuple[float, float]:
        """FILTER ONLY. Never used to decide an edge."""
        return (self.x.approx(), self.y.approx())

    def __repr__(self) -> str:
        return f"Point({self.x!r}, {self.y!r})"


class Rotation:
    """Exact rotation by an angle whose cosine and sine lie in the field."""

    __slots__ = ("cos", "sin", "field")

    def __init__(self, cos: FieldElem, sin: FieldElem):
        if cos.field != sin.field:
            raise TypeError("field mismatch")
        # Verify exactly that cos^2 + sin^2 == 1. A rotation that fails this is
        # not an isometry and would silently corrupt every distance downstream.
        chk = cos * cos + sin * sin
        if not chk.equals_rational(1):
            raise ValueError(
                f"not a rotation: cos^2+sin^2 = {chk!r}, expected exactly 1"
            )
        self.cos = cos
        self.sin = sin
        self.field = cos.field

    @staticmethod
    def from_cos_sin(field: MultiQuadField, cos, sin) -> "Rotation":
        c = cos if isinstance(cos, FieldElem) else field.rational(cos)
        s = sin if isinstance(sin, FieldElem) else field.rational(sin)
        return Rotation(c, s)

    @staticmethod
    def by_degrees_60k(field: MultiQuadField, k: int) -> "Rotation":
        """Rotation by k*60 degrees; exact, needs sqrt(3) in the field."""
        half = field.rational(Rat(1, 2))
        r3 = field.sqrt_gen(3)
        h3 = r3 * Rat(1, 2)
        table = {
            0: (field.one(), field.zero()),
            1: (half, h3),
            2: (-half, h3),
            3: (-field.one(), field.zero()),
            4: (-half, -h3),
            5: (half, -h3),
        }
        c, s = table[k % 6]
        return Rotation(c, s)

    def apply(self, p: Point, center: Point | None = None) -> Point:
        if center is not None:
            p = p - center
        x = self.cos * p.x - self.sin * p.y
        y = self.sin * p.x + self.cos * p.y
        q = Point(x, y)
        if center is not None:
            q = q + center
        return q

    def inverse(self) -> "Rotation":
        return Rotation(self.cos, -self.sin)

    def compose(self, other: "Rotation") -> "Rotation":
        c = self.cos * other.cos - self.sin * other.sin
        s = self.sin * other.cos + self.cos * other.sin
        return Rotation(c, s)


def spindle_rotation(field: MultiQuadField) -> Rotation:
    """The Moser-spindle rotation: cos = 5/6, sin = sqrt(11)/6.

    Rationale (exact): two points at distance sqrt(3) from a common centre and
    separated by angle a are at distance 1 iff 2*3*(1 - cos a) = 1, i.e.
    cos a = 5/6. Then sin^2 a = 1 - 25/36 = 11/36, so sin a = sqrt(11)/6.
    """
    c = field.rational(Rat(5, 6))
    s = field.sqrt_gen(11) * Rat(1, 6)
    return Rotation(c, s)


def dedup_points(points: Iterable[Point]) -> List[Point]:
    """Exact deduplication by canonical key, order-preserving."""
    seen = set()
    out = []
    for p in points:
        k = p.key()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def minkowski_sum(A: Iterable[Point], B: Iterable[Point]) -> List[Point]:
    """Exact Minkowski sum with deduplication."""
    return dedup_points(a + b for a in A for b in B)
