#!/usr/bin/env python3
"""Maszynowy odczyt ANEKS-2/ANEKS-3 workera K26v2 przed P6.

Skrypt wykonuje jeden fail-closed odczyt przez SSH. Nie ustawia governora i nie
buduje binariow; zapisuje wyłącznie zastany, sprawdzony stan.
"""

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
ENV_KEYS = [
    "engine_sha", "kernel", "cpu_online", "cpu_pinning",
    "cpu_isolated", "governor", "arch", "model", "os", "gcc", "screen",
    "temp_c_at_freeze", "mem_total_mb",
]


class CaptureError(RuntimeError):
    pass


def parse_key_values(text, expected):
    out = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or not fields[0] or fields[0] in out:
            raise CaptureError(f"nieprawidlowy lub zdublowany wiersz workera: {line!r}")
        out[fields[0]] = fields[1]
    missing = [key for key in expected if not out.get(key)]
    extra = sorted(set(out) - set(expected))
    if missing or extra:
        raise CaptureError(f"inwentarz odczytu workera: missing={missing}, extra={extra}")
    return out


def write_tsv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    temporary.replace(path)


def remote_script(code_repo, cpu):
    switches = {
        "DEFAULT": ("ON", "ON"),
        "NO_R2_CANON": ("OFF", "ON"),
        "NO_R1_FACTOR": ("ON", "OFF"),
        "NO_R1_NO_R2": ("OFF", "OFF"),
    }
    binary_parts = []
    for profile in PROFILES:
        commutative, factor = switches[profile]
        binary = f"{code_repo}/build/K26v2-{profile}/src/retractor/xretractor"
        binary_parts.append(f"""
binary='{binary}'
test -x "$binary"
info="$("$binary" --build-info)"
grep -qx 'RDB_OPT_DEDUP_SUBSTRATES=ON' <<<"$info"
grep -qx 'RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON' <<<"$info"
grep -qx 'RDB_BENCH_PROBE=ON' <<<"$info"
grep -qx 'RDB_OPT_SIMPLIFY_EXPRESSIONS=ON' <<<"$info"
grep -qx 'RDB_OPT_COMMUTATIVE_ADD={commutative}' <<<"$info"
grep -qx 'RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES={factor}' <<<"$info"
test "$(wc -l <<<"$info")" -eq 6
printf '{profile}\\t'; sha256sum "$binary" | awk '{{print $1}}'
""")
    binaries = "\n".join(binary_parts)
    environment = f"""
set -euo pipefail
test -z "$(git -C '{code_repo}' status --short)"
printf 'engine_sha\\t%s\\n' "$(git -C '{code_repo}' rev-parse HEAD)"
printf 'kernel\\t%s\\n' "$(uname -r)"
printf 'cpu_online\\t%s\\n' "$(cat /sys/devices/system/cpu/online)"
printf 'cpu_pinning\\t%s\\n' "$(tr ' ' '\\n' </proc/cmdline | grep -E '^(isolcpus|nohz_full|rcu_nocbs)=' | paste -sd' ' -)"
printf 'cpu_isolated\\t%s\\n' "$(cat /sys/devices/system/cpu/isolated)"
printf 'governor\\t%s\\n' "$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | paste -sd, -)"
printf 'arch\\t%s\\n' "$(uname -m)"
printf 'model\\t%s\\n' "$(tr -d '\\000' </proc/device-tree/model 2>/dev/null || hostnamectl --static)"
printf 'os\\t%s\\n' "$(. /etc/os-release; printf '%s' "$PRETTY_NAME")"
printf 'gcc\\t%s\\n' "$(gcc --version | head -n1)"
printf 'screen\\t%s\\n' "$(screen --version | head -n1)"
printf 'temp_c_at_freeze\\t%s\\n' "$(awk '{{printf "%.3f", $1/1000}}' /sys/class/thermal/thermal_zone0/temp)"
printf 'mem_total_mb\\t%s\\n' "$(awk '/MemTotal:/ {{printf "%d", $2/1024}}' /proc/meminfo)"
test "$(cat /sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor)" = performance
"""
    return binaries, environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", default="michal@192.168.88.13")
    parser.add_argument("--ssh-config", default=os.environ.get("RDB_SSH_CONFIG", "/dev/null"))
    parser.add_argument("--code-repo", default="/home/michal/K26v2")
    parser.add_argument("--cpu", type=int, default=3)
    parser.add_argument("--out-bin", type=Path, default=HERE / "ANEKS-2_worker_binaria.tsv")
    parser.add_argument("--out-env", type=Path, default=HERE / "ANEKS-3_worker_srodowisko.tsv")
    args = parser.parse_args()
    if args.out_bin.exists() or args.out_env.exists():
        print("BLAD: odmowa nadpisania istniejacego ANEKS-2/ANEKS-3", file=sys.stderr)
        return 2
    try:
        binary_script, environment_script = remote_script(args.code_repo, args.cpu)
        script = ("set -euo pipefail\nprintf '__K26_BIN__\\n'\n" + binary_script +
                  "\nprintf '__K26_ENV__\\n'\n" + environment_script)
        output = subprocess.run(
            ["ssh", "-F", args.ssh_config, "-o", "BatchMode=yes", args.worker, "bash", "-s"], input=script,
            check=True, text=True, capture_output=True,
        ).stdout
        prefix, marker, environment_text = output.partition("__K26_ENV__\n")
        if not marker or not prefix.startswith("__K26_BIN__\n"):
            raise CaptureError("brak znacznikow sekcji w odczycie workera")
        binary_text = prefix.removeprefix("__K26_BIN__\n")
        binaries = parse_key_values(binary_text, PROFILES)
        environment = parse_key_values(environment_text, ENV_KEYS)
        if environment["governor"] != "performance":
            raise CaptureError(f"governor={environment['governor']}, wymagane performance")
        if str(args.cpu) not in environment["cpu_isolated"].split(","):
            raise CaptureError(f"cpu{args.cpu} nie jest izolowany")
        write_tsv(args.out_bin, ["profile", "sha256"], [(key, binaries[key]) for key in PROFILES])
        write_tsv(args.out_env, ["key", "value"], [(key, environment[key]) for key in ENV_KEYS])
    except (CaptureError, OSError, subprocess.CalledProcessError) as exc:
        args.out_bin.unlink(missing_ok=True)
        args.out_env.unlink(missing_ok=True)
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2
    print(f"OK: zapisano {args.out_bin} i {args.out_env}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
