#!/usr/bin/env bash
# S2 — audyt roznicowy: co regresja pojemnosci AGSE zmienila, a czego nie tknela.
#
# Ta sama para binarek co w S1 (FIXED vs MUTANT, roznica: jedna decyzja
# w compiler::computeRequiredCapacities). Trzy warstwy obserwacji:
#
#   A. plan — kompilacja calego korpusu RQL (-c) i porownanie zrzutu planu,
#   B. artefakty plikowe — pelny potok exactness-replay.rql (17 strumieni),
#   C. plan z polityka MEMORY — rec205-qrs.rql, czyli ta klasa planu,
#      w ktorej regresja byla obserwowalna.
#
# A i B odpowiadaja na pytanie "czy wyniki z 20260728 wymagaja powtorki".
# C kwantyfikuje szkode, zeby nie zostala opisana wylacznie jakosciowo.
#
# Badanie nie mierzy czasu i nie korzysta z workera.
set -euo pipefail

cd "$(dirname "$0")"
ROOT="${BUILD_TREES_ROOT:-${TMPDIR:-/tmp}/rdb-extend}"
EXPERIMENT_REPO="$(cd ../.. && pwd)"
SAMPLES="${SAMPLES:-4000}"

BUILD_TREES_ROOT="$ROOT" ../lib/build_trees.sh

FIXED_BIN="$ROOT/fixed/build/Debug/src/retractor/xretractor"
MUTANT_BIN="$ROOT/mutant/build/Debug/src/retractor/xretractor"
CORPUS_REPO="$ROOT/fixed"   # klon stoi na commicie z poprawka; korpus RQL jest ten sam w obu

mkdir -p raw

# --- A. korpus RQL: zrzut planu i kod zakonczenia -----------------------------
# Dwa artefakty srodowiskowe sa normalizowane, bo inaczej udawalyby roznice
# miedzy binarkami, a wystepuja rowniez miedzy dwoma przebiegami tej samej:
#   - komunikaty ANTLR zawieraja adres obiektu (ASLR),
#   - sciezka pliku wejsciowego jest wypisywana w calosci, a kazda kompilacja
#     idzie z innego katalogu tymczasowego.
# Ten sam problem ma results_20260728_K4/collect.py — patrz results.md.
CORPUS_RC=0
python3 - "$FIXED_BIN" "$MUTANT_BIN" "$CORPUS_REPO" >raw/corpus_plan.txt <<'PY' || CORPUS_RC=$?
import hashlib, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

fixed, mutant, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ASLR = re.compile(r" at 0x[0-9a-f]+")

cases = []
for suite, root in [("integration_serial", repo/"test/IntegrationTest_serial"),
                    ("integration_parallel", repo/"test/IntegrationTest_parallel"),
                    ("examples", repo/"examples")]:
    cases += [(suite, p) for p in sorted(root.rglob("*.rql"))]

def compile_case(binary, source):
    with tempfile.TemporaryDirectory(prefix="rdb-extend-") as tmp:
        work = Path(tmp)/"case"
        shutil.copytree(source.parent, work, ignore=shutil.ignore_patterns("__pycache__"))
        env = os.environ.copy(); env["RDB_BENCH_PLAN"] = "1"
        try:
            done = subprocess.run([str(binary), str(work/source.name), "-c"], cwd=work, env=env,
                                  capture_output=True, text=True, errors="replace", timeout=120)
            clean = lambda text: ASLR.sub("", text.replace(str(work), "<WORK>"))
            return done.returncode, clean(done.stdout), clean(done.stderr)
        except subprocess.TimeoutExpired as err:
            return 124, err.stdout or "", "TIMEOUT"

def digest(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

identical, different = 0, []
for suite, src in cases:
    a, b = compile_case(fixed, src), compile_case(mutant, src)
    same = a[0] == b[0] and digest(a[1]) == digest(b[1]) and digest(a[2]) == digest(b[2])
    rel = src.relative_to(repo)
    print(f"{'IDENTYCZNY' if same else 'ROZNY     '}  rc={a[0]}/{b[0]}  {rel}")
    identical += same
    if not same:
        different.append(str(rel))

print()
print(f"plikow RQL: {len(cases)}")
print(f"identyczny plan + rc: {identical}")
print(f"rozne: {len(different)} {different}")
sys.exit(0 if not different else 1)
PY

# --- B. artefakty plikowe potoku exactness-replay ------------------------------
ECG="$CORPUS_REPO/examples/ecg/rec205"
for label in fixed mutant; do
  dir="$ROOT/replay_$label"
  rm -rf "$dir"; mkdir -p "$dir"
  cp "$ECG/rec205" "$ECG/bp_coef.txt" "$ECG/d_coef.txt" "$dir/"
  cp "$EXPERIMENT_REPO/config/exactness-replay.rql" "$dir/"
  if [ "$label" = "mutant" ]; then bin="$MUTANT_BIN"; else bin="$FIXED_BIN"; fi
  ( cd "$dir" && "$bin" exactness-replay.rql -r -k -m "$SAMPLES" ) \
    >"raw/replay_$label.log" 2>&1
done

: >raw/replay_compare.txt
REPLAY_DIFF=0
while IFS= read -r artifact; do
  a="$ROOT/replay_fixed/$artifact"; b="$ROOT/replay_mutant/$artifact"
  if [[ "$artifact" == *.meta ]]; then
    # 8 pierwszych bajtow .meta to znacznik czasu utworzenia (metaIndexStore).
    if cmp -s <(tail -c +9 "$a") <(tail -c +9 "$b"); then
      printf 'IDENT-PO-TIMESTAMP  %s\n' "$artifact" >>raw/replay_compare.txt
    else
      printf 'ROZNY               %s\n' "$artifact" >>raw/replay_compare.txt
      REPLAY_DIFF=$((REPLAY_DIFF + 1))
    fi
  elif cmp -s "$a" "$b"; then
    printf 'IDENTYCZNY          %s\n' "$artifact" >>raw/replay_compare.txt
  else
    printf 'ROZNY               %s\n' "$artifact" >>raw/replay_compare.txt
    REPLAY_DIFF=$((REPLAY_DIFF + 1))
  fi
done < <(find "$ROOT/replay_fixed" -maxdepth 1 -type f -printf '%f\n' |
  grep -Ev '^(rec205|bp_coef\.txt|d_coef\.txt|exactness-replay\.rql)$' | sort)
REPLAY_TOTAL=$(wc -l <raw/replay_compare.txt)

# --- C. plan z polityka MEMORY: skala szkody ----------------------------------
# rec205-qrs.rql zapisuje wylacznie qrs_out; pozostale strumienie sa VOLATILE,
# czyli dokladnie ten uklad, w ktorym regresja byla obserwowalna.
for label in fixed mutant; do
  dir="$ROOT/qrs_$label"
  rm -rf "$dir"; mkdir -p "$dir"
  cp "$ECG/rec205" "$ECG/bp_coef.txt" "$ECG/d_coef.txt" "$dir/"
  sed 's/STREAM qrs_out FROM mlii+mwi+mwi_thr VOLATILE/STREAM qrs_out FROM mlii+mwi+mwi_thr/' \
    "$ECG/rec205-qrs.rql" >"$dir/qrs.rql"
  if [ "$label" = "mutant" ]; then bin="$MUTANT_BIN"; else bin="$FIXED_BIN"; fi
  ( cd "$dir" && "$bin" qrs.rql -r -k -m "$SAMPLES" ) >"raw/qrs_$label.log" 2>&1
done

python3 - "$ROOT/qrs_fixed/qrs_out" "$ROOT/qrs_mutant/qrs_out" >raw/qrs_signal.txt <<'PY'
import struct, sys
def load(path):
    raw = open(path, "rb").read()
    return [struct.unpack_from("<iii", raw, i * 12) for i in range(len(raw) // 12)]
fixed, mutant = load(sys.argv[1]), load(sys.argv[2])
names = ["mlii-900", "mwi*5", "detekcja*5"]
print(f"rekordow: fixed={len(fixed)} mutant={len(mutant)}")
for col, name in enumerate(names):
    f = [r[col] for r in fixed]; m = [r[col] for r in mutant]
    print(f"{name:12s} fixed[min={min(f)} max={max(f)}]  mutant[min={min(m)} max={max(m)}]")
det_f = sum(1 for r in fixed if r[2] > 0)
det_m = sum(1 for r in mutant if r[2] > 0)
print(f"probek z detekcja>0: fixed={det_f} mutant={det_m}")
PY

# --- raport -------------------------------------------------------------------
{
  printf '# S2 — audyt roznicowy regresji pojemnosci AGSE\n\n'
  printf '%s\n' "- data: $(date -Is)"
  printf '%s\n' "- FIXED: \`$(git -C "$ROOT/fixed" rev-parse HEAD)\` (Debug)"
  printf '%s\n' "- MUTANT: ten sam commit z odwrocona silnikowa czescia poprawki (Debug)"
  printf '%s\n\n' "- samples: $SAMPLES"

  printf '## A. Korpus RQL — plan i kod zakonczenia\n\n```\n'
  tail -4 raw/corpus_plan.txt
  printf '```\n\n'

  printf '## B. Artefakty potoku exactness-replay (17 strumieni)\n\n'
  printf '%s\n' "- porownanych plikow: $REPLAY_TOTAL"
  printf '%s\n\n' "- roznych: $REPLAY_DIFF"
  printf 'Pelna lista: `raw/replay_compare.txt`.\n\n'

  printf '## C. Plan z polityka MEMORY (rec205-qrs.rql)\n\n```\n'
  cat raw/qrs_signal.txt
  printf '```\n'
} >results.md

cat results.md

if [ "$REPLAY_DIFF" -ne 0 ] || [ "$CORPUS_RC" -ne 0 ]; then
  printf 'BLAD: regresja dotknela artefaktow plikowych albo planu — patrz raw/\n' >&2
  exit 1
fi
