# current/ - korpus planów RQL w bieżącej składni

To drzewo zawiera kopie planów `.rql` tego repozytorium zapisane w bieżącej składni RQL. Każda kopia leży pod tą samą ścieżką względną co oryginał: `current/<ścieżka>` jest kopią `<ścieżka>`. Oryginały, manifesty skrótów kampanii (`SHA256SUMS`, `manifest.sha256`, `*sha256.tsv`) i ich bramki zostają bez zmian. Powstało w ramach retractordb #593 krok 8 (decyzje człowieka 2026-11-07).

## Dlaczego kopie i dlaczego osobne drzewo

Plany kampanii pochodzą sprzed zmian języka: `DECLARE ... FILE` (zastąpione przez `BINFILE` / `TEXTFILE` / `DEVICE`, retractordb #346) i postfiksowe `s.min` / `s.max` / `s.avg` / `s.sumc` (zastąpione przez `MIN(s)` / `MAX(s)` / `AVG(s)` / `SUMC(s)`). Silnik przyjmuje te formy z ostrzeżeniem i usunie je w przyszłości. Kopie zachowują korpus wykonywalny na bieżących i przyszłych silnikach bez naruszania zapisu kampanii.

Migracja w miejscu łamałaby zamrożone manifesty skrótów (K18, K22v2-K22v5, K23, K23v2, K24, K26, K26v2, K26v3). Kopie obok oryginałów łamałyby zamrożone bramki: `freeze_check.sh` w K26, K26v2, K26v3 i R593_H9 wymaga dokładnie 21 plików `rql/*.rql`, `validate_corpus.py` porównuje listę `rql/*.rql`, a `gen_manifest.sh` w K23 i K23v2 zbiera `pilot/*.rql`. Dlatego kopie leżą tutaj.

## Zawartość

- 224 kopie: każdy plan `.rql` rewizji `5cc7b0a`, w którym migracja coś zmienia. Pozostałe 179 planów jest już w bieżącej składni i kopii nie ma.
- `INDEX.tsv`: jeden wiersz na kopię - ścieżka, SHA-256 oryginału i kopii, status i szczegóły migracji M1 oraz S1/S2 (pola wyjścia `migrate_corpus.py`).

Status S (`s_status`):

- `MIGRATED` (189): dowód na silniku pod testem - wydruk `-c` kopii jest identyczny z wydrukiem planu po samym M1, a `--verbose` nie zgłasza formy przestarzałej;
- `PROBED` (35): plan, którego bieżący silnik nie kompiluje z powodu niezwiązanego ze składnią (31 planów F9-X z K23/K23v2 i `investigation_F9X` odwołuje się do składnika przeplotu `#`; 3 plany przyjmował tylko pin; reproducer K24 ma nagłówek w komentarzach `--`). Dowód sondą: deklaracje kompilowane pojedynczo i wyrażenie FROM z listą `*`. Przyczyny każdego odrzucenia: retractordb #593, komentarz 6585948115. Migracja nie zmienia powodu odrzucenia.

Status M1 (`m1_status` = `MIGRATED`, 54 plany): pin artefaktu `40c28dbe` typował wynik `SUMC` / `AVG` / `MIN` / `MAX` nad polem całkowitym jako INTEGER i obcinał go po cichu; od 2026-09-14 silnik daje tam RATIONAL. M1 zawija takie wyrażenie w `to_integer(...)`, więc kopia na bieżącym silniku liczy to, co liczyła kampania. Dlatego `current/config/exactness-replay.rql` różni się od `results_20261104_R593_K18/config/exactness-replay.rql`: ta druga migracja (R593 K18) miała tę samą binarkę po obu stronach, więc bez M1 - jej teza dotyczy determinizmu, nie wartości K18.

`results_20260803_K24/evidence/sub_ratio3_all_null.current.rql` (kopia ręczna z notką o naprawie) zostaje na swoim miejscu; to ona jest kompilowalną wersją reproducera, a jej odpowiednik tutaj ma status `PROBED`.

Plany generowane w czasie kampanii (generatory K6c, G3, K24e, K24f, `gen_corpus.py` K23) nie są w git, więc nie ma ich tutaj; kontrola zgodności migruje ich wynik w locie.

## Pochodzenie i sprawdzenie

Kopie to pliki silnika pod testem z przebiegu `paper-arXiv/measurment-tool/check_backward_corpus_compatibility.sh` z 2026-11-07 (narzędzia na `paper-arXiv` `08bd80f`): silnik pod testem `dev/muro@e389edd3` Release (wszystkie `RDB_OPT_*` ON), odniesienie pin `40c28dbe`, korpus `rdb-experiment@5cc7b0a`. Wynik ZGODNY we wszystkich grupach (`plans`, `runs`, `artifacts`, `g3`, `k24e`, `k24f`, `ecg`); żaden plan nie zachował formy przestarzałej (`RESIDUAL` = 0). Każdy oryginał w `INDEX.tsv` jest bajtowo równy plikowi z `5cc7b0a`.

Kontrola zgodności pomija to drzewo przy zbieraniu korpusu i porównuje każdą kopię z własnym wynikiem migracji; inny wynik migracji na nowszym silniku jest rozbieżnością tej kontroli.
