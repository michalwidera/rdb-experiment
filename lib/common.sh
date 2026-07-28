#!/bin/bash
# Wspolne funkcje dla start_supervisor.sh i worker/run_study.sh.
# Zrodlo tego pliku, nie uruchamiac bezposrednio.

log()  { printf '[%(%Y-%m-%d %H:%M:%S)T] %s\n' -1 "$*" >&2; }
die()  { log "BLAD: $*"; exit 1; }

# ssh do workera z rozsadnymi timeoutami; propaguje kod wyjscia polecenia.
#
# Nieinteraktywna sesja SSH NIE sourcuje ~/.bashrc (typowy guard "if not
# interactive, return" na jego poczatku) -- PATH do ~/.local/bin (ninja
# install) i aktywacja Python venv (conan) z .bashrc nigdy by sie nie
# zastosowaly. Odtwarzamy je tu jawnie zamiast na tym polegac.
ssh_worker() {
  local host="$1" port="$2"; shift 2
  local ssh_config="${RDB_SSH_CONFIG:-/dev/null}"
  local known_hosts_args=()
  if [ -n "${RDB_KNOWN_HOSTS_FILE:-}" ]; then
    known_hosts_args=(-o "UserKnownHostsFile=$RDB_KNOWN_HOSTS_FILE")
  fi
  ssh -F "$ssh_config" -p "$port" \
      "${known_hosts_args[@]}" \
      -o BatchMode=yes -o StrictHostKeyChecking=yes \
      -o ConnectTimeout=8 -o ServerAliveInterval=5 \
      -o ServerAliveCountMax=3 "$host" \
      "export PATH=\"\$HOME/.local/bin:\$PATH\"; [ -f \"\$HOME/.venv/bin/activate\" ] && source \"\$HOME/.venv/bin/activate\"; $*"
}

# Czeka az worker odpowie po SSH (po reboot). Timeout w sekundach.
#
# Sonda MUSI byc opakowana w 'timeout': ConnectTimeout bounduje wylacznie
# zestawienie TCP, a sesja nawiazana w oknie wczesnego rozruchu potrafi zawisnac
# po autoryzacji i nie wrocic nigdy. Bez tego cialo petli sie nie wykonuje, licznik
# nie rosnie i zadeklarowany timeout NIE wystrzeliwuje -- nadzorca stoi cicho
# w nieskonczonosc (zaobserwowane na czterech restartach z czterech, JOURNAL.md
# 2026-07-21). Z tego samego powodu liczymy czas zegarem, a nie sumowaniem sleepow:
# nieudana iteracja trwa tyle, ile sonda plus sleep, wiec licznik przyrostowy
# zawyzalby faktyczny timeout.
wait_for_worker() {
  local host="$1" port="$2" timeout_s="${3:-600}"
  local probe_timeout_s="${4:-15}" retry_sleep_s="${5:-10}"
  local ssh_config="${RDB_SSH_CONFIG:-/dev/null}"
  local known_hosts_args=()
  local start deadline
  if [ -n "${RDB_KNOWN_HOSTS_FILE:-}" ]; then
    known_hosts_args=(-o "UserKnownHostsFile=$RDB_KNOWN_HOSTS_FILE")
  fi
  start=$(date +%s)
  deadline=$((start + timeout_s))
  log "Czekam az $host:$port wroci po restarcie (timeout ${timeout_s}s)..."
  while ! timeout --kill-after=5s "${probe_timeout_s}s" ssh -F "$ssh_config" -p "$port" \
        "${known_hosts_args[@]}" \
        -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
        -o ServerAliveInterval=5 -o ServerAliveCountMax=3 "$host" true 2>/dev/null; do
    [ "$(date +%s)" -ge "$deadline" ] && die "$host nie odpowiedzial po ${timeout_s}s od restartu"
    sleep "$retry_sleep_s"
  done
  log "$host odpowiada po $(( $(date +%s) - start ))s."
  # Daj czas na dojscie sshd/uslug do stabilnego stanu po boot.
  sleep 15
}

validate_experiment_id() {
  local experiment_id="$1"
  [[ "$experiment_id" =~ ^[0-9]{8}_[a-z0-9][a-z0-9_-]*$ ]] || {
    log "BLAD: identyfikator eksperymentu musi miec postac YYYYMMDD_typ (otrzymano: $experiment_id)"
    return 1
  }
}

validate_results_root() {
  local results_root="$1"
  [[ "$results_root" =~ ^results_[0-9]{8}_[a-z0-9][a-z0-9_-]*$ ]] || {
    log "BLAD: katalog wynikow musi miec postac results_YYYYMMDD_typ (otrzymano: $results_root)"
    return 1
  }
}

validate_safe_absolute_path() {
  local path="$1" label="${2:-sciezka}"
  [[ "$path" =~ ^/[A-Za-z0-9._/-]+$ ]] &&
    [[ "$path" != *"//"* && "$path" != *"/../"* && "$path" != */.. &&
       "$path" != *"/./"* && "$path" != */. ]] || {
    log "BLAD: $label musi byc bezwzgledna, bezpieczna sciezka bez '..' (otrzymano: $path)"
    return 1
  }
}

validate_campaign_name() {
  local campaign="$1"
  [[ "$campaign" =~ ^(rate(_[a-z0-9_-]+)?|clients)$ ]] || {
    log "BLAD: nieprawidlowa nazwa kampanii: $campaign"
    return 1
  }
}

validate_git_branch() {
  local branch="$1" label="${2:-branch}"
  git check-ref-format --branch "$branch" >/dev/null 2>&1 || {
    log "BLAD: nieprawidlowa nazwa $label: $branch"
    return 1
  }
}

validate_ssh_host() {
  local host="$1"
  [[ "$host" =~ ^[A-Za-z0-9._:-]+$ ]] || {
    log "BLAD: nieprawidlowy host SSH: $host"
    return 1
  }
}

validate_worker_name() {
  local name="$1"
  [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
    log "BLAD: nieprawidlowa nazwa hosta workera: $name"
    return 1
  }
}

validate_ipv4() {
  local ip="$1" octet
  local -a octets
  IFS='.' read -r -a octets <<< "$ip"
  [ "${#octets[@]}" -eq 4 ] || return 1
  for octet in "${octets[@]}"; do
    [[ "$octet" =~ ^[0-9]+$ ]] && [ "$octet" -le 255 ] || return 1
  done
}

validate_worker_subnet() {
  local subnet="$1" network
  [[ "$subnet" =~ ^([0-9]{1,3}\.){3}0/24$ ]] || {
    log "BLAD: siec wykrywania workera musi miec postac IPv4.0/24 (otrzymano: $subnet)"
    return 1
  }
  network="${subnet%/24}"
  validate_ipv4 "$network" || {
    log "BLAD: nieprawidlowa siec IPv4: $subnet"
    return 1
  }
}

validate_host_key_fingerprint() {
  local fingerprint="$1"
  [[ "$fingerprint" =~ ^SHA256:[A-Za-z0-9+/]{43}$ ]] || {
    log "BLAD: fingerprint klucza hosta musi miec postac SHA256:<43 znaki>"
    return 1
  }
}

infer_worker_subnet() {
  local host="$1" ip="$1"
  if ! validate_ipv4 "$ip"; then
    ip=$(getent ahostsv4 "$host" 2>/dev/null | awk 'NR == 1 {print $1}')
  fi
  validate_ipv4 "$ip" || {
    log "BLAD: nie mozna wywnioskowac sieci /24 z adresu workera: $host"
    return 1
  }
  printf '%s.0/24\n' "${ip%.*}"
}

known_host_fingerprints() {
  local host="$1" port="$2" known_hosts="$3" query
  local queries=("$host" "[$host]:$port")
  [ -f "$known_hosts" ] || return 1
  for query in "${queries[@]}"; do
    ssh-keygen -F "$query" -f "$known_hosts" 2>/dev/null || true
  done |
    awk '!/^#/ && NF >= 3 {print $2, $3}' |
    ssh-keygen -lf - -E sha256 2>/dev/null |
    awk '{print $2}' |
    sort -u
}

filter_matching_host_keys() {
  local scanned_keys="$1" fingerprints="$2" matched_keys="$3"
  local host key_type key extra fingerprint
  : > "$matched_keys"
  while read -r host key_type key extra; do
    [ -n "${host:-}" ] && [ -n "${key_type:-}" ] && [ -n "${key:-}" ] || continue
    [ -z "${extra:-}" ] || continue
    fingerprint=$(printf '%s %s\n' "$key_type" "$key" |
      ssh-keygen -lf - -E sha256 2>/dev/null | awk '{print $2}') || continue
    if grep -qxF "$fingerprint" "$fingerprints"; then
      printf '%s %s %s\n' "$host" "$key_type" "$key" >> "$matched_keys"
    fi
  done < "$scanned_keys"
  [ -s "$matched_keys" ]
}

probe_worker_identity() {
  local host="$1" port="$2" expected_name="$3" code_repo="$4" experiment_repo="$5"
  ssh_worker "$host" "$port" "
    [ \"\$(hostname)\" = '$expected_name' ] &&
    [ -d '$code_repo/.git' ] &&
    [ -d '$experiment_repo/.git' ]
  " >/dev/null 2>&1
}

scan_worker_candidates() {
  local subnet="$1" port="$2" output_dir="$3"
  local network_prefix="${subnet%.0/24}" active=0 i
  mkdir -p "$output_dir"
  for i in $(seq 1 254); do
    (
      if timeout 1 nc -z -w 1 "$network_prefix.$i" "$port" >/dev/null 2>&1; then
        printf '%s\n' "$network_prefix.$i" > "$output_dir/$i"
      fi
    ) &
    active=$((active + 1))
    if [ "$active" -ge 32 ]; then
      wait -n || true
      active=$((active - 1))
    fi
  done
  wait
  for i in $(seq 1 254); do
    [ -f "$output_dir/$i" ] && cat "$output_dir/$i"
  done
}

# Ustawia RESOLVED_WORKER_HOST. Przy zmianie adresu tworzy tymczasowy plik
# known_hosts zawierajacy tylko klucze o uprzednio zaufanym fingerprintcie.
resolve_worker_host() {
  local host="$1" port="$2" expected_name="$3" subnet="$4" explicit_fingerprint="$5"
  local code_repo="$6" experiment_repo="$7"
  local known_hosts_source="${RDB_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"
  local discovery_dir fingerprints candidates_dir candidate scanned matched
  local -a matches=()

  RESOLVED_WORKER_HOST=""
  if probe_worker_identity "$host" "$port" "$expected_name" "$code_repo" "$experiment_repo"; then
    RESOLVED_WORKER_HOST="$host"
    log "Worker odpowiada pod dotychczasowym adresem: $host:$port"
    return 0
  fi

  [ -n "$subnet" ] || subnet=$(infer_worker_subnet "$host") || return 1
  validate_worker_subnet "$subnet" || return 1
  command -v nc >/dev/null || {
    log "BLAD: automatyczne wykrywanie workera wymaga programu nc"
    return 1
  }
  command -v ssh-keyscan >/dev/null && command -v ssh-keygen >/dev/null || {
    log "BLAD: automatyczne wykrywanie workera wymaga ssh-keyscan i ssh-keygen"
    return 1
  }

  discovery_dir=$(mktemp -d)
  WORKER_DISCOVERY_TMP="$discovery_dir"
  fingerprints="$discovery_dir/fingerprints"
  candidates_dir="$discovery_dir/candidates"
  if [ -n "$explicit_fingerprint" ]; then
    validate_host_key_fingerprint "$explicit_fingerprint" || return 1
    printf '%s\n' "$explicit_fingerprint" > "$fingerprints"
  else
    known_host_fingerprints "$host" "$port" "$known_hosts_source" > "$fingerprints" || true
    [ -s "$fingerprints" ] || {
      log "BLAD: brak zaufanego klucza SSH dla $host:$port; podaj --worker-host-key SHA256:..."
      return 1
    }
  fi

  log "Brak workera pod $host:$port; skanuje $subnet (port $port, maks. 254 hosty)..."
  while IFS= read -r candidate; do
    [ -n "$candidate" ] || continue
    scanned="$discovery_dir/keys_${candidate//./_}"
    matched="$discovery_dir/matched_${candidate//./_}"
    ssh-keyscan -T 2 -p "$port" "$candidate" > "$scanned" 2>/dev/null || true
    filter_matching_host_keys "$scanned" "$fingerprints" "$matched" || continue

    RDB_KNOWN_HOSTS_FILE="$matched"
    if probe_worker_identity "$candidate" "$port" "$expected_name" "$code_repo" "$experiment_repo"; then
      matches+=("$candidate")
      cp "$matched" "$discovery_dir/selected_known_hosts"
    fi
  done < <(scan_worker_candidates "$subnet" "$port" "$candidates_dir")

  [ "${#matches[@]}" -gt 0 ] || {
    log "BLAD: nie znaleziono zaufanego workera $expected_name w sieci $subnet"
    return 1
  }
  [ "${#matches[@]}" -eq 1 ] || {
    log "BLAD: znaleziono wiele hostow pasujacych do workera: ${matches[*]}"
    return 1
  }

  RESOLVED_WORKER_HOST="${matches[0]}"
  RDB_KNOWN_HOSTS_FILE="$discovery_dir/selected_known_hosts"
  log "Worker $expected_name odnaleziony pod adresem $RESOLVED_WORKER_HOST:$port; klucz SSH zweryfikowany."
}

require_disjoint_repositories() {
  local code_repo experiment_repo code_real experiment_real
  code_repo="$1"
  experiment_repo="$2"
  code_real=$(realpath "$code_repo") || return 1
  experiment_real=$(realpath "$experiment_repo") || return 1
  case "$experiment_real/" in
    "$code_real/"*) log "BLAD: repozytorium wynikow lezy wewnatrz repozytorium kodu"; return 1 ;;
  esac
  case "$code_real/" in
    "$experiment_real/"*) log "BLAD: repozytorium kodu lezy wewnatrz repozytorium wynikow"; return 1 ;;
  esac
}

validate_campaign_csv() {
  local csv="$1" kind="$2"
  local expected_header row study_id col2 col3 col4 extra count=0
  [ -f "$csv" ] || {
    log "BLAD: brak pliku konfiguracji: $csv"
    return 1
  }
  case "$kind" in
    rate) expected_header="study_id,rate_hz,clients,samples" ;;
    clients) expected_header="study_id,clients,samples" ;;
    *) log "BLAD: nieznany rodzaj kampanii: $kind"; return 1 ;;
  esac
  IFS= read -r row < "$csv"
  [ "$row" = "$expected_header" ] || {
    log "BLAD: nieprawidlowy naglowek $csv: $row"
    return 1
  }
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    count=$((count + 1))
    IFS=',' read -r study_id col2 col3 col4 extra <<< "$row"
    [ -z "${extra:-}" ] || {
      log "BLAD: za duzo kolumn w konfiguracji: $row"
      return 1
    }
    if [ "$kind" = "rate" ]; then
      [[ "$study_id" =~ ^[0-9]+$ && "$col2" =~ ^[0-9]+$ && "$col3" =~ ^[0-9]+$ && "$col4" =~ ^[0-9]+$ ]] || {
        log "BLAD: nieprawidlowy wiersz konfiguracji: $row"
        return 1
      }
    else
      [[ "$study_id" =~ ^[0-9]+$ && "$col2" =~ ^[0-9]+$ && "$col3" =~ ^[0-9]+$ && -z "$col4" ]] || {
        log "BLAD: nieprawidlowy wiersz konfiguracji: $row"
        return 1
      }
    fi
  done < <(tail -n +2 "$csv")
  [ "$count" -gt 0 ] || {
    log "BLAD: plik konfiguracji nie zawiera zadnego badania: $csv"
    return 1
  }
}

require_tmpfs() {
  local path="$1"
  local fs_type
  fs_type=$(findmnt -n -o FSTYPE --target "$path" 2>/dev/null) || {
    log "BLAD: nie mozna ustalic systemu plikow dla $path"
    return 1
  }
  [ "$fs_type" = "tmpfs" ] || {
    log "BLAD: $path musi byc tmpfs, wykryto: $fs_type"
    return 1
  }
}

verify_probe_binary() {
  local binary="$1"
  local actual expected
  [ -x "$binary" ] || {
    log "BLAD: brak wykonywalnej binarki xretractor: $binary"
    return 1
  }
  actual=$("$binary" --build-info 2>/dev/null) || {
    log "BLAD: $binary --build-info nie powiodlo sie"
    return 1
  }
  expected=$(printf '%s\n' \
    "RDB_OPT_DEDUP_SUBSTRATES=ON" \
    "RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON" \
    "RDB_OPT_COMMUTATIVE_ADD=ON" \
    "RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON" \
    "RDB_BENCH_PROBE=ON")
  [ "$actual" = "$expected" ] || {
    log "BLAD: zainstalowana binarka nie jest oczekiwanym buildem Release-Probe"
    printf '%s\n' "$actual" >&2
    return 1
  }
}

validate_probe_csv() {
  local csv="$1" samples="$2"
  local expected_rows actual_rows header
  [ -s "$csv" ] || {
    log "BLAD: brak danych sondy: $csv"
    return 1
  }
  IFS= read -r header < "$csv"
  [ "$header" = "iter,compute_ns,wake_lag_ns,e2e_ns" ] || {
    log "BLAD: nieoczekiwany naglowek sondy w $csv: $header"
    return 1
  }
  expected_rows=$((samples - 1))
  actual_rows=$(( $(wc -l < "$csv") - 1 ))
  [ "$actual_rows" -eq "$expected_rows" ] || {
    log "BLAD: sonda zawiera $actual_rows rekordow, oczekiwano $expected_rows dla samples=$samples"
    return 1
  }
}

wait_for_required_process() {
  local pid="$1" label="$2"
  local rc
  if wait "$pid"; then
    return 0
  else
    rc=$?
    log "BLAD: $label zakonczyl sie kodem $rc"
    return "$rc"
  fi
}

process_is_running() {
  local pid="$1" state
  state=$(ps -o stat= -p "$pid" 2>/dev/null) || return 1
  state="${state#"${state%%[![:space:]]*}"}"
  [[ "$state" != Z* ]]
}

# Pilnuje procesow wymaganych tak dlugo, jak dziala proces glowny.
# Argumenty po main_pid maja postac: etykieta pid etykieta pid ...
monitor_required_processes() {
  local main_pid="$1" label pid
  shift
  local required=("$@")
  [ $(( $# % 2 )) -eq 0 ] || {
    log "BLAD: monitor_required_processes wymaga par etykieta/pid"
    return 1
  }
  while process_is_running "$main_pid"; do
    set -- "${required[@]}"
    while [ $# -gt 0 ]; do
      label="$1"
      pid="$2"
      shift 2
      if ! process_is_running "$pid"; then
        log "BLAD: wymagany proces $label (pid $pid) zakonczyl sie przed procesem glownym"
        kill "$main_pid" 2>/dev/null || true
        return 1
      fi
    done
    sleep 1
  done
}

terminate_process() {
  local pid="$1" grace_s="${2:-5}"
  local deadline
  [ -n "$pid" ] || return 0
  kill "$pid" 2>/dev/null || true
  deadline=$((SECONDS + grace_s))
  while process_is_running "$pid" && [ "$SECONDS" -lt "$deadline" ]; do
    sleep 0.1
  done
  if process_is_running "$pid"; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  wait "$pid" 2>/dev/null || true
  ! kill -0 "$pid" 2>/dev/null
}

# Konczy wymagany proces po zakonczeniu procesu glownego i zachowuje jego
# wczesniejszy kod bledu. Domyka okno miedzy ostatnia iteracja monitora a
# zakonczeniem procesu glownego: dziecko, ktore zdazylo wtedy wyjsc z bledem,
# nie moze zostac potraktowane jak proces zatrzymany przez nadzorce.
finalize_required_process() {
  local pid="$1" label="$2" grace_s="${3:-5}"
  local term_sent=0 forced_kill=0 rc=0 deadline
  [ -n "$pid" ] || return 0

  if kill "$pid" 2>/dev/null; then
    term_sent=1
    deadline=$((SECONDS + grace_s))
    while process_is_running "$pid" && [ "$SECONDS" -lt "$deadline" ]; do
      sleep 0.1
    done
    if process_is_running "$pid"; then
      if kill -KILL "$pid" 2>/dev/null; then
        forced_kill=1
      fi
    fi
  fi
  if wait "$pid" 2>/dev/null; then
    rc=0
  else
    rc=$?
  fi
  if kill -0 "$pid" 2>/dev/null; then
    log "BLAD: nie udalo sie zatrzymac procesu $label (pid $pid)"
    return 1
  fi

  if [ "$forced_kill" -eq 1 ]; then
    log "BLAD: $label zignorowal SIGTERM i wymagal SIGKILL"
    return 1
  fi
  if [ "$term_sent" -eq 1 ] && { [ "$rc" -eq 0 ] || [ "$rc" -eq 143 ]; }; then
    return 0
  fi
  if [ "$term_sent" -eq 0 ] && [ "$rc" -eq 0 ]; then
    return 0
  fi

  log "BLAD: $label zakonczyl sie kodem $rc przed kontrolowanym zatrzymaniem"
  return "$rc"
}
