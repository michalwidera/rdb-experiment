# Dwie wady instrumentu wykryte w trakcie badania

Oba błędy były w **moim harnessie**, nie w silniku, i oba zostały znalezione
przez pierwszy przebieg. Kolejność — poprawka po zobaczeniu wyniku — zawsze
wymaga ujawnienia, dlatego są opisane tutaj, a surowe wyniki pierwszego
przebiegu zachowane.

## Wada 1 — potok niedeterministyczny jako wyrocznia

**Objaw.** Pierwszy przebieg dał werdykt „WPŁYW WYKRYTY": potok
`test/IntegrationTest_parallel/dsp/query.rql` produkował inne bajty pod
`HISTORICAL` i pod `FIXED`, przy identycznych rozmiarach plików i identycznym
zrzucie planu.

**Przyczyna.** Wejściem potoku jest `/dev/urandom`:

```rql
DECLARE data BYTE STREAM source, 0.02 FILE '/dev/urandom'
```

Sprawdzone empirycznie: **ten sam** silnik, dwa przebiegi → te same różnice
w `accRow`, `output`, `outputAll`, `signalRow`. Potok jest niedeterministyczny
z konstrukcji, więc nie może służyć za wyrocznię porównania między silnikami.

**Poprawka.** Kontrola determinizmu jako element badania, a nie samo usunięcie
kłopotliwego potoku: dla każdego potoku wykonywany jest **trzeci** przebieg,
`HISTORICAL` po raz drugi. Jeżeli dwa przebiegi tym samym silnikiem się różnią,
potok jest oznaczany jako niedeterministyczny i wyłączany z kryterium wraz
z podaniem powodu. Dzięki temu ta klasa błędu ujawni się sama w każdym
przyszłym przebiegu, także dla potoków, o których dziś nie wiem.

**Kierunek błędu.** Wada dawała fałszywy alarm — werdykt „wpływ wykryty" tam,
gdzie wpływu nie było. Poprawka usuwa błąd, którego znak był **niekorzystny**
dla poprawiającego, co jest sytuacją odwrotną do naciągania wyniku.

## Wada 2 — puste porównanie raportowane jako zgodność

**Objaw.** Potok `rec205-qrs.rql` raportował `identyczne: true` przy
`artefaktow: 0`. Zgodność zbioru pustego z pustym.

**Przyczyna.** Kolektor zbierał artefakty wyłącznie z podkatalogu `temp/`,
zakładając obecność dyrektywy `STORAGE 'temp'`. Dwa z czterech potoków jej nie
mają:

| Potok | `STORAGE` |
|---|---|
| `examples/ecg/rec205/rec205-qrs.rql` | brak — pisze do katalogu roboczego |
| `test/IntegrationTest_serial/agse_volatile/query.rql` | brak — pisze do katalogu roboczego |
| `test/IntegrationTest_parallel/dsp/query.rql` | `temp` |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | `temp` |

Połowa warstwy artefaktowej badania była zatem pusta i przechodziła.

**Poprawka.** Dwie zmiany:

1. Artefakt definiowany różnicowo: przed uruchomieniem robiony jest snapshot
   hashy całego katalogu roboczego, a po uruchomieniu zbierany każdy plik
   **nowy albo zmieniony**. Działa niezależnie od tego, gdzie potok pisze,
   i nie wymaga wiedzy o dyrektywach.
2. Puste porównanie jest **porażką**, nie zgodnością. Zbiór pusty nigdy nie
   przejdzie w milczeniu.

**Skutek po poprawce.** Porównywanych artefaktów: `rec205` 15, `agse_volatile`
11, `optimizer_ablation` 116 — razem 142, zamiast 116 przy dwóch potokach
pustych.

## Wniosek metodologiczny

Obie wady należą do tej samej klasy: **milczenie instrumentu wyglądało jak
sukces**. Pierwsza dawała fałszywy alarm i była nieszkodliwa, bo zmusiła do
sprawdzenia. Druga była groźna — cicho zawężała badanie o połowę i przechodziła.
To ta sama klasa co luka pokrycia odnotowana przy K19 i przy pierwszym teście
regresji do `Fix (#214)`.

Wniosek do stosowania w kolejnych kampaniach: **każde porównanie musi
raportować LICZBĘ porównanych rzeczy**, a zero musi być błędem. Sam wynik
„zgodne" nie odróżnia zgodności od braku danych.
