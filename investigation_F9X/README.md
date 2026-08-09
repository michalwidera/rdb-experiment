# Śledztwo F9-X — przyczyna rozjazdu RetractorDB ↔ Flink z kampanii K23

**Założone 2026-08-09, po zamknięciu K23.** Kampania K23 jest **skończona**
i jej katalog `results_20260808_K23v2/` jest **zamrożony** — nic tutaj go nie
dotyka i nic stąd nie wchodzi do jej wyników. To jest osobna praca, uruchomiona
decyzją człowieka: „chcę poznać przyczynę rozjazdu i naprawić silnik, jeśli wina
leży po stronie RetractorDB".

Plan tej pracy, **zamknięty 2026-08-09**:
[`paper-arXiv/debs/done/plan-naprawy-F9.md`](../../paper-arXiv/debs/done/plan-naprawy-F9.md).
Zapis trwały: `research_plan.md` §14.19.

## Co już jest ustalone

Przyczyna rozjazdu **jest znaleziona i sprawdzona na całej serii**, nie na
kilku pierwszych slotach. Szczegóły z liczbami: [`REFERENCE.md`](REFERENCE.md).

W jednym zdaniu: **po przeplocie `#` tożsamość strumieni składowych znika**,
więc `A[0]` i `B[0]` wewnątrz monitora nad `A#B` odwzorowują się na tę samą
wielkość — bieżącą wartość strumienia przeplecionego. Port Flinka trzyma
osobny zatrzask per strumień i te odwołania rozróżnia.

Czego to **nie** rozstrzygało: który odczyt jest poprawny. To była decyzja
człowieka i pierwszy punkt planu naprawy.

## Werdykt — 2026-08-09

**D-F1 = S3: żaden z dwóch odczytów nie jest zamierzony.** Model L (zatrzask
per strumień) nie występuje w podstawach formalnych nigdzie — jest wynalazkiem
portu Flinka. Model S wynika z zapisanej reguły aliasowania (`A[0]` to pozycja
w schemacie strumienia z `FROM`, nie „bieżąca wartość A") przy wymogu
**identycznych schematów** obu argumentów `#`. Składową odzyskuje się rozplotem
`&` / `%` — jedyną operacją odwrotną do `#` w algebrze.

Odwołanie do składnika po przeplocie jest więc od silnika
**`530c80eb3c0ae031f3b3e67712f62547f18771be`** **błędem kompilacji**.
Reproducery z tego katalogu są dziś **odrzucane**:

```
$ xretractor -c reproducer/minimal_identity.rql
Check result:Stream 'roznica' refers to 'A', which is a constituent of an
interleave (#). ... Refer to 'roznica' by its own name, or recover the
constituent with de-interleave (& / %).
```

**Znalezisko B nie było rozjazdem obliczeniowym silnika**, tylko cichą
dwuznacznością języka przy wyroczni realizującej semantykę spoza algebry.
**Znalezisko A pozostaje otwarte** — naprawa go nie tyka.

Materiał w tym katalogu zachowuje wartość dowodową: został zebrany na silniku
`ebd8aab`, przed naprawą, i to na nim opiera się §14.19.

## Zawartość

| Ścieżka | Co to jest |
|---|---|
| `REFERENCE.md` | materiał porównawczy — liczby, proweniencja, odsyłacze do `main` |
| `reference/model_semantyk.py` | dwa modele semantyki i dowód, który odtwarza którą stronę; ma bramkę kształtu przeplotu wobec artefaktu silnika |
| `reference/rdb_m1.txt` | seria RetractorDB, 4496 wartości, odtworzona na hoście |
| `reference/flink_m1_natural.txt` | seria Flinka, 4500 wartości, odtworzona na hoście |
| `reference/rdb_run/` | przebieg RetractorDB (`F9_X_Q1`, `SUBSTRAT 'memory'`) |
| `reference/probe_sub/` | ten sam plan **bez** `SUBSTRAT 'memory'` — substraty utrwalone na dysku, wynik `m1` identyczny |
| `reference/probe_identity/` | sonda tożsamości strumieni po przeplocie |
| `reference/flink_run/` | przebieg `F9XJob --variant natural --q 1` wraz z planami |
| `reproducer/minimal_identity.rql` | **minimalny reproducer** — trzy linijki, bez Flinka i bez kampanii |

## Jak odtworzyć

```bash
# strona RetractorDB (host, binarium profilu DEFAULT z K23)
cd reference/rdb_run && cp <kampania>/data/main/*.txt . \
  && <bin>/xretractor F9_X_Q1.rql -m 6000 -r -k

# strona Flinka (JDK 17 PRZYPIĘTY ŚCIEŻKĄ — domyślne java na hoście to 25.x)
CP="<kampania>/flink/build:$(find /home/michal/opt/flink-2.3.0/lib -name '*.jar' | sort | paste -sd:)"
/usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp "$CP" F9XJob \
  --variant natural --q 1 --slots 3000 --a … --b … --c … --d … --out-dir … --sink-dir …

# porównanie obu stron z modelami
cd reference && ./model_semantyk.py
```

## Pułapki, na które już wpadliśmy

* **`read_flink_csv` zwraca `(slot, (wartość,))`**, a plik ma trzy kolumny
  `monitor,slot,wartość`. Wzięcie `r[0]` daje numer slotu i pozorne 0% zgodności.
* **`SUBSTRAT 'memory'` nie utrwala pośrednich na dysku** — zostają tylko
  `.desc` i `.meta`. Żeby zobaczyć wartości substratów, usuń tę dyrektywę;
  sprawdzone, że wynik `m1` jest wtedy **identyczny** (4496 wartości co do
  jednej), więc zmiana jest diagnostycznie neutralna.
* Domyślne `java` na hoście to **25.0.3**, nie 17. JDK 17 przypinać ścieżką.
* **`freeze_check.sh` kampanii nie przechodzi już po merge'u** — sprawdza nazwę
  gałęzi (`experiment/20260808_K23`), a jesteśmy na `main`. To **nie jest
  defekt**: bramka pilnowała żywej kampanii. Sam skrypt jest artefaktem
  zamrożonym (jest w `manifest.sha256`), więc **nie wolno go poprawiać**.
  Substancję zamrożenia sprawdza się teraz wprost:
  `sha256sum -c manifest.sha256` — 2026-08-09 dawało **188/188 OK**.
