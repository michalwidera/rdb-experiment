#!/usr/bin/env bash
# R607: budowa profilu Release-Probe strony D2r na workerze pi400 (README R607, Aparatura, punkt 1).
# D2r = 4daec944 (dev/muro, retractordb #607): sonda zycia rozlozona na obroty watku komunikacyjnego, najwyzej jedno
# inspectProcess na obrot. Wobec D2s (75e7574c) zmienia tylko ipcServer.{hpp,cpp}, komentarz w constants.hpp i testy.
# Strona D2s NIE jest przebudowywana: ~/R376/bin/R603F_D2s z R603F, suma sprawdzana tu i w campaign.sh.
# Latka aparatury P1 (kolumna deadline_ns w CSV sondy slotu) bez zmian z R603F.
# Jedno drzewo ~/R376/src (to samo co w R376..R603F): D2r przyrostowo po D2s (75e7574c + P1), kopia binarek do
# ~/R376/bin/R607_D2r. Pozostale binarki zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R607.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus_R603F/P1_deadline_ns.patch"
pin=4daec944e8d76c9e95ccdea8f0e43074c5460613

(cd "$root/bin/R603F_D2s" && sha256sum -c "$root/bin/R603F_D2s.sha256")

git -C "$HOME/retractordb" fetch -q origin
git -C "$src" fetch -q "$HOME/retractordb" '+refs/remotes/origin/*:refs/remotes/origin/*'
date -Is
# -f: drzewo nosi latke P1 strony D2s; reset ponizej i tak ja zdejmuje.
git -C "$src" checkout -q -f --detach "$pin"
git -C "$src" reset -q --hard "$pin"
git -C "$src" apply "$patch"
echo "== D2r $(git -C "$src" rev-parse HEAD) diff:"
git -C "$src" diff --stat
(cd "$src" && scripts/buildrdb.sh probe)
out="$root/bin/R607_D2r"
mkdir -p "$out"
cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
(cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R607_D2r.sha256")
"$out/xretractor" --build-info | tee "$root/bin/R607_D2r.build-info"
# --build-info nie niesie rewizji: przelaczniki RDB_OPT_* i sonda musza byc identyczne z D2s (set -e przerywa przy roznicy).
diff "$root/bin/R603F_D2s.build-info" "$root/bin/R607_D2r.build-info" && echo "build-info D2s == D2r"
date -Is
echo BUILD_COMPLETE
