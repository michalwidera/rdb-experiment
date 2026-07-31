#!/usr/bin/env python3
"""Badanie higieniczne, warstwa trzecia: KLIENT.

**W badaniu `abe075e` (sonda E4) ta warstwa jest KONTROLĄ, nie przedmiotem.**
Sonda nie dotyka klienta, więc obie strony porównania mają identyczny kod
`xqry` i wynik musi wyjść identyczny. Różnica oznaczałaby niedeterminizm
harnessu — a wtedy zielonych warstw 1 i 2 też nie wolno byłoby czytać.
Warstwa nie została tu zostawiona przez zaniedbanie; patrz README, tabela
trzech warstw.

Kontekst pierwotny (badanie `e1e5181`), dla którego tę warstwę napisano:
poprawka ruszała silnik w jednym miejscu (`_kbhit`), a `xqry` w sześciu
plikach, więc warstwa porównująca tylko silnik odpowiadałaby na pytanie,
którego nikt nie zadaje, i przeszłaby w ciszy.

Silnik jest w tej warstwie trzymany **stały** (binarka FIXED), żeby każda
różnica była przypisywalna klientowi. Równoważność samego silnika rozstrzygają
warstwy 1 i 2.

Porównywane są dwie klasy poleceń:

1. **Deterministyczne z definicji** — `-l`, `-d`, `-y`, `-t <strumień>`. Ich
   wyjście jest funkcją skompilowanego planu, nie momentu podłączenia. Wśród
   nich `-t` jest najważniejsze i ma tu własny powód: kalibracja K6c czyta
   z niego pole `delta`, więc zmiana formatu tego wyjścia zepsułaby kampanię,
   nie dając ani jednego komunikatu.
2. **Zależne od chwili podłączenia** — `-s <strumień> -m N`. Klient dostaje
   elementy od momentu, w którym się podłączył, więc identyczność bajtowa nie
   jest z góry dana. Rozstrzyga o tym kontrola determinizmu: HISTORICAL biegnie
   dwa razy i jeżeli sam ze sobą się nie zgadza, polecenie jest **wyłączane
   z kryterium** i raportowane, zamiast udawać wynik.

Kody wyjścia mają osobne traktowanie. Treścią poprawki jest właśnie to, że
tryby porażki przestały być nierozróżnialne — zmiana kodu porażki na inny kod
porażki jest więc skutkiem zamierzonym, nie odstępstwem. Odstępstwem jest
przejście **z zera na niezero**: polecenie, które działało, przestało działać.

Reguła zliczania: zero porównanych poleceń jest błędem, nie zgodnością.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

STAGE_ROOT = "/dev/shm"

# Potok musi byc deterministyczny (warstwa 2 to sprawdza) i miec strumienie
# nazwane przez uzytkownika, o ktore da sie zapytac. `optimizer_ablation`
# przechodzi przez obie reguly przepisywania, `rec205-qrs` to potok
# umotywowany zewnetrznie -- ten sam, ktory mierzy rodzina W8 w K6.
PIPELINES = [
    "test/IntegrationTest_serial/optimizer_ablation/query.rql",
    "examples/ecg/rec205/rec205-qrs.rql",
]

ENGINE_SLOTS = 100000
STARTUP_POLL_INTERVAL_S = 0.5
STARTUP_MAX_POLLS = 40
SELECT_ELEMENTS = 20
SELECT_STREAMS = 3
COMMAND_TIMEOUT_S = 120


def stage_pipeline(code_repo: Path, relative: str, stage: Path) -> Path:
    source = code_repo / relative
    work = stage / "case"
    shutil.copytree(source.parent, work, ignore=shutil.ignore_patterns("__pycache__", "temp"))
    (work / "temp").mkdir(exist_ok=True)
    return work


def start_engine(binary: Path, work: Path, query: str) -> subprocess.Popen:
    return subprocess.Popen(
        [str(binary), query, "-r", "-k", "-m", str(ENGINE_SLOTS)],
        cwd=work,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def stop_engine(engine: subprocess.Popen) -> None:
    engine.terminate()
    try:
        engine.wait(timeout=20)
    except subprocess.TimeoutExpired:
        engine.kill()
        engine.wait()


def run_client(binary: Path, work: Path, arguments: list[str]) -> tuple[int, str]:
    """Jedno wywołanie klienta. `stdin` odcięty — to była treść defektu."""
    done = subprocess.run(
        [str(binary), *arguments],
        cwd=work,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=COMMAND_TIMEOUT_S,
        check=False,
    )
    return done.returncode, done.stdout


def parse_dir(text: str) -> list[str]:
    """Nazwy strumieni z tabeli `xqry -d`.

    Tabela jest rozdzielana pionowymi kreskami, a nazwa jest wyrównana do prawej
    w pierwszej kolumnie: `|                    FA|1/10|-1|6|a.txt|4|`. Podział
    po białych znakach dawał dla takiego wiersza token `|`, a dla wiersza
    z nazwą pełnej szerokości — cały wiersz. Pierwszy przebieg warstwy 3
    porównał przez to 66 razy polecenie `-t |`, czyli 66 razy to samo nic,
    i zaraportował to jako 66 zgodności. Dokładnie ten tryb porażki, przed
    którym ma bronić reguła zliczania (K5h/K5i).
    """
    names: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        fields = line.split("|")
        if len(fields) < 3:
            continue
        name = fields[1].strip()
        if name:
            names.append(name)
    return names


def wait_for_server(binary: Path, work: Path, engine: subprocess.Popen) -> list[str]:
    """Czeka na serwer i zwraca listę strumieni, o które można pytać."""
    for _ in range(STARTUP_MAX_POLLS):
        time.sleep(STARTUP_POLL_INTERVAL_S)
        if engine.poll() is not None:
            raise SystemExit("silnik zakonczyl sie przed podlaczeniem klienta")
        code, out = run_client(binary, work, ["-d"])
        if code == 0 and out.strip():
            streams = parse_dir(out)
            if streams:
                return streams
    raise SystemExit("serwer nie odpowiedzial na `-d` w wyznaczonym czasie")


def commands_for(streams: list[str]) -> list[tuple[str, list[str], bool]]:
    """(etykieta, argumenty, czy wyjście wymaga normalizacji kolejności)."""
    # Kolejnosc wierszy w `-d` i `-y` nie jest czescia kontraktu: pochodzi
    # z przejscia po nieuporzadkowanym kontenerze i rozni sie miedzy przebiegami
    # TEGO SAMEGO klienta. Porownujemy wiec zbior wierszy, nie ich kolejnosc --
    # inaczej oba polecenia wypadaja z kryterium i warstwa milczy o tym, o co
    # naprawde pytamy.
    plan: list[tuple[str, list[str], bool]] = [
        ("hello", ["-l"], False),
        ("dir", ["-d"], True),
        ("diryaml", ["-y"], True),
    ]
    for stream in streams:
        # `-t` zasila kalibracje K6c (pole `delta`) -- najwazniejsza pozycja tej warstwy.
        plan.append((f"detail:{stream}", ["-t", stream], False))
    # `-s` jest kosztowne i zalezne od chwili podlaczenia, wiec bierzemy staly,
    # deterministyczny podzbior strumieni NAZWANYCH PRZEZ UZYTKOWNIKA (te
    # z przedrostkiem STREAM_ tworzy kompilator).
    for stream in sorted(s for s in streams if not s.startswith("STREAM_"))[:SELECT_STREAMS]:
        plan.append((f"select:{stream}", ["-s", stream, "-m", str(SELECT_ELEMENTS)], False))
    # Strumien nieistniejacy: sciezka porazki, ktorej kod wyjscia i komunikat
    # poprawka CELOWO zmienila. Porownujemy ja, zeby zmiana byla zapisana.
    plan.append(("detail:brak", ["-t", "nie_ma_takiego_strumienia"], False))
    plan.append(("select:brak", ["-s", "nie_ma_takiego_strumienia", "-m", "1"], False))
    return plan


def collect(binary: Path, work: Path, engine_binary: Path, query: str, plan: list) -> dict[str, tuple[int, str]]:
    """Jeden komplet wywołań klienta przeciwko świeżo wystartowanemu silnikowi."""
    engine = start_engine(engine_binary, work, query)
    try:
        wait_for_server(binary, work, engine)
        return {label: run_client(binary, work, arguments) for label, arguments, _ in plan}
    finally:
        stop_engine(engine)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--historical-client", type=Path, required=True)
    parser.add_argument("--fixed-client", type=Path, required=True)
    parser.add_argument("--engine-binary", type=Path, required=True, help="silnik trzymany stale (FIXED)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    raw = output / "raw/client"
    raw.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    compared = 0
    failures = 0

    for relative in PIPELINES:
        source = code_repo / relative
        if not source.is_file():
            results.append({"potok": relative, "identyczne": False, "uwagi": ["brak pliku"]})
            failures += 1
            continue
        label = source.parent.name
        with tempfile.TemporaryDirectory(prefix="rdb-hyg3-", dir=STAGE_ROOT) as stage:
            work = stage_pipeline(code_repo, relative, Path(stage))
            probe = start_engine(args.engine_binary, work, source.name)
            try:
                streams = wait_for_server(args.fixed_client, work, probe)
            finally:
                stop_engine(probe)
            plan = commands_for(streams)

            historical = collect(args.historical_client, work, args.engine_binary, source.name, plan)
            historical_again = collect(args.historical_client, work, args.engine_binary, source.name, plan)
            fixed = collect(args.fixed_client, work, args.engine_binary, source.name, plan)

        for tree, capture in (("HISTORICAL", historical), ("HISTORICAL_2", historical_again), ("FIXED", fixed)):
            target = raw / label / tree
            target.mkdir(parents=True, exist_ok=True)
            for command, (code, out) in capture.items():
                safe = command.replace(":", "__").replace("/", "__")
                (target / f"{safe}.stdout").write_text(out, encoding="utf-8")
                (target / f"{safe}.rc").write_text(f"{code}\n", encoding="utf-8")

        for command, arguments, order_insensitive in plan:
            historical_code, historical_out = historical[command]
            repeat_code, repeat_out = historical_again[command]
            fixed_code, fixed_out = fixed[command]
            record: dict[str, object] = {
                "potok": relative,
                "polecenie": command,
                "argumenty": " ".join(arguments),
                "HISTORICAL_rc": historical_code,
                "FIXED_rc": fixed_code,
                "kolejnosc_nieistotna": order_insensitive,
            }

            def normalise(text: str) -> str:
                return "\n".join(sorted(text.splitlines())) if order_insensitive else text

            historical_out, repeat_out, fixed_out = (
                normalise(historical_out),
                normalise(repeat_out),
                normalise(fixed_out),
            )

            stable = (historical_out == repeat_out) and (historical_code == repeat_code)
            record["deterministyczne"] = stable
            if not stable:
                # Nie udajemy wyniku tam, gdzie instrument nie odróżnia zmiany
                # kodu od chwili podłączenia.
                record["identyczne"] = None
                record["uwagi"] = [
                    "dwa przebiegi tym samym klientem daja rozne wyjscie -- polecenie wylaczone "
                    "z kryterium, bo nie odroznia zmiany kodu od chwili podlaczenia"
                ]
                results.append(record)
                print(f"{relative} {command}: NIEDETERMINISTYCZNE — wyłączone z kryterium")
                continue

            notes: list[str] = []
            identical = True
            if historical_code == 0:
                # Sciezka, ktora DZIALALA. Tu obowiazuje porownanie scisle:
                # zarowno wyjscie, jak i kod musza zostac bez zmian.
                if historical_out != fixed_out:
                    identical = False
                    notes.append(f"rozne wyjscie ({len(historical_out)} vs {len(fixed_out)} znakow)")
                if fixed_code != 0:
                    identical = False
                    notes.append(f"REGRESJA kodu wyjscia: 0 -> {fixed_code}")
            else:
                # Sciezka, ktora JUZ ZAWODZILA. Poprawka #216 uczynila tryby
                # porazki rozroznialnymi -- zarowno po kodzie wyjscia, jak i po
                # komunikacie. Zmiana jednego albo drugiego jest tu TRESCIA
                # poprawki, a nie odstepstwem; odstepstwem byloby przejscie
                # z zera na niezero, ktore obsluguje galaz wyzej. Predeklaracja
                # deklaruje ten podzial slowami „polecenie, ktore dzialalo,
                # przestalo dzialac"; pierwsza wersja tego kodu zawezala go do
                # samego kodu wyjscia i przez to zglaszala zamierzony komunikat
                # diagnostyczny jako wplyw.
                changes: list[str] = []
                if historical_code != fixed_code:
                    changes.append(f"kod {historical_code} -> {fixed_code}")
                if historical_out != fixed_out:
                    changes.append("komunikat diagnostyczny")
                if changes:
                    record["zmiana_na_sciezce_porazki"] = ", ".join(changes)
                    notes.append(f"sciezka juz zawodzila; {', '.join(changes)} (tresc poprawki, nie odstepstwo)")
            record["identyczne"] = identical
            record["uwagi"] = notes
            compared += 1
            if not identical:
                failures += 1
            results.append(record)
            print(f"{relative} {command}: identyczne={identical} {'; '.join(notes)}")

    # Reguła zliczania: instrument, który nic nie porównał, milczy — a milczenie
    # wygląda jak sukces.
    if compared == 0:
        print("BLAD: warstwa klienta nie porownala ani jednego polecenia", flush=True)
        failures += 1

    (output / "client.json").write_text(
        json.dumps({"porownane": compared, "wyniki": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
