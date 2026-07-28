#!/bin/bash
# Uruchamiane na maszynie nadzorcy z samodzielnego repozytorium rdb-experiment.
# Repozytorium kodu RetractorDB i repozytorium wynikow sa obslugiwane osobno.
#
# Usage:
#   ./start_supervisor.sh rate [opcje]
#   ./start_supervisor.sh rate_dense [opcje]
#   ./start_supervisor.sh clients --rate-hz N [opcje]
#
# Najwazniejsze opcje:
#   --experiment-id ID          YYYYMMDD_typ; wyniki trafia do results_ID
#   --experiment-branch BRANCH  branch w rdb-experiment (domyslnie experiment/ID)
#   --code-branch BRANCH        branch kodu RetractorDB (domyslnie master)
#   --code-repo PATH            lokalne repo kodu (domyslnie ../retractordb)
#   --worker HOST               adres/host SSH workera (domyslnie worker)
#   --worker-port PORT          port SSH workera (domyslnie 22)
#   --worker-name NAME          oczekiwany hostname workera (domyslnie pi400)
#   --worker-subnet CIDR        siec awaryjnego skanu, wylacznie IPv4 /24
#   --worker-host-key SHA256:.. fingerprint SSH, gdy brak starego wpisu known_hosts
#   --no-worker-discovery       nie skanuj sieci po utracie dotychczasowego adresu
#   --worker-code-repo PATH     repo kodu na workerze (domyslnie /home/michal/retractordb)
#   --worker-experiment-repo P  repo wynikow na workerze (domyslnie /home/michal/rdb-experiment)
#   --skip-build                pomin build, ale nadal wymagaj zweryfikowanej binarki Release-Probe
#   --reboot-timeout SEK        czas oczekiwania na powrot workera (domyslnie 600)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_REPO="$SCRIPT_DIR"
# shellcheck source=lib/common.sh
source "$EXPERIMENT_REPO/lib/common.sh"

[ $# -ge 1 ] || die "Usage: $0 <rate|rate_dense|clients> [opcje]"
CAMPAIGN="$1"
shift
case "$CAMPAIGN" in
  rate|rate_*) CAMPAIGN_KIND="rate" ;;
  clients) CAMPAIGN_KIND="clients" ;;
  *) die "campaign musi byc 'rate', 'rate_<wariant>' albo 'clients'" ;;
esac
validate_campaign_name "$CAMPAIGN" || exit 1

CODE_REPO="$(cd "$EXPERIMENT_REPO/../retractordb" 2>/dev/null && pwd || true)"
WORKER_HOST="worker"
WORKER_PORT=22
WORKER_NAME="pi400"
WORKER_SUBNET=""
WORKER_HOST_KEY=""
WORKER_DISCOVERY=1
WORKER_DISCOVERY_TMP=""
WORKER_CODE_REPO="/home/michal/retractordb"
WORKER_EXPERIMENT_REPO="/home/michal/rdb-experiment"
EXPERIMENT_ID="$(date +%Y%m%d)_performance"
EXPERIMENT_BRANCH=""
CODE_BRANCH="master"
SINK="null"
RATE_HZ=360
SKIP_BUILD=0
REBOOT_TIMEOUT=600

while [ $# -gt 0 ]; do
  case "$1" in
    --experiment-id) EXPERIMENT_ID="$2"; shift 2 ;;
    --experiment-branch|--branch) EXPERIMENT_BRANCH="$2"; shift 2 ;;
    --code-branch) CODE_BRANCH="$2"; shift 2 ;;
    --code-repo) CODE_REPO="$2"; shift 2 ;;
    --worker) WORKER_HOST="$2"; shift 2 ;;
    --worker-port) WORKER_PORT="$2"; shift 2 ;;
    --worker-name) WORKER_NAME="$2"; shift 2 ;;
    --worker-subnet) WORKER_SUBNET="$2"; shift 2 ;;
    --worker-host-key) WORKER_HOST_KEY="$2"; shift 2 ;;
    --no-worker-discovery) WORKER_DISCOVERY=0; shift ;;
    --worker-code-repo|--worker-repo) WORKER_CODE_REPO="$2"; shift 2 ;;
    --worker-experiment-repo) WORKER_EXPERIMENT_REPO="$2"; shift 2 ;;
    --rate-hz) RATE_HZ="$2"; shift 2 ;;
    --sink) SINK="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --reboot-timeout) REBOOT_TIMEOUT="$2"; shift 2 ;;
    *) die "Nieznana opcja: $1" ;;
  esac
done

validate_experiment_id "$EXPERIMENT_ID" || exit 1
RESULTS_ROOT="results_${EXPERIMENT_ID}"
validate_results_root "$RESULTS_ROOT" || exit 1
EXPERIMENT_BRANCH="${EXPERIMENT_BRANCH:-experiment/$EXPERIMENT_ID}"

validate_git_branch "$EXPERIMENT_BRANCH" "brancha wynikow" || exit 1
validate_git_branch "$CODE_BRANCH" "brancha kodu" || exit 1
validate_ssh_host "$WORKER_HOST" || exit 1
validate_worker_name "$WORKER_NAME" || exit 1
[ -z "$WORKER_SUBNET" ] || validate_worker_subnet "$WORKER_SUBNET" || exit 1
[ -z "$WORKER_HOST_KEY" ] || validate_host_key_fingerprint "$WORKER_HOST_KEY" || exit 1
validate_safe_absolute_path "$WORKER_CODE_REPO" "repozytorium kodu workera" || exit 1
validate_safe_absolute_path "$WORKER_EXPERIMENT_REPO" "repozytorium wynikow workera" || exit 1
[[ "$WORKER_PORT" =~ ^[0-9]+$ ]] &&
  [ "$WORKER_PORT" -ge 1 ] && [ "$WORKER_PORT" -le 65535 ] ||
  die "Port SSH musi byc liczba z zakresu 1-65535"
[[ "$RATE_HZ" =~ ^[0-9]+$ ]] && [ "$RATE_HZ" -gt 0 ] || die "rate-hz musi byc dodatnia liczba calkowita"
[[ "$REBOOT_TIMEOUT" =~ ^[0-9]+$ ]] && [ "$REBOOT_TIMEOUT" -gt 0 ] ||
  die "reboot-timeout musi byc dodatnia liczba calkowita"
[ "$SINK" = "null" ] || [ "$SINK" = "nc" ] || die "sink musi byc 'null' albo 'nc'"
[ -d "$EXPERIMENT_REPO/.git" ] || die "Brak repozytorium rdb-experiment: $EXPERIMENT_REPO"
[ -n "$CODE_REPO" ] && [ -d "$CODE_REPO/.git" ] || die "Brak repozytorium kodu: $CODE_REPO"
require_disjoint_repositories "$CODE_REPO" "$EXPERIMENT_REPO" || exit 1

CONFIG_CSV="$EXPERIMENT_REPO/config/campaign_${CAMPAIGN}.csv"
validate_campaign_csv "$CONFIG_CSV" "$CAMPAIGN_KIND" || exit 1
mapfile -t ROWS < <(tail -n +2 "$CONFIG_CSV" | sed '/^[[:space:]]*$/d')
TOTAL=${#ROWS[@]}

cleanup_supervisor() {
  if [ -n "$WORKER_DISCOVERY_TMP" ] && [ -d "$WORKER_DISCOVERY_TMP" ]; then
    rm -rf -- "$WORKER_DISCOVERY_TMP"
  fi
}
trap cleanup_supervisor EXIT

REQUESTED_WORKER_HOST="$WORKER_HOST"
if [ "$WORKER_DISCOVERY" -eq 1 ]; then
  resolve_worker_host \
    "$WORKER_HOST" "$WORKER_PORT" "$WORKER_NAME" "$WORKER_SUBNET" "$WORKER_HOST_KEY" \
    "$WORKER_CODE_REPO" "$WORKER_EXPERIMENT_REPO" ||
    die "Nie mozna odnalezc i zweryfikowac workera"
  WORKER_HOST="$RESOLVED_WORKER_HOST"
fi

log "=== Eksperyment $EXPERIMENT_ID, kampania $CAMPAIGN ==="
log "Kod: $CODE_REPO @ $CODE_BRANCH"
log "Wyniki: $EXPERIMENT_REPO/$RESULTS_ROOT na branchu $EXPERIMENT_BRANCH"
log "Worker: $WORKER_HOST:$WORKER_PORT"

# Kod jest tylko zrodlem binarki. Wyniki nigdy nie sa commitowane do tego repozytorium.
[ -z "$(git -C "$CODE_REPO" status --short)" ] || die "Repozytorium kodu na nadzorcy nie jest czyste"
[ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] ||
  die "Repozytorium rdb-experiment na nadzorcy nie jest czyste"
git -C "$CODE_REPO" fetch origin "$CODE_BRANCH" --quiet
git -C "$CODE_REPO" show-ref --verify --quiet "refs/remotes/origin/$CODE_BRANCH" ||
  die "Brak origin/$CODE_BRANCH w repozytorium kodu"
CODE_COMMIT=$(git -C "$CODE_REPO" rev-parse "origin/$CODE_BRANCH")

# Najpierw sprawdzamy worker. Brak drugiego repozytorium lub brudny stan nie
# moze pozostawic nawet przygotowawczego commita/brancha wynikow.
log "Wstepny preflight dwóch repozytoriów na workerze..."
ssh_worker "$WORKER_HOST" "$WORKER_PORT" "
  set -e
  [ -d '$WORKER_CODE_REPO/.git' ] || { echo 'BLAD: brak repozytorium kodu: $WORKER_CODE_REPO' >&2; exit 1; }
  [ -d '$WORKER_EXPERIMENT_REPO/.git' ] || { echo 'BLAD: brak repozytorium wynikow: $WORKER_EXPERIMENT_REPO' >&2; exit 1; }
  code_real=\$(realpath '$WORKER_CODE_REPO')
  experiment_real=\$(realpath '$WORKER_EXPERIMENT_REPO')
  case \"\$experiment_real/\" in \"\$code_real/\"*) echo 'BLAD: repozytorium wynikow lezy w repozytorium kodu' >&2; exit 1;; esac
  case \"\$code_real/\" in \"\$experiment_real/\"*) echo 'BLAD: repozytorium kodu lezy w repozytorium wynikow' >&2; exit 1;; esac
  [ -z \"\$(git -C '$WORKER_CODE_REPO' status --short)\" ] || { echo 'BLAD: repozytorium kodu workera nie jest czyste' >&2; exit 1; }
  [ -z \"\$(git -C '$WORKER_EXPERIMENT_REPO' status --short)\" ] || { echo 'BLAD: repozytorium wynikow workera nie jest czyste' >&2; exit 1; }
  git -C '$WORKER_CODE_REPO' fetch origin '$CODE_BRANCH' --quiet
  git -C '$WORKER_CODE_REPO' checkout -B '$CODE_BRANCH' 'origin/$CODE_BRANCH'
  [ \"\$(git -C '$WORKER_CODE_REPO' rev-parse HEAD)\" = '$CODE_COMMIT' ] || exit 1
"

# Branch wynikow jest tworzony z origin/main. Czysty stan jest warunkiem
# bezpieczenstwa dla commit --amend + push --force-with-lease.
git -C "$EXPERIMENT_REPO" fetch origin --quiet
if git -C "$EXPERIMENT_REPO" show-ref --verify --quiet "refs/remotes/origin/$EXPERIMENT_BRANCH"; then
  git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH"
elif git -C "$EXPERIMENT_REPO" show-ref --verify --quiet "refs/heads/$EXPERIMENT_BRANCH"; then
  git -C "$EXPERIMENT_REPO" checkout "$EXPERIMENT_BRANCH"
  [ "$(git -C "$EXPERIMENT_REPO" rev-parse HEAD)" = "$(git -C "$EXPERIMENT_REPO" rev-parse origin/main)" ] ||
    die "Lokalny branch $EXPERIMENT_BRANCH nie istnieje w origin i nie wskazuje origin/main"
else
  git -C "$EXPERIMENT_REPO" checkout -b "$EXPERIMENT_BRANCH" origin/main
  git -C "$EXPERIMENT_REPO" push -u origin "$EXPERIMENT_BRANCH"
fi

CAMPAIGN_RESULTS_DIR="$RESULTS_ROOT/$CAMPAIGN"
[ ! -e "$EXPERIMENT_REPO/$CAMPAIGN_RESULTS_DIR" ] ||
  die "$CAMPAIGN_RESULTS_DIR juz istnieje; uzyj nowego experiment-id zamiast nadpisywania lub rotacji"
mkdir -p "$EXPERIMENT_REPO/$CAMPAIGN_RESULTS_DIR"

if [ "$CAMPAIGN_KIND" = "rate" ]; then
  CAMPAIGN_GOAL="Ustalenie granicy czestosci naplywu danych dla potoku Pan-Tompkins-inspired na wskazanej rewizji RetractorDB."
else
  CAMPAIGN_GOAL="Ustalenie wplywu 1-3 klientow xqry na queue-emission latency i zasoby systemu przy ustalonej czestosci."
fi

CONFIG_SHA256=$(sha256sum "$CONFIG_CSV" | awk '{print $1}')
EXPERIMENT_BASE=$(git -C "$EXPERIMENT_REPO" rev-parse origin/main)
MANIFEST="$EXPERIMENT_REPO/$RESULTS_ROOT/manifest.md"
if [ -e "$MANIFEST" ]; then
  grep -qF -- "- commit kodu: \`$CODE_COMMIT\`" "$MANIFEST" ||
    die "$RESULTS_ROOT istnieje dla innego commita kodu; utworz nowy experiment-id"
  grep -qF -- "- branch kodu: \`$CODE_BRANCH\`" "$MANIFEST" ||
    die "$RESULTS_ROOT istnieje dla innego brancha kodu; utworz nowy experiment-id"
  cat >> "$MANIFEST" <<EOF

## Uruchomienie kampanii $CAMPAIGN

- utworzono: $(date -Is)
- kampania wykonawcza: \`$CAMPAIGN\`
- worker: \`$WORKER_HOST:$WORKER_PORT\` (hostname: \`$WORKER_NAME\`)
- adres zadany nadzorcy: \`$REQUESTED_WORKER_HOST\`
- siec wykrywania: \`${WORKER_SUBNET:-automatycznie wywnioskowana /24}\`
EOF
else
  cat > "$MANIFEST" <<EOF
# Manifest eksperymentu $EXPERIMENT_ID

- utworzono: $(date -Is)
- branch wynikow: \`$EXPERIMENT_BRANCH\`
- baza repozytorium wynikow: \`$EXPERIMENT_BASE\`
- repozytorium kodu: \`$(git -C "$CODE_REPO" remote get-url origin)\`
- branch kodu: \`$CODE_BRANCH\`
- commit kodu: \`$CODE_COMMIT\`
- worker: \`$WORKER_HOST:$WORKER_PORT\` (hostname: \`$WORKER_NAME\`)
- adres zadany nadzorcy: \`$REQUESTED_WORKER_HOST\`
- siec wykrywania: \`${WORKER_SUBNET:-automatycznie wywnioskowana /24}\`

Katalog jest docelowy. Wyniki nie podlegaja rotacji ani przenoszeniu.
EOF
fi

cat > "$EXPERIMENT_REPO/$CAMPAIGN_RESULTS_DIR/README.md" <<EOF
# Kampania: $CAMPAIGN

- eksperyment: \`$EXPERIMENT_ID\`
- branch wynikow: \`$EXPERIMENT_BRANCH\`
- branch kodu: \`$CODE_BRANCH\`
- commit kodu: \`$CODE_COMMIT\`
- konfiguracja: \`config/campaign_${CAMPAIGN}.csv\`
- SHA-256 konfiguracji: \`$CONFIG_SHA256\`

## Cel

$CAMPAIGN_GOAL

Każdy katalog \`study_NN/\` odpowiada jednemu wierszowi konfiguracji i zawiera
surowe dane sondy, metryki, migawki stanu oraz raport.
EOF

git -C "$EXPERIMENT_REPO" add "$RESULTS_ROOT"
MARKER="Experiment-Branch: $EXPERIMENT_BRANCH"
COMMIT_MSG="eksperyment $EXPERIMENT_ID: przygotowanie kampanii $CAMPAIGN

$MARKER"
if git -C "$EXPERIMENT_REPO" log -1 --pretty=%B 2>/dev/null | grep -qF "$MARKER"; then
  git -C "$EXPERIMENT_REPO" commit --amend -m "$COMMIT_MSG"
else
  git -C "$EXPERIMENT_REPO" commit -m "$COMMIT_MSG"
fi
git -C "$EXPERIMENT_REPO" push --force-with-lease origin "HEAD:$EXPERIMENT_BRANCH"

log "Synchronizacja brancha wynikow na workerze..."
ssh_worker "$WORKER_HOST" "$WORKER_PORT" "
  set -e
  [ -z \"\$(git -C '$WORKER_EXPERIMENT_REPO' status --short)\" ] || { echo 'BLAD: repozytorium wynikow workera nie jest czyste' >&2; exit 1; }
  git -C '$WORKER_EXPERIMENT_REPO' fetch origin '$EXPERIMENT_BRANCH' --quiet
  git -C '$WORKER_EXPERIMENT_REPO' checkout -B '$EXPERIMENT_BRANCH' 'origin/$EXPERIMENT_BRANCH'
"

if [ "$SKIP_BUILD" -ne 1 ]; then
  log "Budowanie i instalacja izolowanego Release-Probe na workerze..."
  ssh_worker "$WORKER_HOST" "$WORKER_PORT" "
    set -e
    cd '$WORKER_CODE_REPO'
    grep -q 'build/Release-Probe' scripts/buildrdb.sh || {
      echo 'BLAD: wybrany commit kodu nie obsluguje izolowanego build/Release-Probe' >&2
      exit 1
    }
    scripts/buildrdb.sh conan ninja probe
    [ -f build/Release-Probe/cmake_install.cmake ] || {
      echo 'BLAD: build nie utworzyl profilu Release-Probe' >&2
      exit 1
    }
    [ -z \"\$(git status --short)\" ] || {
      echo 'BLAD: build zmienil repozytorium kodu' >&2
      exit 1
    }
    cmake --install build/Release-Probe
    source '$WORKER_EXPERIMENT_REPO/lib/common.sh'
    verify_probe_binary \"\$HOME/.local/bin/xretractor\"
  "
else
  log "Pomijam build; weryfikuje zainstalowana binarke Release-Probe..."
  ssh_worker "$WORKER_HOST" "$WORKER_PORT" "
    source '$WORKER_EXPERIMENT_REPO/lib/common.sh'
    verify_probe_binary \"\$HOME/.local/bin/xretractor\"
  "
fi

IDX=0
for row in "${ROWS[@]}"; do
  IDX=$((IDX + 1))
  IFS=',' read -r study_id col2 col3 col4 <<< "$row"
  if [ "$CAMPAIGN_KIND" = "rate" ]; then
    rate_hz="$col2"
    clients="$col3"
    samples="$col4"
  else
    rate_hz="$RATE_HZ"
    clients="$col2"
    samples="$col3"
  fi

  log "--- Badanie $IDX/$TOTAL: id=$study_id rate=${rate_hz}Hz clients=$clients samples=$samples ---"
  ssh_worker "$WORKER_HOST" "$WORKER_PORT" \
    "'$WORKER_EXPERIMENT_REPO/worker/run_study.sh' \
      --code-repo '$WORKER_CODE_REPO' \
      --experiment-repo '$WORKER_EXPERIMENT_REPO' \
      --code-commit '$CODE_COMMIT' \
      --experiment-branch '$EXPERIMENT_BRANCH' \
      --results-root '$RESULTS_ROOT' \
      --campaign '$CAMPAIGN' \
      --study-id '$study_id' \
      --rate-hz '$rate_hz' \
      --clients '$clients' \
      --samples '$samples' \
      --sink '$SINK'" ||
    die "Badanie $study_id nie powiodlo sie; wynik nie zostal zatwierdzony"

  git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet
  [ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] ||
    die "Lokalne repozytorium wynikow zmienilo sie podczas badania"
  git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" \
    "origin/$EXPERIMENT_BRANCH" >/dev/null

  if [ "$IDX" -lt "$TOTAL" ]; then
    log "Restart workera przed kolejnym badaniem..."
    ssh_worker "$WORKER_HOST" "$WORKER_PORT" "sync; sudo -n reboot" || true
    wait_for_worker "$WORKER_HOST" "$WORKER_PORT" "$REBOOT_TIMEOUT"
  fi
done

log "=== Kampania $CAMPAIGN zakonczona: $RESULTS_ROOT/$CAMPAIGN ==="
