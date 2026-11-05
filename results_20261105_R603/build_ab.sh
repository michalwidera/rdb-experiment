#!/usr/bin/env bash
# R603: budowa profili Release-Probe B i B' (Bp) na workerze pi400.
# Obie strony: silnik 221d312b (strona B z R600, #600) + P1 (kolumna deadline_ns) + P2 (liczniki PMU w sondzie slotu).
# B' dodatkowo P3: zwolnienie mapowania porzuconej kolejki w kawalkach 1 MiB (ipcServer.cpp).
# Jedno drzewo ~/R376/src (to samo co w R376 i R600): najpierw B, kopia binarek do ~/R376/bin/R603_B, potem B'
# przyrostowo (roznica B -> B' to wylacznie ipcServer.cpp) i kopia do ~/R376/bin/R603_Bp.
# Binarki R376 i R600 zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R603.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
app="$root/apparatus_R603"
pin=221d312b86d42d1b3868fd7aac0703769f64b760
declare -A patches=([B]="P1_deadline_ns.patch P2_pmu_counters.patch"
                    [Bp]="P1_deadline_ns.patch P2_pmu_counters.patch P3_chunked_unmap.patch")

for side in B Bp; do
  date -Is
  # -f: drzewo nosi latki poprzedniej strony (i R600); reset ponizej i tak je zdejmuje.
  git -C "$src" checkout -q -f --detach "$pin"
  git -C "$src" reset -q --hard "$pin"
  for p in ${patches[$side]}; do git -C "$src" apply "$app/$p"; done
  echo "== $side $(git -C "$src" rev-parse HEAD) diff:"
  git -C "$src" diff --stat
  (cd "$src" && scripts/buildrdb.sh probe)
  out="$root/bin/R603_$side"
  mkdir -p "$out"
  cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
  (cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R603_$side.sha256")
  "$out/xretractor" --build-info | tee "$root/bin/R603_$side.build-info"
done
date -Is
echo BUILD_COMPLETE
