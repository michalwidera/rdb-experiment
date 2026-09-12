# H10 — werdykt regulą decyzyjną, bez odniesienia

Korpus: **10010 planów**, **36162 obserwacji węzłowych**. Ziarno **20260912**, silnik `098e531`.

Progi pochodzą z predeklaracji K24 §6 i są w kodzie stałymi. Ten plik nie
porównuje się z żadną tablicą odniesienia — orzeka o silniku, nie o regresji.

## H10a — dokładność rachunku, per klasa operatora

| Klasa | Węzłów | Ogon (izol.) | Reżim ogona | Origin (izol.) | Reżim origin | Werdykt |
|---|---:|---:|---|---:|---|---|
| `HASH` | 5755 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5280 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `PASS` | 4711 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `SUB` | 4354 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4301 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3256 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `THETA` | 2619 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2609 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `ADD` | 2493 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `WINDOW` | 784 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |

**H10a: WSPARTA** — 10/10 klas dokładnych w obu wielkościach jednocześnie.

## H10b — wystarczalność reguły lokalnej

**H10b: WSPARTA** — rozjazd 53.0% (prog 5%), dodatnie 2276/2276, postac 2276/2276

| Kontrola negatywna | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| plany bez `#` | 7881 | 0 | przeszła |
| HC_SINGLE (operatory bez własnego ogona) | 3640 | 0 | przeszła |
