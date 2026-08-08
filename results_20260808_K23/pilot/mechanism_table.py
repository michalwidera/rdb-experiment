#!/usr/bin/env python3
"""Tabela liczb mechanizmu z listingów kompilacji pilota K23 (P4).

Czyta out/<profil>_<plan>.plan i out/<profil>_<plan>.probe, wypisuje dla każdej
komórki: r1, r2, liczbę STREAM_SELECT_*, liczbę substratów, ich konsumentów oraz
PRZEWIDYWANE jednostki bajtowe = suma po substratach (rate * szerokosc_kanoniczna),
znormalizowana do jednostki n_h*w (rate 150 Hz, jeden INTEGER).

Jednostki bajtowe są arytmetyką predeklaracyjną, nie pomiarem: pilot jest
compile-only, więc liczba rzeczywistych zapisów pochodzi dopiero z licznika
w P6. Zakłada jeden zapis na slot.
"""
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out"
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
PLANS = ["F9_R2_Q8", "F9_R1_Q8", "F9_X_Q8", "F9_R2_controls", "F9_R1_controls", "F9_X_controls"]

HEAD = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\((?P<num>\d+)/(?P<den>\d+)\)")
FIELD = re.compile(r"^\t[A-Za-z_][A-Za-z0-9_]*: (?P<type>[A-Z]+)")
PUSH = re.compile(r"^\t:- PUSH_STREAM\((?P<src>[^)]+)\)")


def canonical_bytes(fields):
    """probe::canonicalRecordBytes: INTEGER = 8 B, plus mapa NULL/luk ceil(n/8)."""
    return 8 * fields + (fields + 7) // 8


def parse(path):
    """Zwraca {nazwa: {'interval': Fraction, 'fields': int, 'sources': [str]}}."""
    streams, current = {}, None
    for line in path.read_text().splitlines():
        head = HEAD.match(line)
        if head:
            current = head.group("name")
            streams[current] = {
                "interval": Fraction(int(head.group("num")), int(head.group("den"))),
                "fields": 0,
                "sources": [],
            }
            continue
        if current is None:
            continue
        if FIELD.match(line):
            streams[current]["fields"] += 1
        push = PUSH.match(line)
        if push:
            streams[current]["sources"].append(push.group("src"))
    return streams


def main():
    unit = 150 * canonical_bytes(1)  # n_h * w przy 150 Hz i jednym polu INTEGER
    for plan in PLANS:
        print(f"\n=== {plan} ===")
        print(f"{'profil':<13} {'r1':>3} {'r2':>3} {'SELECT_':>8} {'substraty':>10} {'jednostki':>10}")
        for profile in PROFILES:
            plan_file = OUT / f"{profile}_{plan}.plan"
            probe_file = OUT / f"{profile}_{plan}.probe"
            if not plan_file.exists():
                sys.exit(f"brak {plan_file}")
            streams = parse(plan_file)
            rewrite = re.search(r"REWRITE_APPLIED r1=(\d+) r2=(\d+)", probe_file.read_text())
            r1, r2 = rewrite.groups()

            # Substrat = strumień wygenerowany przez kompilator: nie jest ani deklaracją
            # (te mają plik źródłowy i brak PUSH_STREAM), ani zapytaniem użytkownika.
            declared = {n for n, s in streams.items() if not s["sources"]}
            user = {n for n in streams if re.fullmatch(r"(m|q|n|d|x|i|h|mm|collide_user)\d*", n)}
            substrates = [n for n in streams if n not in declared and n not in user]

            selects = [n for n in substrates if n.startswith("STREAM_SELECT_")]
            consumers = {}
            for name in substrates:
                consumers[name] = sum(1 for s in streams.values() if name in s["sources"])
            units = sum(
                (1 / s["interval"]) * canonical_bytes(s["fields"])
                for n, s in streams.items()
                if n in substrates
            ) / unit
            print(f"{profile:<13} {r1:>3} {r2:>3} {len(selects):>8} {len(substrates):>10} {float(units):>10.3f}")
            for name in sorted(substrates):
                s = streams[name]
                print(
                    f"    {name:<52} {str(s['interval']):>7}  pol={s['fields']}"
                    f"  konsumentow={consumers[name]}"
                )


if __name__ == "__main__":
    main()
