#!/usr/bin/env bash
# Fail-closed immutability and provenance gate for K26v2.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
JAVA17="${JAVA17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/java}"
JAVAC17="${JAVAC17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/javac}"
FLINK_JAR="${FLINK_JAR:-/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar}"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
WORKER_CODE_REPO="${WORKER_CODE_REPO:-/home/michal/K26v2}"
WORKER_EXP_REPO="${WORKER_EXP_REPO:-/home/michal/rdb-experiment}"

EXPECTED_BRANCH="experiment/20260810_K26v2"
EXPECTED_RECORDS="3000"
EXPECTED_GOVERNOR="performance"
EXPECTED_JAVA_SHA256="a89ad12dc799a14a20d9e570ef788dbcfec70d037d8ede404c2c924354933237"
EXPECTED_JAVAC_SHA256="9a4eedebe503abd0daf458063d99c9dbc2d8892bba03fd5efe48f33d7a65dc9d"
EXPECTED_FLINK_JAR_SHA256="7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493"
EXPECTED_SCREEN_VERSION="Screen version 4.09.01 (GNU) 20-Aug-23"

START_RECORD="$HERE/results/ANEKS-0_start.tsv"
ANEKS_RATE="$HERE/results/ANEKS-1_rate.tsv"
ANEKS_WORKER_BIN="$HERE/ANEKS-2_worker_binaria.tsv"
ANEKS_WORKER_ENV="$HERE/ANEKS-3_worker_srodowisko.tsv"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }
ok() { echo "  ok  $*"; }

check_runtime_evidence() {
  local dir="$HERE/pilot/out_rt"
  local profiles=(DEFAULT NO_R2_CANON NO_R1_FACTOR NO_R1_NO_R2)
  local plans=(F9_R2_Q8 F9_R1_Q8 F9_X_Q8 F9_R2_controls F9_R1_controls F9_X_controls)
  local cells=0 profile plan file logical public
  [[ -r "$HERE/pilot/neg/rejection.txt" ]] || fail "brak odrzuconego mutanta runtime"
  for profile in "${profiles[@]}"; do
    for plan in "${plans[@]}"; do
      file="$dir/${profile}_${plan}.counters"
      [[ -r "$file" ]] || fail "brak dowodu runtime: $profile/$plan"
      logical="$(grep -m1 '^LOGICAL ' "$file" || true)"
      [[ -n "$logical" ]] || fail "$profile/$plan: brak LOGICAL"
      grep -q '^WORK ' "$file" || fail "$profile/$plan: brak WORK"
      public="$(sed -n 's/.*publiczne: dopisania=\([0-9]*\).*/\1/p' <<<"$logical")"
      [[ "${public:-0}" -gt 0 ]] || fail "$profile/$plan: pusty mianownik"
      cells=$((cells + 1))
    done
  done
  eq "$cells" "24" "liczba komorek pilota runtime"
  ok "pilot runtime: 24/24 komorki, mutant odrzucony"
}

check_flink_f9x_runtime() {
  local java_home flink_home
  java_home="$(dirname "$(dirname "$JAVAC17")")"
  flink_home="$(dirname "$(dirname "$FLINK_JAR")")"
  JAVA_HOME_PINNED="$java_home" FLINK_HOME="$flink_home" \
    "$HERE/flink/build_flink.sh" >/dev/null || fail "swiezy build portu Flinka F9-X nie przechodzi"
  JAVA17="$JAVA17" FLINK_HOME="$flink_home" \
    "$HERE/pilot/verify_flink_f9x.py" >/dev/null || fail "swiezy runtime/oracle Flinka F9-X nie przechodzi"
  eq "$(awk -F'\t' 'NR>1 && $4=="true" && $5=="true" && $6=="true" {n++} END {print n+0}' \
    "$HERE/pilot/flink_runtime/verification.tsv")" "16" "strumienie pilota F9-X Flink"
  ok "Flink F9-X przebudowany: 16/16, oracle 100%, historyczny mutant zatrzaskow odrzucony"
}

check_host() {
  local require_frozen="${1:-no}"
  local code_sha experiment_sha
  echo "== zakres hosta K26v2 (require_frozen=$require_frozen) =="

  eq "$(git -C "$EXP_REPO" branch --show-current)" "$EXPECTED_BRANCH" "galaz kampanii"
  eq "$(screen --version | head -n1)" "$EXPECTED_SCREEN_VERSION" "wersja screen hosta"
  code_sha="$(git -C "$CODE_REPO" rev-parse HEAD)"
  experiment_sha="$(git -C "$EXP_REPO" rev-parse HEAD)"
  [[ -z "$(git -C "$CODE_REPO" status --short)" ]] || fail "drzewo silnika jest brudne"
  if [[ -r "$START_RECORD" ]]; then
    ok "galaz i czysty silnik $code_sha"
  else
    ok "galaz i czysty silnik $code_sha (przed startem SHA nie jest jeszcze wiazace)"
  fi

  if [[ -r "$START_RECORD" ]]; then
    eq "$code_sha" "$(awk -F'\t' '$1=="engine_sha"{print $2}' "$START_RECORD")" "pin silnika od startu"
    eq "$experiment_sha" "$(awk -F'\t' '$1=="experiment_sha"{print $2}' "$START_RECORD")" \
      "pin eksperymentu od startu"
    ok "wiazacy pin kampanii aktywny"
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

  "$HERE/gen_blocks.py" --check >/dev/null || fail "blocks.tsv nie zgadza sie z generatorem"
  "$HERE/calib/gen_calib.py" --check >/dev/null || fail "generator skalowania rate nie przechodzi bramki"
  "$HERE/calib/gen_slots.py" --check >/dev/null || fail "slots.tsv nie zgadza sie z TimeLine silnika"
  "$HERE/verdict.py" --selftest >/dev/null || fail "selftest werdyktu nie przechodzi"
  "$HERE/mechanism_table.py" --gate >/dev/null || fail "bramka klasyfikatora planu nie przechodzi"
  (cd "$HERE" && python3 -m unittest -q test_apparatus.py test_pipeline.py) >/dev/null \
    || fail "testy aparatury nie przechodza"
  check_runtime_evidence
  ok "bloki, skala rate, werdykt 20/20, testy aparatury i klasyfikator planu"

  # shellcheck source=../lib/common.sh
  source "$EXP_REPO/lib/common.sh"
  local built=0
  while IFS=$'\t' read -r profile slug dedup share commutative factor; do
    [[ "$profile" == "profile" ]] && continue
    [[ -n "$profile" ]] || continue
    local binary="$CODE_REPO/build/K26v2-$slug/src/retractor/xretractor"
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
  ok "cztery binaria K26v2: flagi i SHA zgodne"

  eq "$(sha256sum "$JAVA17" | awk '{print $1}')" "$EXPECTED_JAVA_SHA256" "SHA java"
  eq "$(sha256sum "$JAVAC17" | awk '{print $1}')" "$EXPECTED_JAVAC_SHA256" "SHA javac"
  eq "$(sha256sum "$FLINK_JAR" | awk '{print $1}')" "$EXPECTED_FLINK_JAR_SHA256" "SHA Flink"
  eq "$(wc -l < "$HERE/flink/oracle/canonical_oracle.tsv")" "18" "wektory oracle C++"
  awk -F'\t' '$1=="F9-X" && $2=="natural" && $3==8 {if ($5!="32.0000") exit 1; n++}
               $1=="F9-X" && $2=="manual" && $3==8 {if ($5!="5.0000") exit 1; n++}
               END {exit n==2 ? 0 : 1}' "$HERE/flink/results/flink_q_curve.tsv" \
    || fail "krzywa planu Flinka F9-X Q=8 jest inna niz 32/5"
  ok "JDK/Flink przypiete; serializer 18/18; F9-X plan natural/manual = 32/5"
  check_flink_f9x_runtime

  if [[ "$require_frozen" == "yes" ]]; then
    [[ -z "$(git -C "$EXP_REPO" status --short)" ]] \
      || fail "swiezy build/runtime Flinka zmienil zamrozone drzewo eksperymentu"
    (cd "$HERE" && sha256sum --quiet --check manifest.sha256) \
      || fail "swiezy build/runtime Flinka nie odtwarza zamrozonego manifestu"
    ok "swiezy runtime Flinka odtwarza zamrozone dowody bajt w bajt"
  fi
}

check_worker() {
  echo "== zakres worker K26v2 (przed P6) =="
  [[ -r "$ANEKS_WORKER_ENV" && -r "$ANEKS_WORKER_BIN" ]] \
    || fail "brak ANEKS-2/ANEKS-3 — worker nie zostal jeszcze zamrozony"
  local frozen_kernel frozen_cpus live_kernel live_governor frozen_code live_code live_exp
  frozen_kernel="$(awk -F'\t' '$1=="kernel"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_cpus="$(awk -F'\t' '$1=="cpu_pinning"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_code="$(awk -F'\t' '$1=="engine_sha"{print $2}' "$ANEKS_WORKER_ENV")"
  live_kernel="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" 'uname -r')" || fail "worker nieosiagalny"
  eq "$live_kernel" "$frozen_kernel" "kernel workera"
  live_governor="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" \
    'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr "\n" " "')"
  eq "${live_governor% }" "$EXPECTED_GOVERNOR" "governor workera"
  eq "$(ssh -F "$SSH_CONFIG" -o BatchMode=yes "$WORKER_SSH" 'screen --version | head -n1')" \
    "$(awk -F'\t' '$1=="screen"{print $2}' "$ANEKS_WORKER_ENV")" "wersja screen workera"
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
      "sha256sum '$WORKER_CODE_REPO/build/K26v2-$profile/src/retractor/xretractor'" | awk '{print $1}')" \
      || fail "nie mozna odczytac binarium $profile na workerze"
    eq "$actual" "$expected" "SHA binarium workera $profile"
  done
  ok "worker: kernel, governor, przypiecie, rewizje i cztery binaria zamrozone"
}

check_bound() {
  [[ -r "$START_RECORD" ]] || fail "brak ANEKS-0_start.tsv — kampania nie zostala jeszcze rozpoczeta"
  check_host yes
  check_worker
}

check_matrix() {
  [[ -r "$START_RECORD" ]] || fail "brak wiazacego pinu startu kampanii"
  [[ -r "$ANEKS_RATE" ]] || fail "brak ANEKS-1 z zamrozonym rate"
  local rate
  rate="$(awk -F'\t' '$1=="rate_scale"{print $2}' "$ANEKS_RATE")"
  [[ -n "$rate" ]] || fail "ANEKS-1 nie zawiera rate_scale"
  awk -F'\t' '$1=="calibration_saw_effect" && $2=="no" {ok=1} END {exit ok ? 0 : 1}' "$ANEKS_RATE" \
    || fail "kalibracja nie potwierdza calibration_saw_effect=no"
  ok "rate zamrozony: skala $rate"
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
