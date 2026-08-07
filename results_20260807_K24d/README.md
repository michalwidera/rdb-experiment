# K24d — przebieg na silniku po naprawach `>N` i `#`

Krok 3e planu `paper-arXiv/debs/research_plan.md` §16.1, dołożony 2026-08-07
jako **warunek wejścia transferu K24 do artykułu** (krok 3a). Badanie
deterministyczne, compile-only w części kampanijnej, bez workera i bez pomiaru
czasu; bramka odwzorowania uruchamia silnik na tej samej maszynie co K24, K24r,
K24b i K24p.

| Dokument | Zawartość |
|---|---|
| [PIN.md](PIN.md) | punkt odniesienia: SHA silnika, `ctest` Debug i Release, sumy plików rachunku, lista zmian aparatury |
| [VERDICT.md](VERDICT.md) | werdykt na ziarnie porównawczym `20260804` (ten sam korpus co K24p i potwierdzenie K24r) |
| [VERDICT_oos.md](VERDICT_oos.md) | werdykt na ziarnie potwierdzającym `20260807` |
| [REPORT.md](REPORT.md) | zestawienie „przed/po” wobec K24p, status epistemiczny, wnioski dla artykułu |

Predeklaracja kampanii jest **odziedziczona** z
[`../results_20260807_K24p/PREDECLARATION.md`](../results_20260807_K24p/PREDECLARATION.md):
te same ziarna, ten sam generator, te same kryteria i progi. K24d nie
przedeklarowuje niczego nowego i **nie jest testem prospektywnym** — pełny
status epistemiczny w REPORT.md §4.

## Wynik w jednym zdaniu

Na silniku `34db1a2` **sześć klas operatorów ma ogon dokładny** (`PASS`, `@`,
`+`, redukcje, `>N`, `#`), **trzy zawyżają o dokładnie jeden slot** (`-`,
`Θ`, `~Θ`), **żadna nie zaniża**, początek logiczny jest dokładny w 100%
węzłów wszystkich dziewięciu klas na obu ziarnach, a człon (b) pozostaje
wsparty w swojej zawężonej populacji (2310/2310).

## Co się zmieniło wobec K24p

Dwie klasy przeszły z reżimu zawyżającego do dokładnego, obie wskutek napraw
silnika z 2026-08-07, nie wskutek zmiany pomiaru:

| Klasa | K24p (`db4a360`) | K24d (`34db1a2`) | Naprawa |
|---|---|---|---|
| `>N` | 93,4% — zawyżająca | **100% — dokładna** | krok 3d, `fcc5a44` |
| `#` | 92,1% — zawyżająca | **100% — dokładna** | krok 3c, `34db1a2` |

**Kontrola zasięgu napraw** (porównanie wiersz po wierszu z surowymi danymi
K24p, ten sam korpus co do węzła):

| Wielkość | Gdzie się zmieniła |
|---|---|
| reguła **izolowana** (ogon węzła z ogonów składowych wziętych z oracle'a) | **wyłącznie** `SHIFT` (353 i 357 węzłów) oraz `HASH` (471 i 482) |
| ogon **silnika** (propagowany przez plan) | dodatkowo `PASS`, `AGSE`, `ADD`, `SUB`, `THETA`, `NTHETA`, `REDUCE` |
| **origin** | nigdzie, na żadnym ziarnie |

Rozjazd między pierwszym a drugim wierszem nie jest usterką, tylko dowodem, że
kolumna izolowana robi to, po co powstała: **reguły siedmiu klas są nietknięte,
a ich ogony w planach zmieniły się wyłącznie przez dziedziczenie po naprawionym
dziecku.** Liczby w pierwszym wierszu zgadzają się co do węzła z liczbami
niezgodności zmierzonymi w K24p (`SHIFT` 6,6%, `HASH` 7,9%) — naprawy trafiły
dokładnie w te węzły, które K24p wskazała, i w żadne inne.

## Czym to NIE jest

To **nie jest** unieważnienie K24, K24r, K24b ani K24p. Każda z tych kampanii
opisuje inny stan silnika i pozostaje w mocy dla swojego stanu. Łańcuch jest
dziś pięcioogniwowy i to jest wynik obserwacyjny wart zapisania: **kampania
semantyczna starzeje się razem z rachunkiem, który mierzy.**

To **nie jest** test prospektywny. Obie naprawy sprawdzono offline na korpusie
K24p **przed** dotknięciem silnika, więc kampania potwierdza przy przypiętym
SHA to, co było już wiadome na poziomie postaci zamkniętej. Wartość K24d leży
gdzie indziej: dostarcza kolumny **silnik wobec oracle'a** dla stanu, który
faktycznie pójdzie do pakietu artefaktów (krok 4).

## Relacja do katalogów poprzedników

[`../results_20260803_K24/`](../results_20260803_K24/),
[`../results_20260804_K24r/`](../results_20260804_K24r/),
[`../results_20260804_K24b/`](../results_20260804_K24b/) oraz
[`../results_20260807_K24p/`](../results_20260807_K24p/) są **zamrożonymi
punktami odniesienia** i nie zostały tu w żaden sposób zmienione.

`generator.py` jest **bajtowo identyczny** we wszystkich pięciu kampaniach —
to warunek ich porównywalności. `oracle/model.py` jest bajtowo identyczny
z K24p: naprawy dotyczyły rachunku silnika, nie definicji operatorów, więc
model zdarzeniowy nie miał się z czego zmienić.

## Układ katalogu

```
oracle/          model zdarzeniowy (origin + ogon), most do silnika, wykonanie,
                 replika rachunku silnika (za silnikiem, dla bramki mutantów)
tests/           cztery bramki wykonywane przed kampanią
generator.py     zamrożony generator korpusu (bez zmian wobec K24)
run_campaign.py  kampania compile-only
verdict.py       werdykt automatyczny per klasa operatora, osobno ogon i origin
capacity.py      kontrola modelu pojemności historii
run_member_b.py  ramię członu (b) na ziarnie 20260805
run_mapping_gate.py  bramka odwzorowania — silnik uruchamiany naprawdę
raw/             surowe wyniki, jeden wiersz na obserwację węzłową
```
