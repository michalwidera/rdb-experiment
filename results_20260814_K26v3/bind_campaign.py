#!/usr/bin/env python3
"""Wiaze rewizje K26v3 dopiero w chwili rozpoczecia kampanii.

Uruchomic bezposrednio przed pierwszym P6. Plik startowy trafia do ignorowanego
``results/`` i od tej chwili jest niezmienny. Ponowne wywolanie nigdy go nie
nadpisuje.
"""

import argparse
import hashlib
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-repo", type=Path, default=Path("/home/michal/github/retractordb"))
    parser.add_argument("--experiment-repo", type=Path, default=HERE.parent)
    parser.add_argument("--out", type=Path, default=HERE / "results" / "ANEKS-0_start.tsv")
    parser.add_argument("--worker", default="michal@192.168.88.13")
    parser.add_argument("--ssh-config", default=os.environ.get("RDB_SSH_CONFIG", "/dev/null"))
    parser.add_argument("--worker-k26-dir", default="/home/michal/rdb-experiment/results_20260814_K26v3")
    args = parser.parse_args()
    if args.out.exists():
        print(f"BLAD: kampania jest juz zwiazana przez {args.out}; odmowa nadpisania", file=sys.stderr)
        return 2
    try:
        freeze_env = os.environ.copy()
        freeze_env["CODE_REPO"] = str(args.code_repo)
        subprocess.run([HERE / "freeze_check.sh", "predeklaracja"], check=True, env=freeze_env)
        engine_sha = git(args.code_repo, "rev-parse", "HEAD")
        experiment_sha = git(args.experiment_repo, "rev-parse", "HEAD")
        rows = [("engine_sha", engine_sha), ("experiment_sha", experiment_sha)]
        for profile in PROFILES:
            binary = args.code_repo / "build" / f"K26v3-{profile}" / "src" / "retractor" / "xretractor"
            rows.append((f"host_binary_sha256_{profile}", sha256(binary)))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_suffix(".tmp")
        content = "key\tvalue\n" + "".join(f"{key}\t{value}\n" for key, value in rows)
        temporary.write_text(content)
        temporary.replace(args.out)
        remote = f"{args.worker_k26_dir}/results/ANEKS-0_start.tsv"
        remote_tmp = remote + ".tmp"
        command = (f"mkdir -p {shlex.quote(str(Path(remote).parent))} && "
                   f"test ! -e {shlex.quote(remote)} && cat >{shlex.quote(remote_tmp)} && "
                   f"mv {shlex.quote(remote_tmp)} {shlex.quote(remote)}")
        remote_created = False
        subprocess.run(["ssh", "-F", args.ssh_config, "-o", "BatchMode=yes", args.worker, command],
                       input=content, text=True, check=True)
        remote_created = True
        subprocess.run([HERE / "freeze_check.sh", "bound"], check=True, env=freeze_env)
    except (OSError, subprocess.CalledProcessError) as exc:
        args.out.unlink(missing_ok=True)
        if locals().get("remote_created", False):
            subprocess.run(["ssh", "-F", args.ssh_config, "-o", "BatchMode=yes", args.worker,
                            f"rm -f {shlex.quote(remote_tmp)} {shlex.quote(remote)}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"BLAD: nie zwiazano kampanii: {exc}", file=sys.stderr)
        return 2
    print(f"START K26v3: przypieto engine={engine_sha}, experiment={experiment_sha}")
    print("Nastepna operacja: pierwsze P6. Od tej chwili zmiana rewizji wymaga nowej iteracji.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
