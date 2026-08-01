# K22v5 — deklaratywny koszt specyfikacji i zmian

K22v5 jest operacyjną kontynuacją zatrzymanego K22v4. Pracuje na tym samym branchu
`experiment/20260801_K22`, ale ma osobny katalog, predeklarację, aparaturę i
pakiet dowodowy.

**Stan: zakończony. H8 — brak wsparcia (0/3 rodzin).** Pełny smoke i właściwa
kampania przeszły po 15/15 komórek, ręczne D1/D2 zgodziły się z automatem
36/36, a przegląd objął 1764/1764 trafień konstrukcji. Szczegóły i granice
wniosku zawiera `REPORT.md`.

**Analiza po werdykcie: `POSTHOC.md`.** Dopisana 2026-08-01, poza zamrożonym
pakietem dowodowym — `REPORT.md`, `PREDECLARATION.md`, `results/` i
`evidence/` pozostają nietknięte, a indeks SHA-256 nadal ważny. Ustalenie
najważniejsze: przy zamrożonym korpusie maksimum osiągalne wynosiło 1/4, 1/4
i 2/4 przy progu 3/4, więc **żadna rodzina nie mogła przejść** i wynik `0/3`
był przesądzony przed pomiarem. Werdykt jest poprawny, ale mało informatywny
o samej H8; twierdzenie, które te dane rzeczywiście uzasadniają, jest węższe.

Jedyna zmiana względem K22v4 to etykieta drugiego pola serializowanego przez
writery Pythona i Flinka w M1/F1: `channel_2` → kanoniczne `f1_out_1`.
Zmiana leży poza mierzonymi rdzeniami; wszystkie 36 sekcji rdzeni jest
identyczne z K22v4.

Kolejność obowiązkowa:

```bash
./tests/run.sh
./freeze_check.sh
./run_campaign.sh
./prepare_review.py
# ręczne wypełnienie manual_coding.csv i manual_hits_review.csv
./analyze.sh
```

Przed lokalnym commitem zamrażającym wolno uruchamiać wyłącznie testy
fixture'ów. Korpus 36 wariantów jest kopiowany i weryfikowany hashami przed
commitem zamrażającym; pomiar D1/D2 następuje dopiero po nim.

K22v5 nie mierzy czasu wykonania. Timeouty chronią przed zawieszeniem aparatury,
nie są obserwacją wydajnościową.
