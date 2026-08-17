#!/usr/bin/env python3
"""Generate the self-contained progress dashboard from catalog + logs.

Re-run this after any change and re-publish; it reads live state from
catalog/hn.sqlite, artifacts/*/verdict.*.json, catalog/*.jsonl and reports/.
Floating point appears here only as DISPLAY GEOMETRY for the canvas drawing; it
decides nothing about the mathematics.
"""
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = "/home/user/CustomLLM"
OUT = os.path.join(ROOT, "dashboard", "index.html")


def read_json(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default if default is not None else {}


def leaderboard():
    rows = []
    try:
        con = sqlite3.connect(os.path.join(ROOT, "catalog", "hn.sqlite"))
        cur = con.execute(
            "SELECT n_vertices,k,verdict,solver,checker,checker_verdict,"
            "proof_sha256,proof_bytes,archived_sha256,archived_bytes,wall_seconds,"
            "checker_seconds FROM attempts WHERE verdict='UNSAT' AND "
            "checker_verdict='VERIFIED' ORDER BY n_vertices"
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        con.close()
    except Exception:
        pass
    return rows


def adversary_findings():
    """Parse severity-tagged findings out of the adversary reports."""
    out = []
    spec = [
        ("ADVERSARY_1.md", "A1 — the 510 claim"),
        ("ADVERSARY_2.md", "A2 — toolchain soundness"),
        ("ADVERSARY_3.md", "A3 — third-party proofs"),
    ]
    for fn, label in spec:
        p = os.path.join(ROOT, "reports", fn)
        if not os.path.exists(p):
            continue
        txt = open(p, errors="replace").read()
        out.append({
            "agent": label,
            "exists": True,
            "bytes": len(txt),
            "critical": len(re.findall(r"\bCRITICAL\b", txt)),
            "major": len(re.findall(r"\bMAJOR\b", txt)),
            "confirmed": len(re.findall(r"\bCONFIRMED\b", txt)),
            "refuted": len(re.findall(r"\bREFUTED\b", txt)),
        })
    return out


def drat_table():
    p = os.path.join(ROOT, "artifacts", "adv3", "drat_results.tsv")
    rows = []
    if os.path.exists(p):
        for line in open(p):
            f = line.rstrip("\n").split("\t")
            if len(f) >= 6:
                rows.append({"tag": f[0], "cnf": f[1], "proof": f[2],
                             "rc": f[3], "wall": round(float(f[4]), 2),
                             "verdict": f[5]})
    return rows


def search6_stats():
    """Triage telemetry from the two-tier search: sampling rate + filter hit rate."""
    rows = []
    p = os.path.join(ROOT, "catalog", "search6.jsonl")
    if os.path.exists(p):
        for line in open(p):
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    attempts = [r for r in rows if "result_n" in r]
    imps = [r for r in rows if r.get("IMPROVED")]
    log = os.path.join(ROOT, "catalog", "search6.log")
    triaged = core_beat = fulls = calls = 0
    finished = 0
    for line in (open(log) if os.path.exists(log) else []):
        m = re.search(r"triaged=(\d+) core_beat=(\d+) full=(\d+) imp=(\d+) calls=(\d+)", line)
        if m:
            finished += 1
            triaged += int(m.group(1)); core_beat += int(m.group(2))
            fulls += int(m.group(3)); calls += int(m.group(5))
    return {"triaged": triaged, "core_beat": core_beat, "full_passes": fulls,
            "solver_calls": calls, "workers_done": finished,
            "improvements": len(imps),
            "best": min([r["n"] for r in rows if r.get("n")] or [510]),
            "full_pass_results": [r["result_n"] for r in attempts]}


def main():
    g = read_json(os.path.join(ROOT, "dashboard", "graph510.json"))
    st = read_json(os.path.join(ROOT, "dashboard", "state.json"))
    v4 = read_json(os.path.join(ROOT, "artifacts", "heule510", "verdict.k4.json"))
    v5 = read_json(os.path.join(ROOT, "artifacts", "heule510", "verdict.k5.json"))
    payload = {
        "graph": g,
        "state": st,
        "v4": {k: v4.get(k) for k in
               ("verdict", "checker", "checker_verdict", "checked_sha256",
                "checked_bytes", "archived_sha256", "archived_bytes",
                "wall_seconds", "checker_seconds", "n_vars", "n_clauses",
                "solver", "solver_version")},
        "v5": {k: v5.get(k) for k in ("verdict", "model_check")},
        "leaderboard": leaderboard(),
        "adversaries": adversary_findings(),
        "drat": drat_table(),
        "lrat": _lrat(),
        "s6": search6_stats(),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(html)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")


def _lrat():
    p = os.path.join(ROOT, "artifacts", "adv3", "LRAT_MANIFEST.txt")
    rows = []
    if os.path.exists(p):
        for line in open(p):
            m = re.match(r"^(\S+\.lrat)\s+(\d+)\s+([0-9a-f]{64})", line.strip())
            if m:
                rows.append({"file": m.group(1), "bytes": int(m.group(2)),
                             "sha": m.group(3)})
    return rows


TEMPLATE = r"""<title>Chromatic Number Attack</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{
  --ground:#F4F5F8; --panel:#FFFFFF; --panel-2:#EDEFF4; --line:#D6DAE3;
  --ink:#171A22; --ink-2:#4A5160; --ink-3:#767E8F;
  --accent:#0E7C86; --accent-soft:#D8ECEE;
  --ok:#1E7A4C; --ok-soft:#DCEEE3; --bad:#B3341F; --bad-soft:#F6E0DB;
  --warn:#A8751A; --warn-soft:#F6EBD6;
  --c0:#2D5BA8; --c1:#B3341F; --c2:#1E7A4C; --c3:#8A5CB8; --c4:#B8860B;
  --shadow:0 1px 2px rgba(20,24,35,.06),0 8px 24px rgba(20,24,35,.05);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0E1017; --panel:#171A23; --panel-2:#1F232E; --line:#2B303D;
    --ink:#E8EAF0; --ink-2:#A6AEBF; --ink-3:#78808F;
    --accent:#4FC3CE; --accent-soft:#123138;
    --ok:#5FCB92; --ok-soft:#14301F; --bad:#F08770; --bad-soft:#3A1710;
    --warn:#E0B15C; --warn-soft:#33260E;
    --c0:#6C97E0; --c1:#F08770; --c2:#5FCB92; --c3:#B892E0; --c4:#E0BE5C;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"]{
  --ground:#0E1017; --panel:#171A23; --panel-2:#1F232E; --line:#2B303D;
  --ink:#E8EAF0; --ink-2:#A6AEBF; --ink-3:#78808F;
  --accent:#4FC3CE; --accent-soft:#123138;
  --ok:#5FCB92; --ok-soft:#14301F; --bad:#F08770; --bad-soft:#3A1710;
  --warn:#E0B15C; --warn-soft:#33260E;
  --c0:#6C97E0; --c1:#F08770; --c2:#5FCB92; --c3:#B892E0; --c4:#E0BE5C;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.3);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:32px 20px 72px}
h1,h2,h3{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:clamp(28px,4.4vw,44px);line-height:1.1;letter-spacing:-.015em}
h2{font-size:21px;letter-spacing:-.005em}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3)}
.sub{color:var(--ink-2);max-width:66ch;margin-top:10px}
header{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:28px}
.topline{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
section{margin-top:36px}
.shead{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.shead .rule{flex:1;height:1px;background:var(--line);min-width:24px}
.grid{display:grid;gap:14px}
.cards{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:16px 18px;box-shadow:var(--shadow)}
.card .k{font-family:var(--mono);font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3)}
.big{font-family:var(--serif);font-size:40px;line-height:1;margin-top:8px;
  font-variant-numeric:tabular-nums}
.card .note{color:var(--ink-2);font-size:13px;margin-top:8px}
.pill{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);
  font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;
  border-radius:999px;border:1px solid transparent;white-space:nowrap}
.p-ok{background:var(--ok-soft);color:var(--ok);border-color:var(--ok)}
.p-bad{background:var(--bad-soft);color:var(--bad);border-color:var(--bad)}
.p-warn{background:var(--warn-soft);color:var(--warn);border-color:var(--warn)}
.p-neutral{background:var(--panel-2);color:var(--ink-2);border-color:var(--line)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;
  background:var(--panel);box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);
  white-space:nowrap}
th{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3);background:var(--panel-2)}
tbody tr:last-child td{border-bottom:none}
td.num{font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:12.5px}
code,.mono{font-family:var(--mono);font-size:12px}
.hash{font-family:var(--mono);font-size:11.5px;color:var(--ink-2)}
.stage{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px}
.step{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:13px 15px;box-shadow:var(--shadow);border-left:3px solid var(--line)}
.step.ok{border-left-color:var(--ok)} .step.bad{border-left-color:var(--bad)}
.step.warn{border-left-color:var(--warn)}
.step .t{font-weight:600;margin:5px 0 4px} .step .d{font-size:12.5px;color:var(--ink-2)}
figure{margin:0;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow);overflow:hidden}
#cv{display:block;width:100%;height:auto;background:var(--panel)}
figcaption{padding:12px 18px;border-top:1px solid var(--line);font-size:13px;
  color:var(--ink-2);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.legend{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.sw{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.ctl{display:flex;gap:8px;flex-wrap:wrap;padding:12px 18px;border-top:1px solid var(--line);
  background:var(--panel-2)}
button{font-family:var(--sans);font-size:13px;padding:6px 13px;border-radius:7px;
  border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.note-block{background:var(--panel-2);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:8px;padding:13px 16px;font-size:13.5px;color:var(--ink-2)}
.note-block strong{color:var(--ink)}
ul.tight{margin:8px 0 0;padding-left:20px;color:var(--ink-2);font-size:13.5px}
ul.tight li{margin:4px 0}
.foot{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--ink-3);font-size:12.5px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">
<header>
  <div class="topline">
    <div>
      <div class="eyebrow">Hadwiger–Nelson · chromatic number of the plane</div>
      <h1>Attacking 5 ≤ CNP ≤ 7</h1>
    </div>
    <div id="hstat"></div>
  </div>
  <p class="sub">Every unit distance is confirmed by exact arithmetic in an algebraic
  number field. Every non-colourability claim carries a machine-checked proof. This page
  reports what is <em>verified</em>, what is <em>blocked</em>, and what was <em>refuted</em> —
  including refutations of our own claims.</p>
</header>

<section>
  <div class="shead"><h2>Where it stands</h2><div class="rule"></div></div>
  <div class="grid cards" id="cards"></div>
  <div class="note-block" style="margin-top:14px">
    <strong>This is not a record.</strong> The smallest known 5-chromatic planar
    unit-distance graph is <strong>509 vertices</strong> (Parts, 2020). Our best verified
    graph has 510, so it is a reproduction that validates the pipeline — one vertex worse
    than the state of the art. A record needs ≤ 508; 509 would only tie.
  </div>
</section>

<section>
  <div class="shead"><h2>The graph, drawn from its exact coordinates</h2><div class="rule"></div></div>
  <figure>
    <canvas id="cv" width="1400" height="880" role="img"
      aria-label="The 510-vertex unit-distance graph, drawn with a verified 5-colouring"></canvas>
    <div class="ctl">
      <button id="b5" aria-pressed="true">5-colouring (verified)</button>
      <button id="b0" aria-pressed="false">Uncoloured</button>
      <button id="be" aria-pressed="true">Edges</button>
    </div>
    <figcaption>
      <div class="legend" id="legend"></div>
      <div id="gcap" class="mono"></div>
    </figcaption>
  </figure>
  <div class="note-block" style="margin-top:14px">
    Every segment above is a pair of points at distance <em>exactly</em> 1, confirmed in
    <span class="mono" id="fieldname"></span> — not within a tolerance. The colouring shown
    was produced by a SAT solver and then re-checked by independent code against the
    exactly-derived edge list. <strong>Four colours are impossible</strong> for this graph,
    and that impossibility is what the proof below certifies. Point positions here are
    floating point for drawing only; they decide nothing.
  </div>
</section>

<section>
  <div class="shead"><h2>Milestones</h2><div class="rule"></div></div>
  <div class="stage" id="miles"></div>
</section>

<section>
  <div class="shead"><h2>The seven things a claim needs</h2><div class="rule"></div></div>
  <div class="tablewrap"><table id="evid"><thead><tr>
    <th>Required item</th><th>State</th><th>Artifact</th></tr></thead><tbody></tbody></table></div>
</section>

<section>
  <div class="shead"><h2>Adversary findings</h2><div class="rule"></div></div>
  <div class="grid cards" id="advs"></div>
  <div class="note-block" style="margin-top:14px">
    Adversaries are scored on what they <em>break</em>. A2 found a real hole: the proof
    checker could report <span class="mono">VERIFIED</span> for a satisfiable formula with a
    zero-byte proof, because a malformed CNF sends drat-trim down a "trivial UNSAT" path
    before it ever reads the proof. It also showed the float prefilter could <em>miss</em> a
    genuine unit edge. Both are fixed — the detector is now float-free, using certified
    rational enclosures — and every prior result was re-verified afterwards to the same
    proof hash.
  </div>
</section>

<section>
  <div class="shead"><h2>Third-party proofs, checked with our checker</h2><div class="rule"></div></div>
  <div class="tablewrap"><table id="drat"><thead><tr>
    <th>Case</th><th>CNF</th><th>Proof</th><th>Wall s</th><th>Verdict</th>
    </tr></thead><tbody></tbody></table></div>
  <p class="sub">Verifying someone else's proofs, produced by different solvers on different
  hardware, is the strongest available evidence that our checker discriminates. The
  deliberately mismatched pairings return <span class="mono">NOT VERIFIED</span> — that
  negative control is what makes the positive verdicts mean anything.</p>
</section>

<section>
  <div class="shead"><h2>Corpus</h2><div class="rule"></div></div>
  <div class="tablewrap"><table id="corp"><thead><tr>
    <th>Graph</th><th>Vertices</th><th>Edges</th><th>χ</th><th>Vertex-critical</th>
    </tr></thead><tbody></tbody></table></div>
</section>

<section>
  <div class="shead"><h2>Why the search is stuck</h2><div class="rule"></div></div>
  <div class="grid cards" id="search"></div>
  <ul class="tight">
    <li>Deletion-MUS run to fixpoint returns each published graph <em>unchanged</em>. All of
      them are already vertex-critical — Heule and Parts ran this minimisation first.</li>
    <li>For the 510 graph, the k=4 UNSAT core is the <em>entire</em> vertex set, and all 510
      single-vertex deletions yield 4-colourable graphs. Measured twice, independently.</li>
    <li>So Parts' 509 is <strong>not a subgraph</strong> of Heule's 510: the two are
      structurally different graphs, not a nested chain.</li>
    <li>Consequence: reaching ≤ 508 means <em>adding</em> ambient points and deleting more
      than were added. That makes this a construction problem, not the minimisation problem
      the plan assumed.</li>
  </ul>
</section>

<div class="foot" id="foot"></div>
</div>

<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const el = (t,c,h) => { const e=document.createElement(t); if(c)e.className=c;
  if(h!==undefined)e.innerHTML=h; return e; };
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const G = D.graph||{}, S = D.state||{}, V4 = D.v4||{}, V5 = D.v5||{};
const fmtB = b => b==null ? "—" : b>=1048576 ? (b/1048576).toFixed(2)+" MB"
  : b>=1024 ? (b/1024).toFixed(1)+" kB" : b+" B";

$("#hstat").innerHTML =
  '<span class="pill '+(V4.checker_verdict==="VERIFIED"?"p-ok":"p-bad")+'">proof '+
  (V4.checker_verdict||"none")+'</span>';
$("#fieldname").textContent = G.field || "";

/* ---- summary cards ---- */
const cards=[
 {k:"Best verified",v:S.search?S.search.best:G.n,n:"vertices, χ = 5 with a checked proof"},
 {k:"World record",v:509,n:"Parts 2020 · we are 1 vertex worse"},
 {k:"Need for a record",v:"≤508",n:"509 would only tie"},
 {k:"Exact unit edges",v:G.m,n:"each confirmed in the number field"},
];
cards.forEach(c=>{const d=el("div","card");
  d.append(el("div","k",c.k),el("div","big",String(c.v)),el("div","note",c.n));
  $("#cards").append(d);});

/* ---- milestones ---- */
[["M0","Arithmetic & detection","ok","Exact field, certified detector. Moser spindle and Golomb: k=3 UNSAT verified, k=4 SAT model-checked. Adversarial near-unit pairs rejected."],
 ["M1","Reproduce de Grey 1581","bad","BLOCKED. arXiv unreachable from this host. H and J confirmed exactly; K/L rotation angles and W/M/N not found. Not guessed — guessing them is the documented silent-failure mode."],
 ["M2","Reproduce the record","warn","PASS at 510, not 509. Parts' coordinates are not obtainable here. χ=5 fully verified for the 510 graph."],
 ["M3","Beat 509","bad","No result. Corpus proven vertex-critical, so deletion alone cannot win."],
 ["M4","Reach χ ≥ 6","bad","Not attempted at scale. Open problem; nothing found."]
].forEach(([id,t,s,d])=>{const e=el("div","step "+s);
  e.append(el("div","eyebrow",id),el("div","t",t),el("div","d",d));$("#miles").append(e);});

/* ---- evidence ---- */
const ok='<span class="pill p-ok">present</span>', no='<span class="pill p-bad">missing</span>';
[["Vertex list in exact coordinates",ok,'510 pts in '+(G.field||'')+' · coord hash <span class="hash">'+String(G.coord_hash||'').slice(0,16)+'…</span>'],
 ["Edge list confirmed by exact arithmetic",ok,G.m+' edges · certified detector + brute-force all-pairs agree'],
 ["CNF",ok,'<span class="mono">'+(V4.n_vars||'?')+' vars / '+(V4.n_clauses||'?')+' clauses</span>'],
 ["Solver proof",ok,'DRAT '+fmtB(V4.checked_bytes)+' <span class="hash">'+String(V4.checked_sha256||'').slice(0,16)+'…</span>'],
 ["Checker verdict on that proof",(V4.checker_verdict==="VERIFIED"?ok:no),
   (V4.checker||'—')+' → <strong>'+(V4.checker_verdict||'—')+'</strong> in '+(V4.checker_seconds||'?')+'s'],
 ["Literature check",'<span class="pill p-warn">secondary only</span>',
   'All primary sources egress-blocked; 509 corroborated across independent summaries'],
 ["Three independent adversary reports",ok,(D.adversaries||[]).length+' filed, each naming its artifacts']
].forEach(r=>{const tr=el("tr");tr.append(el("td",null,r[0]),el("td",null,r[1]),el("td",null,r[2]));
  $("#evid").tBodies[0].append(tr);});

/* ---- adversaries ---- */
(D.adversaries||[]).forEach(a=>{const d=el("div","card");
  const pills=[];
  if(a.critical)pills.push('<span class="pill p-bad">'+a.critical+' critical</span>');
  if(a.major)pills.push('<span class="pill p-warn">'+a.major+' major</span>');
  if(a.confirmed)pills.push('<span class="pill p-ok">'+a.confirmed+' confirmed</span>');
  if(a.refuted)pills.push('<span class="pill p-neutral">'+a.refuted+' refuted</span>');
  d.append(el("div","k",a.agent),el("div",null,
    '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">'+pills.join("")+'</div>'),
    el("div","note",(a.bytes/1024).toFixed(1)+" kB report on disk"));
  $("#advs").append(d);});

/* ---- drat table ---- */
(D.drat||[]).forEach(r=>{const tr=el("tr");
  const cls=r.verdict.indexOf("NOT")>=0?"p-bad":"p-ok";
  tr.append(el("td","mono",r.tag),el("td","mono",r.cnf),el("td","mono",r.proof),
    el("td","num",r.wall),el("td",null,'<span class="pill '+cls+'">'+
    r.verdict.replace("s ","")+'</span>'));
  $("#drat").tBodies[0].append(tr);});

/* ---- corpus ---- */
(S.corpus||[]).forEach(c=>{const tr=el("tr");
  tr.append(el("td","mono",c.name),el("td","num",c.n),el("td","num",c.m),
    el("td","num","5"),el("td",null,c.critical?
      '<span class="pill p-warn">proven</span>':'<span class="pill p-neutral">untested</span>'));
  $("#corp").tBodies[0].append(tr);});
(S.traps||[]).forEach(c=>{const tr=el("tr");
  tr.append(el("td","mono",c.name),el("td","num",c.n),el("td","num",c.m),
    el("td","num","≤4"),el("td",null,'<span class="pill p-neutral">4-colourable</span>'));
  $("#corp").tBodies[0].append(tr);});

/* ---- search cards ---- */
const s6=D.s6||{}; const sc=S.search||{};
[{k:"Ambient pools built",v:(S.pools||[]).length,n:"exact, all round-trip verified"},
 {k:"Perturbations triaged",v:(s6.triaged||0)+(sc.attempts||0),n:"two-tier search, cheap core filter first"},
 {k:"Cores beating 510",v:s6.core_beat==null?"—":s6.core_beat,n:"promising enough for a full pass"},
 {k:"Full deletion passes",v:s6.full_passes||0,n:"the expensive tier"},
 {k:"Solver calls",v:(s6.solver_calls||0).toLocaleString(),n:"search-time; steer only, never a verdict"},
 {k:"Improvements found",v:(s6.improvements||0)+(sc.improvements||0),n:"below the 510 incumbent"},
 {k:"Largest pool",v:Math.max.apply(null,[0].concat((S.pools||[]).map(p=>p.n))),n:"points, exact coordinates"}
].forEach(c=>{const d=el("div","card");
  d.append(el("div","k",c.k),el("div","big",String(c.v)),el("div","note",c.n));
  $("#search").append(d);});

/* ---- canvas ---- */
const cv=$("#cv"), ctx=cv.getContext("2d");
let showCol=true, showEdges=true;
function draw(){
  const W=cv.width,H=cv.height, bb=G.bbox||[-1,-1,1,1], pad=46;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle=cssv("--panel"); ctx.fillRect(0,0,W,H);
  const sx=(W-2*pad)/(bb[2]-bb[0]), sy=(H-2*pad)/(bb[3]-bb[1]);
  const s=Math.min(sx,sy);
  const ox=pad+((W-2*pad)-(bb[2]-bb[0])*s)/2, oy=pad+((H-2*pad)-(bb[3]-bb[1])*s)/2;
  const P=(G.xy||[]).map(p=>[ox+(p[0]-bb[0])*s, H-(oy+(p[1]-bb[1])*s)]);
  const cols=[cssv("--c0"),cssv("--c1"),cssv("--c2"),cssv("--c3"),cssv("--c4")];
  if(showEdges){
    ctx.strokeStyle=cssv("--line"); ctx.lineWidth=0.6; ctx.globalAlpha=0.72;
    ctx.beginPath();
    (G.edges||[]).forEach(e=>{const a=P[e[0]],b=P[e[1]];
      if(a&&b){ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);}});
    ctx.stroke(); ctx.globalAlpha=1;
  }
  P.forEach((p,i)=>{
    ctx.beginPath(); ctx.arc(p[0],p[1],2.9,0,6.2832);
    ctx.fillStyle = showCol ? cols[(G.colors||[])[i]%5] : cssv("--ink-2");
    ctx.fill();
  });
}
function sizeCanvas(){
  const w=cv.clientWidth||1100, dpr=Math.min(window.devicePixelRatio||1,2);
  cv.width=Math.round(w*dpr); cv.height=Math.round(w*0.63*dpr); draw();
}
$("#b5").onclick=()=>{showCol=true;$("#b5").setAttribute("aria-pressed","true");
  $("#b0").setAttribute("aria-pressed","false");draw();};
$("#b0").onclick=()=>{showCol=false;$("#b0").setAttribute("aria-pressed","true");
  $("#b5").setAttribute("aria-pressed","false");draw();};
$("#be").onclick=()=>{showEdges=!showEdges;
  $("#be").setAttribute("aria-pressed",String(showEdges));draw();};
$("#legend").innerHTML=[0,1,2,3,4].map(i=>{
  const n=(G.colors||[]).filter(c=>c===i).length;
  return '<span class="sw"><span class="dot" style="background:var(--c'+i+')"></span>'+n+'</span>';
}).join("");
$("#gcap").textContent = (G.n||0)+" vertices · "+(G.m||0)+" exact unit edges";
$("#foot").innerHTML='Generated from the live catalog. Proof '+
  fmtB(V4.checked_bytes)+' · sha256 <span class="hash">'+
  String(V4.checked_sha256||'').slice(0,32)+'…</span> · checker <strong>'+
  (V4.checker_verdict||'—')+'</strong> · k=5 '+(V5.verdict||'—')+
  ', colouring independently re-checked against the exact edge list.';
addEventListener("resize",sizeCanvas);
matchMedia("(prefers-color-scheme:dark)").addEventListener("change",draw);
sizeCanvas();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
