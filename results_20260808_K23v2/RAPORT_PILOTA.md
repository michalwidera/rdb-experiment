# Raport pilota — ITERACJA 2, z przebiegiem runtime (faza P4′) — K23 / H9

**Data:** 2026-08-08. **Werdykt: GO.** Wszystkie trzy rodziny **wykonują się** na
naprawionym silniku, liczby mechanizmu compile-only są **bajtowo identyczne**
z iteracją 1, a zmierzone redukcje metryki pierwotnej odtwarzają wartości
predeklarowane co do dziesiątej części punktu procentowego.

Ten raport **nie zastępuje** `results_20260808_K23/RAPORT_PILOTA.md`, tylko go
powtarza na innym SHA i dokłada to, czego tamten nie miał. Tamten zostaje
nietknięty jako zapis tego, co było wiadomo przed unieważnieniem.

---

## 0. Po co jest drugi pilot

Iteracja 1 padła w P6 na pierwszym przebiegu runtime — czynności, której cała
kampania do tamtej chwili ani razu nie wykonała. Pilot P4 był **compile-only**,
a `xretractor -c` nie woła ewaluatora, więc korpus, w którym 14 z 21 planów nie
dawało się wykonać, przeszedł bramkę bez jednego ostrzeżenia.

Wniosek nie brzmi „powtórzyć pilota na nowym SHA". Brzmi: **bramka pilota pytała
o kompilację, a odpowiedzi wymagało wykonanie.** Iteracja 2 różni się od iteracji 1
przypięciem SHA i **tą jedną bramką** — reszta aparatury jest przeniesiona bez
zmian merytorycznych (`ITERACJA-1-UNIEWAZNIONA.md`, tabela „co przechodzi dalej").

---

## 1. Aparatura

| Pozycja | Wartość |
|---|---|
| SHA kodu | `ebd8aab826dc471c94c8dc2720af29a31718dbbc`, drzewo czyste |
| `ctest` na tym SHA | **186/186 w Debug i 186/186 w Release**, przebiegnięte w tej sesji |
| Profile | `build_profiles.sh`, `--build-info` zweryfikowane bajtowo dla każdego |
| `xretractor` DEFAULT | `880d5a5f3dd1a327…` |
| `xretractor` NO_R2_CANON | `0f050c4dd85e9cdd…` |
| `xretractor` NO_R1_FACTOR | `465d6ea721059590…` |
| `xretractor` NO_R1_NO_R2 | `5e88a80016e30d2b…` |
| Polecenie compile-only | `RDB_BENCH_PLAN=1 <binarka> <plan>.rql -c` |
| Polecenie runtime | `RDB_BENCH_LOGICAL=1 RDB_BENCH_WORK=1 <binarka> <plan>.rql -m 100 -r -k` |
| Macierz | 4 profile × 6 planów = **24 kompilacje** i **24 przebiegi**, wszystkie rc=0 |
| Dane | `pilot/src_{a,b,c,d}.txt` (120 rekordów), `src_{p,q}.txt` — miniaturowe |
| Surowe wyjście | `pilot/out/` (compile-only), `pilot/out_rt/` (runtime), `pilot/neg/` (wersja obalona) |
| Odtworzenie | `pilot/run_pilot.sh`, `pilot/run_pilot_runtime.sh`, `mechanism_table.py` |

**Czym ten pilot nadal nie jest.** Nie jest pomiarem kosztowym: dane są
miniaturowe, nie główne; nie mierzono czasu; nie dobierano progu ani rate'u;
nie uruchomiono strony Flinka. Progi (40%, 1,05, reguła 2/3) są przeniesione
z iteracji 1 **bez dotknięcia** i nie były przedmiotem żadnej decyzji po
zobaczeniu liczb poniżej.

---

## 2. Bramka runtime pokazana NAJPIERW na wersji obalonej

Reguła tego łuku brzmi: bramka, która nie umie odrzucić wersji obalonej, nie jest
bramką. Wersją obaloną jest tu **korpus, który się kompiluje i nie wykonuje** —
dokładnie stan, w którym iteracja 1 dotarła do P6.

Odtworzenie jest legalne i nie wymaga cofania naprawy: `Abs` **jest w gramatyce**
(`RQL.g4`) i **nie ma implementacji w ewaluatorze**, więc plan z `Abs` idzie tą
samą ścieżką, którą przed `ebd8aab` szedł `Sqrt`.

```
$ xretractor F9_R2_Q8_abs.rql -c                     # DEFAULT, ebd8aab
rc = 0                                               # ← tyle widział pilot iteracji 1
$ xretractor F9_R2_Q8_abs.rql -m 100 -r -k
IPC Fail.
Unsupported function call: Abs
rc = 4
```

Przypadek przechodzi przez **tę samą funkcję asercji** co komórki macierzy
(`assert_cell` w `run_pilot_runtime.sh`) i zostaje **odrzucony**:

```
ok  wersja obalona KOMPILUJE sie z rc=0 (tyle widzial pilot iteracji 1)
ok  wersja obalona ODRZUCONA przez te sama asercje:
    kod wyjscia 4 — plan sie NIE WYKONAL (compile-only by tego nie zobaczyl)
```

Gdyby przypadek negatywny przeszedł, skrypt kończy się błędem **przed** policzeniem
czegokolwiek innego. Zapis przypadku (`pilot/neg/`) wchodzi do manifestu razem
z dowodami strony zdanej — inaczej w katalogu zostałaby sama strona, która się udała.

**Co dokładnie sprawdza asercja komórki.** Cztery warunki, z których żadnego nie da
się spełnić kompilacją: kod wyjścia 0; obecny wiersz `LOGICAL`; **niezerowy
mianownik** (publiczne dopisania > 0 — plan, który nie wypisał ani jednego rekordu
publicznego, nie policzył się, choćby wrócił zerem); obecny wiersz `WORK`. Warunek
na substrat jest osobny i dotyczy wyłącznie planów rodzin — kontrole negatywne mają
prawo nie materializować niczego i to jest ich **oczekiwany** wynik.

---

## 3. Compile-only: liczby mechanizmu bez jednej zmiany

`RAPORT_PILOTA.md` §2 iteracji 1 pozostaje w mocy **dowiedziony, nie założony**:
24 zrzuty `.plan` są **bajtowo identyczne** ze zrzutami iteracji 1; pliki `.probe`
różnią się wyłącznie wierszem `COMPILE_NS` (czas kompilacji, wielkość z natury
zmienna). Naprawa siedzi w ewaluatorze, nie w przejściu kompilatora — i to
przewidywanie z `ITERACJA-1-UNIEWAZNIONA.md` zostało teraz sprawdzone.

| Rodzina | Profil | `r1` | `r2` | `STREAM_SELECT_*` | substraty | jednostki |
|---|---|---|---|---|---|---|
| **F9-R2** | `DEFAULT` | 0 | **4** | **1** | 1 | 0,667 |
| | `NO_R2_CANON` | 0 | 0 | 2 | 2 | 1,333 |
| | `NO_R1_FACTOR` | 0 | 4 | 1 | 1 | 0,667 |
| | `NO_R1_NO_R2` | 0 | 0 | 2 | 2 | 1,333 |
| **F9-R1** | `DEFAULT` | **4** | 0 | 0 | **1** | 1,000 |
| | `NO_R2_CANON` | 4 | 0 | 0 | 1 | 1,000 |
| | `NO_R1_FACTOR` | 0 | 0 | 0 | 3 | 2,000 |
| | `NO_R1_NO_R2` | 0 | 0 | 0 | 3 | 2,000 |
| **F9-X** | `DEFAULT` | 2 | 4 | **1** | 5 | **5,000** |
| | `NO_R2_CANON` | 2 | 0 | 2 | 6 | 6,000 |
| | `NO_R1_FACTOR` | 0 | 4 | 2 | 12 | 10,000 |
| | `NO_R1_NO_R2` | 0 | 0 | 4 | 14 | 12,000 |

Diagnostyka poza macierzą (`diag_X_named`, tylko `DEFAULT`): `r1=2`, `r2=1`,
`STREAM_SELECT_* = 0` — również bez zmiany wobec iteracji 1, więc wniosek §3.4
predeklaracji (nazwanie pośrednich kasuje warstwę R2) stoi na tym samym materiale.

---

## 4. Runtime: metryka pierwotna zmierzona, nie wyprowadzona

To jest część, której iteracja 1 nie miała. Licznik `LOGICAL` czytany po pełnym
przebiegu 100 slotów, metryka = **kanoniczne bajty substratów na jeden publiczny
rekord wyjściowy**.

| Rodzina | Profil | bajty substratów | publiczne rekordy | **B / rekord** |
|---|---|---|---|---|
| **F9-R2** | `DEFAULT` | 891 | 792 | **1,1250** |
| | `NO_R2_CANON` | 1782 | 792 | 2,2500 |
| | `NO_R1_FACTOR` | 891 | 792 | 1,1250 |
| | `NO_R1_NO_R2` | 1782 | 792 | 2,2500 |
| **F9-R1** | `DEFAULT` | 648 | 568 | **1,1408** |
| | `NO_R2_CANON` | 648 | 568 | 1,1408 |
| | `NO_R1_FACTOR` | 1278 | 560 | 2,2821 |
| | `NO_R1_NO_R2` | 1278 | 560 | 2,2821 |
| **F9-X** | `DEFAULT` | 3213 | 568 | **5,6567** |
| | `NO_R2_CANON` | 3852 | 568 | 6,7817 |
| | `NO_R1_FACTOR` | 6336 | 560 | 11,3143 |
| | `NO_R1_NO_R2` | 7596 | 560 | 13,5643 |

**Redukcja `DEFAULT` wobec ablacji minimalnej — zmierzona wobec predeklarowanej:**

| Rodzina | ablacja minimalna | iloraz | **redukcja zmierzona** | predeklarowana (§6.4) |
|---|---|---|---|---|
| F9-R2 | `NO_R2_CANON` | 1,1250 / 2,2500 | **50,00%** | 50,0% ✅ |
| F9-R1 | `NO_R1_FACTOR` | 1,1408 / 2,2821 | **50,01%** | 50,0% ✅ |
| F9-X | `NO_R1_NO_R2` | 5,6567 / 13,5643 | **58,30%** | 58,3% ✅ |

**Kontrole puste — obie czyste.** `NO_R1_FACTOR` w F9-R2 daje liczby **identyczne**
z `DEFAULT` (891 B / 792 rek.), a `NO_R2_CANON` w F9-R1 identyczne z `DEFAULT`
(648 B / 568 rek.). Różnica w tym miejscu byłaby przypadkiem STOP-6, nie słabszym
wynikiem — różnicy nie ma.

**Układ 2×2 dla F9-X działa multiplikatywnie także w wykonaniu:** 13,5643 → 6,7817
po włączeniu samego R1 (×0,500), 13,5643 → 11,3143 po włączeniu samego R2
(×0,834), 13,5643 → 5,6567 łącznie (×0,417). Iloczyn ×0,500 × 0,834 = 0,417,
czyli **interakcja = 1,00** — ta sama liczba, którą pilot compile-only wyliczył
z arytmetyki planu.

**Wielkości rozdzielające pracy (§0.3 predeklaracji, raportowane, nie progowe):**

| Rodzina | wielkość | `DEFAULT` | ablacja minimalna |
|---|---|---|---|
| F9-R2 | `evalCalls` | 891 | 990 |
| F9-R1 | `hashPicks` | 72 | 348 |
| F9-X | `evalCalls` | 925 | 1404 |

**Czego te liczby nie są.** Nie są pomiarem kampanii: 100 slotów na danych
miniaturowych zamiast 3000/1500 rekordów danych głównych, bez rate'u, bez czasu,
bez powtórzeń, bez bloków. Wartością jest tu **zgodność kierunku i wielkości**
z arytmetyką predeklaracji, a nie sama liczba.

---

## 5. Kontrole negatywne w wykonaniu

Wszystkie 12 komórek planów kontrolnych (4 profile × 3 plany) wykonało pełny
przebieg z rc=0 i niepustym mianownikiem. Wnioski compile-only z §3 raportu
iteracji 1 (żadnego `STREAM_SELECT_*` nad źródłami kontrolnymi, niedopasowane
przesunięcia zachowują własne substraty, `Q=1` niczego nie scala) stoją na
zrzutach **bajtowo identycznych**, więc przechodzą bez powtarzania.

Runtime dokłada do nich jedno: **kontrole też się wykonują.** W iteracji 1 nie
wykonywały się — `F9_R2_controls` i `F9_X_controls` zawierają `Sqrt`.

---

## 6. Czego pilot iteracji 2 nadal nie pokazał

1. **Danych głównych** — 3000/1500 rekordów wchodzi w P6, nie tutaj.
2. **Strony Flinka** — plany i serializer są przeniesione i niezmienione, ale
   żaden job nie był w tej sesji uruchomiony.
3. **Oracle'a, mutantów, rate'u** — P6/P7.
4. **Czasu** — trzeci warunek progu (górna granica CI ilorazu czasu ≤ 1,05) jest
   po K6c najbardziej zagrożonym punktem H9 i pilot go nie dotyka.

---

## 7. Werdykt

**GO.** Trzy rodziny mają przebieg runtime z czystymi licznikami, liczby
mechanizmu nie ruszyły się o bajt, zmierzone redukcje odtwarzają predeklarowane,
kontrole puste są puste, a bramka runtime dowiodła, że odrzuca wersję obaloną.

→ **STOP-5 iteracji 2**: predeklaracja zamknięta commitem **przed** pierwszym
pomiarem kosztowym.
