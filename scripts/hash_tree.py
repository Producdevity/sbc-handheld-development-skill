#!/usr/bin/env python3
"""Create or compare a deterministic SHA-256 manifest for an installed data tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


BUFFER_SIZE = 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, help="write the manifest instead of stdout")
    parser.add_argument("--compare", type=Path, help="compare against an existing manifest")
    return parser.parse_args()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(BUFFER_SIZE):
            result.update(chunk)
    return result.hexdigest()


def relative_name(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build_manifest(root: Path, ignored: set[Path]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    pending = [root]
    while pending:
        current = pending.pop()
        with os.scandir(current) as scanner:
            entries = sorted(scanner, key=lambda entry: os.fsencode(entry.name))
        child_directories: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            if path in ignored:
                continue
            metadata = entry.stat(follow_symlinks=False)
            record: dict[str, Any] = {"path": relative_name(path, root)}
            if stat.S_ISREG(metadata.st_mode):
                record.update(type="file", bytes=metadata.st_size, sha256=digest(path))
            elif stat.S_ISLNK(metadata.st_mode):
                record.update(type="symlink", target=os.readlink(path))
            elif stat.S_ISDIR(metadata.st_mode):
                record.update(type="directory")
                child_directories.append(path)
            else:
                record.update(type="special", mode=stat.S_IFMT(metadata.st_mode))
            records.append(record)
        pending.extend(reversed(child_directories))
    records.sort(key=lambda record: os.fsencode(record["path"]))
    return {"schema": 1, "files": records}


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read manifest: {error}") from error
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("unsupported manifest schema")
    files = value.get("files")
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise ValueError("manifest files must be an array of objects")
    return value


def indexed(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in manifest["files"]:
        name = record.get("path")
        if not isinstance(name, str) or not name or name in result:
            raise ValueError("manifest contains an invalid or duplicate path")
        result[name] = record
    return result


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> int:
    before = indexed(expected)
    after = indexed(actual)
    removed = sorted(before.keys() - after.keys(), key=os.fsencode)
    added = sorted(after.keys() - before.keys(), key=os.fsencode)
    changed = sorted(
        (name for name in before.keys() & after.keys() if before[name] != after[name]),
        key=os.fsencode,
    )
    for label, names in (("removed", removed), ("added", added), ("changed", changed)):
        for name in names:
            print(f"{label}\t{name}")
    if removed or added or changed:
        return 1
    print(f"match\t{len(after)} entries")
    return 0


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    ignored = {
        path.expanduser().resolve()
        for path in (args.output, args.compare)
        if path is not None
    }
    try:
        actual = build_manifest(root, ignored)
        if args.compare is not None:
            return compare(load_manifest(args.compare), actual)
        rendered = json.dumps(actual, ensure_ascii=True, indent=2) + "\n"
        if args.output is None:
            sys.stdout.write(rendered)
        else:
            args.output.write_text(rendered, encoding="utf-8")
        return 0
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
