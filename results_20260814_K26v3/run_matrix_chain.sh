#!/usr/bin/env bash
# Lancuch P8 K26v3 po stronie workera, uruchamiany wylacznie przez systemd.
#
# Jedno wywolanie obsluguje DOKLADNIE JEDNA rodzine: wybiera pierwsza bez
# `RUN_COMPLETE`, liczy ja z wznowieniem, a potem prosi o restart workera.
# Usluga jest wlaczona na `multi-user.target`, wiec po restarcie systemd
# uruchamia ja ponownie i lancuch idzie dalej. Dzieki temu zanik zasilania nie
# rozni sie niczym od restartu miedzy rodzinami — te same dwie sciezki, jedna
# obsluga. Host nie jest potrzebny do niczego miedzy rodzinami.
#
# `Restart=no` w unicie jest celowe: STOP-8 i blad aparatury maja zatrzymac
# lancuch, a nie zapetlic go w kolko. Zatrzymanie zostawia plik HALT, ktory
# blokuje kazde nastepne wejscie az do decyzji czlowieka.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAMILIES=(F9-R2 F9-R1 F9-X)

CPU="${CPU:-3}"
CODE_REPO="${CODE_REPO:-/home/michal/K26v3}"
P6_RDB="${P6_RDB:-/home/michal/k26v3_gates_rdb}"
P8_OUT="${P8_OUT:-/home/michal/k26v3_p8}"
ARCHIVES="${ARCHIVES:-/home/michal/k26v3_archives}"
CONTROL="${CONTROL:-/home/michal/k26v3_control}"
FAMILY_SCRIPT="${FAMILY_SCRIPT:-$HERE/run_matrix_family.sh}"
UNIT="${UNIT:-k26v3-p8.service}"
SUDO="${SUDO:-sudo -n}"
# Po boocie dajemy maszynie ostygnac i dojsc do siebie; to tez jedyne okno, w
# ktorym czlowiek moze zatrzymac niechciany start (`systemctl stop`).
SETTLE_SECONDS="${SETTLE_SECONDS:-60}"

log() { printf '%s %s\n' "$(date '+%F %T %Z')" "$*"; }

family=""

halt() {
  local reason="$1" rc="$2"
  printf 'reason\t%s\nfamily\t%s\nrc\t%s\nepoch\t%s\n' \
    "$reason" "$family" "$rc" "$(date +%s)" >"$P8_OUT/HALT"
  log "HALT: $reason (rodzina=${family:-brak} rc=$rc); lancuch zatrzymany do decyzji czlowieka"
  exit "$rc"
}

disable_unit() {
  # Po komplecie usluga nie moze wstawac przy kazdym nastepnym boocie.
  $SUDO systemctl disable "$UNIT" >/dev/null 2>&1 \
    || log "OSTRZEZENIE: nie udalo sie wylaczyc $UNIT"
}

complete_chain() {
  printf '%s/%s rodzin\n' "${#FAMILIES[@]}" "${#FAMILIES[@]}" >"$P8_OUT/P8_COMPLETE"
  log "P8_COMPLETE: ${#FAMILIES[@]}/${#FAMILIES[@]} rodzin; archiwa czekaja w $ARCHIVES"
  disable_unit
  exit 0
}

# Rodzina liczy sie za zrobiona dopiero z ARCHIWUM I JEGO SUMA, nie z samym
# `RUN_COMPLETE`. Runner zapisuje `RUN_COMPLETE`, potem pakuje archiwum, a na
# koncu jego sume — twarde wylaczenie miedzy tymi krokami zostawiloby rodzine
# policzona i bez archiwum, ktorego nikt by juz nie zrobil. Plik sumy powstaje
# po zamknieciu tar-a, wiec jego obecnosc jest znacznikiem zamkniecia rodziny.
family_done() {
  local candidate="$1"
  [[ -e "$P8_OUT/$candidate/RUN_COMPLETE" && -s "$ARCHIVES/K26v3-P8-$candidate.sha256" ]]
}

incomplete_families() {
  local candidate count=0
  for candidate in "${FAMILIES[@]}"; do
    family_done "$candidate" || count=$((count + 1))
  done
  printf '%s\n' "$count"
}

[[ -x "$FAMILY_SCRIPT" ]] || { log "BLAD: brak wykonywalnego $FAMILY_SCRIPT"; exit 2; }
mkdir -p "$P8_OUT" "$CONTROL"

if [[ -e "$P8_OUT/HALT" ]]; then
  log "zastany HALT w $P8_OUT/HALT — lancuch nie rusza bez decyzji czlowieka"
  cat "$P8_OUT/HALT"
  exit 2
fi
if [[ -e "$P8_OUT/P8_COMPLETE" ]]; then
  log "P8 juz kompletne; nic do zrobienia"
  disable_unit
  exit 0
fi

log "start lancucha; odczekanie $SETTLE_SECONDS s po boocie"
sleep "$SETTLE_SECONDS"

# Governor przezywa reboot jako `ondemand`, wiec ustawiamy go po kazdym boocie.
$SUDO sh -c 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance >"$f"; done' \
  || { log "BLAD: nie udalo sie ustawic governora performance"; exit 2; }

for candidate in "${FAMILIES[@]}"; do
  if ! family_done "$candidate"; then
    family="$candidate"
    break
  fi
done
[[ -n "$family" ]] || complete_chain

# Archiwum urwane w polowie pakowania blokowaloby runner ("archiwum juz
# istnieje"), a status poprzedniego podejscia — wrapper rodziny. Rodzina jest
# tu OTWIERANA PONOWNIE, wiec paczka znika, a status idzie do historii: reguly
# "jeden status na zamknieta rodzine" nie lamiemy, tylko przesuwamy zamkniecie.
if [[ -e "$P8_OUT/$family/RUN_COMPLETE" ]]; then
  log "rodzina $family policzona, ale bez zamknietego archiwum; powtarzam samo pakowanie"
  rm -f "$ARCHIVES/K26v3-P8-$family.tar.gz" "$ARCHIVES/K26v3-P8-$family.sha256"
  if [[ -e "$CONTROL/$family/runner.rc" ]]; then
    mv "$CONTROL/$family/runner.rc" "$CONTROL/$family/runner.rc.$(date +%s)"
  fi
fi

log "START: rodzina $family (pozostalo $(incomplete_families) z ${#FAMILIES[@]})"
mkdir -p "$CONTROL/$family"
rc=0
RESUME=1 "$FAMILY_SCRIPT" "$family" "$CPU" "$CODE_REPO" "$P6_RDB" \
  "$P8_OUT/$family" "$ARCHIVES" "$CONTROL/$family" || rc=$?

if (( rc != 0 )); then
  if [[ -e "$P8_OUT/$family/STOP-8" ]]; then halt stop8 "$rc"; fi
  halt apparatus "$rc"
fi
[[ -e "$P8_OUT/$family/RUN_COMPLETE" ]] || halt apparatus_bez_run_complete 2
log "KONIEC: rodzina $family rc=0, RUN_COMPLETE"

if (( $(incomplete_families) == 0 )); then
  complete_chain
fi

log "restart workera przed nastepna rodzina; usluga wstanie sama z bootu"
sync
$SUDO systemctl --no-block reboot || { log "BLAD: restart workera odrzucony"; exit 2; }
exit 0
