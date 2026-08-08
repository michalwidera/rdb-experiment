#!/bin/bash
# Bramka niezmienności i proweniencji K23 — WYPEŁNIONA w P5 (2026-08-08).
#
# Wzorzec: results_20260801_K22v5/freeze_check.sh. Tamten powstał PO zamrożeniu
# i od razu nosił prawdziwe sumy; ten powstał jako szkielet PRZED predeklaracją
# i do tej sesji kończył się kodem 2 na znaczniku `@@CODE_SHA@@`. Znaczników już
# nie ma — od tego commitu bramka albo przechodzi, albo pokazuje, co się zmieniło.
#
# ZAKRES JEST OBOWIĄZKOWY. Skrypt bez argumentu kończy się błędem, zamiast robić
# „wszystko, co się da". Bramka, która sama wybiera sobie łatwiejszy zakres, jest
# tą samą klasą usterki co bramka przechodząca z niewypełnionymi polami — w tym
# projekcie ta klasa zawiodła już czterokrotnie.
#
#   predeklaracja  wszystko, co da się zamrozić na hoście — bramka STOP-5.
#                  Worker NIE jest w tym zakresie potrzebny i nie jest budzony.
#   worker         środowisko workera i jego binaria (ANEKS-2, ANEKS-3) — bramka
#                  przed P6, pierwszą fazą wymagającą workera.
#   macierz        predeklaracja + worker + zamrożony rate (ANEKS-1) — bramka
#                  przed P8. Po D-2 zamrożone są DWA środowiska, nie jedno.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
PAPER_REPO="${PAPER_REPO:-/home/michal/github/paper-arXiv}"
JAVA17="${JAVA17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/java}"
JAVAC17="${JAVAC17:-/usr/lib/jvm/java-17-openjdk-amd64/bin/javac}"
FLINK_JAR="${FLINK_JAR:-/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar}"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }
ok() { echo "  ok  $*"; }

# ─── Pola zamrożone w P5 ─────────────────────────────────────────────────────
EXPECTED_BRANCH="experiment/20260808_K23"

# SHA silnika. Kampania przypina ten commit: instrument logicznych zapisów plus
# bramka 36 przypadków o znanej odpowiedzi.
EXPECTED_CODE_SHA="1cfccf97e954025d5fb055f1cfd4f1fa9aff05e8"

# Źródło NORMATYWNE. Zamrażamy nie HEAD `paper-arXiv` (ten legalnie rusza się co
# sesję, bo §9.1 planu realizacji jest aktualizowane), tylko treść samego §10/K23
# — czyli dokładnie ten tekst, wobec którego kampania jest posłuszna. Bramka na
# HEAD byłaby bramką, którą trzeba wyłączać, żeby pracować; ta nie jest.
EXPECTED_SECTION_SHA256="d99518e12c0bc2b315c4227cc7922a6b0f4412feb27c8c46ce78f539de56b39f"

# Zamrożona liczba rekordów źródła szybkiego taktu; wolny takt ma dokładnie
# połowę. Ta sama liczba obowiązuje OBIE maszyny — po stronie Flinka jest to
# `--slots`. Powód zamrożenia: w Kroku 2 liczba zapisów substratu wahała się
# między uruchomieniami (19 wobec 15) wyłącznie od długości źródła i timingu.
EXPECTED_RECORDS="3000"

# Binaria profili na HOŚCIE (x86-64). Binaria workera są innej architektury,
# więc mają własne sumy i własny aneks — patrz zakres `worker`.
declare -A HOST_BINARY_SHA256=(
  [DEFAULT]="9e1cec8ac707ff330e30362bf1974f385794f76982fa85678bd5b44fb1a730d5"
  [NO_R2_CANON]="8d6d795e998410ec0e451c0f1821f7985c70244fb652cad7050f9e66948e7443"
  [NO_R1_FACTOR]="46d5b367c047830ee9dac24e9ebed342d23726c367a50f38af508ab3d5f70b1e"
  [NO_R1_NO_R2]="6159f5d3b070595c91513a4b29ffd476c04a8df8a0eb9d7f71973beba74789a3"
)

# Host: JDK przypięty ŚCIEŻKĄ. Domyślne `java` z PATH to na tym hoście 25.0.3,
# więc sprawdzenie samego `java -version` byłoby sprawdzeniem czegoś innego.
EXPECTED_JAVA_SHA256="a89ad12dc799a14a20d9e570ef788dbcfec70d037d8ede404c2c924354933237"
EXPECTED_JAVAC_SHA256="9a4eedebe503abd0daf458063d99c9dbc2d8892bba03fd5efe48f33d7a65dc9d"
EXPECTED_FLINK_JAR_SHA256="7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493"

# Worker: wymagania środowiskowe zamrożone jako WYMAGANIA. Wartości odczytane
# maszynowo wchodzą aneksami, bo P5 workera nie budzi (D-2, §5A.3).
EXPECTED_GOVERNOR="performance"

ANEKS_RATE="$HERE/ANEKS-1_rate.tsv"
ANEKS_WORKER_BIN="$HERE/ANEKS-2_worker_binaria.tsv"
ANEKS_WORKER_ENV="$HERE/ANEKS-3_worker_srodowisko.tsv"

# ─────────────────────────────────────────────────────────────────────────────

check_predeclaration() {
  echo "== zakres: predeklaracja (STOP-5) =="

  eq "$(git -C "$EXP_REPO" branch --show-current)" "$EXPECTED_BRANCH" "galaz kampanii"
  ok "galaz $EXPECTED_BRANCH"

  eq "$(git -C "$CODE_REPO" rev-parse HEAD)" "$EXPECTED_CODE_SHA" "retractordb HEAD"
  [[ -z "$(git -C "$CODE_REPO" status --short)" ]] || fail "drzewo retractordb brudne"
  ok "silnik przypiety na $EXPECTED_CODE_SHA, drzewo czyste"

  [[ -z "$(git -C "$EXP_REPO" status --short)" ]] || fail "drzewo rdb-experiment brudne"
  ok "drzewo rdb-experiment czyste"

  local section
  section="$(awk '/^#### K23\./{f=1} /^#### K24\./{f=0} f' \
    "$PAPER_REPO/debs/research_plan.md" | sha256sum | awk '{print $1}')"
  eq "$section" "$EXPECTED_SECTION_SHA256" "tresc §10/K23 (zrodlo normatywne)"
  ok "§10/K23 nietkniete od zamrozenia"

  ( cd "$HERE" && sha256sum --quiet -c manifest.sha256 ) \
    || fail "manifest zamrozonych artefaktow sie nie zgadza"
  ok "manifest: $(grep -c . "$HERE/manifest.sha256") artefaktow zgodnych"

  "$HERE/gen_corpus.py" --check >/dev/null || fail "korpus rozjechany z generatorem"
  ok "korpus (dane glowne, kalibracyjne, 21 planow RQL) zgodny z generatorem"

  local fast
  fast="$(wc -l < "$HERE/data/main/vib.txt")"
  eq "$fast" "$EXPECTED_RECORDS" "liczba rekordow zrodla szybkiego taktu"
  eq "$(wc -l < "$HERE/data/main/cur.txt")" "$((EXPECTED_RECORDS / 2))" \
    "liczba rekordow zrodla wolnego taktu"
  ok "zamrozona liczba rekordow: $EXPECTED_RECORDS / $((EXPECTED_RECORDS / 2))"

  "$HERE/gen_blocks.py" --check >/dev/null || fail "blocks.tsv rozjechany z generatorem"
  ok "kolejnosc 20 sparowanych blokow zgodna z zamrozonym ziarnem"

  "$HERE/verdict.py" --selftest >/dev/null || fail "skrypt werdyktu nie przechodzi wlasnej bramki"
  ok "skrypt werdyktu: bramka na sztucznych danych o znanej odpowiedzi zdana"

  "$HERE/mechanism_table.py" --gate >/dev/null || fail "klasyfikator substratow nie przechodzi bramki"
  ok "klasyfikator substratow: rozni sie od wersji obalonej dokladnie tam, gdzie ma"

  # shellcheck source=../lib/common.sh
  source "$EXP_REPO/lib/common.sh"
  local built=0
  while IFS=$'\t' read -r profile slug dedup share commutative factor; do
    [ "$profile" = "profile" ] && continue
    [ -n "$profile" ] || continue
    local binary="$CODE_REPO/build/K23-$slug/src/retractor/xretractor"
    verify_probe_binary_profile "$binary" "$dedup" "$share" "$commutative" "$factor" ||
      fail "profil $profile nie potwierdza sie w --build-info"
    eq "$(sha256sum "$binary" | awk '{print $1}')" "${HOST_BINARY_SHA256[$profile]}" \
      "SHA-256 binarki hosta $profile"
    built=$((built + 1))
  done < "$HERE/profiles.tsv"
  [ "$built" -eq 4 ] || fail "zweryfikowano $built profili, oczekiwano 4"
  ok "cztery binaria hosta: --build-info i SHA-256 zgodne"

  [[ -x "$JAVA17" && -x "$JAVAC17" ]] || fail "brak przypietego JDK 17 pod $JAVA17"
  eq "$(sha256sum "$JAVA17" | awk '{print $1}')" "$EXPECTED_JAVA_SHA256" "SHA-256 java 17"
  eq "$(sha256sum "$JAVAC17" | awk '{print $1}')" "$EXPECTED_JAVAC_SHA256" "SHA-256 javac 17"
  ok "JDK 17 przypiety sciezka (domyslne java w PATH to 25.x — celowo nieuzywane)"

  [[ -r "$FLINK_JAR" ]] || fail "brak jara Flinka: $FLINK_JAR"
  eq "$(sha256sum "$FLINK_JAR" | awk '{print $1}')" "$EXPECTED_FLINK_JAR_SHA256" "SHA-256 flink-dist"
  ok "Flink 2.3.0 przypiety"

  echo "OK: zamrozenie K23 po stronie hosta potwierdzone"
}

check_worker() {
  echo "== zakres: worker (bramka przed P6) =="

  [[ -r "$ANEKS_WORKER_ENV" ]] || fail \
    "brak $ANEKS_WORKER_ENV — srodowisko workera nie zostalo jeszcze odczytane.
   To jest stan legalny WYLACZNIE przed P6: predeklaracja zamraza WYMAGANIA
   (governor '$EXPECTED_GOVERNOR', przypiecie CPU, stalosc kernela), a odczytane
   wartosci wchodza ANEKSEM-3 w pierwszej sesji, ktora budzi workera. Od tego
   momentu ten plik jest niezmienny i ta bramka porownuje z nim stan zywy."
  [[ -r "$ANEKS_WORKER_BIN" ]] || fail "brak $ANEKS_WORKER_BIN (ANEKS-2: binaria workera)"

  local frozen_kernel frozen_cpus live_kernel live_governor live_cpus
  frozen_kernel="$(awk -F'\t' '$1=="kernel"{print $2}' "$ANEKS_WORKER_ENV")"
  frozen_cpus="$(awk -F'\t' '$1=="cpu_pinning"{print $2}' "$ANEKS_WORKER_ENV")"
  [[ -n "$frozen_kernel" && -n "$frozen_cpus" ]] || fail "ANEKS-3 niepelny (kernel, cpu_pinning)"

  live_kernel="$(ssh -o BatchMode=yes "$WORKER_SSH" 'uname -r')" \
    || fail "worker nieosiagalny ($WORKER_SSH) — STOP-1"
  eq "$live_kernel" "$frozen_kernel" "kernel workera"
  ok "kernel workera niezmieniony od zamrozenia: $frozen_kernel"

  live_governor="$(ssh -o BatchMode=yes "$WORKER_SSH" \
    'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr "\n" " "')"
  eq "${live_governor% }" "$EXPECTED_GOVERNOR" "governor wszystkich rdzeni"
  ok "governor: $EXPECTED_GOVERNOR"

  live_cpus="$(ssh -o BatchMode=yes "$WORKER_SSH" 'nproc --all')"
  eq "$live_cpus" "$(awk -F'\t' '$1=="cpu_online"{print $2}' "$ANEKS_WORKER_ENV")" \
    "liczba rdzeni workera"
  ok "przypiecie CPU wg ANEKS-3: $frozen_cpus"

  while IFS=$'\t' read -r profile digest; do
    [ "$profile" = "profile" ] && continue
    [ -n "$profile" ] || continue
    local live
    live="$(ssh -o BatchMode=yes "$WORKER_SSH" \
      "sha256sum ~/K23/build/K23-$profile/src/retractor/xretractor | cut -d' ' -f1")" \
      || fail "brak binarki profilu $profile na workerze"
    eq "$live" "$digest" "SHA-256 binarki workera $profile"
  done < "$ANEKS_WORKER_BIN"
  ok "binaria workera zgodne z ANEKS-2"

  echo "OK: zamrozenie K23 po stronie workera potwierdzone"
}

check_matrix() {
  echo "== zakres: macierz (bramka przed P8) =="
  [[ -r "$ANEKS_RATE" ]] || fail \
    "brak $ANEKS_RATE — rate nie zostal jeszcze skalibrowany i zamrozony.
   §10 umieszcza kalibracje PO predeklaracji, wiec predeklaracja zamraza PROTOKOL
   kalibracji, a wartosc rate wchodzi ANEKSEM-1 podpisanym przed macierza (P7 ->
   STOP-7). Macierzy nie wolno uruchomic wczesniej."
  local rate
  rate="$(awk -F'\t' '$1=="rate_scale"{print $2}' "$ANEKS_RATE")"
  [[ -n "$rate" ]] || fail "ANEKS-1 nie zawiera pola rate_scale"
  awk -F'\t' '$1=="calibration_saw_effect" && $2!="no" {exit 1}' "$ANEKS_RATE" \
    || fail "ANEKS-1 nie potwierdza, ze kalibracja NIE porownywala DEFAULT z ablacja"
  ok "rate zamrozony (skala $rate), kalibracja bez ogladania efektu"
  echo "OK: bramka przed macierza przeszla"
}

case "${1:-}" in
  predeklaracja) check_predeclaration ;;
  worker)        check_worker ;;
  macierz)       check_predeclaration; check_worker; check_matrix ;;
  *)
    echo "uzycie: $(basename "$0") {predeklaracja|worker|macierz}" >&2
    echo "zakres jest obowiazkowy — skrypt nie wybiera go sam" >&2
    exit 2
    ;;
esac
