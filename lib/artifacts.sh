#!/usr/bin/env bash
# Higiena artefaktów badań — `REQUIREMENTS.md` R14, strona powłoki.
#
# Użycie w `run.sh` kampanii:
#
#   source "$experiment_repo/lib/artifacts.sh"
#   artifacts_pack_on_exit results/raw results/workloads
#
# Pułapka `EXIT` pakuje wskazane katalogi również wtedy, gdy badanie przerwał
# błąd — dowód porażki musi zostać zachowany w tej samej formie co dowód
# sukcesu — i oddaje pierwotny kod wyjścia badania.

ARTIFACTS_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/artifacts.py"
ARTIFACTS_PENDING=()

# Pakuje katalogi do deterministycznych archiwów `tar.gz` z indeksem SHA-256.
artifacts_pack() {
  python3 "$ARTIFACTS_PY" pack "$@"
}

# Zapisuje indeks SHA-256 katalogu bez pakowania.
artifacts_index() {
  python3 "$ARTIFACTS_PY" index "$1" "$2"
}

artifacts_finalize() {
  local status=$?
  trap - EXIT
  if [ ${#ARTIFACTS_PENDING[@]} -gt 0 ]; then
    artifacts_pack "${ARTIFACTS_PENDING[@]}" ||
      echo "OSTRZEZENIE: pakowanie surowych artefaktow nie powiodlo sie" >&2
  fi
  exit "$status"
}

artifacts_pack_on_exit() {
  ARTIFACTS_PENDING+=("$@")
  trap artifacts_finalize EXIT
}
