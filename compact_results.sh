#!/usr/bin/env bash
# Kompaktowanie katalogu wyników do postaci nadającej się do przeglądu —
# `REQUIREMENTS.md` R14.
#
#   ./compact_results.sh <katalog_wynikow> \
#       [--evidence <sciezka_wzgledna>]... [--pack <sciezka_wzgledna>]...
#
# Kolejno: kopiuje wskazane dowody porażki do `results/evidence/`, pakuje
# wskazane katalogi surowe do deterministycznych archiwów `tar.gz` z indeksem
# SHA-256 i wypisuje tabelę do przypięcia w manifeście badania.
#
# Domyślnie pakowane są `results/raw` i `results/workloads`, jeżeli istnieją.
# Narzędzie zmienia FORMĘ zapisu, nie treść: indeks dowodzi tożsamości bajtów,
# więc kompaktowanie nie narusza niemutowalności ukończonego badania (R3).
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
source "$here/lib/artifacts.sh"

if [ $# -lt 1 ]; then
  echo "uzycie: $0 <katalog_wynikow> [--evidence <sciezka>]... [--pack <sciezka>]..." >&2
  exit 2
fi

root=$(cd "$1" && pwd) || exit 2
shift

evidence=()
pack=()
while [ $# -gt 0 ]; do
  case "$1" in
    --evidence) evidence+=("$2"); shift 2 ;;
    --pack) pack+=("$2"); shift 2 ;;
    *) echo "BLAD: nieznany argument $1" >&2; exit 2 ;;
  esac
done

if [ ${#pack[@]} -eq 0 ]; then
  for candidate in results/raw results/workloads; do
    [ -d "$root/$candidate" ] && pack+=("$candidate")
  done
fi
if [ ${#pack[@]} -eq 0 ]; then
  echo "BLAD: brak katalogow do spakowania w $root" >&2
  exit 1
fi

# --- dowody porażki: pliki, nie archiwum ------------------------------------
if [ ${#evidence[@]} -gt 0 ]; then
  for relative in "${evidence[@]}"; do
    source_file="$root/$relative"
    [ -f "$source_file" ] || { echo "BLAD: brak dowodu $relative" >&2; exit 1; }
    # `results/raw/semantic/X/Y.desc` -> `results/evidence/semantic/X/Y.desc`
    target="$root/results/evidence/${relative#results/raw/}"
    mkdir -p "$(dirname "$target")"
    cp "$source_file" "$target"
    echo "dowod: ${target#$root/}"
  done
fi

# --- reszta: jedno archiwum na katalog surowy ------------------------------
declare -a lines=()
for relative in "${pack[@]}"; do
  directory="$root/$relative"
  [ -d "$directory" ] || { echo "BLAD: brak katalogu $relative" >&2; exit 1; }
  files=$(find "$directory" -type f | wc -l)
  artifacts_pack "$directory" > /dev/null
  archive="$directory.tar.gz"
  index="$directory.index.tsv"
  lines+=("| \`${archive#$root/}\` | $files | $(stat -c %s "$archive") | \`$(sha256sum "$archive" | cut -d' ' -f1)\` |")
  echo "spakowano: ${archive#$root/} (${files} plikow) + ${index#$root/}"
done

echo
echo "| Archiwum | Plików | Bajtów | SHA-256 |"
echo "|---|---:|---:|---|"
printf '%s\n' "${lines[@]}"
echo
echo "Plikow w katalogu po kompaktowaniu: $(find "$root" -type f | wc -l)"
