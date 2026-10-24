import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RunInputSequenceTest(unittest.TestCase):
    def test_pointer_plan_reaches_adapter_and_cleans_up(self) -> None:
        plan = {
            "default_hold_ms": 1,
            "max_runtime_ms": 5000,
            "steps": [
                {"action": "move", "control": "pointer.x", "value": 3},
                {"action": "tap", "control": "pointer.primary"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            plan_path = temporary / "plan.json"
            calls_path = temporary / "calls.jsonl"
            log_path = temporary / "result.jsonl"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_input_sequence.py"),
                    str(plan_path),
                    "--log",
                    str(log_path),
                    "--",
                    sys.executable,
                    str(ROOT / "tests" / "fake_input_adapter.py"),
                    str(calls_path),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertEqual(
                calls,
                [
                    ["move", "pointer.x", "3"],
                    ["down", "pointer.primary"],
                    ["up", "pointer.primary"],
                    ["release-all"],
                ],
            )

    def test_hold_duration_starts_after_down_adapter_returns(self) -> None:
        plan = {
            "default_hold_ms": 120,
            "max_runtime_ms": 5000,
            "steps": [
                {"action": "tap", "control": "face.south"},
                {"action": "mark", "name": "complete"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            plan_path = temporary / "plan.json"
            calls_path = temporary / "calls.jsonl"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_input_sequence.py"),
                    str(plan_path),
                    "--",
                    sys.executable,
                    str(ROOT / "tests" / "delayed_input_adapter.py"),
                    str(calls_path),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
            down, up = calls[:2]
            held_ms = (up["monotonic_ns"] - down["monotonic_ns"]) / 1_000_000
            self.assertGreaterEqual(held_ms, 110)

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertTrue(any(record.get("kind") == "mark" for record in records))


if __name__ == "__main__":
    unittest.main()
