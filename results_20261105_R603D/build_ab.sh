#!/usr/bin/env bash
# R603D: budowa profilu Release-Probe strony C' na workerze pi400 (README R603D, Aparatura, punkt 1).
# C' = e0857dc8 (scalenie #605: drenaz w porcjach a33b584c; pierwszym rodzicem jest C = 92faf689, drzewo = a33b584c).
# Strona C NIE jest przebudowywana (decyzja D3): ~/R376/bin/R603C_C z R603C, suma sprawdzana tu i w campaign.sh.
# Latka aparatury P1 (kolumna deadline_ns w CSV sondy slotu) jak w R600/R603C; bez P2.
# Jedno drzewo ~/R376/src (to samo co w R376/R600/R603/R603C): C' przyrostowo po C (roznica: constants.hpp,
# ipcServer.cpp/.hpp, test_ipcServer.cpp), kopia binarek do ~/R376/bin/R603D_Cp. Pozostale binarki zostaja nietkniete.
# Uruchamiac odczepione: setsid nohup ./build_ab.sh > ~/R376/build_R603D.log 2>&1 < /dev/null &
set -euo pipefail

# Sesja odczepiona nie czyta ~/.bashrc: conan i ~/.local/bin trzeba podac jawnie.
source "$HOME/.venv/bin/activate"
export PATH="$HOME/.local/bin:$PATH"

root="$HOME/R376"
src="$root/src"
patch="$root/apparatus_R603D/P1_deadline_ns.patch"
pin=e0857dc8ba5387929c0e79d172cb8c45a669e3a3

(cd "$root/bin/R603C_C" && sha256sum -c "$root/bin/R603C_C.sha256")

git -C "$HOME/retractordb" fetch -q origin
git -C "$src" fetch -q "$HOME/retractordb" '+refs/remotes/origin/*:refs/remotes/origin/*'
date -Is
# -f: drzewo nosi latke P1 strony C; reset ponizej i tak ja zdejmuje.
git -C "$src" checkout -q -f --detach "$pin"
git -C "$src" reset -q --hard "$pin"
git -C "$src" apply "$patch"
echo "== Cp $(git -C "$src" rev-parse HEAD) diff:"
git -C "$src" diff --stat
(cd "$src" && scripts/buildrdb.sh probe)
out="$root/bin/R603D_Cp"
mkdir -p "$out"
cp -p "$src/build/Release-Probe/src/retractor/xretractor" "$src/build/Release-Probe/src/qry/xqry" "$out/"
(cd "$out" && sha256sum xretractor xqry | tee "$root/bin/R603D_Cp.sha256")
"$out/xretractor" --build-info | tee "$root/bin/R603D_Cp.build-info"
# --build-info nie niesie rewizji: przelaczniki RDB_OPT_* i sonda musza byc identyczne z C (set -e przerywa przy roznicy).
diff "$root/bin/R603C_C.build-info" "$root/bin/R603D_Cp.build-info" && echo "build-info C == Cp"
date -Is
echo BUILD_COMPLETE
