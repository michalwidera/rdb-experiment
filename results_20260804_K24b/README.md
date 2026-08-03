# K24b — ramię (b) H10: nielokalność reguły lokalnej

Krok 3b ścieżki `paper-arXiv/debs/research_plan.md` §16.1, kroki b1–b5 z §15.
Badanie deterministyczne, **bez silnika**: porównuje naturalną regułę lokalną
z prawdziwym ogonem z modelu zdarzeniowego (oracle).

| Dokument | Zawartość |
|---|---|
| [PREDECLARATION.md](PREDECLARATION.md) | decyzja o regule lokalnej, populacja, kryteria, ziarna — zamrożone przed przebiegiem |
| [REPORT.md](REPORT.md) | wynik, co trzeba było naprawić, znalezisko o `#`, zagrożenia trafności |
| `run_member_b.py` | jedyny skrypt: liczy trzy kryteria i dwie kontrole negatywne |
| `raw/` | surowe CSV obu ziaren |

## Wynik w jednym zdaniu

Naturalna reguła lokalna zaniża prawdziwy ogon dokładnie o `ceil((p+q-1)/p)`
dla węzłów `#` o obu składowych deklarowanych — 2323/2323 na korpusie roboczym
i **2310/2310 na korpusie potwierdzającym**, przy gęstości rozjazdu ~53% planów
i zerowych kontrolach negatywnych. **H10b wsparta.**

## Odtworzenie

```bash
python3 run_member_b.py --seed 20260803   # korpus roboczy
python3 run_member_b.py --seed 20260805   # potwierdzenie poza próbą
```

Sekundy liczenia, bez silnika i bez workera.
