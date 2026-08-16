# K26v3 / H9 — werdykt kampanii, 2026-08-16

Werdykt wydał zamrożony `verdict.py` uruchomiony **jeden raz** na kompletnych
wejściach P6/P8, kodem wyjścia **0**. Nie pochodzi z interpretacji wykresów ani
z żadnego doboru wejść po fakcie.

**WERDYKT: H9 WSPARTA w klasie `Q=8`, 3/3 rodziny** (reguła progowa wymagała 2/3).

## Przypięcie kampanii

| Pole | Wartość |
|---|---|
| Silnik | `856ee54b0f4ab450a6b61e3c08e045f404a79488` |
| Eksperyment | `81bf4bea00efb922678862c90462fb3c0dfe5fda`, gałąź `experiment/20260814_K26v3` |
| ANEKS-0 (`results/ANEKS-0_start.tsv`, poza git) | `f7e55ecbf7ca8c9ae7313b50e98fb00498abfdbe9ca6d746afa8371ffedd77ed` |
| ANEKS-1 (`results/ANEKS-1_rate.tsv`, poza git) | `fc6e549a8666ec6c23681c87b2d55270038a5c014cb4a9b42d6e3816b52003f1` |
| `rate_scale` | 4 (najmniejszy czynnik spełniający §12; udział p99 41,7%) |
| Worker | `pi400`, aarch64, governor `performance`, ANEKS-2/ANEKS-3 |

Żaden wynik K23, K26 ani K26v2 nie wchodzi do tej kampanii ani do tej redukcji.

## P8 — macierz kosztowa

Pomiar prowadziła usługa `k26v3-p8.service` na workerze: jedna rodzina na
uruchomienie, restart między rodzinami, samodzielny powrót po zaniku zasilania.
Host nie brał udziału w pomiarze.

| Rodzina | Start | Koniec | Czas | Komórki | `rc` |
|---|---|---|---:|---:|---|
| F9-R2 | 2026-08-14 17:29:52 | 2026-08-15 09:39:25 | 16 h 09 min | 480/480 | 0 |
| F9-R1 | 2026-08-15 09:41:07 | 2026-08-16 01:51:17 | 16 h 10 min | 480/480 | 0 |
| F9-X | 2026-08-16 01:52:58 | 2026-08-16 18:03:23 | 16 h 10 min | 480/480 | 0 |

Razem **1440/1440 komórek** i 48 h 34 min zegara, bez `STOP-8`, bez `HALT`,
bez interwencji z hosta. Dwa zaplanowane restarty workera wypadły między
rodzinami; usługa wstała sama z bootu i podjęła następną rodzinę.

Surowe sondy pozostają poza git; ich audyt integralności prowadzi
[`K26v3-P8_raw.index.tsv`](K26v3-P8_raw.index.tsv). Sumy porównano po obu
stronach przed i po kopiowaniu na hosta.

## P9 — redukcja i werdykt

Wejścia w [`matrix/`](matrix/), rozmiary zgodne z zapowiedzianymi co do wiersza:

| Plik | Wiersze | Źródło |
|---|---:|---|
| `matrix/mechanism.tsv` | 108 | zrzuty planu + liczniki P6 |
| `matrix/timing.tsv` | 1440 | sondy P8, przeliczone z `slot.csv` |
| `matrix/gates.tsv` | 21 | `run_gates.py`, P6 |

`reduce_results.py timing` przeliczył każdą komórkę z surowej sondy i porównał
z jej `summary.tsv`: żadnej rozbieżności, żadnego braku, żadnej komórki
nadmiarowej, żadnej zdublowanej, żadnej w złej kolejności bloku.

### Wynik progowy

| Rodzina | Ablacja minimalna | Redukcja / ablacja @`Q=8` | Redukcja / `FLINK_NATURAL` | Cena czasowa, punkt i 95% CI | Rodzina |
|---|---|---:|---:|---|---|
| F9-R2 | `NO_R2_CANON` | 50,000% | 87,500% | 0,9170 [0,9150; 0,9274] | SUPPORT |
| F9-R1 | `NO_R1_FACTOR` | 50,000% | 87,497% | 0,9799 [0,9495; 0,9934] | SUPPORT |
| F9-X | `NO_R1_NO_R2` | 58,333% | 84,374% | 0,7399 [0,7207; 0,7437] | SUPPORT |

Progi zamrożone w `PREDEKLARACJA.md` §7: redukcja **≥ 40%** wobec ablacji
minimalnej **oraz** wobec `FLINK_NATURAL`; górna granica sparowanego bootstrap
95% CI ilorazu `DEFAULT/ablacja` dla `compute_median_ns` **≤ 1,05**. Obie
spełnione w każdej rodzinie.

Praca, raportowana i nieprogowa: redukcja wobec `FLINK_NATURAL` na metryce
rozdzielającej daną rodzinę wynosi 87,504% (F9-R2, `work_costly_evals`),
87,508% (F9-R1, `work_hash_picks`) i 87,511% (F9-X, `work_costly_evals`).

Bramki 21/21 `PASS`, klasyfikacja `clean`; kontrole negatywne czyste;
identyczność wyników publicznych potwierdzona w każdej rodzinie.

### Jakość pomiaru

* `lost_records` w całej macierzy: **0**.
* Żadna komórka nie przekroczyła slotu. Najgorszy udział `p99` to **34,5%**
  (F9-R1, `NO_R1_FACTOR`, `Q=32`, blok 20). Ogon, który w kalibracji dał dwa
  przekroczenia na 11 988 slotów, w macierzy nie wystąpił ani razu.

### Dwa chybione przewidywania punktowe przy `Q=1`

`verdict.py` zaraportował je jako uwagi, nie jako naruszenia progu:

| Rodzina | Redukcja `Q=1` wobec `FLINK_NATURAL` | Wartość predeklarowana |
|---|---:|---:|
| F9-R2 | 100,000% | 0,000% |
| F9-X | −0,011% | −25,000% |

Metryka pierwotna H9 jest zamrożona na `Q=8` i te punkty do niej nie wchodzą,
więc werdykt stoi. Przewidywanie punktowe dla `Q=1` było jednak w obu rodzinach
chybione i nie wolno tego przemilczeć przy transferze do artykułu.

## Granice twierdzenia — nie wygładzać

1. **Wniosek dotyczy automatyzacji współdzielenia materializacji, nie ogólnej
   szybkości.** Zdania „RetractorDB jest szybszy od Flinka", „zawsze zużywa
   mniej pamięci" i „Flink nie potrafi współdzielić" pozostają **nieuprawnione**
   (§10 predeklaracji). Rola Flinka w progu jest bajtowa i strukturalna; czasu
   RetractorDB z czasem JVM nie porównywano.
2. **Wniosek dotyczy klasy `Q=8` i tego korpusu.** `Q=1,2,4` są kontrolą trendu,
   `Q=16,32` pomiarem skalowania — nie dodatkowymi szansami na zaliczenie.
3. **Metryka bajtowa jest niemal binarna.** Przy pełnej deduplikacji spada o
   `1−1/Q`, przy braku mechanizmu o 0%; próg 40% mierzy w praktyce to samo, co
   bramka mechanizmu. Liczbę bajtową podawać jako potwierdzenie mechanizmu,
   nigdy jako nagłówek.
4. **Identyczność `DEFAULT` i `FLINK_MANUAL` jest konstrukcyjna.** `MANUAL`
   zbudowano jako odtworzenie węzłów planu `DEFAULT`; wolno to nazywać wyłącznie
   tak, nigdy jako niezależne potwierdzenie.
5. **Motivational validity pozostaje osią ryzyka.** Konstrukcja broni się przed
   „naturalny Flink sam współdzieli" tym, że rodziny wymuszają monitory
   równoważne, lecz strukturalnie różne. Pytanie „kto pisze to samo obliczenie w
   ośmiu postaciach?" nie zostało rozbrojone — zostało zapisane w predeklaracji
   **przed** wynikami i tak trzeba je cytować.
6. **K26v3 jest powtórzeniem procedury decyzyjnej na naprawionej aparaturze, nie
   niezależną replikacją strony bajtowej.** Korpus i ziarna są te same co w
   K26v2 (`20260809_2601`, `20260809_2602`), bo predeklaracja je zamraża; strona
   planu jest deterministyczna. Świeży jest **pomiar czasu**.
7. **Cena czasowa wyszła poniżej 1 we wszystkich rodzinach**, w F9-X wyraźnie
   (0,7399). Próg tego nie wymagał — wymagał tylko górnej granicy ≤ 1,05 — i nie
   wolno tego uogólniać poza zbadaną klasę zapytań.

## Co ta iteracja dołożyła wobec K26v2

K26v2 przeszła cały pomiar i **nie wydała werdyktu**: procedura decyzyjna
pierwszy raz zetknęła się z prawdziwymi danymi dopiero po 48 h macierzy i
przerwała się na defekcie D6. K26v3 naprawiła D1–D8 i dwa wymagania własne:

* **N9** — pełny `reduce_results.py` + `verdict.py` przećwiczone na danych
  pilota **przed** związaniem kampanii. To jest naprawa, która zdecydowała:
  D6, D7 i D8 zostałyby wykryte w P4 zamiast po macierzy.
* **N10** — wznawialność na poziomie bloku i pętla pod systemd na workerze.
  Sprawdzona bojowo: dwa restarty w łańcuchu, żadnej interwencji z hosta,
  host wyłączalny przez cały pomiar.

Reguły metodyczne, które ta iteracja potwierdziła:

* **Procedurę decyzyjną trzeba przećwiczyć na prawdziwych danych przed
  zamrożeniem**, a nie testować ją samotestem na danych syntetycznych.
* **`RUN_COMPLETE` nie oznacza rodziny zamkniętej** — znacznikiem zamknięcia
  jest plik sumy archiwum. Wznawialność sama tworzyła tę dziurę.
* **Kontrola „plik istnieje" nie wystarcza**: komórka jest zrobiona dopiero,
  gdy `run.rc=0` i `summary.tsv` zgadza się z przeliczoną sondą.

## Ścieżka dowodów

| Artefakt | Miejsce |
|---|---|
| Aparatura, predeklaracja, manifest 438 pozycji | ten katalog, w git |
| Wejścia werdyktu | [`matrix/`](matrix/), w git |
| Bramki P6, kalibracja P7 | `~/k26v3_gates_*`, `~/k26v3_gates.tsv` — poza git |
| Surowe sondy P8 (3 archiwa, 1440 komórek) | `~/k26v3_archives/` — poza git, indeks SHA w git |
| ANEKS-0/ANEKS-1 | `results/` — poza git, sumy powyżej |
| Dokument prowadzący kampanię | `paper-arXiv/debs/plan-K26v3.md` |
