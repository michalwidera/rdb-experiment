# Porównanie kampanii 360 Hz: K18 (rewizja wadliwa) vs extend (po poprawce)

- K18 `study_01`: commit `bc37186`, 2026-07-28T15:06:54
- extend `study_01`: commit `3db7817`, 2026-07-28T21:00:04
- identyczna konfiguracja: `rate_hz=360, clients=1, samples=20000, sink=null`;
  plik konfiguracji ma ten sam SHA-256 co w K18
  (`69f82adac208cd1d3c05f8ef5d8eb5f01de220a774f9a9842a256bbe8d0eafaf`)

| Metryka | K18 (bc37186) | extend (3db7817) | zmiana |
|---|---:|---:|---:|
| E1 mediana [us] | 1312.4 | 1292.8 | -1.5% |
| E1 p99 [us] | 1617.9 | 1598.8 | -1.2% |
| E1 max [us] | 1838.5 | 1816.5 | -1.2% |
| queue-emission mediana [us] | 1372.8 | 1352.7 | -1.5% |
| queue-emission p99 [us] | 1718.6 | 1697.9 | -1.2% |
| queue-emission p99,9 [us] | 1832.5 | 1803.3 | -1.6% |
| queue-emission max [us] | 1944.0 | 1976.6 | +1.7% |
| wake_lag mediana [us] | 20.7 | 20.9 | +1.0% |
| wake_lag max [us] | 54.3 | 73.1 | +34.6% |

## Interpretacja

Poprawka zwiększa o jeden rekord pojemność bufora `MEMORY` każdego źródła okna
AGSE — w tym potoku dotyczy to czterech strumieni po 4 bajty na rekord. Liczba
odczytów okna na slot się nie zmienia, a arytmetyka nie zależy od wartości
danych, więc oczekiwaną zmianą metryk było zero.

Wszystkie metryki opóźnienia mieszczą się w ±2 %. Wyjątkiem jest maksimum
jitteru pobudki (+34,6 %, 54,3 → 73,1 us): to pojedynczy outlier planisty,
nieskorelowany z treścią poprawki i o dwa rzędy wielkości mniejszy od budżetu
slotu.

Żadnej z tych różnic **nie należy czytać jako efektu poprawki**. Każda kampania
to jedno badanie 20 000 interwałów, bez powtórzeń, więc nie ma podstawy do
oddzielenia efektu od zmienności międzyprzebiegowej. Wniosek, który dane
uprawniają, jest słabszy i wystarczający: poprawka nie zmieniła rzędu wielkości
ani marginesu budżetu slotu — potok nadal mieści się w budżecie 2777,8 us
z zapasem około 30 %.

Istotna różnica jakościowa nie jest widoczna w metrykach czasowych: kampania K18
mierzyła potok, który liczył `mwi ≡ 0`, czyli z martwą detekcją QRS. Kampania
extend mierzy ten sam potok liczący poprawnie. Praca procesora jest ta sama, ale
twierdzenie „potok detekcji QRS mieści się w 360 Hz" ma pokrycie w danych dopiero
w tej drugiej kampanii.
