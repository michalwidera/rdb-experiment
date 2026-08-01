#!/usr/bin/env python3
"""Statyczne metryki konstrukcji K22v3.

Najważniejszy inwariant względem pilota: stan jest identyfikowany kluczem
`scope.name`. Jednakowe pola `win` w różnych klasach są różnymi oknami, a
kolektor wyniku nie staje się oknem tylko dlatego, że jest listą.
"""

import argparse
import ast
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


METRICS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C3d", "C4d")
WINDOW_NAME = re.compile(r"(?:^|_)(?:win|window|history|buffer|buf)(?:$|_)", re.I)
CLOCK = (
    "time.monotonic_ns", "time.monotonic", "time.perf_counter_ns", "time.perf_counter",
    "System.nanoTime", "System.currentTimeMillis", "Thread.sleep", "time.sleep",
    "LockSupport.park", "synchronized", "CountDownLatch", "AtomicLong",
)


class MeasureError(RuntimeError):
    pass


@dataclass(frozen=True)
class Hit:
    metric: str
    rule_id: str
    scope: str
    path: str
    line: int
    text: str
    name: str = ""


def core_ranges(lines, path):
    starts, ranges = [], []
    for lineno, raw in enumerate(lines, 1):
        if "CORE_BEGIN" in raw:
            starts.append(lineno + 1)
        if "CORE_END" in raw:
            if not starts:
                raise MeasureError(f"{path}:{lineno}: CORE_END bez CORE_BEGIN")
            ranges.append((starts.pop(), lineno - 1))
    if starts:
        raise MeasureError(f"{path}: CORE_BEGIN bez CORE_END")
    if not ranges:
        raise MeasureError(f"{path}: brak znacznikow CORE_BEGIN/CORE_END")
    return ranges


def in_core(lineno, ranges):
    return any(start <= lineno <= stop for start, stop in ranges)


def _line(lines, node):
    lineno = getattr(node, "lineno", 0)
    return lines[lineno - 1].rstrip() if lineno else ""


def _stored_names(node):
    names = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            names.append(sub.id)
        elif isinstance(sub, ast.Subscript) and isinstance(sub.ctx, ast.Store):
            base = sub.value
            while isinstance(base, (ast.Subscript, ast.Attribute)):
                base = base.value
            if isinstance(base, ast.Name):
                names.append(base.id)
    return names


def _python_scope(tree, node):
    best = "module"
    best_span = None
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = candidate.lineno
        stop = getattr(candidate, "end_lineno", start)
        if start <= node.lineno <= stop:
            span = stop - start
            if best_span is None or span < best_span:
                best = candidate.name
                best_span = span
    return best


def analyze_python(path, lines, ranges):
    tree = ast.parse("".join(lines), filename=path)
    statements = [node for node in ast.walk(tree)
                  if isinstance(node, ast.stmt) and getattr(node, "lineno", 0)
                  and in_core(node.lineno, ranges)]
    loops = [node for node in statements if isinstance(node, (ast.For, ast.While))]
    nested = set()
    for outer in loops:
        for sub in ast.walk(outer):
            if sub is not outer and sub in loops:
                nested.add(sub)
    slot_loops = [node for node in loops if node not in nested]
    loop_lines = set()
    for loop in slot_loops:
        for sub in ast.walk(loop):
            if getattr(sub, "lineno", 0):
                loop_lines.add(sub.lineno)

    hits, claimed = [], set()
    for node in statements:
        line, text = node.lineno, _line(lines, node)
        scope = _python_scope(tree, node)
        if any(token in text for token in CLOCK) or re.search(r"\bdeadline\s*=.*[+*]", text):
            hits.append(Hit("C4", "PY-C4", scope, path, line, text))
            claimed.add(line)
        elif isinstance(node, ast.If) and re.search(r"<\s*(?:[A-Z][A-Z_0-9]+|len\s*\()", text):
            hits.append(Hit("C5", "PY-C5-WARMUP", scope, path, line, text))
            claimed.add(line)
        elif isinstance(node, (ast.For, ast.While)):
            hits.append(Hit("C1", "PY-C1-SLOT" if node in slot_loops else "PY-C1-NESTED",
                            scope, path, line, text))
            claimed.add(line)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and re.search(
                r"\b(?:TAIL|DELAY|LATENCY|WARMUP|SHIFT)\b", text, re.I):
            hits.append(Hit("C5", "PY-C5-CONSTANT", scope, path, line, text))
            claimed.add(line)
        elif isinstance(node, ast.Assign) and "%" in text:
            hits.append(Hit("C5", "PY-C5-PHASE", scope, path, line, text))
            claimed.add(line)

    initialized = {}
    mutated = {}
    shift_names = set()
    for node in statements:
        scope = _python_scope(tree, node)
        key_prefix = f"{scope}."
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for name in _stored_names(node):
                key = key_prefix + name
                if node.lineno in loop_lines:
                    mutated.setdefault(key, (node.lineno, _line(lines, node), name))
                else:
                    initialized.setdefault(key, (node.lineno, _line(lines, node), name))
        if node.lineno in loop_lines:
            text = _line(lines, node)
            for name in re.findall(r"\b([A-Za-z_]\w*)\s*\[[^]]+\]\s*=", text):
                if re.search(rf"\b{re.escape(name)}\s*\[[^]]+\]", text.split("=", 1)[-1]):
                    shift_names.add(key_prefix + name)
            for name in re.findall(r"\b([A-Za-z_]\w*)\.(?:append|appendleft|popleft|rotate)\(", text):
                shift_names.add(key_prefix + name)

    for key in sorted(set(initialized) & set(mutated)):
        line, text, name = initialized[key]
        scope = key.rsplit(".", 1)[0]
        if WINDOW_NAME.search(name) or key in shift_names:
            hits.append(Hit("C3", "PY-C3-WINDOW", scope, path, line, text, key))
        elif name not in {"out", "output", "outputs", "result", "results"}:
            hits.append(Hit("C2", "PY-C2-STATE", scope, path, line, text, key))
        claimed.add(line)
        claimed.add(mutated[key][0])

    for node in statements:
        line, text = node.lineno, _line(lines, node)
        scope = _python_scope(tree, node)
        if re.search(r"\b(?:window|count_window|time_window)\s*=", text):
            hits.append(Hit("C3d", "PY-C3d", scope, path, line, text))
        if re.search(r"\b(?:rate_hz|interval|period)\s*=", text):
            hits.append(Hit("C4d", "PY-C4d", scope, path, line, text))
        if line not in claimed and not isinstance(node, (ast.Import, ast.ImportFrom)):
            hits.append(Hit("C7", "PY-C7", scope, path, line, text))
            claimed.add(line)
    return hits


CLASS_RE = re.compile(r"\bclass\s+(\w+)")
FIELD_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|volatile|transient)\s+)+"
    r"[\w<>, ?\[\]]+\s+(\w+)\s*(?:=[^;]*)?;\s*$"
)


def java_scopes(lines, ranges):
    scopes, stack, depth = {}, [], 0
    for lineno, raw in enumerate(lines, 1):
        if not in_core(lineno, ranges):
            continue
        text = raw.strip()
        match = CLASS_RE.search(text)
        if match:
            stack.append((match.group(1), depth + text.count("{")))
        scopes[lineno] = ".".join(item[0] for item in stack) or "topology"
        depth += text.count("{") - text.count("}")
        while stack and depth < stack[-1][1]:
            stack.pop()
    return scopes


def analyze_java(path, lines, ranges):
    scopes = java_scopes(lines, ranges)
    hits, claimed = [], set()
    fields = {}
    mutations = set()
    window_evidence = set()

    for lineno, raw in enumerate(lines, 1):
        if not in_core(lineno, ranges):
            continue
        text = raw.strip()
        scope = scopes[lineno]
        if not text or text.startswith(("//", "/*", "*", "@Override")):
            continue
        field = FIELD_RE.match(raw)
        if field and scope != "topology":
            name = field.group(1)
            fields[f"{scope}.{name}"] = (lineno, raw.rstrip(), name,
                                         bool(re.search(r"\b(?:final|static)\b", raw)))

        if any(token in text for token in CLOCK) or re.search(r"\bdeadline\s*=.*[+*]", text):
            hits.append(Hit("C4", "JAVA-C4", scope, path, lineno, raw.rstrip()))
            claimed.add(lineno)
        elif re.search(r"\bif\s*\(.*<\s*(?:[A-Z][A-Z_0-9]+|\w+\.length)", text):
            hits.append(Hit("C5", "JAVA-C5-WARMUP", scope, path, lineno, raw.rstrip()))
            claimed.add(lineno)
        elif re.search(r"\b(?:for|while)\s*\(", text):
            hits.append(Hit("C1", "JAVA-C1", scope, path, lineno, raw.rstrip()))
            claimed.add(lineno)
        elif re.search(r"\b(?:TAIL|DELAY|LATENCY|WARMUP|SHIFT)\b", text, re.I) and field:
            hits.append(Hit("C5", "JAVA-C5-CONSTANT", scope, path, lineno, raw.rstrip()))
            claimed.add(lineno)

        for name in re.findall(r"(?<!\.)\b(\w+)\s*(?:\[[^]]+\])?\s*(?:=|\+=|-=|\+\+|--)", text):
            mutations.add(f"{scope}.{name}")
        for name in re.findall(r"\b(\w+)\s*\[[^]]+\]\s*=.*\b\1\s*\[[^]]+\]", text):
            window_evidence.add(f"{scope}.{name}")
        for name in re.findall(r"\b(\w+)\.(?:addLast|pollFirst|rotate)\(", text):
            window_evidence.add(f"{scope}.{name}")

        if re.search(r"\.(?:window|countWindow|timeWindow)\(", text):
            hits.append(Hit("C3d", "JAVA-C3d", scope, path, lineno, raw.rstrip()))
        if re.search(r"\b(?:rateHz|intervalNs)\b", text):
            hits.append(Hit("C4d", "JAVA-C4d", scope, path, lineno, raw.rstrip()))

    # Pola sa mutowane także jako `this.x`; przypisanie konstruktora do finalnego
    # wejścia nie czyni go stanem rekordu. Liczymy tylko niefinalne pola i mapy/
    # liczniki/okna, które mają mutację w tym samym zakresie klasy.
    all_text_by_scope = {}
    for lineno, raw in enumerate(lines, 1):
        if in_core(lineno, ranges):
            all_text_by_scope.setdefault(scopes[lineno], []).append(raw)
    for key, (line, text, name, immutable) in fields.items():
        scope = key.rsplit(".", 1)[0]
        scoped_text = "".join(all_text_by_scope.get(scope, []))
        changed = bool(re.search(rf"(?:this\.)?{re.escape(name)}\s*(?:\[[^]]+\])?\s*"
                                 r"(?:=|\+=|-=|\+\+|--)", scoped_text))
        if immutable or not changed or name == "running":
            continue
        if WINDOW_NAME.search(name) or key in window_evidence:
            hits.append(Hit("C3", "JAVA-C3-WINDOW", scope, path, line, text, key))
        else:
            hits.append(Hit("C2", "JAVA-C2-STATE", scope, path, line, text, key))
        claimed.add(line)

    for lineno, raw in enumerate(lines, 1):
        if not in_core(lineno, ranges):
            continue
        text = raw.strip()
        if not text or text.startswith(("//", "/*", "*", "@Override")) or lineno in claimed:
            continue
        if text.endswith(";") or " class " in f" {text} " or re.search(
                r"\b(?:run|flatMap|map|open|cancel|processElement)\s*\(", text):
            hits.append(Hit("C7", "JAVA-C7", scopes[lineno], path, lineno, raw.rstrip()))
    return hits


def analyze_rql(path, lines, ranges):
    hits = []
    for lineno, raw in enumerate(lines, 1):
        if not in_core(lineno, ranges):
            continue
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if not re.match(r"^(DECLARE|SELECT|RULE)\b", text, re.I):
            continue
        hits.append(Hit("C7", "RQL-C7", "rql", path, lineno, raw.rstrip()))
        for _ in re.finditer(r"@\(", text):
            hits.append(Hit("C3d", "RQL-C3d", "rql", path, lineno, raw.rstrip()))
        if re.match(r"^DECLARE\b", text, re.I) and re.search(r",\s*\d+(?:/\d+)?\s+(?:FILE|DEVICE|TEXTSOURCE)", text):
            hits.append(Hit("C4d", "RQL-C4d", "rql", path, lineno, raw.rstrip()))
    return hits


ANALYZERS = {".py": analyze_python, ".java": analyze_java, ".rql": analyze_rql}


def measure(path):
    path = str(path)
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    analyzer = ANALYZERS.get(Path(path).suffix)
    if not analyzer:
        raise MeasureError(f"{path}: nieobslugiwane rozszerzenie")
    ranges = core_ranges(lines, path)
    hits = analyzer(path, lines, ranges)
    counts = {metric: 0 for metric in METRICS}
    seen = {metric: set() for metric in METRICS}
    for hit in hits:
        key = hit.name or f"{hit.path}:{hit.line}:{hit.rule_id}"
        if key in seen[hit.metric]:
            continue
        seen[hit.metric].add(key)
        counts[hit.metric] += 1
    loc = sum(1 for lineno, raw in enumerate(lines, 1)
              if in_core(lineno, ranges) and raw.strip()
              and not raw.strip().startswith(("#", "//", "/*", "*", "@Override")))
    branches = sum(1 for hit in hits if hit.metric == "C1")
    return counts, hits, loc, 1 + branches


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    totals = {metric: 0 for metric in METRICS}
    all_hits, loc, cyclomatic = [], 0, 0
    for file in args.files:
        counts, hits, file_loc, file_cyc = measure(file)
        for metric in METRICS:
            totals[metric] += counts[metric]
        all_hits.extend(hits)
        loc += file_loc
        cyclomatic += file_cyc
    with (out / "hits.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label"] + list(asdict(all_hits[0]).keys()) if all_hits else
                                ["label", "metric", "rule_id", "scope", "path", "line", "text", "name"])
        writer.writeheader()
        for hit in all_hits:
            writer.writerow({"label": args.label, **asdict(hit)})
    result = {"label": args.label, **totals, "loc": loc, "cyclomatic": cyclomatic, "files": len(args.files)}
    (out / "constructs.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MeasureError, SyntaxError) as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        raise SystemExit(2)

