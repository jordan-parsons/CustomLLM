#!/usr/bin/env python3
"""Promote a search hit to a fully verified claim, or reject it.

Given a pool + a vertex subset, this runs the complete evidence chain required
by the ground rules:

  1. exact coordinates             - reload from the exact pool, no floats
  2. exact edge list              - re-detect with the O(n^2) BRUTE FORCE exact
                                    detector (no prefilter at all), and confirm
                                    it agrees with the indexed detector
  3. CNF                          - written to disk and archived
  4. solver proof                 - kissat with DRAT logging
  5. checker verdict on the proof - drat-trim, recorded with sha256
  6. k=5 SAT + independent model check
  7. catalog row with all of the above

Exit status is nonzero unless every step passes.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/home/user/CustomLLM/src")

from fractions import Fraction

from hn.catalog import connect, record_attempt, register_graph
from hn.detect import (detect_edges, detect_edges_bruteforce_exact,
                       verify_edges_exact)
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.pipeline import assess
from hn.point import Point


def build_published_pool(names=None, gens=(3, 5, 11)):
    names = names or ["510", "517", "529", "553", "610", "633", "803", "826", "874"]
    F = MultiQuadField(tuple(gens))
    allk = {}
    for nm in names:
        pts, _ = load_vtx(f"/home/user/CustomLLM/data/CNP-SAT/vtx/{nm}.vtx", field=F)
        for p in pts:
            allk[p.key()] = p
    return list(allk.values()), F


def verify(points, tag, artifact_dir=None, timeout=7200):
    ad = artifact_dir or f"/home/user/CustomLLM/artifacts/{tag}"
    os.makedirs(ad, exist_ok=True)
    report = {"tag": tag, "n_points": len(points), "steps": {}}
    ok = True

    # 2. exact edges, both detectors
    fast = detect_edges(points)
    slow = detect_edges_bruteforce_exact(points)
    agree = fast == slow
    good, bad = verify_edges_exact(points, slow)
    report["steps"]["exact_edges"] = {
        "indexed_detector_m": len(fast),
        "bruteforce_exact_m": len(slow),
        "detectors_agree": agree,
        "all_edges_exactly_unit": good,
        "bad_edges": bad[:10],
    }
    if not (agree and good):
        ok = False
        print("SOUNDNESS ALARM: detector disagreement or non-unit edge", bad[:10])
        report["ok"] = False
        return report

    g = UDGraph(points, lineage={"op": "verified_candidate", "tag": tag})
    report["n"] = g.n
    report["m"] = g.m
    report["coord_hash"] = g.coord_hash()
    report["graph_hash"] = g.graph_hash()
    report["field"] = list(g.field.gens)

    con = connect()
    register_graph(con, g)

    # 3-5. k=4 with proof + checker
    r4 = assess(g, 4, tag, timeout=timeout)
    record_attempt(con, r4)
    report["steps"]["k4"] = {
        "verdict": r4["verdict"], "checker": r4.get("checker"),
        "checker_verdict": r4.get("checker_verdict"),
        "proof_sha256": r4.get("proof_sha256"), "proof_bytes": r4.get("proof_bytes"),
        "wall": r4.get("wall_seconds"), "cnf": r4.get("cnf_path"),
    }
    if not (r4["verdict"] == "UNSAT" and r4.get("checker_verdict") == "VERIFIED"):
        ok = False

    # 6. k=5 SAT + independent model check
    r5 = assess(g, 5, tag, timeout=timeout)
    record_attempt(con, r5)
    report["steps"]["k5"] = {
        "verdict": r5["verdict"],
        "model_check_ok": (r5.get("model_check") or {}).get("ok"),
        "edges_recomputed": (r5.get("model_check") or {}).get("edges_found_exactly"),
    }
    if r5["verdict"] != "SAT" or not (r5.get("model_check") or {}).get("ok"):
        ok = False

    report["ok"] = ok
    report["chromatic_number_is_5"] = (
        r4["verdict"] == "UNSAT" and r4.get("checker_verdict") == "VERIFIED"
        and r5["verdict"] == "SAT" and (r5.get("model_check") or {}).get("ok")
    )
    with open(os.path.join(ad, "VERIFICATION.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    # exact coordinates archived alongside
    with open(os.path.join(ad, "vertices.json"), "w") as fh:
        json.dump(g.to_dict(), fh)
    return report


def main():
    if len(sys.argv) < 3:
        print("usage: verify_candidate.py <tag> <vertices.json|-> [pool_names_csv]")
        return 2
    tag = sys.argv[1]
    src = sys.argv[2]
    pool, F = build_published_pool(
        sys.argv[3].split(",") if len(sys.argv) > 3 else None
    )
    idx = json.load(sys.stdin if src == "-" else open(src))
    if isinstance(idx, dict):
        idx = idx["vertices"]
    pts = [pool[i] for i in idx]
    rep = verify(pts, tag)
    print(json.dumps({k: v for k, v in rep.items() if k != "steps"}, indent=1))
    print(json.dumps(rep["steps"], indent=1))
    print("VERIFIED 5-CHROMATIC" if rep.get("chromatic_number_is_5") else "NOT VERIFIED")
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
