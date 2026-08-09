#!/bin/bash
# Regresja strażnika czystości repozytorium kodu — `REQUIREMENTS.md` R2 i R11.
#
# Powód istnienia: `git status --short` jest ślepy na pliki wypisane
# w `.gitignore`. Artefakty silnika w `examples/ecg/rec205/` są tam wypisane
# imiennie, więc trzy kampanie z rzędu (K4, K5, badania higieniczne)
# raportowały „repozytorium kodu czyste", mając w nim 34 pliki wyjściowe
# poprzedniego przebiegu. Wykryte 2026-07-30 przy przygotowaniu K6.
#
# Test wymusza to, czego zabrakło: kontrola musi ZAWIEŚĆ, gdy defekt wystąpi
# ponownie, i musi udokumentować, że stary strażnik go nie widzi.
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TEST_DIR/.." && pwd)"
# shellcheck source=../lib/common.sh
source "$REPO_ROOT/lib/common.sh"

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

expect_failure() {
  local name="$1"
  shift
  checks=$((checks + 1))
  if "$@" >/dev/null 2>&1; then
    printf 'FAIL: %s (oczekiwano bledu, dostano sukces)\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

# Atrapa repozytorium kodu: katalog wejściowy z `.gitignore`, który — jak
# oryginał — wypisuje nazwy artefaktów silnika imiennie.
fixture_repo() {
  local root
  root=$(mktemp -d "${TMPDIR:-/tmp}/rdb-code-guard-XXXXXX") || return 1
  git -C "$root" init --quiet
  git -C "$root" config user.email test@example.com
  git -C "$root" config user.name test
  mkdir -p "$root/examples/ecg/rec205" "$root/build/Release"
  printf 'wejscie\n' > "$root/examples/ecg/rec205/rec205"
  printf 'mlii.desc\nmlii.meta\ntemp/\nSTREAM_ADD*\n' > "$root/examples/ecg/rec205/.gitignore"
  # Jak w repozytorium kodu: katalogi budowy są ignorowane, więc bez tego
  # atrapa nie odtwarzałaby warunku, w którym `git status --short` milczy.
  printf 'build/\n' > "$root/.gitignore"
  printf 'artefakt buildu\n' > "$root/build/Release/xretractor"
  git -C "$root" add examples .gitignore >/dev/null 2>&1
  git -C "$root" commit --quiet -m "wejscie" >/dev/null 2>&1
  printf '%s\n' "$root"
}

leak_artifact() {
  local root="$1"
  printf 'wyjscie silnika\n' > "$root/examples/ecg/rec205/mlii.desc"
}

# 1. Czyste drzewo przechodzi.
assert_pristine_passes() {
  local root
  root=$(fixture_repo) || return 1
  require_input_dirs_pristine "$root" examples/ecg
  local rc=$?
  rm -rf "$root"
  return $rc
}

# 2. Wyciek artefaktu ignorowanego zatrzymuje badanie — i stary strażnik milczy.
assert_ignored_leak_detected() {
  local root legacy rc=0
  root=$(fixture_repo) || return 1
  leak_artifact "$root"
  legacy=$(git -C "$root" status --short)
  # Dowód, że powód istnienia tego testu jest realny, a nie domniemany.
  [ -z "$legacy" ] || {
    printf 'atrapa nie odtwarza defektu: git status --short pokazal [%s]\n' "$legacy" >&2
    rc=1
  }
  require_input_dirs_pristine "$root" examples/ecg >/dev/null 2>&1 && rc=1
  rm -rf "$root"
  return $rc
}

# 3. Odcisk drzewa wykrywa zmianę powstałą w trakcie badania.
assert_fingerprint_detects_change() {
  local root before rc=0
  root=$(fixture_repo) || return 1
  before=$(mktemp)
  code_tree_fingerprint "$root" "$before" >/dev/null 2>&1 || rc=1
  require_code_tree_unchanged "$root" "$before" >/dev/null 2>&1 || rc=1
  leak_artifact "$root"
  require_code_tree_unchanged "$root" "$before" >/dev/null 2>&1 && rc=1
  rm -f "$before"
  rm -rf "$root"
  return $rc
}

# 4. Katalogi budowy nie fałszują odcisku: kampania sama je tworzy.
assert_fingerprint_ignores_build_dir() {
  local root before rc=0
  root=$(fixture_repo) || return 1
  before=$(mktemp)
  code_tree_fingerprint "$root" "$before" >/dev/null 2>&1 || rc=1
  mkdir -p "$root/build/K6-ALGSTRUCT/src/retractor"
  printf 'binarka\n' > "$root/build/K6-ALGSTRUCT/src/retractor/xretractor"
  require_code_tree_unchanged "$root" "$before" >/dev/null 2>&1 || rc=1
  rm -f "$before"
  rm -rf "$root"
  return $rc
}

# 5. Zero sprawdzonych ścieżek jest błędem, nie zgodnością (K5h/K5i).
assert_empty_scope_is_error() {
  local root rc=0
  root=$(fixture_repo) || return 1
  require_input_dirs_pristine "$root" >/dev/null 2>&1 && rc=1
  require_input_dirs_pristine "$root" examples/nie_ma >/dev/null 2>&1 && rc=1
  rm -rf "$root"
  return $rc
}

# 6. Weryfikacja profilu jest bajtowa: inny blok flag albo niejawna flaga musi zawieść.
assert_profile_check_is_exact() {
  local root binary rc=0
  root=$(mktemp -d "${TMPDIR:-/tmp}/rdb-profile-XXXXXX") || return 1
  binary="$root/xretractor"
  cat > "$binary" <<'EOF'
#!/bin/bash
printf 'RDB_OPT_DEDUP_SUBSTRATES=ON\n'
printf 'RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON\n'
printf 'RDB_OPT_COMMUTATIVE_ADD=OFF\n'
printf 'RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON\n'
printf 'RDB_BENCH_PROBE=ON\n'
EOF
  chmod +x "$binary"
  verify_probe_binary_profile "$binary" ON ON OFF ON >/dev/null 2>&1 || rc=1  # STRUCT+R1
  verify_probe_binary_profile "$binary" ON ON ON ON >/dev/null 2>&1 && rc=1   # ALGSTRUCT
  verify_probe_binary "$binary" >/dev/null 2>&1 && rc=1
  printf "printf 'RDB_OPT_SIMPLIFY_EXPRESSIONS=ON\\n'\n" >> "$binary"
  verify_probe_binary_profile "$binary" ON ON OFF ON ON >/dev/null 2>&1 || rc=1
  verify_probe_binary_profile "$binary" ON ON OFF ON OFF >/dev/null 2>&1 && rc=1
  verify_probe_binary_profile "$binary" ON ON OFF ON >/dev/null 2>&1 && rc=1
  rm -rf "$root"
  return $rc
}

# 7. Konfiguracja kampanii ablacyjnej jest walidowana jak pozostałe.
assert_ablation_csv_validated() {
  local root rc=0
  root=$(mktemp -d "${TMPDIR:-/tmp}/rdb-csv-XXXXXX") || return 1
  printf 'study_id,family,reps\n1,W2,15\n2,W9,15\n' > "$root/ok.csv"
  printf 'study_id,family,reps\n1,rodzina,15\n' > "$root/zla_rodzina.csv"
  printf 'study_id,family,reps\n' > "$root/pusta.csv"
  validate_campaign_csv "$root/ok.csv" ablation >/dev/null 2>&1 || rc=1
  validate_campaign_csv "$root/zla_rodzina.csv" ablation >/dev/null 2>&1 && rc=1
  validate_campaign_csv "$root/pusta.csv" ablation >/dev/null 2>&1 && rc=1
  rm -rf "$root"
  return $rc
}

expect_success "czyste drzewo wejsciowe przechodzi" assert_pristine_passes
expect_success "wyciek ignorowanego artefaktu zatrzymuje badanie" assert_ignored_leak_detected
expect_success "odcisk wykrywa zmiane w trakcie badania" assert_fingerprint_detects_change
expect_success "odcisk pomija katalogi budowy" assert_fingerprint_ignores_build_dir
expect_success "zero sprawdzonych sciezek jest bledem" assert_empty_scope_is_error
expect_success "weryfikacja profilu jest bajtowa" assert_profile_check_is_exact
expect_success "konfiguracja ablacyjna jest walidowana" assert_ablation_csv_validated

if [ "$failures" -ne 0 ]; then
  printf '%d/%d kontroli nie przeszlo\n' "$failures" "$checks" >&2
  exit 1
fi
printf 'OK: %d kontroli straznika repozytorium kodu\n' "$checks"
