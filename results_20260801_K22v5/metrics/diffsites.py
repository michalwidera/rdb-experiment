#!/usr/bin/env python3
"""D1/D2 K22v5: zmienione linie logiczne i rozłączne miejsca edycji."""

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path

from measure import MeasureError, core_ranges, in_core


COMMENT = {".py": "#", ".rql": "#", ".java": "//"}


def strip_comment(text, marker):
    quote = None
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif text.startswith(marker, index):
            return text[:index]
        index += 1
    return text


def normalized_lines(path):
    path = Path(path)
    marker = COMMENT.get(path.suffix)
    if not marker:
        raise MeasureError(f"{path}: nieobslugiwane rozszerzenie")
    raw = path.read_text(encoding="utf-8").splitlines()
    ranges = core_ranges([line + "\n" for line in raw], str(path))
    result = []
    for lineno, text in enumerate(raw, 1):
        if not in_core(lineno, ranges):
            continue
        normalized = " ".join(strip_comment(text, marker).split())
        if normalized:
            result.append((lineno, normalized))
    if not result:
        raise MeasureError(f"{path}: pusty rdzen po normalizacji")
    return result


def compare(base, variant):
    left = normalized_lines(base)
    right = normalized_lines(variant)
    matcher = difflib.SequenceMatcher(None, [x[1] for x in left], [x[1] for x in right], autojunk=False)
    sites, d1 = [], 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        d1 += max(i2 - i1, j2 - j1)
        sites.append({
            "tag": tag,
            "base_from": left[i1][0] if i1 < len(left) else "EOF",
            "base_to": left[i2 - 1][0] if i2 > i1 else "-",
            "variant_from": right[j1][0] if j1 < len(right) else "EOF",
            "variant_to": right[j2 - 1][0] if j2 > j1 else "-",
            "base": [line for _number, line in left[i1:i2]],
            "variant": [line for _number, line in right[j1:j2]],
        })
    diff = list(difflib.unified_diff([x[1] + "\n" for x in left], [x[1] + "\n" for x in right],
                                     fromfile=str(base), tofile=str(variant), n=0))
    return {"D1": d1, "D2": len(sites), "sites": sites, "diff": diff}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--diff-out")
    args = parser.parse_args(argv)
    result = compare(args.base, args.variant)
    if not result["sites"]:
        raise MeasureError("wariant nie rozni sie od bazy")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.diff_out:
        Path(args.diff_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.diff_out).write_text("".join(result["diff"]), encoding="utf-8")
    print(json.dumps({"D1": result["D1"], "D2": result["D2"], "sites": result["sites"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MeasureError as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        raise SystemExit(2)
