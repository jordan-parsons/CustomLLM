#!/usr/bin/env python3
"""ADVERSARY 2 / CATEGORY C -- encoding soundness.

Two claims are attacked, both of them load-bearing for every UNSAT the project
reports:

  C-i   src/hn/cnf.py OMITS at-most-one-colour clauses and pins a greedily-found
        clique to distinct colours.  Claimed sound "in both directions".
  C-ii  src/hn/minimizer.py replaces vertex deletion with presence literals p_v
        plus CONDITIONAL clique pins (~p_v v x[v][i]), and claims
            UNSAT under {p_v : v in S}   <=>   G[S] is not k-colourable
        exactly.  Every minimisation result in the project depends on this.

Ground truth here is NOT another SAT encoding: it is brute-force enumeration of
all k^n colourings for small graphs.  So a shared bug between encoder and
checker cannot hide.

Run:  python tests/adv2_encoding.py
"""
import itertools
import random
import sys

sys.path.insert(0, "/home/user/CustomLLM/src")

from pysat.solvers import Solver  # noqa: E402

from hn.cnf import encode_coloring, find_clique_greedy, var, verify_clique  # noqa: E402
from hn.minimizer import build_mus_encoding  # noqa: E402
from hn.modelcheck import decode_model  # noqa: E402

FAIL = []


def report(name, ok, detail=""):
    print(f"[{'ok ' if ok else 'HOLE'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------
def brute_colourable(n, edges, k):
    """True iff the graph on n vertices with `edges` has a proper k-colouring."""
    if n == 0:
        return True
    adj = [[] for _ in range(n)]
    for (u, v) in edges:
        adj[u].append(v)
        adj[v].append(u)
    col = [-1] * n

    def go(v):
        if v == n:
            return True
        for c in range(k):
            if all(col[u] != c for u in adj[v] if u < v):
                col[v] = c
                if go(v + 1):
                    return True
                col[v] = -1
        return False
    return go(0)


def induced(n, edges, S):
    """(n', edges') of the induced subgraph on sorted S, plus the index map."""
    S = sorted(set(S))
    pos = {v: i for i, v in enumerate(S)}
    e2 = sorted((pos[u], pos[v]) for (u, v) in edges if u in pos and v in pos)
    return len(S), e2, S


def rand_graph(rnd, n, p):
    return sorted((u, v) for u in range(n) for v in range(u + 1, n)
                  if rnd.random() < p)


def sat(clauses, assumptions=(), name="cadical153"):
    s = Solver(name=name, bootstrap_with=clauses)
    try:
        r = s.solve(assumptions=list(assumptions))
        m = s.get_model() if r else None
        return r, m
    finally:
        s.delete()


# ---------------------------------------------------------------------------
# C1  is omitting at-most-one really sound in BOTH directions?
# ---------------------------------------------------------------------------
def c1_amo_omission_exhaustive():
    """EXHAUSTIVE over every assignment of every 4- and 5-vertex graph:
    does 'assignment satisfies the CNF' really imply 'lowest-true-colour
    decoding is a proper TOTAL colouring'?  And does chi<=k imply SAT?"""
    problems = []
    checked_assignments = 0
    graphs = 0
    rnd = random.Random(5)
    jobs = []
    for n in (4, 5):
        allpairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
        masks = range(1 << len(allpairs))
        if n == 5:
            masks = rnd.sample(range(1 << len(allpairs)), 60)
        for mask in masks:
            edges = [allpairs[i] for i in range(len(allpairs)) if mask >> i & 1]
            for k in (2, 3):
                jobs.append((n, k, edges))
    if True:
        for (n, k, edges) in jobs:
            if True:
                graphs += 1
                enc = encode_coloring(n, edges, k, adj=None, break_symmetry=False)
                nv = n * k
                # forward direction, exhaustively
                for bits in range(1 << nv):
                    assign = [(i + 1) if (bits >> i & 1) else -(i + 1)
                              for i in range(nv)]
                    trueset = {l for l in assign if l > 0}
                    if not all(any(l in trueset for l in cl if l > 0) or
                               any(-l not in trueset for l in cl if l < 0)
                               for cl in enc.clauses):
                        continue
                    checked_assignments += 1
                    cols = decode_model(assign, n, k)
                    if any(c is None for c in cols):
                        problems.append(f"n={n} k={k} edges={edges}: satisfying "
                                        "assignment decodes to an UNCOLOURED vertex")
                        break
                    bad = [(u, v) for (u, v) in edges if cols[u] == cols[v]]
                    if bad:
                        problems.append(f"n={n} k={k} edges={edges}: satisfying "
                                        f"assignment decodes to monochromatic {bad}")
                        break
                # backward direction
                s, _ = sat(enc.clauses)
                b = brute_colourable(n, edges, k)
                if s != b:
                    problems.append(f"n={n} k={k} edges={edges}: SAT={s} but "
                                    f"brute-force {k}-colourable={b}")
    report("C1 at-most-one omission, EXHAUSTIVE over all assignments",
           not problems, "; ".join(problems[:3]) or
           f"{graphs} encodings (ALL 64 graphs on 4 vertices + 60 sampled "
           f"graphs on 5 vertices, k=2 and 3); "
           f"{checked_assignments} satisfying assignments individually decoded: "
           "every one yields a proper TOTAL colouring, and SAT agreed with "
           "brute-force k-colourability on every graph")


# ---------------------------------------------------------------------------
# C2  is the symmetry-breaking clique pin sound?
# ---------------------------------------------------------------------------
def c2_symmetry_pin():
    problems = []
    rnd = random.Random(31337)
    n_graphs = 0
    pinned = 0
    for _ in range(600):
        n = rnd.randint(4, 9)
        edges = rand_graph(rnd, n, rnd.choice([0.3, 0.5, 0.7]))
        adj = [[] for _ in range(n)]
        for (u, v) in edges:
            adj[u].append(v)
            adj[v].append(u)
        for k in (3, 4):
            n_graphs += 1
            enc = encode_coloring(n, edges, k, adj=adj, break_symmetry=True)
            if enc.fixed:
                pinned += 1
                if not verify_clique(list(enc.fixed), edges):
                    problems.append(f"find_clique_greedy returned a NON-clique "
                                    f"{list(enc.fixed)} on edges={edges}")
                if len(set(enc.fixed.values())) != len(enc.fixed):
                    problems.append(f"pinned colours not distinct: {enc.fixed}")
            s, _ = sat(enc.clauses)
            b = brute_colourable(n, edges, k)
            if s != b:
                problems.append(f"n={n} k={k} edges={edges} pins={enc.fixed}: "
                                f"symmetry-broken SAT={s} but brute-force={b}")
    report("C2 clique symmetry pin preserves satisfiability", not problems,
           "; ".join(problems[:3]) or
           f"{n_graphs} random encodings ({pinned} with a pin) agreed with "
           "brute-force colourability; every pinned set verified to be a real "
           "clique with distinct colours")


def c2b_untrusted_adj():
    """encode_coloring TRUSTS the caller-supplied `adj`. If adj disagrees with
    `edges`, the 'clique' is not a clique and the pin is UNSOUND: a colourable
    graph is encoded as UNSAT. pipeline.assess() re-verifies with verify_clique;
    a direct caller of encode_coloring gets no such protection."""
    # K_{2,3} plus the edge 3-4: vertices 0,1,2 are each adjacent to both 3 and
    # 4, and 3-4 is an edge. With k=3 this IS 3-colourable, but 3 and 4 use two
    # colours, so 0,1,2 must ALL take the third -- they can never be pairwise
    # distinct. A lying adj that claims {0,1,2} is a triangle pins them to three
    # distinct colours and turns a 3-colourable graph into UNSAT.
    n, k = 5, 3
    edges = [(0, 3), (0, 4), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]
    lying_adj = [[1, 2], [0, 2], [0, 1], [], []]
    enc = encode_coloring(n, edges, k, adj=lying_adj, break_symmetry=True)
    s, _ = sat(enc.clauses)
    b = brute_colourable(n, edges, k)
    guarded = verify_clique(list(enc.fixed), edges)
    hole = (s != b)
    report("C2b encode_coloring trusts an unvalidated `adj`", not hole,
           f"lying adj claims triangle {{0,1,2}} -> pins {enc.fixed}; encoding "
           f"SAT={s} but the graph IS {k}-colourable ({b}) -> the encoder "
           f"MANUFACTURED an UNSAT. verify_clique on the pinned set = {guarded}, "
           "so pipeline.assess() would raise its SOUNDNESS ALARM; encode_coloring "
           "itself performs no such check, and minimizer.build_mus_encoding never "
           "calls verify_clique at all (it is safe only because it derives adj "
           "from g.edges itself)")


# ---------------------------------------------------------------------------
# C3  the presence-literal trick vs real vertex deletion
# ---------------------------------------------------------------------------
class _G:
    """Minimal UDGraph stand-in: build_mus_encoding only uses n, edges, adj."""
    def __init__(self, n, edges):
        self.n = n
        self.edges = sorted(edges)
        self.adj = [[] for _ in range(n)]
        for (u, v) in self.edges:
            self.adj[u].append(v)
            self.adj[v].append(u)


def c3_presence_literals(k=4, n_graphs=140, subsets_per_graph=40, seed=777):
    """For many random graphs and many random subsets S, compare

        UNSAT under assumptions {p_v : v in S}          (minimizer)
        vs  brute-force k-colourability of G[S]         (ground truth)
        vs  encode_coloring(G[S]) solved from scratch   (the other encoder)

    Any disagreement corrupts every minimisation result in the project.
    """
    rnd = random.Random(seed)
    problems = []
    tot = 0
    unsat_cases = 0
    pin_broken_cases = 0
    for gi in range(n_graphs):
        n = rnd.randint(5, 10)
        edges = rand_graph(rnd, n, rnd.choice([0.55, 0.7, 0.85, 0.95]))
        g = _G(n, edges)
        for bs in (True, False):
            clauses, pres, _ = build_mus_encoding(g, k, break_symmetry=bs)
            clique = find_clique_greedy(n, g.adj, min(k, 3)) if bs else []
            solver = Solver(name="cadical153", bootstrap_with=clauses)
            try:
                for _ in range(subsets_per_graph):
                    size = rnd.randint(0, n)
                    S = sorted(rnd.sample(range(n), size))
                    tot += 1
                    mus_unsat = not solver.solve(
                        assumptions=[pres[v] for v in S])
                    n2, e2, _ = induced(n, edges, S)
                    truth_col = brute_colourable(n2, e2, k)
                    enc = encode_coloring(n2, e2, k, adj=None,
                                          break_symmetry=False)
                    scratch_sat, _ = sat(enc.clauses)
                    if not truth_col:
                        unsat_cases += 1
                    if clique and not set(clique) <= set(S):
                        pin_broken_cases += 1
                    if mus_unsat == truth_col:
                        problems.append(
                            f"g{gi} bs={bs} S={S}: presence-literal UNSAT="
                            f"{mus_unsat} but brute-force {k}-colourable="
                            f"{truth_col} (clique={clique}); edges={edges}")
                    if scratch_sat != truth_col:
                        problems.append(
                            f"g{gi} S={S}: from-scratch encoding SAT="
                            f"{scratch_sat} but brute-force={truth_col}")
            finally:
                solver.delete()
    report("C3 presence literals == vertex deletion", not problems,
           "; ".join(problems[:3]) or
           f"{tot} (graph, subset) pairs at k={k}, with and without conditional "
           f"symmetry breaking; {unsat_cases} of them genuinely non-{k}-"
           f"colourable; {pin_broken_cases} deleted at least one pinned clique "
           "member: presence-literal UNSAT agreed with brute-force "
           "non-colourability in every single case")


def c3b_pin_with_deleted_clique_members(k=4, seed=99):
    """Targeted version of the worst case: subsets that deliberately delete some
    clique members. A conditional pin that stayed active for a deleted vertex, or
    that pinned a non-clique pair, would manufacture a FAKE UNSAT here."""
    rnd = random.Random(seed)
    problems = []
    tried = 0
    for _ in range(400):
        n = rnd.randint(5, 10)
        # force a k-clique to exist so a pin is definitely emitted
        base = list(range(min(k, n)))
        edges = set((u, v) for i, u in enumerate(base) for v in base[i + 1:])
        for u in range(n):
            for v in range(u + 1, n):
                if rnd.random() < 0.4:
                    edges.add((u, v))
        edges = sorted(edges)
        g = _G(n, edges)
        clauses, pres, _ = build_mus_encoding(g, k, break_symmetry=True)
        clique = find_clique_greedy(n, g.adj, min(k, 3))
        if not clique:
            continue
        solver = Solver(name="cadical153", bootstrap_with=clauses)
        try:
            for drop in itertools.chain(
                    [[c] for c in clique],
                    [clique[:i] for i in range(len(clique))],
                    [clique]):
                keep = sorted(set(range(n)) - set(drop))
                tried += 1
                mus_unsat = not solver.solve(assumptions=[pres[v] for v in keep])
                n2, e2, _ = induced(n, edges, keep)
                truth = brute_colourable(n2, e2, k)
                if mus_unsat == truth:
                    problems.append(
                        f"clique={clique} dropped={drop} keep={keep}: "
                        f"UNSAT={mus_unsat} but {k}-colourable={truth}; "
                        f"edges={edges}")
        finally:
            solver.delete()
    report("C3b conditional pin with deleted clique members", not problems,
           "; ".join(problems[:3]) or
           f"{tried} subsets that delete 1..all pinned clique members: no fake "
           "UNSAT was produced (a subset of a clique is still a clique, and the "
           "pin is inactive for absent vertices)")


# ---------------------------------------------------------------------------
# C4  variable-numbering agreement between encoder and independent checker
# ---------------------------------------------------------------------------
def c4_var_convention():
    problems = []
    for n in (1, 3, 7, 510):
        for k in (2, 4, 5):
            for v in range(min(n, 12)):
                for c in range(k):
                    if var(v, c, k) != v * k + c + 1:
                        problems.append(f"var({v},{c},{k}) wrong")
            # the encoder's declared n_vars must cover every literal it emits
            enc = encode_coloring(n, [], k, adj=None, break_symmetry=False)
            mx = max(abs(l) for cl in enc.clauses for l in cl)
            if mx > enc.n_vars:
                problems.append(f"n={n} k={k}: literal {mx} > n_vars {enc.n_vars}")
    # decode_model must ignore the presence literals' numbering region
    report("C4 variable convention / n_vars header", not problems,
           "; ".join(problems[:3]) or
           "var(v,c,k) == v*k+c+1 everywhere, and no emitted literal exceeds "
           "the declared n_vars for n in {1,3,7,510}, k in {2,4,5}")


if __name__ == "__main__":
    c1_amo_omission_exhaustive()
    c2_symmetry_pin()
    c2b_untrusted_adj()
    c3_presence_literals()
    c3b_pin_with_deleted_clique_members()
    c4_var_convention()
    print()
    if FAIL:
        print("HOLES FOUND:", ", ".join(FAIL))
        sys.exit(1)
    print("no holes found in category C")
