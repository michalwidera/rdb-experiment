#!/usr/bin/env bash
# R603F: budowa profilu Release-Probe strony D2s na workerze pi400 (README R603F, Aparatura, punkt 1).
# D2s = 75e7574c (dev/muro): sonda zycia subskrybentow w watku komunikacyjnym; drzewo = e0857dc8 (C') + sonda,
# C'' (d105498a) wycofany w 71272b8f.
# Strona C' NIE jest przebudowywana: ~/R376/bin/R603D_Cp z R603D, suma sprawdzana tu i w campaign.sh.
# Latka aparatury P1 (kolumna deadline_ns w CSV sondy slotu) jak w R600/R603C/R603D/R603E; bez P2.
# Jedno drzewo ~/R376/src (to samo co w R376..R603E): D2s przyrostowo po C'' (d105498a + P1), kopia binarek do
# ~/R376/bin/R603F_D2s. Pozostale binarki zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R603F.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus_R603F/P1_deadline_ns.patch"
pin=75e7574cf90d7548b1d95c7cef5a80e9b5700f91

(cd "$root/bin/R603D_Cp" && sha256sum -c "$root/bin/R603D_Cp.sha256")

git -C "$HOME/retractordb" fetch -q origin
git -C "$src" fetch -q "$HOME/retractordb" '+refs/remotes/origin/*:refs/remotes/origin/*'
date -Is
# -f: drzewo nosi latke P1 strony C''; reset ponizej i tak ja zdejmuje.
git -C "$src" checkout -q -f --detach "$pin"
git -C "$src" reset -q --hard "$pin"
git -C "$src" apply "$patch"
echo "== D2s $(git -C "$src" rev-parse HEAD) diff:"
git -C "$src" diff --stat
(cd "$src" && scripts/buildrdb.sh probe)
out="$root/bin/R603F_D2s"
mkdir -p "$out"
cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
(cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R603F_D2s.sha256")
"$out/xretractor" --build-info | tee "$root/bin/R603F_D2s.build-info"
# --build-info nie niesie rewizji: przelaczniki RDB_OPT_* i sonda musza byc identyczne z C' (set -e przerywa przy roznicy).
diff "$root/bin/R603D_Cp.build-info" "$root/bin/R603F_D2s.build-info" && echo "build-info Cp == D2s"
date -Is
echo BUILD_COMPLETE
