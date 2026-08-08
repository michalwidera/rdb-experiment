# Raport pilota compile-only (faza P4) — K23 / H9

**Data:** 2026-08-08. **Werdykt: GO.** Wszystkie trzy rodziny uruchamiają
zamierzony mechanizm, wszystkie kontrole negatywne i near-miss przechodzą,
a `F9-X` — jedyna rodzina z bramką NO-GO — **działa**.

Pilot **nie mierzył kosztu**: wyłącznie `xretractor -c` (tryb `--onlycompile`),
bez `-r`, bez `-m`, na danych miniaturowych. Nie użyto danych głównych, nie
dobierano progu ani rate’u. Predeklaracja pozostaje niezamrożona (STOP-5).

---

## 1. Aparatura

| Pozycja | Wartość |
|---|---|
| SHA kodu | `1cfccf97e954025d5fb055f1cfd4f1fa9aff05e8`, drzewo czyste |
| Profile | zbudowane przez `build_profiles.sh`, `--build-info` zweryfikowane bajtowo dla każdego |
| `xretractor` DEFAULT | `9e1cec8ac707ff33…` |
| `xretractor` NO_R2_CANON | `8d6d795e998410ec…` |
| `xretractor` NO_R1_FACTOR | `46d5b367c047830e…` |
| `xretractor` NO_R1_NO_R2 | `6159f5d3b070595c…` |
| Polecenie | `RDB_BENCH_PLAN=1 <binarka> <plan>.rql -c` |
| Macierz | 4 profile × 6 planów = **24 kompilacje, wszystkie rc=0** |
| Dane | `pilot/src_{a,b,c,d}.txt` (120 rekordów), `src_{p,q}.txt` (2 pola) — miniaturowe |
| Surowe wyjście | `pilot/out/<profil>_<plan>.{plan,probe}` |
| Odtworzenie | `pilot/run_pilot.sh`, zestawienie `pilot/mechanism_table.py` |

Jednostka bajtowa w tabelach: `n_h·w` = liczba slotów strumienia przeplecionego
(150 Hz) razy szerokość kanoniczna rekordu jednopolowego (9 B). Jednostki są
**arytmetyką predeklaracyjną** (rate × szerokość), nie odczytem licznika — pilot
jest compile-only, więc rzeczywista liczba zapisów przychodzi dopiero w P6.

---

## 2. Wynik główny — tabela mechanizmu przy `Q = 8`

| Rodzina | Profil | `r1` | `r2` | `STREAM_SELECT_*` | substraty | jednostki | konsumenci wspólnego węzła |
|---|---|---|---|---|---|---|---|
| **F9-R2** | `DEFAULT` | 0 | **4** | **1** | 1 | 0,667 | **8** |
| | `NO_R2_CANON` | 0 | 0 | 2 | 2 | 1,333 | 4 + 4 |
| | `NO_R1_FACTOR` | 0 | 4 | 1 | 1 | 0,667 | 8 |
| | `NO_R1_NO_R2` | 0 | 0 | 2 | 2 | 1,333 | 4 + 4 |
| **F9-R1** | `DEFAULT` | **4** | 0 | 0 | **1** | 1,000 | **8** |
| | `NO_R2_CANON` | 4 | 0 | 0 | 1 | 1,000 | 8 |
| | `NO_R1_FACTOR` | 0 | 0 | 0 | 3 | 2,000 | 4 + 4 + 4 |
| | `NO_R1_NO_R2` | 0 | 0 | 0 | 3 | 2,000 | 4 + 4 + 4 |
| **F9-X** | `DEFAULT` | 2 | 4 | **1** | 5 | **5,000** | **8** |
| | `NO_R2_CANON` | 2 | 0 | 2 | 6 | 6,000 | 4 + 4 |
| | `NO_R1_FACTOR` | 0 | 4 | 2 | 12 | 10,000 | 4 + 4 |
| | `NO_R1_NO_R2` | 0 | 0 | 4 | 14 | 12,000 | 2 × 4 |

**Redukcje `DEFAULT` wobec ablacji minimalnej:**

| Rodzina | ablacja minimalna | iloraz | redukcja | przewidywano w szkicu |
|---|---|---|---|---|
| F9-R2 | `NO_R2_CANON` | 0,667 / 1,333 | **50,0%** | 50,0% ✅ |
| F9-R1 | `NO_R1_FACTOR` | 1,000 / 2,000 | **50,0%** | 50,0% ✅ |
| F9-X | `NO_R1_NO_R2` | 5,000 / 12,000 | **58,3%** | 58,3% ✅ |

Układ 2×2 dla F9-X wypadł dokładnie jak predeklarowano: `12 → 6` po włączeniu
samego R1 (×0,500), `12 → 10` po włączeniu samego R2 (×0,833), `12 → 5` łącznie.
`12 × 0,500 × 0,833 = 5,0`, czyli **interakcja multiplikatywna = 1,00** —
złożenie jest dokładnie multiplikatywne, tak jak zapisano przed pilotem.
Współdziałanie przejść widać w liczbie instancji: jedna instancja wspólnego
podplanu powstaje **wyłącznie** w komórce z oboma przejściami (1 / 2 / 2 / 4).

**Bramka mechanizmu §10** („plan `DEFAULT` ma zawierać jedną fizyczną instancję
wspólnego podplanu, a minimalna ablacja co najmniej dwie”): spełniona w każdej
rodzinie — 1 wobec 2 (F9-R2), 1 wobec 3 (F9-R1), 1 wobec 4 (F9-X, licząc
instancje wspólnego `STREAM_SELECT_*`).

---

## 3. Kontrole negatywne i near-miss

Kryterium: nad źródłami kontrolnymi **nie powstaje żaden `STREAM_SELECT_*`**,
a niedopasowane przesunięcia zachowują własne substraty.

| Kontrola | Plan | Wynik |
|---|---|---|
| `Q=1`, F9-R2 | `F9_R2_controls` | 0 × `STREAM_SELECT_*` we wszystkich profilach ✅ |
| zmieniona kolejność pól wyniku (`n1`/`n2`) | `F9_R2_controls` | nie scalone ✅ |
| `SELECT *` ujawnia kolejność wejścia (`d1`/`d2`) | `F9_R2_controls` | nie scalone ✅ |
| inne grupowanie trzech źródeł (`x1`/`x3`) | `F9_R2_controls` | dwa osobne `STREAM_ADD_*`, nie scalone ✅ |
| `Q=1`, F9-R1 | `F9_R1_controls` | `DEFAULT` 7,778 jednostki = `NO_R1_FACTOR` 7,778 — **redukcja 0%** ✅ |
| niedopasowane przesunięcie (`MA>2 # MB>2`) | `F9_R1_controls` | `STREAM_TIMEMOVE_MA` i `_MB` przeżywają także w `DEFAULT`, brak węzła przeplotu ✅ |
| równoważne postacie nad **różnymi** instancjami źródeł (`i1`/`i2`) | `F9_R1_controls` | `STREAM_HASH_IA_IB` i `STREAM_HASH_IA2_IB2` osobno, nie scalone ✅ |
| granica obserwowalności — publiczny strumień o nazwie konwencji kompilatora | `F9_R1_controls` | `collide_user` zostaje na własnych przesunięciach ✅ |
| `Q=1`, F9-X | `F9_X_controls` | 0 × `STREAM_SELECT_*`, jednostki równe w obu profilach ✅ |
| jedna para dopasowana, druga nie (`h1`/`h2`) | `F9_X_controls` | nie scalone, `STREAM_TIMEMOVE_HC`/`_HD` przeżywają w `DEFAULT` ✅ |

**Obserwacja do predeklaracji.** `r2` w kontrolach F9-R2 wynosi 3 przy
`commutative=ON`, mimo że nic się nie scaliło. `REWRITE_APPLIED r2` liczy
**zamiany w odcisku**, nie scalenia — dodatnie `r2` w planie kontrolnym jest
poprawne i nie oznacza naruszenia kontroli. Skrypt werdyktu musi patrzeć na
liczbę `STREAM_SELECT_*` i konsumentów, a nie na samo `r2`.

**Wynik `Q=1` w F9-R1 wart osobnego zdania.** Liczba instancji zmienia się
(1 wobec 2), ale liczba jednostek bajtowych **nie** — reguła R1 przy jednej
postaci jedynie przenosi przesunięcie, nie usuwa materializacji
(`1/100 + 1/50 = 1/150` po obu stronach). To jest empiryczne potwierdzenie, że
metryką pierwotną muszą być bajty, a nie liczba węzłów planu: samo liczenie
instancji zawyżyłoby efekt tam, gdzie go nie ma.

---

## 4. P-1 — rozstrzygnięte pozytywnie

Najkruchsze miejsce kampanii (`SZKIC_RODZIN.md` §6.4) było pytaniem, czy program
pól wolno odwołać do zadeklarowanych źródeł leżących pod trzema piętrami
operatorów (`>`, `#`, `+`) i czy po przepisaniu R1 odciski obu postaci pozostaną
identyczne.

**Tak.** W profilu `DEFAULT` wszystkie osiem monitorów F9-X (`m1`…`m8`, cztery
różne postacie składniowe) czyta **jeden** `STREAM_SELECT_m1`:

```
m1(1/150) origin=3  :- PUSH_STREAM(STREAM_SELECT_m1)
…
m8(1/150) origin=3  :- PUSH_STREAM(STREAM_SELECT_m1)
```

Odwołania `A[0]`, `B[0]`, `C[0]`, `D[0]` rozwiązały się przez całe złożenie,
a `retargetSchemaReferences` w regule R1 zostawiło je w postaci zgodnej między
W1–W4. Rodzina F9-X istnieje, więc kampania nie zatrzymuje się przed
predeklaracją.

---

## 5. Rozbieżności wobec szkicu — dwie, obie wyjaśnione

1. **`r1` w F9-X: przewidywano 8, wyszło 2.** Powód: identyczne podwyrażenia
   inline są unifikowane **już na etapie ekstrakcji**, po nazwie generowanej
   z operandów — cztery monitory postaci W1/W2 dzielą jeden substrat
   `(A>2)#(B>1)`, więc reguła R1 ma do przepisania dwa węzły (para przednia
   i tylna), nie osiem. Ta unifikacja jest **niezależna od profilu** (nie stoi za
   nią żaden przełącznik `RDB_OPT_*`), więc znosi się w ilorazie 2×2 — i
   rzeczywiście wszystkie cztery komórki bajtowe wyszły zgodnie z predykcją.
   Do predeklaracji: `r1` dla F9-X wynosi **2** (i `3` w planie kontrolnym).
2. **Kolumna „substraty złożenia” w `SZKIC_RODZIN.md` §6.3.** Podano 8 tam, gdzie
   plan ma **10** instancji: dwa substraty przesunięć (100 Hz i 50 Hz) sumują się
   do **jednej** jednostki bajtowej i tak je liczyłem w kolumnie bajtowej.
   Instancje i jednostki bajtowe to dwie różne wielkości; kolumna bajtowa (10 i
   12) była poprawna, kolumna instancji nie. Poprawione w szkicu.

Żadna z rozbieżności nie zmienia werdyktu ani przewidywanych redukcji.

---

## 6. Czego pilot nie pokazał

1. **Rzeczywistej liczby zapisów** — jednostki bajtowe to `rate × szerokość`
   przy założeniu jednego zapisu na slot. Licznik `LOGICAL` czyta się dopiero
   w P6, na zamrożonej liczbie rekordów.
2. **Strony Flinka** — czeka na **D-2**; bez niej nie ma drugiego członu progu
   (redukcja ≥40% także wobec `FLINK_NATURAL`).
3. **Oracle, mutantów, rate’u** — P5/P6/P7.
4. `mechanism_table.py` klasyfikuje publiczny strumień nazwany konwencją
   kompilatora (`STREAM_HASH_CA_CB` w kontrolach F9-R1) jako substrat, przez co
   zawyża tam liczbę substratów i jednostek. Dotyczy **wyłącznie** planu
   kontrolnego i nie wpływa na żadną liczbę z §2. Do naprawy zanim skrypt wejdzie
   do aparatury werdyktu.

---

## 7. Werdykt i następny krok

**GO.** Warunki z §5 Kroku 3 spełnione dla każdej rodziny: `REWRITE_APPLIED`,
liczba `STREAM_SELECT_*`, substraty i ich konsumenci zgodne z predeklarowaną
tabelą (z dwiema poprawkami z §5), `Q=1` niczego nie scala, kontrole near-miss
nie zostały scalone.

→ **STOP-4**: decyzja człowieka o wejściu w P5 (predeklarację). Przed nią
pozostaje otwarte jedno pytanie D-3 — zakres twierdzenia dla F9-X
(`SZKIC_D3.md` §3.3) — którego pilot nie rozstrzyga i rozstrzygnąć nie mógł:
działanie mechanizmu nie jest odpowiedzią na pytanie, kto pisze te postacie.
