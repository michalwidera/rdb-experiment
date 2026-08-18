# K24e — predeklaracja, iteracja 2

**Data zamrożenia:** 2026-08-18, **przed** uruchomieniem kampanii iteracji 2
**Silnik:** `retractordb` gałąź `issue_232-k24h10`, commit **`e2a61ff`** (bez zmian)
**Powód iteracji:** [`STOP.md`](STOP.md) — sufit `ORIGIN_LIMIT` w oracle'u
**Podstawa:** [`PREDECLARATION.md`](PREDECLARATION.md) — obowiązuje w całości
poza pozycjami zmienionymi niżej

## 1. Co się zmienia wobec iteracji 1

### 1.1. Aparatura

`oracle/model.py`: strażnik poszukiwania początku logicznego liczy limit jako
**margines nad oknem sondowania** (`ORIGIN_LIMIT + window`) zamiast stałej
bezwzględnej. Uzasadnienie i skala problemu: `STOP.md` §2-3. Żaden inny plik
aparatury nie jest zmieniony — `generator.py`, `run_campaign.py`, `verdict.py`,
`oracle/plan.py`, `oracle/engine.py`, `oracle/execute.py` pozostają bajtowo
takie same jak w K24d.

Zmiana dotyka **wyłącznie warunku przerwania**, nie żadnej liczonej wielkości.
Sprawdzeniem tej tezy jest kontrola z §2.2 — i to ona, a nie to zdanie, ma
o niej rozstrzygnąć.

### 1.2. Ziarna

| Rola | Ziarno | Status |
|---|---|---|
| ziarno w próbie | `20260818` | **spalone** — wynik obejrzany w iteracji 1 |
| ziarno potwierdzające (out-of-sample) | **`20260820`** | **nowe, nieoglądane** |
| ziarno wycofane | `20260819` | spalone (częściowy wynik obejrzany, `STOP.md` §4) |
| ziarno członu (b) | `20260805` | bez zmian |

`20260820` jest jedynym ziarnem potwierdzającym iteracji 2. Wynik negatywny na
nim jest wynikiem negatywnym; nie wolno próbować kolejnych.

### 1.3. Korekta przewidywania P6

W iteracji 1 zapisałem P6 jako „zerowy niedomiar we wszystkich klasach dla
składowych deklarowanych”. Brzmienie przepisałem z predeklaracji K24p **bez
zawężenia**, a jest ono zbyt mocne: `capacity.py` od K24p pokazuje dla `AGSE`
niedomiar w ok. 69% par ze składową deklarowaną — wielkość znaną, przypisaną
członowi `DECLARATION_PREFETCH` liczonemu po innej stronie w modelu niż
w silniku, sprawdzoną w K24p kontrolą celowaną na 55 planach (zero objawów).

**To jest defekt mojej predeklaracji, nie wynik pomiaru.** W iteracji 1 zostaje
zapisany jako literalnie sfalsyfikowany i tak będzie raportowany.

Brzmienie obowiązujące w iteracji 2:

> **P6'.** Klasy dotknięte naprawą (`-`, `Θ`, `~Θ`) oraz klasy `>N`, `#`, `+`
> mają **zerowy niedomiar** pojemności dla składowych deklarowanych. Dla `AGSE`
> przewidywana jest wartość **niezmieniona wobec K24d** (ok. 69%), bo naprawa
> nie tyka ani rachunku okna, ani modelu pojemności. Odchylenie `AGSE` od tej
> wartości jest wynikiem wymagającym wyjaśnienia; jej powtórzenie nie jest
> wsparciem niczego.

## 2. Przewidywania iteracji 2

P1-P5 bez zmian wobec `PREDECLARATION.md` §3. P6 w brzmieniu P6' z §1.3.
Dodatkowo:

### 2.1. P7 — powtarzalność ziarna w próbie

Ziarno `20260818` przebiegnie ponownie. Przewidywanie: **9/9 klas dokładnych,
kolumna propagowana 100%, origin 9/9** — czyli dokładnie to, co zmierzyła
iteracja 1.

### 2.2. P8 — bezczynność naprawy aparatury

Plik surowy ziarna `20260818` z iteracji 2 musi być **bajtowo identyczny**
z plikiem z iteracji 1. Żaden plan tego korpusu nie zbliżał się do sufitu
(okno maksymalne 76 348 wobec limitu 100 000), więc zmiana warunku przerwania
nie ma prawa niczego w nim poruszyć.

**Różnica choćby w jednym bajcie falsyfikuje P8** i oznacza, że naprawa
aparatury nie jest bezczynna — wtedy zatrzymanie i analiza, nie raport.

## 3. Co unieważnia iterację 2

Jak w `PREDECLARATION.md` §8, z jedną pozycją dodaną: **jakakolwiek dalsza
zmiana `oracle/model.py`** po tej dacie. Naprawa z §1.1 jest jedyną dozwoloną
i jest już wykonana w chwili zamrożenia tego dokumentu.
