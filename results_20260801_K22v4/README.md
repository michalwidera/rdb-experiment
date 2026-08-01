# K22v4 — deklaratywny koszt specyfikacji i zmian

K22v4 jest operacyjną kontynuacją zatrzymanego K22v3. Pracuje na tym samym branchu
`experiment/20260801_K22`, ale ma osobny katalog, predeklarację, aparaturę i
pakiet dowodowy.

**Stan: zatrzymany przed D1/D2.** Bazy F1--F3 przeszły, ale M1/F1 ujawniło
niezgodność samej etykiety drugiego pola: RQL emituje `f1_out_1`, a Python i
Flink emitowały `channel_2`. Wartości były zgodne. Naprawa etykiety aparatury
jest wykonywana w K22v5, nie w zamrożonym K22v4.

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

K22v4 nie mierzy czasu wykonania. Timeouty chronią przed zawieszeniem aparatury,
nie są obserwacją wydajnościową.
