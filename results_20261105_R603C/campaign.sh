#!/usr/bin/env bash
# R603C: kampania - rodziny uc03 uc05 uc06 uc07 uc08 x 9 par B/C, kolejnosc w parze ABBA (para nieparzysta B C, parzysta C B).
# Strumien subskrybowany w rodzinie czyta streams.tsv z aparatury R600 (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh [rodziny...] > ~/R376/campaign_R603C.log 2>&1 < /dev/null &
# Zmienne: R603C_PAIRS (liczba par, domyslnie 9), R603C_RAW (katalog wyjscia), R603C_CONNS (podlaczenia, domyslnie 30).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R603C_RAW:-$HOME/R376/raw_R603C}"
pairs="${R603C_PAIRS:-9}"
conns="${R603C_CONNS:-30}"
streams="$HOME/R376/apparatus_R600/streams.tsv"
families=("$@")
# uc01 i uc02 nasycone na pi400 pod -t (R376); uc04 nie zwalnia kolejki w czasie przebiegu (R376, metryka 5).
[ ${#families[@]} -eq 0 ] && families=(uc03 uc05 uc06 uc07 uc08)

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

for fam in "${families[@]}"; do
  stream=$(awk -v f="$fam" '$1 == f {print $2}' "$streams")
  [ -n "$stream" ] || { echo "brak strumienia dla $fam w $streams"; exit 2; }
  for ((p = 1; p <= pairs; p++)); do
    if ((p % 2)); then order=(B C); else order=(C B); fi
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" --conns "$conns" \
        --out "$raw/$fam/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
