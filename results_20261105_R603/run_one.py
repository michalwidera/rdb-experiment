#!/usr/bin/env python3
"""R603: jeden przebieg --realtime z seria podlaczen `xqry -s <strumien> -m 1` (runner R600, binarki R603).

Uzycie: run_one.py --side B|Bp --family ucNN --run K --stream NAZWA --out KATALOG [--conns 30]

Zmiany wobec R600: strony B i Bp (B') z ~/R376/bin/R603_<strona> (BIN_PREFIX); setcap z cap_perfmon
(latka P2 czyta liczniki PMU, perf_event_paranoid = 4); kopia logu silnika ($TMPDIR/xretractor.log)
do engine.log (ostrzezenia P2/P3); przebieg niewazny, gdy po pierwszym slocie kolumny P2 maja -1.
Sciezka uruchomienia ~/R376/exec i katalog pracy /dev/shm/r376/run bez zmian.

Obie strony startuja z tej samej sciezki ~/R376/exec/xretractor (ten sam argv[0]); katalog pracy
/dev/shm/r376/run. Binarka nie moze lezec w /dev/shm: montowanie nosuid ignoruje uprawnienia pliku
(setcap), a bez nich silnik nie dostaje SCHED_FIFO ani mlockall.
Zapisuje do --out:
  slots.csv   - CSV sondy slotu z latka P1 (kolumna deadline_ns, CLOCK_MONOTONIC),
  trace.txt   - ftrace (trace_clock=mono) wywolan openat/statfs/fstatfs/ftruncate/fallocate/mmap/
                munmap/unlinkat watkow procesu silnika; okno budowy kolejki wyznacza analiza,
  conns.tsv   - czasy CLOCK_MONOTONIC startu, pierwszego wiersza i konca kazdego klienta oraz kod wyjscia,
  rt.txt      - polityka, priorytet, powinowactwo kazdego watku i VmLck procesu,
  meta.json   - strona, rodzina, ziarno, sumy binarek, stan governora.
"""

import argparse
import hashlib
import json
import os
import random
import select
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / "R376"
RUN = Path("/dev/shm/r376/run")
EXEC = ROOT / "exec"
DATA = Path("/dev/shm/r376/data")
TRACEFS = Path("/sys/kernel/tracing")
SYSCALLS = ["openat", "statfs", "fstatfs", "ftruncate", "fallocate", "mmap", "munmap", "unlinkat"]
RT_UNTRACED = {"openat", "statfs", "fstatfs"}
WARMUP_S = 5.0
GAP_MIN_S, GAP_MAX_S = 2.0, 3.0
CLIENT_TIMEOUT_S = 15.0
RELEASE_TAIL_S = 12.0
# Rdzen izolowany workera (isolcpus=3 nohz_full=3 rcu_nocbs=3), jak w kampaniach K23v2..K26v3. Silnik z -t
# bierze rdzenie RT z maski procesu i przenosi watek komunikacyjny na pozostale; bez taskset
# watek slotu dzielil rdzenie 0-2 z reszta systemu, a komunikacyjny dostawal rdzen izolowany.
RT_CPU = "3"
BIN_PREFIX = "R603_"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracefs_write(name, value):
    subprocess.run(["sudo", "-n", "tee", str(TRACEFS / name)], input=value.encode(), stdout=subprocess.DEVNULL,
                   check=True)


def trace_start(tids, rt):
    tracefs_write("tracing_on", "0")
    tracefs_write("trace", "")
    tracefs_write("trace_clock", "mono")
    tracefs_write("buffer_size_kb", "16384")
    tracefs_write("set_event_pid", " ".join(str(t) for t in tids))
    # Watek slotu otwiera pliki zrodel TEXTFILE w kazdym slocie; okno budowy kolejki zaczyna sie
    # od tych wywolan w watku komunikacyjnym, wiec dla watku RT nie sa potrzebne, a ich zapis
    # obciazalby slot. munmap/unlinkat zostaja dla wszystkich watkow (zwolnienie kolejki w broadcast()).
    rt_filter = " && ".join(f"common_pid != {t}" for t in rt) or "0"
    for call in SYSCALLS:
        for kind in ("enter", "exit"):
            event = f"events/syscalls/sys_{kind}_{call}"
            tracefs_write(f"{event}/filter", rt_filter if call in RT_UNTRACED else "0")
            tracefs_write(f"{event}/enable", "1")
    tracefs_write("tracing_on", "1")


def trace_stop(dest):
    tracefs_write("tracing_on", "0")
    with open(dest, "wb") as out:
        subprocess.run(["sudo", "-n", "cat", str(TRACEFS / "trace")], stdout=out, check=True)
    for call in SYSCALLS:
        for kind in ("enter", "exit"):
            tracefs_write(f"events/syscalls/sys_{kind}_{call}/enable", "0")
            tracefs_write(f"events/syscalls/sys_{kind}_{call}/filter", "0")
    tracefs_write("set_event_pid", "")
    tracefs_write("trace", "")


def client(stream, env):
    """Jedno podlaczenie: (start_ns, first_row_ns, end_ns, rc).

    `xqry -s S -m 1` po pierwszym elemencie oproznia kolejke po jednym elemencie na
    kQueuePollInterval (1 ms) i na strumieniu szybszym niz ~1 kHz nie konczy sie nigdy
    (qry.cpp, petla za `while (!transport_->done)`). Dlatego klient jest zamykany SIGINT
    zaraz po pierwszym wierszu - jednakowo w obu stronach i we wszystkich rodzinach.
    Serwer nie dowiaduje sie o wyjsciu klienta ani przy SIGINT, ani przy zwyklym wyjsciu.
    """
    t0 = time.monotonic_ns()
    p = subprocess.Popen([str(EXEC / "xqry"), "-s", stream, "-m", "1"], cwd=RUN, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    first = None
    ready, _, _ = select.select([p.stdout], [], [], CLIENT_TIMEOUT_S)
    if ready and p.stdout.readline():
        first = time.monotonic_ns()
    p.send_signal(signal.SIGINT)
    try:
        rc = p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        rc = "killed"
    if first is None:
        rc = f"no_row:{rc}"
    return t0, first if first is not None else "-", time.monotonic_ns(), rc


def rt_report(pid):
    lines, rt = [], []
    for tid in sorted(int(t) for t in os.listdir(f"/proc/{pid}/task")):
        sched = subprocess.run(["chrt", "-p", str(tid)], capture_output=True, text=True).stdout.split("\n")
        aff = subprocess.run(["taskset", "-cp", str(tid)], capture_output=True, text=True).stdout.strip()
        policy = sched[0].split(":")[-1].strip()
        prio = sched[1].split(":")[-1].strip() if len(sched) > 1 else "?"
        if policy == "SCHED_FIFO":
            rt.append(tid)
        lines.append(f"tid={tid}\tpolicy={policy}\tprio={prio}\t{aff.split(':')[-1].strip()}")
    vmlck = next(l for l in open(f"/proc/{pid}/status") if l.startswith("VmLck")).split()[1]
    lines.append(f"VmLck_kB={vmlck}")
    return lines, len(rt), int(vmlck), rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["B", "Bp"], required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--stream", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--conns", type=int, default=30)
    args = ap.parse_args()

    seed = int.from_bytes(os.urandom(4), "little")
    rng = random.Random(seed)
    args.out.mkdir(parents=True, exist_ok=False)

    # Swiezy katalog pracy pod ta sama sciezka dla obu stron.
    shutil.rmtree(RUN, ignore_errors=True)
    shutil.copytree(DATA / args.family, RUN)
    (RUN / "temp").mkdir(exist_ok=True)
    build = ROOT / "bin" / f"{BIN_PREFIX}{args.side}"
    shutil.rmtree(EXEC, ignore_errors=True)
    EXEC.mkdir()
    shutil.copy2(build / "xretractor", EXEC / "xretractor")
    shutil.copy2(build / "xqry", EXEC / "xqry")
    subprocess.run(["sudo", "-n", "setcap", "cap_ipc_lock,cap_sys_nice,cap_perfmon=ep", str(EXEC / "xretractor")], check=True)

    governor = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    meta = {"side": args.side, "family": args.family, "run": args.run, "seed": seed, "governor": governor,
            "sched_rt_runtime_us": Path("/proc/sys/kernel/sched_rt_runtime_us").read_text().strip(),
            "conns": args.conns, "xretractor_sha256": sha256(EXEC / "xretractor"),
            "xqry_sha256": sha256(EXEC / "xqry"), "build_xretractor_sha256": sha256(build / "xretractor"),
            "bin_dir": str(build)}
    if governor != "performance":
        sys.exit(f"governor={governor}, wymagany performance")

    env = dict(os.environ, RDB_BENCH_CSV=str(RUN / "slots.csv"), TMPDIR=str(RUN / "temp"))
    engine_log = open(args.out / "engine.out", "wb")
    engine = subprocess.Popen(["taskset", "-c", RT_CPU, str(EXEC / "xretractor"), "query.rql", "-k", "-r", "-t"], cwd=RUN, env=env, stdout=engine_log,
                              stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(WARMUP_S)
    if engine.poll() is not None:
        sys.exit(f"silnik zakonczyl sie przed seria podlaczen, kod {engine.returncode}")

    rt_lines, fifo, vmlck, rt = rt_report(engine.pid)
    (args.out / "rt.txt").write_text("\n".join(rt_lines) + "\n")
    meta.update(rt_fifo_threads=fifo, rt_vmlck_kB=vmlck)
    rt_ok = fifo >= 1 and vmlck > 0

    conns = ["i\tstart_ns\tfirst_row_ns\tend_ns\trc"]
    if rt_ok:
        trace_start([int(t) for t in os.listdir(f"/proc/{engine.pid}/task")], rt)
        for i in range(args.conns):
            time.sleep(rng.uniform(GAP_MIN_S, GAP_MAX_S))
            conns.append("\t".join(str(v) for v in (i, *client(args.stream, env))))
        # Kolejka klienta zyje po jego wyjsciu, az sie zapelni (10 s danych), i dopiero wtedy
        # broadcast() ja zwalnia - slad musi objac zwolnienie ostatniej.
        time.sleep(RELEASE_TAIL_S)
        trace_stop(args.out / "trace.txt")
    (args.out / "conns.tsv").write_text("\n".join(conns) + "\n")

    engine.send_signal(signal.SIGTERM)
    try:
        meta["engine_rc"] = engine.wait(timeout=30)
    except subprocess.TimeoutExpired:
        engine.kill()
        meta["engine_rc"] = "killed"
    shutil.move(RUN / "slots.csv", args.out / "slots.csv")
    if (RUN / "temp" / "xretractor.log").exists():
        shutil.copy2(RUN / "temp" / "xretractor.log", args.out / "engine.log")
    with open(args.out / "slots.csv") as f:
        header = f.readline().strip().split(",")
        rows = [l for l in f][1:]  # pierwszy slot otwiera liczniki
    pmu_bad = sum(1 for l in rows if "-1" in l.strip().split(",")[5:])
    meta.update(pmu_columns=len(header) - 5, pmu_invalid_rows=pmu_bad)
    meta["rt_ok"] = rt_ok
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    if not rt_ok:
        sys.exit("brak watku SCHED_FIFO albo VmLck=0 - przebieg niewazny")
    if len(header) != 17 or pmu_bad:
        sys.exit(f"kolumny P2: {len(header) - 5}, wiersze z -1: {pmu_bad} - przebieg niewazny")


if __name__ == "__main__":
    main()
