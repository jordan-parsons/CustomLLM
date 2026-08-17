#!/usr/bin/env python3
"""ADVERSARY 3 - CHECK B.

For each of Heule's graphs: rebuild the edge set from HIS exact .vtx coordinates
using OUR exact multiquadratic arithmetic (brute force O(n^2), no float in the
decision), rebuild the CNF with OUR encoder, and compare semantically against
HIS published cnf/*-4.cnf and edge/*.edge.

Nothing here uses floating point to decide anything. The grid detector is also
run purely to check it agrees with the O(n^2) exact reference.

Output: artifacts/adv3/checkB.json + human-readable stdout.
"""
import json
import os
import sys
from fractions import Fraction as Fr

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.mathematica import load_vtx, load_edge_file  # noqa: E402
from hn.detect import detect_edges, detect_edges_bruteforce_exact  # noqa: E402
from hn.cnf import encode_coloring, var  # noqa: E402

ROOT = "/home/user/CustomLLM/data/CNP-SAT"
OUT = "/home/user/CustomLLM/artifacts/adv3"
NAMES = [517, 529, 553, 610, 633, 803, 826, 874]
K = 4


def parse_dimacs(path):
    """Return (nvars, header_nclauses, list_of_clauses(sorted tuples))."""
    nvars = None
    nhdr = None
    clauses = []
    cur = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0] == "c":
                continue
            if line[0] == "p":
                _, _, nv, nc = line.split()
                nvars, nhdr = int(nv), int(nc)
                continue
            for tok in line.split():
                x = int(tok)
                if x == 0:
                    clauses.append(tuple(sorted(cur)))
                    cur = []
                else:
                    cur.append(x)
    if cur:
        raise ValueError(f"{path}: trailing literals without terminating 0")
    return nvars, nhdr, clauses


def edges_from_cnf(clauses, k=K):
    """Recover the implied edge set from binary all-negative clauses.

    var(v,c) = v*k + c + 1, so v = (|lit|-1)//k, c = (|lit|-1)%k.
    An edge (u,v) must appear as {-var(u,c), -var(v,c)} for every c in [0,k).
    """
    from collections import defaultdict

    byc = defaultdict(set)
    other = []
    for cl in clauses:
        if len(cl) == 2 and cl[0] < 0 and cl[1] < 0:
            a, b = -cl[0], -cl[1]
            ua, ca = (a - 1) // k, (a - 1) % k
            ub, cb = (b - 1) // k, (b - 1) % k
            if ca != cb:
                other.append(cl)  # binary negative but not a same-colour pair
                continue
            if ua == ub:
                other.append(cl)  # at-most-one-colour clause, not an edge
                continue
            byc[ca].add((min(ua, ub), max(ua, ub)))
        else:
            other.append(cl)
    return byc, other


def amo_clauses_in(clauses, k=K):
    """Count at-most-one-colour clauses {-var(v,c1), -var(v,c2)}, c1!=c2."""
    out = set()
    for cl in clauses:
        if len(cl) == 2 and cl[0] < 0 and cl[1] < 0:
            a, b = -cl[0], -cl[1]
            if (a - 1) // k == (b - 1) // k and (a - 1) % k != (b - 1) % k:
                out.add(cl)
    return out


def alo_clauses_in(clauses, n, k=K):
    out = {}
    for cl in clauses:
        if len(cl) == k and all(x > 0 for x in cl):
            vs = {(x - 1) // k for x in cl}
            cs = {(x - 1) % k for x in cl}
            if len(vs) == 1 and cs == set(range(k)):
                out[vs.pop()] = cl
    return out


def sqd_str(pi, pj):
    """Exact squared distance rendered as text (never a float)."""
    d = pi.sqdist(pj)
    return repr(d)


def main():
    report = {}
    alarms = []
    for name in NAMES:
        print("=" * 72)
        print("GRAPH", name)
        vtx = f"{ROOT}/vtx/{name}.vtx"
        pts, field = load_vtx(vtx)
        n = len(pts)
        rec = {"vtx": vtx, "n_vtx_lines": n, "field": list(field.gens)}
        print(f"  vtx lines = {n}, field = {field}")
        assert n == name, f"vtx line count {n} != name {name}"

        # exact dedup
        keys = {p.key() for p in pts}
        rec["distinct_points"] = len(keys)
        if len(keys) != n:
            alarms.append(f"{name}: vtx has {n-len(keys)} exact duplicate points")
        print(f"  distinct exact points = {len(keys)}")

        # OUR edge set: O(n^2) exact reference
        E_exact = set(detect_edges_bruteforce_exact(pts))
        E_grid = set(detect_edges(pts))
        rec["our_edges_exact_bruteforce"] = len(E_exact)
        rec["our_edges_grid_detector"] = len(E_grid)
        rec["grid_vs_bruteforce_agree"] = E_exact == E_grid
        print(f"  our exact edges (brute force O(n^2)) = {len(E_exact)}")
        print(f"  our grid-prefilter detector          = {len(E_grid)}  agree={E_exact == E_grid}")
        if E_exact != E_grid:
            miss = sorted(E_exact - E_grid)
            extra = sorted(E_grid - E_exact)
            rec["grid_missed"] = miss[:20]
            rec["grid_extra"] = extra[:20]
            alarms.append(
                f"{name}: grid detector disagrees with exact brute force: "
                f"{len(miss)} missed, {len(extra)} spurious"
            )

        # THEIR .edge file
        ef = f"{ROOT}/edge/{name}.edge"
        if os.path.exists(ef):
            en, E_theirs = load_edge_file(ef)
            E_theirs = set(E_theirs)
            rec["their_edge_file_n"] = en
            rec["their_edge_file_m"] = len(E_theirs)
            same = E_theirs == E_exact
            rec["edge_file_matches_our_exact"] = same
            print(f"  their edge/{name}.edge: n={en} m={len(E_theirs)}  match_our_exact={same}")
            if not same:
                bad_theirs = sorted(E_theirs - E_exact)
                miss = sorted(E_exact - E_theirs)
                rec["edge_file_not_unit"] = [
                    {"u": u + 1, "v": v + 1, "sqdist": sqd_str(pts[u], pts[v])}
                    for u, v in bad_theirs[:40]
                ]
                rec["edge_file_missing_unit_pairs"] = [
                    {"u": u + 1, "v": v + 1} for u, v in miss[:40]
                ]
                if bad_theirs:
                    alarms.append(
                        f"SOUNDNESS ALARM {name}: edge/{name}.edge asserts "
                        f"{len(bad_theirs)} pair(s) that are NOT exactly unit "
                        f"distance, e.g. {bad_theirs[:3]}"
                    )
                if miss:
                    alarms.append(
                        f"{name}: edge/{name}.edge OMITS {len(miss)} exactly-unit "
                        f"pairs, e.g. {miss[:3]} (under-reporting edges is "
                        f"conservative for a colouring LOWER bound only if the "
                        f"graph is still shown non-4-colourable)"
                    )

        # THEIR plain cnf
        cf = f"{ROOT}/cnf/{name}-4.cnf"
        nv, nc_hdr, cls = parse_dimacs(cf)
        cls_set = set(cls)
        rec["their_cnf"] = os.path.basename(cf)
        rec["their_cnf_nvars_header"] = nv
        rec["their_cnf_nclauses_header"] = nc_hdr
        rec["their_cnf_nclauses_actual"] = len(cls)
        rec["their_cnf_distinct_clauses"] = len(cls_set)
        print(f"  their {os.path.basename(cf)}: header p cnf {nv} {nc_hdr}, "
              f"actual {len(cls)} clauses, {len(cls_set)} distinct")
        if nc_hdr != len(cls):
            alarms.append(f"{name}: header claims {nc_hdr} clauses, file has {len(cls)}")
        if nv != n * K:
            alarms.append(f"{name}: their CNF has {nv} vars, expected {n*K}")

        byc, other = edges_from_cnf(cls)
        percolor = {c: len(s) for c, s in byc.items()}
        rec["their_cnf_edge_clauses_per_colour"] = percolor
        allsame = len(set(map(tuple, (sorted(s) for s in byc.values())))) <= 1
        rec["their_cnf_edge_sets_identical_across_colours"] = allsame
        E_cnf = set().union(*byc.values()) if byc else set()
        rec["their_cnf_implied_edges"] = len(E_cnf)
        print(f"  their CNF implies {len(E_cnf)} edges; per-colour counts {percolor}; "
              f"identical across colours = {allsame}")
        if not allsame:
            alarms.append(f"{name}: their CNF edge clauses differ between colours")

        amo = amo_clauses_in(cls)
        alo = alo_clauses_in(cls, n)
        rec["their_cnf_amo_clauses"] = len(amo)
        rec["their_cnf_alo_clauses"] = len(alo)
        print(f"  their CNF: {len(alo)} ALO clauses, {len(amo)} AMO clauses")

        # THE CENTRAL COMPARISON: their CNF's edges vs our exact edges
        same_cnf_edges = E_cnf == E_exact
        rec["their_cnf_edges_match_our_exact"] = same_cnf_edges
        print(f"  *** their CNF edge set == our exact edge set : {same_cnf_edges}")
        if not same_cnf_edges:
            bad = sorted(E_cnf - E_exact)
            miss = sorted(E_exact - E_cnf)
            rec["cnf_edges_not_unit"] = [
                {"u1": u + 1, "v1": v + 1, "sqdist": sqd_str(pts[u], pts[v])}
                for u, v in bad[:40]
            ]
            rec["cnf_edges_missing"] = [{"u1": u + 1, "v1": v + 1} for u, v in miss[:40]]
            if bad:
                alarms.append(
                    f"SOUNDNESS ALARM {name}: {len(bad)} edge(s) in their CNF are "
                    f"NOT exactly unit distance: " +
                    "; ".join(f"({u+1},{v+1}) d^2={sqd_str(pts[u],pts[v])}" for u, v in bad[:3])
                )
            if miss:
                alarms.append(
                    f"{name}: their CNF omits {len(miss)} exactly-unit pairs, "
                    f"e.g. {[(u+1,v+1) for u,v in miss[:3]]}"
                )

        # OUR CNF from OUR exact edges, plain (no symmetry breaking)
        enc = encode_coloring(n, sorted(E_exact), K, adj=None, break_symmetry=False)
        our_set = set(tuple(sorted(cl)) for cl in enc.clauses)
        rec["our_cnf_nvars"] = enc.n_vars
        rec["our_cnf_nclauses"] = len(enc.clauses)
        rec["our_cnf_distinct_clauses"] = len(our_set)
        ident = our_set == cls_set
        rec["clause_sets_identical"] = ident
        print(f"  our CNF: p cnf {enc.n_vars} {len(enc.clauses)} ({len(our_set)} distinct)")
        print(f"  *** clause SET identical to theirs : {ident}")
        if not ident:
            only_ours = our_set - cls_set
            only_theirs = cls_set - our_set
            rec["clauses_only_ours"] = len(only_ours)
            rec["clauses_only_theirs"] = len(only_theirs)
            # characterise
            def classify(cs):
                from collections import Counter
                cnt = Counter()
                for cl in cs:
                    if len(cl) == K and all(x > 0 for x in cl):
                        cnt["ALO"] += 1
                    elif len(cl) == 2 and cl[0] < 0 and cl[1] < 0:
                        a, b = -cl[0], -cl[1]
                        if (a - 1) // K == (b - 1) // K:
                            cnt["AMO(same vertex)"] += 1
                        elif (a - 1) % K == (b - 1) % K:
                            cnt["edge"] += 1
                        else:
                            cnt["binary-neg-other"] += 1
                    elif len(cl) == 1:
                        cnt["unit"] += 1
                    else:
                        cnt["other len=%d" % len(cl)] += 1
                return dict(cnt)
            rec["clauses_only_ours_kinds"] = classify(only_ours)
            rec["clauses_only_theirs_kinds"] = classify(only_theirs)
            print(f"      only in ours   ({len(only_ours)}): {rec['clauses_only_ours_kinds']}")
            print(f"      only in theirs ({len(only_theirs)}): {rec['clauses_only_theirs_kinds']}")

        report[str(name)] = rec

    report["_alarms"] = alarms
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/checkB.json", "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print("=" * 72)
    print("ALARMS:" if alarms else "NO ALARMS")
    for a in alarms:
        print("  !", a)
    print("wrote", f"{OUT}/checkB.json")


if __name__ == "__main__":
    main()
