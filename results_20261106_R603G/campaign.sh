#!/usr/bin/env bash
# R603G: kampania - uc05, N z R603G_NS (domyslnie 1 8 32) x 9 par C'/D2s (README R603G, Obciazenie i przebieg).
# W parze p kolejnosc N przesunieta o p - 1; strony w parze nieparzystej Cp D2s, w parzystej D2s Cp.
# Strumien subskrybowany czyta streams.tsv z aparatury R600 (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh > ~/R376/campaign_R603G.log 2>&1 < /dev/null &
# Zmienne: R603G_PAIRS (domyslnie 9), R603G_NS (domyslnie "1 8 32"), R603G_RAW (katalog wyjscia), R603G_WINDOW (s, 60).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R603G_RAW:-$HOME/R376/raw_R603G}"
pairs="${R603G_PAIRS:-9}"
read -r -a ns <<< "${R603G_NS:-1 8 32}"
window="${R603G_WINDOW:-60}"
fam=uc05
streams="$HOME/R376/apparatus_R600/streams.tsv"

# Binarki z R603D (C') i R603F (D2s) bez przebudowy: sumy jak w R603F; xqry obu stron z R603D_Cp (G3).
(cd "$HOME/R376/bin/R603D_Cp" && sha256sum -c "$HOME/R376/bin/R603D_Cp.sha256")
grep -q '^e435618bf853f0e3.*  xretractor$' "$HOME/R376/bin/R603D_Cp.sha256" || { echo "R603D_Cp: inny xretractor niz w R603D"; exit 2; }
grep -q '^4e8dd234b9214ebc.*  xqry$' "$HOME/R376/bin/R603D_Cp.sha256" || { echo "R603D_Cp: inny xqry niz w R603D"; exit 2; }
(cd "$HOME/R376/bin/R603F_D2s" && sha256sum -c "$HOME/R376/bin/R603F_D2s.sha256")
grep -q '^7c02c52cc9014765.*  xretractor$' "$HOME/R376/bin/R603F_D2s.sha256" || { echo "R603F_D2s: inny xretractor niz w R603F"; exit 2; }
diff "$HOME/R376/bin/R603D_Cp.build-info" "$HOME/R376/bin/R603F_D2s.build-info" > /dev/null || { echo "build-info D2s != Cp"; exit 2; }

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

stream=$(awk -v f="$fam" '$1 == f {print $2}' "$streams")
[ -n "$stream" ] || { echo "brak strumienia dla $fam w $streams"; exit 2; }
for ((p = 1; p <= pairs; p++)); do
  if ((p % 2)); then order=(Cp D2s); else order=(D2s Cp); fi
  for ((i = 0; i < ${#ns[@]}; i++)); do
    n=${ns[$(((i + p - 1) % ${#ns[@]}))]}
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam N=$n pair=$p side=$side"
      python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --n "$n" --stream "$stream" \
        --window "$window" --out "$raw/$fam/N$n/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
