#!/usr/bin/env python3
"""Komparator kanonicznych strumieni K22 (PREDECLARATION.md §5).

Porównuje strumienie kanoniczne trzech modeli dla jednej rodziny/wariantu
i orzeka o równoważności wartości. Tolerancja numeryczna: ZERO — arytmetyka
jest całkowita, więc tolerancja byłaby przyznaniem, że porty nie realizują
tej samej semantyki (PREDECLARATION.md §5.4).

Format wejścia (bez nagłówka):
    family,variant,logical_index,field_name,value,is_null,is_gap

Użycie:
    compare.py --tail rql=234 --tail python=234 --tail flink=234 \\
               --span 2000 rql=a.csv python=b.csv flink=c.csv
"""
import argparse
import csv
import sys
from collections import OrderedDict

FIELDS = ["family", "variant", "logical_index", "field_name", "value", "is_null", "is_gap"]


class OracleError(Exception):
    """Błąd aparatury — NIE jest wynikiem negatywnym, tylko awarią pomiaru."""


def load(path):
    """Wczytuje strumień kanoniczny -> OrderedDict[index] = lista (field, value, null, gap).

    Kolejność pól w obrębie jednego indeksu jest ISTOTNA (PREDECLARATION.md §5.1)
    i jest tu zachowana.
    """
    rows = OrderedDict()
    with open(path, newline="", encoding="utf-8") as fh:
        for lineno, rec in enumerate(csv.reader(fh), start=1):
            if not rec or (rec and rec[0].startswith("#")):
                continue
            if len(rec) != len(FIELDS):
                raise OracleError(f"{path}:{lineno}: oczekiwano {len(FIELDS)} kolumn, jest {len(rec)}")
            r = dict(zip(FIELDS, rec))
            try:
                idx = int(r["logical_index"])
            except ValueError as exc:
                raise OracleError(f"{path}:{lineno}: logical_index nie jest liczba: {r['logical_index']}") from exc
            if r["is_null"] not in ("0", "1") or r["is_gap"] not in ("0", "1"):
                raise OracleError(f"{path}:{lineno}: is_null/is_gap musza byc 0 albo 1")
            if r["is_null"] == "1" and r["value"] != "":
                raise OracleError(f"{path}:{lineno}: is_null=1 wymaga pustego value (PREDECLARATION.md §5.1)")
            rows.setdefault(idx, []).append((r["field_name"], r["value"], r["is_null"], r["is_gap"]))
    if not rows:
        raise OracleError(f"{path}: strumien pusty — zero porownanych rekordow jest bledem, nie wynikiem")
    return rows


def compare(streams, tails, span):
    """Porównuje modele w zakresie [T, T+span), gdzie T = max(tail).

    Zwraca (verdict, detail, range_from, range_to, rows_compared).
    """
    if len(streams) < 2:
        raise OracleError("porownanie wymaga co najmniej dwoch modeli")
    missing = set(streams) - set(tails)
    if missing:
        raise OracleError(f"brak zadeklarowanego tail dla: {sorted(missing)}")

    start = max(tails[m] for m in streams)
    stop = start + span
    models = list(streams)
    ref = models[0]

    compared = 0
    for idx in range(start, stop):
        rows_ref = streams[ref].get(idx)
        if rows_ref is None:
            return ("FAIL", f"model {ref}: brak indeksu {idx} w zakresie porownania (luka)", start, stop, compared)
        for field, _value, _null, gap in rows_ref:
            if gap == "1":
                return ("FAIL", f"model {ref}: is_gap=1 w indeksie {idx}, pole {field} — luka w zakresie porownania",
                        start, stop, compared)
        for other in models[1:]:
            rows_oth = streams[other].get(idx)
            if rows_oth is None:
                return ("FAIL", f"model {other}: brak indeksu {idx} w zakresie porownania (luka)",
                        start, stop, compared)
            if len(rows_ref) != len(rows_oth):
                return ("FAIL",
                        f"indeks {idx}: rozna liczba pol — {ref}={len(rows_ref)}, {other}={len(rows_oth)}",
                        start, stop, compared)
            for pos, (a, b) in enumerate(zip(rows_ref, rows_oth)):
                if a != b:
                    return ("FAIL",
                            f"indeks {idx}, pozycja pola {pos}: {ref}={a} vs {other}={b}",
                            start, stop, compared)
        compared += 1

    if compared == 0:
        raise OracleError("zero porownanych rekordow — blad aparatury, nie wynik")
    return ("PASS", "", start, stop, compared)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Komparator kanonicznych strumieni K22.")
    ap.add_argument("--tail", action="append", default=[], metavar="MODEL=N",
                    help="ogon odczytany z silnika (xretractor -t); NIE wyliczany recznie")
    ap.add_argument("--span", type=int, default=2000, help="zamrozony zakres porownania w slotach")
    ap.add_argument("streams", nargs="+", metavar="MODEL=PLIK")
    args = ap.parse_args(argv)

    tails = {}
    for item in args.tail:
        model, _, val = item.partition("=")
        tails[model] = int(val)

    streams = {}
    for item in args.streams:
        model, _, path = item.partition("=")
        if not path:
            ap.error(f"oczekiwano MODEL=PLIK, dostano {item!r}")
        streams[model] = load(path)

    verdict, detail, start, stop, compared = compare(streams, tails, args.span)
    print(f"verdict={verdict} range=[{start},{stop}) rows_compared={compared}")
    if detail:
        print(f"first_mismatch: {detail}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OracleError as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
