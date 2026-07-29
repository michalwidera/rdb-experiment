#!/usr/bin/env python3
"""Generator rodzin workloadów K5.

Każdy przypadek to katalog z `query.rql`, kompletem małych plików danych oraz
opcjonalnym `external_data.txt` wskazującym duże pliki wejściowe do dostarczenia
z repozytorium kodu (wyłącznie do odczytu).

Konstrukcje rodzin i ich przewidywany mechanizm są opisane w README.md i były
zamrożone przed uruchomieniem generatora.
"""
import argparse
import json
from fractions import Fraction
from pathlib import Path

Q_VALUES = [1, 2, 4, 8, 16, 32]
DEPTHS = [1, 2, 3]
DEPTH_Q = 8

HEADER = "STORAGE 'temp'\nSUBSTRAT 'memory'\n"

# Strumienie bazowe: i * delta_A = k * delta_B dla (i,k) = (2,1).
DELTA_A = Fraction(1, 10)
DELTA_B = Fraction(1, 5)

ROWS = 512


def rational(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def hash_interval(left: Fraction, right: Fraction) -> Fraction:
    """Interwał przeplotu: częstotliwości się sumują."""
    return 1 / (1 / left + 1 / right)


def base_declarations() -> str:
    return (
        f"DECLARE value INTEGER STREAM A, {rational(DELTA_A)} FILE 'a.txt'\n"
        f"DECLARE value INTEGER STREAM B, {rational(DELTA_B)} FILE 'b.txt'\n"
    )


def small_data() -> dict[str, str]:
    a = "\n".join(str(i) for i in range(1, ROWS + 1)) + "\n"
    b = "\n".join(str(1000 + i) for i in range(1, ROWS + 1)) + "\n"
    return {"a.txt": a, "b.txt": b}


def w1() -> str:
    return HEADER + base_declarations() + "SELECT * STREAM w1_out FROM (A>2)#(B>1)\n"


def w2(q: int) -> str:
    body = "".join(f"SELECT * STREAM w2_out_{j:03d} FROM (A>2)#(B>1)\n" for j in range(q))
    return HEADER + base_declarations() + body


def w3(depth: int) -> str:
    """Zagnieżdżone przepisanie: każdy poziom dokłada strumień o interwale 2*delta_phi."""
    declarations = base_declarations()
    expression = "(A>2)#(B>1)"
    interval = hash_interval(DELTA_A, DELTA_B)
    for level in range(1, depth):
        name = f"S{level}"
        # Warunek reguły dla (i,k) = (2,1): 2 * delta_phi = 1 * delta_S.
        delta = 2 * interval
        declarations += f"DECLARE value INTEGER STREAM {name}, {rational(delta)} FILE 'a.txt'\n"
        expression = f"(({expression})>2)#({name}>1)"
        interval = hash_interval(interval, delta)
    body = "".join(f"SELECT * STREAM w3_out_{j:03d} FROM {expression}\n" for j in range(DEPTH_Q))
    return HEADER + declarations + body


def w4(q: int) -> str:
    """Kosztowny operator za wspólnym podplanem (§9.2).

    Okno i agregat siedzą w osobnych strumieniach pochodnych, zgodnie z
    brzmieniem planu badawczego. W pierwszej kampanii ten kształt trafiał
    w wadę `resolveStreamIntervals` i musiał być zastąpiony; wada została
    naprawiona w `master` (`Fix (#214)`), więc rodzina wraca do oryginału.
    """
    body = ""
    for j in range(q):
        body += (
            f"SELECT * STREAM w4_out_{j:03d} FROM (A>2)#(B>1)\n"
            f"SELECT w4_out_{j:03d}[0] STREAM w4_p_{j:03d} FROM w4_out_{j:03d}\n"
            f"SELECT * STREAM w4_win_{j:03d} FROM w4_p_{j:03d}@(1,30)\n"
            f"SELECT w4_win_{j:03d}[0] STREAM w4_avg_{j:03d} FROM w4_win_{j:03d}.avg\n"
        )
    return HEADER + base_declarations() + body


def w5(q: int) -> str:
    """Kontrola negatywna: brak wspólności i brak przesunięć."""
    declarations = ""
    body = ""
    for j in range(q):
        declarations += (
            f"DECLARE value INTEGER STREAM w5a_{j:03d}, {rational(DELTA_A)} FILE 'a.txt'\n"
            f"DECLARE value INTEGER STREAM w5b_{j:03d}, {rational(DELTA_B)} FILE 'b.txt'\n"
        )
        body += f"SELECT * STREAM w5_out_{j:03d} FROM w5a_{j:03d}#w5b_{j:03d}\n"
    return HEADER + declarations + body


def w6(q: int) -> str:
    """Near-miss: 1 * delta_A != 1 * delta_B, więc warunek reguły nie zachodzi."""
    body = "".join(f"SELECT * STREAM w6_out_{j:03d} FROM (A>1)#(B>1)\n" for j in range(q))
    return HEADER + base_declarations() + body


def w7(q: int) -> str:
    """Przesunięcia zmaterializowane jako strumienie publiczne blokują regułę."""
    body = "SELECT * STREAM w7_sa FROM A>2\nSELECT * STREAM w7_sb FROM B>1\n"
    body += "".join(f"SELECT * STREAM w7_out_{j:03d} FROM w7_sa#w7_sb\n" for j in range(q))
    return HEADER + base_declarations() + body


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
# okno całkujące 30 -> 15. Monitor porównujący surowy sygnał z obwiednią musi
# wyrównać oba kanały o tę wartość.
ECG_GROUP_DELAY = 29


def w8(q: int) -> str:
    body = "".join(
        f"SELECT * STREAM mon_{j:03d} FROM (mlii>{ECG_GROUP_DELAY})#(mwi>{ECG_GROUP_DELAY})\n"
        for j in range(q)
    )
    return HEADER + ECG_PIPELINE + "\n" + body


def cases() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    result.append({"family": "W1", "case": "W1", "param": "-", "q": 1, "rql": w1(), "external": []})
    for q in Q_VALUES:
        result.append({"family": "W2", "case": f"W2_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w2(q), "external": []})
    for depth in DEPTHS:
        result.append(
            {
                "family": "W3",
                "case": f"W3_d{depth}",
                "param": f"d={depth}",
                "q": DEPTH_Q,
                "rql": w3(depth),
                "external": [],
            }
        )
    for q in Q_VALUES:
        result.append({"family": "W4", "case": f"W4_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w4(q), "external": []})
    for q in Q_VALUES:
        result.append({"family": "W5", "case": f"W5_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w5(q), "external": []})
    for q in Q_VALUES:
        result.append({"family": "W6", "case": f"W6_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w6(q), "external": []})
    for q in Q_VALUES:
        result.append({"family": "W7", "case": f"W7_Q{q:02d}", "param": f"Q={q}", "q": q, "rql": w7(q), "external": []})
    for q in Q_VALUES:
        result.append(
            {
                "family": "W8",
                "case": f"W8_Q{q:02d}",
                "param": f"Q={q}",
                "q": q,
                "rql": w8(q),
                "external": ["examples/ecg/rec205/rec205", "examples/ecg/rec205/bp_coef.txt", "examples/ecg/rec205/d_coef.txt"],
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    data = small_data()

    index: list[dict[str, object]] = []
    for entry in cases():
        directory = root / str(entry["case"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "query.rql").write_text(str(entry["rql"]), encoding="utf-8")
        external = list(entry["external"])
        if external:
            (directory / "external_data.txt").write_text("\n".join(external) + "\n", encoding="utf-8")
        else:
            for name, content in data.items():
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

    (root / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(index)} przypadków w {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
