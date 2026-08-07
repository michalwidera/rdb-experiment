# K24b — predeklaracja ramienia (b), nielokalność

**Data zamrożenia:** 2026-08-04, przed uruchomieniem przebiegu potwierdzającego
**Poprzednik:** [`../results_20260803_K24/`](../results_20260803_K24/) — kampania,
w której człon (b) okazał się **nieocenialny** wskutek sprzeczności w specyfikacji
**Diagnoza sprzeczności:** `../results_20260803_K24/REPORT.md` §5
**Ścieżka:** `paper-arXiv/debs/research_plan.md` §15, pozycja `[K24/H10 — człon (b)]`,
kroki b1–b5; §16.1 krok 3b

Ramię (a) jest tą predeklaracją **nietknięte**. Aparatura (`oracle/`,
`generator.py`) jest kopią bez zmian.

---

## 1. Dlaczego stara specyfikacja była nieocenialna

Predeklaracja K24 wymagała dwóch rzeczy naraz: (1) reguła lokalna „bez
składnika fazowego”, (2) zero rozjazdu przy ilorazie całkowitym (kontrola
`HC_INT`). Są sprzeczne: przy regule bez fazy i ilorazie całkowitym
`p/q = p/1` deficyt wynosi `ceil((p+1-1)/p) = 1`, więc **nie może** być zerowy.
Kontrola `HC_INT` testowała nie regułę, tylko fałszywe założenie o jej
degeneracji.

Druga pozycja, wykryta 2026-08-04: rozjazd był porównywany z postacią `own`
pochodzącą z **postaci zamkniętej silnika dla `#`**, która sama nie jest
dokładna (zgodność z granicą zdarzeniową 90,8%). Cała odchyłka 15 z 412
rozjazdów korpusu roboczego tłumaczy się tym błędem — sprawdzone tożsamością
`rozjazd = min(own, luka) − błąd_postaci_#` w **412 z 412** przypadków.

## 2. Decyzja b1 — czym jest naturalna reguła lokalna

**Wariant A.** Ta sama rekursja po planie, w której **własny ogon każdego
operatora wynosi zero**, ogon składowej przeliczany jest przez takt wzorem
`ceil(w * D_src / D_dst)`, a przesunięcie `>N` dodaje `N`.

Uzasadnienie wyboru, sformułowane bez odwołania do wyników: wariant B (z członem
pierwszej fazy `ceil(q/p)`) sam zawiera składnik fazowy, więc nazwanie go regułą
„bez składnika fazowego” jest wewnętrznie sprzeczne. Reguła lokalna ma
reprezentować rachunek, który powstaje, gdy ktoś składa ogon operator po
operatorze **nie zauważając zjawiska fazy** — a to jest wariant A.

## 3. Co jest twierdzone (b2)

**H10b.** Istnieje klasa planów, w której naturalna reguła lokalna (wariant A)
**zaniża** prawdziwy ogon — indeks pierwszego w pełni określonego rekordu
wynikający z modelu zdarzeniowego — o wartość daną postacią zamkniętą

```
    deficyt = ceil((p + q - 1) / p),   gdzie p/q = D_a / D_b w postaci nieskracalnej
```

dla węzła `#` o składowych `A` i `B`. Klasa ta ma dodatnią gęstość w losowo
generowanym korpusie.

**Populacja twierdzenia:** węzły `#`, których **obie składowe są deklaracjami**.
Zawężenie wobec K24 jest świadome i ma powód strukturalny, nie wynikowy: gdy
składowa jest strumieniem obliczanym, jej własny ogon wchodzi do obu reguł przez
`max` po gałęziach i **częściowo pokrywa** deficyt, więc obserwowana różnica
przestaje być własnością operatora `#`, a staje się własnością konkretnego
kształtu poddrzewa. Twierdzenie ma mówić o operatorze.

**Odniesieniem jest oracle** (model zdarzeniowy), nie postać zamknięta silnika.
Ta zmiana usuwa drugą przyczynę nieocenialności z §1.

## 4. Kryteria

**Wsparcie H10b** wymaga łącznie:

1. **próg gęstości:** reguła lokalna A rozjeżdża się z prawdziwym ogonem
   w co najmniej **5%** planów korpusu;
2. **postać:** w populacji twierdzenia deficyt równa się `ceil((p+q-1)/p)`
   w **100%** węzłów; jedna niezgodność falsyfikuje człon (b);
3. **dodatniość:** deficyt jest ostro dodatni w 100% populacji — inaczej
   „zaniża” jest nieprawdziwe.

**Kontrole negatywne (b3).** Rozjazd zerowy w klasach:

* **plany bez `#`**, złożone wyłącznie z operatorów pozbawionych własnego ogona
  (`PASS`, `>N`, redukcje) — obie reguły muszą dać identyczny wynik;
* `HC_SINGLE` **ograniczone** do operatorów pozbawionych własnego ogona.
  Zapis dosłowny z K24 pęka, bo dopuszcza `@` i `-`, które własny ogon mają —
  to defekt kontroli, nie wynik.

**Kontrola `HC_INT` zostaje usunięta.** Powód w §1: przy ilorazie całkowitym
deficyt wynosi 1 z samej postaci, więc zerowa kontrola jest niemożliwa dla
każdej reguły bez fazy. Usunięcie jest **osłabieniem aparatury** i musi być
raportowane jako takie.

## 5. Korpus i ziarna

| Pozycja | Wartość |
|---|---|
| generator | `generator.py`, bez zmian wobec K24 |
| liczność | 10 010 planów |
| ziarno robocze (na nim powstało przeformułowanie) | `20260803` |
| **ziarno potwierdzające (out-of-sample)** | **`20260805`** |

Ziarno `20260805` jest zapisane **przed uruchomieniem** i jest jedynym ziarnem
potwierdzającym. Wynik negatywny na nim jest wynikiem negatywnym; nie wolno
próbować kolejnych ziaren.

## 6. Co unieważnia ten przebieg

* zmiana `generator.py`, `oracle/`, definicji reguły lokalnej, populacji lub
  progów po dacie zamrożenia;
* uruchomienie przebiegu potwierdzającego na ziarnie innym niż `20260805`;
* użycie postaci zamkniętej silnika zamiast oracle'a jako odniesienia.

## 7. Status epistemiczny

Przeformułowanie powstało **po zobaczeniu** wyniku K24 i na korpusie
`20260803`. Przebieg na `20260805` jest **potwierdzeniem poza próbą, nie testem
prospektywnym** — predeklarowane są ziarno, populacja i kryteria, nie hipoteza.
W artykule raportować dosłownie w tej formie, tak samo jak dla członu (a).
