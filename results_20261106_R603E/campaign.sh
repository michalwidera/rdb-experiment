#!/usr/bin/env bash
# R603E: kampania - rodziny uc03 uc05 uc06 x 9 par C'/C'', kolejnosc w parze ABBA (para nieparzysta Cp Cpp,
# parzysta Cpp Cp; README R603E, Aparatura, punkt 3). Strumien subskrybowany w rodzinie czyta streams.tsv
# z aparatury R600 (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh [rodziny...] > ~/R376/campaign_R603E.log 2>&1 < /dev/null &
# Zmienne: R603E_PAIRS (liczba par, domyslnie 9), R603E_RAW (katalog wyjscia), R603E_CONNS (podlaczenia, domyslnie 30).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R603E_RAW:-$HOME/R376/raw_R603E}"
pairs="${R603E_PAIRS:-9}"
conns="${R603E_CONNS:-30}"
streams="$HOME/R376/apparatus_R600/streams.tsv"
families=("$@")
# uc07 i uc08 poza kampania (decyzja D0): seria miesci sie w przerwie po slocie, K2 bez slotow.
[ ${#families[@]} -eq 0 ] && families=(uc03 uc05 uc06)

# Binarka C' z R603D bez przebudowy: sumy jak w meta.json przebiegow R603D. Binarka C'' z build_ab.sh.
(cd "$HOME/R376/bin/R603D_Cp" && sha256sum -c "$HOME/R376/bin/R603D_Cp.sha256")
grep -q '^e435618bf853f0e3.*  xretractor$' "$HOME/R376/bin/R603D_Cp.sha256" || { echo "R603D_Cp: inny xretractor niz w R603D"; exit 2; }
grep -q '^4e8dd234b9214ebc.*  xqry$' "$HOME/R376/bin/R603D_Cp.sha256" || { echo "R603D_Cp: inny xqry niz w R603D"; exit 2; }
(cd "$HOME/R376/bin/R603E_Cpp" && sha256sum -c "$HOME/R376/bin/R603E_Cpp.sha256")

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

for fam in "${families[@]}"; do
  stream=$(awk -v f="$fam" '$1 == f {print $2}' "$streams")
  [ -n "$stream" ] || { echo "brak strumienia dla $fam w $streams"; exit 2; }
  for ((p = 1; p <= pairs; p++)); do
    if ((p % 2)); then order=(Cp Cpp); else order=(Cpp Cp); fi
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" --conns "$conns" \
        --out "$raw/$fam/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
