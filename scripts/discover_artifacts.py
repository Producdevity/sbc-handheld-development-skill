#!/usr/bin/env python3
"""List possible handheld-development helpers without executing them."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time


READ_LIMIT = 64 * 1024
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
TEXT_SUFFIXES = {
    "", ".c", ".cc", ".cpp", ".events", ".evemu", ".gdb", ".gdbinit",
    ".gptk", ".h", ".java", ".json", ".lua", ".md", ".pl", ".py",
    ".r2", ".rb", ".rs", ".rz", ".sh", ".tcl", ".txt", ".yaml",
    ".yml", ".zig",
}
SPECIALIZED_SUFFIXES = {".events", ".evemu", ".gdb", ".gdbinit", ".gptk", ".r2", ".rz"}
TOOL_DIRS = {".agents", ".tmp", "scripts", "tools"}
SCRIPT_SUFFIXES = {
    "", ".c", ".cc", ".cpp", ".java", ".lua", ".pl", ".py", ".rb",
    ".rs", ".sh", ".tcl", ".zig",
}
TEMP_SCRIPT_SUFFIXES = SCRIPT_SUFFIXES - {".java"}
SKIP_DIRS = {
    ".cache", ".cxx", ".git", ".gradle", ".idea", ".pytest_cache", ".tools",
    ".venv", ".zig-cache", "CMakeFiles", "__pycache__", "boost-unused-headers", "build",
    "cache", "deps", "dist", "ipa_extracted", "node_modules", "original-jadx",
    "site-packages", "target", "third_party", "vendor", "venv", "zig-cache",
    "zig-out",
}

def terms(*values: str) -> re.Pattern[str]:
    return re.compile("|".join(values), re.IGNORECASE)


CATEGORY_PATTERNS = {
    "audio": terms(
        r"\bSDL[_ -]?mixer\b", r"\bMix_(?:OpenAudio|LoadMUS|LoadWAV)\b",
        r"\bALSA\b", r"\bPipeWire\b", r"\bPulseAudio\b", r"/proc/asound",
    ),
    "capture": terms(
        r"\bscreenshot\b", r"\bcapture[_ -]?screen\b", r"\bframebuffer\b",
        r"\bfbgrab\b", r"\bmufbset\b", r"\bgrim\b", r"\bswaymsg\b",
        r"\bglReadPixels\b",
    ),
    "debugger": terms(
        r"\bgdbserver\b", r"\btarget (?:extended-)?remote\b", r"\bset sysroot\b",
        r"\bwatchpoint\b", r"\bset logging\b", r"\bcore dump\b", r"\bstrace\b",
    ),
    "deploy": terms(
        r"\bdeploy\b", r"\bautoinstall\b", r"\brsync\b", r"\batomic rename\b",
        r"\bscp\b", r"\binstall(?:ation)? dir(?:ectory)?\b",
    ),
    "input": terms(
        r"\bevemu(?:-(?:describe|device|event|play|record))?\b", r"\bevtest\b",
        r"\buinput\b", r"\bcontroller\b", r"\bgamepad\b", r"\bjoystick\b",
        r"\bgptokeyb?2?\b", r"\bSDL_GAMECONTROLLERCONFIG\b",
        r"\bSDL[_ -]?(?:mapping|GameController|Joystick)", r"\bJSIOCG",
        r"\binput[_ -]?sequence\b",
    ),
    "integrity": terms(
        r"\bsha256(?:sum)?\b", r"\bhash[_ -]?(?:tree|data|manifest)\b",
        r"\bfile manifest\b", r"\bbefore[_ -]?after\b",
    ),
    "launch": terms(
        r"\bPortMaster\b", r"\bfrontend\b", r"\bEmulationStation\b",
        r"\brunningGame\b", r"\bmuxlaunch\b", r"\brom_go\b",
        r"\bpm_platform_helper\b", r"\bpm_finish\b", r"\bforeground_process\b",
    ),
    "network": terms(
        r"\bpcap\b", r"\btcpdump\b", r"\bAF_PACKET\b", r"\bSOCK_RAW\b",
        r"\bretransmission\b", r"\brecvfrom\b", r"\bsendto\b", r"\bzeroconf\b",
    ),
    "performance": terms(
        r"\bbenchmark\b", r"\bframe[_ -]?(?:interval|pacing|timing)\b",
        r"\b(?:egl|glX)?SwapBuffers\b", r"\bSDL_GL_SwapWindow\b",
        r"\bsmaps_rollup\b", r"/proc/.+/task", r"\bperf\b",
    ),
    "probe": terms(
        r"\bdevice[_ -]?probe\b", r"\bdevice profile\b",
        r"/proc/bus/input/devices", r"\breadelf\b", r"\bdevice[- ]tree\b",
        r"\bdiagnostics?\b", r"\bdlopen\b", r"\bdlsym\b",
    ),
    "reverse": terms(
        r"\bghidra\b", r"\bradare2?\b", r"\br2(?:pipe)?\b", r"\brizin\b",
        r"\brz-(?:asm|bin|diff|find|gg|hash|run)\b", r"\bS3E\b",
        r"\bimport[_ -]?table\b", r"\bThumb\b",
    ),
}

SUFFIX_CATEGORIES = {
    ".events": "input", ".evemu": "input", ".gdb": "debugger",
    ".gdbinit": "debugger", ".gptk": "input", ".r2": "reverse", ".rz": "reverse",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", type=Path, default=[Path.cwd()])
    parser.add_argument(
        "--include-temp", action="store_true",
        help="inspect top-level /private/tmp helpers plus specialized files three levels deep",
    )
    parser.add_argument(
        "--modified-within-days", type=float,
        help="keep only files modified within this many days",
    )
    parser.add_argument(
        "--category", action="append", choices=sorted(CATEGORY_PATTERNS),
        help="keep records matching this category; repeat to match any listed category",
    )
    parser.add_argument(
        "--path-contains", action="append", default=[],
        help="keep paths containing this text; repeat to match any listed value",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of TSV")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()
    if args.max_bytes < 1:
        parser.error("--max-bytes must be positive")
    if args.modified_within_days is not None and (
        not math.isfinite(args.modified_within_days)
        or args.modified_within_days < 0
    ):
        parser.error("--modified-within-days must be finite and nonnegative")
    if any(not value for value in args.path_contains):
        parser.error("--path-contains must not be empty")
    return args


def is_skipped_directory(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith(".dSYM")


def contains_tool_directory(parts: tuple[str, ...]) -> bool:
    return any(part in TOOL_DIRS for part in parts)


def is_project_candidate(path: Path, root: Path, tooling: bool) -> bool:
    suffix = path.suffix.lower()
    if suffix in SPECIALIZED_SUFFIXES:
        return True
    if tooling:
        return suffix in SCRIPT_SUFFIXES
    return path.parent == root and suffix in SCRIPT_SUFFIXES


def iter_project_files(root: Path) -> Iterator[tuple[Path, bool]]:
    if root.is_file():
        yield root, True
        return
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(name for name in dirs if not is_skipped_directory(name))
        tooling = contains_tool_directory(current_path.relative_to(root).parts)
        for name in sorted(files):
            path = current_path / name
            if is_project_candidate(path, root, tooling):
                yield path, tooling


def iter_temp_files(root: Path) -> Iterator[tuple[Path, bool]]:
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = sorted(
            name for name in dirs if depth < 3 and not is_skipped_directory(name)
        )
        for name in sorted(files):
            path = current_path / name
            suffix = path.suffix.lower()
            if (
                (depth == 0 and suffix in TEMP_SCRIPT_SUFFIXES)
                or suffix in SPECIALIZED_SUFFIXES
            ):
                yield path, True


def inspect(
    path: Path, max_bytes: int, keep_unclassified: bool, origin: str,
) -> dict[str, object] | None:
    suffix = path.suffix.lower()
    if suffix not in TEXT_SUFFIXES:
        return None
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
            return None
        with path.open("rb") as handle:
            data = handle.read(READ_LIMIT)
    except OSError:
        return None
    if b"\x00" in data:
        return None
    if suffix == "" and not data.startswith(b"#!"):
        return None

    content = f"{path.name}\n{data.decode('utf-8', errors='replace')}"
    categories = {
        name for name, pattern in CATEGORY_PATTERNS.items() if pattern.search(content)
    }
    implied = SUFFIX_CATEGORIES.get(suffix)
    if implied:
        categories.add(implied)
    if not categories:
        if not keep_unclassified:
            return None
        categories.add("unclassified")
    return {
        "path": str(path.resolve()), "origin": origin,
        "categories": sorted(categories), "bytes": metadata.st_size,
        "modified_ns": metadata.st_mtime_ns,
    }


def main() -> int:
    args = parse_args()
    records: dict[str, dict[str, object]] = {}
    for requested in args.roots:
        root = requested.expanduser().resolve()
        if not root.exists():
            print(f"warning: root does not exist: {root}", file=sys.stderr)
            continue
        for path, keep_unclassified in iter_project_files(root):
            record = inspect(path, args.max_bytes, keep_unclassified, "project")
            if record:
                records[str(record["path"])] = record

    if args.include_temp:
        for path, keep_unclassified in iter_temp_files(Path("/private/tmp")):
            record = inspect(path, args.max_bytes, keep_unclassified, "temporary")
            if record:
                records[str(record["path"])] = record

    cutoff_ns = None
    if args.modified_within_days is not None:
        cutoff_ns = time.time_ns() - int(
            args.modified_within_days * 86400 * 1_000_000_000
        )
    requested_categories = set(args.category or [])
    path_terms = [value.casefold() for value in args.path_contains]

    def keep_record(record: dict[str, object]) -> bool:
        if cutoff_ns is not None and int(record["modified_ns"]) < cutoff_ns:
            return False
        if requested_categories and not requested_categories.intersection(
            record["categories"]
        ):
            return False
        path = str(record["path"]).casefold()
        return not path_terms or any(term in path for term in path_terms)

    def order_key(record: dict[str, object]) -> tuple[object, ...]:
        if record["origin"] == "project":
            return (0, str(record["path"]))
        return (1, -int(record["modified_ns"]), str(record["path"]))

    ordered = sorted(
        (record for record in records.values() if keep_record(record)),
        key=order_key,
    )
    if args.json:
        json.dump(ordered, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("origin\tcategories\tbytes\tpath")
    for record in ordered:
        categories = ",".join(record["categories"])
        print(f"{record['origin']}\t{categories}\t{record['bytes']}\t{record['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
