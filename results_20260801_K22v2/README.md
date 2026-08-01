# K22v2 — deklaratywny koszt specyfikacji i zmian

K22v2 jest poprawioną, prospektywną kontynuacją zatrzymanego pilota
`../results_20260801_K22/`. Pracuje na tym samym branchu
`experiment/20260801_K22`, ale ma osobny katalog, predeklarację, aparaturę i
pakiet dowodowy.

**Stan: ZATRZYMANY BEZ WYNIKU.** Pierwsza komórka `base/F1` nie rozpoczęła
wykonania z powodu błędnej ścieżki pliku blokady przy absolutnym `argv[0]`.
Zgodnie z regułą zamrożenia naprawa żyje w `../results_20260801_K22v3/`, a ten
katalog zachowuje warianty i surowy log nieudanego startu.

Kolejność obowiązkowa:

```bash
./tests/run.sh
./freeze_check.sh
./generate_variants.py
./run_campaign.sh
```

Przed lokalnym commitem zamrażającym wolno uruchamiać wyłącznie testy
fixture'ów. `generate_variants.py` odmawia pracy, dopóki `PREDECLARATION.md`
nie zawiera commita zamrażającego.

K22v2 nie mierzy czasu wykonania. Timeouty chronią przed zawieszeniem aparatury,
nie są obserwacją wydajnościową.
