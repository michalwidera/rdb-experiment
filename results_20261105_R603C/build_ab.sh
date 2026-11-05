#!/usr/bin/env bash
# R603C: budowa profili Release-Probe B i C na workerze pi400.
# B = 10f491b8 (#600; drzewo identyczne z 221d312b, strona B R600 i R603), C = 92faf689 (scalenie #604 z naprawa (a)
# c9e3e80e: pula kolejek odpowiedzi; pierwszym rodzicem jest B, drzewo identyczne z c9e3e80e).
# Obie strony dostaja te sama latke aparatury P1 (kolumna deadline_ns w CSV sondy slotu), jak w R600; bez P2 z R603.
# Jedno drzewo ~/R376/src (to samo co w R376/R600/R603): najpierw B, kopia binarek do ~/R376/bin/R603C_B, potem C
# przyrostowo (roznica B->C to ipcServer.cpp/.hpp, ipcSecurity.cpp/.hpp, constants.hpp i testy) i kopia do ~/R376/bin/R603C_C.
# Binarki R376, R600 i R603 zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R603C.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus_R603C/P1_deadline_ns.patch"
declare -A pin=([B]=10f491b8197108611e22ef822acdd45b1644282f [C]=92faf6896cad8d55ad8afbe35918f44218850758)

git -C "$HOME/retractordb" fetch -q origin
git -C "$src" fetch -q "$HOME/retractordb" '+refs/remotes/origin/*:refs/remotes/origin/*'
for side in B C; do
  date -Is
  # -f: drzewo nosi latki z poprzedniej strony (i z R603: P1+P2+P3); reset ponizej i tak je zdejmuje.
  git -C "$src" checkout -q -f --detach "${pin[$side]}"
  git -C "$src" reset -q --hard "${pin[$side]}"
  git -C "$src" apply "$patch"
  echo "== $side $(git -C "$src" rev-parse HEAD) diff:"
  git -C "$src" diff --stat
  (cd "$src" && scripts/buildrdb.sh probe)
  out="$root/bin/R603C_$side"
  mkdir -p "$out"
  cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
  (cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R603C_$side.sha256")
  "$out/xretractor" --build-info | tee "$root/bin/R603C_$side.build-info"
done
date -Is
echo BUILD_COMPLETE
