#!/usr/bin/env bash
# R600: ponowny wybor strumienia subskrybowanego (regula R376) binarka R600_A -> streams.tsv w katalogu
# aparatury R600 (tylko na workerze, embargo); wynik porownywany ze streams.tsv z R376.
# Regula: najkrotszy takt (`delta` z `xqry -d -y`) wsrod strumieni publicznych - bez `$` (skladowa
# substratu) i bez prefiksu `STREAM_` (substrat syntetyczny); przy remisie pierwszy w kolejnosci `xqry -d`.
# Silnik strony A, bez -t, kilka sekund; potem sprawdzenie, ze `xqry -s <strumien>` dostaje wiersz
# (sam kod wyjscia nie wystarcza: na strumieniu szybszym niz ~1 kHz `-m 1` nie konczy sie, patrz run_one.py).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
: > "$here/streams.tsv"
for fam in uc03 uc05 uc06 uc07 uc08; do
  d="/dev/shm/r376/select_$fam"
  rm -rf "$d" && cp -r "/dev/shm/r376/data/$fam" "$d" && mkdir -p "$d/temp" && cd "$d"
  cp "$HOME/R376/bin/R600_A/xretractor" "$HOME/R376/bin/R600_A/xqry" .
  export TMPDIR="$d/temp"
  setsid ./xretractor query.rql -k -r > engine.out 2>&1 < /dev/null &
  sleep 4
  stream=$(timeout 20 ./xqry -w -d -y | python3 -I -c '
import sys, fractions
rows, cur = [], {}
for line in sys.stdin:
    s = line.strip()
    if s.startswith("- name:"):
        cur = {"name": s.split(":", 1)[1].strip()}; rows.append(cur)
    elif s.startswith("delta:") and cur:
        cur["delta"] = fractions.Fraction(s.split(":", 1)[1].strip())
pub = [r for r in rows if "$" not in r["name"] and not r["name"].startswith("STREAM_")]
best = min(pub, key=lambda r: r["delta"])
print(best["name"], best["delta"])')
  name=${stream% *}
  delta=${stream#* }
  row=$(timeout 20 ./xqry -s "$name" -m 1 2> /dev/null | head -1 || true)
  ./xqry -k > /dev/null 2>&1 || true
  for _ in $(seq 20); do pgrep -x xretractor > /dev/null || break; sleep 0.5; done
  if pgrep -x xretractor > /dev/null; then echo "$fam: silnik nie zakonczyl sie"; exit 2; fi
  [ -n "$row" ] || { echo "$fam: strumien nie dostarczyl wiersza"; exit 2; }
  printf '%s\t%s\t%s\n' "$fam" "$name" "$delta" >> "$here/streams.tsv"
  echo "$fam delta=$delta row=ok"
  cd / && rm -rf "$d"
done
