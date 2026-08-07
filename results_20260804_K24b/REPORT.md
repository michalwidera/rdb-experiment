# K24b — raport ramienia (b)

**Data:** 2026-08-04
**Predeklaracja:** [`PREDECLARATION.md`](PREDECLARATION.md), zamrożona przed
przebiegiem potwierdzającym
**Poprzednik:** [`../results_20260803_K24/`](../results_20260803_K24/) §5 —
diagnoza nieocenialności. Katalog nietknięty.

---

## 1. Wynik

**H10b wsparta**, potwierdzona poza próbą.

| Kryterium | Próg | Ziarno robocze `20260803` | Ziarno potwierdzające `20260805` |
|---|---|---:|---:|
| gęstość rozjazdu reguły lokalnej | ≥ 5% planów | **52,8%** (5287/10010) | **52,9%** (5294/10010) |
| deficyt `= ceil((p+q−1)/p)` | 100% populacji | **2323/2323** | **2310/2310** |
| deficyt ostro dodatni | 100% populacji | **2323/2323** | **2310/2310** |
| kontrola: plany bez `#` | zero rozjazdu | **0/8518** | **0/8568** |
| kontrola: `HC_SINGLE` bez własnego ogona | zero rozjazdu | **0/1151** | **0/1113** |

Treść twierdzenia: dla węzła `#`, którego obie składowe są deklaracjami,
naturalna reguła lokalna — składająca ogon operator po operatorze bez
jakiegokolwiek członu fazowego — **zaniża** prawdziwy ogon dokładnie o
`ceil((p+q−1)/p)`, gdzie `p/q` to nieskracalny iloraz taktów składowych.
Zaniżenie jest zawsze dodatnie, a klasa ma gęstość rzędu połowy korpusu.

## 2. Co trzeba było naprawić, żeby (b) dało się w ogóle ocenić

Dwie przyczyny, obie usunięte.

**Pierwsza — sprzeczność w specyfikacji.** Predeklaracja K24 żądała reguły „bez
składnika fazowego” i jednocześnie zera rozjazdu przy ilorazie całkowitym.
Przy ilorazie całkowitym `p/1` postać daje `ceil(p/p) = 1`, więc kontrola
`HC_INT` była niemożliwa do spełnienia dla **każdej** reguły bez fazy.
Testowała nie regułę, tylko fałszywe założenie o jej degeneracji. Kontrola
została usunięta, co jest osłabieniem aparatury i tak jest raportowane; jej
rolę przejęły dwie kontrole, które nie mają tej wady: plany bez `#` oraz
`HC_SINGLE` ograniczone do operatorów faktycznie pozbawionych własnego ogona.

**Druga — złe odniesienie, wykryta 2026-08-04.** Rozjazd był porównywany
z postacią `own` pochodzącą z **postaci zamkniętej silnika dla `#`**, a ta
sama nie jest dokładna (zgodność z granicą zdarzeniową 90,8%). Stąd 9 z 293
rozjazdów „o złej postaci” w K24. Cała odchyłka tłumaczy się tożsamością

```
    rozjazd = min(own, luka między gałęziami) − błąd postaci zamkniętej `#`
```

sprawdzoną w **412 z 412** rozjazdów korpusu roboczego. Po przejściu na oracle
jako odniesienie i po zawężeniu populacji do węzłów `#` o obu składowych
deklarowanych — gdzie luka między gałęziami jest zerowa, więc nic nie pokrywa
deficytu — postać trafia w 100%.

**Zawężenie populacji ma powód strukturalny, nie wynikowy.** Gdy składowa jest
strumieniem obliczanym, jej własny ogon wchodzi do obu reguł przez `max` po
gałęziach i częściowo pokrywa deficyt; obserwowana różnica przestaje być wtedy
własnością operatora `#`, a staje się własnością kształtu poddrzewa.
Twierdzenie ma mówić o operatorze.

## 3. Znalezisko poboczne: `#` ma regułę dokładną

Przy okazji ustalono, że klasa `#` — jedna z czterech otwartych w członie (a) —
**ma regułę dokładną**, wyprowadzoną z warunku dostępności tak samo jak dla `+`
i `@`: ogon jest maksimum po jednym okresie fazowym z

```
    ceil( (j(i) + 1 + W_src(i)) * D_src(i) / D_c ) − 1 − i
```

gdzie `(src, j)` to składowa i indeks wybrane przez definicję przeplotu dla
rekordu `i`. Zgodność z granicą zdarzeniową: **5995 z 5995** węzłów korpusu
roboczego, zero zaniżeń.

Dwa zastrzeżenia, oba istotne:

1. To jest **reguła wyliczalna z planu**, ale nie wyrażenie `O(1)` — wymaga
   przebiegu po jednym okresie fazowym o długości `p+q`. Czy mieści się
   w pojęciu „postać zamknięta” użytym w H10a, jest **pytaniem definicyjnym
   do rozstrzygnięcia**, nie faktem pomiarowym.
2. Reguła **nie jest wdrożona w silniku**. Wdrożenie to osobna pozycja o koszcie
   porównywalnym z naprawą `+` i `@`: zmiana `computeStartupLatency`, aktualizacja
   repliki, przeliczenie wzorców testów (ogony `#` zmienią się w ~9% węzłów),
   pełna bramka odwzorowania. Dopóki nie jest wdrożona, klasa `#` w członie (a)
   pozostaje **otwarta**, a silnik nadal zawyża ogon `#` o slot w ~9% przypadków.

Wynik ramienia (b) **nie zależy** od tego wdrożenia: (b) porównuje regułę lokalną
z oracle'em, a nie z silnikiem.

## 4. Zagrożenia dla trafności

1. **Przeformułowanie po zobaczeniu danych.** Definicja reguły, populacja
   i zestaw kontroli powstały po K24. Zaadresowane przebiegiem na ziarnie
   `20260805`, predeklarowanym przed uruchomieniem, użytym raz. Status:
   **potwierdzenie poza próbą, nie test prospektywny** — raportować dosłownie.
2. **Usunięta kontrola `HC_INT`.** Aparatura jest o jedną kontrolę słabsza niż
   w K24. Uzasadnienie w §2 jest dowodowe, nie wygodnościowe: kontrola była
   niespełnialna z samej postaci. Zastąpiona dwiema, które są spełnialne
   i faktycznie testują definicję reguły.
3. **Zawężona populacja.** Twierdzenie dotyczy węzłów `#` o obu składowych
   deklarowanych — 2323 z 5995 węzłów `#` korpusu. Dla pozostałych deficyt
   istnieje, ale jego wartość zależy od kształtu poddrzewa i nie jest opisana
   postacią zamkniętą. To zawężenie **musi** znaleźć się w treści twierdzenia
   w artykule; bez niego twierdzenie jest fałszywe.
4. **Oracle wspólny z K24 i K24r.** Bajtowo ten sam plik, co jest warunkiem
   porównywalności, ale oznacza, że błąd oracle'a przeszedłby przez wszystkie
   trzy badania. Zabezpieczenie: bramka niezależności, 37 przypadków ręcznych,
   zestaw mutantów wykrywany w 100%.

## 5. Co z tego wynika dla artykułu

Fakty do decyzji człowieka — **nie podejmuję jej w tym raporcie**:

1. **Trzecia noga różnicy wobec prior work przestała być pusta.** Nielokalność
   `ceil((p+q−1)/p)` jest teraz zmierzona i potwierdzona poza próbą, a nie
   „raportowana bez werdyktu”. Wchodzi do contributions razem z zawężeniem
   populacji z §4 punkt 3.
2. **Twierdzenie trzeba przenieść w brzmieniu zawężonym.** Zdanie „reguła
   lokalna zaniża o `ceil((p+q−1)/p)`” bez warunku o deklarowanych składowych
   jest nieprawdziwe i zostanie obalone pierwszym kontrprzykładem recenzenta.
3. **Znalezisko z §3 zmienia bilans członu (a)**, ale dopiero po wdrożeniu:
   `#` to 5995 z 35 827 obserwacji węzłowych korpusu, więc domknięcie tej klasy
   przesuwa człon (a) z pięciu klas wspartych na sześć, zostawiając trzy otwarte
   (`-`, `Θ`, `~Θ`).
