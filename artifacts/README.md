# Artefakty kampanii

Dowody objętościowe czterech kampanii łuku H9, trzymane **w repozytorium**,
żeby przetrwały zmianę maszyny. Powstał 2026-08-16, gdy te pliki leżały luzem
w katalogach domowych hosta i workera.

Reguła nadrzędna jest w [`../README.md`](../README.md), sekcja „Artefakty poza
gitem — gdzie wolno pisać": aparatura nie pisze do katalogu domowego, a to, co
wytworzy, ma trafić pod kontrolę repozytorium.

## Postać przechowywania

Drzewa katalogów są spakowane, bo kompresują się 20-krotnie (bramki RDB:
27 MB → 1,3 MB). Rozpakowywać **poza repozytorium**:

```bash
tar xzf artifacts/K26v3/k26v3_gates_rdb.tar.gz -C /tmp
```

Spakowane trzymają tylko oryginalne drzewa; archiwa sond P8 (`*_archives/`)
zostają w postaci, w jakiej wyszły z workera, bo są już skompresowane.

**Rozpakowanych kopii archiwów P8 tu nie ma i nie ma ich odtwarzać do
repozytorium.** Poprzednie `k26v3_p9/raw/` i `k26v2_p9/raw/` (2 × 659 MB) były
bajtowo tym samym co archiwa — sprawdzono sumą sum przed usunięciem. Wejścia
werdyktu (`*_p9/matrix/`) zostają, bo są małe i to one karmią `verdict.py`.

## Mapa

| Katalog | Kampania | Werdykt | Co zawiera |
|---|---|---|---|
| `K23v2/` | K23 iteracja 2, `results_20260808_K23v2/` | brak — `apparatus` | bramki Flinka; `k23v2_worker_evidence` = bramki i kalibracja odzyskane z workera 2026-08-16, **jedyna kopia** |
| `K26/` | K26, `results_20260809_K26/` | brak — `apparatus` | bramki, kalibracja; `k26_p8_partial` = 9/480 komórek sprzed awarii SSH, **jedyna kopia** |
| `K26v2/` | K26v2, `results_20260810_K26v2/` | **BRAK WERDYKTU** | archiwa pełnej macierzy 1440/1440, bramki, kalibracja, dowody STOP-8, wejścia werdyktu |
| `K26v3/` | K26v3, `results_20260814_K26v3/` | **H9 WSPARTA, `Q=8`, 3/3** | archiwa P8, bramki P6, kalibracja P7, `k26v3_control/`, wejścia werdyktu |
| `NIEREJESTROWANE/` | — | — | `k26v2_explore` — patrz niżej |

## Czego nie wolno

* **`NIEREJESTROWANE/k26v2_explore` nie jest dowodem.** Powstał poza
  predeklaracją, żeby rozstrzygnąć „czy warto powtarzać". Liczb stamtąd nie
  wolno cytować w artykule, planie ani w dokumentach kampanii.
* **Danych czterech kampanii nie wolno łączyć.** Każda ma osobną
  predeklarację; jedyna z werdyktem to K26v3.
* `K26v3/k26v3_control/chain.log` i logi rodzin **nie są w archiwach P8** —
  archiwum zawiera wyłącznie `F9-*/raw/…` i `RUN_COMPLETE`. To jedyny zapis osi
  czasu P8 i źródło czasów 16 h 09 / 16 h 10 / 16 h 10, na które powołuje się
  `research_plan.md` §14.21.

## Kontrola spójności

```bash
cd artifacts && sha256sum -c MANIFEST.sha256        # 139 pozycji

# archiwa K26v3 dodatkowo wobec indeksu kampanii w git:
cd K26v3/k26v3_archives && sha256sum -c <(awk 'NR>1 {print $2"  "$1}' \
  ../../../results_20260814_K26v3/K26v3-P8_raw.index.tsv)
```
