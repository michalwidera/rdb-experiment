#!/usr/bin/env python3
"""Higiena artefaktów badań — `REQUIREMENTS.md` R14.

Surowe drzewa artefaktów silnika (`.desc`, `.meta`, `.shadow`, zrzuty `stdout`
każdej kompilacji) liczą tysiące plików na kampanię. Taki katalog jest
nieprzetwarzalny dla IDE i bezużyteczny w przeglądzie ręcznym, a merytorycznie
wnosi tyle, co jego indeks: kampania czyta z niego wyłącznie kilka bajtów, które
i tak trafiają do `summary.md`.

Kontrakt modułu:

1. surowe artefakty powstają w `/dev/shm` i tam są porównywane;
2. do repozytorium trafiają jako **pliki** wyłącznie dowody porażki —
   imiennie wskazane w werdykcie;
3. resztę zachowuje jedno archiwum `tar.gz` plus indeks `SHA-256`, tworzone
   na koniec badania, także po porażce.

Archiwum jest deterministyczne (kolejność nazw, `mtime=0`, właściciel `0:0`),
więc jego `SHA-256` można przypiąć w manifeście. Zapisywane są tylko pliki
regularne — katalogi puste i dowiązania nie przechodzą przez pakowanie.
"""
import argparse
import csv
import gzip
import hashlib
import shutil
import stat
import tarfile
from collections.abc import Iterable
from pathlib import Path

INDEX_HEADER = ("path", "bytes", "sha256")
INDEX_SUFFIX = ".index.tsv"
ARCHIVE_SUFFIX = ".tar.gz"
CHUNK = 1 << 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_index(root: Path) -> list[tuple[str, int, str]]:
    """Indeks drzewa: ścieżka względna, rozmiar, `SHA-256`. Posortowany po ścieżce."""
    root = Path(root)
    rows = [
        (str(path.relative_to(root)), path.stat().st_size, sha256_file(path))
        for path in root.rglob("*")
        if path.is_file()
    ]
    return sorted(rows)


def write_index(rows: Iterable[tuple[str, int, str]], destination: Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, delimiter="\t", lineterminator="\n")
        writer.writerow(INDEX_HEADER)
        writer.writerows(rows)
    return destination


def pack(directory: Path, archive: Path | None = None, remove: bool = True) -> tuple[Path, Path] | None:
    """Pakuje katalog do deterministycznego `tar.gz` obok niego i zapisuje indeks.

    Zwraca `(archiwum, indeks)` albo `None`, gdy katalogu nie ma — wywołanie
    z pułapki `EXIT` nie może się wywrócić na nieukończonym badaniu.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return None
    archive = Path(archive) if archive else directory.with_name(directory.name + ARCHIVE_SUFFIX)
    index = archive.with_name(archive.name[: -len(ARCHIVE_SUFFIX)] + INDEX_SUFFIX)

    rows = tree_index(directory)
    write_index(rows, index)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(archive, "wb", compresslevel=9, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as tar:
            for relative, size, _ in rows:
                source = directory / relative
                info = tarfile.TarInfo(f"{directory.name}/{relative}")
                info.size = size
                info.mtime = 0
                info.mode = stat.S_IMODE(source.stat().st_mode)
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                with source.open("rb") as handle:
                    tar.addfile(info, handle)
    if remove:
        shutil.rmtree(directory)
    return archive, index


def keep_evidence(files: Iterable[Path], source_root: Path, destination: Path) -> list[str]:
    """Kopiuje do repozytorium imiennie wskazane dowody porażki.

    Układ względny jest zachowany, żeby nazwa pliku dowodowego zgadzała się
    z nazwą z werdyktu. Zwraca listę skopiowanych ścieżek względnych.
    """
    source_root = Path(source_root)
    destination = Path(destination)
    kept: list[str] = []
    for path in sorted(Path(f) for f in files):
        relative = path.relative_to(source_root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
        kept.append(str(relative))
    return kept


def keep_output(base: Path, stdout: str, stderr: str, evidence: bool) -> dict[str, object]:
    """Zrzuty procesu: pliki tylko dla porażki, dla sukcesu wyłącznie skróty.

    Przy kilkuset kompilacjach na kampanię para `stdout`/`stderr` udanego
    przebiegu to czysty przyrost liczby plików — wynik jest już sparsowany
    do `counts.json`, a skrót pozwala wykazać, że zrzut nie zmienił się
    między przebiegami.
    """
    base = Path(base)
    record: dict[str, object] = {}
    for name, text in (("stdout", stdout), ("stderr", stderr)):
        payload = text.encode("utf-8")
        record[f"{name}_bytes"] = len(payload)
        record[f"{name}_sha256"] = hashlib.sha256(payload).hexdigest()
    if evidence:
        base.parent.mkdir(parents=True, exist_ok=True)
        Path(f"{base}.stdout").write_text(stdout, encoding="utf-8")
        Path(f"{base}.stderr").write_text(stderr, encoding="utf-8")
        record["zrzuty"] = f"{base.name}.stdout, {base.name}.stderr"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Higiena artefaktów badań (R14).")
    commands = parser.add_subparsers(dest="command", required=True)

    pack_parser = commands.add_parser("pack", help="spakuj katalog do tar.gz i zapisz indeks")
    pack_parser.add_argument("directory", type=Path, nargs="+")
    pack_parser.add_argument("--keep", action="store_true", help="nie usuwaj katalogu źródłowego")

    index_parser = commands.add_parser("index", help="zapisz indeks SHA-256 katalogu")
    index_parser.add_argument("directory", type=Path)
    index_parser.add_argument("destination", type=Path)

    args = parser.parse_args()
    if args.command == "pack":
        for directory in args.directory:
            result = pack(directory, remove=not args.keep)
            if result is None:
                print(f"pominięto (brak katalogu): {directory}")
                continue
            archive, index = result
            print(f"{archive} {sha256_file(archive)} ({sum(1 for _ in open(index, encoding='utf-8')) - 1} plików)")
        return 0

    rows = tree_index(args.directory)
    write_index(rows, args.destination)
    print(f"{args.destination} ({len(rows)} plików)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
