# R603 część I - wynik mikrotestu (pi400, 2026-11-05)

Protokół i kryteria: `../README.md`, sekcja *Część I* (commit `fab5036`, wypchnięty przed uruchomieniem). Źródło `tlb_microtest.c` (SHA-256 `421eabd3...`, ta sama suma na workerze i na hoście), binarka `~/R603/microtest/tlb_microtest` (`gcc -O2 -Wall -Wextra -pthread`, `setcap cap_perfmon,cap_sys_nice,cap_ipc_lock=ep`), governor `performance`. Przebiegi 2026-11-05 08:10-08:12 (`raw/micro.log`). Surowe CSV w `raw/`; mikrotest nie używa korpusu, więc dane są tu w całości.

Odtworzenie analizy (surowe CSV jako `raw/*.csv.gz`, sumy w `raw/SHA256SUMS`): `python3 analyze_microtest.py raw/m1 raw/m2 raw/m3` (NumPy) daje `raw/analysis.txt`; eksploracja: `python3 explore_microtest.py raw/m1 raw/m2` daje `raw/exploration.txt`.

Ważność: 3 z 3 przebiegów ważne (żaden slot multipleksowany), po 80 zdarzeń (40 `whole`, 40 `chunk`), ~35 300 slotów, ~13 600 kontrolnych.

## Wyniki kryteriów (wartości z `raw/analysis.txt`)

Nadwyżka Δ = mediana zdarzeń - mediana pseudo-zdarzeń; zdarzenie = max miary po slotach dotkniętych oknem (z pierwszym slotem po oknie); liczniki = odcinek pobudki + pracy.

| przebieg, tryb | Δ `l1d_tlb_refill` (p) | Δ `work_ns` (p) | Δ `e2e_ns` | Δ `l1i_tlb_refill` | Δ `l2d_cache` | Δ `l2d_cache_refill` |
|---|---|---|---|---|---|---|
| m1 (16 stron) `whole` | 3 (1,7e-05) | 962 ns | 3636 ns | 14 | 216 | 32 |
| m1 (16 stron) `chunk` 1 MiB | 2 | 796 ns | 2734 ns | 2 | 18 | 17 |
| m2 (512 stron) `whole` | -9 | 1064 ns (4,2e-18) | 3084 ns | 13 | 1132 | 56 |
| m2 (512 stron) `chunk` 1 MiB | -6 | 1565 ns (2,7e-15) | 2652 ns | 1 | -10 | 28 |
| m3 (16 stron) `whole` | 1 (0,30) | 1204 ns | 3538 ns | 16 | 207 | 30 |
| m3 (16 stron) `chunk` 2 MiB | 0 | 778 ns | 2378 ns | 4 | 44 | 18 |

- **M1 - NIEZDANE** według brzmienia kryterium: w m1 `whole` Δ `l1d_tlb_refill` = 3 < 8, mimo p = 1,7e-05.
- **M2 - NIEZDANE**: m2 `whole` Δ `work_ns` = +1064 ns przy p = 4,2e-18 (pierwsza część zdana), ale m2 `chunk` Δ `work_ns` = +1565 ns, więcej niż 50 % (i więcej niż 100 %) wartości `whole`. Według brzmienia protokołu jest to wskazanie H-c.
- **M3 - NIEZDANE**: m3 `whole` Δ `l1d_tlb_refill` = 1 (p = 0,30), m3 `chunk` 2 MiB = 0; kryterium „≥ 50 % wartości `whole`” przy wartości `whole` równej 1 nic nie mierzy.

## Dlaczego M1 i M3 nie mierzą tego, co miały mierzyć (błąd przesłanki, nie wynik o H-a)

Kryterium M1 zakładało, że przy 16 stronach tło `l1d_tlb_refill` jest bliskie 0, a unieważnienie ASID doda ~16. Tło wynosi jednak **~296 uzupełnień na slot** (mediana pseudo-zdarzeń m1). Licznik obejmuje jądro: powrót z `clock_nanosleep`, przerwanie zegara, dwa odczyty `read()` grupy PMU, a przy KPTI także przełączanie tablic stron. 16 stron użytkownika to ułamek tego, co slot dotyka. Test sprawdzający w kroku 2 (`pmu_probe.c`) mierzył 100 przebiegów pętli między odczytami, więc koszt jądra rozkładał się tam na 100 i nie było go widać. Przesłanka M1 była więc fałszywa, a z nią wniosek protokołu „H-a odrzucona na poziomie sprzętu i jądra”. M3 dziedziczy tę samą miarę.

**Werdykt protokołu zostaje zapisany taki, jaki jest (M1, M2 i M3 niezdane).** To, że przesłanka M1 była fałszywa, jest ustaleniem, a nie zmianą kryterium. O tym, czy przyjąć aneks zastępujący miarę M1, decyduje człowiek (zob. *Do decyzji*).

## Co mikrotest pokazuje (opisowo: miary raportowane w protokole jako opisowe, oraz eksploracja)

**1. Sygnatura unieważnienia TLB istnieje i znika przy kawałkach 1 MiB.** Miary opisowe z tabeli powyżej:
- w `whole` Δ `l1i_tlb_refill` = +13..16 i Δ `l2d_cache` = +207..1132 (p ≤ 1e-26 we wszystkich trzech przebiegach);
- w `chunk` 1 MiB Δ `l1i_tlb_refill` = +1..2 i Δ `l2d_cache` = -10..18.

Dostępy do L2 bez wzrostu chybień L1D (`l1d_cache_refill` Δ ≈ 0) to obraz przejść tablic stron: walker A72 czyta deskryptory przez L2. W m2 (512 stron) przybywa ~1000 dostępów, czyli ~2 na stronę zbioru roboczego. Wzrost `l1i_tlb_refill` o ~14 (kod jądra i programu) wskazuje, że unieważnienie zabiera też wpisy instrukcji, zgodnie z `TLBI ASIDE1IS` i KPTI.

**2. Większość nadwyżki czasu NIE pochodzi z unieważnienia TLB.** Δ `e2e_ns` w `chunk` 1 MiB to 75 % (m1) i 86 % (m2) wartości `whole`. W m3 kawałki 2 MiB dają 67 %.

**3. Eksploracja po odczytaniu wyniku** (`explore_microtest.py`, jednostka = pojedynczy slot, nadwyżka mediany wobec slotów kontrolnych; nie jest częścią kryteriów). Okno zwolnienia rozdzielono na fazę `munmap` (p50 ~2,8-3,0 ms) i fazę `shm_unlink` (p50 ~3,1 ms):

| m1, nadwyżka mediany | `whole` / munmap | `whole` / unlink | `chunk` / munmap | `chunk` / unlink |
|---|---|---|---|---|
| `wake_lag_ns` | +2070 | +1088 | +1425 | +1134 |
| `work_ns` | +667 | +389 | +361 | +352 |
| `wake_l1i_tlb_refill` | +15 | +2 | +2 | +2 |
| `wake_l2d_cache` | +152 | -3 | -16 | -17 |
| `wake_l2d_cache_refill` | +12 | +7 | +4 | +7 |
| `work_l2d_cache_refill` | +6 | +4 | +3 | +3 |

- Sygnatura TLB (`l1i_tlb_refill`, `l2d_cache` w odcinku pobudki) występuje **tylko w fazie `munmap` trybu `whole`**. Jej koszt to różnica między `whole` a `chunk` w fazie `munmap`: ~0,6 µs `wake_lag_ns` i ~0,3 µs `work_ns` (m1).
- **We wszystkich czterech komórkach zostaje +1,1..1,4 µs `wake_lag_ns` i +0,35 µs `work_ns`, także w fazie `shm_unlink`**, w której nie ma żadnego `munmap`. Ta wspólna część niesie kilka dodatkowych chybień L2 (`l2d_cache_refill` +3..8 na odcinek), bez sygnatury TLB.
- W m2 (512 stron) zbiór roboczy dodaje +992 dostępów L2 w fazie `munmap` `whole` (przejścia tablic), ale tylko ~+0,65 µs `work_ns`. Tablice stron zostają w L2, więc przejście jest tanie. Nadwyżka `work_l2d_cache_refill` +22..41 występuje w obu trybach i w obu fazach.
- Nadwyżka `wake_lag_ns` ~2 µs w fazie `munmap` `whole` jest tego samego rzędu co +3 µs `wake_lag_ns` p50 w R600 (uc03, uc05, uc06). Mikrotest odtwarza więc tę część obserwacji R600 bez silnika.

**Interpretacja (hipoteza po eksploracji, niesprawdzona kryterium):**
- Na tym sprzęcie unieważnienie ASID przy `munmap` ≥ 2 MiB działa (H-a jako mechanizm istnieje). Odpowiada jednak tylko za ~25-30 % nadwyżki czasu slotu w mikroteście.
- Reszta towarzyszy zarówno `munmap`, jak i `shm_unlink` i wiąże się z niewielką liczbą dodatkowych chybień L2. Pasuje to do H-b w szerszej postaci: wspólna hierarchia pamięci (L2 1 MiB i magistrala DRAM) obciążona przez zwalnianie 2048 stron. Liczba chybień (+3..8 w pobudce) jest mała jak na +1 µs, więc możliwy jest też wzrost opóźnienia każdego chybienia przy zajętej magistrali, którego liczniki zdarzeń nie pokazują.
- Wskazanie H-c z M2 (`work_ns` `chunk` > `whole` w m2) nie ma odpowiednika w licznikach ani w `e2e_ns`, które w `chunk` jest mniejsze niż w `whole`. Rozstrzygnąć je może dopiero część II.

**Otwarte pytanie (M3):** kawałki 2 MiB usunęły sygnaturę w większości (Δ `l2d_cache` 44 wobec 207), wbrew przewidywaniu. Możliwe wyjaśnienie, nie sprawdzone: mapowanie segmentu nie jest wyrównane do 2 MiB. Każdy kawałek 2 MiB obejmuje wtedy dwie tablice PTE, a jądro przy brudnych stronach współdzielonych opróżnia TLB po każdej tablicy (`force_flush` w `zap_pte_range`), zakresami poniżej progu. Do sprawdzenia: adres mapowania w mikroteście i źródło `mm/memory.c` jądra 6.8.

## Skutek dla części II

- Kryteria C0-C4 nie opierają się na M1-M3, więc kampania jest nadal rozstrzygająca: B' usuwa część TLB, a C4 mierzy jej udział w silniku. Silnik ma większy zbiór roboczy i wielokrotnie większą resztkę (R600: Δ `e2e_ns` 30-43 µs wobec 3-4 µs w mikroteście), więc jej skład może być inny.
- Przewidywanie wynikające z mikrotestu (zapisane przed kampanią): u_a znacznie poniżej 1, C2 raczej „niewsparta” (Δ_e2e(B') > 0,5 · Δ_e2e(B)), resztka po B' istnieje (C3).
- Miara T w C2 (`l1d_tlb_refill` + `l1i_tlb_refill`) ma tę samą wadę co M1: tło jądra w `l1d_tlb_refill`. W C2 decyduje warunek na `e2e`, a T rozstrzyga tylko o rodzaju wsparcia („wsparta” albo „tylko interwencyjnie”), więc wada nie zmienia werdyktu „niewsparta”. Opisowo raportuje się też `l1i_tlb_refill` i `l2d_cache` w odcinku pobudki, które w mikroteście niosą sygnaturę.

## Do decyzji

1. Czy przyjąć aneks do M1/M3: sygnatura TLB = Δ `wake_l1i_tlb_refill` i Δ `wake_l2d_cache` zamiast Δ `l1d_tlb_refill`. Werdykt według aneksu musiałby być oznaczony jako ustalony po zobaczeniu danych.
2. Czy w części II zmienić T na `wake_l1i_tlb_refill` + `wake_l2d_cache` przed kampanią. To byłaby zmiana kryterium przed pomiarem kampanii, ale po zobaczeniu mikrotestu, więc trzeba ją zapisać jako aneks z datą i powodem.
