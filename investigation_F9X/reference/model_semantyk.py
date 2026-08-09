#!/usr/bin/env python3
"""Dwa modele semantyki `Sqrt(A[0]*C[0]+B[0]*D[0])` nad przeplotem — i to, ktory
z nich odtwarza ktora strone rozjazdu K23 / F9-X.

Skad to sie wzielo
------------------
Rozjazd znaleziony w P6 kampanii K23: RetractorDB i port Flinka zgadzaja sie
w 5 przypadkach na 4496 (0,11%) dla monitora

    SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m1
    FROM ((A>2)#(B>1)) + ((C>2)#(D>1))

Obie strony sa WEWNETRZNIE spojne (cztery profile RetractorDB daja identyczne
wartosci; FLINK_NATURAL i FLINK_MANUAL tez), wiec rozjazd nie jest bledem
implementacji po zadnej ze stron — jest roznica ODCZYTU tego, co znaczy `A[0]`
wewnatrz monitora, ktorego `FROM` jest strumieniem PRZEPLECIONYM.

Ten skrypt nie rozstrzyga, ktory odczyt jest poprawny. Rozstrzyga tylko, ktory
odczyt KTORA strona realizuje — a to jest fakt sprawdzalny i sprawdzony ponizej
na calej serii, nie na kilku pierwszych slotach.

Model L ("latch per strumien") — realizowany przez port Flinka
--------------------------------------------------------------
Kazdy ze strumieni skladowych ma wlasna, ostatnio widziana wartosc. Slot
przeplotu wnosi wartosc DOKLADNIE JEDNEGO skladnika; pozostale zachowuja
poprzednia. Przed pierwszym wystapieniem skladnika jego wartosc to 0.
`A[0]` i `B[0]` sa wtedy ROZROZNIALNE.

Model S ("wartosc strumienia przeplecionego") — realizowany przez RetractorDB
-----------------------------------------------------------------------------
Po przeplocie tozsamosc skladnikow zanika: `A[0]` i `B[0]` odwzorowuja sie na
te sama wielkosc, czyli biezaca wartosc strumienia `A#B`. Analogicznie `C[0]`
i `D[0]` na biezaca wartosc `C#D`. Program pola degeneruje sie do
`Sqrt(2 * HAB[0] * HCD[0])`.

Konsekwencja, ktora trzeba nazwac wprost: w modelu S zapytanie
`Sqrt(A[0]*C[0]+B[0]*D[0])` NIE MOZE wyrazic tego, co autor napisal — dwa rozne
odwolania daja tozsamy wynik. To jest material do decyzji o naprawie, nie sama
decyzja.
"""

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = Path("/home/michal/github/rdb-experiment/results_20260808_K23v2")
sys.path.insert(0, str(CAMPAIGN))
import oracle_values as ov  # noqa: E402


def read_source(name):
    return [int(line) for line in (CAMPAIGN / "data" / "main" / name).read_text().split()]


def interleave(fast, slow):
    """Przeplot 1/100 z 1/50 tak, jak robi to silnik: na kazdy slot przypada
    wartosc jednego skladnika, w stosunku 2:1 na korzysc szybszego, a slot
    zerowy nalezy do wolniejszego. Ksztalt odczytany z ARTEFAKTU SILNIKA
    (`STREAM_HASH_A_B`), nie zalozony — `--gate` ponizej to sprawdza.

    Zwraca liste (tag, wartosc), gdzie tag to 'f' albo 's'.
    """
    out, i, j = [], 0, 0
    while i < len(fast) and j < len(slow):
        out.append(("s", slow[j])); j += 1
        if i < len(fast): out.append(("f", fast[i])); i += 1
        if i < len(fast): out.append(("f", fast[i])); i += 1
    return out


def model_L(hab, hcd):
    """Latch per strumien skladowy — odczyt portu Flinka."""
    a = b = c = d = 0
    out = []
    for (tag_ab, v_ab), (tag_cd, v_cd) in zip(hab, hcd):
        if tag_ab == "f": a = v_ab
        else: b = v_ab
        if tag_cd == "f": c = v_cd
        else: d = v_cd
        out.append(int(math.isqrt(a * c + b * d)))
    return out


def model_S(hab, hcd):
    """Tozsamosc skladnikow zanika po przeplocie — odczyt RetractorDB."""
    return [int(math.isqrt(2 * v_ab * v_cd)) for (_, v_ab), (_, v_cd) in zip(hab, hcd)]


def main():
    A = read_source("front_vib.txt"); B = read_source("front_cur.txt")
    C = read_source("rear_vib.txt");  D = read_source("rear_cur.txt")
    hab, hcd = interleave(A, B), interleave(C, D)

    # Bramka ksztaltu przeplotu wobec ARTEFAKTU SILNIKA — zanim porownamy
    # cokolwiek innego. Bez niej model odtwarzalby wlasne zalozenie.
    probe = HERE / "probe_sub" / "temp"
    if probe.exists():
        eng = [x[0] for x in ov.read_rdb_stream(str(probe), "STREAM_HASH_A_B")["records"]]
        mine = [v for _, v in hab][:len(eng)]
        n = min(len(eng), len(mine))
        assert eng[:n] == mine[:n], "przeplot modelu NIE zgadza sie z artefaktem silnika"
        print(f"  bramka ksztaltu przeplotu wobec STREAM_HASH_A_B: zgodna na {n} rekordach")

    rdb = [x[0] for x in ov.read_rdb_stream(str(HERE / "rdb_run" / "temp"), "m1")["records"]]
    fl = [v[0] for _, v in ov.read_flink_csv(str(HERE / "flink_run" / "f9x_m1.csv"))]

    L, S = model_L(hab, hcd), model_S(hab, hcd)

    print(f"\n{'porownanie':38s} {'okno':>6s} {'zgodnych':>9s} {'udzial':>8s}")
    for label, left, right in (
        ("RetractorDB  ~ model S",      rdb, S),
        ("RetractorDB  ~ model L",      rdb, L),
        ("Flink natural ~ model L",     fl,  L),
        ("Flink natural ~ model S",     fl,  S),
        ("RetractorDB  ~ Flink natural", rdb, fl),
    ):
        w = min(len(left), len(right))
        same = sum(1 for i in range(w) if left[i] == right[i])
        print(f"  {label:36s} {w:6d} {same:9d} {100 * same / w:7.2f}%")

    print(f"\n  pierwsze 8 slotow")
    print(f"    RetractorDB : {rdb[:8]}")
    print(f"    model S     : {S[:8]}")
    print(f"    Flink       : {fl[:8]}")
    print(f"    model L     : {L[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
