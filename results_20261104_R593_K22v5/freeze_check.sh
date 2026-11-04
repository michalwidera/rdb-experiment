#!/bin/bash
# Bramka niezmienności i proweniencji R593 K22v5 (kopia results_20260801_K22v5/freeze_check.sh z nowymi przypięciami).
# Zamrożone pliki K22 / K22v5 są tylko czytane; jedyny zapis to results/ tego katalogu.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
FROZEN="$EXP_REPO/results_20260801_K22v5"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
PAPER_REPO="${PAPER_REPO:-/home/michal/github/paper-arXiv}"
XRETRACTOR="${XRETRACTOR:?ustaw XRETRACTOR na kopie xretractor z build/Debug dfcc42d2 (obok niej xtrdb)}"
XTRDB="$(dirname "$XRETRACTOR")/xtrdb"
FLINK_JAR="${FLINK_JAR:-/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar}"
JAVA17="${JAVA17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/java}"
JAVAC17="${JAVAC17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/javac}"
ENGINE_PIN="dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb"
K22V5_ENGINE="dd733e3792fbcd5727db244b802610a6d710b8dc"
K22V5_VERDICT="a9af132"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }

eq "$(git -C "$EXP_REPO" branch --show-current)" "experiment/20261103_R593" "branch"

# Silnik: drzewo kodu równe dfcc42d2 (HEAD może być późniejszym commitem bez zmian drzewa), wejścia
# danych bez lokalnych zmian i bajtowo równe wersjom z dd733e3, na których liczyło K22v5.
git -C "$CODE_REPO" diff --quiet "$ENGINE_PIN" HEAD || fail "drzewo retractordb HEAD rozni sie od $ENGINE_PIN"
INPUTS=(test/IntegrationTest/dsp/filterremez.txt examples/ecg/rec205/rec205 examples/ecg/rec205/bp_coef.txt
        examples/ecg/rec205/d_coef.txt)
OLD_INPUTS=(test/IntegrationTest_parallel/dsp/filterremez.txt examples/ecg/rec205/rec205 examples/ecg/rec205/bp_coef.txt
            examples/ecg/rec205/d_coef.txt)
[[ -z "$(git -C "$CODE_REPO" status --porcelain -- "${INPUTS[@]}")" ]] || fail "lokalne zmiany w plikach wejsciowych"
for i in "${!INPUTS[@]}"; do
  eq "$(git -C "$CODE_REPO" hash-object "${INPUTS[$i]}")" \
     "$(git -C "$CODE_REPO" rev-parse "$K22V5_ENGINE:${OLD_INPUTS[$i]}")" "wejscie ${INPUTS[$i]}"
done

[[ -x "$XRETRACTOR" && -x "$XTRDB" ]] || fail "brak xretractor albo xtrdb w $(dirname "$XRETRACTOR")"
[[ -r "$FLINK_JAR" ]] || fail "brak JAR Flink: $FLINK_JAR"
[[ -x "$JAVA17" && -x "$JAVAC17" ]] || fail "brak przypietego JDK 17"
eq "$(sha256sum "$XRETRACTOR" | awk '{print $1}')" \
  "eae9b59651892d2cd00b5e4f46e2ac37492fa80b5b15986d47527a4cc04657ea" "xretractor SHA-256"
eq "$(sha256sum "$XTRDB" | awk '{print $1}')" \
  "b7784b0558d7cc9e7deb827d5c58895584796de4a06e3b8b9f25ca865bc50ce3" "xtrdb SHA-256"
"$XRETRACTOR" --help | grep -q '^Branch: dev/muro:dfcc42d2, .*Type: Debug$' || fail "xretractor nie jest Debug dfcc42d2"
eq "$(sha256sum "$FLINK_JAR" | awk '{print $1}')" \
  "7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493" "Flink JAR SHA-256"

# Zamrożona aparatura i korpus K22 / K22v5: bez zmian od werdyktu K22v5 i bez lokalnych zmian.
FROZEN_PATHS=(results_20260801_K22/corpus results_20260801_K22/oracle results_20260801_K22v5/tasks
              results_20260801_K22v5/results/semantic.csv results_20260801_K22v5/manifest.md)
git -C "$EXP_REPO" diff --quiet "$K22V5_VERDICT" HEAD -- "${FROZEN_PATHS[@]}" \
  || fail "zamrozone pliki K22/K22v5 zmienione od $K22V5_VERDICT"
[[ -z "$(git -C "$EXP_REPO" status --porcelain --untracked-files=no -- "${FROZEN_PATHS[@]}")" ]] \
  || fail "lokalne zmiany w zamrozonych plikach K22/K22v5"

EXPECTED_BASES="$(mktemp)"
trap 'rm -f "$EXPECTED_BASES"' EXIT
sed -n '/^```text$/,/^```$/p' "$FROZEN/manifest.md" | sed '1d;$d' >"$EXPECTED_BASES"
bases=0
while read -r digest label; do
  case "$label" in
    F1/flink) rel="F1_fir/flink/F1Fir.java" ;;
    F1/python) rel="F1_fir/python/core.py" ;;
    F1/rql) rel="F1_fir/rql/core.rql" ;;
    F2/flink) rel="F2_ecg/flink/F2Ecg.java" ;;
    F2/python) rel="F2_ecg/python/core.py" ;;
    F2/rql) rel="F2_ecg/rql/core.rql" ;;
    F3/flink) rel="F3_multirate/flink/F3Multirate.java" ;;
    F3/python) rel="F3_multirate/python/core.py" ;;
    F3/rql) rel="F3_multirate/rql/core.rql" ;;
    *) fail "nieznana baza w manifescie: $label" ;;
  esac
  eq "$(sha256sum "$EXP_REPO/results_20260801_K22/corpus/$rel" | awk '{print $1}')" "$digest" "baza $label"
  bases=$((bases + 1))
done <"$EXPECTED_BASES"
eq "$bases" "9" "liczba baz"

variants=0
while IFS=$'\t' read -r digest path; do
  [[ "$digest" == sha256 ]] && continue
  eq "$(sha256sum "$FROZEN/$path" | awk '{print $1}')" "$digest" "plik zadania $path"
  variants=$((variants + 1))
done <"$FROZEN/results/variant_sha256.tsv"
eq "$(find "$FROZEN/tasks" -type f | wc -l)" "$variants" "liczba plikow zadan wobec variant_sha256.tsv"

# Zmigrowane rdzenie: dokładnie te z config/migration.tsv.
cores=0
while IFS=$'\t' read -r cell _source _orig migrated _rest; do
  [[ "$cell" == cell ]] && continue
  eq "$(sha256sum "$HERE/config/cores/$cell.rql" | awk '{print $1}')" "$migrated" "zmigrowany rdzen $cell"
  cores=$((cores + 1))
done <"$HERE/config/migration.tsv"
eq "$cores" "15" "liczba zmigrowanych rdzeni"

mkdir -p "$HERE/results"
{
  printf 'key\tvalue\n'
  printf 'captured_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'experiment_head\t%s\n' "$(git -C "$EXP_REPO" rev-parse HEAD)"
  printf 'retractordb_head\t%s\n' "$(git -C "$CODE_REPO" rev-parse HEAD)"
  printf 'retractordb_tree_equal\t%s\n' "$ENGINE_PIN"
  printf 'paper_head\t%s\n' "$(git -C "$PAPER_REPO" rev-parse HEAD)"
  printf 'python\t%s\n' "$(python3 --version 2>&1)"
  printf 'java\t%s\n' "$("$JAVA17" -version 2>&1 | head -n1)"
  printf 'javac\t%s\n' "$("$JAVAC17" -version 2>&1)"
  printf 'flink_jar\t%s\n' "$FLINK_JAR"
  printf 'flink_sha256\t%s\n' "$(sha256sum "$FLINK_JAR" | awk '{print $1}')"
  printf 'xretractor\t%s\n' "$XRETRACTOR"
  printf 'xretractor_sha256\t%s\n' "$(sha256sum "$XRETRACTOR" | awk '{print $1}')"
  printf 'xtrdb_sha256\t%s\n' "$(sha256sum "$XTRDB" | awk '{print $1}')"
  "$XRETRACTOR" --help | grep '^Branch:' | sed 's/^/build_stamp\t/'
  "$XRETRACTOR" --build-info | sed 's/^/build_info\t/'
} >"$HERE/results/environment.tsv"

echo "OK: przypiecia, narzedzia, 9 baz, $variants plikow zadan K22v5 i 15 zmigrowanych rdzeni"
