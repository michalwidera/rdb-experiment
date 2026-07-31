# K20 etap 1c — model kosztu slotu z rodziną okienną w zbiorze uczącym

**Predeklaracja.** Napisana i commitowana **przed** uruchomieniem dopasowania.
Podział rodzin, warianty cech, kryterium sukcesu i przewidywanie są zamrożone.
Po pierwszym wyniku nie wolno ich zmienić. Reakcją na niespodziankę jest
zatrzymanie i nowy katalog (`REQUIREMENTS.md` R3).

Katalogi `results_20260730_K6c` i `results_20260731_instrument` są **zamknięte**.
To badanie z nich tylko **czyta**.

## Dlaczego to badanie istnieje — czego nie dało się rozstrzygnąć w E4

`results_20260731_instrument` (E4) zebrało cechy pracy na slot i **nie wydało
werdyktu**: układ równań wyszedł osobliwy. Przyczyna jest strukturalna, nie
numeryczna.

Tylko **dwie z siedmiu** rodzin workloadów K6c używają operatorów okna: `W4`
i `W8`. Zamrożony podział K6c umieszcza `W4` w zbiorze **testowym** — celowo, bo
to ona łamie model liczący same tokeny — a `W8` **poza oboma zbiorami**, bo jej
rodzina nie należy ani do uczenia, ani do testu. Kolumna `agse_elements` jest
więc w uczeniu tożsamościowo zerowa i współczynnika nie da się oszacować.

Skrypt **odmówił wydania liczby** zamiast ją zregularyzować. To jest zachowanie
poprawne i zostaje odnotowane jako wynik E4, a nie jako awaria.

## Co się zmienia — dokładnie jedna rzecz

**Podział rodzin.** Do zbioru uczącego wchodzi `W8`, czyli rodzina niosąca okna:

| zbiór | rodziny | obserwacji |
|---|---|---:|
| uczenie | `W2`, `W3`, `W5`, `W7`, **`W8`** | 25 |
| predykcja | `W4`, `W9` | 18 |

Cechy, cele, postać modelu i warianty pozostają **bez zmian** wobec E4.

**Dlaczego `W8` wolno użyć.** `W8_Q32` została wykluczona z Tier B **decyzją
człowieka** (przeciążenie: duty 243 % `p99` przy 720 Hz). Wykluczenie dotyczy
werdyktu ablacyjnego, a nie kalibracji — `W8` ma w `rate.json` komplet liczników
i celów `p99` zmierzonych rytuałem kampanii. Model kosztu nie jest werdyktem
Tier B, więc użycie tych obserwacji nie narusza tamtej decyzji. Gdyby kiedyś
naruszało, należałoby to wykazać, a nie założyć.

**Czym to badanie NIE jest:** nie jest powtórzeniem E4 z „poprawionym"
podziałem po zobaczeniu wyniku. Podział E4 był odziedziczony po K6c i nie został
zaprojektowany pod cechy klasy operatora; ten jest zaprojektowany pod nie i
zamrożony **przed** dopasowaniem. Różnica jest istotna i ma być tak opisana.

## Odniesienie — uczciwe, czyli z tego samego podziału

Etap 1 dał **MAE_test = 258,3 %**, ale przy **innym** zbiorze uczącym (bez `W8`).
Porównywanie do tej liczby byłoby porównaniem dwóch rzeczy naraz. Dlatego:

- **odniesieniem właściwym** jest wariant `v1` (same liczniki planu) policzony
  **na tym samym podziale** co warianty z cechami E4;
- liczba 258,3 % jest raportowana jako **kontekst historyczny**, nie jako punkt
  odniesienia oceny.

## Warianty cech — zamrożone, wszystkie raportowane

| wariant | cechy |
|---|---|
| `v1` (odniesienie) | tokeny, bajty trwałe/slot, bajty pamięciowe/slot |
| `v2` (**oceniany**) | v1 + `agse_elements`/slot |
| `v3` | `agse_elements`, `agse_reads`, `eval_tokens` (wszystkie /slot) |
| `v4` | v3 + bajty trwałe/slot |

Wariantu nie wolno wybrać po zobaczeniu wyników. Oceniany jest `v2`.

## Kryterium sukcesu — zamrożone

**Sukces** wtedy i tylko wtedy, gdy jednocześnie:

1. `v2` osiąga **MAE_test ≤ 50 %**,
2. MAE_train `v2` ≤ 2 × MAE_test `v2` (kontrola przeuczenia),
3. `v2` jest **lepszy od `v1` na tym samym podziale** — bo inaczej poprawa
   pochodziłaby ze zmiany podziału, a nie z nowej cechy.

Warunek 3 jest nowy wobec E4 i jest tam właśnie po to, żeby nie przypisać cesze
zasługi, która należy się dodaniu `W8` do uczenia.

Współczynnik ujemny przy dowolnej cesze jest raportowany jako **ostrzeżenie
o współliniowości**, nie chowany.

## Przewidywanie — zapisane przed dopasowaniem

**Przewiduję, że kryterium NIE zostanie spełnione**, mimo że cecha jest
mechanistycznie właściwa. Powody, wszystkie znane przed dopasowaniem:

1. Współczynnik okna opiera się w uczeniu **wyłącznie na `W8`**, czyli na
   **3 obserwacjach**, wszystkich przy jednej skali (`s = 6`).
2. `W8` ma wewnętrzny rozrzut kosztu na element **4×** (28 014 – 112 534 ns),
   bo przy stałych 30 elementach zmienia się tam liczba zapytań `Q`. Cecha
   okienna nie tłumaczy tej zmienności, więc współczynnik wyjdzie słabo
   określony.
3. `W4` ma koszt na element stabilny w granicach **1,28×** (44 994 – 57 706 ns
   na 12 obserwacjach), ale to jest zbiór **testowy** — ta stabilność nie
   uczestniczy w dopasowaniu.

Konkretnie: przewiduję **MAE_test poniżej 100 %** (czyli wyraźną poprawę wobec
kontekstu historycznego) i **powyżej 50 %** (czyli poniżej progu przydatności).
Przewidywanie zostanie skonfrontowane z wynikiem niezależnie od tego, czy się
sprawdzi.

## Pochodzenie danych

- **Cele `p99`**: `results_20260730_K6c/results/rate.json` (kampania K6c, worker,
  rytuał pomiarowy).
- **Cechy E4**: `results_20260731_instrument/results/work.json` (nadzorca, pomiar
  różnicowy 200/400 slotów, binarka `abe075e` z badania higienicznego).
- **Warunek ważności zestawienia**: badanie higieniczne `1bb2d2c` → `abe075e`,
  werdykt **BRAK WPŁYWU** (`results_20260731_hygiene220`).

Oba zagrożenia trafności opisane w predeklaracji E4 **obowiązują tu bez zmian**:
cechy i cele pochodzą z różnych drzew kodu oraz z różnych architektur
(x86-64 vs aarch64).
