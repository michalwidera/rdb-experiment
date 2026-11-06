#!/usr/bin/env python3
"""R603G: jeden przebieg --realtime z N dlugo zyjacymi subskrybentami `xqry -s <strumien>` bez -m (README R603G).

Uzycie: run_one.py --side Cp|D2s --family uc05 --run K --n N --stream NAZWA --out KATALOG [--window 60]

Wobec R603F (README R603G, Aparatura, punkt 2): zamiast serii krotkich podlaczen N subskrybentow podlaczanych po kolei
(nastepny po pierwszym wierszu poprzedniego i przerwie 0,25 s), ustalenie 5 s, slad tylko w oknie pomiaru (60 s).
Klient `xqry` z R603D_Cp po obu stronach (G3). Sledzone wywolania, filtry, bufor ftrace, sciezka uruchomienia
~/R376/exec i katalog pracy /dev/shm/r376/run bez zmian. Wyjscie klientow (dane korpusu) zostaje w /dev/shm/r376/run
i jest kasowane po przebiegu; do --out trafiaja tylko liczby wierszy.

Zapisuje do --out:
  slots.csv   - CSV sondy slotu z latka P1 (deadline_ns, CLOCK_MONOTONIC), caly przebieg,
  trace.txt   - ftrace (trace_clock=mono) watkow silnika w oknie pomiaru,
  clients.tsv - i, pid, start_ns, first_row_ns, wiersze i chwila liczenia na poczatku i koncu okna, zywy na koncu okna,
  window.json - granice okna (start i stop sladu, CLOCK_MONOTONIC),
  cpu.txt     - wiersze cpu0..cpu2 z /proc/stat na poczatku i koncu okna,
  rt.txt      - polityka, priorytet, powinowactwo kazdego watku i VmLck procesu,
  meta.json   - strona, rodzina, N, sumy binarek, governor, overrun, pozostalosci w /dev/shm.
"""

import argparse
import hashlib
import json
import os
import shlex
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
SHM = Path("/dev/shm")
TRACEFS = Path("/sys/kernel/tracing")
SYSCALLS = ["openat", "statfs", "fstatfs", "ftruncate", "fallocate", "mmap", "munmap", "unlinkat", "renameat", "renameat2",
            "kill", "futex", "clock_nanosleep", "nanosleep"]
RT_UNTRACED = {"openat", "statfs", "fstatfs", "kill", "clock_nanosleep", "nanosleep"}
RT_ONLY = {"futex"}
WARMUP_S = 5.0
CONNECT_GAP_S = 0.25
FIRST_ROW_TIMEOUT_S = 15.0
SETTLE_S = 5.0
RT_CPU = "3"
# Aneks A4(b): watek komunikacyjny sam na rdzeniu 0, klienci (i runner, campaign.sh) na rdzeniach 1-2.
COMM_CPU = "0"
CLIENT_CPUS = "1,2"
BIN_DIR = {"Cp": "R603D_Cp", "D2s": "R603F_D2s"}
CLIENT_BIN_DIR = "R603D_Cp"  # G3: ten sam xqry po obu stronach
QUEUE_PREFIX = "brcdbr"  # kResponseQueuePrefix: obiekty kolejek odpowiedzi w /dev/shm


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracefs_batch(writes):
    """Zapisy do tracefs w kolejnosci, jednym wywolaniem sudo (aneks A2: ~60 osobnych `sudo tee` przy N obciazonych
    klientach trwalo ~75 s)."""
    script = "\n".join(f"printf %s {shlex.quote(v)} > {shlex.quote(str(TRACEFS / n))}" for n, v in writes)
    subprocess.run(["sudo", "-n", "sh", "-e", "-c", script], check=True)


def trace_start(tids, rt):
    rt_filter = " && ".join(f"common_pid != {t}" for t in rt) or "0"
    rt_only = " || ".join(f"common_pid == {t}" for t in rt)
    writes = [("tracing_on", "0"), ("trace", ""), ("trace_clock", "mono"), ("buffer_size_kb", "65536"),
              ("set_event_pid", " ".join(str(t) for t in tids))]
    for call in SYSCALLS:
        if call in RT_ONLY and not rt_only:
            continue
        for kind in ("enter", "exit"):
            event = f"events/syscalls/sys_{kind}_{call}"
            filt = rt_filter if call in RT_UNTRACED else (rt_only if call in RT_ONLY else "0")
            writes += [(f"{event}/filter", filt), (f"{event}/enable", "1")]
    writes.append(("tracing_on", "1"))
    tracefs_batch(writes)


def trace_overrun():
    total = 0
    for stats in sorted(TRACEFS.glob("per_cpu/cpu*/stats")) or []:
        text = subprocess.run(["sudo", "-n", "cat", str(stats)], capture_output=True, text=True, check=True).stdout
        total += int(next(l for l in text.splitlines() if l.startswith("overrun:")).split()[1])
    return total


def trace_stop(dest):
    tracefs_batch([("tracing_on", "0")])
    overrun = trace_overrun()
    with open(dest, "wb") as out:
        subprocess.run(["sudo", "-n", "cat", str(TRACEFS / "trace")], stdout=out, check=True)
    writes = []
    for call in SYSCALLS:
        for kind in ("enter", "exit"):
            writes += [(f"events/syscalls/sys_{kind}_{call}/enable", "0"), (f"events/syscalls/sys_{kind}_{call}/filter", "0")]
    tracefs_batch(writes + [("set_event_pid", ""), ("trace", "")])
    return overrun


def leftovers():
    return sorted(p.name for p in SHM.iterdir() if p.name.startswith(QUEUE_PREFIX))


def count_rows(path):
    """(liczba wierszy, chwila CLOCK_MONOTONIC po policzeniu)."""
    n = 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            n += chunk.count(b"\n")
    return n, time.monotonic_ns()


def cpu_lines():
    return [l for l in Path("/proc/stat").read_text().splitlines() if l.split()[0] in ("cpu0", "cpu1", "cpu2")]


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


def connect(i, stream, env):
    """Start klienta bez -m; czeka na pierwszy wiersz w pliku wyjscia. (Popen, sciezka wyjscia, start_ns, first_ns)."""
    out_path = RUN / "temp" / f"client_{i:02d}.out"
    out = open(out_path, "wb")
    t0 = time.monotonic_ns()
    p = subprocess.Popen(["taskset", "-c", CLIENT_CPUS, str(EXEC / "xqry"), "-s", stream], cwd=RUN, env=env, stdout=out, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)
    out.close()
    first = None
    deadline = time.monotonic() + FIRST_ROW_TIMEOUT_S
    while time.monotonic() < deadline and p.poll() is None:
        if out_path.stat().st_size > 0:
            first = time.monotonic_ns()
            break
        time.sleep(0.005)
    return p, out_path, t0, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["Cp", "D2s"], required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--stream", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--window", type=float, default=60.0)
    args = ap.parse_args()

    left = leftovers()
    if left:
        sys.exit(f"pozostalosci kolejek odpowiedzi w /dev/shm przed przebiegiem: {left}")
    args.out.mkdir(parents=True, exist_ok=False)

    shutil.rmtree(RUN, ignore_errors=True)
    shutil.copytree(DATA / args.family, RUN)
    (RUN / "temp").mkdir(exist_ok=True)
    build = ROOT / "bin" / BIN_DIR[args.side]
    client_build = ROOT / "bin" / CLIENT_BIN_DIR
    shutil.rmtree(EXEC, ignore_errors=True)
    EXEC.mkdir()
    shutil.copy2(build / "xretractor", EXEC / "xretractor")
    shutil.copy2(client_build / "xqry", EXEC / "xqry")
    subprocess.run(["sudo", "-n", "setcap", "cap_ipc_lock,cap_sys_nice=ep", str(EXEC / "xretractor")], check=True)

    governor = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    meta = {"side": args.side, "family": args.family, "run": args.run, "n": args.n, "window_s": args.window,
            "governor": governor, "sched_rt_runtime_us": Path("/proc/sys/kernel/sched_rt_runtime_us").read_text().strip(),
            "xretractor_sha256": sha256(EXEC / "xretractor"), "xqry_sha256": sha256(EXEC / "xqry"),
            "build_xretractor_sha256": sha256(build / "xretractor"), "bin_dir": str(build),
            "client_bin_dir": str(client_build)}
    if governor != "performance":
        sys.exit(f"governor={governor}, wymagany performance")

    env = dict(os.environ, RDB_BENCH_CSV=str(RUN / "slots.csv"), TMPDIR=str(RUN / "temp"))
    engine_log = open(args.out / "engine.out", "wb")
    engine = subprocess.Popen(["taskset", "-c", RT_CPU, str(EXEC / "xretractor"), "query.rql", "-k", "-r", "-t"], cwd=RUN,
                              env=env, stdout=engine_log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(WARMUP_S)
    if engine.poll() is not None:
        sys.exit(f"silnik zakonczyl sie przed podlaczeniami, kod {engine.returncode}")

    rt_lines, fifo, vmlck, rt = rt_report(engine.pid)
    meta.update(rt_fifo_threads=fifo, rt_vmlck_kB=vmlck)
    rt_ok = fifo >= 1 and vmlck > 0
    # Aneks A4(b): kazdy watek spoza SCHED_FIFO (watek komunikacyjny) na rdzen 0; sprawdzane w rt.txt po podlaczeniach.
    for tid in sorted(int(x) for x in os.listdir(f"/proc/{engine.pid}/task")):
        if tid not in rt:
            # sudo: silnik ma uprawnienia plikowe (setcap), zwykly uzytkownik dostaje EPERM (suchy przebieg 2).
            subprocess.run(["sudo", "-n", "taskset", "-pc", COMM_CPU, str(tid)], stdout=subprocess.DEVNULL, check=True)

    clients = []
    rows = ["i\tpid\tstart_ns\tfirst_row_ns\trows0\tcount0_ns\trows1\tcount1_ns\talive"]
    if rt_ok:
        for i in range(args.n):
            clients.append(connect(i, args.stream, env))
            time.sleep(CONNECT_GAP_S)
        time.sleep(SETTLE_S)
        # rt.txt po podlaczeniach: VmLck obejmuje mapowania N kolejek (opisowo).
        rt_lines, fifo, vmlck, rt = rt_report(engine.pid)
        meta.update(rt_vmlck_kB_connected=vmlck)
        c0 = [count_rows(c[1]) for c in clients]
        trace_start([int(t) for t in os.listdir(f"/proc/{engine.pid}/task")], rt)
        # Granice okna = slad wlaczony (aneks A2): t0 po tracing_on=1, t1 przed tracing_on=0.
        t0 = time.monotonic_ns()
        cpu0 = cpu_lines()
        time.sleep(args.window)
        cpu1 = cpu_lines()
        t1 = time.monotonic_ns()
        meta["trace_overrun"] = trace_stop(args.out / "trace.txt")
        alive = [c[0].poll() is None for c in clients]
        c1 = [count_rows(c[1]) for c in clients]
        (args.out / "window.json").write_text(json.dumps({"t0_ns": t0, "t1_ns": t1}) + "\n")
        (args.out / "cpu.txt").write_text("\n".join(["# t0"] + cpu0 + ["# t1"] + cpu1) + "\n")
        for i, (c, a, b, al) in enumerate(zip(clients, c0, c1, alive)):
            rows.append("\t".join(str(v) for v in (i, c[0].pid, c[2], c[3] if c[3] is not None else "-", a[0], a[1], b[0],
                                                   b[1], int(al))))
    (args.out / "rt.txt").write_text("\n".join(rt_lines) + "\n")
    (args.out / "clients.tsv").write_text("\n".join(rows) + "\n")

    for p, _, _, _ in clients:
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
    rcs = []
    for p, path, _, _ in clients:
        try:
            rcs.append(p.wait(timeout=5))
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            rcs.append("killed")
        path.unlink(missing_ok=True)
    meta["client_rc"] = rcs
    time.sleep(2.0)
    engine.send_signal(signal.SIGTERM)
    try:
        meta["engine_rc"] = engine.wait(timeout=30)
    except subprocess.TimeoutExpired:
        engine.kill()
        meta["engine_rc"] = "killed"
    shutil.move(RUN / "slots.csv", args.out / "slots.csv")
    shutil.rmtree(RUN / "temp", ignore_errors=True)
    meta["leftovers_after"] = leftovers()
    meta["rt_ok"] = rt_ok
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    if not rt_ok:
        sys.exit("brak watku SCHED_FIFO albo VmLck=0 - przebieg niewazny")


if __name__ == "__main__":
    main()
