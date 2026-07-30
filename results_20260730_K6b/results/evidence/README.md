# Dowody porażek — K6b

Oba wpisy niżej to **defekty harnessu**, nie silnika i nie pomiaru. Kod silnika
pozostał zamrożony na `bb3a521` przez całą kampanię.

## 1. `harness_defect_stdin_study_01_W2` — klient dziedziczył plan jako stdin

Pierwsze uruchomienie Tier B (19:37) padło na **pierwszym** przebiegu:
„klient xqry nie uruchomil sie".

**Przyczyna.** Pętla przebiegów w `worker/run_ablation_study.sh` czytała plan
konstrukcją `while read ... done < plan.tsv`, więc procesy potomne dziedziczyły
**plik planu jako stdin**. Klient `xqry` czytał go do końca i kończył się kodem
0, zanim skrypt zdążył sprawdzić, czy żyje.

Drugi skutek był cichszy i groźniejszy: potomek **konsumował** plan, więc pętla
gubiłaby przebiegi bez ani jednego komunikatu — złapałaby to dopiero reguła
zliczania `executed == TOTAL_RUNS`.

**Rozstrzygnięcie eksperymentalne** (`/dev/shm`, poza repozytoriami): ten sam
kod z `xqry ... < /dev/null` — klient żyje; bez tego — martwy, kod 0.

**Naprawa.** Plan czytany z deskryptora 9 (`read <&9` … `done 9< plan.tsv`),
stdin odcięty każdemu procesowi potomnemu w pętli.

Archiwum zawiera jeden przebieg `W2_Q08/STRUCT/r05` zabity po ~4 s przez
sprzątanie po błędzie. **Nie jest pomiarem**: sonda ma 389 slotów z 719.

## 2. `discarded_study_01_W2` — pomiar poprawny, odrzucony razem z harnessem

Drugie uruchomienie Tier B (19:45–20:04) **zmierzyło badanie W2 w całości**:
180/180 przebiegów, odcisk drzewa kodu bez zmian, katalogi wejściowe czyste,
artefakty spakowane. Padł dopiero `git push`:

```
! [rejected]  HEAD -> experiment/20260730_K6 (stale info)
```

**Przyczyna.** R4 trzyma **jeden** commit kampanii, wspólny dla nadzorcy
i workera. Nadzorca wypchnął poprawkę `cost_model.py` o 19:52, w trakcie
badania; worker pobrał branch o 19:45, więc jego `--force-with-lease` słusznie
odmówił — inaczej cicho skasowałby commit nadzorcy. Dzierżawa zadziałała
dokładnie tak, jak powinna.

**Naprawa dwutorowa.** (a) Dyscyplina: żadnych pushów na branch kampanii, gdy
badanie jest w locie. (b) Kod: worker odświeża branch i przenosi wyniki na
aktualny wierzchołek **tuż przed** commitem, a wpis do `JOURNAL.md` powstaje
dopiero po odświeżeniu, na świeżej wersji pliku. Odrzucony push kończy badanie
błędem z informacją, że pomiar leży w drzewie roboczym i nie został utracony.

**Dlaczego dane zostały odrzucone, a nie doszyte.** Naprawa (b) zmienia
`run_ablation_study.sh`. Doszycie badania 1 znaczyłoby, że jedna rodzina
zmierzona jest inną wersją harnessu niż pozostałe sześć. Zmiana leży poza
ścieżką pomiarową i dałoby się to obronić, ale ponowny przebieg kosztuje
19 minut maszyny i zero godzin człowieka — jednolita proweniencja wszystkich
siedmiu badań jest tego warta.

Zachowane: `discarded_study_01_W2_runs.csv` (180 przebiegów) oraz
`discarded_study_01_W2_results.md`. **Nie wolno ich użyć jako danych kampanii** —
kampania raportuje wyłącznie badania z katalogu `ablation/`.

## 3. `harness_defect_race_study_02_W3` — wyścig w protokole dołączania klienta

Trzecie uruchomienie Tier B: badanie 1 (W2) przeszło i **zostało zapisane**,
badanie 2 (W3) padło na szóstym przebiegu, `W3_d3_STRUCT_r12`, z tym samym
komunikatem co defekt nr 1 — ale z zupełnie innej przyczyny.

**Przyczyna.** Protokół dołączania klienta trwa ~3 s (`sleep 2` → start `xqry`
→ `sleep 1` → kontrola żywotności) i milcząco zakładał, że przebieg trwa dłużej.
Pomiar faz na workerze:

| komórka | czas silnika | kontrola klienta o | wynik |
|---|---:|---:|---|
| `W3_d1` | 6098 ms | 3039 ms | klient żyje |
| `W3_d3` | **3053 ms** | 3044 ms | klient martwy — **o 9 ms** |
| `W2_Q32` | 6131 ms | 3041 ms | klient żyje |

Silnik kończył się **sam**, klient wychodził za nim kodem 0, a kontrola
żywotności czytała normalny koniec jako „klient nie uruchomil sie". Sonda
w archiwum ma komplet 2880 slotów — pomiar był kompletny.

Wyścig, więc awaria losowa: badanie 1 przeszło szczęśliwie, bo przebiegi W2
trwają 6 s. Mogła trafić dowolną rodzinę w dowolnym momencie kampanii.

**Naprawa.** Rozróżnienie, którego brakowało: klient nieobecny przy
**działającym** silniku to awaria; klient nieobecny po **zakończonym** silniku
to normalny koniec krótkiego przebiegu — pod warunkiem, że wyszedł zerem.
Regresja: `tests/test_rate_guard.sh`, kontrole 17 i 18.

## 4. `slot(phi)` a rzeczywisty interwał złożony w rodzinie W3 — NIE defekt kodu

Diagnostyka wyścigu odsłoniła rzecz istotniejszą, której **nie da się naprawić
w kodzie**, bo dotyczy zamrożonej definicji.

Predeklaracja definiuje `slot(phi) = 1/(15·s)`, czyli interwał przeplotu **dwóch**
strumieni `A#B`. Rodzina W3 zagnieżdża kolejne przepłoty, więc jej strumień
wyjściowy ma interwał **gęstszy**: częstotliwości się sumują.

Przy `s = 24` (rate wybrany dla W3):

| komórka | nominalne `slot(phi)` | rzeczywisty `phi` | rzeczywisty slot | `p99` | udział slotu |
|---|---:|---:|---:|---:|---:|
| `W3_d1` | 2778 µs | 360 Hz | 2778 µs | 886 µs | 32 % |
| `W3_d3` | 2778 µs | **810 Hz** | **1235 µs** | 1122 µs | **91 %** |

Reguła 50 % została zastosowana **dokładnie tak, jak zapisana** — kalibracja
porównała `p99 = 1122 µs` z budżetem `1389 µs` i słusznie uznała, że się mieści.
Ale intencja reguły („porównanie profili musi zachodzić w reżimie
nienasyconym") dla `W3_d3` **nie jest osiągnięta**: komórka pracuje na 91 %
swojego rzeczywistego slotu, nie na 40 %.

**Nie korygujemy tego w trakcie kampanii.** Drabina i próg są zamrożone, a
predeklaracja przewiduje dokładnie taką sytuację dla W8: „jeżeli najcięższa
komórka narusza regułę 50 %, jej cele **nie są zwalniane** — komórka zostaje
w macierzy i jest raportowana jako nasycona, wraz z konsekwencją dla
interpretacji". `W3_d3` jest raportowana tak samo.

**Decyzja należy do człowieka na etapie werdyktu** (P2): czy `W3_d3` wchodzi do
werdyktu jako komórka nasycona z zastrzeżeniem, czy wypada z niego, czy rodzina
W3 wymaga powtórzenia w nowym katalogu z poprawioną definicją `slot(phi)`.
Dane W3 zostaną zebrane niezależnie od tej decyzji — jest to decyzja
o interpretacji, nie o zbieraniu.

`W3_d2` nie należy do Tier B, więc nie dotyczy.
