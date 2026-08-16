#!/usr/bin/env bash
# P7 — KALIBRACJA RATE. Przebiegi na DANYCH KALIBRACYJNYCH, worker.
#
# Co ten skrypt robi i czego NIE robi
# -----------------------------------
# Uruchamia plan Q=32 każdej rodziny w każdym z czterech profili, dla drabiny
# czynników `rate_scale`, i zbiera CSV sondy slotu (`iter,compute_ns,wake_lag_ns,
# e2e_ns`). Kryterium PREDEKLARACJI §12: NAJGORSZY profil przy Q=32 ma
# `p99 <= 50%` logicznego slotu.
#
# Czego NIE robi, i to jest istotne dla ważności kampanii (§12, §12.1):
#   * NIE porównuje DEFAULT z ablacją — profile wchodzą tylko po to, żeby wziąć
#     z nich MAKSIMUM; żaden iloraz DEFAULT/ablacja nie jest liczony ani
#     wypisywany. To jest treść pola `calibration_saw_effect=no` w ANEKS-1;
#   * NIE czyta metryki pierwotnej (bajtów substratów) ani liczników LOGICAL/WORK;
#   * NIE dotyka danych głównych — wyłącznie `data/calib/` (ziarno 20260809_2602).
#
# Dlaczego bez `-t`
# -----------------
# Kryterium dotyczy `compute_ns`, czyli czasu `processRows()`. Ta wielkość nie
# zależy od trybu snu — `-t` zmienia wyłącznie sposób budzenia (absolutny wobec
# kotwicy), więc wpływa na `wake_lag_ns` i `e2e_ns`, których kryterium §12 nie
# używa. Bez `-t` nie trzeba SCHED_FIFO ani uprawnień roota, a przypięcie do
# odizolowanego rdzenia 3 (ANEKS-3: `isolcpus=3`) i tak odcina rywalizację.
#
# Wynik: $OUT/<profil>/<rodzina>_s<skala>/{slot.csv,run.out,run.rc}
set -euo pipefail

cd "$(dirname "$0")"
HERE="$(pwd)"
# Kalibracja biegnie NA WORKERZE, wiec domyslna wartosc to workerowe repozytorium
# biezacej kampanii. W K26v2 stalo tu $HOME/K26 — katalog uniewaznionej kampanii
# z innymi binariami (D2); defekt byl fail-closed, ale domyslna wartosc nie moze
# wskazywac cudzej kampanii.
CODE_REPO="${CODE_REPO:-$HOME/K26v3}"
OUT="${OUT:-$HOME/k26v3_calib}"
CPU="${CPU:-3}"

profiles=(DEFAULT NO_R2_CANON NO_R1_FACTOR NO_R1_NO_R2)
families=(F9_R2 F9_R1 F9_X)
scales=(1_4 1_2 1_1 2_1 4_1)

# `-m` jest limitem ITERACJI PĘTLI, nie licznikiem rekordów, i NIE zależy od
# rate'u: przeskalowanie osi czasu zmienia długość przebiegu w sekundach, a nie
# liczbę slotów. Wartości to przelicznik zmierzony w P6 podzielony przez 5,
# bo dane kalibracyjne są 5x krótsze (600/300 wobec 3000/1500).
slots_for() {
  case "$1" in
    F9_R2) echo 600 ;;
    F9_R1|F9_X) echo 1200 ;;
    *) echo "BLAD: nieznana rodzina $1" >&2; exit 2 ;;
  esac
}

# Osłona MUSI siedzieć w skrypcie: `pgrep -af '[x]retractor'` przekazany przez
# ssh w jednolinijkowcu łapie sam siebie i cicho nie uruchamia przebiegu
# (pułapka potwierdzona w P6).
if pgrep -x xretractor >/dev/null; then
  echo "BLAD: w systemie biegnie xretractor — najpierw sprzatnij" >&2
  pgrep -af '[x]retractor' >&2
  exit 2
fi

# Governor nie przeżywa wyłączenia zasilania. Sprawdzamy, nie zakładamy.
gov="$(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor 2>/dev/null || echo nieznany)"
if [ "$gov" != "performance" ]; then
  echo "BLAD: governor rdzenia $CPU to '$gov', wymagane 'performance' (ANEKS-3)" >&2
  exit 2
fi
echo "governor cpu$CPU: $gov"

[[ "$OUT" = /* ]] || { echo "BLAD: OUT musi byc sciezka bezwzgledna" >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo "BLAD: $OUT juz istnieje; odmowa nadpisania kalibracji" >&2; exit 2; }
mkdir -p "$OUT/plans"
for scale in "${scales[@]}"; do
  "$HERE/gen_calib.py" --scale "${scale/_//}" --out "$OUT/plans" >/dev/null
done
runs=0

for profile in "${profiles[@]}"; do
  binary="$CODE_REPO/build/K26v3-$profile/src/retractor/xretractor"
  [ -x "$binary" ] || { echo "BLAD: brak binarki profilu $profile" >&2; exit 2; }
  echo "== profil $profile =="
  for family in "${families[@]}"; do
    slots="$(slots_for "$family")"
    for scale in "${scales[@]}"; do
      dir="$OUT/$profile/${family}_s${scale}"
      mkdir -p "$dir/temp"
      ( cd "$dir"
        cp "$OUT/plans/${family}_Q32_s${scale}.rql" p.rql
        cp "$HERE"/../data/calib/*.txt .
        set +e
        RDB_BENCH_CSV="$dir/slot.csv" timeout 600 \
          taskset -c "$CPU" "$binary" p.rql -m "$slots" -r -k >run.out 2>&1
        echo $? >run.rc
        set -e
        rm -f ./*.txt p.rql
      )
      rc="$(cat "$dir/run.rc")"
      rows=$(( $(wc -l <"$dir/slot.csv" 2>/dev/null || echo 1) - 1 ))
      if [ "$rc" != "0" ] || [ "$rows" -lt 100 ]; then
        echo "BLAD: $profile/${family}_s${scale} rc=$rc wierszy=$rows" >&2
        tail -3 "$dir/run.out" >&2
        exit 3
      fi
      printf '  ok  %-12s skala %-5s wierszy=%s\n' "$family" "$scale" "$rows"
      runs=$((runs + 1))
    done
  done
done

echo
echo "OK: $runs przebiegow kalibracyjnych, kazdy z niepusta sonda slotu"
