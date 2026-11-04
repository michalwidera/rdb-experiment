#!/usr/bin/env bash
# R376: budowa profili Release-Probe A i B na workerze pi400.
# A = 96b74dc0 (subscribe() pod plan_epoch_mutex), B = 393b24ca (#283, rodzicem jest A).
# Obie strony dostaja te sama latke aparatury P1 (kolumna deadline_ns w CSV sondy slotu).
# Jedno drzewo ~/R376/src: najpierw A, kopia binarek do ~/R376/bin/A, potem B przyrostowo
# (roznica A->B to trzy pliki silnika) i kopia do ~/R376/bin/B. Obie binarki maja te same
# sciezki zrodel i budowy, wiec roznia sie wylacznie zmiana z #283.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus/P1_deadline_ns.patch"
declare -A pin=([A]=96b74dc0ad66df3c645d239145b8821eaceacb8d [B]=393b24ca08bbd1692079a97e6ee107115814789f)

git -C "$HOME/retractordb" fetch -q origin
[ -d "$src/.git" ] || git clone -q "$HOME/retractordb" "$src"
for side in A B; do
  git -C "$src" checkout -q --detach "${pin[$side]}"
  git -C "$src" reset -q --hard "${pin[$side]}"
  git -C "$src" apply "$patch"
  echo "== $side $(git -C "$src" rev-parse HEAD) diff:"
  git -C "$src" diff --stat
  (cd "$src" && scripts/buildrdb.sh probe)
  out="$root/bin/$side"
  mkdir -p "$out"
  cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
  (cd "$out" && sha256sum xretractor xqry | tee "$root/bin/$side.sha256")
  "$out/xretractor" --build-info | tee "$root/bin/$side.build-info"
done
echo BUILD_COMPLETE
