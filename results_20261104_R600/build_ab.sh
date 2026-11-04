#!/usr/bin/env bash
# R600: budowa profili Release-Probe A i B na workerze pi400.
# A = 42fcaa5d (zwolnienie porzuconej kolejki w watku slotu, z poprawka #599), B = 221d312b (#600, rodzicem jest A).
# Obie strony dostaja te sama latke aparatury P1 (kolumna deadline_ns w CSV sondy slotu), jak w R376.
# Jedno drzewo ~/R376/src (to samo co w R376): najpierw A, kopia binarek do ~/R376/bin/R600_A, potem B
# przyrostowo (roznica A->B to ipcServer.cpp/.hpp i test jednostkowy) i kopia do ~/R376/bin/R600_B.
# Obie binarki maja te same sciezki zrodel i budowy, wiec roznia sie wylacznie zmiana z #600.
# Binarki R376 (~/R376/bin/A, ~/R376/bin/B) zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R600.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus_R600/P1_deadline_ns.patch"
declare -A pin=([A]=42fcaa5db33928fa42fadbc8dd0b91816c0c13c9 [B]=221d312b86d42d1b3868fd7aac0703769f64b760)

git -C "$HOME/retractordb" fetch -q origin
git -C "$src" fetch -q "$HOME/retractordb" '+refs/remotes/origin/*:refs/remotes/origin/*'
for side in A B; do
  date -Is
  # -f: drzewo nosi latke P1 z poprzedniej strony (i z R376); reset ponizej i tak ja zdejmuje.
  git -C "$src" checkout -q -f --detach "${pin[$side]}"
  git -C "$src" reset -q --hard "${pin[$side]}"
  git -C "$src" apply "$patch"
  echo "== $side $(git -C "$src" rev-parse HEAD) diff:"
  git -C "$src" diff --stat
  (cd "$src" && scripts/buildrdb.sh probe)
  out="$root/bin/R600_$side"
  mkdir -p "$out"
  cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
  (cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R600_$side.sha256")
  "$out/xretractor" --build-info | tee "$root/bin/R600_$side.build-info"
done
date -Is
echo BUILD_COMPLETE
