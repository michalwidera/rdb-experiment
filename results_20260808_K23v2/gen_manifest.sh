#!/bin/bash
# Manifest zamrożonych artefaktów K23 — lista jest tu, nie w `find .`.
#
# Powód: `find` zbierałby też pliki wynikowe, katalogi robocze i wszystko, co
# przyjdzie później, więc manifest przestałby być zamrożeniem, a stałby się
# zdjęciem katalogu. Poniższa lista jest DEKLARACJĄ, co należy do aparatury.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

mapfile -t FILES < <(
  printf '%s\n' \
    PREDEKLARACJA.md \
    RAPORT_PILOTA.md \
    SZKIC_RODZIN.md \
    SZKIC_D3.md \
    README.md \
    profiles.tsv \
    blocks.tsv \
    build_profiles.sh \
    freeze_check.sh \
    gen_corpus.py \
    gen_blocks.py \
    gen_manifest.sh \
    mechanism_table.py \
    verdict.py \
    flink/PLANY_FLINKA.md \
    flink/README.md \
    flink/canonical_vectors.tsv
  find data rql -type f | sort
  find pilot -maxdepth 1 -type f \( -name '*.rql' -o -name '*.py' -o -name '*.sh' -o -name 'src_*.txt' \) | sort
  # Surowe zrzuty pilota: bramka klasyfikatora liczy na nich swoja odpowiedz,
  # wiec sa aparatura, a nie tylko zalacznikiem do raportu.
  find pilot/out -type f | sort
  # Liczniki przebiegow runtime (iteracja 2). Bez nich `freeze_check.sh
  # predeklaracja` pilnowalby plikow, ktorych manifest nie obejmuje — a dowod
  # wykonywalnosci, ktorego nikt nie zamrozil, mozna po cichu dopisac po fakcie.
  find pilot/out_rt -type f | sort
  # Zapis przypadku, ktory bramka runtime ma ODRZUCIC (plan z `Abs`: kompiluje sie,
  # nie wykonuje). Bez niego w katalogu zostalby sam dowod strony zdanej.
  find pilot/neg -maxdepth 1 -type f \
    \( -name '*.rql' -o -name 'negatyw.*' -o -name 'compile.*' -o -name 'odrzucenie.txt' \) | sort
  find flink/java -name '*.java' | sort
  find flink -maxdepth 1 -name '*.sh' | sort
  find flink/oracle -type f \( -name '*.cc' -o -name '*.sh' \) | sort
)

sha256sum "${FILES[@]}" > manifest.sha256
echo "OK: manifest.sha256 — ${#FILES[@]} artefaktow"
