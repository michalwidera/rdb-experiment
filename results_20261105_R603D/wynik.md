# R603D - wynik

Badanie: pomiar potwierdzający drenaż w porcjach (C', `e0857dc8`) wobec drenażu jednym ciągiem (C, `92faf689`) z michalwidera/retractordb#603. Protokół i kryteria w `README.md` (`2f1d3e6`, przed pomiarem), aparatura i test parsera `c39b31d`, suchy przebieg `8b30a0d`, aneksy 1 i 2 zatwierdzone przez człowieka przed analizą (`128f025`).

Kampania 2026-11-06 08:00:53 - ok. 10:32 (ostatni przebieg uruchomiony 10:30:40), pi400, rodziny uc03, uc05, uc06, uc07, uc08, 9 par C / C' w kolejności ABBA, 30 podłączeń na przebieg: razem 90 przebiegów i 2700 podłączeń. Strony: C = binarka R603C bez przebudowy (`xretractor` `3458ed99...`, `xqry` `a7b7dcbd...`, D3), C' = `e0857dc8` + P1 (`xretractor` `e435618b...`, `xqry` `4e8dd234...`). Każdy przebieg był ważny: jeden wątek `SCHED_FIFO` z `VmLck` > 0, governor `performance`, uruchomiona binarka równa zbudowanej, `trace_overrun` = 0 przy buforze 65 536 kB (aneks 2), kod wyjścia silnika 0. Wszystkie 2700 klientów zakończyło się kodem -2 (SIGINT) i zostało zebranych (`reaped` = 1). Log kampanii kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`.

Surowe dane (korpus pod embargiem) poza tym repozytorium, w prywatnym `paper-arXiv`, katalog `rdb-experiment-embargo/R603D/`, w pięciu częściach po rodzinach (*Aparatura*, punkt 6; G5), każda z indeksem 108 plików (18 przebiegów × 6 plików), razem 540 plików i 113 522 472 B:

| część | bajty | SHA-256 | indeks |
|---|---|---|---|
| `results_20261105_R603D_raw_uc03.tar.gz` | 18 869 961 | `aca059ea941897e7cdcdb4a0b47889a326525e16aa292ceeacbf44facc561aaa` | `results_20261105_R603D_raw_uc03.index.tsv` |
| `results_20261105_R603D_raw_uc05.tar.gz` | 37 751 533 | `28f384d83220f4e1c02a5c3034f7a10d77e48a9484cb4b2ff8d0f3cab45e1963` | `results_20261105_R603D_raw_uc05.index.tsv` |
| `results_20261105_R603D_raw_uc06.tar.gz` | 26 722 943 | `e3fe17c839c24b9105ed6fea48ed1f1ab63b93e09ee7cad1f3dc503707e29cf8` | `results_20261105_R603D_raw_uc06.index.tsv` |
| `results_20261105_R603D_raw_uc07.tar.gz` | 15 395 711 | `7c0a351db951777cd581e0a90bda56a58628e66a2a5434b81110dcb480a0a5a6` | `results_20261105_R603D_raw_uc07.index.tsv` |
| `results_20261105_R603D_raw_uc08.tar.gz` | 14 782 324 | `abdf42eb6a24148ea4fadb248154a61aa1216c08eab3a1f25352d99f232a8cb5` | `results_20261105_R603D_raw_uc08.index.tsv` |

Analiza: `analyze.py --raw <raw> --seed 6034`; pełny wydruk niżej, w części *Wydruk analizy*.

## Odpowiedź

**Drenaż w porcjach robi to, co miał zrobić z pojedynczym slotem, ale nie spełnia ani K2a, ani K1'.** Slot obudzony w trakcie porcji liczy dłużej o 5,98 µs (uc05) i 12,00 µs (uc06), wobec 46,46 i 89,59 µs w trakcie drenażu C w tej samej kampanii: u' = 0,13 w obu rodzinach, czyli ~87 % mniej na slot. Obie dolne granice leżą jednak nad progiem δ_c = 5 µs, więc **K2a NIEZDANE w uc05 i uc06**. Seria trwa 36 ms (uc05) i 22 ms (uc06) zamiast 2,4 i 1,6 ms, naraża 2,7 razy więcej slotów, a **łączny koszt na porzucenie (O4) nie spadł**: suma odchyleń narażonych slotów ponad placebo jest w C' wyższa niż w C, w uc03 rozstrzygalnie (C nie trafia tam w żaden slot), w uc05 i uc06 w granicach przedziału. **K1' NIEZDANE w uc03, uc05 i uc06** wyłącznie z warunku gotowości (a): 10 z 726 serii C' bez przepełnień w tych rodzinach nie skończyło się przed startem następnego klienta. Mechanizm puli jest przy tym poprawny (model stanu puli bez naruszeń, wszystkie porzucenia do puli). Przyczyną jest przesłanka przewidywania, która nie zachodzi: seria nie zaczyna się po śmierci klienta, tylko 10 s później, niezależnie od rytmu podłączeń (*Odstępstwa*, punkt 1). K2b ma werdykt nigdzie (kontrola C bez mocy), uc03, uc07 i uc08 są w K2 NIEROZSTRZYGNIĘTE z liczności, a poza seriami nic się nie pogorszyło (K3).

| rodzina | takt | k | K1' C' | seria C' p50 [ms] (P0 C → C') | K2a C' Δ_c [µs] (95 %) | K2a C Δ_c [µs] (95 %) | u' (95 %) | sloty narażone na serię C → C' | O4: suma odchyleń na serię C → C' [µs] | K3 |
|---|---|---|---|---|---|---|---|---|---|---|
| uc03 | 5 ms | 7 | **NIEZDANE** (1 seria niegotowa) | 8,42 (0,785 → 0,311) | +33,70 (+30,72..+38,60), n = 73: **NIEROZSTRZYGNIĘTE** (n < 100) | n = 0 | - | 0 → 0,30 | 0,0 → 14,9; C' - C +14,9 (+11,2..+19,0) | bez regresji |
| uc05 | 1 ms | 31 | **NIEZDANE** (5 serii niegotowych) | 36,25 (2,373 → 0,310) | +5,98 (+5,52..+6,48), n = 1533: **NIEZDANE** | +46,46 (+42,48..+50,85) | 0,13 (0,11..0,15) | 2,4 → 6,5 | 116,6 → 126,6; +10,0 (-28,3..+48,1) | bez regresji |
| uc06 | 2 ms | 19 | **NIEZDANE** (4 serie niegotowe) | 22,37 (1,605 → 0,314) | +12,00 (+11,02..+12,82), n = 797: **NIEZDANE** | +89,59 (+79,92..+95,85) | 0,13 (0,12..0,15) | 1,3 → 3,4 | 412,1 → 966,7; +554,6 (-822,1..+1978,9) | bez regresji |
| uc07 | 20 ms | 1 | **ZDANE** | 1,47 (0,370 → 0,312) | n = 0: **NIEROZSTRZYGNIĘTE** | n = 0 | - | 0 → 0 | 0,0 → 0,0 | bez regresji |
| uc08 | 100 ms | 0 | **ZDANE** | 0,27 (0,269 → 0,273) | n = 0: **NIEROZSTRZYGNIĘTE** | n = 0 | - | 0 → 0 | -1,4 → -1,4 | bez regresji |

- **Ważność miary K2 spełniona.** Kontrola dodatnia C: dolna granica Δ_c 42,48 µs (uc05) i 79,92 µs (uc06), obie > δ_c. Kontrola H0 (syntetyczne serie porcji o fazie i długościach C' na tle C tej kampanii): +0,01 (-0,57..+0,31) µs w uc03, +0,04 (-0,09..+0,19) w uc05, -0,18 (-0,32..+0,06) w uc06, wszystkie w ±1 µs. Strona C powtarza R603C: Δ_c C w uc05 +46,46 wobec +47,26 µs, w uc06 +89,59 wobec +94,07 µs (*Ustalenia*, punkt 4).
- **K2a: porcja wydłuża liczenie slotu ~8 razy mniej niż drenaż C, ale ponad próg.** Pełna porcja trwa p50 75-77 µs, czyli tyle, ile typowy slot uc05 liczy, więc slot narażony nakłada się z nią na znacznej części liczenia (*Przewidywanie*, punkt 3: uc05 +5..+25, uc06 +10..+50 µs; wyszło +5,98 i +12,00). W uc03 slot narażony liczy dłużej o +33,70 µs przy n = 73 (próg liczności 100), czyli werdykt NIEROZSTRZYGNIĘTE z przewidywanego powodu, ale wartość jest bliższa drenażowi B z R603C (+34,99) niż progowi.
- **K2b: bez werdyktu.** Kontrola C w uc05 ma w tej kampanii +2,90 pp (+1,80..+4,20), wobec +3,94 (+2,55..+5,33) na danych R603C, czyli dolną granicę pod δ_m = 2 pp: zgodnie z D1 K2b jest wtedy opisowe. Opisowo: C' uc05 +2,14 pp (+0,06..+4,23), uc06 +0,31 (-0,55..+1,32).
- **O4: rozłożenie drenażu rozprasza koszt, a nie go zmniejsza** (*Przewidywanie*, punkt 5). Seria C' naraża 6,5 slotu w uc05 (C 2,4) i 3,4 w uc06 (C 1,3), zgodnie z symulacją H0 (~6 wobec ~2,5). Mniejsze Δ na slot nie równoważy większej liczby narażonych slotów: średnia suma odchyleń ponad placebo na porzucenie rośnie z 116,6 do 126,6 µs (uc05) i z 412,1 do 966,7 µs (uc06); przedziały różnicy zawierają 0. W uc03 drenaż C (0,79 ms) mieści się w przerwie po slocie i nie trafia w żaden slot, a seria C' (8,4 ms) obejmuje kolejne terminy: +14,9 µs na porzucenie, przedział +11,2..+19,0. Pierwszy człon O4 (liczba slotów narażonych ponad placebo) jest bliski 0 z konstrukcji, bo kopie placebo przesunięte o m · H · takt mają tę samą fazę (*Granice wniosków*).
- **K1': mechanika puli bez zarzutu, warunek gotowości (a) naruszony losowo.** W każdej rodzinie wszystkie porzucenia z `kill` = -ESRCH trafiają do puli (uc06: 266 z 270, 4 wyłączenia martwego muteksu, 1,5 %, w C 4 tak samo), zero niewyjaśnionych par `munmap` + `unlinkat` w fazie pracy (w tym zero zwolnień wpisu niegotowego z `drainPooledStep`), spójność ogona, kontrola dodatnia (≥ 1 przepełnienie w ogonie każdego przebiegu) spełniona, model stanu puli bez naruszeń: żadne podłączenie nie utworzyło kolejki przy gotowym wpisie i żadne nie dostało z puli wpisu niegotowego. Naruszenie (a) dotyczy 1 serii w uc03, 5 w uc05 i 4 w uc06: następny klient wystartował 0,7-22 ms po `kill`, czyli w trakcie serii. W 3 przypadkach (uc03 Cp_07, uc06 Cp_01, Cp_04) klient poprosił o kolejkę dopiero po końcu serii, w 5 dostał z puli drugi, gotowy wpis (seria zakłócona przez `renameat`), w 2 (uc05 Cp_07, uc06 Cp_05) pula nie miała wpisu gotowego i klient dostał kolejkę utworzoną (`openat`, `ftruncate`, `fallocate`, `mmap`), czyli zdarzenie podłączenia #283, które pula miała usuwać. Liczba oczekiwana przy niezależnym starcie serii i podłączeń (270 · długość serii / średni odstęp startów 2,54-2,58 s): 0,9 (uc03), 3,9 (uc05), 2,4 (uc06), 0,2 (uc07), 0,03 (uc08), wobec zaobserwowanych 1, 5, 4, 0, 0. W C ten sam rachunek daje 0,08-0,25 na rodzinę i zaobserwowano 0.
- **O5: serie zakłócone** tylko w uc05 (8) i uc06 (5): wywołania obsługi podłączenia (`renameat` oddania z puli albo budowa kolejki) albo innego porzucenia (`kill`, `munmap`, `unlinkat`) w obrotach P1..Pk. Wyłączone z K2, zgodnie z protokołem. 7 z 13 to serie niegotowe z punktu wyżej.
- **O3: porcje zachowują się jak w suchym przebiegu.** P0 w C' p50 310-314 µs (uc03, uc05, uc06; w C 0,79-2,37 ms), pełna porcja p50 75-77 µs, p99 127-134 µs, ostatnia porcja 30-72 µs zależnie od liczby komunikatów, obrót Pk+1 p50 14 µs, odstęp obrotów w serii p50 1150-1157 µs (stąd seria ~10 % dłuższa niż w *Przewidywaniu*). W uc08 (k = 0) C' to C z kolejką 100: P0 0,273 wobec 0,269 ms. Obrót bezczynny p50 13 µs w obu stronach.
- **K3: bez regresji.** Żadna różnica median C' - C nie jest dodatnia i większa od rozrzutu wewnątrz strony. Najmniejsze p dotyczą różnic ujemnych (C' szybszy): uc06 `wake_lag_ns` p99 i `e2e_ns` p99 -377 i -381 µs (p = 8,2e-05, przy rozrzucie do 479 i 484 µs; ogon tej rodziny to okresowy slot ~48 ms), uc05 `compute_ns` p50 -0,33 µs (p = 0,0056, rozrzut 0,87 µs).
- **O1, O2 bez zmian wobec C.** `futex` wątku slotu w 0,036-0,106 % slotów C', `FUTEX_WAIT` na muteksie kolejki 0-15 na rodzinę, max 43 µs, żadne w oknie. Okno podłączenia z puli p50 0,049-0,050 ms w obu stronach, kolejki utworzonej jak w R603C (uc05 9,9 ms).

## Odstępstwa od protokołu i od przewidywania

1. **Przesłanka przewidywania K1' nie zachodzi.** *Przewidywanie*, punkt 2, zakładało, że seria (najwyżej ~33 ms) kończy się na długo przed następnym podłączeniem, bo to przychodzi 2-3 s po poprzednim. Seria nie startuje jednak po śmierci klienta, tylko po rozpoznaniu porzucenia, które w tej aparaturze następuje 10 s po końcu martwego klienta (9,98-10,00 s we wszystkich 10 przypadkach), czyli w chwili niezwiązanej z rytmem podłączeń. Po 10 s startuje zwykle czwarty z kolejnych klientów (4 odstępy po 2-3 s), więc nałożenie serii na start klienta jest zdarzeniem losowym z prawdopodobieństwem ~ długość serii / odstęp startów. Protokół tego nie przewidział, a warunek (a) ocenia wtedy kolizję czasową, nie działanie puli. Werdykt K1' podano według litery protokołu (NIEZDANE w uc03, uc05, uc06), bez reinterpretacji; czy warunek (a) ma w tej postaci zostać kryterium kolejnych pomiarów, rozstrzyga człowiek (*Skutek*, punkt 3).
2. **Aneksy 1 i 2** (postać operacyjna bramki H, bufor ftrace 65 536 kB), zapisane przed suchym przebiegiem i przed analizą kampanii, zatwierdzone przez człowieka 2026-11-06.
3. **Etykiety wydruku przy n = 0.** W uc07 i uc08 kontrola H0 nie ma ani jednego slotu narażonego, a wydruk podaje „POZA ±1 µs”. To etykieta braku wyniku, nie wynik; werdykt K2a wynika tam z liczności (n = 0) i nie zależy od H0. `analyze.py` nie zmieniono po obejrzeniu danych, żeby wydruk pozostał wydrukiem zatwierdzonej aparatury. Tak samo K3 pisze „w szumie” przy różnicach ujemnych z małym p (uc06): kryterium regresji wymaga różnicy dodatniej.
4. **Przewidywanie wobec wyniku.** K2a: sprawdziło się (NIEZDANE w uc05 i uc06, Δ_c w przewidzianych przedziałach, blisko ich dolnych końców; uc03 NIEROZSTRZYGNIĘTE z n = 73 przy przewidzianym ~80; uc07, uc08 n = 0). K2b: przewidywano NIEROZSTRZYGNIĘTE w uc05, a wyszło opisowe, bo kontrola C straciła w tej kampanii moc (dolna granica 1,80 pp). O4: sprawdziło się (punkt 5: koszt łączny nie spada). K3: sprawdziło się. K1': nie sprawdziło się (punkt 1 wyżej). Długość serii: ~10 % ponad przewidywaniem, bo obrót trwa 1,15 ms, nie 1,07 ms.

## Granice wniosków

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`. Porcja 256 komunikatów (~256 KiB) mieści się tu w L2; na innym procesorze Δ na slot może wyjść inaczej.
- Kolejka jest przy porzuceniu zawsze pełna (rozpoznanie po 10 s), więc k jest tu największe możliwe dla danej pojemności. Tak samo będzie w pracy dla każdego martwego klienta, dopóki rozpoznanie trwa 10 s.
- Liczba naruszeń warunku (a) zależy od rytmu podłączeń aparatury (start co ~2,5 s): przy rzadszych podłączeniach będzie proporcjonalnie mniejsza, przy częstszych większa. Długość serii jest własnością C', a rytm podłączeń - aparatury.
- Δ_c to różnica median, a O4 to średnia sum odchyleń, czuła na długi ogon (uc06: okresowy slot ~48 ms). Dlatego O4 w uc06 ma przedział szerszy niż sama wartość.
- Pierwszy człon O4 (sloty narażone ponad placebo) jest ~0 z konstrukcji: kopia placebo przesunięta o m · H · takt ma tę samą fazę względem terminów, więc naraża tyle samo slotów. Liczbę narażonych slotów na serię podano wprost w tabeli *Odpowiedzi*.
- Ślad nie odróżnia porcji od innej pracy obrotu bez wywołań systemowych; G2 w suchym przebiegu i długości porcji w O3 (pełna porcja dłuższa niż p99,9 obrotu bezczynnego) wskazują, że w niezakłóconych seriach obroty P1..Pk to porcje.

## Skutek dla naprawy (do decyzji człowieka)

C' (już w `master`, `e0857dc8`) zmniejsza wpływ na pojedynczy slot ~8 razy, ale rozkłada drenaż na 8-36 ms i 2,7 razy więcej slotów, więc łączny koszt porzucenia nie spada, a długa seria może zastać podłączenie bez gotowego wpisu w puli. Możliwe kierunki:

1. **Wyrównanie porcji do przerwy po slocie** (alternatywa D2 z planu; *Przewidywanie*, punkt 5 wskazało ją przed pomiarem jako następny krok, jeśli O4 nie spadnie). Porcja ~75 µs mieści się w przerwie po slocie (uc05 p50 ~0,6 ms), więc wyrównana do rozesłania wyniku nie powinna trafiać w liczenie slotu. Celuje w K2a i O4, nie skraca serii, więc warunku (a) nie zmienia.
2. **Wcześniejsze rozpoznanie śmierci klienta** (kierunek 2 z wyniku R603C): przy rozpoznaniu po ~1 s zamiast 10 s kolejka ma ~10 razy mniej komunikatów, więc w uc05 seria to P0 i ~3 porcje (~4 ms), a w C drenaż ~0,24 ms, mniej niż przerwa po slocie. Zmniejsza O4, liczbę naruszeń (a) i ruch pamięci przy przepełnieniach. Koszt: `openat` + `kill` na subskrybenta na sprawdzenie w wątku komunikacyjnym. Δ na slot narażony zostaje takie jak teraz.
3. **Warunek (a) K1'.** Pula działa poprawnie (model stanu bez naruszeń), a skutkiem naruszenia (a) było w 2 z 540 podłączeń C' w uc05 i uc06 utworzenie kolejki zamiast wzięcia z puli. Albo przyjąć to jako koszt C' i w następnych protokołach oceniać gotowość przez warunek (b), albo wymagać, żeby seria nie mogła zastać podłączenia (kierunek 2 zmniejsza prawdopodobieństwo ~10 razy, nie do zera).

Rekomendacja: 1 jako następny wariant mierzony tą samą aparaturą (strona C'' wobec C'), bo został zapisany przed pomiarem jako krok na ten wynik i jako jedyny celuje w to, co K2a i O4 mierzą; 2 jako osobna zmiana do rozważenia niezależnie, bo skraca serię i zmniejsza ruch pamięci przy każdym porzuceniu; w punkcie 3 - ocena przez (b) z raportowaniem (a) opisowo.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603D` (kopia tego katalogu), poza analizą:

1. Korpus uc03, uc05-uc08 jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3) do `/dev/shm/r376/data/<rodzina>`; `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skróty SHA-256 drzew z *Suchy przebieg*, punkt 1 w `README.md`.
2. Binarka C: `~/R376/bin/R603C_C` z R603C (`results_20261105_R603C/wynik.md`, *Odtworzenie od zera*, punkt 2), suma wobec `R603C_C.sha256`. Budowa C': `setsid nohup ./build_ab.sh > ~/R376/build_R603D.log 2>&1 < /dev/null &` (przyrostowo po C, ~22 min).
3. Kampania: `setsid nohup ./campaign.sh > ~/R376/campaign_R603D.log 2>&1 < /dev/null &` (~2,5 h). Przerwana rodzina = powtórzyć całą (ABBA).
4. Analiza na hoście: `rsync -a <worker>:R376/raw_R603D/ <katalog>/raw/` albo pięć części archiwum rozpakowanych do jednego katalogu (`tar xzf <część> -C <katalog>`, sprawdzenie każdej z jej indeksem jak w README `rdb-experiment-embargo`), potem Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --seed 6034` z tego katalogu (importuje `../results_20261105_R603C/analyze.py`). Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `analyze.py ... --out w.txt && sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-06 na archiwum rozpakowanym od nowa (5 indeksów zgodnych, 540 plików, wydruk identyczny); czas analizy ~1,5 min.
5. Serie niegotowe (K1', punkt w *Odpowiedzi*): pole `late` wyniku `analyze_run` (numery podłączeń), a dla każdej z nich `kind`, `reason`, `t_kill`, `end` serii i `start` następnego podłączenia z `conns.tsv`. Liczba oczekiwana: 270 · (p50 serii z O3) / średni odstęp `start_ns` kolejnych podłączeń po 18 przebiegach rodziny.

## Wydruk analizy


Źródło: `raw`, ziarna: placebo 6034, bootstrap 6035, H0 6036, pseudo-zdarzenia 6037.

Kontrola dodatnia C dla ważności K2a (dolna granica Δ_c > δ_c): uc05 42.48 µs, uc06 79.92 µs - spełniona.

Parametry H0 uc03: P0 311.0 µs, porcja 75.0 µs, obrót 1154.0 µs, faza 125..1120 µs, rozrzut 60 µs.

### uc03

Takt slotu: 5.000 ms, H = 8, k = 7 (z pojemności mmap: [7], pojemność [2000]).

| wielkość | C | C' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 243 / 27 / 0 | 243 / 27 / 0 |
| O5: powody zakłóceń | - | - |
| O3: P0 [µs] p50 / p99 / max | 785.0 / 868.0 / 881.0 | 311.0 / 399.0 / 419.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | 116.0 / 560.1 / 1102.7 | 125.0 / 624.5 / 1120.2 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | - / - / - | 75.0 / 127.0 / 556.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | - / - / - | 63.0 / 126.0 / 130.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | - / - / - | 14.0 / 25.0 / 34.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 25.0 / 1415.0 | 13.0 / 22.0 / 431.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | - / - / - | 1154.0 / 1207.0 / 1638.0 |
| O3: seria P0..Pk [ms] p50 / max | 0.785 / 0.881 | 8.421 / 8.865 |
| K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem | 0 slotów (243 serii) | +33.70 µs (+30.72..+38.60); n = 73, serie 73/243 |
| K2b Δ_m [pp] (95 % bootstrap) | 0 slotów (243 serii) | +0.00 pp (+0.00..+0.00); n = 73, serie 73/243 |
| H0 (syntetyczne serie porcji na tle C) K2a / K2b | +0.01 µs (-0.57..+0.31); n = 83, serie 83/242 | +0.00 pp (+0.00..+0.00); n = 83, serie 83/242 |
| opisowo P0: max e2e okna wobec pseudo-zdarzeń | okna 243, trafione 0 | okna 243, trafione 0 |
| opisowo P1..Pk: max e2e okna wobec pseudo-zdarzeń | okna 0, trafione 0 | okna 1701, trafione 137, Δ_e2e -2378.71 µs, MW p = 2.66e-10 |
| O4: sloty narażone na serię ponad placebo (średnia) | 0.00 | -0.00 |
| O4: suma odchyleń na serię ponad placebo [µs] (średnia) | 0.0 | 14.9 |
| kontrola e2e [µs] p50 / p99 / max | 170.1 / 2802.2 / 3409.1 | 169.3 / 2704.0 / 2958.1 |
| kontrola compute [µs] p50 / p99 / max | 127.4 / 2769.7 / 3206.3 | 126.7 / 2641.9 / 2898.3 |
| kontrola wake [µs] p50 / p99 / max | 23.8 / 33.2 / 154.9 | 23.9 / 25.5 / 62.9 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 108 / 140037 (0.077 %) | 103 / 140124 (0.074 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt | 3 / 40.0 / 0 / 0 | 0 / - / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 2.783 | 45 / 2.803 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.049 | 225 / 0.050 |

- **K1'** C': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 1. Werdykt C': **NIEZDANE**.
- K1' C (opisowo, powtórzenie R603C): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C: ZDANE.
- **K2a** (próg δ_c = 5 µs): C' +33.70 µs (+30.72..+38.60); n = 73, serie 73/243. Kontrola H0: +0.01 µs (-0.57..+0.31); n = 83, serie 83/242 - w ±1 µs. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 73 slotów, 73 serii z narażeniem)**. C (opisowo): NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem).
- **K2b** (próg δ_m = 2 pp, werdykt tylko przy mocy kontroli C): C' +0.00 pp (+0.00..+0.00); n = 73, serie 73/243; kontrola C 0 slotów (243 serii) - moc brak. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 73 slotów, 73 serii z narażeniem)**.
- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = nan (95 % bootstrap nan..nan).
- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo -0.00 (-0.02..+0.01), suma odchyleń ponad placebo +14.9 µs (+11.2..+19.0).
- **K3**, compute_ns p50 per przebieg: mediana C' - C = -0.59 µs, rozrzut wewnątrz strony do 2.87 µs, permutacyjny MW p = 0.0528 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C' - C = -0.11 µs, rozrzut wewnątrz strony do 29.98 µs, permutacyjny MW p = 0.489 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C' - C = -61.87 µs, rozrzut wewnątrz strony do 240.38 µs, permutacyjny MW p = 0.222 - w szumie.

Parametry H0 uc05: P0 310.0 µs, porcja 76.0 µs, obrót 1157.0 µs, faza 0..884 µs, rozrzut 60 µs.

### uc05

Takt slotu: 1.000 ms, H = 40, k = 31 (z pojemności mmap: [31], pojemność [8000]).

| wielkość | C | C' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 244 / 26 / 0 | 235 / 27 / 8 |
| O5: powody zakłóceń | - | wywolanie w P1..Pk: fallocate, fstatfs, ftruncate, mmap, openat, unlinkat; wywolanie w P1..Pk: renameat |
| O3: P0 [µs] p50 / p99 / max | 2373.0 / 2529.0 / 2831.0 | 310.0 / 397.0 / 402.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -78.9 / 377.0 / 879.4 | -68.6 / 342.2 / 883.7 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | - / - / - | 76.0 / 134.0 / 772.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | - / - / - | 30.0 / 85.0 / 99.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | - / - / - | 14.0 / 18.0 / 28.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 27.0 / 3368.0 | 13.0 / 30.0 / 3210.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | - / - / - | 1157.0 / 1215.0 / 1857.0 |
| O3: seria P0..Pk [ms] p50 / max | 2.373 / 2.831 | 36.251 / 37.181 |
| K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem | +46.46 µs (+42.48..+50.85); n = 584, serie 244/244 | +5.98 µs (+5.52..+6.48); n = 1533, serie 235/235 |
| K2b Δ_m [pp] (95 % bootstrap) | +2.90 pp (+1.80..+4.20); n = 584, serie 244/244 | +2.14 pp (+0.06..+4.23); n = 1533, serie 235/235 |
| H0 (syntetyczne serie porcji na tle C) K2a / K2b | +0.04 µs (-0.09..+0.19); n = 1541, serie 241/241 | -0.76 pp (-2.02..+0.59); n = 1541, serie 241/241 |
| opisowo P0: max e2e okna wobec pseudo-zdarzeń | okna 244, trafione 244, Δ_e2e 92.10 µs, MW p = 4.59e-33 | okna 235, trafione 89, Δ_e2e 5.66 µs, MW p = 0.0433 |
| opisowo P1..Pk: max e2e okna wobec pseudo-zdarzeń | okna 0, trafione 0 | okna 7285, trafione 1746, Δ_e2e 7.07 µs, MW p = 2.28e-32 |
| O4: sloty narażone na serię ponad placebo (średnia) | -0.03 | 0.01 |
| O4: suma odchyleń na serię ponad placebo [µs] (średnia) | 116.6 | 126.6 |
| kontrola e2e [µs] p50 / p99 / max | 111.4 / 1020.7 / 1471.2 | 111.3 / 1023.5 / 3253.7 |
| kontrola compute [µs] p50 / p99 / max | 63.9 / 965.4 / 1346.3 | 63.6 / 965.1 / 2291.3 |
| kontrola wake [µs] p50 / p99 / max | 23.7 / 76.2 / 532.0 | 23.8 / 91.9 / 2486.3 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 218 / 696588 (0.031 %) | 253 / 700747 (0.036 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt | 10 / 41.0 / 1 / 0 | 15 / 43.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 44 / 9.873 | 45 / 9.891 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 226 / 0.050 | 225 / 0.050 |

- **K1'** C': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 5. Werdykt C': **NIEZDANE**.
- K1' C (opisowo, powtórzenie R603C): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 44 / 226, przepełnienia 26 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C: ZDANE.
- **K2a** (próg δ_c = 5 µs): C' +5.98 µs (+5.52..+6.48); n = 1533, serie 235/235. Kontrola H0: +0.04 µs (-0.09..+0.19); n = 1541, serie 241/241 - w ±1 µs. Werdykt C': **NIEZDANE**. C (opisowo): NIEZDANE.
- **K2b** (próg δ_m = 2 pp, werdykt tylko przy mocy kontroli C): C' +2.14 pp (+0.06..+4.23); n = 1533, serie 235/235; kontrola C +2.90 pp (+1.80..+4.20); n = 584, serie 244/244 - moc brak. Werdykt C': **opisowo (kontrola dodatnia C bez mocy)**.
- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = 0.13 (95 % bootstrap 0.11..0.15).
- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo +0.03 (-0.03..+0.09), suma odchyleń ponad placebo +10.0 µs (-28.3..+48.1).
- **K3**, compute_ns p50 per przebieg: mediana C' - C = -0.33 µs, rozrzut wewnątrz strony do 0.87 µs, permutacyjny MW p = 0.00564 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C' - C = -1.66 µs, rozrzut wewnątrz strony do 164.35 µs, permutacyjny MW p = 0.605 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C' - C = -1.54 µs, rozrzut wewnątrz strony do 119.71 µs, permutacyjny MW p = 0.605 - w szumie.

Parametry H0 uc06: P0 314.0 µs, porcja 77.0 µs, obrót 1157.0 µs, faza 0..1078 µs, rozrzut 60 µs.

### uc06

Takt slotu: 2.000 ms, H = 5, k = 19 (z pojemności mmap: [19], pojemność [5000]).

| wielkość | C | C' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 241 / 25 / 0 | 235 / 26 / 5 |
| O5: powody zakłóceń | - | wywolanie w P1..Pk: fallocate, fstatfs, ftruncate, mmap, openat, unlinkat; wywolanie w P1..Pk: kill, munmap, openat, unlinkat; wywolanie w P1..Pk: renameat |
| O3: P0 [µs] p50 / p99 / max | 1605.0 / 1729.0 / 1755.0 | 314.0 / 390.0 / 396.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -6448.8 / 562.4 / 1092.4 | -6653.2 / 613.6 / 1078.0 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | - / - / - | 77.0 / 132.0 / 1347.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | - / - / - | 49.0 / 98.0 / 109.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | - / - / - | 14.0 / 18.0 / 20.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 25.0 / 1528.0 | 13.0 / 25.0 / 690.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | - / - / - | 1157.0 / 1212.0 / 2434.0 |
| O3: seria P0..Pk [ms] p50 / max | 1.605 / 1.755 | 22.365 / 23.739 |
| K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem | +89.59 µs (+79.92..+95.85); n = 317, serie 226/241 | +12.00 µs (+11.02..+12.82); n = 797, serie 233/235 |
| K2b Δ_m [pp] (95 % bootstrap) | +0.45 pp (-1.04..+2.25); n = 317, serie 226/241 | +0.31 pp (-0.55..+1.32); n = 797, serie 233/235 |
| H0 (syntetyczne serie porcji na tle C) K2a / K2b | -0.18 µs (-0.32..+0.06); n = 924, serie 231/233 | +0.12 pp (-0.66..+0.95); n = 924, serie 231/233 |
| opisowo P0: max e2e okna wobec pseudo-zdarzeń | okna 241, trafione 232, Δ_e2e 155.95 µs, MW p = 3.77e-44 | okna 235, trafione 18, Δ_e2e 42305.39 µs, MW p = 0.117 |
| opisowo P1..Pk: max e2e okna wobec pseudo-zdarzeń | okna 0, trafione 0 | okna 4465, trafione 1110, Δ_e2e -45596.22 µs, MW p = 1 |
| O4: sloty narażone na serię ponad placebo (średnia) | 0.60 | 0.75 |
| O4: suma odchyleń na serię ponad placebo [µs] (średnia) | 412.1 | 966.7 |
| kontrola e2e [µs] p50 / p99 / max | 285.2 / 45066.7 / 47003.2 | 284.2 / 44698.0 / 46707.0 |
| kontrola compute [µs] p50 / p99 / max | 224.5 / 353.2 / 46911.8 | 224.2 / 350.9 / 46624.4 |
| kontrola wake [µs] p50 / p99 / max | 23.9 / 43110.7 / 45079.2 | 23.9 / 42743.8 / 44780.8 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 365 / 351581 (0.104 %) | 370 / 349831 (0.106 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt | 3 / 37.0 / 0 / 0 | 6 / 42.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 47 / 6.334 | 48 / 6.343 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 223 / 0.050 | 222 / 0.050 |

- **K1'** C': do puli 266 z 270 (wyłączenia 4: martwy muteks 4, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 48 / 222, przepełnienia 26 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 4. Werdykt C': **NIEZDANE**.
- K1' C (opisowo, powtórzenie R603C): do puli 266 z 270 (wyłączenia 4: martwy muteks 4, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 47 / 223, przepełnienia 25 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C: ZDANE.
- **K2a** (próg δ_c = 5 µs): C' +12.00 µs (+11.02..+12.82); n = 797, serie 233/235. Kontrola H0: -0.18 µs (-0.32..+0.06); n = 924, serie 231/233 - w ±1 µs. Werdykt C': **NIEZDANE**. C (opisowo): NIEZDANE.
- **K2b** (próg δ_m = 2 pp, werdykt tylko przy mocy kontroli C): C' +0.31 pp (-0.55..+1.32); n = 797, serie 233/235; kontrola C +0.45 pp (-1.04..+2.25); n = 317, serie 226/241 - moc brak. Werdykt C': **opisowo (kontrola dodatnia C bez mocy)**.
- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = 0.13 (95 % bootstrap 0.12..0.15).
- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo +0.15 (-0.12..+0.41), suma odchyleń ponad placebo +554.6 µs (-822.1..+1978.9).
- **K3**, compute_ns p50 per przebieg: mediana C' - C = -0.15 µs, rozrzut wewnątrz strony do 3.02 µs, permutacyjny MW p = 0.546 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C' - C = -376.65 µs, rozrzut wewnątrz strony do 479.37 µs, permutacyjny MW p = 8.23e-05 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C' - C = -381.22 µs, rozrzut wewnątrz strony do 484.45 µs, permutacyjny MW p = 8.23e-05 - w szumie.

Parametry H0 uc07: P0 312.0 µs, porcja 72.0 µs, obrót 1150.0 µs, faza 115..1108 µs, rozrzut 60 µs.

### uc07

Takt slotu: 20.000 ms, H = 10, k = 1 (z pojemności mmap: [1], pojemność [500]).

| wielkość | C | C' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 243 / 27 / 0 | 243 / 27 / 0 |
| O5: powody zakłóceń | - | - |
| O3: P0 [µs] p50 / p99 / max | 370.0 / 456.0 / 477.0 | 312.0 / 395.0 / 408.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | 96.9 / 594.3 / 1113.7 | 114.9 / 585.2 / 1108.2 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | - / - / - | - / - / - |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | - / - / - | 72.0 / 137.0 / 145.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | - / - / - | 14.0 / 17.0 / 18.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 16.0 / 318.0 | 13.0 / 16.0 / 236.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | - / - / - | 1150.0 / 1223.0 / 1234.0 |
| O3: seria P0..Pk [ms] p50 / max | 0.370 / 0.477 | 1.473 / 1.586 |
| K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem | 0 slotów (243 serii) | 0 slotów (243 serii) |
| K2b Δ_m [pp] (95 % bootstrap) | 0 slotów (243 serii) | 0 slotów (243 serii) |
| H0 (syntetyczne serie porcji na tle C) K2a / K2b | 0 slotów (243 serii) | 0 slotów (243 serii) |
| opisowo P0: max e2e okna wobec pseudo-zdarzeń | okna 243, trafione 0 | okna 243, trafione 0 |
| opisowo P1..Pk: max e2e okna wobec pseudo-zdarzeń | okna 0, trafione 0 | okna 243, trafione 0 |
| O4: sloty narażone na serię ponad placebo (średnia) | 0.00 | 0.00 |
| O4: suma odchyleń na serię ponad placebo [µs] (średnia) | 0.0 | 0.0 |
| kontrola e2e [µs] p50 / p99 / max | 106.9 / 2067.7 / 2525.8 | 107.9 / 2065.4 / 2412.9 |
| kontrola compute [µs] p50 / p99 / max | 63.8 / 2009.6 / 2411.2 | 64.4 / 2007.9 / 2328.4 |
| kontrola wake [µs] p50 / p99 / max | 23.8 / 26.0 / 31.0 | 23.8 / 26.0 / 32.4 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 23 / 34906 (0.066 %) | 21 / 35095 (0.060 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt | 0 / - / 0 / 0 | 0 / - / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 0.994 | 45 / 0.988 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 225 / 0.049 |

- **K1'** C': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C': **ZDANE**.
- K1' C (opisowo, powtórzenie R603C): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C: ZDANE.
- **K2a** (próg δ_c = 5 µs): C' 0 slotów (243 serii). Kontrola H0: 0 slotów (243 serii) - POZA ±1 µs. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem)**. C (opisowo): NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem).
- **K2b** (próg δ_m = 2 pp, werdykt tylko przy mocy kontroli C): C' 0 slotów (243 serii); kontrola C 0 slotów (243 serii) - moc brak. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem)**.
- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = nan (95 % bootstrap nan..nan).
- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo +0.00 (+0.00..+0.00), suma odchyleń ponad placebo +0.0 µs (+0.0..+0.0).
- **K3**, compute_ns p50 per przebieg: mediana C' - C = 0.20 µs, rozrzut wewnątrz strony do 2.57 µs, permutacyjny MW p = 0.0728 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C' - C = -0.15 µs, rozrzut wewnątrz strony do 1.85 µs, permutacyjny MW p = 0.666 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C' - C = -3.36 µs, rozrzut wewnątrz strony do 34.15 µs, permutacyjny MW p = 0.436 - w szumie.

Parametry H0 uc08: P0 273.0 µs, porcja 75.0 µs, obrót 1070.0 µs, faza 138..1095 µs, rozrzut 60 µs.

### uc08

Takt slotu: 100.000 ms, H = 12, k = 0 (z pojemności mmap: [0], pojemność [100]).

| wielkość | C | C' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 243 / 27 / 0 | 243 / 27 / 0 |
| O5: powody zakłóceń | - | - |
| O3: P0 [µs] p50 / p99 / max | 269.0 / 354.0 / 362.0 | 273.0 / 384.0 / 1140.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | 112.2 / 651.5 / 1116.3 | 137.6 / 621.3 / 1095.4 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | - / - / - | - / - / - |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | - / - / - | - / - / - |
| O3: obrót Pk+1 [µs] p50 / p99 / max | - / - / - | - / - / - |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 16.0 / 3353.0 | 13.0 / 16.0 / 166.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | - / - / - | - / - / - |
| O3: seria P0..Pk [ms] p50 / max | 0.269 / 0.362 | 0.273 / 1.140 |
| K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem | 0 slotów (243 serii) | 0 slotów (243 serii) |
| K2b Δ_m [pp] (95 % bootstrap) | 0 slotów (243 serii) | 0 slotów (243 serii) |
| H0 (syntetyczne serie porcji na tle C) K2a / K2b | 0 slotów (243 serii) | 0 slotów (243 serii) |
| opisowo P0: max e2e okna wobec pseudo-zdarzeń | okna 243, trafione 0 | okna 243, trafione 0 |
| opisowo P1..Pk: max e2e okna wobec pseudo-zdarzeń | okna 0, trafione 0 | okna 0, trafione 0 |
| O4: sloty narażone na serię ponad placebo (średnia) | -0.03 | -0.03 |
| O4: suma odchyleń na serię ponad placebo [µs] (średnia) | -1.4 | -1.4 |
| kontrola e2e [µs] p50 / p99 / max | 315.1 / 1233.1 / 1408.9 | 315.4 / 1235.0 / 1434.3 |
| kontrola compute [µs] p50 / p99 / max | 264.2 / 1165.4 / 1302.1 | 264.2 / 1165.2 / 1342.9 |
| kontrola wake [µs] p50 / p99 / max | 24.4 / 27.9 / 42.6 | 24.5 / 27.6 / 30.6 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 3 / 8499 (0.035 %) | 6 / 8571 (0.070 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt | 0 / - / 0 / 0 | 0 / - / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 0.493 | 45 / 0.475 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 225 / 0.050 |

- **K1'** C': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C': **ZDANE**.
- K1' C (opisowo, powtórzenie R603C): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C: ZDANE.
- **K2a** (próg δ_c = 5 µs): C' 0 slotów (243 serii). Kontrola H0: 0 slotów (243 serii) - POZA ±1 µs. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem)**. C (opisowo): NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem).
- **K2b** (próg δ_m = 2 pp, werdykt tylko przy mocy kontroli C): C' 0 slotów (243 serii); kontrola C 0 slotów (243 serii) - moc brak. Werdykt C': **NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem)**.
- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = nan (95 % bootstrap nan..nan).
- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo +0.00 (-0.00..+0.01), suma odchyleń ponad placebo +0.1 µs (-0.8..+0.9).
- **K3**, compute_ns p50 per przebieg: mediana C' - C = 0.39 µs, rozrzut wewnątrz strony do 4.96 µs, permutacyjny MW p = 0.931 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C' - C = -0.27 µs, rozrzut wewnątrz strony do 2.45 µs, permutacyjny MW p = 0.489 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C' - C = 2.36 µs, rozrzut wewnątrz strony do 32.29 µs, permutacyjny MW p = 0.73 - w szumie.

### Werdykty

| rodzina | K1' C' | K2a C' | K2b C' | K2a C (opisowo) |
|---|---|---|---|---|
| uc03 | NIEZDANE | NIEROZSTRZYGNIĘTE (n = 73 slotów, 73 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 73 slotów, 73 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) |
| uc05 | NIEZDANE | NIEZDANE | opisowo (kontrola dodatnia C bez mocy) | NIEZDANE |
| uc06 | NIEZDANE | NIEZDANE | opisowo (kontrola dodatnia C bez mocy) | NIEZDANE |
| uc07 | ZDANE | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) |
| uc08 | ZDANE | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) | NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem) |
