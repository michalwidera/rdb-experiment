# Śledztwo F9-X — przyczyna rozjazdu RetractorDB ↔ Flink z kampanii K23

**Założone 2026-08-09, po zamknięciu K23.** Kampania K23 jest **skończona**
i jej katalog `results_20260808_K23v2/` jest **zamrożony** — nic tutaj go nie
dotyka i nic stąd nie wchodzi do jej wyników. To jest osobna praca, uruchomiona
decyzją człowieka: „chcę poznać przyczynę rozjazdu i naprawić silnik, jeśli wina
leży po stronie RetractorDB".

Plan tej pracy: [`paper-arXiv/debs/plan-naprawy-F9.md`](../../paper-arXiv/debs/plan-naprawy-F9.md).

## Co już jest ustalone

Przyczyna rozjazdu **jest znaleziona i sprawdzona na całej serii**, nie na
kilku pierwszych slotach. Szczegóły z liczbami: [`REFERENCE.md`](REFERENCE.md).

W jednym zdaniu: **po przeplocie `#` tożsamość strumieni składowych znika**,
więc `A[0]` i `B[0]` wewnątrz monitora nad `A#B` odwzorowują się na tę samą
wielkość — bieżącą wartość strumienia przeplecionego. Port Flinka trzyma
osobny zatrzask per strumień i te odwołania rozróżnia.

Czego to **nie** rozstrzyga: który odczyt jest poprawny. To jest decyzja
człowieka i pierwszy punkt planu naprawy.

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
