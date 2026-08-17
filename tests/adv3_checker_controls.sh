#!/bin/bash
# ADVERSARY 3 - negative controls on OUR drat-trim build, plus our own solver proofs.
# A checker that says VERIFIED for everything is worthless; these show it discriminates.
ROOT=/home/user/CustomLLM
DT=$ROOT/vendor/drat-trim/drat-trim
KIS=$ROOT/vendor/kissat/build/kissat
CAD=$ROOT/vendor/cadical/build/cadical
CNF=$ROOT/data/CNP-SAT/cnf
PRF=$ROOT/data/CNP-SAT/proof
OUT=$ROOT/artifacts/adv3
RES=$OUT/control_results.tsv
: > $RES

rec () { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> $RES; echo "REC $1 rc=$2 wall=$3 -> $4"; }

dt () { # tag cnf proof
  s=$(date +%s.%N); nice -n 19 $DT "$2" "$3" -t 900 > $OUT/ctl_$1.log 2>&1; rc=$?; e=$(date +%s.%N)
  v=$(grep -Eo 's VERIFIED|s NOT VERIFIED|s TRIVIAL UNSAT' $OUT/ctl_$1.log | head -1); [ -z "$v" ] && v="(none)"
  rec "$1" "$rc" "$(echo "$e-$s"|bc)" "$v"
}

# C1: corrupt one literal of a core lemma in the middle of the 517 proof
python3 - <<'PY'
src="/home/user/CustomLLM/data/CNP-SAT/proof/517-4-sbp.drat"
L=open(src).read().split("\n")
# find a non-deletion lemma around line 12000 and flip the sign of its first literal
i=12000
while i < len(L) and (not L[i].strip() or L[i].startswith("d ")): i+=1
t=L[i].split(); t[0]=str(-int(t[0])); L[i]=" ".join(t)
open("/home/user/CustomLLM/artifacts/adv3/517_corrupt.drat","w").write("\n".join(L))
print("corrupted line",i)
PY
dt corrupt_517 $CNF/517-4-sbp.cnf $OUT/517_corrupt.drat

# C2: truncate the 517 proof (drop the final empty clause + last 500 lemmas)
python3 - <<'PY'
src="/home/user/CustomLLM/data/CNP-SAT/proof/517-4-sbp.drat"
L=[l for l in open(src).read().split("\n") if l.strip()]
open("/home/user/CustomLLM/artifacts/adv3/517_trunc.drat","w").write("\n".join(L[:-500])+"\n")
print("kept",len(L)-500,"of",len(L))
PY
dt trunc_517 $CNF/517-4-sbp.cnf $OUT/517_trunc.drat

# C3: swap proofs between two different graphs (517 proof against 553 sbp cnf)
dt crossgraph_517p_553f $CNF/553-4-sbp.cnf $PRF/517-4-sbp.drat

# C4: OUR OWN proofs from OUR OWN solvers on THEIR cnf -> verify with drat-trim
for g in 517 553 610 633 803 826 874; do
  f=$CNF/$g-4-sbp.cnf
  [ -f "$f" ] || f=$CNF/$g-4.cnf
  s=$(date +%s.%N); nice -n 19 $KIS --unsat "$f" $OUT/ours_kissat_$g.drat > $OUT/kissat_$g.log 2>&1; rc=$?; e=$(date +%s.%N)
  rec "kissat_$g($(basename $f))" "$rc" "$(echo "$e-$s"|bc)" "$(grep -Eo '^s .*' $OUT/kissat_$g.log|head -1)"
  dt ourproof_$g "$f" $OUT/ours_kissat_$g.drat
done

# C5: cadical independent solve on 826 / 874 (the two with NO published proof)
for g in 826 874; do
  s=$(date +%s.%N); nice -n 19 $CAD -q "$CNF/$g-4.cnf" $OUT/ours_cadical_$g.drat --no-binary > $OUT/cadical_$g.log 2>&1; rc=$?; e=$(date +%s.%N)
  rec "cadical_$g" "$rc" "$(echo "$e-$s"|bc)" "$(grep -Eo '^s .*' $OUT/cadical_$g.log|head -1)"
  dt cadicalproof_$g "$CNF/$g-4.cnf" $OUT/ours_cadical_$g.drat
done

echo CONTROLS DONE
