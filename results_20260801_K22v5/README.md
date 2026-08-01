# K22v5 — deklaratywny koszt specyfikacji i zmian

K22v5 jest operacyjną kontynuacją zatrzymanego K22v4. Pracuje na tym samym branchu
`experiment/20260801_K22`, ale ma osobny katalog, predeklarację, aparaturę i
pakiet dowodowy.

**Stan: przygotowany do pełnego smoke i zamrożenia.** Jedyna zmiana względem
K22v4 to etykieta drugiego pola serializowanego przez writery Pythona i
Flinka w M1/F1: `channel_2` → kanoniczne `f1_out_1`. Zmiana leży poza
mierzonymi rdzeniami; wszystkie 36 sekcji rdzeni jest identyczne z K22v4.

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
