#!/usr/bin/env bash
# R607: kampania - uc05, N z R607_NS (domyslnie 1 8 16) x 9 par D2s/D2r (README R607, Obciazenie i przebieg).
# W parze p kolejnosc N przesunieta o p - 1; strony w parze nieparzystej D2s D2r, w parzystej D2r D2s.
# Strumien subskrybowany czyta streams.tsv z aparatury R600 (rodzina<TAB>strumien), plik tylko na workerze.
# Uruchamiac odczepione: setsid nohup ./campaign.sh > ~/R376/campaign_R607.log 2>&1 < /dev/null &
# Zmienne: R607_PAIRS (domyslnie 9), R607_NS (domyslnie "1 8 16"), R607_RAW (katalog wyjscia), R607_WINDOW (s, 60).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R607_RAW:-$HOME/R376/raw_R607}"
pairs="${R607_PAIRS:-9}"
read -r -a ns <<< "${R607_NS:-1 8 16}"
window="${R607_WINDOW:-60}"
fam=uc05
streams="$HOME/R376/apparatus_R600/streams.tsv"

# D2s z R603F bez przebudowy, D2r z build_ab.sh; xqry obu stron z R603D_Cp (J4, jak G3 R603G).
(cd "$HOME/R376/bin/R603D_Cp" && sha256sum -c "$HOME/R376/bin/R603D_Cp.sha256")
grep -q '^4e8dd234b9214ebc.*  xqry$' "$HOME/R376/bin/R603D_Cp.sha256" || { echo "R603D_Cp: inny xqry niz w R603D"; exit 2; }
(cd "$HOME/R376/bin/R603F_D2s" && sha256sum -c "$HOME/R376/bin/R603F_D2s.sha256")
grep -q '^7c02c52cc9014765.*  xretractor$' "$HOME/R376/bin/R603F_D2s.sha256" || { echo "R603F_D2s: inny xretractor niz w R603F"; exit 2; }
(cd "$HOME/R376/bin/R607_D2r" && sha256sum -c "$HOME/R376/bin/R607_D2r.sha256")
diff "$HOME/R376/bin/R603F_D2s.build-info" "$HOME/R376/bin/R607_D2r.build-info" > /dev/null || { echo "build-info D2r != D2s"; exit 2; }

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

stream=$(awk -v f="$fam" '$1 == f {print $2}' "$streams")
[ -n "$stream" ] || { echo "brak strumienia dla $fam w $streams"; exit 2; }
for ((p = 1; p <= pairs; p++)); do
  if ((p % 2)); then order=(D2s D2r); else order=(D2r D2s); fi
  for ((i = 0; i < ${#ns[@]}; i++)); do
    n=${ns[$(((i + p - 1) % ${#ns[@]}))]}
    for side in "${order[@]}"; do
      echo "$(date -Is) $fam N=$n pair=$p side=$side"
      # Aneks A4(b) R603G: runner (i jego sudo) na rdzeniach 1-2; silnik startuje z wlasnym taskset -c 3.
      taskset -c 1,2 python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --n "$n" --stream "$stream" \
        --window "$window" --out "$raw/$fam/N$n/${side}_$(printf %02d "$p")"
    done
  done
done
echo CAMPAIGN_COMPLETE
