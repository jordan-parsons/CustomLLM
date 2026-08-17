#!/bin/sh
# Snapshot live search telemetry into a committed, timestamped record.
# The live jsonl/log files are gitignored because a running search rewrites them
# continuously; this captures a stable point-in-time copy worth keeping.
set -e
cd /home/user/CustomLLM
mkdir -p catalog/snapshots
TS=$(date -u +%Y%m%dT%H%M%SZ)
for f in catalog/search*.jsonl catalog/search*.log; do
  [ -f "$f" ] && cp "$f" "catalog/snapshots/$TS-$(basename $f)" || true
done
python3 - <<'PY'
import json, glob, os, re
rows = []
for f in glob.glob('catalog/search*.jsonl'):
    for l in open(f):
        try: rows.append(json.loads(l))
        except Exception: pass
att = [r for r in rows if 'result_n' in r]
imp = [r for r in rows if r.get('IMPROVED')]
tri = cb = fp = calls = done = 0
for lg in glob.glob('catalog/search*.log'):
    for line in open(lg):
        m = re.search(r'triaged=(\d+) core_beat=(\d+) full=(\d+) imp=(\d+) calls=(\d+)', line)
        if m:
            done += 1; tri += int(m.group(1)); cb += int(m.group(2))
            fp += int(m.group(3)); calls += int(m.group(5))
summary = {
  'workers_finished': done, 'perturbations_triaged': tri,
  'cores_beating_incumbent': cb, 'full_deletion_passes': fp,
  'search_solver_calls': calls, 'improvements_below_510': len(imp),
  'full_pass_results': sorted(r['result_n'] for r in att),
  'best_verified': min([r['n'] for r in rows if r.get('n')] or [510]),
}
json.dump(summary, open('catalog/SEARCH_SUMMARY.json','w'), indent=1)
print(json.dumps(summary, indent=1)[:900])
PY
