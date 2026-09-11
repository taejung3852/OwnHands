from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from .model import fingerprint


def _git(repository: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"unable to inspect Git code state: {detail}") from error


def _paths(raw: bytes) -> list[str]:
    return sorted(item.decode("utf-8", errors="surrogateescape") for item in raw.split(b"\0") if item)


def capture_code_state(repository: Path | str) -> dict:
    repository = Path(repository).resolve()
    commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    tracked = set(_paths(_git(repository, "ls-files", "-z", "--cached")))
    untracked = set(_paths(_git(repository, "ls-files", "-z", "--others", "--exclude-standard")))
    ignored = _paths(_git(repository, "ls-files", "-z", "--others", "--ignored", "--exclude-standard"))
    files: list[dict] = []
    exclusions: list[dict] = [
        {"area": relative, "reason": "ignored content not captured"}
        for relative in ignored
    ]

    for relative in sorted(tracked | untracked):
        path = repository / relative
        origin = "tracked" if relative in tracked else "untracked"
        if not os.path.lexists(path):
            files.append({"path": relative, "origin": origin, "kind": "missing", "mode": None, "hash": None})
            continue
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(path)
            files.append({"path": relative, "origin": origin, "kind": "symlink", "mode": mode, "hash": fingerprint(target)})
        elif stat.S_ISREG(metadata.st_mode):
            files.append({"path": relative, "origin": origin, "kind": "file", "mode": mode, "hash": fingerprint(path.read_bytes())})
        elif stat.S_ISDIR(metadata.st_mode):
            exclusions.append({"area": relative, "reason": "nested working tree or submodule content not inspected"})
            files.append({"path": relative, "origin": origin, "kind": "directory", "mode": mode, "hash": None})
        else:
            exclusions.append({"area": relative, "reason": "unsupported filesystem object"})

    document = {
        "code_state_version": 1,
        "commit": commit,
        "files": files,
        "coverage": "partial" if exclusions else "complete",
        "exclusions": exclusions,
    }
    document["fingerprint"] = fingerprint(document)
    return document
