#!/usr/bin/env bash
# R376b: powtorzenie uc05 z R376 - 9 par A/B, kolejnosc w parze ABBA (para nieparzysta AB, parzysta BA),
# 60 podlaczen na przebieg. Binarki A i B z kampanii R376, bez przebudowy (README, Strony porownania).
# Lezy w ~/R376/apparatus_R376b obok kopii run_one.py R376 (bez zmian) i streams.tsv (tylko na workerze).
# Uruchamiac odczepione: setsid nohup ./campaign.sh > ~/R376/campaign_R376b.log 2>&1 < /dev/null &
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
raw="${R376B_RAW:-$HOME/R376/raw_R376b}"
pairs="${R376B_PAIRS:-9}"
fam=uc05
conns=60

# Sumy z meta.json przebiegow uc05 R376 (archiwum rdb-experiment-embargo/R376/, 9 przebiegow na strone, jednakowe).
declare -A want=(
  [A/xretractor]=6e84c5497ecab47717ec4bf88491f578c0c9e3ec65213160c7f19fb0901a432d
  [A/xqry]=2f6004834740f006ef019dc65ebb25fc6cb27453bf02fedb1adbe765dace5f05
  [B/xretractor]=d01c95d5888e9c2bf01b1d400fab10e399bb2a13cb9e4a559661bc0aa33e6bd5
  [B/xqry]=6bfdb5ee2b844f69ff88771e0c3f37a0fea9dac5ee533975a2fe3f6497e4da8d
)
for f in "${!want[@]}"; do
  got=$(sha256sum "$HOME/R376/bin/$f" | cut -d' ' -f1)
  [ "$got" = "${want[$f]}" ] || { echo "suma $f: $got, oczekiwana ${want[$f]} - kampania zatrzymana"; exit 2; }
  echo "suma $f zgodna z R376"
done

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  echo performance | sudo -n tee "$cpu" > /dev/null
done

stream=$(awk -v f="$fam" '$1 == f {print $2}' "$here/streams.tsv")
[ -n "$stream" ] || { echo "brak strumienia dla $fam w streams.tsv"; exit 2; }
for ((p = 1; p <= pairs; p++)); do
  if ((p % 2)); then order=(A B); else order=(B A); fi
  for side in "${order[@]}"; do
    echo "$(date -Is) $fam pair=$p side=$side shm_used_kB=$(df --output=used /dev/shm | tail -1)"
    python3 -I "$here/run_one.py" --side "$side" --family "$fam" --run "$p" --stream "$stream" --conns "$conns" \
      --out "$raw/$fam/${side}_$(printf %02d "$p")" || echo "$(date -Is) przebieg ${side}_$p NIEWAZNY, kod $? (bez powtorzenia)"
  done
done
echo CAMPAIGN_COMPLETE
