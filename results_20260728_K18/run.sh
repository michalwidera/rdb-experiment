#!/usr/bin/env bash
# K18: powtorzenie exactness/replay po G1 i K19 na przypietym masterze.
#
# Harness nie wykonuje operacji Git zmieniajacych historie i nie zapisuje nic
# do repozytorium kodu. Wyniki trafiaja do katalogu exactness/ tego
# eksperymentu dopiero po przejsciu wszystkich porownan.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

EXPECTED_CODE_BRANCH="master"
EXPECTED_CODE_COMMIT="bc37186ac87cb944d76cf74c7be92706a4a3a87f"
EXPECTED_CODE_SHORT="bc37186"
EXPECTED_EXPERIMENT_BRANCH="experiment/20260728_K18"

CODE_REPO="$(cd "$EXPERIMENT_REPO/../retractordb" 2>/dev/null && pwd || true)"
XRETRACTOR=""
PYTHON_BIN="python3"
SAMPLES=20000
PREFLIGHT_ONLY=0

usage() {
  cat <<'EOF'
Usage: ./run.sh [options]

Options:
  --code-repo PATH       checkout RetractorDB (default: sibling repository)
  --xretractor PATH      Release-Probe binary from the pinned checkout
  --python PATH          Python 3 interpreter (default: python3)
  --samples N            replay/round-trip loop scale (default: 20000)
  --preflight-only       validate repositories, binary and inputs, then stop
  -h, --help             show this help

The harness requires RetractorDB master@bc37186ac87cb944d76cf74c7be92706a4a3a87f
and rdb-experiment branch experiment/20260728_K18.
EOF
}

die() {
  printf 'BLAD: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --code-repo)
      [ "$#" -ge 2 ] || die "brak wartosci --code-repo"
      CODE_REPO="$2"
      shift 2
      ;;
    --xretractor)
      [ "$#" -ge 2 ] || die "brak wartosci --xretractor"
      XRETRACTOR="$2"
      shift 2
      ;;
    --python)
      [ "$#" -ge 2 ] || die "brak wartosci --python"
      PYTHON_BIN="$2"
      shift 2
      ;;
    --samples)
      [ "$#" -ge 2 ] || die "brak wartosci --samples"
      SAMPLES="$2"
      shift 2
      ;;
    --preflight-only)
      PREFLIGHT_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "nieznana opcja: $1"
      ;;
  esac
done

[[ "$SAMPLES" =~ ^[0-9]+$ ]] && [ "$SAMPLES" -ge 32 ] ||
  die "--samples musi byc liczba calkowita >= 32"
[ -n "$CODE_REPO" ] || die "nie znaleziono repozytorium kodu"
CODE_REPO="$(realpath "$CODE_REPO")"
[ -d "$CODE_REPO/.git" ] || die "brak repozytorium kodu: $CODE_REPO"

if [ -z "$XRETRACTOR" ]; then
  XRETRACTOR="$CODE_REPO/build/Release-Probe/src/retractor/xretractor"
fi
XRETRACTOR="$(realpath -m "$XRETRACTOR")"

[ "$(git -C "$CODE_REPO" branch --show-current)" = "$EXPECTED_CODE_BRANCH" ] ||
  die "kod musi byc na branchu $EXPECTED_CODE_BRANCH"
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$EXPECTED_CODE_COMMIT" ] ||
  die "kod musi wskazywac commit $EXPECTED_CODE_COMMIT"
[ -z "$(git -C "$CODE_REPO" status --short)" ] ||
  die "repozytorium kodu nie jest czyste"

[ "$(git -C "$EXPERIMENT_REPO" branch --show-current)" = "$EXPECTED_EXPERIMENT_BRANCH" ] ||
  die "wyniki musza powstac na branchu $EXPECTED_EXPERIMENT_BRANCH"
[ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] ||
  die "repozytorium eksperymentu nie jest czyste"

[ -x "$XRETRACTOR" ] || die "brak wykonywalnej binarki Release-Probe: $XRETRACTOR"
command -v "$PYTHON_BIN" >/dev/null || die "brak interpretera: $PYTHON_BIN"
command -v sha256sum >/dev/null || die "brak sha256sum"
command -v findmnt >/dev/null || die "brak findmnt"
[ "$(findmnt -n -o FSTYPE /dev/shm)" = "tmpfs" ] || die "/dev/shm nie jest tmpfs"

BINARY_ID="$("$XRETRACTOR" --help 2>&1)"
grep -qF "Branch: ${EXPECTED_CODE_BRANCH}:${EXPECTED_CODE_SHORT}" <<<"$BINARY_ID" ||
  die "binarka nie pochodzi z ${EXPECTED_CODE_BRANCH}@${EXPECTED_CODE_SHORT}"

BUILD_INFO="$("$XRETRACTOR" --build-info)"
for expected in \
  "RDB_OPT_DEDUP_SUBSTRATES=ON" \
  "RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON" \
  "RDB_OPT_COMMUTATIVE_ADD=ON" \
  "RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON" \
  "RDB_BENCH_PROBE=ON"; do
  grep -qxF "$expected" <<<"$BUILD_INFO" ||
    die "niezgodna konfiguracja binarki: brak '$expected'"
done

ECG_DIR="$CODE_REPO/examples/ecg/rec205"
for input in rec205 bp_coef.txt d_coef.txt; do
  [ -f "$ECG_DIR/$input" ] || die "brak danych wejsciowych: $ECG_DIR/$input"
done

CONFIG_DIR="$EXPERIMENT_REPO/config"
for config in exactness-replay.rql exactness-roundtrip-write.rql exactness-roundtrip-read.rql; do
  [ -f "$CONFIG_DIR/$config" ] || die "brak konfiguracji: $CONFIG_DIR/$config"
done

OUTPUT_DIR="$SCRIPT_DIR/exactness"
OUTPUT_FILES=(
  binary_build_info.txt
  binary_identity.txt
  configuration.sha256
  replay_artifacts.txt
  replay_compare.txt
  replay_hashes_run1.txt
  replay_hashes_run2.txt
  replay_run1.log
  replay_run2.log
  results.md
  roundtrip_compare.txt
  roundtrip_read.log
  roundtrip_write.log
  state_after.md
  state_before.md
)
for output in "${OUTPUT_FILES[@]}"; do
  [ ! -e "$OUTPUT_DIR/$output" ] ||
    die "wynik juz istnieje: $OUTPUT_DIR/$output; uzyj nowego identyfikatora eksperymentu"
done

printf '%s\n' "Preflight OK: RetractorDB ${EXPECTED_CODE_BRANCH}@${EXPECTED_CODE_COMMIT}"
printf '%s\n' "Binary: $XRETRACTOR"
if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  exit 0
fi

mkdir -p /dev/shm/rdb-experiment
WORKDIR="$(mktemp -d /dev/shm/rdb-experiment/K18_exactness.XXXXXX)"

cleanup() {
  if [[ "$WORKDIR" == /dev/shm/rdb-experiment/K18_exactness.* ]] && [ -d "$WORKDIR" ]; then
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

snapshot_state() {
  local label="$1"
  local output="$2"
  {
    printf '# Stan maszyny — %s\n\n' "$label"
    printf '%s\n' "- data: $(date -Is)"
    printf '%s\n' "- kod: \`${EXPECTED_CODE_BRANCH}@${EXPECTED_CODE_COMMIT}\`"
    printf '%s\n' "- branch wynikow: \`$EXPECTED_EXPERIMENT_BRANCH\`"
    printf '%s\n' "- samples: $SAMPLES"
    printf '\n## Binarka\n\n```\n%s\n```\n' "$BINARY_ID"
    printf '\n## Build info\n\n```\n%s\n```\n' "$BUILD_INFO"
    printf '\n## System\n\n```\n'
    uname -a
    printf '\n'
    cat /proc/cmdline 2>/dev/null || true
    printf '```\n'
  } >"$output"
}

snapshot_state "przed badaniem" "$WORKDIR/state_before.md"
printf '%s\n' "$BUILD_INFO" >"$WORKDIR/binary_build_info.txt"
printf '%s\n' "$BINARY_ID" >"$WORKDIR/binary_identity.txt"
(
  cd "$CONFIG_DIR"
  sha256sum exactness-replay.rql exactness-roundtrip-write.rql exactness-roundtrip-read.rql
) >"$WORKDIR/configuration.sha256"

printf '%s\n' "== Replay 1/2 =="
for run in 1 2; do
  run_dir="$WORKDIR/replay_run$run"
  mkdir -p "$run_dir"
  cp "$ECG_DIR/rec205" "$ECG_DIR/bp_coef.txt" "$ECG_DIR/d_coef.txt" "$run_dir/"
  cp "$CONFIG_DIR/exactness-replay.rql" "$run_dir/"
  (
    cd "$run_dir"
    "$XRETRACTOR" exactness-replay.rql -r -k -m "$SAMPLES"
  ) >"$WORKDIR/replay_run$run.log" 2>&1 ||
    die "replay run$run zakonczyl sie bledem"
done

list_artifacts() {
  find "$1" -maxdepth 1 -type f -printf '%f\n' |
    grep -Ev '^(rec205|bp_coef\.txt|d_coef\.txt|exactness-replay\.rql)$' |
    sort
}

list_artifacts "$WORKDIR/replay_run1" >"$WORKDIR/replay_artifacts_run1.txt"
list_artifacts "$WORKDIR/replay_run2" >"$WORKDIR/replay_artifacts_run2.txt"
cmp -s "$WORKDIR/replay_artifacts_run1.txt" "$WORKDIR/replay_artifacts_run2.txt" ||
  die "replay utworzyl rozne zbiory artefaktow"
[ "$(wc -l <"$WORKDIR/replay_artifacts_run1.txt")" -eq 67 ] ||
  die "replay powinien utworzyc 67 plikow dla 17 strumieni"
cp "$WORKDIR/replay_artifacts_run1.txt" "$WORKDIR/replay_artifacts.txt"

for run in 1 2; do
  hash_file="$WORKDIR/replay_hashes_run$run.txt"
  : >"$hash_file"
  while IFS= read -r artifact; do
    hash="$(sha256sum "$WORKDIR/replay_run$run/$artifact" | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$artifact" >>"$hash_file"
  done <"$WORKDIR/replay_artifacts_run1.txt"
done

: >"$WORKDIR/replay_compare.txt"
while IFS= read -r artifact; do
  if [[ "$artifact" == *.meta ]]; then
    if cmp -s \
      <(tail -c +9 "$WORKDIR/replay_run1/$artifact") \
      <(tail -c +9 "$WORKDIR/replay_run2/$artifact"); then
      printf 'IDENT-PO-TIMESTAMP  %s\n' "$artifact" >>"$WORKDIR/replay_compare.txt"
    else
      printf 'ROZNY               %s\n' "$artifact" >>"$WORKDIR/replay_compare.txt"
      die "replay: rozny artefakt $artifact po pominieciu timestampu"
    fi
  elif cmp -s "$WORKDIR/replay_run1/$artifact" "$WORKDIR/replay_run2/$artifact"; then
    printf 'IDENTYCZNY          %s\n' "$artifact" >>"$WORKDIR/replay_compare.txt"
  else
    printf 'ROZNY               %s\n' "$artifact" >>"$WORKDIR/replay_compare.txt"
    die "replay: rozny artefakt $artifact"
  fi
done <"$WORKDIR/replay_artifacts_run1.txt"

printf '%s\n' "== Round-trip =="
ROUNDTRIP_DIR="$WORKDIR/roundtrip"
mkdir -p "$ROUNDTRIP_DIR"
cp "$ECG_DIR/rec205" "$ROUNDTRIP_DIR/"
cp "$CONFIG_DIR/exactness-roundtrip-write.rql" "$CONFIG_DIR/exactness-roundtrip-read.rql" "$ROUNDTRIP_DIR/"
(
  cd "$ROUNDTRIP_DIR"
  "$XRETRACTOR" exactness-roundtrip-write.rql -r -k -m "$SAMPLES"
) >"$WORKDIR/roundtrip_write.log" 2>&1 ||
  die "round-trip: faza zapisu zakonczyla sie bledem"

mv "$ROUNDTRIP_DIR/a" "$ROUNDTRIP_DIR/a_data"
mv "$ROUNDTRIP_DIR/b" "$ROUNDTRIP_DIR/b_data"
rm -f \
  "$ROUNDTRIP_DIR/a.desc" "$ROUNDTRIP_DIR/a.meta" "$ROUNDTRIP_DIR/a.shadow" \
  "$ROUNDTRIP_DIR/b.desc" "$ROUNDTRIP_DIR/b.meta" "$ROUNDTRIP_DIR/b.shadow"

ROUNDTRIP_LOOPS=$((2 * SAMPLES - 4))
(
  cd "$ROUNDTRIP_DIR"
  "$XRETRACTOR" exactness-roundtrip-read.rql -r -k -m "$ROUNDTRIP_LOOPS"
) >"$WORKDIR/roundtrip_read.log" 2>&1 ||
  die "round-trip: faza odczytu zakonczyla sie bledem"

"$PYTHON_BIN" - "$ROUNDTRIP_DIR" "$SAMPLES" >"$WORKDIR/roundtrip_compare.txt" <<'PY'
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
samples = int(sys.argv[2])

def load(name: str) -> list[int]:
    raw = (root / name).read_bytes()
    if not raw or len(raw) % 4:
        raise SystemExit(f"FAIL: {name} ma nieprawidlowy rozmiar {len(raw)}")
    return [value[0] for value in struct.iter_unpack("<i", raw)]

a = load("a_data")
b = load("b_data")
c = load("c")
a2 = load("a2")
b2 = load("b2")

even = c[0::2]
odd = c[1::2]
checks = {
    "c[2i] == b[i]": even == b[:len(even)],
    "c[2i+1] == a[i]": odd == a[:len(odd)],
    "a2 == a (bez rekordu zastepczego)": a2 == a[:len(a2)],
    "b2 == b": b2 == b[:len(b2)],
    "wystarczajacy prefiks a2": len(a2) >= samples - 10,
    "wystarczajacy prefiks b2": len(b2) >= samples - 10,
}

for label, passed in checks.items():
    print(f"{label}: {passed}")
print(f"records: a={len(a)} b={len(b)} c={len(c)} a2={len(a2)} b2={len(b2)}")
print(f"first: a={a[0]} a2={a2[0]} b={b[0]} b2={b2[0]}")

if not all(checks.values()):
    print("VERDICT: FAIL")
    raise SystemExit(1)
print("VERDICT: OK")
PY

snapshot_state "po badaniu" "$WORKDIR/state_after.md"

[ -z "$(git -C "$CODE_REPO" status --short)" ] ||
  die "repozytorium kodu zmienilo sie podczas badania"
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$EXPECTED_CODE_COMMIT" ] ||
  die "commit kodu zmienil sie podczas badania"

{
  printf '# K18 exactness/replay — wynik\n\n'
  printf '%s\n' "- kod: \`${EXPECTED_CODE_BRANCH}@${EXPECTED_CODE_COMMIT}\`"
  printf '%s\n' "- branch wynikow: \`$EXPECTED_EXPERIMENT_BRANCH\`"
  printf '%s\n' "- samples: $SAMPLES"
  printf '%s\n' "- replay: 2 przebiegi, 17 strumieni, 67 plikow artefaktow"
  printf '%s\n\n' "- round-trip: \`a2 == a\` i \`b2 == b\` bez rekordu zastepczego"
  printf '## Replay\n\n```\n'
  cat "$WORKDIR/replay_compare.txt"
  printf '```\n\n## Round-trip\n\n```\n'
  cat "$WORKDIR/roundtrip_compare.txt"
  printf '```\n'
} >"$WORKDIR/results.md"

for output in "${OUTPUT_FILES[@]}"; do
  cp "$WORKDIR/$output" "$OUTPUT_DIR/$output"
done

printf '%s\n' "K18 exactness/replay: OK"
printf 'Wyniki: %s\n' "$OUTPUT_DIR"
