#!/bin/bash
# ADVERSARY 3 - CHECK A: verify Marijn Heule's published DRAT proofs with OUR drat-trim build.
# Each run: nice -n 19, wall-clocked, stdout+stderr captured.
ROOT=/home/user/CustomLLM
DT=$ROOT/vendor/drat-trim/drat-trim
CNF=$ROOT/data/CNP-SAT/cnf
PRF=$ROOT/data/CNP-SAT/proof
OUT=$ROOT/artifacts/adv3
mkdir -p $OUT
RES=$OUT/drat_results.tsv
: > $RES

run () {  # $1=tag $2=cnf $3=proof $4=timelimit
  tag=$1; cnfp=$2; prfp=$3; tl=$4
  log=$OUT/dt_$tag.log
  s=$(date +%s.%N)
  nice -n 19 $DT "$cnfp" "$prfp" -t "$tl" > "$log" 2>&1
  rc=$?
  e=$(date +%s.%N)
  wall=$(echo "$e - $s" | bc)
  verdict=$(grep -Eo 's VERIFIED|s NOT VERIFIED|s TRIVIAL UNSAT' "$log" | head -1)
  [ -z "$verdict" ] && verdict="(none)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$tag" "$(basename $cnfp)" "$(basename $prfp)" "$rc" "$wall" "$verdict" >> $RES
  echo "DONE $tag rc=$rc wall=$wall verdict=$verdict"
}

# --- primary: proof vs the -sbp CNF variant ---
run 517_sbp   $CNF/517-4-sbp.cnf   $PRF/517-4-sbp.drat   1800
run 553_sbp   $CNF/553-4-sbp.cnf   $PRF/553-4-sbp.drat   1800
run 610_sbp   $CNF/610-4-sbp.cnf   $PRF/610-4-sbp.drat   1800
run 633_sbp   $CNF/633-4-sbp.cnf   $PRF/633-4-sbp.drat   1800

# --- controls: same proof vs the PLAIN CNF (wrong pairing) ---
run 517_plain $CNF/517-4.cnf       $PRF/517-4-sbp.drat   900
run 553_plain $CNF/553-4.cnf       $PRF/553-4-sbp.drat   900
run 610_plain $CNF/610-4.cnf       $PRF/610-4-sbp.drat   900
run 633_plain $CNF/633-4.cnf       $PRF/633-4-sbp.drat   900

# --- 529: repo ships NO -sbp cnf; try plain + two reconstructions ---
run 529_plain $CNF/529-4.cnf       $PRF/529-4-sbp.drat   900
run 529_reconA $OUT/529-4-sbpA.cnf $PRF/529-4-sbp.drat   1800
run 529_reconB $OUT/529-4-sbpB.cnf $PRF/529-4-sbp.drat   1800

# --- 803: largest proof, run last ---
run 803_sbp   $CNF/803-4-sbp.cnf   $PRF/803-4-sbp.drat   7200
run 803_plain $CNF/803-4.cnf       $PRF/803-4-sbp.drat   1800

echo "ALL RUNS COMPLETE"
