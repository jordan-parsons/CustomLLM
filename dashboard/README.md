# Progress dashboard

Two ways to view it.

## 1. Published page (works from anywhere)
Regenerate and re-publish after any run:
```
python3 build_dashboard.py     # reads live state, writes dashboard/index.html
```
Then re-publish `dashboard/index.html` to the same artifact URL to refresh it.
The page is fully self-contained (data embedded, no external requests), so it keeps
working regardless of whether this container is alive.

## 2. Local server (for a live run on your own machine)
```
python3 serve_dashboard.py            # http://localhost:8000
python3 serve_dashboard.py --port 9000 --interval 30
```
This regenerates the HTML every `--interval` seconds from the catalog, so a running
search updates the page in place.

## What it reads
| source | feeds |
|---|---|
| `catalog/hn.sqlite` | leaderboard (verified proofs only) |
| `artifacts/heule510/verdict.k{4,5}.json` | proof sizes, hashes, checker verdicts |
| `artifacts/adv3/drat_results.tsv` | third-party proof cross-validation table |
| `artifacts/adv3/LRAT_MANIFEST.txt` | LRAT artifact hashes |
| `reports/ADVERSARY_*.md` | critical/major/confirmed/refuted counts |
| `catalog/search*.jsonl` | perturbation attempts, improvements, best |
| `data/pools/*.json` | ambient pool inventory |
| `dashboard/graph510.json` | drawing geometry + the verified 5-colouring |

`dashboard/graph510.json` is rebuilt by the exporter inside the data step; the
5-colouring it contains is checked by independent code against the exactly-derived
edge list before it is written, so the page never draws an unverified colouring.

Floating point appears in this directory ONLY as drawing geometry. It decides
nothing about the mathematics.
