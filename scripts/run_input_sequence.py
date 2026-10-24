#!/usr/bin/env python3
"""Run a bounded semantic input sequence through an external command adapter."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any

from input_sequence_plan import Plan, PlanError, load_plan


OUTPUT_LIMIT = 4096


class SequenceError(RuntimeError):
    pass


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    separator = argv.index("--") if "--" in argv else len(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sequence", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv[:separator])
    runner = argv[separator + 1 :] if separator < len(argv) else []
    if not args.dry_run and not runner:
        parser.error("a command adapter is required after -- unless --dry-run is used")
    return args, runner


class Log:
    def __init__(self, path: Path | None) -> None:
        self._handle = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = path.open("x", encoding="utf-8")

    def write(self, **record: Any) -> None:
        line = json.dumps(record, sort_keys=True)
        print(line, flush=True)
        if self._handle is not None:
            self._handle.write(line + "\n")
            self._handle.flush()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()


class Sequence:
    def __init__(self, plan: Plan, runner: list[str], log: Log, dry_run: bool) -> None:
        self.plan = plan
        self.runner = runner
        self.log = log
        self.dry_run = dry_run
        self.start = time.monotonic()
        self.nominal_ms = 0
        self.cleaned = False

    def elapsed_ms(self) -> int:
        return round((time.monotonic() - self.start) * 1000)

    def wait(self, duration_ms: int) -> None:
        self.nominal_ms += duration_ms
        if self.nominal_ms > self.plan.max_runtime_ms:
            raise SequenceError("nominal delays exceed max_runtime_ms")
        if self.dry_run:
            return
        deadline = time.monotonic() + duration_ms / 1000
        while time.monotonic() < deadline:
            self._check_runtime()
            time.sleep(min(deadline - time.monotonic(), 0.1))

    def command(self, operation: str, *arguments: str, timeout_ms: int) -> None:
        record: dict[str, Any] = {
            "kind": "command",
            "operation": operation,
            "arguments": arguments,
            "nominal_ms": self.nominal_ms,
            "actual_ms": self.elapsed_ms(),
        }
        if self.dry_run:
            self.log.write(**record, dry_run=True)
            return
        self._check_runtime()
        remaining_ms = self.plan.max_runtime_ms - self.elapsed_ms()
        if remaining_ms <= 0:
            raise SequenceError("sequence exceeded max_runtime_ms")
        try:
            result = subprocess.run(
                [*self.runner, operation, *arguments],
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=min(timeout_ms, remaining_ms) / 1000,
            )
        except subprocess.TimeoutExpired as error:
            self.log.write(**record, status="timeout", timeout_ms=timeout_ms)
            raise SequenceError(f"command timed out during {operation}") from error
        self.log.write(
            **record,
            status="ok" if result.returncode == 0 else "failed",
            returncode=result.returncode,
            stdout=result.stdout[-OUTPUT_LIMIT:],
            stderr=result.stderr[-OUTPUT_LIMIT:],
            finished_ms=self.elapsed_ms(),
        )
        if result.returncode:
            raise SequenceError(f"command failed during {operation}: {result.returncode}")

    def release_all(self) -> bool:
        if self.cleaned or self.dry_run or not self.runner:
            return True
        self.cleaned = True
        try:
            result = subprocess.run(
                [*self.runner, "release-all"],
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=3,
            )
            self.log.write(
                kind="cleanup", operation="release-all", actual_ms=self.elapsed_ms(),
                returncode=result.returncode, stdout=result.stdout[-OUTPUT_LIMIT:],
                stderr=result.stderr[-OUTPUT_LIMIT:],
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as error:
            self.log.write(kind="cleanup", operation="release-all", error=str(error))
            return False

    def run(self) -> None:
        self.log.write(
            kind="header", schema=2, name=self.plan.name,
            sequence_sha256=self.plan.sha256,
            started_utc=datetime.now(timezone.utc).isoformat(), dry_run=self.dry_run,
        )
        for index, step in enumerate(self.plan.steps):
            self.log.write(
                kind="step", index=index, action=step["action"],
                nominal_ms=self.nominal_ms, actual_ms=self.elapsed_ms(),
            )
            self._run_step(step)
        if not self.release_all():
            raise SequenceError("release-all cleanup failed")
        self.log.write(kind="complete", nominal_ms=self.nominal_ms, actual_ms=self.elapsed_ms())

    def _run_step(self, step: dict[str, Any]) -> None:
        action = step["action"]
        if action == "wait":
            self.wait(step["duration_ms"])
            return
        if action == "mark":
            self.log.write(
                kind="mark", name=step["name"], nominal_ms=self.nominal_ms,
                actual_ms=self.elapsed_ms(),
            )
            self.wait(step["after_ms"])
            return

        timeout = step["timeout_ms"]
        if action in {"tap", "hold"}:
            self.command("down", step["control"], timeout_ms=timeout)
            self.wait(step["duration_ms"])
            self.command("up", step["control"], timeout_ms=timeout)
        elif action == "chord":
            for control in step["controls"]:
                self.command("down", control, timeout_ms=timeout)
            self.wait(step["duration_ms"])
            for control in reversed(step["controls"]):
                self.command("up", control, timeout_ms=timeout)
        elif action in {"down", "up"}:
            self.command(action, step["control"], timeout_ms=timeout)
        elif action == "axis":
            self.command(
                "axis", step["control"], format(step["value"], ".9g"),
                timeout_ms=timeout,
            )
            if "duration_ms" in step:
                self.wait(step["duration_ms"])
                self.command("axis", step["control"], "0", timeout_ms=timeout)
        elif action == "move":
            self.command("move", step["control"], str(step["value"]), timeout_ms=timeout)
        self.wait(step["after_ms"])

    def _check_runtime(self) -> None:
        if self.elapsed_ms() > self.plan.max_runtime_ms:
            raise SequenceError("sequence exceeded max_runtime_ms")


def interrupted(signum: int, _frame: Any) -> None:
    raise InterruptedError(f"received signal {signum}")


def main(argv: list[str]) -> int:
    args, runner = parse_args(argv)
    try:
        log = Log(args.log)
    except OSError as error:
        print(f"cannot open log: {error}", file=sys.stderr)
        return 1

    sequence: Sequence | None = None
    try:
        sequence = Sequence(load_plan(args.sequence), runner, log, args.dry_run)
        signal.signal(signal.SIGINT, interrupted)
        signal.signal(signal.SIGTERM, interrupted)
        sequence.run()
        return 0
    except (PlanError, SequenceError, InterruptedError, OSError) as error:
        log.write(kind="error", error=str(error))
        return 1
    finally:
        if sequence is not None:
            sequence.release_all()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
