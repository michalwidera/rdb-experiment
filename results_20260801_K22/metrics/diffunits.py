#!/usr/bin/env python3
"""Zakres zmiany M1–M4: D1 (instrukcje) i D2 (jednostki programu).

`D2` jest wielkością ROZSTRZYGAJĄCĄ w kryterium go/no-go (PREDECLARATION.md §8,
warunek 2), więc definicje są tu implementacją `coding_manual.md` §2, nie
swobodną interpretacją.

Jednostki programu (zamrożone per model):
  RQL    — instrukcja DECLARE/SELECT/RULE; kluczem jest nazwa strumienia,
           bo nazwany strumień jest tożsamy z instrukcją, która go definiuje.
  Python — funkcja/metoda/klasa oraz blok pętli rdzenia (osobna jednostka).
  Java   — klasa operatora, metoda funkcjonalna, blok składania topologii.

Reguły zmiany (coding_manual.md §2.1):
  * jednostka zmieniona = różni się treścią poza białymi znakami i komentarzami;
  * jednostka dodana i usunięta liczą się po 1;
  * jednostka PRZENIESIONA bez zmiany treści NIE liczy się — inaczej samo
    przestawienie kolejności zawyżałoby D2.

D1 liczy instrukcje na diffie znormalizowanym; modyfikacja liczy się RAZ,
nie jako para usunięcie+dodanie.
"""
import argparse
import ast
import difflib
import json
import re
import sys
from pathlib import Path

from measure import MeasureError, core_ranges, in_core

RQL_STMT = re.compile(r"^\s*(DECLARE|SELECT|RULE)\b", re.IGNORECASE)
RQL_STREAM = re.compile(r"\bSTREAM\s+(\w+)", re.IGNORECASE)
JAVA_CLASS = re.compile(r"\b(?:static\s+)?class\s+(\w+)")
JAVA_METHOD = re.compile(r"\b(map|flatMap|open|close|invoke|run|processElement)\s*\(")


def core_lines(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    ranges = core_ranges(lines, path)
    return [(i, lines[i - 1]) for i in range(1, len(lines) + 1) if in_core(i, ranges)]


def normalize(text, comment):
    """Usuwa komentarz i zbędne białe znaki — porównujemy treść, nie formatowanie."""
    cut = text.find(comment)
    if cut >= 0:
        text = text[:cut]
    return " ".join(text.split())


def units_rql(path):
    units = {}
    for _lineno, raw in core_lines(path):
        text = normalize(raw, "#")
        if not text or not RQL_STMT.match(text):
            continue
        m = RQL_STREAM.search(text)
        key = m.group(1) if m else text
        units[key] = text
    return units


def units_python(path):
    src = Path(path).read_text(encoding="utf-8")
    lines = src.splitlines()
    ranges = core_ranges(lines, path)
    tree = ast.parse(src)
    units = {}

    def body_of(node):
        start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
        body = [normalize(lines[i - 1], "#") for i in range(start, end + 1)]
        return " ".join(x for x in body if x)

    loop_no = 0
    for node in ast.walk(tree):
        if not getattr(node, "lineno", None) or not in_core(node.lineno, ranges):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            units[f"def:{node.name}"] = body_of(node)
        elif isinstance(node, (ast.For, ast.While)):
            loop_no += 1
            units[f"loop:{loop_no}"] = body_of(node)
    return units


def units_java(path):
    units = {}
    current_class = None
    buf_key = None
    buf = []
    depth = 0
    topo = []
    for _lineno, raw in core_lines(path):
        text = normalize(raw, "//")
        if not text:
            continue
        mc = JAVA_CLASS.search(text)
        if mc:
            current_class = mc.group(1)
            units[f"class:{current_class}"] = text
        # Blok skladania topologii MUSI byc sprawdzony PRZED deklaracja metody.
        # Linia `.flatMap(new Assemble(v1))` pasuje do wzorca nazwy metody, wiec
        # bez tej kolejnosci byla klasyfikowana jako deklaracja `flatMap` ostatniej
        # widzianej klasy i NADPISYWALA prawdziwa jednostke tej metody.
        is_topology = (text.startswith(".") or "addSource(" in text or ".addSink(" in text
                       or ("(new " in text and not text.endswith("{")))
        if is_topology and not buf_key:
            topo.append(text)
            continue
        mm = JAVA_METHOD.search(text)
        # Deklaracja metody ma nazwe poprzedzona TYPEM; wywolanie ma ja po kropce.
        # Deklaracja bywa lamana na dwie linie, wiec nie mozna wymagac konca '{'.
        if mm and f".{mm.group(1)}(" in text:
            mm = None
        if mm and current_class:
            if buf_key:
                units[buf_key] = " ".join(buf)
            buf_key = f"method:{current_class}.{mm.group(1)}"
            buf = [text]
            depth = text.count("{") - text.count("}")
            continue
        if buf_key:
            buf.append(text)
            depth += text.count("{") - text.count("}")
            if depth <= 0:
                units[buf_key] = " ".join(buf)
                buf_key = None
                buf = []
            continue
    if buf_key:
        units[buf_key] = " ".join(buf)
    if topo:
        units["topology"] = " ".join(topo)
    return units


EXTRACT = {".rql": units_rql, ".py": units_python, ".java": units_java}
COMMENT = {".rql": "#", ".py": "#", ".java": "//"}


def statements(path):
    ext = Path(path).suffix
    return [normalize(raw, COMMENT[ext]) for _l, raw in core_lines(path)
            if normalize(raw, COMMENT[ext])]


def d1(base, variant):
    """Instrukcje zmienione: modyfikacja liczy sie RAZ, nie jako para."""
    a, b = statements(base), statements(variant)
    total = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        total += max(i2 - i1, j2 - j1)
    return total


def d2(base, variant):
    ext = Path(base).suffix
    if ext != Path(variant).suffix:
        raise MeasureError(f"rozne modele: {base} vs {variant}")
    ua, ub = EXTRACT[ext](base), EXTRACT[ext](variant)
    changed = []
    for key in sorted(set(ua) | set(ub)):
        if key not in ua:
            changed.append((key, "dodana"))
        elif key not in ub:
            changed.append((key, "usunieta"))
        elif ua[key] != ub[key]:
            changed.append((key, "zmieniona"))
    return changed, len(ua), len(ub)


def main():
    ap = argparse.ArgumentParser(description="D1/D2 miedzy baza a wariantem K22.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    changed, n_base, n_var = d2(args.base, args.variant)
    result = {
        "D1": d1(args.base, args.variant),
        "D2": len(changed),
        "units_total": n_base,
        "units_variant": n_var,
        "changed": [f"{k} ({w})" for k, w in changed],
    }
    if not n_base:
        raise MeasureError(f"{args.base}: zero jednostek — blad aparatury, nie wynik")
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"D1={result['D1']} D2={result['D2']} jednostek_bazy={n_base}")
        for item in result["changed"]:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MeasureError as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
