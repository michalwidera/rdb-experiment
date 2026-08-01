#!/usr/bin/env python3
"""Statyczne metryki konstrukcji K22 (coding_manual.md).

Implementuje reguły podręcznika DOSŁOWNIE. Rozbieżność między podręcznikiem
a tym skryptem jest błędem skryptu, nie podręcznika.

Emituje dwie rzeczy:
  * `constructs.csv` — zagregowane kolumny C1..C7, C3d, C4d, loc, cyclomatic;
  * `hits.csv`       — SUROWĄ tabelę kwalifikacji każdego trafienia
                       (metryka, rule_id, plik, linia, treść), żeby recenzent
                       mógł zakwestionować pojedyncze trafienie bez czytania
                       tego kodu.

Zasady twarde (PREDECLARATION.md §7.5):
  * zero zeskanowanych programów => kod wyjścia != 0, to BŁĄD, nie wynik;
  * nierozstrzygnięty kandydat C5-02 => kod wyjścia != 0.

Zliczanie:
  * C1, C4, C5, C7 — per INSTRUKCJA, w zamrożonej kolejności rozstrzygania
    C4 -> C5 -> C1 -> C3 -> C2 -> C7 (coding_manual.md §0.1);
  * C2, C3, C6     — per UNIKALNA NAZWA;
  * C3d, C4d       — per deklaracja, poza kolejnością rozstrzygania.
"""
import argparse
import ast
import csv
import os
import re
import sys
from collections import OrderedDict

METRICS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C3d", "C4d"]

CORE_BEGIN = "CORE_BEGIN"
CORE_END = "CORE_END"


class MeasureError(Exception):
    """Błąd aparatury pomiarowej — nie jest wynikiem."""


class Hit:
    __slots__ = ("metric", "rule_id", "path", "line", "text", "name")

    def __init__(self, metric, rule_id, path, line, text, name=None):
        self.metric = metric
        self.rule_id = rule_id
        self.path = path
        self.line = line
        self.text = text.strip()
        self.name = name


# ---------------------------------------------------------------------------
# Granica rdzenia (PREDECLARATION.md §2)
# ---------------------------------------------------------------------------

def core_ranges(lines, path):
    """Zwraca listę (start, stop) 1-indeksowanych, domkniętych przedziałów rdzenia."""
    ranges = []
    open_at = None
    for i, line in enumerate(lines, start=1):
        if CORE_BEGIN in line:
            if open_at is not None:
                raise MeasureError(f"{path}:{i}: CORE_BEGIN wewnatrz otwartego rdzenia")
            open_at = i
        elif CORE_END in line:
            if open_at is None:
                raise MeasureError(f"{path}:{i}: CORE_END bez CORE_BEGIN")
            ranges.append((open_at + 1, i - 1))
            open_at = None
    if open_at is not None:
        raise MeasureError(f"{path}: CORE_BEGIN bez CORE_END")
    if not ranges:
        raise MeasureError(f"{path}: brak znacznikow CORE_BEGIN/CORE_END — plik nie moze byc mierzony")
    return ranges


def in_core(lineno, ranges):
    return any(a <= lineno <= b for a, b in ranges)


# ---------------------------------------------------------------------------
# Wspólne wzorce (coding_manual.md §1)
# ---------------------------------------------------------------------------

CLOCK_TOKENS = [
    "time.monotonic_ns", "time.monotonic", "time.perf_counter_ns", "time.perf_counter",
    "time.time", "System.nanoTime", "System.currentTimeMillis", "Instant.now",
]
SLEEP_TOKENS = ["time.sleep", "Thread.sleep", "LockSupport.park"]
SYNC_TOKENS = [
    "threading.", "Lock(", "Queue(", "synchronized", "AtomicLong",
    "ConcurrentLinkedQueue", "CountDownLatch",
]
SCHED_TOKENS = [
    "setBufferTimeout", "TimeCharacteristic", "assignTimestampsAndWatermarks",
    "WatermarkStrategy", "TumblingProcessingTimeWindows", "SlidingProcessingTimeWindows",
]
DEADLINE_NAMES = ["deadline", "period", "termin"]
TAIL_NAMES = ["delay", "tail", "latency", "warmup", "ogon"]

PY_CONTAINER_CTOR = ["np.zeros(", "np.empty(", "np.array(", "list(", "deque(", "collections.deque("]
PY_SHIFT_OPS = [".append(", ".popleft("]
JAVA_CONTAINER_CTOR = ["new double[", "new int[", "new long[", "new ArrayDeque", "new ArrayList", "new LinkedList"]
JAVA_SHIFT_OPS = ["System.arraycopy(", ".addLast(", ".pollFirst("]

BRANCH_TOKENS_PY = ["if ", "elif ", "for ", "while ", " and ", " or "]
BRANCH_TOKENS_JAVA = ["if (", "else if", "for (", "while (", "case ", "catch (", "&&", "||", "?"]


def _has_any(text, tokens):
    return any(t in text for t in tokens)


def _clock_rule(text):
    if _has_any(text, CLOCK_TOKENS):
        return "C4-01"
    if _has_any(text, SLEEP_TOKENS):
        return "C4-02"
    if _has_any(text, SYNC_TOKENS):
        return "C4-04"
    if _has_any(text, SCHED_TOKENS):
        return "C4-05"
    low = text.lower()
    if any(n in low for n in DEADLINE_NAMES) and ("+" in text or "*" in text):
        return "C4-03"
    return None


def _tail_rule(text):
    """C5 — ręczne wyprowadzanie historii/fazy/ogona."""
    low = text.lower()
    if any(n in low for n in TAIL_NAMES) and re.search(r"=\s*-?\d+\s*;?\s*$", text):
        return "C5-04"
    if "%" in text and not text.lstrip().startswith("#"):
        return "C5-03"
    return None


# ---------------------------------------------------------------------------
# RQL
# ---------------------------------------------------------------------------

RQL_STMT = re.compile(r"^\s*(DECLARE|SELECT|RULE)\b", re.IGNORECASE)
RQL_INTERVAL = re.compile(r"\bSTREAM\s+\w+\s*,\s*(\d+(?:\s*/\s*\d+)?)", re.IGNORECASE)
# Konstrukcje, ktorych obecnosc liczylaby sie do C1..C6. W gramatyce RQL ich nie
# ma; skanujemy mechanicznie, zeby zero bylo WYNIKIEM POMIARU, a nie zalozeniem.
RQL_IMPERATIVE = ["for ", "while ", "loop", ":=", "++", "sleep", "clock", "thread"]


def analyze_rql(path, lines, ranges):
    hits = []
    for i, raw in enumerate(lines, start=1):
        if not in_core(i, ranges):
            continue
        text = raw.strip()
        if not text or text.startswith("#"):
            continue

        for tok in RQL_IMPERATIVE:
            if tok in text.lower():
                hits.append(Hit("C1", "RQL-C1-01", path, i, raw))
                break

        if RQL_STMT.match(text):
            hits.append(Hit("C7", "RQL-C7-01", path, i, raw))
        if "@(" in text:
            for _ in range(text.count("@(")):
                hits.append(Hit("C3d", "RQL-C3d-01", path, i, raw))
        m = RQL_INTERVAL.search(text)
        if m:
            hits.append(Hit("C4d", "RQL-C4d-01", path, i, raw))
    return hits


# ---------------------------------------------------------------------------
# Python (parser skladniowy — ast)
# ---------------------------------------------------------------------------

def _py_names_stored(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.append(n.id)
        elif isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store):
            base = n.value
            while isinstance(base, (ast.Subscript, ast.Attribute)):
                base = base.value
            if isinstance(base, ast.Name):
                out.append(base.id)
        elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
            if isinstance(n.value, ast.Name) and n.value.id == "self":
                out.append(f"self.{n.attr}")
    return out


def analyze_python(path, lines, ranges):
    src = "".join(lines)
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise MeasureError(f"{path}: nie da sie sparsowac: {exc}") from exc

    def line_of(node):
        return getattr(node, "lineno", None)

    def text_of(node):
        ln = line_of(node)
        return lines[ln - 1] if ln and ln <= len(lines) else ""

    core_stmts = [n for n in ast.walk(tree)
                  if isinstance(n, ast.stmt) and line_of(n) and in_core(line_of(n), ranges)]
    core_loops = [n for n in core_stmts if isinstance(n, (ast.For, ast.While))]

    def is_nested_loop(loop):
        for other in core_loops:
            if other is loop:
                continue
            for sub in ast.walk(other):
                if sub is loop:
                    return True
        return False

    slot_loops = [lp for lp in core_loops if not is_nested_loop(lp)]
    slot_lines = set()
    for lp in slot_loops:
        for sub in ast.walk(lp):
            if line_of(sub):
                slot_lines.add(line_of(sub))

    hits = []
    claimed = set()

    # C4 / C5 / C1 — per instrukcja, w zamrozonej kolejnosci.
    for stmt in core_stmts:
        ln = line_of(stmt)
        text = text_of(stmt)
        rule = _clock_rule(text)
        if rule:
            hits.append(Hit("C4", f"PY-{rule}", path, ln, text))
            claimed.add(ln)
            continue
        rule = _tail_rule(text)
        if rule:
            hits.append(Hit("C5", f"PY-{rule}", path, ln, text))
            claimed.add(ln)
            continue
        if isinstance(stmt, ast.If) and re.search(r"<\s*[A-Z_]{3,}|<\s*len\(", text):
            hits.append(Hit("C5", "PY-C5-01", path, ln, text))
            claimed.add(ln)
            continue
        if isinstance(stmt, (ast.For, ast.While)):
            rid = "PY-C1-01" if stmt in slot_loops else "PY-C1-02"
            hits.append(Hit("C1", rid, path, ln, text))
            claimed.add(ln)
            continue

    # C3 / C2 — per unikalna nazwa: inicjalizowana poza petla slotowa,
    # mutowana wewnatrz niej (albo pole `self.`).
    init_names = {}
    for stmt in core_stmts:
        ln = line_of(stmt)
        if ln in slot_lines:
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for nm in _py_names_stored(stmt):
                init_names.setdefault(nm, (ln, text_of(stmt)))

    mutated = {}
    for stmt in core_stmts:
        ln = line_of(stmt)
        if ln not in slot_lines:
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for nm in _py_names_stored(stmt):
                mutated.setdefault(nm, (ln, text_of(stmt)))
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if _has_any("." + sub.func.attr + "(", PY_SHIFT_OPS) and isinstance(sub.func.value, ast.Name):
                    mutated.setdefault(sub.func.value.id, (ln, text_of(stmt)))

    containers, plain = OrderedDict(), OrderedDict()
    for nm, (ln, text) in init_names.items():
        if nm not in mutated:
            continue
        mline, mtext = mutated[nm]
        if _has_any(text, PY_CONTAINER_CTOR) or "[" in text.split("=", 1)[-1]:
            containers[nm] = ("PY-C3-01", ln, text)
        elif re.search(rf"{re.escape(nm)}\[:-1\]\s*=\s*{re.escape(nm)}\[1:\]", mtext) or _has_any(mtext, PY_SHIFT_OPS):
            containers[nm] = ("PY-C3-02", mline, mtext)
        else:
            plain[nm] = ("PY-C2-01", ln, text)
    for nm, (rid, ln, text) in containers.items():
        hits.append(Hit("C3", rid, path, ln, text, name=nm))
        claimed.add(ln)
    for nm, (rid, ln, text) in plain.items():
        hits.append(Hit("C2", rid, path, ln, text, name=nm))
        claimed.add(ln)
    for nm in list(containers) + list(plain):
        claimed.add(mutated[nm][0])

    # C6 — nazwa przypisana raz w petli slotowej i odczytana >= 2 razy.
    # Petle slotowe sa przechodzone RAZ, a nie raz na kazda instrukcje w srodku:
    # `ast.walk` po kazdej instrukcji z osobna liczylby kazde wczytanie tyle
    # razy, ile instrukcji zlozonych je otacza, i zawyzalby C6.
    assigned_once, load_count = {}, {}
    for lp in slot_loops:
        for sub in ast.walk(lp):
            if isinstance(sub, ast.Assign):
                for nm in _py_names_stored(sub):
                    assigned_once[nm] = assigned_once.get(nm, 0) + 1
            elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                load_count[sub.id] = load_count.get(sub.id, 0) + 1
    for nm, cnt in assigned_once.items():
        if cnt == 1 and load_count.get(nm, 0) >= 2 and nm not in containers and nm not in plain:
            for stmt in core_stmts:
                if line_of(stmt) in slot_lines and isinstance(stmt, ast.Assign) \
                        and nm in _py_names_stored(stmt):
                    hits.append(Hit("C6", "PY-C6-01", path, line_of(stmt), text_of(stmt), name=nm))
                    # C6 rozstrzyga PRZED C7 (coding_manual.md §0.1), wiec linia
                    # jest zajeta i nie moze trafic takze do instrukcji domenowych.
                    claimed.add(line_of(stmt))
                    break

    # C7 — reszta instrukcji rdzenia.
    for stmt in core_stmts:
        ln = line_of(stmt)
        if ln in claimed:
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Expr)) and not isinstance(stmt, ast.Assign):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
        hits.append(Hit("C7", "PY-C7-01", path, ln, text_of(stmt)))
        claimed.add(ln)

    return hits


# ---------------------------------------------------------------------------
# Java (wzorce tekstowe — coding_manual.md §5 pkt 1)
# ---------------------------------------------------------------------------

JAVA_METHOD = re.compile(r"\b(public|private|protected|static|final|\s)*[\w<>\[\],\s]+\s+"
                         r"(map|flatMap|open|close|invoke|run|processElement)\s*\(")
JAVA_FIELD = re.compile(r"^\s*(?:private|public|protected)?\s*(?:final\s+)?"
                        r"([\w<>\[\],\s]+?)\s+(\w+)\s*(?:=|;)")


def analyze_java(path, lines, ranges):
    hits = []
    depth = 0
    loop_depth_stack = []
    containers, plain = OrderedDict(), OrderedDict()
    decl_lines = {}

    for i, raw in enumerate(lines, start=1):
        if not in_core(i, ranges):
            continue
        text = raw.strip()
        if not text or text.startswith("//") or text.startswith("*") or text.startswith("/*"):
            continue
        if text.startswith("@"):
            continue

        # C2 w Javie liczy POLA operatora, nie zmienne lokalne: pole przezywa
        # rekord, zmienna lokalna metody `map` nie. Bez tego ograniczenia
        # akumulator iloczynu skalarnego (`double acc = 0.0;`) bylby liczony
        # jako stan, a nie jest nim (coding_manual.md §1, C2 — zdanie
        # o zmiennej czysto lokalnej dla jednego slotu).
        m = JAVA_FIELD.match(raw) if re.match(r"^\s*(private|public|protected|static|final)\b", raw) else None
        if m:
            decl_lines[m.group(2)] = (i, raw, m.group(1).strip())

        rule = _clock_rule(text)
        if rule:
            hits.append(Hit("C4", f"JAVA-{rule}", path, i, raw))
        elif _tail_rule(text):
            hits.append(Hit("C5", f"JAVA-{_tail_rule(text)}", path, i, raw))
        elif re.search(r"\bif\s*\(.*<\s*\w+\.length", text):
            hits.append(Hit("C5", "JAVA-C5-01", path, i, raw))
        elif re.search(r"\b(for|while)\s*\(", text):
            rid = "JAVA-C1-02" if loop_depth_stack else "JAVA-C1-01"
            hits.append(Hit("C1", rid, path, i, raw))
            loop_depth_stack.append(depth)
        elif _has_any(text, JAVA_CONTAINER_CTOR):
            nm = m.group(2) if m else _java_lhs(text)
            if nm:
                containers.setdefault(nm, ("JAVA-C3-01", i, raw))
        elif _has_any(text, JAVA_SHIFT_OPS):
            nm = _java_arraycopy_name(text)
            if nm:
                containers.setdefault(nm, ("JAVA-C3-02", i, raw))
        elif _has_any(text, SCHED_TOKENS):
            hits.append(Hit("C4", "JAVA-C4-05", path, i, raw))
        elif ".window(" in text or ".countWindow(" in text or ".timeWindow(" in text:
            hits.append(Hit("C3d", "JAVA-C3d-01", path, i, raw))
        elif re.search(r"\brateHz\b|\bintervalNs\b", text):
            hits.append(Hit("C4d", "JAVA-C4d-01", path, i, raw))
        elif text.endswith(";") or JAVA_METHOD.search(text) or re.search(r"\bclass\s+\w+", text):
            hits.append(Hit("C7", "JAVA-C7-01", path, i, raw))

        depth += text.count("{") - text.count("}")
        while loop_depth_stack and depth <= loop_depth_stack[-1]:
            loop_depth_stack.pop()

    for nm, (rid, ln, raw) in containers.items():
        hits.append(Hit("C3", rid, path, ln, raw, name=nm))
    for nm, (ln, raw, _ty) in decl_lines.items():
        if nm in containers:
            continue
        pat = re.compile(rf"\b{re.escape(nm)}\s*(=[^=]|\+=|-=|\+\+|--)")
        for j, other in enumerate(lines, start=1):
            if j == ln or not in_core(j, ranges):
                continue
            if pat.search(other):
                plain[nm] = ("JAVA-C2-01", ln, raw)
                break
    for nm, (rid, ln, raw) in plain.items():
        hits.append(Hit("C2", rid, path, ln, raw, name=nm))

    return hits


def _java_lhs(text):
    m = re.search(r"(\w+)\s*=", text)
    return m.group(1) if m else None


def _java_arraycopy_name(text):
    m = re.search(r"System\.arraycopy\(\s*(\w+)", text)
    if m:
        return m.group(1)
    m = re.search(r"(\w+)\.(addLast|pollFirst)\(", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Metryki drugorzedne
# ---------------------------------------------------------------------------

def secondary(lines, ranges, kind):
    loc = 0
    branches = 0
    tokens = BRANCH_TOKENS_PY if kind == "python" else BRANCH_TOKENS_JAVA
    for i, raw in enumerate(lines, start=1):
        if not in_core(i, ranges):
            continue
        text = raw.strip()
        if not text:
            continue
        if kind == "rql" and text.startswith("#"):
            continue
        if kind == "python" and text.startswith("#"):
            continue
        if kind == "java" and (text.startswith("//") or text.startswith("*") or text.startswith("/*")):
            continue
        if re.match(r"^\s*(import|from|package)\b", text):
            continue
        loc += 1
        if kind != "rql":
            branches += sum(text.count(t) for t in tokens)
    return loc, (1 if kind == "rql" else 1 + branches)


# ---------------------------------------------------------------------------
# Sterowanie
# ---------------------------------------------------------------------------

KIND_BY_EXT = {".rql": "rql", ".py": "python", ".java": "java"}
ANALYZER = {"rql": analyze_rql, "python": analyze_python, "java": analyze_java}


def measure_file(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    ext = os.path.splitext(path)[1]
    kind = KIND_BY_EXT.get(ext)
    if kind is None:
        raise MeasureError(f"{path}: nieobslugiwane rozszerzenie {ext}")
    ranges = core_ranges(lines, path)
    hits = ANALYZER[kind](path, lines, ranges)
    loc, cyc = secondary(lines, ranges, kind)
    return hits, loc, cyc, kind


def aggregate(hits):
    counts = {m: 0 for m in METRICS}
    seen_names = {m: set() for m in METRICS}
    for h in hits:
        if h.metric in ("C2", "C3", "C6"):
            key = h.name or f"{h.path}:{h.line}"
            if key in seen_names[h.metric]:
                continue
            seen_names[h.metric].add(key)
        counts[h.metric] += 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Statyczne metryki konstrukcji K22.")
    ap.add_argument("--out-dir", required=True, help="katalog na constructs.csv i hits.csv")
    ap.add_argument("--label", default="", help="etykieta rodzina/model/wariant dla wierszy wyjscia")
    ap.add_argument("--manual-c5", default=None, help="rozstrzygniecia kandydatow C5-02")
    # nargs="*", nie "+": pusta lista MUSI dojsc do straznika ponizej i skonczyc
    # sie bledem aparatury. Gdyby argparse odrzucal ja wczesniej, straznik
    # "zero programow to blad, nie wynik" bylby nieosiagalny, czyli nietestowalny.
    ap.add_argument("files", nargs="*")
    args = ap.parse_args(argv)

    all_hits, loc_total, cyc_total, scanned = [], 0, 0, 0
    for path in args.files:
        hits, loc, cyc, _kind = measure_file(path)
        all_hits.extend(hits)
        loc_total += loc
        cyc_total += cyc
        scanned += 1

    if scanned == 0:
        raise MeasureError("zero zeskanowanych programow — to jest BLAD, nie wynik "
                           "(PREDECLARATION.md §7.5 pkt 2)")

    pending = [h for h in all_hits if h.rule_id.endswith("C5-02?")]
    if pending and not args.manual_c5:
        raise MeasureError(f"{len(pending)} nierozstrzygnietych kandydatow C5-02; "
                           f"wymagany --manual-c5 (coding_manual.md §1, C5)")

    counts = aggregate(all_hits)
    os.makedirs(args.out_dir, exist_ok=True)

    hits_path = os.path.join(args.out_dir, "hits.csv")
    with open(hits_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["label", "metric", "rule_id", "file", "line", "text"])
        for h in all_hits:
            w.writerow([args.label, h.metric, h.rule_id, h.path, h.line, h.text])

    constructs_path = os.path.join(args.out_dir, "constructs.csv")
    with open(constructs_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["label"] + METRICS + ["loc", "cyclomatic", "files"])
        w.writerow([args.label] + [counts[m] for m in METRICS] + [loc_total, cyc_total, scanned])

    print(" ".join(f"{m}={counts[m]}" for m in METRICS)
          + f" loc={loc_total} cyclomatic={cyc_total} files={scanned}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MeasureError as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
