"""Validation and normalization for handheld input-sequence plans."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable


CONTROL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")
MAX_STEPS = 1000
MAX_DURATION_MS = 600_000
MAX_RUNTIME_MS = 3_600_000


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class Plan:
    name: str
    default_hold_ms: int
    default_timeout_ms: int
    max_runtime_ms: int
    steps: tuple[dict[str, Any], ...]
    sha256: str


def load_plan(path: Path) -> Plan:
    try:
        data = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise PlanError(f"cannot read sequence: {error}") from error
    if not isinstance(data, dict):
        raise PlanError("sequence root must be an object")

    _reject_unknown(
        data,
        {"$schema", "name", "default_hold_ms", "default_timeout_ms", "max_runtime_ms", "steps"},
        "sequence",
    )
    name = _name(data.get("name", path.stem), "sequence.name")
    hold_ms = _integer(data.get("default_hold_ms", 120), "default_hold_ms", 1, MAX_DURATION_MS)
    timeout_ms = _integer(data.get("default_timeout_ms", 3000), "default_timeout_ms", 100, 60_000)
    runtime_ms = _integer(data.get("max_runtime_ms", 60_000), "max_runtime_ms", 1, MAX_RUNTIME_MS)
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PlanError("steps must be a non-empty array")
    if len(raw_steps) > MAX_STEPS:
        raise PlanError(f"steps exceeds {MAX_STEPS}")

    steps = tuple(
        _normalize_step(item, index, hold_ms, timeout_ms)
        for index, item in enumerate(raw_steps)
    )
    normalized = {
        "name": name,
        "default_hold_ms": hold_ms,
        "default_timeout_ms": timeout_ms,
        "max_runtime_ms": runtime_ms,
        "steps": steps,
    }
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return Plan(
        name,
        hold_ms,
        timeout_ms,
        runtime_ms,
        steps,
        hashlib.sha256(canonical).hexdigest(),
    )


def _normalize_step(
    value: Any, index: int, default_hold_ms: int, default_timeout_ms: int,
) -> dict[str, Any]:
    label = f"steps[{index}]"
    if not isinstance(value, dict):
        raise PlanError(f"{label} must be an object")
    action = value.get("action")
    normalizers: dict[str, Callable[[dict[str, Any], str, int, int], dict[str, Any]]] = {
        "axis": _axis,
        "chord": _chord,
        "down": _button,
        "hold": _hold,
        "mark": _mark,
        "move": _move,
        "tap": _tap,
        "up": _button,
        "wait": _wait,
    }
    if not isinstance(action, str) or action not in normalizers:
        choices = ", ".join(sorted(normalizers))
        raise PlanError(f"{label}.action must be one of {choices}")
    return normalizers[action](value, label, default_hold_ms, default_timeout_ms)


def _wait(value: dict[str, Any], label: str, _hold: int, _timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "duration_ms"}, label)
    return {"action": "wait", "duration_ms": _duration(value, label, "duration_ms", 0, 0)}


def _mark(value: dict[str, Any], label: str, _hold: int, _timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "name", "after_ms"}, label)
    return {
        "action": "mark",
        "name": _name(value.get("name"), f"{label}.name"),
        "after_ms": _after(value, label),
    }


def _button(value: dict[str, Any], label: str, _hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "control", "after_ms", "timeout_ms"}, label)
    return _timed(value, label, timeout)


def _tap(value: dict[str, Any], label: str, hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "control", "hold_ms", "after_ms", "timeout_ms"}, label)
    result = _timed(value, label, timeout)
    result["duration_ms"] = _duration(value, label, "hold_ms", hold, 1)
    return result


def _hold(value: dict[str, Any], label: str, hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "control", "duration_ms", "after_ms", "timeout_ms"}, label)
    result = _timed(value, label, timeout)
    result["duration_ms"] = _duration(value, label, "duration_ms", hold, 1)
    return result


def _chord(value: dict[str, Any], label: str, hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "controls", "duration_ms", "after_ms", "timeout_ms"}, label)
    raw_controls = value.get("controls")
    if not isinstance(raw_controls, list) or not 2 <= len(raw_controls) <= 8:
        raise PlanError(f"{label}.controls must contain 2 to 8 controls")
    controls = [_control(item, f"{label}.controls") for item in raw_controls]
    if len(set(controls)) != len(controls):
        raise PlanError(f"{label}.controls contains duplicates")
    return {
        "action": "chord",
        "controls": controls,
        "duration_ms": _duration(value, label, "duration_ms", hold, 1),
        "after_ms": _after(value, label),
        "timeout_ms": _timeout(value, label, timeout),
    }


def _axis(value: dict[str, Any], label: str, _hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(
        value,
        {"action", "control", "value", "duration_ms", "after_ms", "timeout_ms"},
        label,
    )
    axis_value = value.get("value")
    if isinstance(axis_value, bool) or not isinstance(axis_value, (int, float)):
        raise PlanError(f"{label}.value must be a number between -1 and 1")
    axis_value = float(axis_value)
    if not -1.0 <= axis_value <= 1.0:
        raise PlanError(f"{label}.value must be a number between -1 and 1")
    result = _timed(value, label, timeout)
    result["value"] = axis_value
    if "duration_ms" in value:
        result["duration_ms"] = _duration(value, label, "duration_ms", 0, 1)
    return result


def _move(value: dict[str, Any], label: str, _hold: int, timeout: int) -> dict[str, Any]:
    _reject_unknown(value, {"action", "control", "value", "after_ms", "timeout_ms"}, label)
    result = _timed(value, label, timeout)
    result["value"] = _integer(value.get("value"), f"{label}.value", -32768, 32767)
    return result


def _timed(value: dict[str, Any], label: str, timeout: int) -> dict[str, Any]:
    return {
        "action": value["action"],
        "control": _control(value.get("control"), f"{label}.control"),
        "after_ms": _after(value, label),
        "timeout_ms": _timeout(value, label, timeout),
    }


def _duration(value: dict[str, Any], label: str, field: str, default: int, minimum: int) -> int:
    return _integer(value.get(field, default), f"{label}.{field}", minimum, MAX_DURATION_MS)


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlanError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise PlanError(f"{name} must be between {minimum} and {maximum}")
    return value


def _name(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise PlanError(f"{name} must be 1 to 120 characters")
    return value.strip()


def _control(value: Any, name: str) -> str:
    if not isinstance(value, str) or not CONTROL_PATTERN.fullmatch(value):
        raise PlanError(f"{name} is not a valid semantic control")
    return value


def _after(value: dict[str, Any], label: str) -> int:
    return _integer(value.get("after_ms", 0), f"{label}.after_ms", 0, MAX_DURATION_MS)


def _timeout(value: dict[str, Any], label: str, default: int) -> int:
    return _integer(value.get("timeout_ms", default), f"{label}.timeout_ms", 100, 60_000)


def _reject_unknown(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PlanError(f"{label} has unknown fields: {', '.join(unknown)}")
