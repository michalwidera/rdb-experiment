#!/usr/bin/env bash
# R600: kampania - rodziny uc03 uc05 uc06 uc07 uc08 x 9 par A/B, kolejnosc w parze ABBA (para nieparzysta AB, parzysta BA).
# Strumien subskrybowany w rodzinie czyta streams.tsv (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh [rodziny...] > ~/R376/campaign.log 2>&1 < /dev/null &
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="$HOME/R376/raw_R600"
pairs="${R600_PAIRS:-9}"
families=("$@")
# uc01 i uc02 nasycone na pi400 pod -t (R376); uc04 nie zwalnia kolejki w czasie przebiegu (R376, metryka 5).
[ ${#families[@]} -eq 0 ] && families=(uc03 uc05 uc06 uc07 uc08)

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

for fam in "${families[@]}"; do
  stream=$(awk -v f="$fam" '$1 == f {print $2}' "$here/streams.tsv")
  [ -n "$stream" ] || { echo "brak strumienia dla $fam w streams.tsv"; exit 2; }
  for ((p = 1; p <= pairs; p++)); do
    if ((p % 2)); then order=(A B); else order=(B A); fi
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" \
        --out "$raw/$fam/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
