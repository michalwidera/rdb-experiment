#!/usr/bin/env bash
# R603: kampania - rodziny uc05 uc06 x 9 par B/B' (Bp), kolejnosc w parze ABBA (para nieparzysta B Bp, parzysta Bp B).
# Strumien subskrybowany w rodzinie czyta streams.tsv (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh [rodziny...] > ~/R376/campaign_R603.log 2>&1 < /dev/null &
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="$HOME/R376/raw_R603"
pairs="${R603_PAIRS:-9}"
families=("$@")
# Tylko uc05 i uc06: jedyne rodziny, w ktorych K2 R600 bylo rozstrzygalne.
[ ${#families[@]} -eq 0 ] && families=(uc05 uc06)

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

for fam in "${families[@]}"; do
  stream=$(awk -v f="$fam" '$1 == f {print $2}' "$here/streams.tsv")
  [ -n "$stream" ] || { echo "brak strumienia dla $fam w streams.tsv"; exit 2; }
  for ((p = 1; p <= pairs; p++)); do
    if ((p % 2)); then order=(B Bp); else order=(Bp B); fi
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" \
        --out "$raw/$fam/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
