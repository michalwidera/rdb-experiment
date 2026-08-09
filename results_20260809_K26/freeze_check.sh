#!/usr/bin/env bash
# Fail-closed immutability and provenance gate for K26.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
JAVA17="${JAVA17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/java}"
JAVAC17="${JAVAC17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/javac}"
FLINK_JAR="${FLINK_JAR:-/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar}"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"

EXPECTED_BRANCH="experiment/20260809_K26"
EXPECTED_CODE_SHA="189b3f8187d80492644438be706e45c7e783b201"
EXPECTED_RECORDS="3000"
EXPECTED_GOVERNOR="performance"
EXPECTED_JAVA_SHA256="a89ad12dc799a14a20d9e570ef788dbcfec70d037d8ede404c2c924354933237"
EXPECTED_JAVAC_SHA256="9a4eedebe503abd0daf458063d99c9dbc2d8892bba03fd5efe48f33d7a65dc9d"
EXPECTED_FLINK_JAR_SHA256="7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493"

declare -A HOST_BINARY_SHA256=(
  [DEFAULT]="f32ed01424cd35e31b04affd8290da95b459adae8950004c3cdcc875018598ec"
  [NO_R2_CANON]="ed31681ca8a8a02f324c79a9b3400a2e072ae977e8fcdac740debfd7f00305b8"
  [NO_R1_FACTOR]="7261659b07eb6fab52530b0f107f3d71e0ce93fef1808ed87c432964c2de8367"
  [NO_R1_NO_R2]="6a59ffaf0102e31db94c9c202ac3e26ea0b431a7073e8e6c90d43c05d6fd1021"
)

ANEKS_RATE="$HERE/ANEKS-1_rate.tsv"
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

check_host() {
  local require_frozen="${1:-no}"
  echo "== zakres hosta K26 (require_frozen=$require_frozen) =="

  eq "$(git -C "$EXP_REPO" branch --show-current)" "$EXPECTED_BRANCH" "galaz kampanii"
  eq "$(git -C "$CODE_REPO" rev-parse HEAD)" "$EXPECTED_CODE_SHA" "SHA silnika"
  [[ -z "$(git -C "$CODE_REPO" status --short)" ]] || fail "drzewo silnika jest brudne"
  ok "galaz i czysty silnik $EXPECTED_CODE_SHA"

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
  "$HERE/verdict.py" --selftest >/dev/null || fail "selftest werdyktu nie przechodzi"
  "$HERE/mechanism_table.py" --gate >/dev/null || fail "bramka klasyfikatora planu nie przechodzi"
  (cd "$HERE" && python3 -m unittest -q test_apparatus.py) >/dev/null \
    || fail "testy aparatury nie przechodza"
  check_runtime_evidence
  eq "$(awk -F'\t' 'NR>1 && $4=="true" && $5=="true" {n++} END {print n+0}' \
    "$HERE/pilot/flink_runtime/verification.tsv")" "16" "strumienie pilota F9-X Flink"
  ok "bloki, werdykt 20/20, testy aparatury 6/6 i klasyfikator planu"
  ok "Flink F9-X runtime: 16/16 strumieni, niezalezny oracle 100%"

  # shellcheck source=../lib/common.sh
  source "$EXP_REPO/lib/common.sh"
  local built=0
  while IFS=$'\t' read -r profile slug dedup share commutative factor; do
    [[ "$profile" == "profile" ]] && continue
    [[ -n "$profile" ]] || continue
    local binary="$CODE_REPO/build/K26-$slug/src/retractor/xretractor"
    verify_probe_binary_profile "$binary" "$dedup" "$share" "$commutative" "$factor" \
      || fail "profil $profile ma inne flagi"
    eq "$(sha256sum "$binary" | awk '{print $1}')" "${HOST_BINARY_SHA256[$profile]}" \
      "SHA binarium $profile"
    built=$((built + 1))
  done < "$HERE/profiles.tsv"
  eq "$built" "4" "liczba binariow profili"
  ok "cztery binaria K26: flagi i SHA zgodne"

  eq "$(sha256sum "$JAVA17" | awk '{print $1}')" "$EXPECTED_JAVA_SHA256" "SHA java"
  eq "$(sha256sum "$JAVAC17" | awk '{print $1}')" "$EXPECTED_JAVAC_SHA256" "SHA javac"
  eq "$(sha256sum "$FLINK_JAR" | awk '{print $1}')" "$EXPECTED_FLINK_JAR_SHA256" "SHA Flink"
  eq "$(wc -l < "$HERE/flink/oracle/canonical_oracle.tsv")" "18" "wektory oracle C++"
  awk -F'\t' '$1=="F9-X" && $2=="natural" && $3==8 {if ($5!="32.0000") exit 1; n++}
               $1=="F9-X" && $2=="manual" && $3==8 {if ($5!="5.0000") exit 1; n++}
               END {exit n==2 ? 0 : 1}' "$HERE/flink/results/flink_q_curve.tsv" \
    || fail "krzywa planu Flinka F9-X Q=8 jest inna niz 32/5"
  ok "JDK/Flink przypiete; serializer 18/18; F9-X plan natural/manual = 32/5"
}

check_worker() {
  echo "== zakres worker K26 (przed P6) =="
  [[ -r "$ANEKS_WORKER_ENV" && -r "$ANEKS_WORKER_BIN" ]] \
    || fail "brak ANEKS-2/ANEKS-3 — worker nie zostal jeszcze zamrozony"
  local frozen_kernel frozen_cpus live_kernel live_governor
  frozen_kernel="$(awk -F'\t' '$1=="kernel"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_cpus="$(awk -F'\t' '$1=="cpu_pinning"{print $2}' "$ANEKS_WORKER_ENV")"
  live_kernel="$(ssh -o BatchMode=yes "$WORKER_SSH" 'uname -r')" || fail "worker nieosiagalny"
  eq "$live_kernel" "$frozen_kernel" "kernel workera"
  live_governor="$(ssh -o BatchMode=yes "$WORKER_SSH" \
    'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr "\n" " "')"
  eq "${live_governor% }" "$EXPECTED_GOVERNOR" "governor workera"
  [[ -n "$frozen_cpus" ]] || fail "ANEKS-3 nie zawiera cpu_pinning"
  ok "worker: kernel, governor i przypiecie zamrozone"
}

check_matrix() {
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
  macierz)        check_host yes; check_worker; check_matrix ;;
  *)
    echo "uzycie: $(basename "$0") {preflight|predeklaracja|worker|macierz}" >&2
    echo "zakres jest obowiazkowy" >&2
    exit 2
    ;;
esac
