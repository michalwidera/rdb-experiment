#!/usr/bin/env python3
"""P7 — ocena drabiny rate'ow wobec kryterium PREDEKLARACJI §8.1.

Kryterium
---------
„Najgorszy profil RetractorDB przy Q=32 ma `p99 <= 50%` logicznego slotu."
Logicznym slotem jest NAJKROTSZY odstep miedzy kolejnymi pobudkami petli, bo
w nim silnik ma najmniej czasu, a obliczenie wykonuje sie w kazdym slocie.
Wartosc bierze sie z `slots.tsv`, ktore powstalo z `slot_grid` — czyli z klasy
`TimeLine` SILNIKA, nie z przepisania regul osi czasu.

Czego ten skrypt NIE liczy
--------------------------
Zadnego ilorazu `DEFAULT/ablacja`. Profile wchodza wylacznie przez `max`, bo
tego zada §8.1 („najgorszy profil"). To jest tresc pola `calibration_saw_effect`
w ANEKS-1 i powod, dla ktorego kalibracja moze biec przed macierza.

Percentyl liczony metoda najblizszego rangu, bez interpolacji — tak samo jak
`verdict.py` i `examples/ecg/e1_stats.py`, zeby aparatura lucznie sie nie
rozjezdzala.

Transjentu startowego NIE odrzucamy. Kierunek jest zachowawczy: pierwsze sloty
sa najdrozsze, wiec ich zostawienie moze kalibracje tylko UTRUDNIC.
"""

import argparse
import csv
import sys
from pathlib import Path

PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
FAMILIES = ["F9_R2", "F9_R1", "F9_X"]
SCALES = ["1_4", "1_2", "1_1", "2_1", "4_1"]

#: §8.1 — udzial slotu, ktorego p99 nie moze przekroczyc.
BUDGET_FRACTION = 0.50


def scale_label(tag):
    num, den = tag.split("_")
    return num if den == "1" else f"{num}/{den}"


def percentile(values_sorted, p):
    """Percentyl metoda najblizszego rangu (bez interpolacji)."""
    idx = min(len(values_sorted) - 1, int(p * len(values_sorted)))
    return values_sorted[idx]


def read_compute_ms(path):
    out = []
    with path.open() as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header or header[1] != "compute_ns":
            raise SystemExit(f"BLAD: {path} nie ma kolumny compute_ns")
        for row in reader:
            out.append(int(row[1]) / 1e6)
    if not out:
        raise SystemExit(f"BLAD: {path} jest pusty")
    return sorted(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", required=True, help="katalog z <profil>/<rodzina>_s<skala>/slot.csv")
    parser.add_argument("--slots", default=str(Path(__file__).resolve().parent / "slots.tsv"))
    args = parser.parse_args()

    slots = {}
    with open(args.slots) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            slots[(row["family"], row["scale"])] = float(row["min_slot_ms"])

    runs = Path(args.runs)
    verdict_rows = []

    for scale in SCALES:
        print(f"\n=== rate_scale = {scale_label(scale)} ===")
        scale_ok = True
        for family in FAMILIES:
            slot = slots[(family, scale)]
            budget = BUDGET_FRACTION * slot
            worst_p99, worst_max = 0.0, 0.0
            per_profile = []
            for profile in PROFILES:
                csv_path = runs / profile / f"{family}_s{scale}" / "slot.csv"
                if not csv_path.exists():
                    raise SystemExit(f"BLAD: brak {csv_path} — przebieg niepelny")
                values = read_compute_ms(csv_path)
                p99 = percentile(values, 0.99)
                per_profile.append(p99)
                worst_p99 = max(worst_p99, p99)
                worst_max = max(worst_max, values[-1])
            passed = worst_p99 <= budget
            scale_ok = scale_ok and passed
            print(f"  {family:7s} slot {slot:8.3f} ms  budzet {budget:7.3f} ms  "
                  f"najgorszy p99 {worst_p99:7.3f} ms  ({100 * worst_p99 / slot:5.1f}% slotu)  "
                  f"{'OK' if passed else 'PRZEKROCZONY'}")
            print(f"          p99 per profil [ms]: " +
                  "  ".join(f"{p:.3f}" for p in per_profile) + f"   max {worst_max:.3f}")
        print(f"  --> rate_scale {scale_label(scale)}: "
              f"{'SPELNIA kryterium §8.1' if scale_ok else 'ODRZUCONY przez kryterium §8.1'}")
        verdict_rows.append((scale, scale_ok))

    accepted = [s for s, ok in verdict_rows if ok]
    rejected = [s for s, ok in verdict_rows if not ok]
    print("\n" + "=" * 74)
    print(f"ODRZUCONE (za szybkie): {', '.join(scale_label(s) for s in rejected) or '(zadne)'}")
    print(f"SPELNIAJACE          : {', '.join(scale_label(s) for s in accepted) or '(zadne)'}")
    if not accepted:
        print("BRAK skali spelniajacej kryterium — kalibracja nie ma wyniku.")
        return 2
    # Najszybszy dopuszczalny rate, czyli najmniejszy czynnik z tych, ktore
    # przeszly. Wolniejszy rate zawsze przechodzi, wiec wybor "najmniejszy
    # przechodzacy" jest jedynym, ktory nie jest arbitralny.
    chosen = min(accepted, key=lambda s: int(s.split("_")[0]) / int(s.split("_")[1]))
    print(f"WYBRANY rate_scale   : {scale_label(chosen)} (najmniejszy czynnik spelniajacy kryterium)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
