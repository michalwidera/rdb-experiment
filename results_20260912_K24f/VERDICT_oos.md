# H10 — werdykt regulą decyzyjną, bez odniesienia

Korpus: **10010 planów**, **36089 obserwacji węzłowych**. Ziarno **20260913**, silnik `098e531`.

Progi pochodzą z predeklaracji K24 §6 i są w kodzie stałymi. Ten plik nie
porównuje się z żadną tablicą odniesienia — orzeka o silniku, nie o regresji.

## H10a — dokładność rachunku, per klasa operatora

| Klasa | Węzłów | Ogon (izol.) | Reżim ogona | Origin (izol.) | Reżim origin | Werdykt |
|---|---:|---:|---|---:|---|---|
| `HASH` | 5742 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5363 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `PASS` | 4721 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4219 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `SUB` | 4212 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3379 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2594 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `THETA` | 2587 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `ADD` | 2503 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |
| `WINDOW` | 769 | 100.0% | dokładna | 100.0% | dokładna | **wsparta** |

**H10a: WSPARTA** — 10/10 klas dokładnych w obu wielkościach jednocześnie.

## H10b — wystarczalność reguły lokalnej

**H10b: WSPARTA** — rozjazd 52.9% (prog 5%), dodatnie 2200/2200, postac 2200/2200

| Kontrola negatywna | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| plany bez `#` | 7990 | 0 | przeszła |
| HC_SINGLE (operatory bez własnego ogona) | 3719 | 0 | przeszła |
