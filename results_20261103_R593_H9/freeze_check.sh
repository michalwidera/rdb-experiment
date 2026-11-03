#!/usr/bin/env bash
# Fail-closed immutability and provenance gate for the R593 H9 replication (Q=8).
#
# KOPIA results_20260814_K26v3/freeze_check.sh, zawezona do tego, co powtorka
# faktycznie konsumuje. Odpadaja: Flink (JDK, port, oracle, krzywa planu) i
# pilot runtime - powtorka nie liczy niczego po stronie Flinka; gen_blocks.py i
# kalibracja - blocks.tsv jest podzbiorem Q=8 zamrozonego blocks.tsv K26v3,
# a rate jest zamrozonym ANEKS-1 K26v3 (sprawdzanym tu po sumie z WERDYKT.md).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
WORKER_CODE_REPO="${WORKER_CODE_REPO:-/home/michal/R593}"
WORKER_EXP_REPO="${WORKER_EXP_REPO:-/home/michal/rdb-experiment}"
WORKER_CAMPAIGN_DIR="${WORKER_CAMPAIGN_DIR:-$WORKER_EXP_REPO/results_20261103_R593_H9}"

EXPECTED_BRANCH="experiment/20261103_R593"
EXPECTED_ENGINE="dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb"
EXPECTED_RECORDS="3000"
EXPECTED_GOVERNOR="performance"
# Suma ANEKS-1 K26v3 zapisana w results_20260814_K26v3/WERDYKT.md.
EXPECTED_RATE_SHA256="fc6e549a8666ec6c23681c87b2d55270038a5c014cb4a9b42d6e3816b52003f1"
FROZEN_BLOCKS="$EXP_REPO/results_20260814_K26v3/blocks.tsv"

START_RECORD="$HERE/results/ANEKS-0_start.tsv"
ANEKS_RATE="$HERE/ANEKS-1_rate.tsv"
ANEKS_WORKER_BIN="$HERE/ANEKS-2_worker_binaria.tsv"
ANEKS_WORKER_ENV="$HERE/ANEKS-3_worker_srodowisko.tsv"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }
ok() { echo "  ok  $*"; }

check_host() {
  local require_frozen="${1:-no}"
  local code_sha experiment_sha
  echo "== zakres hosta R593 H9 (require_frozen=$require_frozen) =="

  eq "$(git -C "$EXP_REPO" branch --show-current)" "$EXPECTED_BRANCH" "galaz powtorki"
  code_sha="$(git -C "$CODE_REPO" rev-parse HEAD)"
  experiment_sha="$(git -C "$EXP_REPO" rev-parse HEAD)"
  [[ -z "$(git -C "$CODE_REPO" status --short)" ]] || fail "drzewo silnika jest brudne"
  eq "$code_sha" "$EXPECTED_ENGINE" "silnik hosta wobec przypiecia powtorki"
  ok "galaz i czysty silnik $code_sha"

  if [[ -r "$START_RECORD" ]]; then
    eq "$code_sha" "$(awk -F'\t' '$1=="engine_sha"{print $2}' "$START_RECORD")" "pin silnika od startu"
    eq "$experiment_sha" "$(awk -F'\t' '$1=="experiment_sha"{print $2}' "$START_RECORD")" \
      "pin eksperymentu od startu"
    ok "wiazacy pin powtorki aktywny"
  fi

  if [[ "$require_frozen" == "yes" ]]; then
    [[ -z "$(git -C "$EXP_REPO" status --short)" ]] || fail "drzewo rdb-experiment nie jest zamrozone"
    (cd "$HERE" && sha256sum --quiet --check manifest.sha256) || fail "manifest aparatury jest niezgodny"
    ok "czyste drzewo eksperymentu i zgodny manifest ($(grep -c . "$HERE/manifest.sha256") plikow)"
  fi

  "$HERE/gen_corpus.py" --check >/dev/null || fail "korpus nie zgadza sie z generatorem"
  "$HERE/validate_corpus.py" --selftest >/dev/null || fail "selftest bramki korpusu nie przechodzi"
  "$HERE/validate_corpus.py" --check >/dev/null || fail "dowod kompilacji calego korpusu jest niezgodny"
  eq "$(find "$HERE/rql" -maxdepth 1 -type f -name '*.rql' | wc -l)" "21" "liczba planow RQL"
  eq "$(wc -l < "$HERE/data/main/vib.txt")" "$EXPECTED_RECORDS" "rekordy szybkiego zrodla"
  eq "$(wc -l < "$HERE/data/main/cur.txt")" "$((EXPECTED_RECORDS / 2))" "rekordy wolnego zrodla"
  ok "korpus: 21 planow, 84/84 kompilacje, 4/4 mutanty odrzucone"

  cmp -s "$HERE/blocks.tsv" <(awk -F'\t' 'NR==1 || $3==8' "$FROZEN_BLOCKS") \
    || fail "blocks.tsv nie jest podzbiorem Q=8 zamrozonego blocks.tsv K26v3"
  eq "$(sha256sum "$ANEKS_RATE" | awk '{print $1}')" "$EXPECTED_RATE_SHA256" "suma ANEKS-1 wobec K26v3"
  "$HERE/verdict.py" --selftest >/dev/null || fail "selftest werdyktu nie przechodzi"
  "$HERE/mechanism_table.py" --gate >/dev/null || fail "bramka klasyfikatora planu nie przechodzi"
  (cd "$HERE" && python3 -m unittest -q test_apparatus.py test_pipeline.py) >/dev/null \
    || fail "testy aparatury nie przechodza"
  ok "bloki Q=8, ANEKS-1 K26v3, werdykt, testy aparatury i klasyfikator planu"

  # shellcheck source=../lib/common.sh
  source "$EXP_REPO/lib/common.sh"
  local built=0
  while IFS=$'\t' read -r profile slug dedup share commutative factor; do
    [[ "$profile" == "profile" ]] && continue
    [[ -n "$profile" ]] || continue
    local binary="$CODE_REPO/build/R593-$slug/src/retractor/xretractor"
    verify_probe_binary_profile "$binary" "$dedup" "$share" "$commutative" "$factor" ON \
      || fail "profil $profile ma inne flagi"
    if [[ -r "$START_RECORD" ]]; then
      eq "$(sha256sum "$binary" | awk '{print $1}')" \
        "$(awk -F'\t' -v key="host_binary_sha256_$profile" '$1==key{print $2}' "$START_RECORD")" \
        "SHA binarium $profile od startu"
    fi
    built=$((built + 1))
  done < "$HERE/profiles.tsv"
  eq "$built" "4" "liczba binariow profili"
  ok "cztery binaria R593 hosta: flagi zgodne"
}

check_worker() {
  echo "== zakres worker R593 H9 (przed P6) =="
  [[ -r "$ANEKS_WORKER_ENV" && -r "$ANEKS_WORKER_BIN" ]] \
    || fail "brak ANEKS-2/ANEKS-3 - worker nie zostal jeszcze zamrozony"
  local frozen_kernel frozen_cpus live_kernel live_governor frozen_code live_code live_exp
  frozen_kernel="$(awk -F'\t' '$1=="kernel"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_cpus="$(awk -F'\t' '$1=="cpu_pinning"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_code="$(awk -F'\t' '$1=="engine_sha"{print $2}' "$ANEKS_WORKER_ENV")"
  eq "$frozen_code" "$EXPECTED_ENGINE" "ANEKS-3 wobec przypiecia powtorki"
  live_kernel="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" 'uname -r')" || fail "worker nieosiagalny"
  eq "$live_kernel" "$frozen_kernel" "kernel workera"
  live_governor="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" \
    'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr "\n" " "')"
  eq "${live_governor% }" "$EXPECTED_GOVERNOR" "governor workera"
  eq "$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" 'systemctl --version | head -n1')" \
    "$(awk -F'\t' '$1=="systemd"{print $2}' "$ANEKS_WORKER_ENV")" "wersja systemd workera"
  [[ -n "$frozen_cpus" ]] || fail "ANEKS-3 nie zawiera cpu_pinning"
  live_code="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" "git -C '$WORKER_CODE_REPO' rev-parse HEAD")" \
    || fail "nie mozna odczytac SHA silnika workera"
  live_exp="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" "git -C '$WORKER_EXP_REPO' rev-parse HEAD")" \
    || fail "nie mozna odczytac SHA eksperymentu workera"
  eq "$live_code" "$frozen_code" "SHA silnika workera wobec ANEKS-3"
  if [[ -r "$START_RECORD" ]]; then
    eq "$live_code" "$(awk -F'\t' '$1=="engine_sha"{print $2}' "$START_RECORD")" "worker wobec pinu silnika"
    eq "$live_exp" "$(awk -F'\t' '$1=="experiment_sha"{print $2}' "$START_RECORD")" "worker wobec pinu eksperymentu"
  else
    eq "$live_exp" "$(git -C "$EXP_REPO" rev-parse HEAD)" "SHA eksperymentu workera przed startem"
  fi
  local profile expected actual
  for profile in DEFAULT NO_R2_CANON NO_R1_FACTOR NO_R1_NO_R2; do
    expected="$(awk -F'\t' -v p="$profile" '$1==p{print $2}' "$ANEKS_WORKER_BIN")"
    [[ -n "$expected" ]] || fail "ANEKS-2 nie zawiera $profile"
    actual="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" \
      "sha256sum '$WORKER_CODE_REPO/build/R593-$profile/src/retractor/xretractor'" | awk '{print $1}')" \
      || fail "nie mozna odczytac binarium $profile na workerze"
    eq "$actual" "$expected" "SHA binarium workera $profile"
  done
  ok "worker: kernel, governor, przypiecie, rewizje i cztery binaria zamrozone"
}

check_bound() {
  [[ -r "$START_RECORD" ]] || fail "brak ANEKS-0_start.tsv - powtorka nie zostala jeszcze rozpoczeta"
  check_host yes
  check_worker
}

check_matrix() {
  [[ -r "$START_RECORD" ]] || fail "brak wiazacego pinu startu powtorki"
  local rate
  rate="$(awk -F'\t' '$1=="rate_scale"{print $2}' "$ANEKS_RATE")"
  [[ -n "$rate" ]] || fail "ANEKS-1 nie zawiera rate_scale"
  awk -F'\t' '$1=="calibration_saw_effect" && $2=="no" {ok=1} END {exit ok ? 0 : 1}' "$ANEKS_RATE" \
    || fail "ANEKS-1 nie potwierdza calibration_saw_effect=no"
  ok "rate zamrozony z K26v3: skala $rate"

  # ANEKS-1 jest konsumowany PRZEZ WORKERA (D3 z K26v2): sprawdzamy kopie workera.
  local host_sum worker_sum worker_annex="$WORKER_CAMPAIGN_DIR/ANEKS-1_rate.tsv"
  host_sum="$(sha256sum "$ANEKS_RATE" | awk '{print $1}')"
  worker_sum="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" \
    "sha256sum $(printf '%q' "$worker_annex") 2>/dev/null" | awk '{print $1}')" \
    || fail "nie mozna odczytac ANEKS-1 na workerze"
  [[ -n "$worker_sum" ]] || fail "brak ANEKS-1 na workerze ($worker_annex) - macierz go konsumuje"
  eq "$worker_sum" "$host_sum" "ANEKS-1 na workerze wobec kopii hosta"
  ok "ANEKS-1 obecny po obu stronach, sumy zgodne"
}

case "${1:-}" in
  preflight)      check_host no ;;
  predeklaracja)  check_host yes ;;
  worker)         check_worker ;;
  bound)          check_bound ;;
  macierz)        check_bound; check_matrix ;;
  *)
    echo "uzycie: $(basename "$0") {preflight|predeklaracja|worker|bound|macierz}" >&2
    echo "zakres jest obowiazkowy" >&2
    exit 2
    ;;
esac
