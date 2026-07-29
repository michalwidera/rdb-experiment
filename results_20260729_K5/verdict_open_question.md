# Werdykt K5 wymaga rozstrzygnięcia człowieka

**Stan:** reguła decyzyjna wyliczona bez zmian daje **NO-GO**. Powód jest
jednak wąski i dotyczy jednego pola metadanych, a nie treści strumieni.
Rozstrzygnięcie, czy to pole należy do „wyniku", zmienia werdykt całego punktu
go/no-go — dlatego nie podejmuję go sam.

## Co dokładnie zawodzi

Warunki (a) i (c) oraz kwalifikator W8 są spełnione. Warunek (b) zawodzi
wyłącznie w sześciu przypadkach rodziny W8 (EKG), i wyłącznie na dwóch plikach:

| Artefakt | STRUCT | ALGSTRUCT |
|---|---|---|
| `mlii.desc` | `RETMEMORY 30` | `RETMEMORY 63` |
| `mwi.desc` | `RETMEMORY 30` | `RETMEMORY 4` |

Poza polem `RETMEMORY` oba deskryptory są identyczne. Wszystko pozostałe
zgadza się co do bajtu:

- dane wyjściowe wszystkich monitorów `mon_000..mon_003` — identyczne (1680 B);
- `.meta` wszystkich monitorów — identyczne (bez nagłówka czasowego);
- wszystkie pozostałe deskryptory strumieni nazwanych przez użytkownika;
- wszystkie 16 przypadków rodzin W1–W4 — w pełni identyczne.

`mlii` i `mwi` są strumieniami `VOLATILE`. Nie mają pliku danych — na dysku
istnieje tylko ich deskryptor. `RETMEMORY` to wyliczona pojemność historii
(`computeRequiredCapacities`), czyli parametr zasobowy zależny od kształtu
planu: pod `STRUCT` strumień karmi substrat przesunięcia, pod `ALGSTRUCT` —
węzeł przeplotu, i wymagana głębokość historii jest inna.

## Dwa czytania reguły

**Czytanie dosłowne — NO-GO.** Warunek (b) mówi „bajtowo identyczny" o
artefaktach; `mlii.desc` jest artefaktem strumienia nazwanego przez
użytkownika i różni się. Werdykt: NO-GO, a zgodnie z §K5 planu badawczego
narracja optymalizatorowa zostaje wycofana.

**Czytanie celowościowe — GO.** Sekcja „Kontrola semantyczna" README mówi
o „artefaktach wynikowych", a intencją warunku (b) było odróżnić optymalizację
od zepsucia planu. `RETMEMORY` nie jest wynikiem: nie wpływa na żaden bajt
danych ani metadanych obserwowalnych strumieni, a jego zmiana jest oczekiwaną
konsekwencją zmiany planu. Werdykt: GO (z kwalifikatorem zewnętrznej
motywacji spełnionym, bo redukcja zachodzi w W8).

## Dlaczego nie rozstrzygam tego sam

W tej kampanii poprawiłem już raz instrument po zobaczeniu wyniku
(`instrument_defect_semantic.md`). Tamta poprawka miała jednoznaczne
uzasadnienie: porównanie obejmowało nazwy substratów, więc warunek (b) był
niespełnialny zawsze, gdy reguła działała — test mierzył sam siebie, a błąd
działał przeciw hipotezie.

Tutaj jest inaczej. Wykluczenie pola `RETMEMORY` byłoby **drugą** zmianą
instrumentu po danych, tym razem zawężającą porównanie do tego, co akurat
przechodzi. Nawet gdyby było merytorycznie słuszne, procedura go/no-go
straciłaby moc dowodową: predeklaracja istnieje po to, żeby autor nie dobierał
kryterium do wyniku. Dlatego zapisuję werdykt dosłowny i przekazuję decyzję.

## Materiał do decyzji

Cokolwiek zostanie rozstrzygnięte, dane pozostają te same i są jednoznaczne:

- R1 odpala `r1 = Q` we wszystkich rodzinach ze wspólnym `phi`, do `Q = 32`;
- `net = -1` w W1, W2, W4, W8 dla każdego `Q`; `net = -d` w W3;
- oszczędność tokenów FROM rośnie liniowo z `Q`: 2, 3, 5, 9, 17, 33;
- kontrole negatywne W5, W6, W7 dają dokładnie zero dla każdego `Q`;
- 16 z 22 przypadków z redukcją jest bajtowo identycznych bez żadnych zastrzeżeń.

Jeżeli decyzja brzmi „`RETMEMORY` nie jest wynikiem", właściwym trybem jest
**nie** poprawianie `semantic.py` w tej kampanii, tylko zapisanie decyzji tutaj
i w `JOURNAL.md`, z werdyktem GO uzasadnionym jawnie wskazanym odstępstwem od
dosłownego brzmienia (b). Kolejna kampania może wtedy wystartować
z predeklaracją, która definiuje „artefakt wynikowy" precyzyjnie.
