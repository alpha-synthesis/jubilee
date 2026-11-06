#!/usr/bin/env bash
# Reruns on the 48-core server: paired campaign with the cash reward,
# then the archived grid on generator version 2 (20-seed cells, 5-seed cells).
#
# Layout expected: <workspace>/repo (this repository, this script inside it at
# scripts/rerun_20261106/ or outputs/rerun_20261106/) and <workspace>/venv
# (its Python at venv/bin/python). Override with WORKSPACE=... and PYTHON=...;
# PROTO_DIR=... and OUT_DIR=... point a dry run at tiny protocols elsewhere.
# Run inside tmux, e.g.:
#   tmux new -d -s rerun "bash repo/scripts/rerun_20261106/launch_rerun.sh > rerun.log 2>&1"
#
# Per protocol, in order: plan -> simulate (40 workers, 1 BLAS thread each) ->
# estimate (11 workers, 4 threads each; both rewards) -> aggregate (score and
# cash) -> DM+ from the extracts. Every step's exit code goes to
# <D>/exit_codes.txt; a DONE_<name> marker (or FAILED_<name>) is written in
# outputs/rerun_20261106/ with the codes inside. Nothing is ever deleted:
# logs are appended, the drivers skip finished jobs, so a relaunch resumes.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WORKSPACE="${WORKSPACE:-$(dirname "$REPO")}"
PY="${PYTHON:-$WORKSPACE/venv/bin/python}"
PROTO_DIR="${PROTO_DIR:-$REPO/scripts/rerun_20261106}"
OUT="${OUT_DIR:-$REPO/outputs/rerun_20261106}"
SIM_WORKERS="${SIM_WORKERS:-40}"
EST_WORKERS="${EST_WORKERS:-11}"
EST_THREADS="${EST_THREADS:-4}"
# Which protocols this instance runs, as name:file pairs; several instances with
# disjoint lists and smaller worker counts can share the server concurrently.
PROTOCOLS="${PROTOCOLS:-paired:paired_cash.json grid20:grid_v2_20seeds.json grid5:grid_v2_5seeds.json}"
TIME=/usr/bin/time

cd "$REPO" || exit 1
mkdir -p "$OUT"
stamp() { date +%FT%T%z; }
log() { echo "[$(stamp)] $*"; }

if [ ! -x "$PY" ]; then
  log "python not found at $PY"; exit 1
fi
{
  echo "launched $(stamp)"; echo "python $PY"; git rev-parse HEAD 2>/dev/null
  git status --porcelain 2>/dev/null | head -50; "$PY" --version; nproc
} >> "$OUT/launch_state.txt"
if "$PY" -c "import matplotlib" 2>/dev/null; then FIGURES="--figures"; else FIGURES=""; fi

run_protocol() {
  local name="$1" proto_file="$2"
  local D="$OUT/$name" P="$PROTO_DIR/$proto_file"
  mkdir -p "$D"
  cp -n "$P" "$D/protocol.json" 2>/dev/null || true
  local codes="$D/exit_codes.txt" fail=0 rc
  log "$name: plan"
  "$PY" scripts/tmlr_campaign.py plan --protocol "$P" > "$D/plan.json" 2>> "$D/plan.err"
  rc=$?; echo "plan $rc $(stamp)" >> "$codes"; [ $rc -ne 0 ] && fail=1

  log "$name: simulate ($SIM_WORKERS workers)"
  export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
  $TIME -v "$PY" scripts/tmlr_campaign.py simulate --protocol "$P" --workers "$SIM_WORKERS" \
    >> "$D/simulate.out" 2>> "$D/simulate.err"
  rc=$?; echo "simulate $rc $(stamp)" >> "$codes"; [ $rc -ne 0 ] && fail=1
  local sim_failed
  sim_failed=$(grep -c '"ok": false' "$D/simulate.out" 2>/dev/null || true)
  echo "simulate_jobs_failed ${sim_failed:-0} $(stamp)" >> "$codes"
  [ "${sim_failed:-0}" != "0" ] && fail=1

  log "$name: estimate ($EST_WORKERS workers, $EST_THREADS threads each)"
  export OMP_NUM_THREADS=$EST_THREADS OPENBLAS_NUM_THREADS=$EST_THREADS MKL_NUM_THREADS=$EST_THREADS
  $TIME -v "$PY" scripts/tmlr_campaign.py estimate --protocol "$P" --workers "$EST_WORKERS" \
    >> "$D/estimate.out" 2>> "$D/estimate.err"
  rc=$?; echo "estimate $rc $(stamp)" >> "$codes"; [ $rc -ne 0 ] && fail=1
  local est_failed
  est_failed=$(grep -c '"ok": false' "$D/estimate.out" 2>/dev/null || true)
  echo "estimate_runs_failed ${est_failed:-0} $(stamp)" >> "$codes"
  [ "${est_failed:-0}" != "0" ] && fail=1
  "$PY" scripts/tmlr_campaign.py status --protocol "$P" > "$D/status.json" 2>> "$D/estimate.err"

  local reward
  for reward in score cash; do
    log "$name: aggregate ($reward)"
    "$PY" scripts/tmlr_aggregate.py --protocol "$P" --dest "$D/aggregate_$reward" \
      --reward "$reward" --allow-missing $FIGURES \
      >> "$D/aggregate_$reward.out" 2>> "$D/aggregate_$reward.err"
    rc=$?; echo "aggregate_$reward $rc $(stamp)" >> "$codes"; [ $rc -ne 0 ] && fail=1
    local missing
    missing=$(($(wc -l < "$D/aggregate_$reward/missing_runs.csv" 2>/dev/null || echo 1) - 1))
    echo "aggregate_${reward}_missing_runs $missing $(stamp)" >> "$codes"
    [ "$missing" -gt 0 ] && fail=1
  done

  log "$name: DM+ from the extracts"
  export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
  $TIME -v "$PY" scripts/tmlr_evidence/dm_plus_from_extracts.py --protocol "$P" \
    --dest "$D/dm_plus" --workers "$EST_WORKERS" >> "$D/dm_plus.out" 2>> "$D/dm_plus.err"
  rc=$?; echo "dm_plus $rc $(stamp)" >> "$codes"; [ $rc -ne 0 ] && fail=1

  if [ $fail -eq 0 ]; then
    cp "$codes" "$OUT/DONE_$name"; log "$name: DONE"
  else
    cp "$codes" "$OUT/FAILED_$name"; log "$name: FAILED (see $codes)"
  fi
  return $fail
}

for item in $PROTOCOLS; do
  run_protocol "${item%%:*}" "${item#*:}"
done
log "protocols finished: $PROTOCOLS"
ls "$OUT"/DONE_* "$OUT"/FAILED_* 2>/dev/null
