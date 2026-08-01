#!/bin/bash
# Bramka niezmienności i proweniencji K22v5.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
PAPER_REPO="${PAPER_REPO:-/home/michal/github/paper-arXiv}"
XRETRACTOR="${XRETRACTOR:-/home/michal/.local/bin/xretractor}"
FLINK_JAR="${FLINK_JAR:-/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar}"
JAVA17="${JAVA17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/java}"
JAVAC17="${JAVAC17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/javac}"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }

eq "$(git -C "$EXP_REPO" branch --show-current)" "experiment/20260801_K22" "branch"
eq "$(git -C "$CODE_REPO" rev-parse HEAD)" "dd733e3792fbcd5727db244b802610a6d710b8dc" "retractordb HEAD"
eq "$(git -C "$PAPER_REPO" rev-parse HEAD)" "6a4c5f794060fbe672d04db6aa072c0b9d2708f1" "paper-arXiv HEAD"
git -C "$EXP_REPO" merge-base --is-ancestor 73f2418 HEAD \
  || fail "commit zatrzymujący K22v4 nie jest przodkiem HEAD"

[[ -x "$XRETRACTOR" ]] || fail "brak xretractor: $XRETRACTOR"
[[ -r "$FLINK_JAR" ]] || fail "brak JAR Flink: $FLINK_JAR"
[[ -x "$JAVA17" && -x "$JAVAC17" ]] || fail "brak przypietego JDK 17"
eq "$(sha256sum "$XRETRACTOR" | awk '{print $1}')" \
  "6fe7fd978a99ecb450d334407bbd63392fd69e803c3efd8a8e658deb259e17a6" "xretractor SHA-256"
eq "$(sha256sum "$FLINK_JAR" | awk '{print $1}')" \
  "7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493" "Flink JAR SHA-256"

EXPECTED_BASES="$(mktemp)"
trap 'rm -f "$EXPECTED_BASES"' EXIT
sed -n '/^```text$/,/^```$/p' "$HERE/manifest.md" | sed '1d;$d' >"$EXPECTED_BASES"
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
    *) fail "nieznana baza w manifeście: $label" ;;
  esac
  actual="$(sha256sum "$HERE/../results_20260801_K22/corpus/$rel" | awk '{print $1}')"
  eq "$actual" "$digest" "baza $label"
done <"$EXPECTED_BASES"

REFERENCE="$HERE/../results_20260801_K22v4/tasks"
core_count=0
while IFS= read -r -d '' path; do
  rel="${path#"$HERE/tasks/"}"
  ref="$REFERENCE/$rel"
  [[ -f "$ref" ]] || fail "brak pliku referencyjnego: $rel"
  case "$rel" in
    */rql/core.rql|*/python/core.py|*/flink/*.java)
      core_count=$((core_count + 1))
      diff <(sed -n '/CORE_BEGIN/,/CORE_END/p' "$path") \
           <(sed -n '/CORE_BEGIN/,/CORE_END/p' "$ref") >/dev/null \
        || fail "mierzony rdzeń różni się od K22v4: $rel"
      ;;
  esac
  case "$rel" in
    M1/F1_fir/python/run.py|M1/F1_fir/flink/F1Fir.java)
      eq "$(grep -c 'f1_out_1' "$path")" "1" "kanoniczna etykieta $rel"
      diff <(sed 's/f1_out_1/channel_2/' "$path") "$ref" >/dev/null \
        || fail "niedozwolona zmiana writera: $rel"
      ;;
    *)
      cmp -s "$path" "$ref" || fail "nieoczekiwana zmiana pliku zadania: $rel"
      ;;
  esac
done < <(find "$HERE/tasks" -type f -print0 | sort -z)
eq "$core_count" "36" "liczba niezmienionych rdzeni wariantów"

mkdir -p "$HERE/results"
{
  printf 'key\tvalue\n'
  printf 'captured_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'experiment_head\t%s\n' "$(git -C "$EXP_REPO" rev-parse HEAD)"
  printf 'retractordb_head\t%s\n' "$(git -C "$CODE_REPO" rev-parse HEAD)"
  printf 'paper_head\t%s\n' "$(git -C "$PAPER_REPO" rev-parse HEAD)"
  printf 'python\t%s\n' "$(python3 --version 2>&1)"
  printf 'java\t%s\n' "$("$JAVA17" -version 2>&1 | head -n1)"
  printf 'javac\t%s\n' "$("$JAVAC17" -version 2>&1)"
  printf 'flink_jar\t%s\n' "$FLINK_JAR"
  printf 'flink_sha256\t%s\n' "$(sha256sum "$FLINK_JAR" | awk '{print $1}')"
  printf 'xretractor\t%s\n' "$XRETRACTOR"
  printf 'xretractor_sha256\t%s\n' "$(sha256sum "$XRETRACTOR" | awk '{print $1}')"
  "$XRETRACTOR" --build-info | sed 's/^/build_info\t/'
} >"$HERE/results/environment.tsv"

{
  printf 'sha256\tlabel\tpath\n'
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
    esac
    printf '%s\t%s\t%s\n' "$digest" "$label" "../results_20260801_K22/corpus/$rel"
  done <"$EXPECTED_BASES"
} >"$HERE/results/base_sha256.tsv"

{
  printf 'sha256\tpath\n'
  while IFS= read -r -d '' path; do
    printf '%s\t%s\n' "$(sha256sum "$path" | awk '{print $1}')" "${path#"$HERE/"}"
  done < <(find "$HERE/tasks" -type f -print0 | sort -z)
} >"$HERE/results/variant_sha256.tsv"

echo "OK: przypięcia, narzędzia, 9 baz i 36 rdzeni K22v5"
