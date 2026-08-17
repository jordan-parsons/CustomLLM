# ADVERSARY 3 — Third-party proof cross-validation and provenance audit

Scope: (A) verify Marijn Heule's own published DRAT proofs with **our** drat-trim build;
(B) rebuild his CNFs from his exact coordinates with **our** exact-arithmetic pipeline and
compare semantically; (C) provenance and record audit.

Deliberately **not** in scope (other adversaries' lanes): re-encoding the 510 graph with an
independent encoder (Adversary 1), auditing `src/hn/*` for soundness holes (Adversary 2).
Nothing in `reports/ADVERSARY_1.md`, `reports/ADVERSARY_2.md`, `tests/adv1_*`, `tests/adv2_*`
was read or written.

Scripts: `tests/adv3_drat_runs.sh`, `tests/adv3_checker_controls.sh`,
`tests/adv3_cnf_crosscheck.py`, `tests/adv3_provenance_510.py`, `tests/adv3_510_unsat.py`,
`tests/adv3_derived_g2167.py`.
Artifacts: `artifacts/adv3/` (all logs, `drat_results.tsv`, `control_results.tsv`,
`checkB.json`, `prov510.json`).

Upstream under test: `data/CNP-SAT`, a clone of `https://github.com/marijnheule/CNP-SAT.git`
at commit `bb414955a6ef5f49f7df2b245b1e778aa67c068a` ("T721", 2021-09-27). The clone shipped
shallow (`depth=1`); I ran `git fetch --unshallow` to recover the full history used in Check C.

---

## VERDICTS

| Check | Verdict |
|---|---|
| **A** — our drat-trim verifies all six published third-party DRAT proofs | **CONFIRMED** |
| **B** — our exact-arithmetic CNFs agree with Heule's published CNFs | **CONFIRMED** (one fully characterised, benign encoding difference at 517) |
| **C.1** — provenance of the 510-vertex graph | **PARTIALLY RESOLVED / INCONCLUSIVE on literature attribution** (see below) |
| **C.2** — 509 / 2442 (Parts 2020) is the smallest known, nothing at or below 509 | **CONFIRMED, but only at the strength of secondary sources** (primary sources egress-blocked) |
| **C.3** — no 6-chromatic unit-distance graph in the plane is known | **CONFIRMED**; adjacent problems where 6 *is* achieved are enumerated and kept separate |
| **C.4** — machine-readable Parts 509 or de Grey 1581/1585 on GitHub | **NOT FOUND** (search was not exhaustive — GitHub code search is blocked in this session) |

### Nothing failed. Findings ranked by how much they matter

1. **The 510-vertex graph our entire search is built on carries no certificate in the upstream
   repo.** `data/CNP-SAT` ships `vtx/510.vtx` and `edge/510.edge` but **no `cnf/510-4*.cnf`,
   no `proof/510-4*.drat`, and no `check/510.singular`** — unlike 517/529/553/610/633/803,
   which all have at least a proof or a Singular distance certificate. Inherited as-is, the
   510 graph was an *unverified* third-party assertion. I closed that specific hole (below):
   it really is 5-chromatic. But the gap was real and should be recorded in the catalog.
2. **510 is *not* an induced subgraph of 517.** Its exact coordinate set shares only 479 of
   510 points with `517.vtx`; 31 of its points do not occur in 517 at all. So it was not
   produced by deleting 7 vertices from the 517 graph, and any lineage note claiming that
   would be wrong.
3. **`cnf/517-4.cnf` is encoded differently from every other CNF in the repo** — it carries
   3102 extra at-most-one-colour clauses. Benign (characterised below) but it means "their
   plain CNF" is not a single consistent format, and a script that assumes one format will
   silently mis-parse.
4. **`cnf/517-4.edge` in the upstream repo is a misnamed duplicate of `cnf/517-4-sbp.cnf`**
   (byte-identical, sha256 `c9757e78…`). It is a CNF, not an edge file. Anything that globs
   `*.edge` will read a CNF.
5. **`cnf/529-4-sbp.cnf` does not exist upstream, but `proof/529-4-sbp.drat` does.** The
   published 529 proof is unpairable with any published 529 CNF until you reconstruct the
   symmetry-broken variant. Reconstruction succeeds (below), so this is a repo packaging gap,
   not a proof defect.
6. **`data/derived/G2167.edge` and `data/auxiliary_4colorable/G2167.edge` have no upstream
   counterpart** — upstream ships `vtx/G2167.vtx` but no `edge/G2167.edge`. That edge list is
   ours, not a third party's, and must not be described as acquired data. Audit result below.
7. **`data/dist-graphs` is an incomplete copy of `vsvor/dist-graphs`**: `plane/series 2/cnf/`,
   `plane/series 2/dimacs/old/` and `unsolved CNFs/` are missing locally. Everything present
   is byte-identical to upstream. Cosmetic, but the acquisition record should not claim a
   complete mirror.

---

## CHECK A — verifying Heule's own published proofs

Checker: `vendor/drat-trim/drat-trim` (our build). Every run `nice -n 19`, single-threaded,
on a machine shared with other agents' searches, so wall times are indicative, not benchmarks.

### Pairing determination (asked for explicitly)

All six published proofs belong to the **`-sbp` (symmetry-broken)** CNF variant, not the plain
one. Three independent lines of evidence:

* **Filename.** Every proof is named `<n>-4-sbp.drat`.
* **Empirical.** Each proof verifies against `<n>-4-sbp.cnf` and *fails* against `<n>-4.cnf`
  with a genuine mid-proof RAT failure — e.g. 517 against the plain CNF fails at proof line
  25818 on pivot `-1791 -1638 1665 0`; 553 fails at line 46927. These are real RAT check
  failures deep in the proof, not parse errors, so the discriminator is meaningful.
* **Structural.** The `-sbp` files pin a triangle to three colours by adding/substituting the
  units `1 0`, `6 0`, `23 0` — i.e. vertices 1, 2, 6 (1-indexed) to colours 1, 2, 3 under the
  `var(v,c) = 4v + c + 1` convention. I confirmed by exact arithmetic that **{1, 2, 6} really
  is a triangle in all nine graphs** (510/517/529/553/610/633/803/826/874), so the symmetry
  breaking is sound (colour classes are interchangeable and a clique forces distinct colours).
  These units are *not* logically implied by the plain formula, which is exactly why the plain
  pairing must fail — a proof relying on them cannot be RAT against the un-broken formula.

Two distinct `-sbp` conventions coexist upstream: for **517** the three 4-literal ALO clauses
are *replaced* by the units (same clause count, 13935); for **553/610/633/803/826/874** the
units are *appended* (clause count +3). Both were tested for 529.

### Every proof checked

| # | CNF | Proof | Proof bytes | Proof sha256 | Verdict | Wall (s) |
|---|---|---|---|---|---|---|
| 1 | `cnf/517-4-sbp.cnf` | `proof/517-4-sbp.drat` | 2 383 731 | `d4df20867ea18cc1b41642a2f87495d9941e48e0882239cd76b39c20a1a5558b` | **s VERIFIED** | 2.90 |
| 2 | `cnf/553-4-sbp.cnf` | `proof/553-4-sbp.drat` | 4 143 373 | `d71180c6d30f85ec95c91a54aee09f60b728588257198116157c92e99dd17d50` | **s VERIFIED** | 1.13 |
| 3 | `cnf/610-4-sbp.cnf` | `proof/610-4-sbp.drat` | 3 209 172 | `1b3d9b73e5249a492134e4778c23c4bad64f1bebb7cd20a1e6d5fa37adf21b34` | **s VERIFIED** | 0.84 |
| 4 | `cnf/633-4-sbp.cnf` | `proof/633-4-sbp.drat` | 4 565 335 | `24533b196fdfa2d8b6a316f7dd86538662a3033bfcd602744b17c530c4c040b0` | **s VERIFIED** | 1.22 |
| 5 | `cnf/803-4-sbp.cnf` | `proof/803-4-sbp.drat` | 21 904 992 | `9438aafe71fc887b69c6d7649d77769f1ce651c87c8f3dc5593309e1e2e07ddb` | **s VERIFIED** | 6.98 |
| 6 | `artifacts/adv3/529-4-sbpA.cnf` (reconstructed, units appended) | `proof/529-4-sbp.drat` | 2 704 564 | `fc2edf1fb573de69f5f2c786d62c50b7da13e7b2b8bc1b1bb5859bea58ee4cb6` | **s VERIFIED** | 4.32 |
| 7 | `artifacts/adv3/529-4-sbpB.cnf` (reconstructed, ALO replaced) | `proof/529-4-sbp.drat` | (same as #6) | (same as #6) | **s VERIFIED** | 3.34 |
| 8 | `cnf/517-4.cnf` (wrong pairing, control) | `proof/517-4-sbp.drat` | — | — | s NOT VERIFIED (RAT fail @ line 25818) | 0.15 |
| 9 | `cnf/553-4.cnf` (wrong pairing, control) | `proof/553-4-sbp.drat` | — | — | s NOT VERIFIED (RAT fail @ line 46927) | 0.17 |
| 10 | `cnf/610-4.cnf` (wrong pairing, control) | `proof/610-4-sbp.drat` | — | — | s NOT VERIFIED | 0.15 |
| 11 | `cnf/633-4.cnf` (wrong pairing, control) | `proof/633-4-sbp.drat` | — | — | s NOT VERIFIED | 0.19 |
| 12 | `cnf/529-4.cnf` (only published 529 CNF; wrong pairing) | `proof/529-4-sbp.drat` | — | — | s NOT VERIFIED (RAT fail @ line 30758) | 0.17 |
| 13 | `cnf/803-4.cnf` (wrong pairing, control) | `proof/803-4-sbp.drat` | — | — | s NOT VERIFIED | 1.14 |

**All 6 of 6 published proofs verify.** 826 and 874 have `-sbp` CNFs upstream but **no published
proof**, so there was nothing of Heule's to check for them (see the solver cross-check below).

Core statistics reported by drat-trim (from `artifacts/adv3/dt_*.log`) — note **0 RAT lemmas**
in every core, i.e. all six proofs are in fact RUP/DRUP:

| Graph | clauses in core | lemmas in core | resolution steps |
|---|---|---|---|
| 517 | 9481 / 13935 | 25835 / 25838 | 2 707 196 |
| 553 | 9436 / 11444 | 18792 / 18793 | 2 500 237 |
| 610 | 10261 / 12613 | 13906 / 13907 | 1 944 440 |
| 633 | 10531 / 13300 | 18972 / 18973 | 2 661 872 |
| 803 | 15453 / 17382 | 75910 / 75911 | 8 231 747 |
| 529 (recon) | 9487 / 11209 | 30835 / 30836 | 3 154 242 |

That the two independently reconstructed 529 CNFs give *identical* core and lemma counts
(9487 / 30835 / 3 154 242) is strong evidence the reconstruction recovered the intended formula.

### Negative controls on our checker — it is not a rubber stamp

`artifacts/adv3/control_results.tsv`, `artifacts/adv3/ctl_*.log`:

| Control | Result | Checker message |
|---|---|---|
| 517 proof, one literal sign-flipped at line 12000 | s NOT VERIFIED | RAT check failed on all pivots, failed at line 12001 |
| 517 proof truncated (last 500 lemmas + empty clause dropped) | s NOT VERIFIED | `ERROR: no conflict` |
| 517 proof against 553's `-sbp` CNF (cross-graph) | s NOT VERIFIED | `conflict claimed, but not detected` |

Each failure mode is distinct and diagnostic. Combined with the 6 VERIFIED and 6 wrong-pairing
NOT VERIFIED results, our drat-trim build discriminates correctly in both directions on a third
party's artifacts produced by a different solver on different hardware.

### Second, independently implemented checker: LRAT

drat-trim vouching for itself is weak evidence. So every published proof was also re-checked
through a **different checker program**: `drat-trim -L` emits an LRAT proof (a resolution-hint
chain), which is then verified by `lrat-check` — a separate source file with a separate
verification algorithm (it *follows* given hints instead of searching for them). I built it
from `vendor/drat-trim/lrat-check.c` to `artifacts/adv3/lrat-check`.

| Graph | CNF | drat-trim -L | LRAT bytes | `lrat-check` verdict | added / deleted clauses |
|---|---|---|---|---|---|
| 517 | `517-4-sbp.cnf` | s VERIFIED | 17 181 634 | **c VERIFIED** | 39770 / 39638 |
| 553 | `553-4-sbp.cnf` | s VERIFIED | 14 543 350 | **c VERIFIED** | 30236 / 30195 |
| 610 | `610-4-sbp.cnf` | s VERIFIED | 11 387 173 | **c VERIFIED** | 26519 / 26422 |
| 633 | `633-4-sbp.cnf` | s VERIFIED | 16 072 672 | **c VERIFIED** | 32272 / 32243 |
| 803 | `803-4-sbp.cnf` | s VERIFIED | 56 274 614 | **c VERIFIED** | — |
| 529 | `529-4-sbpA.cnf` (recon) | s VERIFIED | 19 008 522 | **c VERIFIED** | — |

Negative control on the second checker: corrupting one antecedent hint id in `517.lrat`
(line 19689) makes `lrat-check` exit 1 with
`c FAILED: multiple literals unassigned in hint 131: 521 522`. So `lrat-check` is also not a
rubber stamp. Logs: `artifacts/adv3/lratgen_*.log`, `artifacts/adv3/lratchk_*.log`,
`artifacts/adv3/lratchk_517bad.log`.

**All 6 published proofs are therefore VERIFIED by two independently implemented checkers.**

### Our own solvers on their CNFs (independent of their proofs)

`vendor/kissat` emitting DRAT, verified by our drat-trim (`artifacts/adv3/ctl_ourproof_*.log`):

| CNF | kissat | wall (s) | our proof re-checked |
|---|---|---|---|
| `517-4-sbp.cnf` | s UNSATISFIABLE | 1.73 | **s VERIFIED** (1.00) |
| `553-4-sbp.cnf` | s UNSATISFIABLE | 2.05 | **s VERIFIED** (1.03) |
| `610-4-sbp.cnf` | s UNSATISFIABLE | 1.33 | **s VERIFIED** (0.76) |
| `633-4-sbp.cnf` | s UNSATISFIABLE | 1.79 | **s VERIFIED** (0.97) |
| `803-4-sbp.cnf` | s UNSATISFIABLE | 10.58 | **s VERIFIED** (7.61) |
| `826-4-sbp.cnf` | s UNSATISFIABLE | 6.98 | **s VERIFIED** (3.83) |
| `874-4-sbp.cnf` | s UNSATISFIABLE | 6.74 | **s VERIFIED** (3.27) |

So 826 and 874 — the two graphs with no published proof — now have machine-checked
certificates of non-4-colourability produced entirely by our toolchain.

**Aborted run, disclosed:** a planned cadical cross-solve of the *plain* (un-symmetry-broken)
`826-4.cnf` / `874-4.cnf` was killed after ~9 minutes because it had written a 900 MB DRAT file
and was competing with other agents for the 4 shared cores. Its partial proof was deleted and
**no verdict is claimed from it**. The kissat rows above already give an independent-solver
result on those two graphs.

---

## CHECK B — do our CNFs agree with theirs?

`tests/adv3_cnf_crosscheck.py`, full machine-readable output `artifacts/adv3/checkB.json`,
console log `artifacts/adv3/checkB.log`.

Method — no float decides anything:
* Parse `vtx/<n>.vtx` with `hn.mathematica.load_vtx` into exact elements of
  Q(√3, √5, √11) (the field is auto-detected from the radicals actually present, and is
  Q(√3,√5,√11) for all eight files).
* Edge set derived by **`detect_edges_bruteforce_exact`** — exact arithmetic on all O(n²)
  pairs, no prefilter — used as the reference. The production grid detector `detect_edges`
  is run too, purely to check it agrees.
* Their CNF's implied edge set recovered from binary all-negative clauses under
  `var(v,c) = 4v + c + 1`, per colour, then required identical across all four colours.
* Our CNF built by `hn.cnf.encode_coloring(n, exact_edges, 4, break_symmetry=False)` and
  compared as a **set of sorted literal tuples** against theirs.

| n | our exact edges (O(n²)) | grid detector agrees | their `.edge` == our exact | their CNF header | their CNF's implied edges == our exact | ALO | AMO | clause **set** identical to ours |
|---|---|---|---|---|---|---|---|---|
| 517 | 2579 | yes | **yes** | `p cnf 2068 13935` | **yes** | 517 | 3102 | no — see note |
| 529 | 2670 | yes | **yes** | `p cnf 2116 11209` | **yes** | 529 | 0 | **yes** |
| 553 | 2722 | yes | **yes** | `p cnf 2212 11441` | **yes** | 553 | 0 | **yes** |
| 610 | 3000 | yes | **yes** | `p cnf 2440 12610` | **yes** | 610 | 0 | **yes** |
| 633 | 3166 | yes | **yes** | `p cnf 2532 13297` | **yes** | 633 | 0 | **yes** |
| 803 | 4144 | yes | **yes** | `p cnf 3212 17379` | **yes** | 803 | 0 | **yes** |
| 826 | 4273 | yes | **yes** | `p cnf 3304 17918` | **yes** | 826 | 0 | **yes** |
| 874 | 4461 | yes | **yes** | `p cnf 3496 18718` | **yes** | 874 | 0 | **yes** |

Additional confirmations, all eight graphs: `.vtx` line count equals the graph's name;
zero exact duplicate points; `nvars == 4n`; header clause count equals the actual number of
clauses; zero duplicate clauses; the four per-colour edge-clause sets are identical to each
other.

**No soundness alarm.** Specifically: **not one edge in any of their CNFs or `.edge` files
fails to be exactly unit distance in our arithmetic, and not one exactly-unit pair is
omitted.** The symmetric difference is empty in both directions for all eight graphs, so
there is no vertex pair to report with an exact squared distance.

### The single difference, fully characterised (517)

For seven of eight graphs our clause set is **bit-for-bit set-identical** to theirs
(clause counts match exactly, e.g. 11209 = 529 ALO + 4·2670 edge). For **517** theirs has
13935 clauses to our 10833. The difference is entirely one-directional and one kind:

* clauses only in ours: **0**
* clauses only in theirs: **3102**, all of them at-most-one-colour clauses
  `{-var(v,c₁), -var(v,c₂)}` — exactly 517 × C(4,2) = 3102.

So their 517 formula is ours plus a complete exactly-one-colour encoding.
**Logically harmless in both directions**: ALO + edge clauses is satisfiable iff the graph is
4-colourable (pick any true colour per vertex), and ALO + AMO + edge clauses is satisfiable iff
the graph is 4-colourable (the assignment *is* a colouring). Both are equisatisfiable with
4-colourability, so `517-4.cnf` UNSAT and our `517` UNSAT assert the same mathematical fact.
The 517 file is simply the odd one out in their repo — it was committed in a later batch
(2019-07-27) than the May-2018 files, and `color.c` in the repo emits the *no-AMO* form, so
`517-4.cnf` was not produced by the `color.c` in that repo.

---

## CHECK C — provenance and record audit

**Method limits, stated up front.** In this session `arxiv.org`, `mathworld.wolfram.com`,
`cs.cmu.edu`, `researchgate.net`, `zenodo.org`, and also `dustingmixon.wordpress.com`,
`michaelnielsen.org`, `handwiki.org`, `semanticscholar.org`, `grokipedia.com` are **all
egress-blocked** for both curl and WebFetch, and `api.github.com` is restricted to
`repos/{owner}/{repo}` (no code/repo search). Only `github.com` git transport worked.

Therefore, unless a claim below is marked **VERIFIED**, it rests on **WebSearch result
summaries, which are machine-generated paraphrases of pages I could not open**. I did not
read the primary PDFs. I have marked every such claim **INFERRED** and, where the summaries
disagreed with each other, said so rather than picking one.

### C.1 — Where does the 510-vertex graph come from?

**VERIFIED (from the repo's own git history, recovered by `git fetch --unshallow`):**

| commit | date | author | message | files added |
|---|---|---|---|---|
| `f558d07` | 2018-05-26 | marijn | first graphs | `vtx/{610,633,803,826,874}.vtx`, `edge/*` |
| `e67d584` | 2018-05-26 | marijn | first proofs | `color.c`, `proof/{610,633}-4-sbp.drat` |
| `d55d37f` | 2018-05-30 | marijn | 553 cnf | all `cnf/{553..874}-4*.cnf`, `proof/803-4-sbp.drat` |
| `59350ba` / `bbe07ed` / `a238bb0` | 2018-05-30 | marijn | 553 graph / singular / proof | `vtx/553.vtx`, `check/553.singular`, `proof/553-4-sbp.drat` |
| `efe60fb` | **2019-07-02** | cav | **529 graph** | `cnf/529-4.cnf`, `edge/529.edge`, `proof/529-4-sbp.drat`, `vtx/529.vtx` |
| `f4dc890` | **2019-07-27** | cav | **graph with 517 vertices** | `cnf/517-4*.cnf`, `cnf/517-4.edge`, `edge/517.edge`, `proof/517-4-sbp.drat`, `vtx/517.vtx`, `vtx/G2167.vtx` |
| `a65ee28` | **2019-08-08** | cav | **510 vertices 2504 edges** | **`edge/510.edge`, `vtx/510.vtx` — and nothing else** |
| `1f05ea2` | 2019-08-10 | cav | union of large subgraphs | `edge/L403.edge`, `vtx/L403.vtx` |
| `bb41495` | 2021-09-27 | Marienus Heule | T721 | `edge/T721.edge`, `vtx/T721.vtx` |

Author/committer identity on the head commit is `Marienus Heule <mheule@SCS003B8.SP.CS.CMU.EDU>`;
the 2019 commits are authored as `cav`. So:

* **VERIFIED:** the 510 graph enters the repo on **2019-08-08**, one month after 517, in a
  commit authored by the same repo owner, with the commit message `510 vertices 2504 edges`.
  It is committed as **Heule's repo content**; there is no attribution to anyone else in the
  repo and no README, paper reference, or note accompanying it.
* **VERIFIED:** the 510 commit contains **only** coordinates and an edge list. Unlike every
  other 5-chromatic candidate in the repo it has **no CNF, no DRAT proof, and no Singular
  distance certificate**. Inside the repo the 510 graph is an uncertified assertion.
* **VERIFIED by our own toolchain** (`tests/adv3_510_unsat.py`, log
  `artifacts/adv3/` + task output): from `vtx/510.vtx`, 510 distinct exact points in
  Q(√3,√5,√11), **2504 exactly-unit edges** — matching `edge/510.edge` **exactly** (symmetric
  difference empty), minimum degree 4, no vertex of degree < 4. Encoding with our encoder:
  4-colouring is **UNSAT** (kissat, 116.85 s) and the refutation is **s VERIFIED** by
  drat-trim (135.42 s); 5-colouring is **SAT** (0.08 s). Hence **χ(510-graph) = 5**, now
  machine-certified. Artifacts: `artifacts/adv3/adv3_510_k4.cnf`
  (sha256 `e112735ceeffc8d8132017d75a65ca7c065a6106e48219b82b85d042d1e99eef`, 138 001 B) and
  `artifacts/adv3/adv3_510_k4.drat`
  (sha256 `a6a20711c451dcba519ef24cfc413e9182b6ab123bda9d72d88d8fac61270d99`, 117 170 893 B).
* **VERIFIED (`tests/adv3_provenance_510.py`, `artifacts/adv3/prov510.json`):** 510 is **not**
  a vertex-subset of any other file in the repo. Exact-coordinate overlaps:

  | vs | n | shared exact points | 510 ⊆ it? |
  |---|---|---|---|
  | 517 | 517 | **479** | no |
  | 529 | 529 | 468 | no |
  | 553 | 553 | 385 | no |
  | 633 | 633 | 389 | no |
  | L403 | 403 | 375 | no |
  | G2167 | 2167 | 373 | no |
  | 610 / 803 / 826 / 874 / S199 | — | 204 / 231 / 224 / 239 / 143 | no |

  So the 510 graph is **not** 517 minus 7 vertices: 31 of its 510 points do not appear in
  `517.vtx` at all. **CONJECTURE (labelled as such, not verified):** it was produced by a
  fresh run of the minimiser from a differently-placed/rotated starting configuration rather
  than by trimming 517. I have no evidence for the mechanism.

* **INFERRED, and genuinely conflicting — the discrepancy the brief asked about.** Web search
  summaries disagree about who owns "510":
  * Wolfram MathWorld's *Heule Graphs* entry is reported to implement the family as
    `GraphData["HeuleGraph510"]`, and to say Heule "reduced the number of vertices to 553,
    then to 517" — i.e. **517 is MathWorld's headline number for Heule**, yet a *510* entry
    is named after him. ([MathWorld: Heule Graphs](https://mathworld.wolfram.com/HeuleGraphs.html))
  * MathWorld's *Heule Spindle* entry is reported to say the Heule spindle occurs "in Heule
    graphs and **Parts graphs on 510, 525, 529, and 553** vertices", which would put a 510 in
    the *Parts* family. ([MathWorld: Heule Spindle](https://mathworld.wolfram.com/HeuleSpindle.html))
  * One search summary asserted flatly that "Jaan Parts achieved a 510-vertex graph while
    Marijn Heule achieved a 517-vertex graph", and another gave a 510 graph "2508 edges" —
    **which contradicts the file in front of me: `edge/510.edge` has 2504 edges, and I
    confirmed 2504 by exact arithmetic.** I treat the 2508 figure as an artefact of the
    search summariser, not evidence.

  **Best reading, stated as inference:** the *published, paper-attributed* Heule record is
  517 (the SAT/CP-2019 line of work; the arXiv abstract for *Trimming Graphs Using Clausal
  Proof Optimization*, arXiv:1907.00929, is summarised as reducing 553 → **529**, with 517
  arriving after the July 2019 posting). The 510 graph is dated 2019-08-08 in Heule's own
  repo — **after** that paper — and I found **no paper attributing a 510-vertex 5-chromatic
  unit-distance graph to anyone.** Its likeliest status is *repo-only, unpublished follow-up
  work in the Polymath16 period*, possibly overlapping with Parts' contemporaneous
  minimisation. **Attribution: INCONCLUSIVE.** What is certain is that citing "510" as a
  literature record would be citing a bare git commit.

  **Practical consequence for this project:** the 510 graph is a legitimate 5-chromatic
  unit-distance graph (I certified it), but it is **not the record** (509 is), it is **not
  the number the literature associates with Heule** (517 is), and it has **no citable
  publication**. Any write-up must describe it as "the 510-vertex graph in Heule's CNP-SAT
  repository, commit `a65ee28`, 2019-08-08", not as a published result.

### C.2 — Is 509 / 2442 (Parts 2020) the smallest known, with nothing at or below 509?

**CONFIRMED at secondary-source strength; primary sources were unreachable.**

Search summaries consistently report: as of August 2026 the smallest known 5-chromatic
unit-distance graph in the plane is the **509-vertex Parts graph**, with **2442 edges**,
implemented as `GraphData["PartsGraph509"]`; the progression was de Grey 1581 (2018) →
Mixon graphs → Heule graphs → Parts graphs. Parts' papers:
*Graph minimization, focusing on the example of 5-chromatic unit-distance graphs in the plane*
(arXiv:2010.12665; Geombinatorics 29(3):137–166, 2020) and *The chromatic number of the plane
is at least 5 — a human-verifiable proof* (arXiv:2010.12661; Geombinatorics 30(2):77–102, 2020).

Targeted searches for **508, 507, 505, 500 vertices** and for **"below 509"** / improvements in
2023–2026 returned **no** smaller construction. The only 2026-dated result that surfaced is
**Haugland (2026), arXiv:2608.04542, "A Moser-spindle-free 5-chromatic unit distance graph on
2131 vertices in the plane"** — a *restricted* class (no Moser spindle), explicitly **not** an
improvement on the unrestricted 509 record.

Uncertainty I am not going to paper over: I could not open arXiv:2010.12665 or MathWorld, so
**the "2442 edges" figure is INFERRED from search summaries only**, and one summary attributed
the current-record statement jointly to "Parts 2020, Haugland 2026" (probably meaning Haugland
2026 restates the record). I did not find any machine-readable 509 graph to check the counts
against (see C.4), so **nothing about 509 in this report is verified by computation.**

### C.3 — Is a 6-chromatic unit-distance graph in the plane known?

**CONFIRMED: no.** χ(plane) ∈ {5, 6, 7} as of August 2026; the lower bound is still 5
(de Grey 2018, arXiv:1804.02385), the upper bound 7 (Isbell/Hadwiger, 1950s). No 6-chromatic
**unit-distance** graph **in the plane** is known.

Adjacent results where chromatic number 6 **is** achieved — these are **different problems**
and must not be conflated:

| Result | Problem | Same as ours? |
|---|---|---|
| 6-chromatic **odd-distance** graph in the plane (Parts; arXiv:2206.12632) — claimed Heule's $500 prize | edges = *odd integer* distance, not unit distance | **No.** Different edge relation. |
| 6-chromatic **two-distance** graph in the plane, 16 vertices (arXiv:2010.12656; cf. arXiv:1909.13177) | edges = either of *two* distances | **No.** Different edge relation. |
| 6-chromatic **unit-distance graph in ℝ³**, 79 vertices / 250 edges | unit distance, but dimension 3 | **No.** Different ambient space; χ(ℝ³) ≥ 6 is a separate quantity. |
| 5-chromatic unit-distance graphs on **2-spheres** S²(r) (arXiv:2106.11824; vsvor/dist-graphs) | unit distance on a sphere | **No.** Different surface. |
| 5-chromatic same-distance graph in the **hyperbolic** plane (arXiv:2303.06801) | hyperbolic metric | **No.** |
| de Grey (2026): 5-chromatic triangle-free unit-distance graph in **ℝ³**, 61 vertices | dimension 3, triangle-free | **No.** |

**The only claim relevant to this project is: no 6-chromatic unit-distance graph in the
Euclidean plane is known, so raising χ(plane) ≥ 6 remains open.** This is INFERRED from
search summaries (the primary sources were blocked), but it is uniformly reported and I found
no source claiming otherwise.

### C.4 — Machine-readable Parts 509, or de Grey 1581/1585, on GitHub?

**NOT FOUND.** What I actually did:

* WebSearch restricted to `github.com` / `gist.github.com` / `raw.githubusercontent.com`,
  multiple phrasings (509 + Parts, 1581 + de Grey, polymath16 data, coordinates, Mathematica).
* `git ls-remote` existence probes on 17 plausible repository names
  (`jaanparts/hadwiger-nelson`, `aubreydegrey/cnp`, `dustingmixon/polymath16`,
  `tomsirgedas/hadwiger-nelson`, `philipgibbs/cnp`, `boris-alexeev/hadwiger`,
  `marijnheule/CNP`, `marijnheule/hadwiger-nelson`, `haugland/cnp`, … ): **all not found**,
  except the three below.
* Cloned and inspected the three HN-related repos that do exist:
  * **`vsvor/dist-graphs`** — Voronov et al.'s plane/sphere search. Plane graphs are
    `p edge 3877 26814`-class (series 1) and `p edge 64513 542592`-class (series 2). **No 509,
    no 1581.**
  * **`simon-tiger/Hadwiger-Nelson-Project-Data`** — contains `517.edge`, which is
    **byte-identical to Heule's `edge/517.edge`** (sha256
    `dc5085db9682aa246c3fc56efed9767e2a294a43e621a3e67a690d0489bdadc9`). A re-hosting of
    Heule's 517, not a new graph. **No 509, no 1581.**
  * **`alozanoroble/Erdos90`** — images/PDFs of unit-distance figures only, no graph data.
* `marijnheule/CNP-SAT` itself: no 509, no 1581/1585 (largest are `G2167.vtx`, `G2347.cnf`).

**Caveat, stated plainly:** GitHub's code-search API is blocked for this session
(`api.github.com` is restricted to `repos/{owner}/{repo}`), so this is a name- and
web-search-driven sweep, **not an exhaustive search of GitHub.** The honest verdict is
**NOT FOUND, non-exhaustive** — a copy may well exist in a repo I could not discover, or
outside GitHub (Geombinatorics supplements, the Polymath16 wiki, MathWorld's `GraphData`).

### C.5 — Local record audit (our own `data/` vs upstream)

**VERIFIED by sha256, all files:**

* `data/five_chromatic_plane/{510,517,529,553,610,633,803,826,874}.{vtx,edge}` — **18/18
  byte-identical** to `data/CNP-SAT/{vtx,edge}/`.
* `data/auxiliary_4colorable/{G2167.vtx, L403.*, S199.*, T721.*}` — byte-identical to upstream.
* `data/auxiliary_4colorable/G2167.edge` and `data/derived/G2167.edge` — **no upstream file
  exists**; upstream ships `vtx/G2167.vtx` only. These are *our* derivations, so I audited
  them (`tests/adv3_derived_g2167.py` → `artifacts/adv3/g2167.log`): `G2167.vtx` parses to
  **2167 lines, 2167 distinct exact points** in Q(√3,√5,√11); O(n²) exact brute force yields
  **16512 edges**, the grid detector yields the same 16512 (agree = True), and **both local
  `G2167.edge` files match the exact edge set exactly** (`matches_exact=True`, symmetric
  difference empty in both directions). **Our derived G2167 edge list is CORRECT.**
* `data/dist-graphs` — every present file matches `vsvor/dist-graphs`, but
  `plane/series 2/cnf/`, `plane/series 2/dimacs/old/` and `unsolved CNFs/` are **absent
  locally**. Not a soundness issue; the acquisition record should not claim a full mirror.

---

## What would change these verdicts

* Check A would flip if **both** checkers were accepting unsound proofs. Four negative
  controls (corrupted DRAT, truncated DRAT, cross-graph DRAT, corrupted LRAT hint) argue
  against that, and the LRAT path is a second, separately implemented algorithm. Residual
  gap: `lrat-check` ships in the same repository as `drat-trim` and was written by the same
  group, so it is *independent in implementation* but not *independent in origin*. A checker
  from an unrelated author (e.g. cake_lpr, a verified LRAT checker) has **not** been run.
* Check B is as strong as `hn.field`'s canonical-basis equality test. I used it as the oracle
  and did not attempt to break it — that is Adversary 2's lane. I did confirm the grid
  prefilter and the O(n²) exact detector agree on all 9 graphs (≈2 M pairs), which is
  evidence for the prefilter but not a proof of its window.
* Check C's literature claims are search-summary-grade, not primary-source-grade, because
  every relevant domain except github.com is egress-blocked. If any of C.2/C.3/C.4 matters to
  a headline claim, it must be re-checked with real access to arXiv and MathWorld before
  publication.
