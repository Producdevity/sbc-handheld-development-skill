from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import hash_tree


class HashTreeTest(unittest.TestCase):
    def test_manifest_is_stable_and_reports_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty").mkdir()
            (root / "data.bin").write_bytes(b"first")
            (root / "link").symlink_to("data.bin")

            before = hash_tree.build_manifest(root, set())
            after = hash_tree.build_manifest(root, set())
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(hash_tree.compare(before, after), 0)
            self.assertIn("match", output.getvalue())

            (root / "data.bin").write_bytes(b"second")
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(
                    hash_tree.compare(before, hash_tree.build_manifest(root, set())), 1
                )
            self.assertIn("changed\tdata.bin", output.getvalue())


if __name__ == "__main__":
    unittest.main()
