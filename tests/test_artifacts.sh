#!/bin/bash
# Regresja higieny artefaktów — `REQUIREMENTS.md` R14.
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TEST_DIR/.." && pwd)"
# shellcheck source=../lib/artifacts.sh
source "$REPO_ROOT/lib/artifacts.sh"

# Górna granica liczby luźnych plików w katalogu wyników. Katalog przekraczający
# ten limit jest nieprzetwarzalny dla IDE i nie nadaje się do przeglądu ręcznego.
LOOSE_FILE_LIMIT=300

failures=0
checks=0

expect_success() {
  local name="$1"
  shift
  checks=$((checks + 1))
  if ! "$@" >/dev/null 2>&1; then
    printf 'FAIL: %s (oczekiwano sukcesu)\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

sandbox() {
  mktemp -d "${TMPDIR:-/tmp}/rdb-artifacts-test-XXXXXX"
}

fixture() {
  local root="$1"
  mkdir -p "$root/raw/case_a/STRUCT" "$root/raw/case_b"
  printf 'alfa\n' > "$root/raw/case_a/STRUCT/a.desc"
  printf 'beta\n' > "$root/raw/case_a/STRUCT/b.meta"
  printf 'gamma\n' > "$root/raw/case_b/c.shadow"
}

# Pakowanie zostawia archiwum i indeks, a katalog surowy znika.
assert_pack_replaces_tree() {
  local root archive index
  root=$(sandbox) || return 1
  fixture "$root"
  artifacts_pack "$root/raw" > /dev/null || return 1
  archive="$root/raw.tar.gz"
  index="$root/raw.index.tsv"
  [ -f "$archive" ] && [ -f "$index" ] && [ ! -d "$root/raw" ] &&
    [ "$(wc -l < "$index")" -eq 4 ] &&
    grep -q 'case_a/STRUCT/a.desc' "$index"
  local status=$?
  rm -rf "$root"
  return $status
}

# Archiwum musi dać się rozpakować bajt w bajt zgodnie z indeksem —
# inaczej nie jest dowodem, tylko balastem.
assert_archive_round_trip() {
  local root status
  root=$(sandbox) || return 1
  fixture "$root"
  python3 "$REPO_ROOT/lib/artifacts.py" index "$root/raw" "$root/before.tsv" > /dev/null || return 1
  artifacts_pack "$root/raw" > /dev/null || return 1
  mkdir -p "$root/out"
  tar -xzf "$root/raw.tar.gz" -C "$root/out" || return 1
  python3 "$REPO_ROOT/lib/artifacts.py" index "$root/out/raw" "$root/after.tsv" > /dev/null || return 1
  cmp -s "$root/before.tsv" "$root/after.tsv"
  status=$?
  rm -rf "$root"
  return $status
}

# Identyczna treść daje identyczne archiwum — SHA-256 archiwum wolno przypiąć
# w manifeście badania.
assert_archive_deterministic() {
  local root first second status
  root=$(sandbox) || return 1
  fixture "$root/one"
  fixture "$root/two"
  artifacts_pack "$root/one/raw" > /dev/null || return 1
  artifacts_pack "$root/two/raw" > /dev/null || return 1
  first=$(sha256sum "$root/one/raw.tar.gz" | cut -d' ' -f1)
  second=$(sha256sum "$root/two/raw.tar.gz" | cut -d' ' -f1)
  [ "$first" = "$second" ]
  status=$?
  rm -rf "$root"
  return $status
}

# Pułapka EXIT pakuje także po porażce i oddaje pierwotny kod wyjścia.
assert_pack_on_failure() {
  local root status
  root=$(sandbox) || return 1
  cat > "$root/run.sh" <<SCRIPT
#!/bin/bash
set -euo pipefail
source "$REPO_ROOT/lib/artifacts.sh"
cd "$root"
mkdir -p results/raw/case
printf 'delta\n' > results/raw/case/d.desc
artifacts_pack_on_exit results/raw
false
SCRIPT
  chmod +x "$root/run.sh"
  "$root/run.sh" > /dev/null 2>&1
  status=$?
  [ "$status" -eq 1 ] && [ -f "$root/results/raw.tar.gz" ] && [ ! -d "$root/results/raw" ]
  status=$?
  rm -rf "$root"
  return $status
}

# Zrzuty udanego przebiegu nie tworzą plików; dowód porażki tworzy.
assert_keep_output_policy() {
  local root status
  root=$(sandbox) || return 1
  python3 - "$REPO_ROOT" "$root" <<'PYTHON'
import sys
from pathlib import Path

sys.path.insert(0, f"{sys.argv[1]}/lib")
import artifacts

base = Path(sys.argv[2]) / "raw" / "case"
ok = artifacts.keep_output(base, "plan\n", "", evidence=False)
assert not base.parent.exists(), "sukces nie moze tworzyc plikow"
assert ok["stdout_sha256"] and ok["stdout_bytes"] == 5

bad = artifacts.keep_output(base, "plan\n", "blad\n", evidence=True)
assert (base.parent / "case.stdout").is_file() and (base.parent / "case.stderr").is_file()
assert bad["stderr_bytes"] == 5
PYTHON
  status=$?
  rm -rf "$root"
  return $status
}

# Dowody porażki zachowują nazwę z werdyktu.
assert_keep_evidence_layout() {
  local root status
  root=$(sandbox) || return 1
  fixture "$root"
  python3 - "$REPO_ROOT" "$root" <<'PYTHON'
import sys
from pathlib import Path

sys.path.insert(0, f"{sys.argv[1]}/lib")
import artifacts

root = Path(sys.argv[2])
kept = artifacts.keep_evidence(
    [root / "raw/case_a/STRUCT/a.desc"], root / "raw", root / "evidence"
)
assert kept == ["case_a/STRUCT/a.desc"], kept
assert (root / "evidence/case_a/STRUCT/a.desc").read_text() == "alfa\n"
PYTHON
  status=$?
  rm -rf "$root"
  return $status
}

# Żaden katalog wyników w repozytorium nie może wracać do postaci tysięcy
# luźnych plików.
assert_results_dirs_compacted() {
  local directory count over=0
  for directory in "$REPO_ROOT"/results_*; do
    [ -d "$directory" ] || continue
    count=$(find "$directory" -type f -not -path '*/__pycache__/*' | wc -l)
    if [ "$count" -gt "$LOOSE_FILE_LIMIT" ]; then
      printf 'katalog %s ma %d luznych plikow (limit %d)\n' \
        "${directory##*/}" "$count" "$LOOSE_FILE_LIMIT" >&2
      over=1
    fi
  done
  [ "$over" -eq 0 ]
}

# Każde archiwum surowych artefaktów ma obok indeks SHA-256.
assert_archives_have_index() {
  local archive index missing=0
  while IFS= read -r archive; do
    index="${archive%.tar.gz}.index.tsv"
    if [ ! -f "$index" ]; then
      printf 'archiwum bez indeksu: %s\n' "$archive" >&2
      missing=1
    fi
  done < <(find "$REPO_ROOT"/results_* -name '*.tar.gz' 2>/dev/null)
  [ "$missing" -eq 0 ]
}

expect_success "pakowanie zastepuje drzewo surowe" assert_pack_replaces_tree
expect_success "archiwum rozpakowuje sie zgodnie z indeksem" assert_archive_round_trip
expect_success "archiwum jest deterministyczne" assert_archive_deterministic
expect_success "porazka takze pakuje i zachowuje kod wyjscia" assert_pack_on_failure
expect_success "zrzuty tylko dla porazki" assert_keep_output_policy
expect_success "dowody zachowuja uklad nazw" assert_keep_evidence_layout
expect_success "katalogi wynikow skompaktowane" assert_results_dirs_compacted
expect_success "kazde archiwum ma indeks" assert_archives_have_index

if [ "$failures" -ne 0 ]; then
  printf '%d/%d kontroli nie przeszlo\n' "$failures" "$checks" >&2
  exit 1
fi
printf 'OK: %d kontroli higieny artefaktow\n' "$checks"
