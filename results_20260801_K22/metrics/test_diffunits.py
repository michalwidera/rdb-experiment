#!/usr/bin/env python3
"""Testy o znanej odpowiedzi dla pomiaru D1/D2.

`D2` jest wielkością ROZSTRZYGAJĄCĄ w kryterium go/no-go, a pierwsza wersja
`diffunits.py` miała w niej dwa błędy wykryte dopiero na realnym wariancie:

  * linia składania topologii `.flatMap(new Assemble(v1))` pasowała do wzorca
    nazwy metody i NADPISYWAŁA jednostkę `method:Assemble.flatMap`;
  * deklaracja metody łamana na dwie linie nie była rozpoznawana.

Oba zaniżały `D2` Flinka, czyli działały NA KORZYŚĆ tezy H8. Dlatego instrument
dostaje własne fixture'y — narzędzie, które decyduje o werdykcie, nie może być
sprawdzane wyłącznie na danych, których wynik chcemy poznać.
"""
import os
import sys
import tempfile

from diffunits import d1, d2

failures = 0
checks = 0


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def expect(name, base_text, var_text, ext, want_d2, want_changed, want_d1=None):
    global failures, checks
    checks += 1
    with tempfile.TemporaryDirectory() as tmp:
        b = write(tmp, "base" + ext, base_text)
        v = write(tmp, "var" + ext, var_text)
        changed, n_base, _n_var = d2(b, v)
        got_d2 = len(changed)
        got_keys = sorted(k for k, _w in changed)
        got_d1 = d1(b, v)
    if got_d2 != want_d2 or got_keys != sorted(want_changed):
        print(f"FAIL  {name}: D2={got_d2} {got_keys}, oczekiwano {want_d2} {sorted(want_changed)}")
        failures += 1
        return
    if want_d1 is not None and got_d1 != want_d1:
        print(f"FAIL  {name}: D1={got_d1}, oczekiwano {want_d1}")
        failures += 1
        return
    print(f"ok    {name}: D1={got_d1} D2={got_d2} {got_keys}")


RQL_BASE = """# CORE_BEGIN
DECLARE x INTEGER STREAM src, 1/100 FILE 'a.txt'
SELECT * STREAM win FROM src@(1,5)
SELECT win[0] STREAM out FROM win.avg
# CORE_END
"""
# Zmiana szerokosci okna: 1 jednostka zmieniona, 1 instrukcja.
RQL_WIN = RQL_BASE.replace("@(1,5)", "@(1,9)")
# Dodanie strumienia: 1 jednostka dodana.
RQL_ADD = RQL_BASE.replace("# CORE_END", "SELECT src[0] STREAM raw FROM src\n# CORE_END")
# Przestawienie kolejnosci BEZ zmiany tresci: D2 = 0 (coding_manual.md §2.1).
RQL_MOVED = """# CORE_BEGIN
SELECT * STREAM win FROM src@(1,5)
DECLARE x INTEGER STREAM src, 1/100 FILE 'a.txt'
SELECT win[0] STREAM out FROM win.avg
# CORE_END
"""
# Sam komentarz i biale znaki nie sa zmiana.
RQL_COMMENT = RQL_BASE.replace("SELECT * STREAM win FROM src@(1,5)",
                               "SELECT  *  STREAM win FROM src@(1,5)   # nowy komentarz")

expect("RQL: zmiana szerokosci okna", RQL_BASE, RQL_WIN, ".rql", 1, ["win"], want_d1=1)
expect("RQL: dodany strumien", RQL_BASE, RQL_ADD, ".rql", 1, ["raw"], want_d1=1)
expect("RQL: przestawienie bez zmiany tresci -> D2=0", RQL_BASE, RQL_MOVED, ".rql", 0, [])
expect("RQL: komentarz i biale znaki nie sa zmiana", RQL_BASE, RQL_COMMENT, ".rql", 0, [])

JAVA_BASE = """public class T {
// CORE_BEGIN
  static class Op {
    public void flatMap(Tuple2<Long, Integer> in,
        Collector<Tuple2<Long, Integer>> out) {
      out.collect(in);
    }
  }
// CORE_END
  void main() {
// CORE_BEGIN
    src.flatMap(new Op()).addSink(new Sink());
// CORE_END
  }
}
"""
# Zmiana WYLACZNIE w linii topologii. Blad #1 klasyfikowal ja jako deklaracje
# metody `flatMap` i gubil rozroznienie; poprawnie to jednostka `topology`.
JAVA_TOPO = JAVA_BASE.replace("new Op()", "new Op(v1)")
# Zmiana WYLACZNIE w ciele metody lamanej na dwie linie. Blad #2 nie rozpoznawal
# takiej deklaracji, wiec ta zmiana nie byla liczona wcale.
JAVA_BODY = JAVA_BASE.replace("out.collect(in);", "out.collect(in.f0);")

expect("Java: zmiana tylko w topologii", JAVA_BASE, JAVA_TOPO, ".java", 1, ["topology"], want_d1=1)
expect("Java: zmiana w ciele metody lamanej na dwie linie", JAVA_BASE, JAVA_BODY, ".java",
       1, ["method:Op.flatMap"], want_d1=1)
expect("Java: obie zmiany naraz", JAVA_BASE, JAVA_TOPO.replace("out.collect(in);", "out.collect(in.f0);"),
       ".java", 2, ["topology", "method:Op.flatMap"], want_d1=2)

PY_BASE = '''def run(xs):
    # CORE_BEGIN
    total = 0
    for x in xs:
        total = total + x
    # CORE_END
    return total
'''
PY_LOOP = PY_BASE.replace("total = total + x", "total = total + x * 2")
PY_ADD = PY_BASE.replace("    total = 0\n", "    total = 0\n    count = 0\n")

expect("Python: zmiana w ciele petli", PY_BASE, PY_LOOP, ".py", 1, ["loop:1"], want_d1=1)
expect("Python: dodana instrukcja poza petla", PY_BASE, PY_ADD, ".py", 0, [], want_d1=1)

print(f"\n{checks - failures}/{checks} kontroli OK")
sys.exit(1 if failures else 0)
