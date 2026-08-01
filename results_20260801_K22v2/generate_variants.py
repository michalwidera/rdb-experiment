#!/usr/bin/env python3
"""Deterministycznie materializuje 12 zamrożonych wariantów K22v2."""

import re
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PILOT = REPO / "results_20260801_K22"
TASKS = HERE / "tasks"
FAMILIES = {"F1": "F1_fir", "F2": "F2_ecg", "F3": "F3_multirate"}


def die(message):
    raise SystemExit(f"BLAD GENERATORA: {message}")


def replace(text, old, new, count=None):
    found = text.count(old)
    expected = found if count is None else count
    if found != expected or found == 0:
        die(f"zamiana niejednoznaczna: {old!r}, znaleziono {found}, oczekiwano {expected}")
    return text.replace(old, new)


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, text):
    path.write_text(text, encoding="utf-8")


def copy_base(task, family):
    source = PILOT / "corpus" / FAMILIES[family]
    target = TASKS / task / FAMILIES[family]
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return target


def core_paths(root, family):
    java = {"F1": "F1Fir.java", "F2": "F2Ecg.java", "F3": "F3Multirate.java"}[family]
    return root / "rql/core.rql", root / "python/core.py", root / f"flink/{java}"


def generate_m2(family):
    root = copy_base("M2", family)
    rql, py, java = core_paths(root, family)
    rt, pt, jt = read(rql), read(py), read(java)
    if family == "F1":
        rt = replace(rt, "INTEGER[26] STREAM coef", "INTEGER[45] STREAM coef", 1)
        rt = replace(rt, "src@(1,26)", "src@(1,45)", 1)
        rt = replace(rt, "acc[0]/26/1000", "acc[0]/45/1000", 1)
        pt = replace(pt, "WIN = 26", "WIN = 45", 1)
        jt = replace(jt, "private static final int WIN = 26;", "private static final int WIN = 45;", 1)
    elif family == "F2":
        rt = replace(rt, "sq_out@(1,30)", "sq_out@(1,45)", 1)
        pt = replace(pt, "WIN_MWI = 30", "WIN_MWI = 45", 1)
        jt = replace(jt, "static class SquareMwi", "static class SquareMwi", 1)
        marker = "static class SquareMwi"
        before, after = jt.split(marker, 1)
        after = replace(after, "private static final int WIN = 30;", "private static final int WIN = 45;", 1)
        jt = before + marker + after
    else:
        rt = replace(rt, "f3_mix@(1,30)", "f3_mix@(1,45)", 1)
        pt = replace(pt, "WIN = 30", "WIN = 45", 1)
        jt = replace(jt, "private static final int WIN = 30;", "private static final int WIN = 45;", 1)
    write(rql, rt); write(py, pt); write(java, jt)


def generate_m3(family):
    root = copy_base("M3", family)
    rql, py, java = core_paths(root, family)
    rt, pt, jt = read(rql), read(py), read(java)
    if family == "F1":
        rt = replace(rt, "1/1000 FILE 'f1_source.txt'", "1/750 FILE 'f1_source.txt'", 1)
        pt = replace(pt, "INTERVAL_NS = 1_000_000", "INTERVAL_NS = 1_333_333", 1)
        jt = replace(jt, "INTERVAL_NS = 1_000_000L", "INTERVAL_NS = 1_333_333L", 1)
    elif family == "F2":
        rt = replace(rt, "1/360 FILE 'rec205'", "1/250 FILE 'rec205'", 1)
        pt = replace(pt, "INTERVAL_NS = 2_777_778", "INTERVAL_NS = 4_000_000", 1)
        jt = replace(jt, "INTERVAL_NS = 2_777_778L", "INTERVAL_NS = 4_000_000L", 1)
    else:
        rt = replace(rt, "STREAM A, 1/10 FILE", "STREAM A, 1/12 FILE", 1)
        rt = replace(rt, "(A>2)#(B>1)", "(A>12)#(B>5)", 1)
        pt = replace(pt, "UNIT_A = 3", "UNIT_A = 5", 1)
        pt = replace(pt, "UNIT_B = 6", "UNIT_B = 12", 1)
        pt = replace(pt, "INTERVAL_NS = 66_666_667", "INTERVAL_NS = 58_823_529", 1)
        pt = replace(pt, "SHIFT = 5", "SHIFT = 19", 1)
        jt = replace(jt, "INTERVAL_NS = 66_666_667L", "INTERVAL_NS = 58_823_529L", 1)
        jt = replace(jt, "UNIT_A = 3", "UNIT_A = 5", 1)
        jt = replace(jt, "UNIT_B = 6", "UNIT_B = 12", 1)
        jt = replace(jt, "TAIL = 5", "TAIL = 19", 1)
    write(rql, rt); write(py, pt); write(java, jt)


def generate_m1_f2():
    source = PILOT / "tasks/M1/F2_ecg"
    if not source.is_dir():
        die("brak znanego wariantu pilota M1/F2")
    shutil.copytree(source, TASKS / "M1/F2_ecg")


def generate_m1_f1():
    root = copy_base("M1", "F1")
    rql, py, java = core_paths(root, "F1")
    rt = read(rql)
    rt = replace(rt, "DECLARE c INTEGER[26] STREAM coef", "DECLARE x2 INTEGER STREAM channel2, 1/1000 FILE 'f1_source2.txt'\nDECLARE c INTEGER[26] STREAM coef", 1)
    rt = replace(rt, "SELECT acc[0]/26/1000 STREAM f1_out FROM acc.sumc", "SELECT acc[0]/26/1000 STREAM fir FROM acc.sumc\nSELECT fir[0], channel2[0] STREAM f1_out FROM fir+channel2", 1)
    write(rql, rt)

    pt = read(py)
    pt = replace(pt, "def run(samples, coef, slots):", "def run(samples, samples2, coef, slots):", 1)
    pt = replace(pt, "out.append((n + 1, y))", "out.append((n + 1, [y, samples2[n + 1]]))", 1)
    write(py, pt)
    run = read(root / "python/run.py")
    run = replace(run, 'ap.add_argument("--coef", required=True)', 'ap.add_argument("--source2", required=True)\n    ap.add_argument("--coef", required=True)', 1)
    run = replace(run, "rows = run(samples, coef, args.slots)", "samples2 = load_ints(args.source2)\n    rows = run(samples, samples2, coef, args.slots)", 1)
    run = replace(run, "for idx, value in rows:\n            fh.write(f\"{args.family},{args.variant},{idx},f1_out_0,{value},0,0\\n\")", "for idx, values in rows:\n            for name, value in zip((\"f1_out_0\", \"channel_2\"), values):\n                fh.write(f\"{args.family},{args.variant},{idx},{name},{value},0,0\\n\")", 1)
    write(root / "python/run.py", run)

    jt = read(java)
    jt = replace(jt, "import org.apache.flink.api.java.tuple.Tuple2;", "import org.apache.flink.api.java.tuple.Tuple3;", 1)
    jt = replace(jt, "RichSourceFunction<Tuple2<Long, Integer>>", "RichSourceFunction<Tuple3<Long, Integer, Integer>>", 1)
    jt = replace(jt, "private final int[] samples;", "private final int[] samples;\n    private final int[] samples2;", 1)
    jt = replace(jt, "PacedSource(int[] samples, long slots) {\n      this.samples = samples;", "PacedSource(int[] samples, int[] samples2, long slots) {\n      this.samples = samples;\n      this.samples2 = samples2;", 1)
    jt = replace(jt, "SourceContext<Tuple2<Long, Integer>>", "SourceContext<Tuple3<Long, Integer, Integer>>", 1)
    jt = replace(jt, "ctx.collect(Tuple2.of(n, samples[(int) n]));", "ctx.collect(Tuple3.of(n, samples[(int) n], samples2[(int) n + 1]));", 1)
    jt = replace(jt, "RichFlatMapFunction<Tuple2<Long, Integer>, Tuple2<Long, Integer>>", "RichFlatMapFunction<Tuple3<Long, Integer, Integer>, Tuple3<Long, Integer, Integer>>", 1)
    jt = replace(jt, "Tuple2<Long, Integer> in, Collector<Tuple2<Long, Integer>> out", "Tuple3<Long, Integer, Integer> in, Collector<Tuple3<Long, Integer, Integer>> out", 1)
    jt = replace(jt, "out.collect(Tuple2.of(in.f0 + 1, y));", "out.collect(Tuple3.of(in.f0 + 1, y, in.f2));", 1)
    jt = replace(jt, "RichSinkFunction<Tuple2<Long, Integer>>", "RichSinkFunction<Tuple3<Long, Integer, Integer>>", 1)
    jt = replace(jt, "invoke(Tuple2<Long, Integer> rec)", "invoke(Tuple3<Long, Integer, Integer> rec)", 1)
    jt = replace(jt, 'writer.write(family + "," + variant + "," + rec.f0 + ",f1_out_0," + rec.f1 + ",0,0");\n      writer.newLine();', 'writer.write(family + "," + variant + "," + rec.f0 + ",f1_out_0," + rec.f1 + ",0,0");\n      writer.newLine();\n      writer.write(family + "," + variant + "," + rec.f0 + ",channel_2," + rec.f2 + ",0,0");\n      writer.newLine();', 1)
    jt = replace(jt, 'String coefPath = argVal(args, "--coef", null);', 'String source2 = argVal(args, "--source2", null);\n    String coefPath = argVal(args, "--coef", null);', 1)
    jt = replace(jt, "if (source == null || coefPath == null)", "if (source == null || source2 == null || coefPath == null)", 1)
    jt = replace(jt, "int[] coef = loadInts(coefPath);", "int[] samples2 = loadInts(source2);\n    int[] coef = loadInts(coefPath);", 1)
    jt = replace(jt, "DataStream<Tuple2<Long, Integer>> src = env.addSource(new PacedSource(samples, slots));", "DataStream<Tuple3<Long, Integer, Integer>> src = env.addSource(new PacedSource(samples, samples2, slots));", 1)
    write(java, jt)


def generate_m1_f3():
    root = copy_base("M1", "F3")
    rql, py, java = core_paths(root, "F3")
    rt = read(rql)
    rt = replace(rt, "DECLARE value INTEGER STREAM A", "DECLARE value INTEGER, aux INTEGER STREAM A", 1)
    rt = replace(rt, "DECLARE value INTEGER STREAM B", "DECLARE value INTEGER, aux INTEGER STREAM B", 1)
    rt = replace(rt, "FILE 'f3_a.txt'", "FILE 'f3_a2.txt'", 1)
    rt = replace(rt, "FILE 'f3_b.txt'", "FILE 'f3_b2.txt'", 1)
    rt = replace(rt, "SELECT f3_win[0] STREAM f3_out FROM f3_win.avg", "SELECT f3_win[0], f3_win[1] STREAM f3_out FROM f3_win.avg", 1)
    write(rql, rt)

    pt = read(py)
    pt = replace(pt, "def run(a_values, b_values, slots):", "def run(a_values, a_aux, b_values, b_aux, slots):", 1)
    pt = replace(pt, "win = [0] * WIN", "win = [0] * WIN\n    aux_win = [0] * WIN", 1)
    pt = replace(pt, "value = b_values[ib]\n            ib = ib + 1", "value = b_values[ib]\n            aux = b_aux[ib]\n            ib = ib + 1", 1)
    pt = replace(pt, "value = a_values[ia]\n            ia = ia + 1", "value = a_values[ia]\n            aux = a_aux[ia]\n            ia = ia + 1", 1)
    pt = replace(pt, "win[k] = win[k - 1]", "win[k] = win[k - 1]\n            aux_win[k] = aux_win[k - 1]", 1)
    pt = replace(pt, "win[0] = value", "win[0] = value\n        aux_win[0] = aux", 1)
    pt = replace(pt, "out.append((SHIFT + r + 1, avg(win)))", "out.append((SHIFT + r + 1, [avg(win), avg(aux_win)]))", 1)
    write(py, pt)
    run = read(root / "python/run.py")
    run = replace(run, "rows = run(load_ints(args.a), load_ints(args.b), args.slots)", "a = load_ints(args.a)\n    b = load_ints(args.b)\n    rows = run(a, [20000 + i for i in range(len(a))], b,\n               [30000 + i for i in range(len(b))], args.slots)", 1)
    run = replace(run, "for idx, value in rows:\n            fh.write(f\"{args.family},{args.variant},{idx},f3_out_0,{value},0,0\\n\")", "for idx, values in rows:\n            for name, value in zip((\"f3_out_0\", \"f3_out_1\"), values):\n                fh.write(f\"{args.family},{args.variant},{idx},{name},{value},0,0\\n\")", 1)
    write(root / "python/run.py", run)

    jt = read(java)
    jt = replace(jt, "import org.apache.flink.api.java.tuple.Tuple2;", "import org.apache.flink.api.java.tuple.Tuple3;", 1)
    jt = jt.replace("Tuple2<Long, Integer>", "Tuple3<Long, Integer, Integer>")
    jt = replace(jt, "private final int[] b;", "private final int[] b;\n    private final int[] aAux;\n    private final int[] bAux;", 1)
    jt = replace(jt, "MergedSource(int[] a, int[] b, long slots) {", "MergedSource(int[] a, int[] b, int[] aAux, int[] bAux, long slots) {", 1)
    jt = replace(jt, "this.b = b;\n      this.slots", "this.b = b;\n      this.aAux = aAux;\n      this.bAux = bAux;\n      this.slots", 1)
    jt = replace(jt, "int value;", "int value;\n        int aux;", 1)
    jt = replace(jt, "value = b[ib];\n          ib", "value = b[ib];\n          aux = bAux[ib];\n          ib", 1)
    jt = replace(jt, "value = a[ia];\n          ia", "value = a[ia];\n          aux = aAux[ia];\n          ia", 1)
    jt = replace(jt, "ctx.collect(Tuple2.of(TAIL + r, value));", "ctx.collect(Tuple3.of(TAIL + r, value, aux));", 1)
    jt = replace(jt, "private int[] win;", "private int[] win;\n    private int[] auxWin;", 1)
    jt = replace(jt, "win = new int[WIN];", "win = new int[WIN];\n      auxWin = new int[WIN];", 1)
    jt = replace(jt, "win[k] = win[k - 1];", "win[k] = win[k - 1];\n        auxWin[k] = auxWin[k - 1];", 1)
    jt = replace(jt, "win[0] = in.f1;", "win[0] = in.f1;\n      auxWin[0] = in.f2;", 1)
    jt = replace(jt, "long sum = 0;", "long sum = 0;\n      long auxSum = 0;", 1)
    jt = replace(jt, "sum += win[k];", "sum += win[k];\n        auxSum += auxWin[k];", 1)
    jt = replace(jt, "out.collect(Tuple2.of(in.f0 + 1, (int) (sum / WIN)));", "out.collect(Tuple3.of(in.f0 + 1, (int) (sum / WIN), (int) (auxSum / WIN)));", 1)
    jt = replace(jt, "invoke(Tuple3<Long, Integer, Integer> r)", "invoke(Tuple3<Long, Integer, Integer> r)", 1)
    jt = replace(jt, 'writer.write(family + "," + variant + "," + r.f0 + ",f3_out_0," + r.f1 + ",0,0");\n      writer.newLine();', 'writer.write(family + "," + variant + "," + r.f0 + ",f3_out_0," + r.f1 + ",0,0");\n      writer.newLine();\n      writer.write(family + "," + variant + "," + r.f0 + ",f3_out_1," + r.f2 + ",0,0");\n      writer.newLine();', 1)
    jt = replace(jt, "int[] b = loadInts(bPath);", "int[] b = loadInts(bPath);\n    int[] aAux = new int[a.length];\n    int[] bAux = new int[b.length];\n    for (int i = 0; i < a.length; i++) aAux[i] = 20000 + i;\n    for (int i = 0; i < b.length; i++) bAux[i] = 30000 + i;", 1)
    jt = replace(jt, "new MergedSource(a, b, slots)", "new MergedSource(a, b, aAux, bAux, slots)", 1)
    write(java, jt)


def monitor_java(jt, family):
    jt = replace(jt, "import org.apache.flink.api.java.tuple.Tuple2;", "import org.apache.flink.api.java.tuple.Tuple2;\nimport org.apache.flink.api.java.tuple.Tuple9;\nimport org.apache.flink.api.common.functions.RichMapFunction;", 1) if family != "F2" else replace(jt, "import org.apache.flink.api.java.tuple.Tuple5;", "import org.apache.flink.api.java.tuple.Tuple5;\nimport org.apache.flink.api.java.tuple.Tuple9;\nimport org.apache.flink.api.common.functions.RichMapFunction;", 1)
    input_type = "Tuple5<Long, Integer, Integer, Integer, Integer>" if family == "F2" else "Tuple2<Long, Integer>"
    value = "in.f3" if family == "F2" else "in.f1"
    monitor = f'''\n  static class Monitor extends RichMapFunction<{input_type},
      Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer>> {{
    @Override
    public Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer> map({input_type} in) {{
      int v = {value};
      return Tuple9.of(in.f0, v, v + 1, v + 2, v + 3, v + 4, v + 5, v + 6, v + 7);
    }}
  }}
'''
    marker = "  // CORE_END"
    first = jt.find(marker)
    if first < 0:
        die("Java: brak pierwszego CORE_END")
    jt = jt[:first] + monitor + jt[first:]
    sink_old = "Tuple4<Long, Integer, Integer, Integer>" if family == "F2" else "Tuple2<Long, Integer>"
    jt = jt.replace(f"RichSinkFunction<{sink_old}>", "RichSinkFunction<Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer>>", 1)
    rec = "r" if family != "F1" else "rec"
    jt = jt.replace(f"invoke({sink_old} {rec})", f"invoke(Tuple9<Long, Integer, Integer, Integer, Integer, Integer, Integer, Integer, Integer> {rec})", 1)
    start = jt.index("    @Override\n    public void invoke(")
    body_start = jt.index(" {\n", start) + 3
    body_end = jt.index("    }\n\n    @Override", body_start)
    prefix = "f1_q" if family == "F1" else ("mwi_q" if family == "F2" else "f3_q")
    body = f'''      for (int j = 1; j <= 8; j++) {{
        Object value = {rec}.getField(j);
        writer.write(family + "," + variant + "," + {rec}.f0 + ",{prefix}_" + (j - 1) + "," + value + ",0,0");
        writer.newLine();
      }}
'''
    jt = jt[:body_start] + body + jt[body_end:]
    return jt


def generate_m4(family):
    root = copy_base("M4", family)
    rql, py, java = core_paths(root, family)
    rt, pt, jt = read(rql), read(py), read(java)
    values = ", ".join(f"{{stream}}[0]+{j}" for j in range(8))
    if family == "F1":
        rt = rt.replace("# CORE_END", "SELECT " + values.format(stream="f1_out") + " STREAM f1_q FROM f1_out\n# CORE_END", 1)
        pt = replace(pt, "out.append((n + 1, y))", "out.append((n + 1, [y + j for j in range(8)]))", 1)
        jt = monitor_java(jt, family)
        jt = replace(jt, "src.flatMap(new Fir(coef)).addSink", "src.flatMap(new Fir(coef)).map(new Monitor()).addSink", 1)
    elif family == "F2":
        rt = rt.replace("# CORE_END", "SELECT " + values.format(stream="mwi") + " STREAM mwi_q FROM mwi\n# CORE_END", 1)
        pt = replace(pt, "out = []", "out = []\n    monitors = []", 1)
        pt = replace(pt, "mwi_at[n + 3] = mwi", "mwi_at[n + 3] = mwi\n                    monitors.append((n + 3, [mwi + j for j in range(8)]))", 1)
        pt = replace(pt, "return out", "return monitors", 1)
        jt = monitor_java(jt, family)
        jt = replace(jt, "return Tuple9.of(in.f0, v,", "return Tuple9.of(in.f0 + 3, v,", 1)
        old = '''    DataStream<Tuple5<Long, Integer, Integer, Integer, Integer>> src =
        env.addSource(new PacedSource(mlii, slots));
    src.flatMap(new BandPass(bpCoef))
        .flatMap(new Derivative(dCoef))
        .flatMap(new SquareMwi())
        .flatMap(new Threshold())
        .flatMap(new Assemble())
        .addSink(new CanonicalSink(out, family, variant));'''
        new = '''    DataStream<Tuple5<Long, Integer, Integer, Integer, Integer>> src =
        env.addSource(new PacedSource(mlii, slots));
    src.flatMap(new BandPass(bpCoef))
        .flatMap(new Derivative(dCoef))
        .flatMap(new SquareMwi())
        .map(new Monitor())
        .addSink(new CanonicalSink(out, family, variant));'''
        jt = replace(jt, old, new, 1)
    else:
        rt = rt.replace("# CORE_END", "SELECT " + values.format(stream="f3_mix") + " STREAM f3_q FROM f3_mix\n# CORE_END", 1)
        pt = replace(pt, "out = []", "out = []\n    monitors = []", 1)
        pt = replace(pt, "for k in range(WIN - 1, 0, -1):", "monitors.append((SHIFT + r, [value + j for j in range(8)]))\n        for k in range(WIN - 1, 0, -1):", 1)
        pt = replace(pt, "return out", "return monitors", 1)
        jt = monitor_java(jt, family)
        jt = replace(jt, "src.flatMap(new Aggregate()).addSink", "src.map(new Monitor()).addSink", 1)
    write(rql, rt); write(py, pt); write(java, jt)
    run = read(root / "python/run.py")
    old = {"F1": "f1_out_0", "F2": "qrs_out_", "F3": "f3_out_0"}[family]
    # Zastąpienie harnessu prostym emiterem listy 8 pól pozostaje poza CORE.
    if family == "F1":
        run = replace(run, "for idx, value in rows:\n            fh.write(f\"{args.family},{args.variant},{idx},f1_out_0,{value},0,0\\n\")", "for idx, values in rows:\n            for j, value in enumerate(values):\n                fh.write(f\"{args.family},{args.variant},{idx},f1_q_{j},{value},0,0\\n\")", 1)
    elif family == "F2":
        run = replace(run, "for name, value in zip(FIELDS, values):", "for name, value in zip([f\"mwi_q_{j}\" for j in range(8)], values):", 1)
    else:
        run = replace(run, "for idx, value in rows:\n            fh.write(f\"{args.family},{args.variant},{idx},f3_out_0,{value},0,0\\n\")", "for idx, values in rows:\n            for j, value in enumerate(values):\n                fh.write(f\"{args.family},{args.variant},{idx},f3_q_{j},{value},0,0\\n\")", 1)
    write(root / "python/run.py", run)


def main():
    predecl = read(HERE / "PREDECLARATION.md")
    match = re.search(r"Commit zamrażający aparaturę \| `([0-9a-f]{40})`", predecl)
    if not match:
        die("PREDECLARATION.md nie zawiera pełnego commita zamrażającego")
    freeze = match.group(1)
    subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", freeze, "HEAD"], check=True)
    if TASKS.exists() and any(TASKS.iterdir()):
        die(f"{TASKS} nie jest puste; generator nie nadpisuje wariantów")
    TASKS.mkdir(parents=True, exist_ok=True)
    generate_m1_f1(); generate_m1_f2(); generate_m1_f3()
    for family in FAMILIES:
        generate_m2(family)
        generate_m3(family)
        generate_m4(family)
    for path in TASKS.rglob("run.sh"):
        path.chmod(0o755)
    print("OK: wygenerowano 12 wariantów K22v2")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as exc:
        die(str(exc))
