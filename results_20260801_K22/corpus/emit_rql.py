#!/usr/bin/env python3
"""Harness RQL: artefakty silnika -> strumień kanoniczny K22 (PREDECLARATION.md §5.1).

To jest APARATURA, nie rdzeń: nie realizuje żadnej logiki monitora, tylko
przekłada zapisane artefakty na wspólny format porównania. Nie ma tu znaczników
CORE_BEGIN/CORE_END, więc skrypt metryk nigdy tego nie policzy.

Mapowanie indeksu (ustalone pomiarem, PREDECLARATION.md §11.1 E2):
    logical_index = tail + numer_rekordu
Silnik wycisza emisję przez pierwsze `tail` slotów (dataModel.cpp:167), więc
rekord 0 artefaktu leży w slocie `tail`.
"""
import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

TYPE_FMT = {"INTEGER": ("<i", 4), "UINT": ("<I", 4), "BYTE": ("<B", 1),
            "FLOAT": ("<f", 4), "DOUBLE": ("<d", 8)}

DESC_FIELD = re.compile(r"^\s*(\w+)\s+(\S+)\s*$")


class EmitError(Exception):
    """Błąd aparatury — nie jest wynikiem."""


def parse_desc(path):
    """Zwraca listę (nazwa, format_struct, rozmiar) z pliku .desc."""
    fields = []
    # Format .desc: '{' stoi w tej samej linii co pierwsze pole, '}' zamyka
    # ostatnią. Nawiasy są usuwane przed dopasowaniem, nie traktowane jako
    # osobne wiersze.
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("{").rstrip("}").strip()
        if not line:
            continue
        m = DESC_FIELD.match(line)
        if not m:
            raise EmitError(f"{path}: nierozpoznany wiersz deskryptora: {line!r}")
        rtype, name = m.group(1), m.group(2)
        if rtype not in TYPE_FMT:
            raise EmitError(f"{path}: nieobslugiwany typ {rtype} (pole {name})")
        fmt, size = TYPE_FMT[rtype]
        fields.append((name, fmt, size))
    if not fields:
        raise EmitError(f"{path}: deskryptor bez pol")
    return fields


def assert_no_nulls(stream_path):
    """Sprawdza raportem silnika, że artefakt nie zawiera nulli ani luk.

    Emiter nie parsuje `.meta` — jego format nie został zweryfikowany, a
    zgadywanie formatu metadanych po to, żeby wypełnić kolumny `is_null`
    i `is_gap`, byłoby dokładnie tym błędem, który K6c popełnił z interwałem
    slotu: rachunkiem obok systemu zamiast odczytem z niego. Zamiast tego
    pytamy silnik i ZATRZYMUJEMY SIĘ, jeżeli nulle są obecne — wtedy trzeba
    najpierw ustalić format `.meta`, a nie wypisać zera.
    """
    out = subprocess.run(["xtrdb", "-n", "-s", str(stream_path)],
                         capture_output=True, text=True, check=False).stdout
    if "no nulls" not in out:
        raise EmitError(
            f"{stream_path}: artefakt zawiera nulle albo luki, a emiter ich nie "
            f"odwzorowuje. Ustalic format .meta przed dalszym porownaniem.\n{out}")


def emit(stream_path, family, variant, tail, limit, out_fh):
    desc = parse_desc(f"{stream_path}.desc")
    assert_no_nulls(stream_path)
    record_size = sum(size for _n, _f, size in desc)
    data = Path(stream_path).read_bytes()
    if len(data) % record_size:
        raise EmitError(f"{stream_path}: {len(data)} B nie dzieli sie przez rekord {record_size} B")
    count = len(data) // record_size
    if count == 0:
        raise EmitError(f"{stream_path}: zero rekordow — blad aparatury, nie wynik")
    if limit and count < limit:
        raise EmitError(f"{stream_path}: {count} rekordow, zadano {limit}; "
                        f"zwieksz -m (patrz PREDECLARATION.md §11.1 E2)")
    n = min(count, limit) if limit else count
    for r in range(n):
        offset = r * record_size
        for name, fmt, size in desc:
            value = struct.unpack(fmt, data[offset:offset + size])[0]
            offset += size
            out_fh.write(f"{family},{variant},{tail + r},{name},{value},0,0\n")
    return n


def main():
    ap = argparse.ArgumentParser(description="Artefakty RQL -> strumien kanoniczny K22.")
    ap.add_argument("--stream", required=True, help="sciezka do artefaktu, np. temp/f1_out")
    ap.add_argument("--family", required=True)
    ap.add_argument("--variant", default="base")
    ap.add_argument("--tail", type=int, required=True,
                    help="odczytany z 'xretractor <plan>.rql -c', NIE wyliczony")
    ap.add_argument("--limit", type=int, default=0, help="ile rekordow wypisac (0 = wszystkie)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.out, "w", encoding="utf-8") as fh:
        n = emit(args.stream, args.family, args.variant, args.tail, args.limit, fh)
    print(f"{args.out}: {n} rekordow, logical_index {args.tail}..{args.tail + n - 1}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except EmitError as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
