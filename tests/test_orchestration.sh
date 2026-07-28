#!/bin/bash
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TEST_DIR/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$REPO_ROOT/lib/common.sh"

failures=0
checks=0

expect_success() {
  local name="$1"
  shift
  checks=$((checks + 1))
  if ! "$@" >/dev/null 2>&1; then
    printf 'FAIL: %s (oczekiwano sukcesu)\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

expect_failure() {
  local name="$1"
  shift
  checks=$((checks + 1))
  if "$@" >/dev/null 2>&1; then
    printf 'FAIL: %s (oczekiwano bledu)\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

assert_no_code_repo_writes() {
  ! grep -Eq 'git -C "\$CODE_REPO" (add|commit|push)' "$REPO_ROOT/worker/run_study.sh"
}

assert_results_use_experiment_repo() {
  grep -q 'RESULTS_DIR="\$EXPERIMENT_REPO/' "$REPO_ROOT/worker/run_study.sh"
}

assert_no_rotation() {
  ! grep -R -E 'rotated/[A-Za-z0-9]|rotacja poprzednich wynikow' \
    "$REPO_ROOT/start_supervisor.sh" "$REPO_ROOT/worker/run_study.sh"
}

assert_release_probe_install() {
  grep -q "scripts/buildrdb.sh conan ninja probe" "$REPO_ROOT/start_supervisor.sh" &&
    grep -q "cmake --install build/Release-Probe" "$REPO_ROOT/start_supervisor.sh" &&
    ! grep -q "cmake --install build/Release[^-]" "$REPO_ROOT/start_supervisor.sh"
}

assert_worker_discovery_wired() {
  grep -q "resolve_worker_host" "$REPO_ROOT/start_supervisor.sh" &&
    grep -q -- "--worker-subnet" "$REPO_ROOT/start_supervisor.sh" &&
    grep -q -- "--worker-host-key" "$REPO_ROOT/start_supervisor.sh"
}

assert_inferred_subnet() {
  [ "$(infer_worker_subnet 192.168.88.21)" = "192.168.88.0/24" ]
}

assert_matching_host_key_filter() {
  filter_matching_host_keys \
    "$tmp_dir/scanned_keys" "$tmp_dir/trusted_fingerprints" "$tmp_dir/matched_keys" &&
    [ "$(wc -l < "$tmp_dir/matched_keys")" -eq 1 ] &&
    grep -qF "$trusted_key" "$tmp_dir/matched_keys"
}

assert_current_worker_resolution() {
  (
    PATH="$tmp_dir/fake_ssh:$PATH"
    unset RDB_KNOWN_HOSTS_FILE
    RESOLVED_WORKER_HOST=""
    resolve_worker_host \
      192.0.2.21 22 pi400 "" "" \
      /home/michal/retractordb /home/michal/rdb-experiment
    [ "$RESOLVED_WORKER_HOST" = "192.0.2.21" ]
  )
}

assert_wait_timeout() {
  (
    PATH="$tmp_dir/hanging_ssh:$PATH"
    RDB_TIMEOUT_PID_FILE="$tmp_dir/timeout_pid"
    export RDB_TIMEOUT_PID_FILE
    wait_for_worker unavailable 22 0 1 0
  )
}

assert_process_gone() {
  local pid="$1"
  ! kill -0 "$pid" 2>/dev/null
}

assert_timed_out_ssh_cleaned() {
  local pid
  [ -s "$tmp_dir/timeout_pid" ] || return 1
  pid=$(cat "$tmp_dir/timeout_pid")
  assert_process_gone "$pid"
}

assert_child_failure_at_main_exit() {
  local main_pid dependency_pid
  (exit 0) &
  main_pid=$!
  (exit 9) &
  dependency_pid=$!
  sleep 0.1
  wait_for_required_process "$main_pid" main || return 1
  monitor_required_processes "$main_pid" dependency "$dependency_pid" || return 1
  finalize_required_process "$dependency_pid" dependency
}

assert_stubborn_child_cleanup() {
  bash -c 'trap "" TERM; exec sleep 30' &
  stubborn_pid=$!
  sleep 0.1
  finalize_required_process "$stubborn_pid" stubborn-child 1
}

assert_legacy_blocked() {
  local script="$1" rc
  bash "$script" >/dev/null 2>&1
  rc=$?
  [ "$rc" -eq 2 ]
}

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

mkdir -p "$tmp_dir/hanging_ssh"
cat > "$tmp_dir/hanging_ssh/ssh" <<'EOF'
#!/bin/bash
printf '%s\n' "$$" > "$RDB_TIMEOUT_PID_FILE"
exec sleep 30
EOF
chmod +x "$tmp_dir/hanging_ssh/ssh"

cat > "$tmp_dir/probe-good" <<'EOF'
#!/bin/bash
printf '%s\n' \
  RDB_OPT_DEDUP_SUBSTRATES=ON \
  RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON \
  RDB_OPT_COMMUTATIVE_ADD=ON \
  RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON \
  RDB_BENCH_PROBE=ON
EOF
cat > "$tmp_dir/probe-bad" <<'EOF'
#!/bin/bash
printf '%s\n' RDB_BENCH_PROBE=OFF
EOF
chmod +x "$tmp_dir/probe-good" "$tmp_dir/probe-bad"

mkdir -p "$tmp_dir/fake_ssh"
cat > "$tmp_dir/fake_ssh/ssh" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$tmp_dir/fake_ssh/ssh"

ssh-keygen -q -t ed25519 -N "" -f "$tmp_dir/trusted_key"
ssh-keygen -q -t ed25519 -N "" -f "$tmp_dir/other_key"
trusted_key=$(awk '{print $1, $2}' "$tmp_dir/trusted_key.pub")
other_key=$(awk '{print $1, $2}' "$tmp_dir/other_key.pub")
trusted_fingerprint=$(ssh-keygen -lf "$tmp_dir/trusted_key.pub" -E sha256 | awk '{print $2}')
printf '%s\n' "$trusted_fingerprint" > "$tmp_dir/trusted_fingerprints"
{
  printf '192.0.2.21 %s\n' "$trusted_key"
  printf '192.0.2.21 %s\n' "$other_key"
} > "$tmp_dir/scanned_keys"
printf '192.0.2.21 %s\n' "$trusted_key" > "$tmp_dir/known_hosts"

cat > "$tmp_dir/probe.csv" <<'EOF'
iter,compute_ns,wake_lag_ns,e2e_ns
0,10,20,30
1,10,20,30
2,10,20,30
EOF
cat > "$tmp_dir/rate.csv" <<'EOF'
study_id,rate_hz,clients,samples
1,360,1,20000
EOF
cat > "$tmp_dir/clients.csv" <<'EOF'
study_id,clients,samples
1,1,20000
EOF
cat > "$tmp_dir/empty.csv" <<'EOF'
study_id,rate_hz,clients,samples
EOF
cat > "$tmp_dir/malformed.csv" <<'EOF'
study_id,rate_hz,clients,samples
1,fast,1,20000
EOF

expect_success "poprawny experiment-id" validate_experiment_id 20260728_performance
expect_failure "experiment-id bez typu" validate_experiment_id 20260728
expect_success "poprawny katalog wynikow" validate_results_root results_20260728_performance
expect_failure "katalog przejsciowy results" validate_results_root results
expect_success "bezpieczna sciezka bezwzgledna" validate_safe_absolute_path /home/michal/rdb-experiment repo
expect_failure "sciezka z przejsciem do rodzica" validate_safe_absolute_path /home/michal/../retractordb repo
expect_success "poprawna kampania wariantowa" validate_campaign_name rate_dense
expect_failure "kampania z metaznakami" validate_campaign_name "rate';touch_x"
expect_success "poprawny branch wynikow" validate_git_branch experiment/20260728_performance branch
expect_failure "branch wygladajacy jak opcja" validate_git_branch --force branch
expect_success "poprawny adres workera" validate_ssh_host 192.168.88.21
expect_failure "host z metaznakami" validate_ssh_host "worker;false"
expect_success "poprawna nazwa workera" validate_worker_name pi400
expect_failure "nazwa workera z metaznakami" validate_worker_name "pi400;false"
expect_success "poprawny adres IPv4" validate_ipv4 192.168.88.21
expect_failure "IPv4 z oktetem poza zakresem" validate_ipv4 192.168.88.999
expect_success "poprawna siec skanu /24" validate_worker_subnet 192.168.88.0/24
expect_failure "zbyt szeroka siec skanu" validate_worker_subnet 192.168.0.0/16
expect_success "wyprowadzenie sieci /24 z IP" assert_inferred_subnet
expect_success "poprawny fingerprint SSH" validate_host_key_fingerprint "$trusted_fingerprint"
expect_failure "nieprawidlowy fingerprint SSH" validate_host_key_fingerprint SHA256:short
expect_success "odczyt fingerprintu z known_hosts" \
  grep -qxF "$trusted_fingerprint" <(
    known_host_fingerprints 192.0.2.21 22 "$tmp_dir/known_hosts"
  )
expect_success "filtrowanie tylko zaufanego klucza hosta" assert_matching_host_key_filter
expect_success "brak skanu, gdy dotychczasowy adres odpowiada" assert_current_worker_resolution
mkdir -p "$tmp_dir/code/.git" "$tmp_dir/experiment/.git" "$tmp_dir/code/nested/.git"
expect_success "repozytoria sa rozlaczne" require_disjoint_repositories "$tmp_dir/code" "$tmp_dir/experiment"
expect_failure "repozytorium wynikow wewnatrz kodu" require_disjoint_repositories "$tmp_dir/code" "$tmp_dir/code/nested"
expect_success "/dev/shm jest tmpfs" require_tmpfs /dev/shm
expect_success "build Release-Probe" verify_probe_binary "$tmp_dir/probe-good"
expect_failure "build bez sondy" verify_probe_binary "$tmp_dir/probe-bad"
expect_success "pelny CSV sondy" validate_probe_csv "$tmp_dir/probe.csv" 4
expect_failure "nieoczekiwana liczba rekordow sondy" validate_probe_csv "$tmp_dir/probe.csv" 5
expect_success "poprawna kampania rate" validate_campaign_csv "$tmp_dir/rate.csv" rate
expect_success "poprawna kampania clients" validate_campaign_csv "$tmp_dir/clients.csv" clients
expect_failure "pusta lista badan" validate_campaign_csv "$tmp_dir/empty.csv" rate
expect_failure "bledny wiersz kampanii" validate_campaign_csv "$tmp_dir/malformed.csv" rate
expect_failure "osiagalny timeout oczekiwania na worker" assert_wait_timeout
expect_success "timeout sprzata zawieszona sonde SSH" assert_timed_out_ssh_cleaned

(exit 0) &
pid=$!
expect_success "sukces procesu dziecka" wait_for_required_process "$pid" child-ok
(exit 7) &
pid=$!
expect_failure "blad procesu dziecka" wait_for_required_process "$pid" child-fail
expect_success "bledny proces dziecka zostal zebrany" assert_process_gone "$pid"
expect_failure "blad dziecka przy koncu procesu glownego" assert_child_failure_at_main_exit
expect_failure "SIGKILL po zignorowaniu SIGTERM" assert_stubborn_child_cleanup
expect_success "oporny proces dziecka zostal zebrany" assert_process_gone "$stubborn_pid"
sleep 30 &
main_pid=$!
sleep 30 &
dependency_pid=$!
monitor_required_processes "$main_pid" dependency "$dependency_pid" &
monitor_assertion_pid=$!
sleep 0.1
terminate_process "$main_pid"
expect_success "zakonczenie monitora po procesie glownym" \
  wait_for_required_process "$monitor_assertion_pid" monitor
terminate_process "$dependency_pid"
sleep 30 &
main_pid=$!
(exit 9) &
dependency_pid=$!
expect_failure "monitor wykrywa przedwczesny blad zaleznosci" \
  monitor_required_processes "$main_pid" dependency "$dependency_pid"
expect_success "monitor zatrzymuje proces glowny po bledzie zaleznosci" \
  terminate_process "$main_pid"
sleep 30 &
pid=$!
expect_success "sprzatanie procesu dziecka" finalize_required_process "$pid" child-cleanup

expect_success "brak git add/commit/push w repo kodu" assert_no_code_repo_writes
expect_success "wyniki zakorzenione w rdb-experiment" assert_results_use_experiment_repo
expect_success "brak rotacji" assert_no_rotation
expect_success "build i instalacja tylko z Release-Probe" assert_release_probe_install
expect_success "wykrywanie workera podlaczone do nadzorcy" assert_worker_discovery_wired
expect_failure "nadzorca odrzuca zly experiment-id" \
  "$REPO_ROOT/start_supervisor.sh" rate --experiment-id invalid
expect_failure "worker wymaga pelnego kontraktu argumentow" \
  "$REPO_ROOT/worker/run_study.sh"

for legacy in \
  "$REPO_ROOT/start_40ms_phase0.sh" \
  "$REPO_ROOT/worker/run_40ms_phase0.sh" \
  "$REPO_ROOT/worker/run_40ms_phase2.sh" \
  "$REPO_ROOT/worker/run_exactness.sh" \
  "$REPO_ROOT/worker/run_fir_contrast.sh" \
  "$REPO_ROOT/worker/run_flink_baseline.sh" \
  "$REPO_ROOT/worker/run_flink_pantompkins.sh" \
  "$REPO_ROOT/worker/run_numpy_baseline.sh"; do
  expect_success "historyczny skrypt zablokowany: ${legacy##*/}" assert_legacy_blocked "$legacy"
done

if [ "$failures" -ne 0 ]; then
  printf '%d/%d kontroli nie przeszlo\n' "$failures" "$checks" >&2
  exit 1
fi
printf 'OK: %d kontroli orkiestracji\n' "$checks"
