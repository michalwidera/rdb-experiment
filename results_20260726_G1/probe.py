#!/usr/bin/env python3
"""Sonda obserwowalności planu — dane wejściowe dla luki G1 / kroku K1.

Pytanie: co dokładnie jest obserwowalne w wyniku planu i które z obserwowanych
własności zależą od KSZTAŁTU planu, a nie od zapytania. Sonda uruchamia rodzinę
zapytań różniących się wyłącznie kształtem planu (ta sama denotacja
matematyczna) i zbiera dla każdego z nich pełny obserwowalny artefakt:

    - sekwencję wartości rekordów (plik binarny),
    - status null per rekord (plik .meta, dekodowany bezpośrednio),
    - schemat i nazwy pól (plik .desc),
    - skompilowany plan (xretractor -c).

Porównania są prowadzone PARAMI planów, nie względem oracle'a — K1 rozstrzyga
relację równoważności planów, a nie poprawność bezwzględną (to jest K2).

Kontrole (reguła R-a z research_plan.md §4): pary `add_declared/add_computed`
oraz `shift_declared/shift_declared_copy` MUSZĄ wyjść zgodne. Jeżeli sonda
raportuje rozbieżność także tam, jej wynik jest nieważny — mierzy artefakt
środowiska, nie własność silnika.

Uruchomienie:
    python3 probe.py [--xretractor ŚCIEŻKA] [--json PLIK] [--workdir KATALOG]
"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys

# Kodowanie źródła w wartościach: A[k] = k + 1, B[j] = B_BASE + j. Dzięki temu
# każdy rekord wyniku jednoznacznie wskazuje źródło i indeks rekordu źródłowego.
B_BASE = 1000000
SOURCE_RECORDS = 400
SLOTS = 48
PREVIEW = 14

PREAMBLE = """STORAGE '.'

DECLARE value INTEGER STREAM A, {da} FILE 'a.txt'
DECLARE value INTEGER STREAM B, {db} FILE 'b.txt'
"""

# Pozycje NULL-i (modulo 16) w źródłach A i B dla przypadków z dziedziny z NULL-ami.
# W A jest seria trzech kolejnych (5,6,7) — dłuższa niż próg nullfill (R17 = 2).
NULL_SPEC = ({1, 5, 6, 7}, {2, 11})

# (nazwa, delta_a, delta_b, ciało zapytania[, (NULL-e w A, NULL-e w B)]).
# Badany strumień zawsze nazywa się `probe`, żeby dekodowanie było wspólne.
CASES = [
    # --- operator przesunięcia: źródło deklarowane vs strumień obliczany ---
    ("shift_declared", "1/10", "1/5", "SELECT * STREAM probe FROM A>3\n"),
    (
        "shift_declared_copy",
        "1/10",
        "1/5",
        "SELECT * STREAM probe FROM A>3\n",
    ),
    (
        "shift_computed",
        "1/10",
        "1/5",
        "SELECT A[0]+0 STREAM mid FROM A\n"
        "SELECT * STREAM probe FROM mid>3\n",
    ),
    # --- operator przeplotu: źródła deklarowane vs strumienie obliczane ---
    ("hash_declared", "1/10", "1/5", "SELECT * STREAM probe FROM A#B\n"),
    (
        "hash_computed",
        "1/10",
        "1/5",
        "SELECT A[0]+0 STREAM midA FROM A\n"
        "SELECT B[0]+0 STREAM midB FROM B\n"
        "SELECT * STREAM probe FROM midA#midB\n",
    ),
    # ten sam przeplot nad obliczanymi, ale z DOŁOŻONYM zapytaniem niezwiązanym,
    # które wyzwala regułę R1. `factorMatchedHashTimeMoves()` kończy się
    # `topologicalSort()`, więc odpalenie reguły przywraca porządek zależności
    # zniszczony wcześniej przez sortowanie po interwale w
    # `resolveStreamIntervals()`. Zapytanie `trigger` nie dotyka `probe`.
    (
        "hash_computed_sorted",
        "1/10",
        "1/5",
        "DECLARE value INTEGER STREAM T1, 1/10 FILE 'a.txt'\n"
        "DECLARE value INTEGER STREAM T2, 1/5 FILE 'b.txt'\n"
        "SELECT A[0]+0 STREAM midA FROM A\n"
        "SELECT B[0]+0 STREAM midB FROM B\n"
        "SELECT * STREAM probe FROM midA#midB\n"
        "SELECT * STREAM trigger FROM (T1>2)#(T2>1)\n",
    ),
    # --- tożsamość R1 nad danymi Z NULL-AMI ---
    # Cała dotychczasowa weryfikacja reguły biegła na danych bez NULL-i, więc
    # twierdzenie o zachowaniu wyniku nie obejmowało tej dziedziny. NULL-e są
    # rozłożone tak, by trafiły w oba argumenty przeplotu, w tym seria dłuższa
    # niż próg nullfill (R17 = 2).
    (
        "null_r1_lhs_auto",
        "1/10",
        "1/5",
        "SELECT * STREAM probe FROM (A>2)#(B>1)\n",
        NULL_SPEC,
    ),
    (
        "null_r1_lhs_blocked",
        "1/10",
        "1/5",
        "SELECT * STREAM sA FROM A>2\n"
        "SELECT * STREAM sB FROM B>1\n"
        "SELECT * STREAM probe FROM sA#sB\n",
        NULL_SPEC,
    ),
    (
        "null_r1_rhs",
        "1/10",
        "1/5",
        "SELECT * STREAM probe FROM (A#B)>3\n",
        NULL_SPEC,
    ),
    # kontrola dziedziny z NULL-ami: ten sam plan dwa razy musi dać to samo
    (
        "null_r1_rhs_copy",
        "1/10",
        "1/5",
        "SELECT * STREAM probe FROM (A#B)>3\n",
        NULL_SPEC,
    ),
    # --- kontrola: ten sam podział na wejścia deklarowane/obliczane dla + ---
    ("add_declared", "1/10", "1/10", "SELECT * STREAM probe FROM A+B\n"),
    (
        "add_computed",
        "1/10",
        "1/10",
        "SELECT A[0]+0 STREAM midA FROM A\n"
        "SELECT B[0]+0 STREAM midB FROM B\n"
        "SELECT * STREAM probe FROM midA+midB\n",
    ),
    # --- tożsamość R1: phi(tau_i A, tau_k B) == tau_(i+k) phi(A, B) ---
    # lewa strona zapisana wprost; przy RDB_OPT_FACTOR_...=ON przebieg
    # faktoryzacji przepisuje ją na prawą stronę
    ("r1_lhs_auto", "1/10", "1/5", "SELECT * STREAM probe FROM (A>2)#(B>1)\n"),
    # lewa strona z przesunięciami jako STRUMIENIAMI UŻYTKOWNIKA — przebieg
    # faktoryzacji wymaga substratów (query::isSubstrat), więc się nie odpala;
    # to jest wykonanie planu NIEPRZEPISANEGO bez konieczności przebudowy
    (
        "r1_lhs_blocked",
        "1/10",
        "1/5",
        "SELECT * STREAM sA FROM A>2\n"
        "SELECT * STREAM sB FROM B>1\n"
        "SELECT * STREAM probe FROM sA#sB\n",
    ),
    # prawa strona tożsamości zapisana wprost w RQL
    ("r1_rhs", "1/10", "1/5", "SELECT * STREAM probe FROM (A#B)>3\n"),
]

# Pary planów, które relacja równoważności musi rozstrzygnąć.
# rola: control -> MUSI być zgodne; question -> przedmiot decyzji K1.
PAIRS = [
    ("shift_declared", "shift_declared_copy", "control", "ten sam plan dwa razy"),
    ("add_declared", "add_computed", "control", "+ nad wejściem deklarowanym vs obliczanym"),
    ("shift_declared", "shift_computed", "question", ">N nad wejściem deklarowanym vs obliczanym"),
    ("hash_declared", "hash_computed", "question", "# nad wejściem deklarowanym vs obliczanym"),
    ("hash_computed", "hash_computed_sorted", "question",
     "wpływ SAMEJ kolejności planu: to samo zapytanie, dołożone niezwiązane zapytanie wyzwala topologicalSort"),
    ("hash_declared", "hash_computed_sorted", "question",
     "residuum po przywróceniu porządku: co zostaje niezgodne"),
    ("null_r1_rhs", "null_r1_rhs_copy", "control", "dziedzina z NULL-ami: ten sam plan dwa razy"),
    ("null_r1_lhs_auto", "null_r1_rhs", "question", "R1 nad danymi z NULL-ami: przepisany vs prawa strona"),
    ("null_r1_lhs_blocked", "null_r1_rhs", "question", "R1 nad danymi z NULL-ami: nieprzepisany vs prawa strona"),
    ("r1_lhs_auto", "r1_rhs", "question", "R1: plan przepisany vs prawa strona tożsamości"),
    ("r1_lhs_blocked", "r1_rhs", "question", "R1: plan nieprzepisany vs prawa strona tożsamości"),
    ("r1_lhs_auto", "r1_lhs_blocked", "question", "R1: plan przepisany vs nieprzepisany"),
]


def write_sources(workdir, nulls=None):
    """Zapisuje źródła; `nulls` to para zbiorów pozycji, które mają być NULL-em.

    NULL w źródle tekstowym zapisuje się słowem NULL — tak samo jak w testach
    issue113/issue121. Pozycje powtarzają się co 16 rekordów, żeby NULL-e
    wystąpiły w całym przebiegu, a nie tylko na jego początku.
    """
    nulls_a, nulls_b = nulls if nulls else (set(), set())

    def cell(index, value, null_positions):
        return "NULL" if (index % 16) in null_positions else str(value)

    with open(os.path.join(workdir, "a.txt"), "w") as handle:
        handle.write("".join(cell(k, k + 1, nulls_a) + "\n" for k in range(SOURCE_RECORDS)))
    with open(os.path.join(workdir, "b.txt"), "w") as handle:
        handle.write("".join(cell(j, B_BASE + j, nulls_b) + "\n" for j in range(SOURCE_RECORDS)))


def decode_data(path, field_count):
    """Artefakt INTEGER: 4 bajty na pole, little-endian, field_count pól na rekord."""
    with open(path, "rb") as handle:
        raw = handle.read()
    values = list(struct.unpack(f"<{len(raw) // 4}i", raw[: len(raw) // 4 * 4]))
    return [values[i:i + field_count] for i in range(0, len(values), field_count)]


def decode_meta(path):
    """Wpisy indeksu null: 8-bajtowy nagłówek czasu, potem wpisy IndexRecord.

    Format wpisu (src/rdb/lib/indexRecord.cc): uint8 isGap, size_t recordCount,
    size_t bitsetSize, spakowane bity (LSB-first, packedByteCount bajtów).
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    entries = []
    pos = 8
    while pos + 17 <= len(raw):
        is_gap = raw[pos]
        count, bits = struct.unpack_from("<QQ", raw, pos + 1)
        byte_count = (bits + 7) // 8
        pos += 17
        packed = raw[pos:pos + byte_count]
        pos += byte_count
        bitset = [bool(packed[i // 8] >> (i % 8) & 1) for i in range(bits)]
        entries.append({"gap": bool(is_gap), "records": count, "null": bitset})
    return entries


def null_flags(entries, limit):
    """Rozwinięcie RLE do listy 'czy rekord jest all-null' dla pierwszych `limit`."""
    flags = []
    for entry in entries:
        if entry["gap"]:
            continue
        state = "null" if all(entry["null"]) else ("part" if any(entry["null"]) else "data")
        flags.extend([state] * min(entry["records"], limit - len(flags)))
        if len(flags) >= limit:
            break
    return flags


def read_desc(path):
    with open(path) as handle:
        return handle.read().strip()


def field_names(desc_text):
    names = []
    for line in desc_text.splitlines():
        parts = line.replace("{", "").strip().split()
        if len(parts) == 2 and parts[0].isupper():
            names.append(parts[1])
    return names


def run_case(binary, workroot, name, delta_a, delta_b, body, nulls=None):
    workdir = os.path.join(workroot, name)
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir)
    write_sources(workdir, nulls)

    with open(os.path.join(workdir, "q.rql"), "w") as handle:
        handle.write(PREAMBLE.format(da=delta_a, db=delta_b) + "\n" + body)

    plan = subprocess.run(
        [binary, "q.rql", "-c"], cwd=workdir, capture_output=True, text=True, check=True
    ).stdout
    subprocess.run(
        [binary, "q.rql", "-r", "-k", "-m", str(SLOTS)],
        cwd=workdir, capture_output=True, text=True, check=True,
    )

    desc = read_desc(os.path.join(workdir, "probe.desc"))
    names = field_names(desc)
    records = decode_data(os.path.join(workdir, "probe"), max(len(names), 1))
    meta = decode_meta(os.path.join(workdir, "probe.meta"))
    flags = null_flags(meta, len(records))

    zero_prefix = 0
    for record in records:
        if any(value != 0 for value in record):
            break
        zero_prefix += 1

    # Wpisy gap są markerami przerw i NIE są wliczane do numeracji rekordów, więc
    # stanowią osobną warstwę obserwowalną (punkt 5 relacji równoważności).
    gaps = [entry["records"] for entry in meta if entry["gap"]]

    return {
        "case": name,
        "gap_entries": gaps,
        "delta_a": delta_a,
        "delta_b": delta_b,
        "rql": body.strip(),
        "plan": [line for line in plan.splitlines() if line.startswith("\t:- ") or not line.startswith("\t")],
        "field_names": names,
        "desc": desc,
        "records_total": len(records),
        "records": records[:PREVIEW],
        "null_flags": flags[:PREVIEW],
        "zero_prefix": zero_prefix,
        "all_null_records": sum(1 for flag in flags if flag == "null"),
    }


def compare(left, right):
    """Porównanie w warstwach relacji równoważności z §6.1 research_plan.md."""
    return {
        "values": left["records"] == right["records"],
        "null_map": left["null_flags"] == right["null_flags"],
        "zero_prefix": left["zero_prefix"] == right["zero_prefix"],
        "field_names": left["field_names"] == right["field_names"],
        "gaps": left["gap_entries"] == right["gap_entries"],
        "schema_shape": len(left["field_names"]) == len(right["field_names"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xretractor", default="../../../build/Debug/src/retractor/xretractor")
    parser.add_argument("--json", default="results/probe.json")
    parser.add_argument("--workdir", default="work")
    parser.add_argument("--profile", default="default", help="etykieta konfiguracji optymalizatora")
    args = parser.parse_args()

    binary = os.path.abspath(args.xretractor)
    if not os.path.exists(binary):
        sys.exit(f"brak binarki: {binary}")

    build_info = subprocess.run(
        [binary, "--build-info"], capture_output=True, text=True, check=True
    ).stdout.strip()

    os.makedirs(args.workdir, exist_ok=True)
    workroot = os.path.abspath(args.workdir)

    cases = {}
    for case in CASES:
        name, delta_a, delta_b, body = case[:4]
        nulls = case[4] if len(case) > 4 else None
        print(f"-- {name}")
        cases[name] = run_case(binary, workroot, name, delta_a, delta_b, body, nulls)

    pairs = []
    for left, right, role, note in PAIRS:
        result = compare(cases[left], cases[right])
        pairs.append({"left": left, "right": right, "role": role, "note": note, **result})

    broken_controls = [
        pair for pair in pairs
        if pair["role"] == "control" and not (pair["values"] and pair["null_map"])
    ]

    report = {
        "profile": args.profile,
        "build_info": dict(
            line.split("=", 1) for line in build_info.splitlines() if "=" in line
        ),
        "slots": SLOTS,
        "cases": cases,
        "pairs": pairs,
        "controls_ok": not broken_controls,
    }

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w") as handle:
        json.dump(report, handle, indent=2)

    print()
    for pair in pairs:
        layers = [key for key in ("values", "null_map", "zero_prefix", "field_names", "gaps") if not pair[key]]
        verdict = "ZGODNE" if not layers else "ROZBIEŻNE: " + ", ".join(layers)
        print(f"[{pair['role']:>8}] {pair['left']} <-> {pair['right']}: {verdict}")

    if broken_controls:
        print("\nKONTROLA ZAWIODŁA — wynik sondy jest nieważny", file=sys.stderr)
        return 1
    print(f"\nzapisano: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
