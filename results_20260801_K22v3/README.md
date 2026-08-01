# K22v3 — deklaratywny koszt specyfikacji i zmian

K22v3 jest operacyjną kontynuacją zatrzymanych K22 i K22v2. Pracuje na tym samym branchu
`experiment/20260801_K22`, ale ma osobny katalog, predeklarację, aparaturę i
pakiet dowodowy.

**Stan: zatrzymany przed D1/D2.** Bazy F1/F2 przeszły, ale baza F3 przekroczyła
timeout, ponieważ otrzymała zapas 4200 cykli potrzebny tylko M3/F3. Naprawa
wyboru cykli jest wykonywana w K22v4, nie w zamrożonym K22v3.

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

K22v3 nie mierzy czasu wykonania. Timeouty chronią przed zawieszeniem aparatury,
nie są obserwacją wydajnościową.
