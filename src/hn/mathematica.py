"""Parse published Mathematica-format exact coordinates into field elements.

Input lines look like:

    {0, 0}
    {-1/2, Sqrt[3]/2}
    {1/6, -1/(2*Sqrt[3])}
    {(-21 - 3*Sqrt[5] + 7*Sqrt[33] - 3*Sqrt[165])/96, (7*Sqrt[3] + ...)/96}
    {(Sqrt[11/3]*(7 - 3*Sqrt[5]))/16, (Sqrt[11]*(7 + Sqrt[5]))/16}

Parsing is done via Python's `ast` on a lightly rewritten string, then evaluated
by an explicit recursive evaluator over exact values only. Integer literals
become Fractions, so `1/2` can never become a float. There is no `eval` of
arithmetic on Python numbers anywhere in this path.

Radicals are reduced exactly: Sqrt[n] with n = s^2 * d gives s * sqrt(d), and d
must be a product of distinct field generators or the parse fails loudly.
Sqrt[p/q] is normalised to sqrt(p*q)/q.
"""

from __future__ import annotations

import ast
import re
from fractions import Fraction as F
from typing import List, Tuple, Union

from .field import FieldElem, MultiQuadField
from .point import Point

Value = Union[F, FieldElem]


def _sqrt_int(field: MultiQuadField, n: int) -> Value:
    """Exact sqrt of a positive integer inside the field."""
    if n <= 0:
        raise ValueError(f"Sqrt of non-positive integer {n}")
    # extract the largest square factor
    s = 1
    d = n
    p = 2
    while p * p <= d:
        while d % (p * p) == 0:
            d //= p * p
            s *= p
        p += 1
    if d == 1:
        return F(s)
    return field.sqrt_gen(d) * F(s)


def _sqrt_value(field: MultiQuadField, q: F) -> Value:
    """Exact sqrt of a positive rational: sqrt(a/b) = sqrt(a*b)/b."""
    if q <= 0:
        raise ValueError(f"Sqrt of non-positive rational {q}")
    a, b = q.numerator, q.denominator
    return _mul(field, _sqrt_int(field, a * b), F(1, b))


def _lift(field: MultiQuadField, v: Value) -> FieldElem:
    return field.rational(v) if isinstance(v, F) else v


def _add(field, a: Value, b: Value) -> Value:
    if isinstance(a, F) and isinstance(b, F):
        return a + b
    return _lift(field, a) + _lift(field, b)


def _mul(field, a: Value, b: Value) -> Value:
    if isinstance(a, F) and isinstance(b, F):
        return a * b
    if isinstance(a, F):
        return b * a
    if isinstance(b, F):
        return a * b
    return a * b


def _div(field, a: Value, b: Value) -> Value:
    if isinstance(b, F):
        if b == 0:
            raise ZeroDivisionError
        if isinstance(a, F):
            return a / b
        return a * (F(1) / b)
    return _lift(field, a) / b


def _pow(field, a: Value, e: int) -> Value:
    if e < 0:
        return _div(field, F(1), _pow(field, a, -e))
    out: Value = F(1)
    for _ in range(e):
        out = _mul(field, out, a)
    return out


def _eval(node: ast.AST, field: MultiQuadField) -> Value:
    if isinstance(node, ast.Expression):
        return _eval(node.body, field)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return F(node.value)
        raise ValueError(f"non-integer literal {node.value!r} in exact coordinate")
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand, field)
        if isinstance(node.op, ast.USub):
            return _mul(field, v, F(-1))
        if isinstance(node.op, ast.UAdd):
            return v
        raise ValueError(f"unsupported unary op {node.op}")
    if isinstance(node, ast.BinOp):
        a = _eval(node.left, field)
        b = _eval(node.right, field)
        if isinstance(node.op, ast.Add):
            return _add(field, a, b)
        if isinstance(node.op, ast.Sub):
            return _add(field, a, _mul(field, b, F(-1)))
        if isinstance(node.op, ast.Mult):
            return _mul(field, a, b)
        if isinstance(node.op, ast.Div):
            return _div(field, a, b)
        if isinstance(node.op, ast.Pow):
            if not isinstance(b, F) or b.denominator != 1:
                raise ValueError("non-integer exponent")
            return _pow(field, a, int(b))
        raise ValueError(f"unsupported binary op {node.op}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id != "SQ":
            raise ValueError("only Sqrt[] calls are permitted")
        arg = _eval(node.args[0], field)
        if not isinstance(arg, F):
            raise ValueError("Sqrt of a non-rational argument is not supported")
        return _sqrt_value(field, arg)
    raise ValueError(f"unsupported node {type(node).__name__}")


def parse_expr(text: str, field: MultiQuadField) -> FieldElem:
    """Parse one Mathematica scalar expression into an exact field element."""
    s = text.strip()
    # Sqrt[...] -> SQ(...)
    s = re.sub(r"Sqrt\s*\[", "SQ(", s)
    # close the bracket that Sqrt opened: rewrite ']' to ')'
    s = s.replace("]", ")")
    if "[" in s:
        raise ValueError(f"unhandled bracket in {text!r}")
    tree = ast.parse(s, mode="eval")
    return _lift(field, _eval(tree, field))


def split_pair(line: str) -> Tuple[str, str]:
    """Split '{x, y}' on the top-level comma, respecting nesting."""
    s = line.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise ValueError(f"not a brace pair: {line!r}")
    inner = s[1:-1]
    depth = 0
    for i, ch in enumerate(inner):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            return inner[:i], inner[i + 1 :]
    raise ValueError(f"no top-level comma in {line!r}")


def radicals_in(text: str) -> List[int]:
    """All squarefree radicands appearing, so the right field can be chosen."""
    out = set()
    for m in re.finditer(r"Sqrt\s*\[\s*([0-9]+)(?:\s*/\s*([0-9]+))?\s*\]", text):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else 1
        n = a * b
        d = n
        p = 2
        while p * p <= d:
            while d % (p * p) == 0:
                d //= p * p
            p += 1
        for q in _prime_factors(d):
            out.add(q)
    return sorted(out)


def _prime_factors(n: int) -> List[int]:
    out = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def load_vtx(path: str, field: MultiQuadField | None = None) -> Tuple[List[Point], MultiQuadField]:
    """Load a .vtx file of exact Mathematica coordinates."""
    with open(path) as fh:
        text = fh.read()
    lines = [l for l in (x.strip() for x in text.splitlines()) if l]
    if field is None:
        gens = radicals_in(text)
        if not gens:
            gens = [3]
        field = MultiQuadField(tuple(gens))
    pts = []
    for i, line in enumerate(lines):
        try:
            xs, ys = split_pair(line)
            pts.append(Point(parse_expr(xs, field), parse_expr(ys, field)))
        except Exception as e:
            raise ValueError(f"{path}:{i+1}: {e} in {line!r}") from e
    return pts, field


def load_edge_file(path: str) -> Tuple[int, List[Tuple[int, int]]]:
    """Load a DIMACS-ish '.edge' file ('p edge n m' then 'e u v', 1-indexed)."""
    n = 0
    edges = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                parts = line.split()
                n = int(parts[2])
            elif line.startswith("e"):
                _, u, v = line.split()
                a, b = int(u) - 1, int(v) - 1
                edges.append((min(a, b), max(a, b)))
    return n, sorted(set(edges))
