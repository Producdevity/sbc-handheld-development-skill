import json
from pathlib import Path
import tempfile
import unittest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from input_sequence_plan import PlanError, load_plan


class InputSequencePlanTest(unittest.TestCase):
    def test_shipped_examples_load(self) -> None:
        gamepad = load_plan(ROOT / "examples" / "input-sequence.json")
        pointer = load_plan(ROOT / "examples" / "pointer-sequence.json")
        self.assertEqual(gamepad.name, "gamepad-input-sequence")
        self.assertEqual(pointer.steps[0]["action"], "move")

    def test_unknown_field_is_rejected(self) -> None:
        plan = {"steps": [{"action": "wait", "duration_ms": 1, "typo": True}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(PlanError, "unknown fields"):
                load_plan(path)

    def test_pointer_delta_must_be_integer(self) -> None:
        plan = {
            "steps": [
                {"action": "move", "control": "pointer.x", "value": 1.5}
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(PlanError, "must be an integer"):
                load_plan(path)


if __name__ == "__main__":
    unittest.main()
