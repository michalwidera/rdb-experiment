#!/usr/bin/env python3
"""Generator rodzin workloadów K6.

Konstrukcje rodzin W1–W8 są **niezmienione** względem K5
(`results_20260729_K5_rerun/generate.py`); różni je wyłącznie mnożnik rate'u
`--scale`, bo K5 był compile-only, a K6 mierzy czas. Warunek reguły R1
`i·Δ_A = k·Δ_B` jest niezmienniczy na skalowanie, więc mnożnik nie zmienia
struktury planu — sprawdza to kontrola wejściowa `check_counters.py`, porównując
`net`, `r1` i `r2` z tabelą werdyktu K5.

W9 jest nowa w K6: jedyna rodzina, w której odpala R2. Bez niej atrybucja
kosztowa R2 (luka G14) pozostałaby otwarta.

Każdy przypadek to katalog z `query.rql`, kompletem plików danych oraz
opcjonalnym `external_data.txt` wskazującym duże pliki wejściowe do dostarczenia
z repozytorium kodu (wyłącznie do odczytu, **kopiowane** — nie symlinkowane).
"""
import argparse
import json
from fractions import Fraction
from pathlib import Path

Q_VALUES = [1, 2, 4, 8, 16, 32]
DEPTHS = [1, 2, 3]
DEPTH_Q = 8

# Drabina rate'u v2 (README K6b). Rozszerzona o `3` i `1` względem v1, bo rodziny
# z kosztem stałym co-slot (W4, okno `@(1,30)`) nie mieszczą się w budżecie przy
# żadnym szczeblu v1 — to był powód upadku kalibracji K6.0.
LADDER = [36, 24, 12, 6, 3, 1]

HEADER = "STORAGE 'temp'\nSUBSTRAT 'memory'\n"

# Strumienie bazowe K5: i * delta_A = k * delta_B dla (i,k) = (2,1).
# Rate pomiarowy powstaje przez przemnożenie obu częstotliwości przez `scale`;
# proporcja Δ_B/Δ_A = 2 zostaje, więc warunek reguły też.
BASE_FA = 10
BASE_FB = 5

# Liczba wierszy danych. Najszybszym czytnikiem jest A (f_A = 10·scale Hz);
# przy scale = 36 i budżecie 8 s przebiegu potrzeba 2880 wierszy. 8000 pokrywa
# ponad 22 s, więc żaden przebieg nie dobija do końca pliku — czytanie poza
# koniec danych zaczyna indeksować od zera (§3.2 planu) i zafałszowałoby wynik.
ROWS = 8000

# W9: liczba pól na strumień. Program pól `wa[_]*wb[_]` wykonuje tyle mnożeń na
# slot, więc to ten parametr decyduje o koszcie wspólnego substratu.
W9_FIELDS = 16


def rational(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def hash_interval(left: Fraction, right: Fraction) -> Fraction:
    """Interwał przeplotu: częstotliwości się sumują."""
    return 1 / (1 / left + 1 / right)


class Rates:
    """Interwały bazowe dla zadanego mnożnika rate'u."""

    def __init__(self, scale: int) -> None:
        if scale < 1:
            raise ValueError("scale musi być dodatnie")
        self.scale = scale
        self.delta_a = Fraction(1, BASE_FA * scale)
        self.delta_b = Fraction(1, BASE_FB * scale)
        self.delta_phi = hash_interval(self.delta_a, self.delta_b)

    def declarations(self) -> str:
        return (
            f"DECLARE value INTEGER STREAM A, {rational(self.delta_a)} FILE 'a.txt'\n"
            f"DECLARE value INTEGER STREAM B, {rational(self.delta_b)} FILE 'b.txt'\n"
        )


def small_data() -> dict[str, str]:
    a = "\n".join(str(i) for i in range(1, ROWS + 1)) + "\n"
    b = "\n".join(str(1000 + i) for i in range(1, ROWS + 1)) + "\n"
    return {"a.txt": a, "b.txt": b}


def w9_data() -> dict[str, str]:
    """Dane szerokie: W9_FIELDS wartości w wierszu, po jednym pliku na stronę."""
    rows_a = []
    rows_b = []
    for i in range(1, ROWS + 1):
        rows_a.append(" ".join(str(i + k) for k in range(W9_FIELDS)))
        rows_b.append(" ".join(str(1000 + i + k) for k in range(W9_FIELDS)))
    return {"wa.txt": "\n".join(rows_a) + "\n", "wb.txt": "\n".join(rows_b) + "\n"}


def w1(r: Rates) -> str:
    return HEADER + r.declarations() + "SELECT * STREAM w1_out FROM (A>2)#(B>1)\n"


def w2(r: Rates, q: int) -> str:
    body = "".join(f"SELECT * STREAM w2_out_{j:03d} FROM (A>2)#(B>1)\n" for j in range(q))
    return HEADER + r.declarations() + body


def w3(r: Rates, depth: int) -> str:
    """Zagnieżdżone przepisanie: każdy poziom dokłada strumień o interwale 2*delta_phi."""
    declarations = r.declarations()
    expression = "(A>2)#(B>1)"
    interval = r.delta_phi
    for level in range(1, depth):
        name = f"S{level}"
        # Warunek reguły dla (i,k) = (2,1): 2 * delta_phi = 1 * delta_S.
        delta = 2 * interval
        declarations += f"DECLARE value INTEGER STREAM {name}, {rational(delta)} FILE 'a.txt'\n"
        expression = f"(({expression})>2)#({name}>1)"
        interval = hash_interval(interval, delta)
    body = "".join(f"SELECT * STREAM w3_out_{j:03d} FROM {expression}\n" for j in range(DEPTH_Q))
    return HEADER + declarations + body


def w4(r: Rates, q: int) -> str:
    """Kosztowny operator za wspólnym podplanem (§9.2)."""
    body = ""
    for j in range(q):
        body += (
            f"SELECT * STREAM w4_out_{j:03d} FROM (A>2)#(B>1)\n"
            f"SELECT w4_out_{j:03d}[0] STREAM w4_p_{j:03d} FROM w4_out_{j:03d}\n"
            f"SELECT * STREAM w4_win_{j:03d} FROM w4_p_{j:03d}@(1,30)\n"
            f"SELECT w4_win_{j:03d}[0] STREAM w4_avg_{j:03d} FROM w4_win_{j:03d}.avg\n"
        )
    return HEADER + r.declarations() + body


def w5(r: Rates, q: int) -> str:
    """Kontrola negatywna: brak wspólności i brak przesunięć."""
    declarations = ""
    body = ""
    for j in range(q):
        declarations += (
            f"DECLARE value INTEGER STREAM w5a_{j:03d}, {rational(r.delta_a)} FILE 'a.txt'\n"
            f"DECLARE value INTEGER STREAM w5b_{j:03d}, {rational(r.delta_b)} FILE 'b.txt'\n"
        )
        body += f"SELECT * STREAM w5_out_{j:03d} FROM w5a_{j:03d}#w5b_{j:03d}\n"
    return HEADER + declarations + body


def w6(r: Rates, q: int) -> str:
    """Near-miss: 1 * delta_A != 1 * delta_B, więc warunek reguły nie zachodzi."""
    body = "".join(f"SELECT * STREAM w6_out_{j:03d} FROM (A>1)#(B>1)\n" for j in range(q))
    return HEADER + r.declarations() + body


def w7(r: Rates, q: int) -> str:
    """Przesunięcia zmaterializowane jako strumienie publiczne blokują regułę."""
    body = "SELECT * STREAM w7_sa FROM A>2\nSELECT * STREAM w7_sb FROM B>1\n"
    body += "".join(f"SELECT * STREAM w7_out_{j:03d} FROM w7_sa#w7_sb\n" for j in range(q))
    return HEADER + r.declarations() + body


ECG_PIPELINE = """DECLARE MLII INTEGER, V1 INTEGER STREAM ecg, 1/360 FILE 'rec205'
DECLARE bp_coef INTEGER[25] STREAM bpf, 1 FILE 'bp_coef.txt'
DECLARE d_coef INTEGER[5] STREAM df, 1 FILE 'd_coef.txt'

SELECT ecg.MLII STREAM mlii FROM ecg VOLATILE

SELECT * STREAM mlii_win FROM mlii@(1,25) VOLATILE
SELECT mlii_win[_]*bpf[_] STREAM bp_acc FROM mlii_win+bpf VOLATILE
SELECT bp_acc[0]/1000 STREAM bp_out FROM bp_acc.sumc VOLATILE

SELECT * STREAM bp_win FROM bp_out@(1,5) VOLATILE
SELECT bp_win[_]*df[_] STREAM d_acc FROM bp_win+df VOLATILE
SELECT d_acc[0] STREAM d_out FROM d_acc.sumc VOLATILE

SELECT d_out[0]*d_out[0]/1000 STREAM sq_out FROM d_out VOLATILE

SELECT * STREAM mwi_win FROM sq_out@(1,30) VOLATILE
SELECT mwi_win[0] STREAM mwi FROM mwi_win.avg VOLATILE
"""

# Sumaryczne opóźnienie grupowe potoku Pan-Tompkins: 25-tap -> 12, 5-tap -> 2,
# okno całkujące 30 -> 15.
ECG_GROUP_DELAY = 29


def w8(q: int) -> str:
    """Rodzina umotywowana zewnętrznie; rate zamrożony na 360 Hz przez źródło."""
    body = "".join(
        f"SELECT * STREAM mon_{j:03d} FROM (mlii>{ECG_GROUP_DELAY})#(mwi>{ECG_GROUP_DELAY})\n" for j in range(q)
    )
    return HEADER + ECG_PIPELINE + "\n" + body


def w9(r: Rates, q: int) -> str:
    """R2-shaped: `Q` publicznych SELECT-ów o tym samym kosztownym programie pól,
    naprzemiennie nad `wa+wb` i `wb+wa`.

    Pod `STRUCT` deduplikacja strukturalna scala każdą połowę osobno — zostają
    dwa substraty `STREAM_SELECT_*`, każdy wykonujący program raz na slot.
    Kanonizacja odcisku R2 zrównuje dzieci węzła `STREAM_ADD`, więc obie połowy
    trafiają do jednego substratu i program wykonuje się raz.

    `Q = 1` jest przypadkiem zdegenerowanym: nie ma z czym scalać, więc
    `net = 0`. To kontrola, że sama obecność R2 nic nie usuwa.
    """
    fields_a = ", ".join(f"a{k} INTEGER" for k in range(W9_FIELDS))
    fields_b = ", ".join(f"b{k} INTEGER" for k in range(W9_FIELDS))
    declarations = (
        f"DECLARE {fields_a} STREAM wa, {rational(r.delta_a)} FILE 'wa.txt'\n"
        f"DECLARE {fields_b} STREAM wb, {rational(r.delta_b)} FILE 'wb.txt'\n"
    )
    body = ""
    for j in range(q):
        source = "wa+wb" if j % 2 == 0 else "wb+wa"
        body += f"SELECT wa[_]*wb[_] STREAM w9_out_{j:03d} FROM {source}\n"
    return HEADER + declarations + body


def cases(scale: int) -> list[dict[str, object]]:
    r = Rates(scale)
    result: list[dict[str, object]] = []
    result.append({"family": "W1", "case": "W1", "param": "-", "q": 1, "rql": w1(r), "external": [], "data": "small"})
    for q in Q_VALUES:
        result.append(
            {"family": "W2", "case": f"W2_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w2(r, q), "external": [], "data": "small"}
        )
    for depth in DEPTHS:
        result.append(
            {
                "family": "W3",
                "case": f"W3_d{depth}",
                "param": f"d={depth}",
                "q": DEPTH_Q,
                "rql": w3(r, depth),
                "external": [],
                "data": "small",
            }
        )
    for q in Q_VALUES:
        result.append(
            {"family": "W4", "case": f"W4_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w4(r, q), "external": [], "data": "small"}
        )
    for q in Q_VALUES:
        result.append(
            {"family": "W5", "case": f"W5_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w5(r, q), "external": [], "data": "small"}
        )
    for q in Q_VALUES:
        result.append(
            {"family": "W6", "case": f"W6_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w6(r, q), "external": [], "data": "small"}
        )
    for q in Q_VALUES:
        result.append(
            {"family": "W7", "case": f"W7_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w7(r, q), "external": [], "data": "small"}
        )
    for q in Q_VALUES:
        result.append(
            {
                "family": "W8",
                "case": f"W8_Q{q:02d}",
                "param": f"Q={q}",
                "q": q,
                "rql": w8(q),
                "external": [
                    "examples/ecg/rec205/rec205",
                    "examples/ecg/rec205/bp_coef.txt",
                    "examples/ecg/rec205/d_coef.txt",
                ],
                "data": "none",
            }
        )
    for q in Q_VALUES:
        result.append(
            {"family": "W9", "case": f"W9_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w9(r, q), "external": [], "data": "wide"}
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--scale",
        type=int,
        required=True,
        help="mnożnik rate'u z zamrożonej drabiny README v2: 36, 24, 12, 6, 3 albo 1",
    )
    args = parser.parse_args()
    if args.scale not in LADDER:
        parser.error(f"scale musi należeć do zamrożonej drabiny {set(LADDER)}")

    rates = Rates(args.scale)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    narrow = small_data()
    wide = w9_data()

    index: list[dict[str, object]] = []
    for entry in cases(args.scale):
        directory = root / str(entry["case"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "query.rql").write_text(str(entry["rql"]), encoding="utf-8")
        external = list(entry["external"])
        if external:
            (directory / "external_data.txt").write_text("\n".join(external) + "\n", encoding="utf-8")
        payload = {"small": narrow, "wide": wide, "none": {}}[str(entry["data"])]
        for name, content in payload.items():
            (directory / name).write_text(content, encoding="utf-8")
        index.append(
            {
                "family": entry["family"],
                "case": entry["case"],
                "param": entry["param"],
                "q": entry["q"],
                "external": external,
            }
        )

    meta = {
        "scale": args.scale,
        "delta_a": rational(rates.delta_a),
        "delta_b": rational(rates.delta_b),
        "delta_phi": rational(rates.delta_phi),
        "f_phi_hz": float(1 / rates.delta_phi),
        "slot_phi_ms": float(rates.delta_phi * 1000),
        "rows": ROWS,
        "w9_fields": W9_FIELDS,
        "note": "W8 nie podlega skalowaniu — rate zamrożony na 360 Hz przez deklarację źródła rec205.",
    }
    (root / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (root / "rates.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(index)} przypadków w {root}; scale={args.scale}, f_phi={meta['f_phi_hz']:.1f} Hz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
