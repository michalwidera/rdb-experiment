#!/usr/bin/env python3
"""Most do silnika: kompilacja planu i odczyt postaci zamkniętej ze zrzutu.

Most nie liczy niczego — wyłącznie uruchamia `xretractor <plan> -c` i parsuje
zrzut planu. Ogon zerowy nie jest drukowany, więc brak `tail=` czytamy jako 0.
"""

import os
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

HEADER = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z_0-9]*)\((?P<interval>\d+/\d+)\)(?P<rest>.*)$")
TAIL = re.compile(r"tail=(\d+)")

DEFAULT_BINARY = Path(__file__).resolve().parents[3] / "retractordb/build/Debug/src/retractor/xretractor"


class EngineError(RuntimeError):
    """Awaria aparatury silnika — zatrzymuje iterację."""


def resolve_binary(explicit=None):
    if explicit:
        return Path(explicit).resolve()
    if DEFAULT_BINARY.exists():
        return DEFAULT_BINARY
    found = shutil.which("xretractor")
    if not found:
        raise EngineError("nie znaleziono xretractor — podaj --xretractor")
    return Path(found).resolve()


def build_info(binary):
    done = subprocess.run([str(binary), "--build-info"], capture_output=True, text=True, timeout=30)
    return done.stdout.strip()


def parse_plan(dump):
    """Zwraca {nazwa: (interwał, ogon)} dla każdego strumienia w zrzucie."""
    result = {}
    for line in dump.splitlines():
        match = HEADER.match(line)
        if not match:
            continue
        tail = TAIL.search(match.group("rest"))
        result[match.group("name")] = (Fraction(match.group("interval")),
                                       int(tail.group(1)) if tail else 0)
    return result


def compile_plan(rql_text, binary, workdir, timeout=30):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    query = workdir / "query.rql"
    query.write_text(rql_text, encoding="utf-8")
    env = dict(os.environ, SPDLOG_LEVEL="warn")
    done = subprocess.run([str(binary), "query.rql", "-c"], cwd=workdir, capture_output=True,
                          text=True, timeout=timeout, env=env)
    if done.returncode != 0:
        raise EngineError(f"kompilacja nieudana ({done.returncode}):\n{done.stdout}\n{done.stderr}")
    if "unresolved startup latency" in done.stdout or "unresolved startup latency" in done.stderr:
        raise EngineError("postać zamknięta nie rozwiązała ogona — nierozwiązany węzeł planu")
    return done.stdout, done.stderr
