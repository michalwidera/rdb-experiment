#!/bin/bash
# Kroki K6c wykonywane na workerze poza pętlą badań nadzorcy: kalibracja
# (K6c.0), Tier A (K6c.3) i punkt saturacji (K6c.5).
#
# Żaden z nich nie przyjmuje rate'u z zewnątrz. Kalibracja go WYZNACZA (per
# rodzina, do `results/rate.json`), Tier A jest od niego niezależny i biegnie na
# zamrożonym `s = 6`, a saturacja dotyczy W8, której rate wynika z deklaracji
# źródła.
#
# Każdy z nich jest pomiarem czasu, więc obowiązuje governor `performance`
# i izolowany rdzeń 3 (R7). Reżim RT jest ustawiany przez samą binarkę (`-t`)
# tam, gdzie mierzy się pętlę slotową; kompilacja go nie potrzebuje.
#
# Wyniki i wpis w JOURNAL.md trafiają wyłącznie do repozytorium wyników (R2).
set -euo pipefail

# Skrypty kampanii importuja sie nawzajem w katalogu wynikow, wiec bez tego
# kazdy przebieg zostawia __pycache__ w repozytorium wynikow i nastepne
# badanie odmawia startu na kontroli czystosci.
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_EXPERIMENT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

CODE_REPO="/home/michal/retractordb"
EXPERIMENT_REPO="$DEFAULT_EXPERIMENT_REPO"
CODE_COMMIT=""
EXPERIMENT_BRANCH=""
RESULTS_ROOT=""
STEP=""
# Tier A mierzy kompilację, nie pętlę slotową, więc nie podlega wyborowi rate'u
# per rodzina. README v2 zamraża dla niego jeden mnożnik.
TIER_A_SCALE=6
REPS=15

while [ $# -gt 0 ]; do
  case "$1" in
    --code-repo) CODE_REPO="$2"; shift 2 ;;
    --experiment-repo) EXPERIMENT_REPO="$2"; shift 2 ;;
    --code-commit) CODE_COMMIT="$2"; shift 2 ;;
    --experiment-branch) EXPERIMENT_BRANCH="$2"; shift 2 ;;
    --results-root) RESULTS_ROOT="$2"; shift 2 ;;
    --step) STEP="$2"; shift 2 ;;
    --reps) REPS="$2"; shift 2 ;;
    *) printf 'Nieznana opcja: %s\n' "$1" >&2; exit 1 ;;
  esac
done

# shellcheck source=../lib/common.sh
source "$EXPERIMENT_REPO/lib/common.sh"

[ -n "$CODE_COMMIT" ] || die "Brak --code-commit"
[ -n "$EXPERIMENT_BRANCH" ] || die "Brak --experiment-branch"
[ -n "$RESULTS_ROOT" ] || die "Brak --results-root"
[ -n "$STEP" ] || die "Brak --step (calibrate|tier-a|saturation)"
validate_results_root "$RESULTS_ROOT" || exit 1
validate_git_branch "$EXPERIMENT_BRANCH" "brancha wynikow" || exit 1
validate_safe_absolute_path "$CODE_REPO" "repozytorium kodu" || exit 1
[[ "$CODE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "code-commit musi byc pelnym SHA-1"
case "$STEP" in
  calibrate|tier-a|saturation) ;;
  *) die "nieznany krok: $STEP" ;;
esac

require_disjoint_repositories "$CODE_REPO" "$EXPERIMENT_REPO" || exit 1
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$CODE_COMMIT" ] ||
  die "Repozytorium kodu nie wskazuje wymaganego commita $CODE_COMMIT"
require_input_dirs_pristine "$CODE_REPO" examples/ecg || exit 1
CODE_FINGERPRINT=$(mktemp)
code_tree_fingerprint "$CODE_REPO" "$CODE_FINGERPRINT" || exit 1

git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet
[ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] || die "Repozytorium wynikow workera nie jest czyste"
git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH" >/dev/null

CAMPAIGN_DIR="$EXPERIMENT_REPO/$RESULTS_ROOT"
[ -d "$CAMPAIGN_DIR" ] || die "Brak katalogu kampanii: $CAMPAIGN_DIR"
require_tmpfs /dev/shm || exit 1
uname -v | grep -q PREEMPT_RT || die "Kernel workera nie jest buildem PREEMPT_RT"
# Od K6c kalibracja pyta silnik o interwal strumienia mierzonego (`xqry -t`),
# wiec klient musi byc na PATH tak samo jak w Tier B.
command -v xqry >/dev/null || die "xqry nie jest na PATH"
# `xqry` na PATH jest czescia aparatury pomiarowej: kampania czyta z niego
# interwal strumienia (`-t`, pole `delta`), a w Tier B podlacza go jako klienta.
# Staly klient z innego commita przeszedlby kontrole `command -v` i po cichu
# wrocilby z defektem, dla ktorego naprawy zatrzymano K6b. `--help` wypisuje
# `Branch: <branch>:<short-sha>` ustalone przy KONFIGURACJI cmake, wiec kontrola
# wykrywa podmieniona binarke, a nie przebudowe bez rekonfiguracji -- i to jest
# jej zadeklarowany zakres.
XQRY_COMMIT=$(xqry --help 2>&1 | sed -n 's/.*Branch: [^:]*:\([0-9a-f]\{7,\}\).*/\1/p' | head -1)
[ -n "$XQRY_COMMIT" ] || die "nie udalo sie ustalic commita klienta xqry"
case "$CODE_COMMIT" in
  "$XQRY_COMMIT"*) ;;
  *) die "xqry pochodzi z commita $XQRY_COMMIT, a kampania z $CODE_COMMIT" ;;
esac
log "klient xqry: $XQRY_COMMIT (zgodny z przypieciem)"

sudo -n true 2>/dev/null || die "Krok wymaga bezhaslowego sudo (governor)"

ORIG_GOVERNOR=""
restore_governor() {
  local c
  if [ -n "$ORIG_GOVERNOR" ]; then
    echo "$ORIG_GOVERNOR" |
      sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null 2>&1 || return 1
    for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
      [ "$(cat "$c")" = "$ORIG_GOVERNOR" ] || return 1
    done
    ORIG_GOVERNOR=""
  fi
}
cleanup() {
  local status=$?
  restore_governor || true
  return "$status"
}
trap cleanup EXIT

ORIG_GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
echo performance | sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null
for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  [ "$(cat "$c")" = "performance" ] || die "Nie ustawiono governora performance dla $c"
done
log "governor: performance (poprzedni: $ORIG_GOVERNOR)"

case "$STEP" in
  calibrate)
    log "K6c.0 — kalibracja rate'u per rodzina"
    python3 "$CAMPAIGN_DIR/calibrate.py" \
      --code-repo "$CODE_REPO" \
      --output "$CAMPAIGN_DIR/results"
    ARTIFACTS=("$RESULTS_ROOT/results/calibration.md" "$RESULTS_ROOT/results/rate.json")
    JOURNAL_LINE=$(python3 - "$CAMPAIGN_DIR/results/rate.json" <<'RATEPY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
rates = ", ".join(
    f"{family}=s{entry['scale']}" if entry["source"] == "kalibracja" else f"{family}=zrodlo"
    for family, entry in sorted(data["families"].items())
)
slots = ", ".join(f"{case}={cell['slots']}" for case, cell in sorted(data["cells"].items()))
excluded = ", ".join(entry["case"] for entry in data["excluded_cases"]) or "brak"
print(
    f"K6c.0 kalibracja: przebiegow={data['checked_runs']}, rate per rodzina: {rates}; "
    f"slotow per komorka (slot z silnika): {slots}; komorki wykluczone: {excluded}"
)
RATEPY
)
    ;;
  tier-a)
    log "K6c.3 — Tier A (metryki kompilacji), scale=$TIER_A_SCALE, reps=$REPS"
    WORKLOADS="/dev/shm/k6b-tierA/workloads"
    rm -rf "$WORKLOADS"
    python3 "$CAMPAIGN_DIR/generate.py" --output "$WORKLOADS" --scale "$TIER_A_SCALE" >/dev/null
    python3 "$CAMPAIGN_DIR/collect_compile.py" \
      --code-repo "$CODE_REPO" \
      --workloads "$WORKLOADS" \
      --output "$CAMPAIGN_DIR/results" \
      --reps "$REPS"
    ARTIFACTS=("$RESULTS_ROOT/results/compile_runs.csv")
    JOURNAL_LINE="K6c.3 Tier A: $(( $(wc -l < "$CAMPAIGN_DIR/results/compile_runs.csv") - 1 )) kompilacji, scale=$TIER_A_SCALE, reps=$REPS"
    ;;
  saturation)
    log "K6c.5 — punkt saturacji (W8, rate ze zrodla)"
    python3 "$CAMPAIGN_DIR/saturation.py" \
      --code-repo "$CODE_REPO" \
      --output "$CAMPAIGN_DIR/results"
    ARTIFACTS=("$RESULTS_ROOT/results/saturation.md" "$RESULTS_ROOT/results/saturation.json")
    JOURNAL_LINE="K6c.5 punkt saturacji zmierzony"
    ;;
esac

restore_governor || die "Nie udalo sie przywrocic pierwotnego governora CPU"
require_code_tree_unchanged "$CODE_REPO" "$CODE_FINGERPRINT" ||
  die "Repozytorium kodu zmienilo sie podczas kroku $STEP"
require_input_dirs_pristine "$CODE_REPO" examples/ecg ||
  die "Krok $STEP zostawil artefakty w katalogu wejsciowym repozytorium kodu"
rm -f "$CODE_FINGERPRINT"

# Jak w run_ablation_study.sh: R4 trzyma jeden commit kampanii, wiec przed
# commitem przenosimy wyniki na aktualny wierzcholek brancha. Wyniki kroku sa
# nowymi plikami, wiec `checkout -B` ich nie rusza.
git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet ||
  die "Nie udalo sie odswiezyc brancha wynikow przed commitem"
git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH" --quiet ||
  die "Nie udalo sie przeniesc wynikow na aktualny wierzcholek brancha"

cat >> "$EXPERIMENT_REPO/JOURNAL.md" <<EOF

## $(date -Is) — $RESULTS_ROOT / krok $STEP

- wynik: sukces
- commit kodu: \`$CODE_COMMIT\`
- $JOURNAL_LINE
EOF

git -C "$EXPERIMENT_REPO" add "${ARTIFACTS[@]}" JOURNAL.md
MARKER="Experiment-Branch: $EXPERIMENT_BRANCH"
git -C "$EXPERIMENT_REPO" log -1 --pretty=%B | grep -qF "$MARKER" ||
  die "Ostatni commit nie nalezy do eksperymentu $EXPERIMENT_BRANCH"
git -C "$EXPERIMENT_REPO" commit --amend --no-edit --quiet
git -C "$EXPERIMENT_REPO" push --force-with-lease origin "HEAD:$EXPERIMENT_BRANCH" ||
  die "Push wynikow odrzucony; wynik kroku jest w drzewie roboczym workera i nie zostal utracony"
log "Krok $STEP zakonczony."
