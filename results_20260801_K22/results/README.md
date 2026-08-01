# Wyniki K22

**Stan: pusty. Tabele powstają w etapie K22d, werdykt na końcu.**

Ten katalog jest celowo pusty. Pusta tabela wygenerowana wcześniej wyglądałaby
na wynik, a nim nie jest — dlatego `oracle/run.sh` i `metrics/measure.py`
zatrzymują się kodem ≠ 0 zamiast wypisać zera (`PREDECLARATION.md` §7.5 pkt 2).

## Pliki, które powstaną

| Plik | Kolumny |
|---|---|
| `tails.csv` | `family,variant,model,stream,tail_slots,source` |
| `semantic.csv` | `family,variant,model,tail,range_from,range_to,rows_compared,verdict,first_mismatch` |
| `constructs.csv` | `family,model,C1..C7,C3d,C4d,loc,cyclomatic` |
| `modifications.csv` | `family,task,model,D1,D2,units_total,units_changed,test_fail_before,test_pass_after` |
| `hits.csv` | `family,model,variant,metric,rule_id,file,line,text` |
| `double_coding.csv` | `family,model,metric,script_value,manual_value,delta` |
| `verdict.md` | rozstrzygnięcie per rodzina + agregat + threats to validity |

## Zobowiązania wobec tych tabel

1. **Powstaną także dla wyniku negatywnego.** NO-GO jest prawidłowym wynikiem
   badania. Nie wolno wtedy zmieniać metryki, usuwać niekorzystnej rodziny ani
   dodawać języka, na tle którego RQL wypadnie lepiej.

2. **`verdict.md` pokazuje każdą rodzinę osobno.** Agregat nie może ukryć
   rodziny, w której RQL jest bardziej rozbudowany.

3. **`hits.csv` jest surową tabelą kwalifikacji.** Każde policzone wystąpienie
   ma plik, linię, treść i `rule_id`. Recenzent musi móc zakwestionować
   pojedyncze trafienie bez czytania kodu skryptu.

4. **`double_coding.csv` powstaje niezależnie od zgodności.** Rozbieżność > 10 %
   w dowolnej metryce zatrzymuje kampanię: poprawia się **podręcznik**, nie
   liczby, i liczy całość od nowa.

5. **`source` w `tails.csv` musi brzmieć `xretractor <plan>.rql -c`.** Ogon odczytany
   z silnika, nie wyliczony rachunkiem obok niego — to jest wniosek
   metodologiczny z K6c i najczęstsze źródło błędu w poprzedniej kampanii.
