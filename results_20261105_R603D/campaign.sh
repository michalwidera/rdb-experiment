#!/usr/bin/env bash
# R603D: kampania - rodziny uc03 uc05 uc06 uc07 uc08 x 9 par C/C', kolejnosc w parze ABBA (para nieparzysta C Cp,
# parzysta Cp C). Strumien subskrybowany w rodzinie czyta streams.tsv z aparatury R600 (rodzina<TAB>strumien),
# plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh [rodziny...] > ~/R376/campaign_R603D.log 2>&1 < /dev/null &
# Zmienne: R603D_PAIRS (liczba par, domyslnie 9), R603D_RAW (katalog wyjscia), R603D_CONNS (podlaczenia, domyslnie 30).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R603D_RAW:-$HOME/R376/raw_R603D}"
pairs="${R603D_PAIRS:-9}"
conns="${R603D_CONNS:-30}"
streams="$HOME/R376/apparatus_R600/streams.tsv"
families=("$@")
# uc01 i uc02 nasycone na pi400 pod -t (R376); uc04 nie zwalnia kolejki w czasie przebiegu (R376, metryka 5).
[ ${#families[@]} -eq 0 ] && families=(uc03 uc05 uc06 uc07 uc08)

# Binarka C z R603C bez przebudowy (decyzja D3): sumy jak w meta.json przebiegow R603C. Binarka C' z build_ab.sh.
(cd "$HOME/R376/bin/R603C_C" && sha256sum -c "$HOME/R376/bin/R603C_C.sha256")
grep -q '^3458ed9915c5925a' "$HOME/R376/bin/R603C_C.sha256" || { echo "R603C_C: inna binarka niz w R603C"; exit 2; }
(cd "$HOME/R376/bin/R603D_Cp" && sha256sum -c "$HOME/R376/bin/R603D_Cp.sha256")

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

for fam in "${families[@]}"; do
  stream=$(awk -v f="$fam" '$1 == f {print $2}' "$streams")
  [ -n "$stream" ] || { echo "brak strumienia dla $fam w $streams"; exit 2; }
  for ((p = 1; p <= pairs; p++)); do
    if ((p % 2)); then order=(C Cp); else order=(Cp C); fi
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" --conns "$conns" \
        --out "$raw/$fam/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
